import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.styles import inject_css, format_risk_column
from utils.storage import load_followup_results, load_doctor_queue, load_cases, load_patients, load_patient_records
from utils.constants import TRANSPORT_NODES, SOUTHLAKE_HOSPITAL

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #4A1D96 0%, #7C3AED 100%);">
    <h1> Simulation &amp; Operations Validation</h1>
    <p>Validate synthetic cohort operational impact — callback burden, shuttle demand, escalation workload, care program stress.</p>
</div>
""", unsafe_allow_html=True)

followups = load_followup_results()
queue = load_doctor_queue()
cases = load_cases()
patients = load_patients()
records = load_patient_records()

# Build task lists from followup_results (where clinician decisions are stored)
callback_tasks, shuttle_tasks, emergency_tasks = [], [], []

c_ops_title, c_ops_ref = st.columns([3, 1])
with c_ops_ref:
    if st.button(" Refresh", key="ops_refresh", use_container_width=True):
        st.rerun()

if not followups.empty:
    for _, row in followups.iterrows():
        level = str(row.get("risk_level", "Green"))
        transport = str(row.get("transport_level", "None"))
        review = str(row.get("clinician_review_status", "Pending"))

        # Try to find patient name from multiple sources
        name = "Unknown"; phone = "N/A"
        pid = str(row.get("patient_id", ""))
        cid = str(row.get("case_id", ""))

        # Try patients.csv
        if not patients.empty and pid and pid != "UNKNOWN" and pid != "nan":
            pm = patients[patients["patient_id"] == pid]
            if not pm.empty:
                name = pm.iloc[0]["full_name"]
                phone = str(pm.iloc[0].get("phone", "N/A"))

        # Try cases.csv → patients.csv
        if name == "Unknown" and not cases.empty and cid:
            cm = cases[cases["case_id"] == cid]
            if not cm.empty:
                c_pid = str(cm.iloc[0].get("patient_id", ""))
                if not patients.empty and c_pid and c_pid != "UNKNOWN":
                    pm = patients[patients["patient_id"] == c_pid]
                    if not pm.empty:
                        name = pm.iloc[0]["full_name"]
                        phone = str(pm.iloc[0].get("phone", "N/A"))
                # Also try patient_name from queue
                if name == "Unknown" and not queue.empty:
                    qm = queue[queue["case_id"] == cid]
                    if not qm.empty:
                        name = str(qm.iloc[0].get("patient_name", "Unknown"))

        # Try discharge summaries for name
        if name == "Unknown":
            name = f"Patient ({cid})"

        task = {"followup_id": row.get("followup_id",""), "case_id": cid, "patient": name, "phone": phone,
                "risk_level": level, "transport": transport, "action": row.get("recommended_action",""),
                "review_status": review, "date": row.get("followup_date",""),
                "recovery": row.get("recovery_level",""), "report": row.get("clinician_report","")}

        # Classify into task buckets
        if level == "Yellow" or "callback" in str(row.get("recommended_action","")).lower():
            callback_tasks.append(task)
        elif level == "Red":
            if "LEVEL3" in str(transport):
                emergency_tasks.append(task)
            else:
                shuttle_tasks.append(task)

st.markdown(f"""
<div class="metric-row">
    <div class="metric-card"><div class="number" style="color:#EAB308">{len(callback_tasks)}</div><div class="label"> Callbacks</div></div>
    <div class="metric-card"><div class="number" style="color:#EA580C">{len(shuttle_tasks)}</div><div class="label"> Shuttle</div></div>
    <div class="metric-card"><div class="number" style="color:#DC2626">{len(emergency_tasks)}</div><div class="label"> Emergency</div></div>
    <div class="metric-card"><div class="number">{len(followups) if not followups.empty else 0}</div><div class="label">Total Follow-ups</div></div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([f" Callbacks ({len(callback_tasks)})", f" Shuttle ({len(shuttle_tasks)})", f" Emergency ({len(emergency_tasks)})", " Transport Nodes"])

with tab1:
    if callback_tasks:
        for i, t in enumerate(callback_tasks):
            report_snip = str(t.get("report",""))[:80] if t.get("report") else ""
            st.markdown(f'<div class="case-card case-card-yellow"><div style="display:flex;justify-content:space-between;"><strong>{t["patient"]}</strong><span class="badge badge-yellow"> Callback</span></div><p>{t["case_id"]} | {t["followup_id"]} | {t["date"]} | {t["action"]}</p><p> Phone: <strong>{t["phone"]}</strong> | Recovery: {t.get("recovery","N/A")}</p>{f"<p> <em>{report_snip}</em></p>" if report_snip else ""}</div>', unsafe_allow_html=True)
            if st.button(f" Call {t['patient']}", key=f"call_{i}", use_container_width=False):
                st.success(f"Initiating call to {t['patient']} at {t['phone']}...")
    else: st.info("No callbacks. Clinician actions from Follow-Up History will appear here.")

