# auth.py
from typing import Optional
from firestore_setup import db

USERS_COLLECTION = "users"

def get_user_by_email(email: str) -> Optional[dict]:
    """Get user from Firestore by email"""
    docs = db.collection(USERS_COLLECTION).where("email", "==", email).limit(1).stream()
    for d in docs:
        user = d.to_dict()
        user["id"] = d.id
        return user
    return None

def create_user(email: str, password: str, role: str = "student") -> dict:
    """Create new user in Firestore"""
    doc_ref = db.collection(USERS_COLLECTION).document()
    doc_ref.set({
        "email": email,
        "password": password,  # later: use bcrypt for hashing
        "role": role,
    })
    user = doc_ref.get().to_dict()
    user["id"] = doc_ref.id
    return user

def check_password(user: dict, password: str) -> bool:
    """Verify password (later: use bcrypt)"""
    return user["password"] == password
