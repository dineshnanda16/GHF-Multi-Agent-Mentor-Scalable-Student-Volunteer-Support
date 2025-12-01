import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
# Read the [firebase] section from Streamlit secrets
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)

# Initialize Firebase (only once)
db = firestore.client()

def get_db():
    return db