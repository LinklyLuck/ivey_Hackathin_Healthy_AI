import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.styles import inject_css, format_risk_column
from utils.storage import load_doctor_queue, load_cases, load_patients, load_patient_records
from utils.chat_store import list_active_sessions, load_chat_session, add_message, update_status
from utils.auth import require_login

inject_css()
auth = require_login(st)

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);">
    <h1>👨‍⚕️ Clinical Queue Stress Test</h1>
    <p>Validate synthetic cohort queue pressure, priority distribution, and case routing under simulated load.</p>
</div>
""", unsafe_allow_html=True)

queue = load_doctor_queue()
cases = load_cases()
patients = load_patients()
records = load_patient_records()
southlake = records[records["anchor_hospital"] == "Southlake Regional Health Centre"] if not records.empty else pd.DataFrame()

# ═══════════════════════════════════════════
#  TABS: Queue | Live Chat | Analytics
# ═══════════════════════════════════════════
tab_queue, tab_chat, tab_analytics = st.tabs(["📋 Patient Queue", "💬 Live Chat", "📈 Analytics"])

# ─── TAB 1: Queue ───
with tab_queue:
    if queue.empty:
        st.info("No cases in queue.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: df_ = st.selectbox("Dept", ["All"] + sorted(queue["department"].unique().tolist()), key="dq_d")
        with c2: rf_ = st.selectbox("Risk", ["All", "Red", "Yellow", "Green"], key="dq_r")
        with c3: sf_ = st.selectbox("Status", ["All"] + sorted(queue["queue_status"].unique().tolist()), key="dq_s")

        f = queue.copy()
        if df_ != "All": f = f[f["department"] == df_]
        if rf_ != "All": f = f[f["risk_level"] == rf_]
        if sf_ != "All": f = f[f["queue_status"] == sf_]
        f = f.sort_values("final_priority", ascending=False)

        red=len(f[f["risk_level"]=="Red"]); yellow=len(f[f["risk_level"]=="Yellow"]); green=len(f[f["risk_level"]=="Green"])
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card"><div class="number">{len(f)}</div><div class="label">Total</div></div>
            <div class="metric-card"><div class="number" style="color:#DC2626">{red}</div><div class="label">🔴 Red</div></div>
            <div class="metric-card"><div class="number" style="color:#EAB308">{yellow}</div><div class="label">🟡 Yellow</div></div>
            <div class="metric-card"><div class="number" style="color:#22C55E">{green}</div><div class="label">🟢 Green</div></div>
        </div>
        """, unsafe_allow_html=True)

        dcols = ["queue_id","patient_name","age","complaint_summary","final_priority","risk_level","department","queue_status"]
        avail = [c for c in dcols if c in f.columns]
        st.dataframe(format_risk_column(f[avail]), use_container_width=True, hide_index=True,
            column_config={"final_priority": st.column_config.ProgressColumn("Priority", min_value=0, max_value=100, format="%d")})

        # Case detail
        st.markdown("### 🔍 Case Detail")
        names = f["patient_name"].tolist()
        if names:
            sel = st.selectbox("Select patient:", names, key="dq_sel")
            s = f[f["patient_name"]==sel].iloc[0]
            level = s["risk_level"]
            circle = {"Green":"🟢","Yellow":"🟡","Red":"🔴"}.get(level,"⚪")
            c1, c2 = st.columns([2,1])
            with c1:
                st.markdown(f'<div class="case-card case-card-{level.lower()}"><div style="display:flex;justify-content:space-between;"><h3 style="margin:0">{s["patient_name"]}</h3><span class="badge badge-{level.lower()}">{circle} {level}</span></div><hr style="border-color:#E2E8F0;"><p><strong>Case:</strong> {s["case_id"]} | <strong>Age:</strong> {s["age"]} | <strong>Dept:</strong> {s["department"]}</p><p><strong>Complaint:</strong> {s["complaint_summary"]}</p><p><strong>Priority:</strong> {s["final_priority"]}/100</p></div>', unsafe_allow_html=True)
                if st.button(f"📋 Start Chart for {s['patient_name']}", type="primary", key=f"chart_{sel}"):
                    st.success(f"Chart started for {s['patient_name']} — Case {s['case_id']}. Ready for clinical documentation.")
            with c2:
                fig = go.Figure(go.Indicator(mode="gauge+number", value=s["final_priority"], title={"text":"Priority"},
                    gauge={"axis":{"range":[0,100]},"bar":{"color":"#0066CC"},"steps":[{"range":[0,30],"color":"#DCFCE7"},{"range":[30,60],"color":"#FEF9C3"},{"range":[60,100],"color":"#FEE2E2"}]}))
                fig.update_layout(height=220, margin=dict(t=40,b=0,l=20,r=20))
                st.plotly_chart(fig, use_container_width=True)

