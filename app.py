import streamlit as st
from utils.styles import inject_css
from utils.auth import authenticate

st.set_page_config(page_title="Southlake Agentic Synthetic Data Factory", page_icon="", layout="wide")

# ─── Init auth ───
if "auth" not in st.session_state:
    st.session_state.auth = None


def login_page():
    """Login screen."""
    inject_css()
    st.markdown("""
    <div class="hero-card" style="text-align:center;">
        <h1> Southlake Agentic Synthetic Data Factory</h1>
        <p>An agentic synthetic data creation and validation service for healthcare<br>
        <strong>Southlake Health × Ivey Hackathon 2026</strong><br>By Qi Sun &amp; Jia An · Advisor: Kaiyu Li</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        st.markdown("""
        <div class="result-card" style="text-align:center;">
            <h3> Sign In</h3>
            <p style="color:#64748B;">Enter your credentials to access the platform.</p>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="user1 / admin")
        password = st.text_input("Password", type="password", placeholder="Enter password")

        if st.button("Sign In", type="primary", use_container_width=True):
            result = authenticate(username, password)
            if result:
                st.session_state.auth = result
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.markdown("""
        <div style="margin-top:1.5rem; padding:1rem; background:#F0F7FF; border-radius:8px; font-size:0.85rem; color:#475569;">
            <strong>Demo Accounts:</strong><br>
             Patient: <code>user1</code> / <code>user2</code> / <code>user3</code> — Password: <code>123456</code><br>
             Admin: <code>admin</code> — Password: <code>admin</code><br>
             Synthetic Data Admin: <code>admin123</code> — Password: <code>admin123</code>
        </div>
        """, unsafe_allow_html=True)


