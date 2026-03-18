import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.styles import inject_css, risk_banner, risk_circle, format_risk_column
from utils.storage import load_cases, load_discharge_summaries, load_followup_results, load_patient_records, load_patients, append_row_csv, get_next_id, now_str, DATA_DIR
from utils.ai_client import ai_generate_followup_questionnaire, ai_analyze_followup_risk
from core.followup import classify_followup
from core.transport import recommend_transport
from utils.constants import TRANSPORT_NODES, SOUTHLAKE_HOSPITAL

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #065F46 0%, #059669 100%);">
    <h1>📊 Post-Discharge Follow-Up Simulation</h1>
    <p>Validate synthetic cohort follow-up risk classification, transport demand, and clinician review workload.</p>
</div>
""", unsafe_allow_html=True)

fu = load_followup_results()
cases = load_cases()
discharge = load_discharge_summaries()
records = load_patient_records()
southlake = records[records["anchor_hospital"] == "Southlake Regional Health Centre"] if not records.empty else pd.DataFrame()

# ═══════════════════════════════════════════
#  Metrics
# ═══════════════════════════════════════════
total_fu = len(fu) if not fu.empty else 0
red = len(fu[fu["risk_level"]=="Red"]) if not fu.empty else 0
yellow = len(fu[fu["risk_level"]=="Yellow"]) if not fu.empty else 0
green = len(fu[fu["risk_level"]=="Green"]) if not fu.empty else 0
pending = len(fu[fu["clinician_review_status"]=="Pending"]) if not fu.empty and "clinician_review_status" in fu.columns else 0

st.markdown(f"""
<div class="metric-row">
    <div class="metric-card"><div class="number">{total_fu}</div><div class="label">Total Follow-ups</div></div>
    <div class="metric-card"><div class="number" style="color:#DC2626">{red}</div><div class="label">🔴 Red</div></div>
    <div class="metric-card"><div class="number" style="color:#EAB308">{yellow}</div><div class="label">🟡 Yellow</div></div>
    <div class="metric-card"><div class="number" style="color:#22C55E">{green}</div><div class="label">🟢 Green</div></div>
    <div class="metric-card"><div class="number" style="color:#EA580C">{pending}</div><div class="label">⏳ Pending</div></div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
#  Tabs: Analytics | Case Management | History
# ═══════════════════════════════════════════
tab_analytics, tab_manage, tab_history = st.tabs(["📈 Analytics", "🔧 Case Management", "📁 Follow-Up History"])

