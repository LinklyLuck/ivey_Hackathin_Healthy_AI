"""
Southlake — Auth System
"""

USERS = {
    "user1": {"password": "123456", "role": "patient", "display": "Patient - User 1"},
    "user2": {"password": "123456", "role": "patient", "display": "Patient - User 2"},
    "user3": {"password": "123456", "role": "patient", "display": "Patient - User 3"},
    "admin": {"password": "admin", "role": "admin", "display": "Administrator"},
    "admin123": {"password": "admin123", "role": "superadmin", "display": "Synthetic Data Admin"},
}

# Page access control
PATIENT_PAGES = ["Registration", "PreTriage", "FollowUp", "Live Doctor"]
ADMIN_PAGES = ["Admin Registration", "Admin Triage", "Admin FollowUp", "Doctor Dashboard", "Admin Operations"]
SUPERADMIN_PAGES = ["Synthetic Data Agent"]


def authenticate(username: str, password: str) -> dict | None:
    user = USERS.get(username)
    if user and user["password"] == password:
        return {"username": username, "role": user["role"], "display": user["display"]}
    return None


def require_login(st):
    """Check login state, stop page if not logged in."""
    if "auth" not in st.session_state or st.session_state.auth is None:
        st.warning("Please log in from the home page.")
        st.stop()
    return st.session_state.auth


def require_role(st, role: str):
    """Check role, stop if wrong."""
    auth = require_login(st)
    if auth["role"] != role:
        st.error(f"Access denied. This page requires **{role}** access.")
        st.stop()
    return auth
