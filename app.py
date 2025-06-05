import streamlit as st
import pandas as pd
import base64
import requests
from PIL import Image
import io
import os
from difflib import get_close_matches

# Configuración de Firebase (sustituir con tu propia configuración)
FIREBASE_STORAGE_BUCKET = "https://firebasestorage.googleapis.com/v0/b/TU_BUCKET.appspot.com/o"

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

st.title("Panel Principal")
st.subheader(f"Bienvenido, {st.session_state.user}")

opcion = st.selectbox("Selecciona una opción:", [
    "Ver inventario de reactivos",
    "Buscar reactivo",
    "Ver inventario de anticuerpos",
    "Buscar anticuerpo"
])

if opcion == "Ver inventario de reactivos":
    st.subheader("Inventario de Reactivos (orden alfabético)")
    for nombre in sorted(data['Nombre'].unique()):
        st.markdown(f"- {nombre}")

elif opcion == "Buscar reactivo":
    search = st.text_input("Buscar reactivo por nombre")

    if search:
        matches = data[data['Nombre'].str.contains(search, case=False)]
        if matches.empty:
            similares = get_close_matches(search, data['Nombre'].tolist(), n=3, cutoff=0.5)
            matches = data[data['Nombre'].isin(similares)]

        if not matches.empty:
            opciones = sorted(matches['Nombre'].unique())
            selected = st.selectbox("Resultados:", opciones)
            seleccionados = data[data['Nombre'] == selected]
            info = seleccionados.iloc[0]

            st.header(selected)

            if info.get('Foto') and isinstance(info['Foto'], str) and info['Foto'].startswith("http"):
                st.image(info['Foto'], use_column_width=True)
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
                    filename = selected.replace(" ", "_") + ".jpg"
                    response = requests.post(
                        f"{FIREBASE_STORAGE_BUCKET}?name={filename}",
                        headers={"Content-Type": "image/jpeg"},
                        data=buffer.getvalue()
                    )
                    if response.status_code in [200, 201]:
                        photo_url = f"{FIREBASE_STORAGE_BUCKET.replace('/o', '')}/o/{filename}?alt=media"
                        st.success("Foto subida exitosamente")
                        st.image(photo_url, use_column_width=True)
                    else:
                        st.error("Error al subir la foto")

            st.markdown(f"**Ubicación:** {info.get('Ubicación', 'No disponible')}")
            etiquetas = ', '.join(seleccionados['Numero'].dropna().astype(str).unique())
            empresas = ', '.join(seleccionados['Empresa'].dropna().astype(str).unique())
            catalogos = ', '.join(seleccionados['Catalogo'].dropna().astype(str).unique())
            st.markdown(f"**Número de etiqueta:** {etiquetas}")
            st.markdown(f"**Empresa:** {empresas}")
            st.markdown(f"**Catálogo:** {catalogos}")
            st.markdown(f"**Observaciones:** {info.get('Observaciones', 'No disponible')}")

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

elif opcion.startswith("Inventario de anticuerpos"):
    st.warning("Esta sección estará disponible pronto. Puedes proporcionarme el inventario cuando quieras.")