with tab_analytics:
    if not fu.empty:
        c1, c2 = st.columns(2)
        with c1:
            risk = fu["risk_level"].value_counts().reset_index(); risk.columns = ["Risk","Count"]
            st.plotly_chart(px.pie(risk, names="Risk", values="Count", color="Risk", color_discrete_map={"Red":"#EF4444","Yellow":"#EAB308","Green":"#22C55E"}, title="Risk Distribution"), use_container_width=True)
        with c2:
            status = fu["clinician_review_status"].value_counts().reset_index(); status.columns = ["Status","Count"]
            st.plotly_chart(px.bar(status, x="Status", y="Count", title="Review Status", color_discrete_sequence=["#7C3AED"]), use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            if "transport_level" in fu.columns:
                tr = fu["transport_level"].value_counts().reset_index(); tr.columns = ["Level","Count"]
                st.plotly_chart(px.bar(tr.sort_values("Count"), x="Count", y="Level", orientation="h", title="Transport Levels", color_discrete_sequence=["#EA580C"]), use_container_width=True)
        with c4:
            if "risk_score" in fu.columns:
                st.plotly_chart(px.histogram(fu, x="risk_score", nbins=10, title="Risk Score Distribution", color_discrete_sequence=["#DC2626"]), use_container_width=True)
    else:
        st.info("No follow-up data yet.")

with tab_manage:
    st.markdown("### Select a Case for Follow-Up Assessment")

    tab_d, tab_r = st.tabs(["📄 Discharge Summaries", "📊 Patient Records (Escalated/Monitoring)"])

    with tab_d:
        if discharge.empty:
            st.warning("No discharge summaries.")
        else:
            opts = [f"{r['case_id']} — {r['diagnosis_summary'][:60]}..." for _, r in discharge.iterrows()]
            sel = st.selectbox("Choose case:", opts, key="adm_fu_d")
            sel_id = sel.split(" — ")[0]
            dr = discharge[discharge["case_id"]==sel_id].iloc[0]
            st.markdown(f'<div class="case-card"><h3>📄 {sel_id}</h3><p><strong>Diagnosis:</strong> {dr["diagnosis_summary"]}</p><p><strong>Medications:</strong> {dr["medications"]}</p><p><strong>Instructions:</strong> {dr["discharge_instructions"]}</p></div>', unsafe_allow_html=True)
            st.session_state["adm_fu_dr"] = dr; st.session_state["adm_fu_cid"] = sel_id

    with tab_r:
        if southlake.empty:
            st.warning("No records.")
        else:
            active = southlake[southlake["care_status"].isin(["Escalated","Monitoring"])].sort_values("age", ascending=False).head(80)
            rl = {}
            for _, r in active.iterrows():
                l = f"{r['record_id']} — {r['patient_name']} | {r['primary_diagnosis']} | {r['care_status']}"
                rl[l] = r
            if rl:
                sel_r = st.selectbox("Choose patient:", list(rl.keys()), key="adm_fu_r")
                rr = rl[sel_r]
                st.markdown(f'<div class="case-card {"case-card-red" if rr["care_status"]=="Escalated" else "case-card-yellow"}"><h3>👤 {rr["patient_name"]} ({rr["record_id"]})</h3><p>Age: {rr["age"]} | {rr["primary_diagnosis"]} | Meds: {rr["medication_plan"]} | Goal: {rr["next_visit_goal"]}</p></div>', unsafe_allow_html=True)
                st.session_state["adm_fu_dr"] = pd.Series({"case_id":rr["record_id"],"diagnosis_summary":rr["primary_diagnosis"],"medications":rr["medication_plan"],"discharge_instructions":f"Goal: {rr['next_visit_goal']}. Program: {rr['care_program']}.","attending_service":rr["department"],"discharge_date":rr["last_visit_date"]})
                st.session_state["adm_fu_cid"] = rr["record_id"]

    dr = st.session_state.get("adm_fu_dr")
    cid = st.session_state.get("adm_fu_cid","UNKNOWN")
    if dr is not None:
        st.markdown("---")

        def _q2str(q):
            """Force any question object to plain text string."""
            if isinstance(q, dict):
                for key in ["text", "question", "content", "q"]:
                    if key in q and q[key]:
                        return str(q[key])
                return str(q)
            return str(q)

        # ─── Generate + Edit buttons side by side ───
        c_gen, c_edit = st.columns(2)
        with c_gen:
            gen_clicked = st.button("🤖 Generate AI Questionnaire", type="primary", key="adm_gen_q", use_container_width=True)
        with c_edit:
            edit_clicked = st.button("✏️ Edit Questions", key="adm_edit_q_top", use_container_width=True)

        if edit_clicked:
            if "adm_fu_qlist" not in st.session_state or not st.session_state["adm_fu_qlist"]:
                st.session_state["adm_fu_qlist"] = [
                    "How is your pain level today on a scale of 0-10?",
                    "Have you experienced any new symptoms since discharge?",
                    "Are you taking all medications as prescribed?",
                    "Have you noticed any changes in your condition?",
                    "Do you have any concerns about your recovery?",
                ]
            st.session_state["adm_fu_editing"] = True
            st.rerun()

        if gen_clicked:
            with st.spinner("AI generating questionnaire..."):
                ai_qs = ai_generate_followup_questionnaire(dr["discharge_instructions"], dr["diagnosis_summary"], dr["medications"])
            clean = []
            if ai_qs and "questions" in ai_qs:
                st.session_state["adm_fu_ai"] = ai_qs
                for q in ai_qs["questions"]:
                    clean.append(_q2str(q))
            if not clean:
                clean = [
                    "How is your pain level today on a scale of 0-10?",
                    "Have you experienced any fever, chills, or shortness of breath since discharge?",
                    "Are you taking all prescribed medications on schedule?",
                    "How would you describe your energy level compared to before discharge?",
                    "Have you noticed any signs of infection such as redness, swelling, or warmth?",
                    "Have you been able to follow the dietary instructions given at discharge?",
                    "Do you have any new symptoms or concerns since leaving the hospital?",
                ]
            st.session_state["adm_fu_qlist"] = clean
            st.session_state["adm_fu_editing"] = False
            st.rerun()

        # ─── Question list ───
        if "adm_fu_qlist" in st.session_state and st.session_state["adm_fu_qlist"]:
            qlist = [_q2str(q) for q in st.session_state["adm_fu_qlist"]]

            if not st.session_state.get("adm_fu_editing"):
                # ═══ VIEW MODE ═══
                st.markdown("### 📋 Follow-Up Questions")
                for i, txt in enumerate(qlist):
                    st.markdown(f"""<div style="padding:0.7rem 1rem;margin:0.4rem 0;background:#F8FAFC;border-left:3px solid #3B82F6;border-radius:6px;font-size:1rem;">
                        <strong style="color:#2563EB;">Q{i+1}.</strong> {txt}</div>""", unsafe_allow_html=True)
                st.markdown("")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✏️ Edit Questions", key="adm_edit_q", use_container_width=True):
                        st.session_state["adm_fu_editing"] = True
                        st.rerun()
                with c2:
                    if st.button("📤 Send Questionnaire to Patient", type="primary", key="adm_send_q", use_container_width=True):
                        import json as _json
                        q_path = os.path.join(DATA_DIR, "followup_questions.json")
                        existing = {}
                        if os.path.exists(q_path):
                            with open(q_path, "r") as f:
                                try: existing = _json.load(f)
                                except: existing = {}
                        existing[cid] = {"questions": qlist, "sent_at": now_str(), "status": "pending"}
                        with open(q_path, "w") as f:
                            _json.dump(existing, f, indent=2)
                        st.success(f"✅ Questionnaire ({len(qlist)} questions) sent to case {cid}!")
            else:
                # ═══ EDIT MODE ═══
                st.markdown("### ✏️ Edit Questions")
                st.markdown('<div class="info-panel">Modify existing questions, then add new ones or send directly.</div>', unsafe_allow_html=True)
                edited = []
                for i, txt in enumerate(qlist):
                    val = st.text_input(f"Q{i+1}", value=txt, key=f"adm_eq_{i}")
                    edited.append(val)
                st.markdown("---")
                new_q = st.text_input("➕ Add new question:", placeholder="Type a new follow-up question...", key="adm_new_q")
                st.markdown("")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("➕ Add & Continue Editing", key="adm_add_more", use_container_width=True):
                        saved = [q for q in edited if q.strip()]
                        if new_q.strip():
                            saved.append(new_q.strip())
                        st.session_state["adm_fu_qlist"] = saved
                        st.rerun()
                with c2:
                    if st.button("📤 Send Questionnaire to Patient", type="primary", key="adm_save_send", use_container_width=True):
                        saved = [q for q in edited if q.strip()]
                        if new_q.strip():
                            saved.append(new_q.strip())
                        st.session_state["adm_fu_qlist"] = saved
                        st.session_state["adm_fu_editing"] = False
                        import json as _json
                        q_path = os.path.join(DATA_DIR, "followup_questions.json")
                        existing = {}
                        if os.path.exists(q_path):
                            with open(q_path, "r") as f:
                                try: existing = _json.load(f)
                                except: existing = {}
                        existing[cid] = {"questions": saved, "sent_at": now_str(), "status": "pending"}
                        with open(q_path, "w") as f:
                            _json.dump(existing, f, indent=2)
                        st.success(f"✅ Questionnaire ({len(saved)} questions) sent to case {cid}!")
                        st.rerun()

        if st.session_state.get("adm_fu_ai",{}).get("monitoring_summary"):
            st.markdown(f'<div class="info-panel">🤖 <strong>AI Focus:</strong> {st.session_state["adm_fu_ai"]["monitoring_summary"]}</div>', unsafe_allow_html=True)

with tab_history:
    c_title, c_refresh = st.columns([3, 1])
    with c_title:
        st.markdown("### 📁 All Follow-Up Records")
    with c_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="hist_refresh", use_container_width=True):
            st.rerun()

    fu_fresh = load_followup_results()
    if not fu_fresh.empty:
        # Remove questionnaire_answers column, sort: Pending first, Reviewed last
        display_cols = [c for c in fu_fresh.columns if c not in ["questionnaire_answers", "admin_qa", "patient_notes", "clinician_report"]]
        fu_display = fu_fresh[display_cols].copy()

        # Sort: Pending on top, Reviewed at bottom
        status_order = {"Pending": 0, "Reviewed": 1}
        if "clinician_review_status" in fu_display.columns:
            fu_display["_sort"] = fu_display["clinician_review_status"].map(status_order).fillna(0)
            fu_display = fu_display.sort_values("_sort").drop(columns=["_sort"])

        # Add marking column
        fu_display.insert(0, "✅ Mark", False)
        edited_fu = st.data_editor(
            format_risk_column(fu_display),
            use_container_width=True, hide_index=True, key="fu_hist_editor",
            disabled=[c for c in display_cols],
            column_config={"✅ Mark": st.column_config.CheckboxColumn("✅", default=False)},
        )
        marked = edited_fu[edited_fu["✅ Mark"] == True]
        if not marked.empty:
            st.info(f"Marked {len(marked)} record(s) for review.")

        # ─── Patient Submission Viewer ───
        st.markdown("---")
        st.markdown("### 🔍 Review Patient Submission")
        pending = fu_fresh[fu_fresh["clinician_review_status"] == "Pending"] if "clinician_review_status" in fu_fresh.columns else fu_fresh
        if not pending.empty:
            options = []
            for _, r in fu_fresh.iterrows():
                status_icon = "⏳" if r.get("clinician_review_status") == "Pending" else "✅"
                risk_icon = {"Green":"🟢","Yellow":"🟡","Red":"🔴"}.get(r.get("risk_level",""),"⚪")
                options.append(f"{status_icon} {r.get('followup_id','')} — {r.get('case_id','')} | {risk_icon} {r.get('risk_level','')} | {r.get('followup_date','')}")

            sel_hist = st.selectbox("Select a submission to review:", options, key="hist_sel")
            sel_idx = options.index(sel_hist)
            sel_row = fu_fresh.iloc[sel_idx]

            # Show patient's answers
            st.markdown(f"#### 📋 Patient Submission: {sel_row.get('followup_id','')}")
            risk_icon = {"Green":"🟢","Yellow":"🟡","Red":"🔴"}.get(sel_row.get("risk_level",""),"⚪")
            st.markdown(f'<div class="info-panel"><strong>Case:</strong> {sel_row.get("case_id","")} | <strong>Patient:</strong> {sel_row.get("patient_id","")} | <strong>Date:</strong> {sel_row.get("followup_date","")} | <strong>Risk:</strong> {risk_icon} {sel_row.get("risk_level","")} | <strong>Score:</strong> {sel_row.get("risk_score","")}</div>', unsafe_allow_html=True)

            # Parse standard answers
            qa_str = str(sel_row.get("questionnaire_answers", ""))
            if qa_str and qa_str != "nan":
                st.markdown("**Standard Checklist Answers:**")
                for item in qa_str.split(";"):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        icon = "✅" if v.strip().lower() == "true" else "❌" if v.strip().lower() == "false" else f"**{v.strip()}**"
                        label = k.strip().replace("_", " ").title()
                        st.markdown(f"- {label}: {icon}")

            # Parse admin Q&A answers
            admin_qa = str(sel_row.get("admin_qa", ""))
            if admin_qa and admin_qa != "nan" and admin_qa.strip():
                st.markdown("**Care Team Questions & Patient Answers:**")
                for qa in admin_qa.split(" || "):
                    if "Q" in qa:
                        st.markdown(f'<div style="padding:0.5rem 1rem;margin:0.3rem 0;background:#EBF5FF;border-left:3px solid #3B82F6;border-radius:6px;">{qa}</div>', unsafe_allow_html=True)

            # Patient notes
            pn = str(sel_row.get("patient_notes", ""))
            if pn and pn != "nan" and pn.strip():
                st.markdown(f"**Patient Notes:** {pn}")

            # ─── Admin Clinical Assessment ───
            st.markdown("---")
            st.markdown("### 👨‍⚕️ Clinician Assessment")

            c1, c2 = st.columns(2)
            with c1:
                h_pain = st.slider("Pain (0-10)", 0, 10, 2, key="hist_fp")
                h_fever = st.checkbox("Fever", key="hist_ff")
                h_sob = st.checkbox("Shortness of breath", key="hist_fs")
                h_bsh = st.checkbox("Blood sugar high", key="hist_fb")
            with c2:
                h_bpa = st.checkbox("BP abnormal", key="hist_fbp")
                h_o2 = st.checkbox("O2 < 94%", key="hist_fo")
                h_worse = st.checkbox("Worse", key="hist_fw")
                h_new = st.checkbox("New symptoms", key="hist_fn")
                h_med = st.checkbox("Med non-compliant", key="hist_fm")
                h_wound = st.checkbox("Wound issue", key="hist_fwd")

            h_family = st.checkbox("Family transport available", key="hist_fam")
            medical_report = st.text_area("📝 Clinician Medical Report / Notes:", height=120, key="hist_report", placeholder="Write your clinical assessment, treatment plan, and any follow-up instructions here...")

            if st.button("⚡ Run Assessment & Update Record", type="primary", key="hist_assess", use_container_width=True):
                h_answers = {"pain_level":h_pain,"fever":h_fever,"shortness_of_breath":h_sob,"blood_sugar_high":h_bsh,"blood_pressure_abnormal":h_bpa,"oxygen_low":h_o2,"worse_than_before":h_worse,"new_symptoms":h_new,"medication_noncompliant":h_med,"wound_issue":h_wound}
                h_result = classify_followup(h_answers)
                h_level = h_result["level"]
                h_transport = recommend_transport(h_level, h_family, h_sob and h_o2)
                h_circle = {"Green":"🟢","Yellow":"🟡","Red":"🔴"}.get(h_level,"⚪")

                st.markdown(risk_banner(h_level, f"{h_circle} {risk_circle(h_level)} — {h_result['urgency']}"), unsafe_allow_html=True)

                # Update the record in CSV
                import csv
                csv_path = os.path.join(DATA_DIR, "followup_results.csv")
                if os.path.exists(csv_path):
                    df_update = pd.read_csv(csv_path)
                    fuid = sel_row.get("followup_id", "")
                    mask = df_update["followup_id"] == fuid
                    if mask.any():
                        df_update.loc[mask, "risk_level"] = h_level
                        df_update.loc[mask, "risk_score"] = h_result["score"]
                        df_update.loc[mask, "clinician_review_status"] = "Reviewed"
                        df_update.loc[mask, "recommended_action"] = h_result["action"]
                        if "clinician_report" not in df_update.columns:
                            df_update["clinician_report"] = ""
                        df_update.loc[mask, "clinician_report"] = medical_report
                        df_update.to_csv(csv_path, index=False)
                        st.success(f"✅ Record **{fuid}** updated: Risk → {h_circle} {h_level} | Score → {h_result['score']} | Status → Reviewed")
                    else:
                        st.warning("Record not found for update.")
        else:
            st.info("No submissions to review.")
    else:
        st.info("No follow-up records.")
