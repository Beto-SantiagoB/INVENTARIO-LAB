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
import pyrebase

# Configurar Firebase con pyrebase (solo para autenticación)
firebase_config = {
    "apiKey": st.secrets["firebase_api_key"],
    "authDomain": f"{st.secrets['firebase']['project_id']}.firebaseapp.com",
    "projectId": st.secrets["firebase"]["project_id"],
    "storageBucket": st.secrets["firebase"]["project_id"] + ".appspot.com",
    "messagingSenderId": st.secrets["firebase_messaging_sender_id"],
    "appId": st.secrets["firebase_app_id"],
    "databaseURL": ""
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# Configuración de Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred, {
        'storageBucket': st.secrets["firebase"]["project_id"] + '.appspot.com'
    })

db = firestore.client()
bucket = storage.bucket()

# Autenticación
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None

def login():
    st.title("Inicio de sesión")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.rerun()
        except:
            st.error("Credenciales inválidas o error de conexión")

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

        if st.session_state.user_email and st.session_state.user_email.endswith("@admin.com"):
            if st.button("⚠️ Reactivos por agotarse"):
                st.session_state.pantalla = "reactivos_alerta"
                st.rerun()

    st.markdown("---")
    if st.button("🔓 Cerrar sesión"):
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.pantalla = None
        st.rerun()

# Resto del código sin cambios...
