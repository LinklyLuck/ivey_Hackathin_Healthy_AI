import streamlit as st
import pandas as pd
from utils.styles import inject_css, risk_banner, score_breakdown_html, risk_circle, format_risk_column
from utils.storage import load_patients, load_patient_records, append_row_csv, get_next_id, now_str
from utils.ai_client import ai_generate_triage_questions, ai_generate_clinical_summary, fallback_triage_questions, fallback_department
from core.triage import get_priority_score
from core.routing import suggest_department

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #B91C1C 0%, #DC2626 50%, #EF4444 100%);">
    <h1>🚑 Emergency Pre-Triage</h1>
    <p>AI-guided symptom collection + transparent rule-based scoring + automated department routing.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer">
    <strong>⚠️ This is NOT an emergency service.</strong> If you are experiencing a life-threatening emergency,
    call <strong>911</strong> immediately.
</div>
""", unsafe_allow_html=True)

for key in ["triage_step", "triage_questions", "triage_ai_data"]:
    if key not in st.session_state:
        st.session_state[key] = None
if st.session_state.triage_step is None:
    st.session_state.triage_step = "input"

# ─── Patient lookup by insurance number ───
records = load_patient_records()
patients = load_patients()

st.markdown("### Patient Lookup")
c_search, c_btn = st.columns([3, 1])
with c_search:
    search_num = st.text_input("Enter OHIP / UHIP Number:", placeholder="e.g. 4839-227-651-TH or 4795352975", key="pt_search")
with c_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("🔍 Search", use_container_width=True)

patient_name, age, medical_history, patient_id = "", 35, "None", None
patient_found = False

if search_num.strip():
    q = search_num.strip()

    # Search registered patients: by insurance_number, phone, or name
    if not patients.empty:
        match = pd.DataFrame()
        for col in ["insurance_number", "phone", "full_name"]:
            if col in patients.columns:
                m = patients[patients[col].astype(str).str.contains(q, case=False, na=False)]
                if not m.empty:
                    match = m; break

        if not match.empty:
            r = match.iloc[0]
            patient_name, age, patient_id = r["full_name"], int(r["age"]), r["patient_id"]
            medical_history = str(r.get("past_medical_history", "None"))
            patient_found = True

            st.markdown("#### ✅ Patient Found")
            info_df = pd.DataFrame([
                {"Field": "Full Name", "Value": str(r.get("full_name", ""))},
                {"Field": "Patient ID", "Value": str(r.get("patient_id", ""))},
                {"Field": "Date of Birth", "Value": str(r.get("dob", ""))},
                {"Field": "Age", "Value": str(r.get("age", ""))},
                {"Field": "Phone", "Value": str(r.get("phone", ""))},
                {"Field": "Email", "Value": str(r.get("email", ""))},
                {"Field": "Address", "Value": str(r.get("address", ""))},
                {"Field": "Insurance", "Value": f"{r.get('insurance_type','')} — {r.get('insurance_number','')}"},
                {"Field": "Allergies", "Value": str(r.get("allergies", "None"))},
                {"Field": "Past Medical History", "Value": str(r.get("past_medical_history", "None"))},
                {"Field": "Emergency Contact", "Value": str(r.get("emergency_contact", ""))},
            ])
            st.dataframe(info_df, use_container_width=True, hide_index=True)

    # Search in DB records if not found in registered
    if not patient_found and not records.empty:
        match = pd.DataFrame()
        for col in ["patient_alias_id", "patient_name"]:
            if col in records.columns:
                m = records[records[col].astype(str).str.contains(q, case=False, na=False)]
                if not m.empty:
                    match = m; break

        if not match.empty:
            r = match.iloc[0]
            patient_name, age, patient_id = r["patient_name"], int(r["age"]), r["record_id"]
            medical_history = str(r.get("primary_diagnosis", "None"))
            patient_found = True

            st.markdown("#### ✅ Patient Found (Database)")
            info_df = pd.DataFrame([
                {"Field": "Name", "Value": str(r.get("patient_name", ""))},
                {"Field": "Record ID", "Value": str(r.get("record_id", ""))},
                {"Field": "Age", "Value": str(r.get("age", ""))},
                {"Field": "Gender", "Value": str(r.get("gender", ""))},
                {"Field": "City", "Value": str(r.get("city", ""))},
                {"Field": "Hospital", "Value": str(r.get("anchor_hospital", ""))},
                {"Field": "Department", "Value": str(r.get("department", ""))},
                {"Field": "Primary Diagnosis", "Value": str(r.get("primary_diagnosis", ""))},
                {"Field": "Insurance", "Value": str(r.get("insurance_plan", ""))},
                {"Field": "Care Status", "Value": str(r.get("care_status", ""))},
            ])
            st.dataframe(info_df, use_container_width=True, hide_index=True)

    if not patient_found:
        st.warning("No patient found with this number. Please register first via the **Registration** page.")

# ─── Step 1: Complaint + AI Analysis ───
st.markdown("---")
st.markdown("### Step 1: Describe Your Main Concern")
chief_complaint = st.text_area("What brought you in today?", placeholder="Example: Severe chest tightness when climbing stairs, broke out in cold sweat.", height=100)

if chief_complaint and st.session_state.triage_step == "input":
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("🤖 AI Analysis", type="primary", use_container_width=True):
            with st.spinner("🤖 AI analyzing complaint..."):
                ai_result = ai_generate_triage_questions(chief_complaint, age, medical_history)
            if ai_result and "questions" in ai_result:
                st.session_state.triage_ai_data = ai_result
                st.session_state.triage_questions = ai_result["questions"]
            else:
                st.session_state.triage_questions = fallback_triage_questions(chief_complaint)
                st.session_state.triage_ai_data = {"symptom_category": "general", "suggested_department": fallback_department(chief_complaint), "initial_assessment": "Rule-based assessment — AI unavailable."}
            st.session_state.triage_step = "questions"
            st.rerun()

# ─── Step 2: Symptom Questions ───
if st.session_state.triage_step in ("questions", "result") and st.session_state.triage_questions:
    st.markdown("---")
    st.markdown("### Step 2: AI-Guided Follow-Up Questions")
    ai_data = st.session_state.triage_ai_data or {}
    if ai_data.get("initial_assessment"):
        st.markdown(f'<div class="info-panel">🤖 <strong>AI Assessment:</strong> {ai_data["initial_assessment"]}</div>', unsafe_allow_html=True)
    if ai_data.get("red_flags_detected"):
        st.markdown(f'<div class="safety-banner"><strong>⚠️ Red Flags:</strong> {", ".join(ai_data["red_flags_detected"])}</div>', unsafe_allow_html=True)

    pain_level = st.slider("**Pain Level (0-10)**", 0, 10, 3, key="tp")
    symptom_keys = {
        "unable_to_walk": "Unable to walk or stand", "swelling": "Visible swelling",
        "fever": "Fever (≥ 38°C)", "shortness_of_breath": "Shortness of breath",
        "rest_breathless": "Short of breath at rest", "cannot_lie_flat": "Cannot lie flat",
        "chest_pain": "Chest pain or tightness", "diaphoresis": "Cold sweats",
        "radiation_to_arm": "Pain radiating to arm/jaw/back", "mental_status_change": "Confusion/altered mental status",
        "facial_droop": "Facial droop", "speech_difficulty": "Difficulty speaking",
        "arm_weakness": "Arm or leg weakness", "severe_bleeding": "Uncontrolled bleeding",
        "nausea": "Nausea or vomiting", "rebound_tenderness": "Abdominal tenderness",
        "wound_issue": "Wound redness/swelling/discharge",
    }
    answers = {}
    c1, c2 = st.columns(2)
    items = list(symptom_keys.items())
    with c1:
        for k, v in items[:len(items)//2]: answers[k] = st.checkbox(v, key=f"s_{k}")
    with c2:
        for k, v in items[len(items)//2:]: answers[k] = st.checkbox(v, key=f"s_{k}")

    text_answers = {}
    for q in st.session_state.triage_questions:
        if q.get("type") in ("text", "duration"):
            text_answers[q.get("id", "")] = st.text_input(q["text"], key=f"aq_{q.get('id', hash(q['text']))}")

    c1, c2 = st.columns(2)
    with c1:
        calc = st.button("⚡ Calculate Triage Score & AI Summary", type="primary", use_container_width=True)
    with c2:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.triage_step = "input"; st.session_state.triage_questions = None; st.session_state.triage_ai_data = None; st.rerun()

    if calc:
        triage_result = get_priority_score(age, pain_level, answers)
        department, route_reason = suggest_department(chief_complaint, answers)
        level = triage_result["level"]
        circle = {"Green": "🟢", "Yellow": "🟡", "Red": "🔴"}.get(level, "⚪")

        with st.spinner("🤖 AI generating clinical summary..."):
            summary = ai_generate_clinical_summary(patient_name, age, chief_complaint, {**answers, **text_answers, "pain_level": pain_level}, medical_history)

        st.markdown("---")
        st.markdown("### 📊 Triage Results")
        st.markdown(risk_banner(level, f"{circle} {risk_circle(level)} — {triage_result['band_description']}"), unsafe_allow_html=True)
        st.markdown(score_breakdown_html(triage_result["pain_score"], triage_result["age_risk"], triage_result["ai_severity"], triage_result["total"]), unsafe_allow_html=True)
        if triage_result["explanations"]:
            for exp in triage_result["explanations"]: st.markdown(f"- {exp}")
        st.markdown(f'<div class="result-card"><h3>🏥 Recommended Department: {department}</h3><p><em>{route_reason}</em></p></div>', unsafe_allow_html=True)
        if triage_result["red_flag"]:
            st.markdown('<div class="safety-banner"><strong>🚨 RED FLAG ALERT</strong><br>Critical symptoms detected. Call 911 if acute.</div>', unsafe_allow_html=True)
        if summary:
            st.markdown(f'<div class="case-card case-card-{level.lower()}"><p><strong>Summary:</strong> {summary.get("clinical_summary","N/A")}</p><p><strong>Key Findings:</strong> {", ".join(summary.get("key_findings",[]))}</p><p><strong>Urgency:</strong> {summary.get("recommended_urgency","N/A")}</p><p><strong>Handoff:</strong> {summary.get("handoff_note","N/A")}</p></div>', unsafe_allow_html=True)

        # Save
        case_id = get_next_id("CASE", "cases.csv", "case_id")
        append_row_csv("cases.csv", {"case_id": case_id, "patient_id": patient_id or "NEW", "chief_complaint": chief_complaint, "symptom_category": ai_data.get("symptom_category","general"), "pain_score": triage_result["pain_score"], "age_risk": triage_result["age_risk"], "ai_severity": triage_result["ai_severity"], "red_flag": triage_result["red_flag"], "total_priority": triage_result["total"], "risk_level": level, "department": department, "structured_answers": ";".join(f"{k}=yes" for k,v in answers.items() if v), "timestamp": now_str(), "status": "completed"})
        append_row_csv("doctor_queue.csv", {"queue_id": get_next_id("Q","doctor_queue.csv","queue_id"), "case_id": case_id, "patient_id": patient_id or "NEW", "patient_name": patient_name, "age": age, "complaint_summary": chief_complaint[:100], "final_priority": triage_result["total"], "risk_level": level, "department": department, "red_flag": triage_result["red_flag"], "queue_status": "Waiting", "queued_at": now_str()})
        st.success(f"Case **{case_id}** created and added to doctor queue.")
