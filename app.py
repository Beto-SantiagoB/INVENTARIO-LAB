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
from datetime import datetime

# Configuración de Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred, {
        'storageBucket': st.secrets["firebase"]["project_id"] + '.appspot.com'
    })

db = firestore.client()
bucket = storage.bucket()

# Autenticación con Firestore (sin pyrebase)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_role = None

def login():
    st.title("Inicio de sesión")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        user_ref = db.collection("usuarios").document(email)
        doc = user_ref.get()
        if doc.exists:
            user_data = doc.to_dict()
            if user_data.get("password") == password:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.user_role = user_data.get("rol", "usuario")
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        else:
            st.error("Usuario no encontrado")

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
    st.subheader(f"Bienvenido, {st.session_state.user_email}")

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

        if st.session_state.user_role == "admin":
            if st.button("⚠️ Reactivos por agotarse"):
                st.session_state.pantalla = "reactivos_alerta"
                st.rerun()

    st.markdown("---")
    if st.button("🔓 Cerrar sesión"):
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_role = None
        st.session_state.pantalla = None
        st.rerun()

# Resto del código sin cambios...
