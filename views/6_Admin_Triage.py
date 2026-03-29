import streamlit as st
import pandas as pd
import plotly.express as px
from utils.styles import inject_css, format_risk_column
from utils.storage import load_cases

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #991B1B 0%, #DC2626 100%);">
    <h1> Triage Scenario Validator</h1>
    <p>Validate synthetic cohorts against triage rules — risk distribution, department routing, scoring analytics.</p>
</div>
""", unsafe_allow_html=True)

if st.button(" Refresh Data", key="tri_refresh", use_container_width=False):
    st.rerun()

cases = load_cases()

if cases.empty:
    st.info("No intake cases yet."); st.stop()

red = len(cases[cases["risk_level"] == "Red"])
yellow = len(cases[cases["risk_level"] == "Yellow"])
green = len(cases[cases["risk_level"] == "Green"])
avg_score = cases["total_priority"].mean()
rf = cases["red_flag"].sum() if "red_flag" in cases.columns else 0

st.markdown(f"""
<div class="metric-row">
    <div class="metric-card"><div class="number">{len(cases)}</div><div class="label">Total Cases</div></div>
    <div class="metric-card"><div class="number" style="color:#DC2626">{red}</div><div class="label"> Red</div></div>
    <div class="metric-card"><div class="number" style="color:#EAB308">{yellow}</div><div class="label"> Yellow</div></div>
    <div class="metric-card"><div class="number" style="color:#22C55E">{green}</div><div class="label"> Green</div></div>
    <div class="metric-card"><div class="number">{avg_score:.0f}</div><div class="label">Avg Priority</div></div>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    risk = cases["risk_level"].value_counts().reset_index(); risk.columns = ["Risk", "Count"]
    st.plotly_chart(px.pie(risk, names="Risk", values="Count", color="Risk", color_discrete_map={"Red":"#EF4444","Yellow":"#EAB308","Green":"#22C55E"}, title="Risk Level Distribution"), use_container_width=True)
with c2:
    dept = cases["department"].value_counts().reset_index(); dept.columns = ["Department", "Count"]
    st.plotly_chart(px.bar(dept.sort_values("Count"), x="Count", y="Department", orientation="h", title="Cases by Department", color_discrete_sequence=["#0066CC"]), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    if "pain_score" in cases.columns:
        st.plotly_chart(px.histogram(cases, x="pain_score", nbins=10, title="Pain Score Distribution", color_discrete_sequence=["#EF4444"]), use_container_width=True)
with c4:
    if "total_priority" in cases.columns:
        st.plotly_chart(px.histogram(cases, x="total_priority", nbins=15, title="Priority Score Distribution", color_discrete_sequence=["#7C3AED"]), use_container_width=True)

if "symptom_category" in cases.columns:
    cat = cases["symptom_category"].value_counts().reset_index(); cat.columns = ["Category", "Count"]
    st.plotly_chart(px.bar(cat.sort_values("Count"), x="Count", y="Category", orientation="h", title="Symptom Categories", color_discrete_sequence=["#059669"]), use_container_width=True)

st.markdown("---")
c_t, c_r = st.columns([3,1])
with c_t: st.markdown("###  All Intake Cases")
with c_r:
    if st.button(" Refresh", key="tri_refresh2", use_container_width=True): st.rerun()
display = format_risk_column(cases)
# Remove red_flag column
drop_cols = [c for c in ["red_flag"] if c in display.columns]
if drop_cols:
    display = display.drop(columns=drop_cols)
st.dataframe(display, use_container_width=True, hide_index=True)

# Follow Up buttons
st.markdown("###  Create Follow-Up Case")
if not cases.empty:
    case_opts = [f"{r['case_id']} — {r.get('patient_name', r.get('patient_id',''))} | {r.get('risk_level','')}" for _, r in cases.iterrows() if r.get("case_id","")]
    if case_opts:
        sel_case = st.selectbox("Select case for follow-up:", case_opts, key="triage_fu_sel")
        if st.button(" Create Follow-Up for This Case", type="primary", key="triage_fu_btn"):
            cid = sel_case.split(" — ")[0].strip()
            c_row = cases[cases["case_id"] == cid]
            if not c_row.empty:
                r = c_row.iloc[0]
                # Create discharge summary entry
                from utils.storage import append_row_csv, now_str
                new_case_id = cid
                # Check if already exists in discharge_summaries
                from utils.storage import load_discharge_summaries
                ds = load_discharge_summaries()
                if not ds.empty and new_case_id in ds["case_id"].values:
                    st.info(f"Follow-up case **{new_case_id}** already exists in discharge summaries.")
                else:
                    append_row_csv("discharge_summaries.csv", {
                        "case_id": new_case_id,
                        "patient_id": r.get("patient_id", "UNKNOWN"),
                        "diagnosis_summary": r.get("chief_complaint", "See triage notes"),
                        "medications": "As prescribed — see clinical notes",
                        "discharge_instructions": f"Follow-up required. Risk: {r.get('risk_level','')}. Dept: {r.get('department','')}. Priority: {r.get('total_priority','')}/100.",
                        "attending_service": r.get("department", "General"),
                        "discharge_date": now_str()[:10],
                    })
                    st.success(f" Follow-up case **{new_case_id}** created! Patient can now access it in Follow-Up using this case number.")
                    st.markdown(f'<div style="background:#FEF3C7;border:2px solid #F59E0B;padding:1rem;border-radius:8px;text-align:center;margin:0.5rem 0;"><span style="font-size:1.5rem;font-weight:700;color:#B45309;"> CASE NUMBER: {new_case_id}</span><br><span style="color:#92400E;">Please make sure the patient remembers this number for their follow-up.</span></div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="case-card">
                        <h3> {new_case_id}</h3>
                        <p><strong>Diagnosis:</strong> {r.get('chief_complaint', 'See triage notes')}</p>
                        <p><strong>Department:</strong> {r.get('department', 'General')}</p>
                        <p><strong>Instructions:</strong> Follow-up required. Risk: {r.get('risk_level','')}. Priority: {r.get('total_priority','')}/100.</p>
                    </div>
                    """, unsafe_allow_html=True)
