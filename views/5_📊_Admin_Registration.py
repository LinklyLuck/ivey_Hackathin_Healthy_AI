import streamlit as st
import pandas as pd
import plotly.express as px
from utils.styles import inject_css
from utils.storage import load_patients, load_patient_records

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #1E3A5F 0%, #1E40AF 100%);">
    <h1>📊 Registration Simulation</h1>
    <p>Synthetic intake schema validation — demographics, insurance, and patient profile analytics.</p>
</div>
""", unsafe_allow_html=True)

patients = load_patients()
records = load_patient_records()

# ─── Metrics ───
total_reg = len(patients) if not patients.empty else 0
total_db = len(records) if not records.empty else 0
st.markdown(f"""
<div class="metric-row">
    <div class="metric-card"><div class="number">{total_reg}</div><div class="label">Registered (Portal)</div></div>
    <div class="metric-card"><div class="number" style="color:#0052A5">{total_db:,}</div><div class="label">Patient Records (DB)</div></div>
    <div class="metric-card"><div class="number">{records['insurance_plan'].value_counts().to_dict().get('OHIP',0) if not records.empty else 0}</div><div class="label">OHIP Patients</div></div>
    <div class="metric-card"><div class="number">{records['insurance_plan'].value_counts().to_dict().get('UHIP',0) + records['insurance_plan'].value_counts().to_dict().get('IFH',0) if not records.empty else 0}</div><div class="label">UHIP / IFH</div></div>
</div>
""", unsafe_allow_html=True)

# ─── Analytics ───
if not records.empty:
    c1, c2 = st.columns(2)
    with c1:
        ins = records["insurance_plan"].value_counts().reset_index(); ins.columns = ["Plan", "Count"]
        st.plotly_chart(px.pie(ins, names="Plan", values="Count", title="Insurance Distribution (n=3,000)"), use_container_width=True)
    with c2:
        age_bins = pd.cut(records["age"], bins=[0,18,40,65,80,120], labels=["0-17","18-39","40-64","65-79","80+"])
        age_dist = age_bins.value_counts().sort_index().reset_index(); age_dist.columns = ["Age Group", "Count"]
        st.plotly_chart(px.bar(age_dist, x="Age Group", y="Count", title="Age Group Distribution", color_discrete_sequence=["#0066CC"]), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        city = records["city"].value_counts().reset_index(); city.columns = ["City", "Count"]
        st.plotly_chart(px.bar(city.sort_values("Count"), x="Count", y="City", orientation="h", title="Patients by City", color_discrete_sequence=["#7C3AED"]), use_container_width=True)
    with c4:
        gender = records["gender"].value_counts().reset_index(); gender.columns = ["Gender", "Count"]
        st.plotly_chart(px.pie(gender, names="Gender", values="Count", title="Gender Distribution"), use_container_width=True)

# ─── Portal Registered Patients Table ───
st.markdown("---")
st.markdown("### 📁 Portal Registered Patients")
if not patients.empty:
    st.dataframe(patients, use_container_width=True, hide_index=True)
else:
    st.info("No patients registered via portal yet.")

# ─── Full DB Explorer ───
with st.expander("🔎 Full Patient Records (3,000)"):
    if not records.empty:
        c1, c2 = st.columns(2)
        with c1: hf = st.selectbox("Hospital", ["All"] + sorted(records["anchor_hospital"].unique().tolist()), key="adm_h")
        with c2: sf = st.selectbox("Status", ["All"] + sorted(records["care_status"].unique().tolist()), key="adm_s")
        f = records.copy()
        if hf != "All": f = f[f["anchor_hospital"] == hf]
        if sf != "All": f = f[f["care_status"] == sf]
        st.dataframe(f, use_container_width=True, hide_index=True, height=400)
        st.caption(f"{len(f):,} records")
