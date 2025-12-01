# streamlit_app.py
import streamlit as st

from auth import get_user_by_email, create_user, check_password
from student_agent_firestore import student_agent
from volunteer_agent_firestore import (
    load_volunteer_profile,
    set_availability,
    set_status,
    add_topic,
    remove_topics,
    get_assigned_students,
    get_scheduled_sessions,
    complete_session,
    get_volunteer_stats,
)

st.set_page_config(page_title="GHF Mentor", page_icon="📚")

if "user" not in st.session_state:
    st.session_state["user"] = None


# ============================================
# LOGIN PAGE
# ============================================
def show_login():
    st.title("GHF Multi-Agent Mentor - Login")

    tab1, tab2 = st.tabs(["Login", "Sign up"])

    with tab1:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = get_user_by_email(email)
            if not user:
                st.error("User not found.")
            elif not check_password(user, password):
                st.error("Incorrect password.")
            else:
                st.session_state["user"] = user
                st.success("Logged in successfully!")
                st.rerun()

    with tab2:
        st.subheader("Sign up")
        email_su = st.text_input("Email (new user)", key="signup_email")
        password_su = st.text_input("Password (new user)", type="password", key="signup_password")
        role = st.selectbox("Role", ["student", "volunteer"], key="signup_role")
        if st.button("Create account"):
            existing = get_user_by_email(email_su)
            if existing:
                st.error("Email already registered.")
            elif not email_su or not password_su:
                st.error("Please enter email and password.")
            else:
                user = create_user(email_su, password_su, role=role)
                st.session_state["user"] = user
                st.success("Account created and logged in!")
                st.rerun()


# ============================================
# STUDENT DASHBOARD
# ============================================
def show_student_dashboard(user):
    st.title("🎓 GHF Student Mentor")
    st.write(f"Logged in as: **{user['email']}** (Student)")

    # Chat-style interface
    st.subheader("💬 Ask Your Mentor")
    
    message = st.text_area("Your question or topic:", placeholder="e.g., Explain linked lists")
    
    if st.button("Ask Mentor", key="ask_mentor_btn"):
        if not message.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("🤔 Mentor is thinking..."):
                reply = student_agent(user_id=user["id"], message=message)
            st.markdown("---")
            st.markdown("**✨ Mentor Reply:**")
            st.write(reply)
    
    st.write("---")
    if st.button("Logout", key="student_logout"):
        st.session_state["user"] = None
        st.rerun()


