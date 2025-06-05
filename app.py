import streamlit as st
import pandas as pd
import base64
import requests
from PIL import Image
import io
import os
from difflib import get_close_matches
import openai
import firebase_admin
from firebase_admin import credentials, firestore, storage

# Configuración de Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'inventario-lab-c0974.appspot.com'  # Reemplaza con tu bucket real
    })

db = firestore.client()
bucket = storage.bucket()

# Usuarios simulados
users = {
    "admin": {"password": "admin123", "role": "admin"},
    "usuario": {"password": "usuario123", "role": "user"}
}

# Autenticación
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

def login():
    st.title("Inicio de sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        if username in users and users[username]["password"] == password:
            st.session_state.authenticated = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

if not st.session_state.authenticated:
    login()
    st.stop()

# Cargar inventario
@st.cache_data
def load_data():
    return pd.read_csv("reactivos.csv")

data = load_data()

if "pantalla" not in st.session_state:
    st.session_state.pantalla = None
if "reactivo_seleccionado" not in st.session_state:
    st.session_state.reactivo_seleccionado = None

if st.session_state.pantalla not in ["buscar_reactivo", "detalle_reactivo", "buscar_anticuerpo"]:
    st.title("Panel Principal")
    st.subheader(f"Bienvenido, {st.session_state.user}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Buscar reactivo"):
            st.session_state.pantalla = "buscar_reactivo"
            st.rerun()
        if st.button("📋 Ver inventario de reactivos"):
            st.session_state.pantalla = "ver_reactivos"
            st.rerun()

    with col2:
        if st.button("🔬 Buscar anticuerpo"):
            st.session_state.pantalla = "buscar_anticuerpo"
            st.rerun()
        if st.button("📄 Ver inventario de anticuerpos"):
            st.session_state.pantalla = "ver_anticuerpos"
            st.rerun()

if st.session_state.pantalla == "ver_reactivos":
    st.subheader("Inventario de Reactivos (orden alfabético)")
    for nombre in sorted(data['Nombre'].unique()):
        if st.button(nombre):
            st.session_state.reactivo_seleccionado = nombre
            st.session_state.pantalla = "detalle_reactivo"
            st.rerun()
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()

if st.session_state.pantalla in ["buscar_reactivo", "detalle_reactivo"]:
    if st.session_state.pantalla == "buscar_reactivo":
        search = st.text_input("Buscar reactivo por nombre")

        if search:
            matches = data[data['Nombre'].str.contains(search, case=False)]
            if matches.empty:
                similares = get_close_matches(search, data['Nombre'].tolist(), n=3, cutoff=0.5)
                matches = data[data['Nombre'].isin(similares)]

            if not matches.empty:
                opciones = sorted(matches['Nombre'].unique())
                selected = st.selectbox("Resultados:", opciones, index=0, key="select_result", label_visibility="visible")
                st.session_state.reactivo_seleccionado = selected

    if st.session_state.reactivo_seleccionado:
        seleccionados = data[data['Nombre'] == st.session_state.reactivo_seleccionado]
        info = seleccionados.iloc[0]
        st.header(st.session_state.reactivo_seleccionado)

        filename = st.session_state.reactivo_seleccionado.replace(" ", "_") + ".jpg"
        blob = bucket.blob(filename)

        if blob.exists():
            photo_url = blob.generate_signed_url(version="v4", expiration=3600)
            st.image(photo_url, use_column_width=True)
        else:
            st.info("Sin foto disponible")
            uploaded = st.file_uploader("📸 Tomar/Subir foto", type=["jpg", "jpeg", "png"], accept_multiple_files=False, label_visibility="visible")
            if uploaded:
                image = Image.open(uploaded).convert("RGB")
                buffer = io.BytesIO()
                quality = 95
                while True:
                    buffer.seek(0)
                    image.save(buffer, format="JPEG", quality=quality)
                    if buffer.tell() / 1024 < 300 or quality <= 10:
                        break
                    quality -= 5
                buffer.seek(0)
                blob.upload_from_file(buffer, content_type='image/jpeg')
                blob.make_public()
                st.success("Foto subida exitosamente")
                st.image(blob.public_url, use_column_width=True)

        st.markdown(f"**Ubicación:** {info.get('Ubicación', 'No disponible')}")
        etiquetas = ', '.join(seleccionados.get('Número', pd.Series(dtype=str)).dropna().astype(str).unique())
        empresas = ', '.join(seleccionados.get('Empresa', pd.Series(dtype=str)).dropna().astype(str).unique())
        catalogos = ', '.join(seleccionados.get('Catálogo', pd.Series(dtype=str)).dropna().astype(str).unique())

        st.markdown(f"**Número de etiqueta:** {etiquetas if etiquetas else 'No disponible'}")
        st.markdown(f"**Empresa:** {empresas if empresas else 'No disponible'}")
        st.markdown(f"**Catálogo:** {catalogos if catalogos else 'No disponible'}")

        # Observaciones generadas y guardadas en Firestore
        observacion = info.get('Observaciones')
        reactivo_id = st.session_state.reactivo_seleccionado.replace(" ", "_").lower()
        doc_ref = db.collection("observaciones").document(reactivo_id)
        doc = doc_ref.get()

        if doc.exists:
            texto_obs = doc.to_dict().get("texto")
        elif pd.notna(observacion):
            texto_obs = observacion
        else:
            descripcion = info['Nombre'] + ' ' + empresas + ' ' + catalogos
            try:
                respuesta = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Eres un asistente experto en seguridad química de laboratorio. Tu tarea es indicar si un reactivo requiere manejo especial, puede desecharse en el drenaje, o en la basura general, y mencionar cualquier precaución de seguridad importante."},
                        {"role": "user", "content": f"Reactivo: {descripcion}"}
                    ]
                )
                texto_obs = respuesta.choices[0].message.content
                doc_ref.set({"texto": texto_obs})
            except Exception as e:
                texto_obs = "No disponible (error de IA)"

        st.markdown(f"**Observaciones:** {texto_obs}")

        if st.button("🔴 Reportar como en riesgo de agotarse"):
            st.warning("Se ha reportado este reactivo como bajo (simulado)")

        if st.session_state.user != "admin":
            st.subheader("Sugerir cambios")
            with st.form("sugerencia_form"):
                nuevo_nombre = st.text_input("Nuevo nombre", value=info['Nombre'])
                nueva_empresa = st.text_input("Nueva empresa", value=empresas)
                nuevo_catalogo = st.text_input("Nuevo catálogo", value=catalogos)
                nueva_obs = st.text_area("Nueva observación", value=info.get('Observaciones', ''))
                submitted = st.form_submit_button("Enviar sugerencia")
                if submitted:
                    st.success("Sugerencia enviada para revisión (simulado)")

        if st.button("⬅️ Volver al menú principal"):
            st.session_state.pantalla = None
            st.session_state.reactivo_seleccionado = None
            st.rerun()

elif st.session_state.pantalla == "buscar_anticuerpo":
    search = st.text_input("Buscar anticuerpo por nombre")
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()

elif st.session_state.pantalla == "ver_anticuerpos":
    st.warning("Esta sección estará disponible pronto. Puedes proporcionarme el inventario cuando quieras.")
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()
