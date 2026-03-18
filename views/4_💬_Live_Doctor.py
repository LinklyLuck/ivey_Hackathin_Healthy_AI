import streamlit as st
import json
import time
from utils.styles import inject_css
from utils.storage import load_patients, load_patient_records, append_row_csv, get_next_id, now_str
from utils.ai_client import call_gpt_chat, gpt_generate_report
from utils.chat_store import create_chat_session, load_chat_session, add_message, update_status, set_ai_summary

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #7C3AED 0%, #A855F7 50%, #C084FC 100%);">
    <h1>💬 Live Doctor Consultation</h1>
    <p>Chat with AI to describe symptoms → AI generates summary → Connect with a real doctor online.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="disclaimer"><strong>⚠️ Important:</strong> AI collects information only — does <strong>not</strong> diagnose. For emergencies, call <strong>911</strong>.</div>', unsafe_allow_html=True)

auth = st.session_state.get("auth", {})

if "ld_phase" not in st.session_state:
    st.session_state.ld_phase = "info"
if "ld_session_id" not in st.session_state:
    st.session_state.ld_session_id = None
if "ld_ai_messages" not in st.session_state:
    st.session_state.ld_ai_messages = []

# ═══════════════════════════════════════════
#  PHASE 1: Patient Info
# ═══════════════════════════════════════════
if st.session_state.ld_phase == "info":
    st.markdown("### Patient Information")
    records = load_patient_records()
    patients = load_patients()
    # Search by OHIP/UHIP
    c_search, c_btn = st.columns([3, 1])
    with c_search:
        search_num = st.text_input("Enter your OHIP / UHIP Number:", placeholder="e.g. 4795352975", key="ld_search")
    with c_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🔍 Search", key="ld_search_btn", use_container_width=True)

    p_name, p_age, p_id, p_history = "", 35, None, ""
    patient_found = False

    if search_num.strip():
        if not patients.empty and "insurance_number" in patients.columns:
            match = patients[patients["insurance_number"].astype(str).str.contains(search_num.strip(), case=False, na=False)]
            if not match.empty:
                r = match.iloc[0]
                p_name, p_age, p_id = r["full_name"], int(r["age"]), r["patient_id"]
                p_history = str(r.get("past_medical_history", ""))
                patient_found = True
                st.markdown(f'<div class="info-panel">✅ <strong>Patient Found:</strong> {p_name} | Age: {p_age} | ID: {p_id}</div>', unsafe_allow_html=True)

        if not patient_found and not records.empty:
            match = records[records["patient_alias_id"].astype(str).str.contains(search_num.strip(), case=False, na=False)]
            if not match.empty:
                r = match.iloc[0]
                p_name, p_age, p_id = r["patient_name"], int(r["age"]), r["record_id"]
                p_history = str(r.get("primary_diagnosis", ""))
                patient_found = True
                st.markdown(f'<div class="info-panel">✅ <strong>Patient Found:</strong> {p_name} | Age: {p_age} | {r["primary_diagnosis"]}</div>', unsafe_allow_html=True)

        if not patient_found:
            st.warning("No patient found. Please register below.")

    if not patient_found:
        st.markdown("**New Patient Registration:**")
        c1, c2 = st.columns(2)
        with c1:
            p_name = st.text_input("Full Name *", key="ld_n")
            from datetime import datetime as dt
            p_dob = st.date_input("Date of Birth *", value=dt(1990,1,1), min_value=dt(1920,1,1), key="ld_dob")
            p_phone = st.text_input("Phone Number *", key="ld_phone")
            p_email = st.text_input("Email", key="ld_email")
            p_address = st.text_input("Address", key="ld_addr")
        with c2:
            p_ins_type = st.selectbox("Insurance Type", ["OHIP", "UHIP", "Other"], key="ld_ins")
            p_ins_num = st.text_input("Insurance Number", key="ld_insn")
            p_allergies = st.text_area("Known Allergies", value="None", height=68, key="ld_allg")
            p_history = st.text_area("Past Medical History", value="None", height=68, key="ld_pmh")
            p_emerg = st.text_input("Emergency Contact (Name & Phone)", key="ld_emerg")
        p_age = (dt.now() - dt.combine(p_dob, dt.min.time())).days // 365 if p_dob else 35

    if st.button("▶ Start Consultation", type="primary"):
        if not p_name:
            st.error("Please enter patient name.")
        else:
            sid = f"CHAT-{auth.get('username','anon')}-{int(time.time())}"
            create_chat_session(sid, p_name, {"age": p_age, "id": p_id, "history": p_history, "user": auth.get("username","")})
            update_status(sid, "ai_collecting")

            # AI sends the first greeting
            greeting = f"Hello {p_name}! I'm the AI medical assistant at Southlake Regional Health Centre. What medical concerns bring you in today? Please describe your symptoms and I'll help gather information for the doctor."
            add_message(sid, "ai", greeting, "AI Assistant")

            st.session_state.ld_session_id = sid
            st.session_state.ld_ai_messages = [{"role": "assistant", "content": greeting}]
            st.session_state.ld_phase = "ai_chat"
            st.session_state.ld_patient_info = {"name": p_name, "age": p_age, "history": p_history}
            st.rerun()