# ─── TAB 2: Live Chat ───
with tab_chat:
    st.markdown("### 💬 Patient Consultations")

    sessions = list_active_sessions()

    if not sessions:
        st.info("No active consultations. Patients can start a consultation from the Live Doctor page.")
    else:
        # Session list
        status_icons = {"ai_collecting": "🤖", "waiting_doctor": "⏳", "active": "💬", "closed": "✅"}
        session_labels = []
        session_map = {}
        for s in sessions:
            icon = status_icons.get(s["status"], "❓")
            label = f"{icon} {s['patient_name']} — {s['status']} ({s['message_count']} msgs)"
            session_labels.append(label)
            session_map[label] = s["session_id"]

        selected_label = st.selectbox("Select a consultation:", session_labels)
        selected_sid = session_map[selected_label]
        data = load_chat_session(selected_sid)

        if data:
            # Session info
            status = data["status"]
            info = data.get("patient_info", {})

            st.markdown(f"""
            <div class="info-panel">
                👤 <strong>{data['patient_name']}</strong> | Age: {info.get('age','N/A')} |
                History: {info.get('history','None')} | Status: <strong>{status}</strong>
            </div>
            """, unsafe_allow_html=True)

            # AI Summary as structured table
            if data.get("ai_summary"):
                summary = data["ai_summary"]
                level = summary.get("risk_level", "Yellow")
                circle = {"Green":"🟢","Yellow":"🟡","Red":"🔴"}.get(level,"🟡")
                st.markdown(f"#### {circle} AI Clinical Summary")
                summary_df = pd.DataFrame([
                    {"Field": "Chief Complaint", "Value": summary.get("chief_complaint", "N/A")},
                    {"Field": "Symptom Summary", "Value": summary.get("symptom_summary", "N/A")},
                    {"Field": "Pain Level", "Value": str(summary.get("pain_level", "N/A"))},
                    {"Field": "Severity", "Value": summary.get("severity", "N/A")},
                    {"Field": "Risk Level", "Value": f"{circle} {level}"},
                    {"Field": "Priority Score", "Value": f"{summary.get('recommended_priority', 'N/A')}/100"},
                    {"Field": "Suggested Department", "Value": summary.get("suggested_department", "N/A")},
                    {"Field": "Clinical Note", "Value": summary.get("clinical_note", "N/A")},
                ])
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

            # Chat messages
            st.markdown("#### Chat History")
            for msg in data["messages"]:
                if msg["role"] == "patient":
                    with st.chat_message("user", avatar="🧑"):
                        st.markdown(f"**{msg.get('sender','Patient')}** ({msg.get('time','')}): {msg['content']}")
                elif msg["role"] == "ai":
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(f"*AI ({msg.get('time','')}): {msg['content']}*")
                elif msg["role"] == "doctor":
                    with st.chat_message("assistant", avatar="👨‍⚕️"):
                        st.markdown(f"**Dr. ({msg.get('time','')}):** {msg['content']}")

            # Doctor reply input
            if status in ("waiting_doctor", "active"):
                if status == "waiting_doctor":
                    if st.button("✅ Accept & Start Chat", type="primary"):
                        update_status(selected_sid, "active")
                        add_message(selected_sid, "doctor", f"Hello {data['patient_name']}, please wait a moment — let me review the AI-collected information about your visit.", "Doctor")
                        st.rerun()
                else:
                    doctor_msg = st.chat_input("Type your message to the patient...", key="doc_chat_input")
                    if doctor_msg:
                        add_message(selected_sid, "doctor", doctor_msg, "Doctor")
                        st.rerun()

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🔄 Refresh", use_container_width=True):
                            st.rerun()
                    with c2:
                        if st.button("💾 Save Case Record", use_container_width=True):
                            from utils.storage import append_row_csv, get_next_id, now_str
                            case_data = data.get("ai_summary", {})
                            append_row_csv("cases.csv", {
                                "case_id": f"LIVE-{selected_sid[-6:]}", "patient_id": info.get("id","WALK-IN"),
                                "chief_complaint": case_data.get("chief_complaint","Live consultation"),
                                "symptom_category": "live_doctor", "pain_score": case_data.get("pain_level",0)*2,
                                "age_risk": 0, "ai_severity": 0, "red_flag": case_data.get("risk_level")=="Red",
                                "total_priority": case_data.get("recommended_priority",40),
                                "risk_level": case_data.get("risk_level","Yellow"),
                                "department": case_data.get("suggested_department","General"),
                                "structured_answers": "live_doctor_session", "timestamp": now_str(), "status": "completed"
                            })
                            st.success("✅ Case record saved to cases.csv")

            elif status == "closed":
                st.success("✅ This consultation has been closed by the patient.")
                if st.button("💾 Save Case Record", key="save_closed", use_container_width=True):
                    from utils.storage import append_row_csv, now_str
                    case_data = data.get("ai_summary", {})
                    append_row_csv("cases.csv", {
                        "case_id": f"LIVE-{selected_sid[-6:]}", "patient_id": info.get("id","WALK-IN"),
                        "chief_complaint": case_data.get("chief_complaint","Live consultation"),
                        "symptom_category": "live_doctor", "pain_score": case_data.get("pain_level",0)*2,
                        "age_risk": 0, "ai_severity": 0, "red_flag": case_data.get("risk_level")=="Red",
                        "total_priority": case_data.get("recommended_priority",40),
                        "risk_level": case_data.get("risk_level","Yellow"),
                        "department": case_data.get("suggested_department","General"),
                        "structured_answers": "live_doctor_session", "timestamp": now_str(), "status": "completed"
                    })
                    st.success("✅ Case record saved.")

# ─── TAB 3: Analytics ───
with tab_analytics:
    if not queue.empty:
        c1, c2 = st.columns(2)
        with c1:
            r = queue["risk_level"].value_counts().reset_index(); r.columns = ["Risk","Count"]
            st.plotly_chart(px.pie(r, names="Risk", values="Count", color="Risk", color_discrete_map={"Red":"#EF4444","Yellow":"#EAB308","Green":"#22C55E"}, title="Risk Distribution"), use_container_width=True)
        with c2:
            d = queue["department"].value_counts().reset_index(); d.columns = ["Dept","Cases"]
            st.plotly_chart(px.bar(d, x="Cases", y="Dept", orientation="h", title="By Department", color_discrete_sequence=["#0066CC"]), use_container_width=True)

    if not southlake.empty:
        st.markdown("### 🔴 Escalated Patients (DB)")
        esc = southlake[southlake["care_status"]=="Escalated"].sort_values("age", ascending=False)
        st.dataframe(esc[["record_id","patient_name","age","department","primary_diagnosis","medication_plan","attending_physician","care_status"]].head(30), use_container_width=True, hide_index=True)