def home_patient():
    """Patient home/dashboard."""
    inject_css()
    auth = st.session_state.auth
    st.markdown("""
    <div class="hero-card">
        <h1> Synthetic Patient Journey Simulator</h1>
        <p>Downstream simulation modules — validate generated cohorts against intake, triage, follow-up, and consultation workflows.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="info-panel"> Logged in as <strong>{auth["display"]}</strong></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="result-card"><h3> AI Registration</h3><p>Complete intake with AI-assisted form filling.</p></div>', unsafe_allow_html=True)
        if st.button(" Go to Registration", use_container_width=True, key="nav_reg"):
            st.switch_page("views/1__Registration.py")
        st.markdown('<div class="result-card"><h3> Emergency Pre-Triage</h3><p>AI analyzes symptoms, scores urgency, routes to department.</p></div>', unsafe_allow_html=True)
        if st.button(" Go to PreTriage", use_container_width=True, key="nav_tri"):
            st.switch_page("views/2__PreTriage.py")
    with c2:
        st.markdown('<div class="result-card"><h3> Smart Follow-Up</h3><p>Post-discharge check-in with risk assessment.</p></div>', unsafe_allow_html=True)
        if st.button(" Go to FollowUp", use_container_width=True, key="nav_fu"):
            st.switch_page("views/3__FollowUp.py")
        st.markdown('<div class="result-card" style="border-left:4px solid #7C3AED;"><h3> Live Doctor</h3><p>Chat with AI then connect with a real doctor online.</p></div>', unsafe_allow_html=True)
        if st.button(" Go to Live Doctor", use_container_width=True, key="nav_ld"):
            st.switch_page("views/4__Live_Doctor.py")

    st.markdown('<div class="disclaimer"><strong></strong> Prototype demo. Not a diagnostic system. Synthetic data only.</div>', unsafe_allow_html=True)


def home_admin():
    """Admin home/dashboard."""
    inject_css()
    from utils.storage import load_patient_records, load_cases, load_doctor_queue, load_followup_results

    records = load_patient_records()
    cases = load_cases()
    queue = load_doctor_queue()
    followups = load_followup_results()

    st.markdown("""
    <div class="hero-card" style="background: linear-gradient(135deg, #1E3A5F 0%, #1E40AF 100%);">
        <h1> Simulation & Validation Workspace</h1>
        <p>Downstream validation modules — test synthetic cohorts against hospital workflows, triage rules, and operational scenarios.</p>
    </div>
    """, unsafe_allow_html=True)

    total = len(records) if not records.empty else 0
    n_cases = len(cases) if not cases.empty else 0
    n_queue = len(queue[queue["queue_status"] == "Waiting"]) if not queue.empty and "queue_status" in queue.columns else 0
    n_fu = len(followups[followups["clinician_review_status"] == "Pending"]) if not followups.empty and "clinician_review_status" in followups.columns else 0

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card"><div class="number">{total:,}</div><div class="label">Seed Records</div></div>
        <div class="metric-card"><div class="number">{n_cases}</div><div class="label">Simulated Cases</div></div>
        <div class="metric-card"><div class="number" style="color:#DC2626">{n_queue}</div><div class="label">Queue Load</div></div>
        <div class="metric-card"><div class="number" style="color:#EAB308">{n_fu}</div><div class="label">Follow-Up Tests</div></div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button(" Registration Simulation", use_container_width=True, key="nav_reg"):
            st.switch_page("views/5__Admin_Registration.py")
        if st.button(" Triage Scenario Validator", use_container_width=True, key="nav_tri"):
            st.switch_page("views/6__Admin_Triage.py")
    with c2:
        if st.button(" Follow-Up Simulation", use_container_width=True, key="nav_fu"):
            st.switch_page("views/7__Admin_FollowUp.py")
        if st.button(" Queue Stress Test", use_container_width=True, key="nav_q"):
            st.switch_page("views/8__Doctor_Dashboard.py")

    if st.button(" Operations Validation", use_container_width=True, key="nav_ops"):
        st.switch_page("views/9__Admin_Operations.py")
    st.markdown('<div class="disclaimer"><strong></strong> Prototype demo. All data is synthetic. Simulation modules validate downstream utility of generated cohorts.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
#  NAVIGATION ROUTER
# ═══════════════════════════════════════════

if st.session_state.auth is None:
    # Not logged in — show login only
    pg = st.navigation([st.Page(login_page, title="Login", icon="")])
    pg.run()

elif st.session_state.auth["role"] == "patient":
    # Patient: 4 functional pages + home
    pg = st.navigation({
        "Patient Simulation": [
            st.Page(home_patient, title="Home", icon=""),
            st.Page("views/1__Registration.py", title="Registration", icon=""),
            st.Page("views/2__PreTriage.py", title="PreTriage", icon=""),
            st.Page("views/3__FollowUp.py", title="FollowUp", icon=""),
            st.Page("views/4__Live_Doctor.py", title="Live Doctor", icon=""),
        ],
    })

    # Sidebar logout
    with st.sidebar:
        st.markdown(f"<div style='font-size:0.8rem;color:#64748B;padding:0.5rem;'> {st.session_state.auth['display']}</div>", unsafe_allow_html=True)
        if st.button(" Logout", use_container_width=True, key="logout_p"):
            st.session_state.auth = None
            st.rerun()

    pg.run()

else:
    # Admin or Superadmin
    admin_pages = [
        st.Page("views/5__Admin_Registration.py", title="Registration Simulation", icon=""),
        st.Page("views/6__Admin_Triage.py", title="Triage Validator", icon=""),
        st.Page("views/7__Admin_FollowUp.py", title="Follow-Up Simulation", icon=""),
        st.Page("views/8__Doctor_Dashboard.py", title="Queue Stress Test", icon=""),
        st.Page("views/9__Admin_Operations.py", title="Operations Validation", icon=""),
    ]
    
    if st.session_state.auth["role"] == "superadmin":
        pg = st.navigation({
            " Synthetic Data Lab": [
                st.Page("views/10__Synthetic_Data_Agent.py", title="Synthetic Data Agent", icon="", default=True),
            ],
        })
    else:
        pg = st.navigation({"Simulation & Validation": [st.Page(home_admin, title="Home", icon="")] + admin_pages})

    with st.sidebar:
        icon = "" if st.session_state.auth["role"] == "superadmin" else ""
        st.markdown(f"<div style='font-size:0.8rem;color:#64748B;padding:0.5rem;'>{icon} {st.session_state.auth['display']}</div>", unsafe_allow_html=True)
        if st.button(" Logout", use_container_width=True, key="logout_a"):
            st.session_state.auth = None
            st.rerun()

    pg.run()