# ═══════════════════════════════════════════
#  PHASE 2: AI Chat (GPT-4o-mini)
# ═══════════════════════════════════════════
if st.session_state.ld_phase == "ai_chat":
    sid = st.session_state.ld_session_id
    info = st.session_state.get("ld_patient_info", {})

    st.markdown(f'<div class="info-panel">🤖 <strong>AI Medical Assistant</strong> — Collecting information for <strong>{info.get("name","")}</strong> (Age {info.get("age","")})</div>', unsafe_allow_html=True)

    AI_SYSTEM = f"""You are a professional medical intake assistant at Southlake Regional Health Centre.
You are currently chatting with {info.get('name','a patient')}, Age: {info.get('age','unknown')}, History: {info.get('history','None')}.

Gather symptom information through friendly, structured conversation. Ask ONE focused question at a time.

YOUR CONVERSATION STYLE:
1. First, ask about the main symptom: location, nature, duration, severity (0-10).
2. Then ask about associated symptoms and what makes it better/worse.
3. Based on what you learn, share brief analysis:
   - "Based on what you've described, this could be related to..." (give 2-3 possible general categories, NOT specific diagnoses)
   - "Here's something you can try to check at home: ..." (suggest simple self-assessment like checking temperature, observing swelling, monitoring pain patterns)
4. Ask about current medications and allergies.
5. After 4-6 exchanges, when you have enough info, say EXACTLY this sentence:
   "Thank you, I now have enough information to prepare a summary for the doctor. Please click the button below to connect with a physician."

RULES:
- Never give a definitive diagnosis. Say "this could be related to" not "you have".
- Self-test suggestions should be safe and simple (e.g. "monitor your temperature", "try gently pressing the area", "note if pain changes with movement").
- Always be empathetic and professional.
- Ask about: main symptom details, duration, severity (0-10), associated symptoms, aggravating/relieving factors, medications, allergies.
"""

    for msg in st.session_state.ld_ai_messages:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Describe your symptoms..."):
        st.session_state.ld_ai_messages.append({"role": "user", "content": prompt})
        add_message(sid, "patient", prompt, info.get("name", ""))

        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("AI is thinking..."):
                reply = call_gpt_chat(AI_SYSTEM, st.session_state.ld_ai_messages)
                if reply is None:
                    reply = "Could you tell me more about your symptoms? How long have they been present, and how would you rate the discomfort from 0-10? (API unavailable — demo mode)"
            st.markdown(reply)

        st.session_state.ld_ai_messages.append({"role": "assistant", "content": reply})
        add_message(sid, "ai", reply, "AI Assistant")
        st.rerun()

    # Transfer button — only after AI says the trigger phrase
    ai_msgs = [m["content"] for m in st.session_state.ld_ai_messages if m["role"] == "assistant"]
    ai_ready = any("enough information to prepare a summary" in msg.lower() for msg in ai_msgs)

    if ai_ready:
        st.markdown("---")
        if st.button("📋 Generate Summary & Connect to Doctor", type="primary", use_container_width=True):
            with st.spinner("🤖 AI generating clinical summary..."):
                transcript = "\n".join([f"{'Patient' if m['role']=='user' else 'AI'}: {m['content']}" for m in st.session_state.ld_ai_messages])
                report_prompt = f"""Summarize this consultation into JSON.
Patient: {info.get('name','')}, Age: {info.get('age','')}, History: {info.get('history','None')}
Transcript:
{transcript}

Output JSON only:
{{"chief_complaint":"...","symptom_summary":"...","pain_level":0,"severity":"Low/Moderate/High","suggested_department":"...","recommended_priority":0,"risk_level":"Green/Yellow/Red","clinical_note":"..."}}"""
                report_text = gpt_generate_report("Output only valid JSON.", report_prompt)

            report = None
            if report_text:
                try:
                    s = report_text.find("{"); e = report_text.rfind("}") + 1
                    if s >= 0: report = json.loads(report_text[s:e])
                except: pass

            if report:
                set_ai_summary(sid, report)
                update_status(sid, "waiting_doctor")
                level = report.get("risk_level", "Yellow")
                append_row_csv("doctor_queue.csv", {
                    "queue_id": get_next_id("Q","doctor_queue.csv","queue_id"), "case_id": sid,
                    "patient_id": info.get("id") or "WALK-IN", "patient_name": info.get("name",""),
                    "age": info.get("age",0), "complaint_summary": report.get("chief_complaint","Live consultation")[:100],
                    "final_priority": report.get("recommended_priority",40), "risk_level": level,
                    "department": report.get("suggested_department","General"), "red_flag": level=="Red",
                    "queue_status": "Waiting", "queued_at": now_str()})

                circle = {"Green":"🟢","Yellow":"🟡","Red":"🔴"}.get(level,"🟡")
                st.markdown(f'<div class="case-card case-card-{level.lower()}"><h3>{circle} AI Summary</h3><p><strong>Complaint:</strong> {report.get("chief_complaint","N/A")}</p><p><strong>Severity:</strong> {report.get("severity","N/A")} | Priority: {report.get("recommended_priority","N/A")}/100</p><p><strong>Dept:</strong> {report.get("suggested_department","N/A")}</p></div>', unsafe_allow_html=True)
                st.success("✅ Summary sent to Doctor Dashboard. Waiting for doctor...")
            else:
                update_status(sid, "waiting_doctor")

            st.session_state.ld_phase = "doctor_chat"
            st.rerun()

