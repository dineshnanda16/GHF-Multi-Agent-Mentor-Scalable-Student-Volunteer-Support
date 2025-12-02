import os
import logging
from typing import Dict, Any

import streamlit as st
import google.generativeai as genai

from logging_config import setup_logging
from firestore_setup import db

setup_logging()
logger = logging.getLogger("student_agent_firestore")

print("DEBUG_SECRETS_KEYS:", list(st.secrets.keys()))
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY # optional, if any code expects env var
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

STUDENTS_COLLECTION = "student_profiles"


def load_student_profile(user_id: str) -> Dict[str, Any]:
    """Load or create student profile from Firestore"""
    doc_ref = db.collection(STUDENTS_COLLECTION).document(user_id)
    snap = doc_ref.get()
    if snap.exists:
        profile = snap.to_dict()
        profile["id"] = user_id
        logger.info(f"Loaded profile for {user_id}")
        return profile

    # Create new profile if doesn't exist
    profile = {
        "id": user_id,
        "weak_topics": [],
        "history": [],
    }
    doc_ref.set({k: v for k, v in profile.items() if k != "id"})
    logger.info(f"Created new profile for {user_id}")
    return profile


def save_student_profile(profile: Dict[str, Any]) -> None:
    """Save student profile to Firestore"""
    doc_ref = db.collection(STUDENTS_COLLECTION).document(profile["id"])
    data = dict(profile)
    data.pop("id", None)
    doc_ref.set(data)
    logger.info(f"Saved profile for {profile['id']}")


def student_agent(user_id: str, message: str) -> str:
    """Main student mentor agent"""
    logger.info(f"Student message | user_id={user_id} | msg={message}")

    # Load or create profile
    profile = load_student_profile(user_id)
    profile["history"].append({"role": "student", "message": message})

    # Build conversation history
    history_text = "\n".join(
        [f"Student: {h['message']}" for h in profile["history"][-5:]]
    )

    # Create prompt for Gemini
    prompt = f"""
You are a friendly college mentor for engineering / medicine / arts students.
Explain clearly, step by step, and give practical tips.

Student ID: {user_id}
Known weak topics: {profile['weak_topics']}

Recent conversation:
{history_text}

Reply to the student's latest message:
\"\"\"{message}\"\"\"
"""

    # Get response from Gemini
    response = model.generate_content(prompt)
    reply = response.text.strip()

    logger.info(f"Student reply | user_id={user_id} | chars={len(reply)}")
    
    # Save conversation
    profile["history"].append({"role": "mentor", "message": reply})
    save_student_profile(profile)

    return reply
