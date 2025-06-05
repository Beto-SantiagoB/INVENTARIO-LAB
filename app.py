import streamlit as st
import pandas as pd
import base64
import requests
from PIL import Image
import io
import os
from difflib import get_close_matches
# import openai  # Comentado temporalmente por falta de crédito
import firebase_admin
from firebase_admin import credentials, firestore, storage

# Configuración de Firebase desde st.secrets
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'inventario-lab-c0974.appspot.com'
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

    imagen_path = detalles["Imagen"].dropna().values[0] if "Imagen" in detalles.columns and not detalles["Imagen"].isna().all() else None
    if imagen_path:
        st.image(imagen_path)
    else:
        st.info("No hay imagen disponible.")

    def extraer_valores(columna):
        return detalles[columna].dropna().tolist() if columna in detalles.columns else []

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

elif st.session_state.pantalla == "buscar_reactivo":
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()

    st.title("Buscar Reactivo")
    query = st.text_input("Escribe el nombre del reactivo")

    resultados = data[data["Nombre"].str.contains(query, case=False, na=False)].drop_duplicates(subset="Nombre")

    for reactivo in resultados["Nombre"].sort_values():
        if st.button(reactivo):
            st.session_state.reactivo_seleccionado = reactivo
            st.session_state.pantalla = "detalle_reactivo"
            st.rerun()

elif st.session_state.pantalla in ["buscar_anticuerpo", "ver_anticuerpos", "añadir_reactivo", "añadir_anticuerpo"]:
    if st.button("⬅️ Volver al menú principal"):
        st.session_state.pantalla = None
        st.rerun()

    st.info(f"Pantalla: {st.session_state.pantalla} (contenido aún por implementar)")
