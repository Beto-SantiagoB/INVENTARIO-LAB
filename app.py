import streamlit as st
import pandas as pd
import base64
import requests
from PIL import Image
import io
import os
from difflib import get_close_matches
import firebase_admin
from firebase_admin import credentials, firestore, storage
import json
from urllib.parse import quote
from uuid import uuid4
import datetime

# Configuración de Firebase desde st.secrets
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'inventario-lab-c0974.firebasestorage.app'
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

if "mostrar_uploader" not in st.session_state:
    st.session_state.mostrar_uploader = False

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

# Panel principal
if st.session_state.pantalla is None:
    st.title("Laboratorio de patogénesis molecular")
    st.subheader(f"Bienvenido, {st.session_state.user}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Buscar reactivo"):
            st.session_state.pantalla = "buscar_reactivo"
            st.rerun()
        if st.button("📋 Ver inventario de reactivos"):
            st.session_state.pantalla = "ver_reactivos"
            st.rerun()
        if st.button("➕ Añadir reactivo"):
            st.session_state.pantalla = "añadir_reactivo"
            st.rerun()

    with col2:
        if st.button("🔬 Buscar anticuerpo"):
            st.session_state.pantalla = "buscar_anticuerpo"
            st.rerun()
        if st.button("📄 Ver inventario de anticuerpos"):
            st.session_state.pantalla = "ver_anticuerpos"
            st.rerun()
        if st.button("➕ Añadir anticuerpo"):
            st.session_state.pantalla = "añadir_anticuerpo"
            st.rerun()
        if st.session_state.user == "admin":
            if st.button("⚠️ Reactivos por agotarse"):
                st.session_state.pantalla = "ver_alertas"
                st.rerun()

    st.markdown("---")
    if st.button("🔓 Cerrar sesión"):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.pantalla = None
        st.rerun()

# Submenús
elif st.session_state.pantalla == "ver_reactivos":
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()

    st.title("Inventario de Reactivos")
    reactivos = data["Nombre"].dropna().unique()
    reactivos.sort()
    for reactivo in reactivos:
        if st.button(reactivo):
            st.session_state.reactivo_seleccionado = reactivo
            st.session_state.pantalla = "detalle_reactivo"
            st.rerun()

elif st.session_state.pantalla == "detalle_reactivo":
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()

    reactivo = st.session_state.reactivo_seleccionado
    st.title(reactivo)
    detalles = data[data["Nombre"] == reactivo]

    try:
        doc_ref = db.collection("imagenes").document(reactivo)
        doc = doc_ref.get()
        if doc.exists:
            token = doc.to_dict().get("token")
            if token:
                url_imagen = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/reactivos%2F{quote(reactivo)}.jpg?alt=media&token={token}"
                st.image(url_imagen, caption="Imagen del reactivo", use_container_width=True)
            else:
                if st.button("No hay imagen disponible (Agregar)"):
                    st.session_state.mostrar_uploader = True
        else:
            if st.button("No hay imagen disponible (Agregar)"):
                st.session_state.mostrar_uploader = True
    except Exception as e:
        st.warning(f"Error al consultar Firestore: {e}")

    if st.session_state.mostrar_uploader:
        imagen_subida = st.file_uploader("Selecciona una imagen", type=["jpg", "jpeg", "png"], key=reactivo)
        if imagen_subida and st.button("Subir imagen"):
            imagen = Image.open(imagen_subida).convert("RGB")
            buffer = io.BytesIO()
            imagen.save(buffer, format="JPEG", quality=50)
            buffer.seek(0)

            token = str(uuid4())
            blob = bucket.blob(f"reactivos/{reactivo}.jpg")
            blob.metadata = {"firebaseStorageDownloadTokens": token}
            blob.upload_from_file(buffer, content_type='image/jpeg')

            try:
                db.collection("imagenes").document(reactivo).set({
                    "token": token,
                    "usuario": st.session_state.user,
                    "timestamp": datetime.datetime.now()
                })
                st.success("Imagen subida y token guardado correctamente")
                st.session_state.mostrar_uploader = False
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar token en Firestore: {e}")

    def extraer_valores(columna):
        if columna in detalles.columns:
            valores = detalles[columna].fillna("NA").tolist()
            return valores
        return ["NA"]

    etiquetas = extraer_valores("Número")
    ubicaciones = extraer_valores("Ubicación")
    empresas = extraer_valores("Empresa")
    catalogos = extraer_valores("Catálogo")
    observaciones = extraer_valores("Observaciones")

    st.write("**Número de etiqueta:**", ", ".join(etiquetas))
    st.write("**Ubicación:**", ", ".join(ubicaciones))
    st.write("**Empresa:**", ", ".join(empresas))
    st.write("**Catálogo:**", ", ".join(catalogos))
    st.write("**Observaciones:**", ", ".join(observaciones))

    if st.button("⚠️ Reportar que se está agotando"):
        st.warning("¡Este reactivo ha sido marcado como en riesgo de agotarse!")
        # Aquí podrías guardar el evento en Firestore si lo deseas
