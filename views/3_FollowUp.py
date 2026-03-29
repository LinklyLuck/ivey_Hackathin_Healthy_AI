import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.styles import inject_css, risk_banner, risk_circle
from utils.storage import load_cases, load_discharge_summaries, load_followup_results, append_row_csv, get_next_id, now_str
from utils.ai_client import ai_analyze_followup_risk
from core.followup import classify_followup
from core.transport import recommend_transport
from utils.constants import TRANSPORT_NODES, SOUTHLAKE_HOSPITAL

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #065F46 0%, #059669 50%, #10B981 100%);">
    <h1> Smart Follow-Up</h1>
    <p>Enter your case number to complete your post-discharge follow-up questionnaire.</p>
</div>
""", unsafe_allow_html=True)

discharge = load_discharge_summaries()
cases = load_cases()

# ─── Step 1: Enter Case Number ───
st.markdown("### Enter Your Case Number")
case_id = st.text_input("Case Number", placeholder="e.g. CASE001, CASE002, CASE004...", key="fu_case_input")

if not case_id.strip():
    st.info("Please enter your case number to access your follow-up questionnaire.")
    st.stop()

# Look up case
case_id = case_id.strip().upper()
dis_row = None
if not discharge.empty:
    match = discharge[discharge["case_id"] == case_id]
    if not match.empty:
        dis_row = match.iloc[0]

if dis_row is None:
    st.error(f"Case **{case_id}** not found. Please check your case number and try again.")
    st.markdown("""
    <div class="info-panel">
         <strong>Available demo cases:</strong> CASE001, CASE002, CASE004, CASE006, CASE008, CASE011
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── Show Case Info ───
st.markdown(f"""
<div class="case-card">
    <h3> Your Case: {case_id}</h3>
    <p><strong>Diagnosis:</strong> {dis_row['diagnosis_summary']}</p>
    <p><strong>Medications:</strong> {dis_row['medications']}</p>
    <p><strong>Attending:</strong> {dis_row['attending_service']}</p>
    <p><strong>Discharge Date:</strong> {dis_row['discharge_date']}</p>
</div>
""", unsafe_allow_html=True)

# ─── Step 2: Questionnaire (directly shown) ───
# ─── Check if this case already has a completed follow-up ───
import os, json as _json
from utils.storage import DATA_DIR

fu_results = load_followup_results()
already_completed = False
if not fu_results.empty and "case_id" in fu_results.columns:
    completed = fu_results[fu_results["case_id"] == case_id]
    if not completed.empty:
        already_completed = True
        latest = completed.iloc[-1]
        risk_icon = {"Green":"","Yellow":"","Red":""}.get(str(latest.get("risk_level","")),"")
        st.markdown(f"""
        <div class="case-card case-card-{str(latest.get('risk_level','')).lower()}">
            <h3> Follow-Up Already Completed</h3>
            <p><strong>Submitted:</strong> {latest.get('followup_date','')} | <strong>Risk:</strong> {risk_icon} {latest.get('risk_level','')} | <strong>Score:</strong> {latest.get('risk_score','')}</p>
            <p><strong>Action:</strong> {latest.get('recommended_action','')}</p>
            <p><strong>Status:</strong> {latest.get('clinician_review_status','Pending')}</p>
        </div>
        """, unsafe_allow_html=True)
        st.info("This case has already been submitted. Enter a different case number or contact your care team for a new follow-up.")
        st.stop()

st.markdown("---")
st.markdown("###  Follow-Up Questionnaire")
st.markdown("*Please answer the following questions about your current condition:*")

# ─── Load admin-sent AI questions (only for THIS case, not completed) ───
q_path = os.path.join(DATA_DIR, "followup_questions.json")
admin_questions = []
if os.path.exists(q_path):
    with open(q_path, "r") as f:
        try:
            all_qs = _json.load(f)
            # Try exact match first
            matched_key = None
            if case_id in all_qs:
                matched_key = case_id
            else:
                # Try partial match (CASE001 in PRCL-xxxx or vice versa)
                for key in all_qs:
                    if case_id.lower() in key.lower() or key.lower() in case_id.lower():
                        matched_key = key
                        break
            if matched_key and all_qs[matched_key].get("status") != "completed":
                admin_questions = all_qs[matched_key].get("questions", [])
        except: pass