with tab2:
    if shuttle_tasks:
        for i, t in enumerate(shuttle_tasks):
            st.markdown(f'<div class="case-card case-card-red"><div style="display:flex;justify-content:space-between;"><strong>{t["patient"]}</strong><span class="badge badge-red"> {t["transport"]}</span></div><p>{t["case_id"]} | {t["date"]} | {t["action"]}</p></div>', unsafe_allow_html=True)
            if st.button(f" Track Shuttle for {t['patient']}", key=f"loc_{i}", use_container_width=False):
                # Show shuttle tracking map
                import plotly.graph_objects as go_map
                hosp = SOUTHLAKE_HOSPITAL
                # Simulate shuttle position between a node and hospital
                node = TRANSPORT_NODES[min(i+1, len(TRANSPORT_NODES)-1)]
                shuttle_lat = (hosp["lat"] + node["lat"]) / 2 + np.random.uniform(-0.005, 0.005)
                shuttle_lng = (hosp["lng"] + node["lng"]) / 2 + np.random.uniform(-0.005, 0.005)
                fig_shuttle = go_map.Figure()
                fig_shuttle.add_trace(go_map.Scattermapbox(
                    lat=[hosp["lat"], shuttle_lat, node["lat"]], lon=[hosp["lng"], shuttle_lng, node["lng"]],
                    mode="lines+markers+text",
                    marker=dict(size=[18, 14, 14], color=["#DC2626", "#F97316", "#EA580C"]),
                    text=[" Hospital", f" Shuttle ({t['patient']})", f" {node['name']}"],
                    textposition="top center", textfont=dict(size=11),
                    hoverinfo="text", showlegend=False,
                ))
                fig_shuttle.update_layout(mapbox=dict(style="open-street-map", center=dict(lat=shuttle_lat, lon=shuttle_lng), zoom=12.5), margin=dict(l=0,r=0,t=0,b=0), height=350)
                st.plotly_chart(fig_shuttle, use_container_width=True)
    else: st.info("No shuttle tasks. Clinician actions from Follow-Up History will appear here.")

with tab3:
    if emergency_tasks:
        for t in emergency_tasks:
            st.markdown(f'<div class="safety-banner"><strong> {t["patient"]}</strong> | {t["case_id"]} | {t["date"]}<br><strong>{t["action"]}</strong></div>', unsafe_allow_html=True)
    else: st.info("No emergency tasks. Clinician actions from Follow-Up History will appear here.")

with tab4:
    st.markdown("###  Community Pickup Nodes")
    hosp = SOUTHLAKE_HOSPITAL; nodes = TRANSPORT_NODES
    ll, ln = [], []
    for n in nodes: ll += [hosp["lat"], n["lat"], None]; ln += [hosp["lng"], n["lng"], None]
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(lat=ll, lon=ln, mode="lines", line=dict(width=2, color="#F97316"), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scattermapbox(lat=[hosp["lat"]]+[n["lat"] for n in nodes], lon=[hosp["lng"]]+[n["lng"] for n in nodes], mode="markers+text", marker=dict(size=[22]+[14]*len(nodes), color=["#DC2626"]+["#EA580C"]*len(nodes)), text=[hosp["name"]]+[n["name"] for n in nodes], textposition="top center", textfont=dict(size=11), hovertext=[" Hospital"]+[f" {n['distance']}" for n in nodes], hoverinfo="text", showlegend=False))
    fig.update_layout(mapbox=dict(style="open-street-map", center=dict(lat=44.03, lon=-79.462), zoom=11.5), margin=dict(l=0,r=0,t=0,b=0), height=420)
    st.plotly_chart(fig, use_container_width=True)
    for n in nodes:
        st.markdown(f'<div class="transport-node"><span class="node-name"> {n["name"]}</span><span class="node-distance">{n["distance"]} ({n["drive_min"]} min)</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"> <strong>L1:</strong> Family pickup | <strong>L2:</strong> Shuttle from node | <strong>L3:</strong> Ambulance dispatch</div>', unsafe_allow_html=True)

# ─── Efficiency ───
st.markdown("---")
st.markdown("###  Efficiency Impact")
st.markdown(f"""
<div class="result-card"><h3>Projected Time Savings</h3>
<div class="metric-row">
    <div class="metric-card"><div class="number" style="color:#059669">~15 min</div><div class="label">Per Registration</div></div>
    <div class="metric-card"><div class="number" style="color:#059669">~8 min</div><div class="label">Per Pre-Triage</div></div>
    <div class="metric-card"><div class="number" style="color:#059669">~12 min</div><div class="label">Per Follow-Up</div></div>
    <div class="metric-card"><div class="number" style="color:#059669">~35 min</div><div class="label">Per Patient Journey</div></div>
</div></div>
""", unsafe_allow_html=True)

# ─── Care Program Workload ───
st.markdown("---")
st.markdown("###  Care Program Workload")
if not records.empty:
    sl = records[records["anchor_hospital"] == "Southlake Regional Health Centre"]
    c1, c2 = st.columns(2)
    with c1:
        prog = sl["care_program"].value_counts().reset_index(); prog.columns = ["Program","Patients"]
        st.plotly_chart(px.bar(prog.sort_values("Patients"), x="Patients", y="Program", orientation="h", title="Patients by Care Program", color_discrete_sequence=["#7C3AED"]), use_container_width=True)
    with c2:
        esc = sl[sl["care_status"]=="Escalated"]["care_program"].value_counts().reset_index(); esc.columns = ["Program","Escalated"]
        st.plotly_chart(px.bar(esc.sort_values("Escalated"), x="Escalated", y="Program", orientation="h", title="Escalated by Program", color_discrete_sequence=["#DC2626"]), use_container_width=True)

    st.markdown("####  Physician Workload")
    phys = sl.groupby("attending_physician").agg(Total=("record_id","count"), Escalated=("care_status", lambda x: (x=="Escalated").sum()), Avg_FU=("followup_count_30d","mean")).reset_index()
    phys["Avg_FU"] = phys["Avg_FU"].round(1)
    phys.columns = ["Physician","Total","Escalated","Avg Follow-ups (30d)"]
    st.dataframe(phys.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)