# ═══════════════════════════════════════════
#  PHASE 3: Live Doctor Chat
# ═══════════════════════════════════════════
if st.session_state.ld_phase == "doctor_chat":
    sid = st.session_state.ld_session_id
    info = st.session_state.get("ld_patient_info", {})

    st.markdown('<div class="info-panel" style="background:#E8F5E9;border-left-color:#4CAF50;">👨‍⚕️ <strong>Live Doctor Chat</strong> — You are in the queue. A physician will join shortly.</div>', unsafe_allow_html=True)

    data = load_chat_session(sid)
    if data:
        for msg in data["messages"]:
            if msg["role"] == "patient":
                with st.chat_message("user", avatar="🧑"): st.markdown(msg["content"])
            elif msg["role"] == "ai":
                with st.chat_message("assistant", avatar="🤖"): st.markdown(f"*{msg['content']}*")
            elif msg["role"] == "doctor":
                with st.chat_message("assistant", avatar="👨‍⚕️"): st.markdown(f"**Dr.:** {msg['content']}")

        if data.get("status") == "closed":
            st.success("✅ Consultation complete. Thank you!")
            st.session_state.ld_phase = "done"

    if prompt := st.chat_input("Send message to doctor..."):
        add_message(sid, "patient", prompt, info.get("name", "Patient"))
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh Chat", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("✅ End Consultation", use_container_width=True):
            add_message(sid, "patient", "Thank you, doctor. I have no more questions.", info.get("name", "Patient"))
            update_status(sid, "closed")
            st.session_state.ld_phase = "done"
            st.rerun()

if st.session_state.ld_phase == "done":
    st.markdown('<div class="result-card" style="text-align:center;"><h3>✅ Consultation Complete</h3><p>Follow your doctor\'s recommendations.</p></div>', unsafe_allow_html=True)
    if st.button("🔄 Start New Consultation"):
        st.session_state.ld_phase = "info"; st.session_state.ld_ai_messages = []; st.session_state.ld_session_id = None; st.rerun()