# ─── Default clinical checklist (always shown) ───
c1, c2 = st.columns(2)
with c1:
    pain_level = st.slider("Current pain/discomfort level (0-10)", 0, 10, 2, key="fp")
    fever = st.checkbox("Fever (≥ 38°C / 100.4°F)", key="ff")
    sob = st.checkbox("Shortness of breath", key="fs")
    bsh = st.checkbox("Blood sugar above target", key="fb")
with c2:
    bpa = st.checkbox("Blood pressure outside normal range", key="fbp")
    o2 = st.checkbox("Oxygen saturation below 94%", key="fo")
    worse = st.checkbox("Condition worse than at discharge", key="fw")
    new_sym = st.checkbox("New symptoms since discharge", key="fn")
    med_nc = st.checkbox("Unable to take medications as prescribed", key="fm")
    wound = st.checkbox("Wound redness, swelling, or discharge", key="fwd")

# ─── AI-generated questions from admin (if sent) ───
admin_answers = {}
if admin_questions:
    st.markdown("---")
    st.markdown("###  Additional Questions from Your Care Team")
    st.markdown(f'<div class="info-panel" style="background:#EBF5FF;border-left-color:#3B82F6;">Your care team has sent <strong>{len(admin_questions)}</strong> personalized questions based on your discharge record. Please answer them below.</div>', unsafe_allow_html=True)
    for i, q in enumerate(admin_questions):
        txt = q.get("text", str(q)) if isinstance(q, dict) else str(q)
        # Skip pain scale questions (already in default)
        if "scale of 0" in txt.lower() and "pain" in txt.lower():
            continue
        st.markdown(f"""<div style="padding:0.5rem 1rem;margin:0.3rem 0;background:#F8FAFC;border-left:3px solid #3B82F6;border-radius:6px;">
            <strong style="color:#2563EB;">Q{i+1}.</strong> {txt}</div>""", unsafe_allow_html=True)
        admin_answers[f"admin_q{i+1}"] = st.text_area("Your answer:", height=68, key=f"aq_{i}", label_visibility="collapsed")
else:
    st.markdown("")
    st.markdown('<div class="info-panel" style="opacity:0.6;">No additional questions from your care team yet. Click <strong>Refresh</strong> to check for updates.</div>', unsafe_allow_html=True)

has_family = st.checkbox("Family member available to assist with transport if needed", key="fam")
notes = st.text_area("Any additional comments or concerns:", height=80, key="fnotes")

# ─── Step 3: Submit & Results ───
c_sub, c_ref = st.columns([1, 1])
with c_sub:
    submit_fu = st.button(" Submit Follow-Up", type="primary", use_container_width=True)
with c_ref:
    if st.button(" Refresh", use_container_width=True):
        st.rerun()

