import os
import logging
from typing import Dict, Any, List
from datetime import datetime

import streamlit as st
import google.generativeai as genai

from logging_config import setup_logging
from firestore_setup import db

setup_logging()
logger = logging.getLogger("volunteer_agent_firestore")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY # optional, if any code expects env var
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

VOLUNTEERS_COLLECTION = "volunteers"
SESSIONS_COLLECTION = "sessions"


def load_volunteer_profile(volunteer_id: str) -> Dict[str, Any]:
    """Load or create volunteer profile from Firestore"""
    doc_ref = db.collection(VOLUNTEERS_COLLECTION).document(volunteer_id)
    snap = doc_ref.get()
    if snap.exists:
        profile = snap.to_dict()
        profile["id"] = volunteer_id
        logger.info(f"Loaded volunteer profile for {volunteer_id}")
        return profile

    # Create new profile if doesn't exist
    profile = {
        "id": volunteer_id,
        "status": "offline",
        "topics": [],
        "availability": {},
        "students_assigned": [],
        "sessions_completed": 0,
        "total_hours": 0.0,
        "rating": 0.0,
    }
    doc_ref.set({k: v for k, v in profile.items() if k != "id"})
    logger.info(f"Created new volunteer profile for {volunteer_id}")
    return profile


def save_volunteer_profile(profile: Dict[str, Any]) -> None:
    """Save volunteer profile to Firestore"""
    doc_ref = db.collection(VOLUNTEERS_COLLECTION).document(profile["id"])
    data = dict(profile)
    data.pop("id", None)
    doc_ref.set(data)
    logger.info(f"Saved volunteer profile for {profile['id']}")


def set_availability(volunteer_id: str, day: str, start_time: str, end_time: str) -> bool:
    """Set availability for a specific day"""
    profile = load_volunteer_profile(volunteer_id)
    
    if "availability" not in profile:
        profile["availability"] = {}
    
    profile["availability"][day] = {
        "start": start_time,
        "end": end_time
    }
    
    save_volunteer_profile(profile)
    logger.info(f"Updated availability for {volunteer_id} on {day}")
    return True


def set_status(volunteer_id: str, status: str) -> bool:
    """Set volunteer status: available, busy, offline"""
    valid_statuses = ["available", "busy", "offline"]
    if status not in valid_statuses:
        return False
    
    profile = load_volunteer_profile(volunteer_id)
    profile["status"] = status
    save_volunteer_profile(profile)
    logger.info(f"Updated status for {volunteer_id} to {status}")
    return True


def add_topic(volunteer_id: str, topic: str) -> bool:
    """Add a topic that volunteer can mentor"""
    profile = load_volunteer_profile(volunteer_id)
    
    if topic not in profile["topics"]:
        profile["topics"].append(topic)
        save_volunteer_profile(profile)
        logger.info(f"Added topic {topic} for volunteer {volunteer_id}")
        return True
    return False


def remove_topics(volunteer_id: str, topics_to_remove: List[str]) -> bool:
    """Remove multiple topics from volunteer's profile"""
    profile = load_volunteer_profile(volunteer_id)
    
    for topic in topics_to_remove:
        if topic in profile["topics"]:
            profile["topics"].remove(topic)
    
    save_volunteer_profile(profile)
    logger.info(f"Removed {len(topics_to_remove)} topics from volunteer {volunteer_id}")
    return True


def create_session(volunteer_id: str, student_id: str, topic: str, scheduled_time: str) -> str:
    """Create a mentoring session"""
    session_ref = db.collection(SESSIONS_COLLECTION).document()
    session_data = {
        "volunteer_id": volunteer_id,
        "student_id": student_id,
        "topic": topic,
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "duration": 0,
        "notes": "",
        "created_at": datetime.now().isoformat(),
    }
    session_ref.set(session_data)
    logger.info(f"Created session: {session_ref.id}")
    return session_ref.id


def get_assigned_students(volunteer_id: str) -> List[Dict[str, Any]]:
    """Get list of students assigned to volunteer"""
    profile = load_volunteer_profile(volunteer_id)
    students_list = []
    
    for student_id in profile.get("students_assigned", []):
        student_ref = db.collection("student_profiles").document(student_id)
        student_snap = student_ref.get()
        if student_snap.exists:
            student_data = student_snap.to_dict()
            student_data["id"] = student_id
            students_list.append(student_data)
    
    return students_list


def get_scheduled_sessions(volunteer_id: str) -> List[Dict[str, Any]]:
    """Get upcoming scheduled sessions"""
    docs = db.collection(SESSIONS_COLLECTION).where(
        "volunteer_id", "==", volunteer_id
    ).where(
        "status", "==", "scheduled"
    ).stream()
    
    sessions = []
    for doc in docs:
        session_data = doc.to_dict()
        session_data["id"] = doc.id
        sessions.append(session_data)
    
    return sessions


def complete_session(session_id: str, duration: int, notes: str = "") -> bool:
    """Mark a session as completed"""
    session_ref = db.collection(SESSIONS_COLLECTION).document(session_id)
    session_snap = session_ref.get()
    
    if not session_snap.exists:
        return False
    
    session_data = session_snap.to_dict()
    session_data["status"] = "completed"
    session_data["duration"] = duration
    session_data["notes"] = notes
    session_data["completed_at"] = datetime.now().isoformat()
    
    session_ref.set(session_data)
    
    # Update volunteer stats
    volunteer_id = session_data["volunteer_id"]
    volunteer_profile = load_volunteer_profile(volunteer_id)
    volunteer_profile["sessions_completed"] += 1
    volunteer_profile["total_hours"] += (duration / 60)
    save_volunteer_profile(volunteer_profile)
    
    logger.info(f"Completed session {session_id}")
    return True


def cancel_session(session_id: str, reason: str = "") -> bool:
    """Cancel a scheduled session"""
    session_ref = db.collection(SESSIONS_COLLECTION).document(session_id)
    session_snap = session_ref.get()
    
    if not session_snap.exists:
        return False
    
    session_data = session_snap.to_dict()
    session_data["status"] = "cancelled"
    session_data["cancellation_reason"] = reason
    session_data["cancelled_at"] = datetime.now().isoformat()
    
    session_ref.set(session_data)
    logger.info(f"Cancelled session {session_id}")
    return True


def get_volunteer_stats(volunteer_id: str) -> Dict[str, Any]:
    """Get statistics for a volunteer"""
    profile = load_volunteer_profile(volunteer_id)
    
    return {
        "sessions_completed": profile.get("sessions_completed", 0),
        "total_hours": profile.get("total_hours", 0.0),
        "students_helped": len(profile.get("students_assigned", [])),
        "rating": profile.get("rating", 0.0),
        "topics": profile.get("topics", []),
        "status": profile.get("status", "offline"),
    }


def get_all_volunteers_by_topic(topic: str) -> List[Dict[str, Any]]:
    """Get all volunteers that can teach a specific topic"""
    docs = db.collection(VOLUNTEERS_COLLECTION).where(
        "topics", "array-contains", topic
    ).stream()
    
    volunteers = []
    for doc in docs:
        vol_data = doc.to_dict()
        vol_data["id"] = doc.id
        volunteers.append(vol_data)
    
    return volunteers
