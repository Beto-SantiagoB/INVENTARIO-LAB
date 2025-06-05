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

st.title("Inventario de Reactivos")
st.subheader(f"Bienvenido, {st.session_state.user}")

search = st.text_input("Buscar reactivo")

if search:
    matches = data[data['Nombre'].str.contains(search, case=False)]
    if matches.empty:
        similares = get_close_matches(search, data['Nombre'].tolist(), n=3, cutoff=0.5)
        matches = data[data['Nombre'].isin(similares)]

    if not matches.empty:
        selected = st.selectbox("Resultados:", matches['Nombre'].tolist())
        selected_data = matches[matches['Nombre'] == selected].iloc[0]

        st.header(selected_data['Nombre'])

        if selected_data['Foto'] and isinstance(selected_data['Foto'], str) and selected_data['Foto'].startswith("http"):
            st.image(selected_data['Foto'], use_column_width=True)
        else:
            st.info("Sin foto disponible")
            uploaded = st.file_uploader("📸 Tomar/Subir foto", type=["jpg", "jpeg", "png"], accept_multiple_files=False, label_visibility="visible")
            if uploaded:
                image = Image.open(uploaded)
                image = image.convert("RGB")

                # Redimensionar si es necesario para mantener < 300 KB
                buffer = io.BytesIO()
                quality = 95
                while True:
                    buffer.seek(0)
                    image.save(buffer, format="JPEG", quality=quality)
                    size_kb = buffer.tell() / 1024
                    if size_kb < 300 or quality <= 10:
                        break
                    quality -= 5

                buffer.seek(0)
                encoded_image = base64.b64encode(buffer.read()).decode()
                filename = selected_data['Nombre'].replace(" ", "_") + ".jpg"

                # Subir a Firebase Storage (requiere configurar token si es necesario)
                response = requests.post(
                    f"{FIREBASE_STORAGE_BUCKET}?name={filename}",
                    headers={"Content-Type": "image/jpeg"},
                    data=base64.b64decode(encoded_image)
                )

                if response.status_code in [200, 201]:
                    photo_url = f"{FIREBASE_STORAGE_BUCKET.replace('/o', '')}/o/{filename}?alt=media"
                    st.success("Foto subida exitosamente")
                    st.image(photo_url, use_column_width=True)
                else:
                    st.error("Error al subir la foto")

        st.markdown(f"**Ubicación:** {selected_data['Ubicacion']}")
        st.markdown(f"**Número de etiqueta:** {selected_data['Numero']}")
        st.markdown(f"**Empresa:** {selected_data['Empresa']}")
        st.markdown(f"**Catálogo:** {selected_data['Catalogo']}")
        st.markdown(f"**Observaciones:** {selected_data['Observaciones']}")

        if st.button("🔴 Reportar como en riesgo de agotarse"):
            st.warning("Se ha reportado este reactivo como bajo (simulado)")

        if st.session_state.user != "admin":
            st.subheader("Sugerir cambios")
            with st.form("sugerencia_form"):
                nuevo_nombre = st.text_input("Nuevo nombre", value=selected_data['Nombre'])
                nueva_empresa = st.text_input("Nueva empresa", value=selected_data['Empresa'])
                nuevo_catalogo = st.text_input("Nuevo catálogo", value=selected_data['Catalogo'])
                nueva_obs = st.text_area("Nueva observación", value=selected_data['Observaciones'])
                submitted = st.form_submit_button("Enviar sugerencia")
                if submitted:
                    st.success("Sugerencia enviada para revisión (simulado)")
else:
    st.info("Ingresa el nombre de un reactivo para buscar")
