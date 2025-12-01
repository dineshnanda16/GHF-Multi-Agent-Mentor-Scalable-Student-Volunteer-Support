import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

if not firebase_admin._apps:
    # Read the JSON string from secrets
    service_account_info = json.loads(st.secrets["firebase_json"])
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_db():
    return get_db()