# ============================================
# VOLUNTEER DASHBOARD
# ============================================
def show_volunteer_dashboard(user):
    st.title("🎓 GHF Volunteer Dashboard")
    st.write(f"Logged in as: **{user['email']}** (Volunteer)")
    
    # Load volunteer profile
    volunteer_id = user["id"]
    vol_profile = load_volunteer_profile(volunteer_id)
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "Status & Topics",
        "My Students",
        "Sessions",
        "Statistics"
    ])
    
    # ---- TAB 1: Status & Topics & Availability ----
    with tab1:
        st.subheader("✨ Set Your Status & Availability")
        
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox(
                "Current Status",
                ["available", "busy", "offline"],
                index=0 if vol_profile["status"] == "available" else (1 if vol_profile["status"] == "busy" else 2)
            )
            if st.button("Update Status"):
                set_status(volunteer_id, status)
                st.success(f"✅ Status updated to {status}!")
                st.rerun()
        
        with col2:
            current_topics = vol_profile.get("topics", [])
            st.write(f"**Topics**: {len(current_topics)} selected")
        
        st.write("---")
        st.subheader("🏷️ Manage Your Topics")
        
        predefined_topics = ["DSA", "OS", "DBMS", "Web Dev", "Placements", "Interviews", "System Design"]
        current_topics = vol_profile.get("topics", [])
        
        st.write("**Select Predefined Topics:**")
        
        cols = st.columns(2)
        selected_topics = []
        
        for idx, topic in enumerate(predefined_topics):
            col = cols[idx % 2]
            with col:
                is_selected = st.checkbox(
                    topic,
                    value=(topic in current_topics),
                    key=f"checkbox_{topic}"
                )
                if is_selected:
                    selected_topics.append(topic)
        
        if st.button("Update Topics"):
            topics_to_add = [t for t in selected_topics if t not in current_topics]
            topics_to_remove = [t for t in current_topics if t not in selected_topics]
            
            for topic in topics_to_add:
                add_topic(volunteer_id, topic)
            
            for topic in topics_to_remove:
                remove_topics(volunteer_id, [topic])
            
            if topics_to_add or topics_to_remove:
                st.success("✅ Topics updated!")
                st.rerun()
            else:
                st.info("No changes made")
        
        st.write("---")
        
        # Add custom topics
        st.write("**Add Custom Topic:**")
        col1, col2 = st.columns([3, 1])
        with col1:
            custom_topic = st.text_input("Enter a new topic", placeholder="e.g., React, Python, Mobile Dev")
        with col2:
            if st.button("Add"):
                if custom_topic.strip():
                    if custom_topic not in current_topics:
                        add_topic(volunteer_id, custom_topic)
                        st.success("✅ Added!")
                        st.rerun()
                    else:
                        st.warning("Already in your topics")
                else:
                    st.error("Enter topic")
        
        # Show current topics
        st.write("---")
        st.write("**Your Topics:**")
        current_topics = vol_profile.get("topics", [])
        if current_topics:
            topics_display = " • ".join([f"🏷️ {t}" for t in current_topics])
            st.write(topics_display)
        else:
            st.info("No topics selected yet. Add some to get started!")
        
        st.write("---")
        st.subheader("📅 Available Time Slots")
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                start_time = st.time_input(f"{day} Start", key=f"{day}_start")
            with col2:
                end_time = st.time_input(f"{day} End", key=f"{day}_end")
            with col3:
                if st.button(f"Save {day}", key=f"save_{day}"):
                    set_availability(volunteer_id, day, str(start_time), str(end_time))
                    st.success(f"✅ {day} saved!")
    
    # ---- TAB 2: My Students ----
    with tab2:
        st.subheader("👥 Students Assigned to You")
        
        students = get_assigned_students(volunteer_id)
        
        if not students:
            st.info("No students assigned yet. Check back soon!")
        else:
            for student in students:
                with st.expander(f"👤 {student.get('email', 'Unknown')}"):
                    weak_topics = student.get("weak_topics", [])
                    history_count = len(student.get("history", []))
                    
                    st.write(f"**Weak Topics**: {', '.join(weak_topics) if weak_topics else 'Not specified'}")
                    st.write(f"**Messages**: {history_count}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Schedule Session", key=f"schedule_{student['id']}"):
                            st.success("📅 Session scheduling coming soon!")
                    with col2:
                        if st.button("View History", key=f"history_{student['id']}"):
                            recent = student.get("history", [])[-3:]
                            if recent:
                                st.write("**Recent Messages:**")
                                for msg in recent:
                                    st.write(f"- {msg.get('message', '')[:100]}")
    
    # ---- TAB 3: Sessions ----
    with tab3:
        st.subheader("📋 Scheduled Sessions")
        
        sessions = get_scheduled_sessions(volunteer_id)
        
        if not sessions:
            st.info("No scheduled sessions. Your calendar is clear!")
        else:
            for session in sessions:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write(f"**Student**: {session.get('student_id')}")
                with col2:
                    st.write(f"**Topic**: {session.get('topic')}")
                with col3:
                    st.write(f"**Time**: {session.get('scheduled_time')}")
                with col4:
                    if st.button("Complete", key=f"complete_{session['id']}"):
                        complete_session(session['id'], duration=60, notes="Session completed")
                        st.success("✅ Session marked as complete!")
                        st.rerun()
                
                st.divider()
    
    # ---- TAB 4: Statistics ----
    with tab4:
        st.subheader("📊 Your Volunteer Statistics")
        
        stats = get_volunteer_stats(volunteer_id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sessions Completed", stats["sessions_completed"])
        with col2:
            st.metric("Total Hours", f"{stats['total_hours']:.1f}h")
        with col3:
            st.metric("Students Helped", stats["students_helped"])
        with col4:
            st.metric("Rating", f"{stats['rating']:.1f} ⭐")
        
        st.write("---")
        st.subheader("🏷️ Your Topics")
        topics_text = ", ".join(stats["topics"]) if stats["topics"] else "No topics added yet"
        st.write(f"**Topics**: {topics_text}")
    
    st.write("---")
    if st.button("Logout", key="volunteer_logout"):
        st.session_state["user"] = None
        st.rerun()


# ============================================
# MAIN FUNCTION
# ============================================
def main():
    user = st.session_state["user"]
    
    if not user:
        # User not logged in - show login page
        show_login()
    else:
        # User is logged in - show appropriate dashboard
        if user.get("role") == "student":
            show_student_dashboard(user)
        else:  # role is "volunteer"
            show_volunteer_dashboard(user)


if __name__ == "__main__":
    main()
