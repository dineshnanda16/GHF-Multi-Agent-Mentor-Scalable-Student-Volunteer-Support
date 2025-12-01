# streamlit_app.py
import streamlit as st

from auth import get_user_by_email, create_user, check_password
from student_agent_firestore import student_agent

st.set_page_config(page_title="GHF Mentor", page_icon="📚")

if "user" not in st.session_state:
    st.session_state["user"] = None


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


def show_student_dashboard(user):
    st.title("GHF Student Mentor")
    st.write(f"Logged in as: **{user['email']}** (role: {user.get('role', 'student')})")

    message = st.text_area("Your question or message")
    if st.button("Ask Mentor"):
        if not message.strip():
            st.warning("Please type something.")
        else:
            reply = student_agent(user_id=user["id"], message=message)
            st.markdown("**Mentor reply:**")
            st.write(reply)

    if st.button("Logout"):
        st.session_state["user"] = None
        st.rerun()


def main():
    st.write("DEBUG: main running")  # temporary debug line
    user = st.session_state["user"]
    if not user:
        show_login()
    else:
        if user.get("role", "student") == "student":
            show_student_dashboard(user)
        else:
            st.title("Volunteer dashboard (coming soon)")
            st.write(f"Logged in as: **{user['email']}** (role: {user.get('role')})")
            if st.button("Logout"):
                st.session_state["user"] = None
                st.rerun()


if __name__ == "__main__":
    main()