if submit_fu:
    answers = {
        "pain_level": pain_level, "fever": fever, "shortness_of_breath": sob,
        "blood_sugar_high": bsh, "blood_pressure_abnormal": bpa, "oxygen_low": o2,
        "worse_than_before": worse, "new_symptoms": new_sym,
        "medication_noncompliant": med_nc, "wound_issue": wound,
    }

    result = classify_followup(answers)
    level = result["level"]
    transport = recommend_transport(level, has_family, sob and o2)
    circle = {"Green": "", "Yellow": "", "Red": ""}.get(level, "")

    with st.spinner(" AI analyzing your responses..."):
        ai_analysis = ai_analyze_followup_risk(dis_row["diagnosis_summary"], dis_row["discharge_instructions"], {**answers, "notes": notes})

    st.markdown("---")
    st.markdown("###  Your Follow-Up Results")
    st.markdown(risk_banner(level, f"{circle} {risk_circle(level)} — {result['urgency']}"), unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f'<div class="result-card" style="text-align:center;"><h3>Risk Score</h3><div style="font-size:3rem;font-weight:700;color:{"#22C55E" if level=="Green" else "#EAB308" if level=="Yellow" else "#EF4444"}">{result["score"]}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="result-card"><h3>What Happens Next</h3><p>{result["action"]}</p></div>', unsafe_allow_html=True)
        if result["concerns"]:
            for c in result["concerns"]:
                st.markdown(f"-  {c}")

    if ai_analysis:
        st.markdown(f'<div class="case-card case-card-{level.lower()}"><h3> AI Analysis</h3><p>{ai_analysis.get("risk_assessment","N/A")}</p></div>', unsafe_allow_html=True)

    # Transport
    if transport["transport_level"] != "None":
        st.markdown("###  Transport Recommendation")
        st.markdown(f'<div class="result-card"><h3>{transport["icon"]} {transport["transport_level"]}</h3><p>{transport["recommendation"]}</p></div>', unsafe_allow_html=True)

        if transport["nodes"]:
            hosp = SOUTHLAKE_HOSPITAL; nodes = transport["nodes"]
            ll, ln = [], []
            for n in nodes: ll += [hosp["lat"], n["lat"], None]; ln += [hosp["lng"], n["lng"], None]
            fig = go.Figure()
            fig.add_trace(go.Scattermapbox(lat=ll, lon=ln, mode="lines", line=dict(width=2, color="#F97316"), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scattermapbox(lat=[hosp["lat"]]+[n["lat"] for n in nodes], lon=[hosp["lng"]]+[n["lng"] for n in nodes], mode="markers+text", marker=dict(size=[22]+[14]*len(nodes), color=["#DC2626"]+["#EA580C"]*len(nodes)), text=[hosp["name"]]+[n["name"] for n in nodes], textposition="top center", textfont=dict(size=11), hovertext=[" Hospital"]+[f" {n['distance']}" for n in nodes], hoverinfo="text", showlegend=False))
            fig.update_layout(mapbox=dict(style="open-street-map", center=dict(lat=44.03, lon=-79.462), zoom=11.5), margin=dict(l=0, r=0, t=0, b=0), height=400)
            st.plotly_chart(fig, use_container_width=True)

    # Save
    fu_id = get_next_id("FU", "followup_results.csv", "followup_id")
    pid = "UNKNOWN"
    if not cases.empty:
        cm = cases[cases["case_id"] == case_id]
        if not cm.empty: pid = cm.iloc[0]["patient_id"]

    # Build admin Q&A string
    admin_qa_str = ""
    if admin_questions and admin_answers:
        qa_parts = []
        for i, q in enumerate(admin_questions):
            txt = q.get("text", str(q)) if isinstance(q, dict) else str(q)
            ans = admin_answers.get(f"admin_q{i+1}", "")
            if ans: qa_parts.append(f"Q{i+1}: {txt} | A: {ans}")
        admin_qa_str = " || ".join(qa_parts)

    append_row_csv("followup_results.csv", {
        "followup_id": fu_id, "case_id": case_id, "patient_id": pid,
        "questionnaire_answers": ";".join(f"{k}={v}" for k, v in answers.items()),
        "admin_qa": admin_qa_str,
        "patient_notes": notes,
        "risk_score": result["score"], "risk_level": level,
        "transport_level": transport["transport_level"], "recommended_action": result["action"],
        "clinician_review_status": "Pending", "followup_date": now_str()[:10],
    })
    st.success(f"Follow-up **{fu_id}** submitted. Your results have been sent to your care team for review.")

    # Mark questions as completed so they don't show again
    if os.path.exists(q_path):
        try:
            with open(q_path, "r") as f:
                all_qs = _json.load(f)
            # Find the key that matches this case
            for key in list(all_qs.keys()):
                if key == case_id or case_id.lower() in key.lower() or key.lower() in case_id.lower():
                    all_qs[key]["status"] = "completed"
            with open(q_path, "w") as f:
                _json.dump(all_qs, f, indent=2)
        except: pass

    st.markdown('<div class="disclaimer">This assessment will be reviewed by a clinician. Transport recommendations require staff confirmation.</div>', unsafe_allow_html=True)
