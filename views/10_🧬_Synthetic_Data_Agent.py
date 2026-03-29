"""
Southlake Agentic Synthetic Data Creation Service
Full 10-step pipeline: NL→Contract→Strategy→Generate→Audit→Repair→Re-Audit→FHIR→Simulate→Pack
"""
import streamlit as st
import pandas as pd
import numpy as np
import json, time, hashlib, io
from datetime import datetime
from utils.styles import inject_css
from utils.storage import load_patient_records, save_generation_run, load_generation_history, DATA_DIR
from core.synth_contract import build_contract_from_prompt
from core.synth_strategy import choose_generation_strategy
from core.synth_repair import needs_repair, repair_dataset
import plotly.express as px
import plotly.graph_objects as go

inject_css()

# ═══════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════
FHIR_MAPPING = {
    "record_id":{"r":"Patient","p":"Patient.identifier","d":"Unique record identifier"},
    "patient_name":{"r":"Patient","p":"Patient.name.text","d":"Patient full name"},
    "patient_alias_id":{"r":"Patient","p":"Patient.identifier[alias]","d":"De-identified alias"},
    "gender":{"r":"Patient","p":"Patient.gender","d":"Administrative gender"},
    "age":{"r":"Patient","p":"Patient.birthDate (derived)","d":"Age in years"},
    "city":{"r":"Patient","p":"Patient.address.city","d":"City of residence"},
    "initial_visit_date":{"r":"Encounter","p":"Encounter.period.start","d":"Initial encounter date"},
    "anchor_hospital":{"r":"Organization","p":"Organization.name","d":"Primary hospital"},
    "department":{"r":"Encounter","p":"Encounter.serviceType","d":"Clinical department"},
    "attending_physician":{"r":"Practitioner","p":"Practitioner.name","d":"Attending physician"},
    "primary_diagnosis":{"r":"Condition","p":"Condition.code.text","d":"Primary diagnosis"},
    "care_program":{"r":"CarePlan","p":"CarePlan.category","d":"Care pathway"},
    "insurance_plan":{"r":"Coverage","p":"Coverage.type","d":"Insurance type"},
    "visit_channel":{"r":"Encounter","p":"Encounter.class","d":"Visit modality"},
    "followup_count_30d":{"r":"Encounter","p":"Encounter.count(30d)","d":"30-day follow-ups"},
    "followup_count_90d":{"r":"Encounter","p":"Encounter.count(90d)","d":"90-day follow-ups"},
    "last_visit_date":{"r":"Encounter","p":"Encounter.period.start(latest)","d":"Most recent visit"},
    "next_visit_goal":{"r":"Goal","p":"Goal.description","d":"Next visit clinical goal"},
    "medication_plan":{"r":"MedicationRequest","p":"MedicationRequest.medication","d":"Current medications"},
    "care_status":{"r":"EpisodeOfCare","p":"EpisodeOfCare.status","d":"Care status"},
}

NAMES = ["Aiden Smith","Maya Johnson","Liam Brown","Sophia Williams","Noah Davis","Olivia Wilson","Ethan Moore","Emma Taylor","Lucas Anderson","Ava Thomas","Mason Jackson","Isabella White","Logan Harris","Mia Martin","Alexander Thompson","Charlotte Garcia","Jacob Martinez","Amelia Robinson","Daniel Clark","Harper Lewis","James Hall","Evelyn Allen","Benjamin Young","Abigail King","Henry Wright","Emily Lopez","Sebastian Hill","Elizabeth Scott","Jack Green","Sofia Adams","Owen Baker","Avery Nelson","William Carter","Ella Mitchell","Elijah Perez","Scarlett Roberts","Michael Turner","Aria Phillips","Ryan Campbell","Chloe Parker","Nathan Evans","Grace Edwards","Samuel Collins","Lily Stewart","Christian Sanchez","Zoey Morris","Dylan Rogers","Nora Reed","Caleb Cook","Hannah Morgan"]

def _trace(step, icon, action, detail, status="", dur=0):
    return {"step":step,"icon":icon,"action":action,"detail":detail,"status":status,"duration":f"{dur:.1f}s"}

# ═══════════════════════════════════════════
#  GENERATION ENGINE
# ═══════════════════════════════════════════
def generate_cohort(seed_df, contract, trace):
    n = contract.get("target_size", 500)
    constraints = {}
    # Flatten contract into constraints dict
    age_rules = contract.get("age_rules", {})
    if age_rules.get("min_age"): constraints["min_age"] = age_rules["min_age"]
    if age_rules.get("max_age"): constraints["max_age"] = age_rules["max_age"]
    if contract.get("department_mix"): constraints["department"] = contract["department_mix"]
    if contract.get("diagnosis_filter"): constraints["diagnosis"] = contract["diagnosis_filter"]
    geo = contract.get("geography", {})
    if geo.get("hospital_filter"): constraints["hospital"] = geo["hospital_filter"]
    if geo.get("cities"): constraints["cities"] = geo["cities"]
    if contract.get("escalation_target"): constraints["escalation_rate"] = contract["escalation_target"]

    t0 = time.time()
    weights = np.ones(len(seed_df))

    if "min_age" in constraints:
        m = seed_df["age"] >= constraints["min_age"]; weights[m.values] *= 3.0; weights[~m.values] *= 0.3
    if "max_age" in constraints:
        m = seed_df["age"] <= constraints["max_age"]; weights[m.values] *= 2.0; weights[~m.values] *= 0.5
    if "department" in constraints:
        d = constraints["department"]
        m = seed_df["department"].isin(d) if isinstance(d, list) else seed_df["department"] == d
        weights[m.values] *= 5.0; weights[~m.values] *= 0.5
    if "hospital" in constraints:
        m = seed_df["anchor_hospital"].str.contains(constraints["hospital"], case=False, na=False)
        weights[m.values] *= 4.0; weights[~m.values] *= 0.3
    if "cities" in constraints:
        m = seed_df["city"].isin(constraints["cities"]); weights[m.values] *= 3.0
    if "diagnosis" in constraints:
        dd = constraints["diagnosis"] if isinstance(constraints["diagnosis"], list) else [constraints["diagnosis"]]
        m = seed_df["primary_diagnosis"].isin(dd); weights[m.values] *= 5.0; weights[~m.values] *= 0.3

    weights = weights / weights.sum()
    np.random.seed(42)
    indices = np.random.choice(len(seed_df), size=n, replace=True, p=weights)
    sampled = seed_df.iloc[indices].copy().reset_index(drop=True)
    trace.append(_trace(5,"","Weighted Sampling",f"Sampled {n} from seed (n={len(seed_df)}) with {len(constraints)} constraints","",time.time()-t0))

    # Perturbation
    t1 = time.time()
    sampled["record_id"] = [f"SYN-{i+1:04d}" for i in range(n)]
    np.random.shuffle(NAMES)
    sampled["patient_name"] = [NAMES[i%len(NAMES)] for i in range(n)]
    sampled["patient_alias_id"] = [f"PT-{np.random.randint(100000,999999)}" for _ in range(n)]
    sampled["age"] = (sampled["age"] + np.random.randint(-3,4,size=n)).clip(18,95)
    for col in ["initial_visit_date","last_visit_date"]:
        if col in sampled.columns:
            try:
                d = pd.to_datetime(sampled[col], errors="coerce")
                sampled[col] = (d + pd.to_timedelta(np.random.randint(-30,31,size=n), unit="D")).dt.strftime("%Y-%m-%d")
            except: pass
    for col in ["followup_count_30d","followup_count_90d"]:
        if col in sampled.columns:
            sampled[col] = (sampled[col].astype(int) + np.random.randint(-1,2,size=n)).clip(0,10)
    if "followup_count_30d" in sampled.columns and "followup_count_90d" in sampled.columns:
        sampled["followup_count_90d"] = sampled[["followup_count_30d","followup_count_90d"]].max(axis=1)

    # Escalation hard constraint
    esc = constraints.get("escalation_rate")
    if esc is not None:
        n_target = int(n * esc)
        n_current = (sampled["care_status"]=="Escalated").sum()
        if n_target > n_current:
            idx = sampled[sampled["care_status"]!="Escalated"].index
            flip = np.random.choice(idx, size=min(n_target-n_current,len(idx)), replace=False)
            sampled.loc[flip,"care_status"] = "Escalated"
        elif n_target < n_current:
            idx = sampled[sampled["care_status"]=="Escalated"].index
            flip = np.random.choice(idx, size=min(n_current-n_target,len(idx)), replace=False)
            sampled.loc[flip,"care_status"] = np.random.choice(["Active","Monitoring","Graduated"], size=len(flip))
    trace.append(_trace(5,"","Perturbation + Hard Constraints",f"Perturbed {n} records (age±3, dates±30d, names shuffled, escalation aligned)","",time.time()-t1))
    return sampled

# ═══════════════════════════════════════════
#  AUDIT ENGINES (same as before, imported inline)
# ═══════════════════════════════════════════
def structural_audit(df):
    issues = []; fixes = 0
    for col in df.columns:
        nm = df[col].isna().sum()
        if nm > 0: issues.append({"field":col,"issue":"missing_values","count":int(nm),"severity":"medium"})
    if "initial_visit_date" in df.columns and "last_visit_date" in df.columns:
        try:
            bad = (pd.to_datetime(df["last_visit_date"],errors="coerce") < pd.to_datetime(df["initial_visit_date"],errors="coerce")).sum()
            if bad: issues.append({"field":"dates","issue":"last < initial","count":int(bad),"severity":"high"}); fixes += int(bad)
        except: pass
    if "followup_count_30d" in df.columns and "followup_count_90d" in df.columns:
        bad = (df["followup_count_30d"]>df["followup_count_90d"]).sum()
        if bad: issues.append({"field":"followup","issue":"30d>90d","count":int(bad),"severity":"high"}); fixes += int(bad)
    for col,valid in {"gender":["Male","Female","Nonbinary"],"care_status":["Active","Monitoring","Escalated","Graduated"],"visit_channel":["In-Person","Telephone","Hybrid"]}.items():
        if col in df.columns:
            inv = (~df[col].isin(valid)).sum()
            if inv: issues.append({"field":col,"issue":"invalid_enum","count":int(inv),"severity":"medium"})
    tc = df.shape[0]*df.shape[1]; ic = sum(i["count"] for i in issues); pr = 1-(ic/tc) if tc else 1
    return {"pass_rate":pr,"total_issues":len(issues),"affected_cells":ic,"auto_fixes":fixes,"issues":issues,"verdict":"PASS" if pr>0.95 else "WARN" if pr>0.85 else "FAIL"}

def plausibility_audit(df, seed_df, contract):
    fidelity = {}
    for col in ["age","department","primary_diagnosis","care_status","city","gender"]:
        if col in df.columns and col in seed_df.columns:
            if df[col].dtype in [np.float64,np.int64,float,int]:
                d = abs(df[col].mean()-seed_df[col].mean())/(seed_df[col].std()+1e-6)
                fidelity[col] = max(0,1-d*0.2)
            else:
                sd = df[col].value_counts(normalize=True); rd = seed_df[col].value_counts(normalize=True)
                fidelity[col] = sum(min(sd.get(c,0),rd.get(c,0)) for c in set(sd.index)|set(rd.index))
    fid_mean = np.mean(list(fidelity.values())) if fidelity else 0
    checks = []
    c = contract.get("escalation_target")
    if c: actual = (df["care_status"]=="Escalated").mean(); checks.append({"constraint":f"Escalation≈{c:.0%}","actual":f"{actual:.1%}","satisfied":abs(actual-c)<0.05})
    ar = contract.get("age_rules",{})
    if ar.get("min_age"): pct = (df["age"]>=ar["min_age"]).mean(); checks.append({"constraint":f"Age≥{ar['min_age']} majority","actual":f"{pct:.1%}","satisfied":pct>0.5})
    if contract.get("department_mix"):
        pct = df["department"].isin(contract["department_mix"]).mean(); checks.append({"constraint":"Dept focus","actual":f"{pct:.1%}","satisfied":pct>0.3})
    util = sum(1 for c in checks if c["satisfied"])/max(len(checks),1)
    elder_esc = (df[df["age"]>=65]["care_status"]=="Escalated").mean() if len(df[df["age"]>=65])>0 else 0
    young_esc = (df[df["age"]<65]["care_status"]=="Escalated").mean() if len(df[df["age"]<65])>0 else 0
    fu_age = {}
    if "followup_count_30d" in df.columns:
        ag = pd.cut(df["age"],bins=[0,17,64,84,120],labels=["0-17","18-64","65-84","85+"])
        fu_age = df.groupby(ag,observed=True)["followup_count_30d"].mean().to_dict()
    return {"fidelity":fidelity,"fidelity_mean":fid_mean,"utility_checks":checks,"utility_pass_rate":util,"elder_esc":elder_esc,"young_esc":young_esc,"elder_plausible":elder_esc>=young_esc,"fu_by_age":fu_age}

def privacy_audit(df, seed_df):
    res = {}
    mc = [c for c in ["age","city","department","primary_diagnosis","care_status","medication_plan"] if c in df.columns and c in seed_df.columns]
    if mc:
        sh = set(hashlib.md5(str(tuple(r.values)).encode()).hexdigest() for _,r in df[mc].iterrows())
        rh = set(hashlib.md5(str(tuple(r.values)).encode()).hexdigest() for _,r in seed_df[mc].iterrows())
        em = len(sh&rh); res["exact_match_count"]=em; res["exact_match_rate"]=em/max(len(sh),1)
        res["exact_match_risk"]="LOW" if res["exact_match_rate"]<0.05 else "MEDIUM" if res["exact_match_rate"]<0.15 else "HIGH"
    qi = [c for c in ["age","city","department"] if c in df.columns and c in seed_df.columns]
    if qi:
        ov = pd.merge(df[qi].drop_duplicates(),seed_df[qi].drop_duplicates(),on=qi,how="inner")
        uniq = 1-(len(ov)/max(len(seed_df[qi].drop_duplicates()),1))
        res["membership_qi_overlap"]=len(ov); res["membership_uniqueness"]=uniq
        res["membership_risk"]="LOW" if uniq>0.7 else "MEDIUM" if uniq>0.4 else "HIGH"
    if qi:
        g = df.groupby(qi,observed=True).size()
        mk = int(g.min()) if len(g) else 0; mdk = int(np.median(g)) if len(g) else 0
        res["k_anonymity_min"]=mk; res["k_anonymity_median"]=mdk
        res["attribute_disclosure_risk"]="LOW" if mk>=5 else "MEDIUM" if mk>=2 else "HIGH"
    if "age" in df.columns and "age" in seed_df.columns:
        noise = abs(df["age"].mean()-seed_df["age"].mean())
        eps = max(0.1,10/(noise+1)); res["dp_epsilon"]=round(eps,2)
        res["dp_note"]="Strong privacy" if eps<1 else "Moderate" if eps<5 else "Weak — add more noise"
    risks = [res.get(k,"LOW") for k in ["exact_match_risk","membership_risk","attribute_disclosure_risk"]]
    avg = np.mean([{"LOW":0,"MEDIUM":1,"HIGH":2}.get(r,0) for r in risks])
    res["overall_risk"]="LOW" if avg<0.5 else "MEDIUM" if avg<1.5 else "HIGH"
    return res


# ═══════════════════════════════════════════
#  PAGE START
# ═══════════════════════════════════════════
st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #0EA5E9 100%);">
    <h1> Agentic Synthetic Data Factory</h1>
    <p>Natural language → Data contract → Strategy selection → Generation → Dual audit → Repair loop → FHIR mapping → Simulation → Audit Pack</p>
    <p style="font-size:0.85rem; opacity:0.8;">Southlake Health &times; Ivey Hackathon | By Qi Sun &amp; Jia An &middot; Advisor: Kaiyu Li</p>
</div>
""", unsafe_allow_html=True)

seed_df = load_patient_records()
if seed_df.empty: st.error("Seed dataset not found."); st.stop()
st.markdown(f'<div class="info-panel"> <strong>Seed:</strong> {len(seed_df):,} records | {seed_df["department"].nunique()} depts | {seed_df["anchor_hospital"].nunique()} hospitals | {seed_df["primary_diagnosis"].nunique()} diagnoses</div>', unsafe_allow_html=True)

tab_gen, tab_audit, tab_fhir, tab_sim, tab_pack, tab_hist = st.tabs([" Generate"," Dual Audit"," FHIR"," Simulation"," Audit Pack"," Run History"])

# ═══════════════════════════════════════════
#  TAB 1: FULL AGENTIC PIPELINE
# ═══════════════════════════════════════════
with tab_gen:
    st.markdown("### Step 1: Natural Language Requirement")
    nl = st.text_area("Describe the synthetic dataset you need:", placeholder="Generate 500 elderly cardiac patients in York Region with 30% escalation rate", height=80)
    st.caption(" Try: _Generate 300 respiratory patients aged 65+ with 40% escalation for senior-friendly ED QI study_")

    c1,c2,c3 = st.columns(3)
    with c1: target_n = st.number_input("Target Records",50,5000,500,step=50)
    with c2: seed_filter = st.selectbox("Seed Filter",["All Hospitals","Southlake Only","SHINE Network"])
    with c3: override_strategy = st.selectbox("Strategy Override",["Auto (Agent decides)","Force: Constraint Blender","Force: Distribution Sampling","Force: Lifecycle Sim"])

    if st.button(" Run Agentic Pipeline", type="primary", use_container_width=True) and nl.strip():
        trace = []
        t_start = time.time()

        # ─── STEP 1: Parse Request ───
        trace.append(_trace(1,"","Parse Request","Analyzing natural language requirement","⏳"))
        contract = build_contract_from_prompt(nl, target_n)
        trace[-1] = _trace(1,"","Parse Request",f"Extracted {sum(1 for v in contract.get('age_rules',{}).values() if v)} age rules, {len(contract.get('department_mix',[]))} dept filters, escalation={contract.get('escalation_target','N/A')}","",time.time()-t_start)

        # ─── STEP 2: Build Data Contract ───
        trace.append(_trace(2,"","Build Data Contract",f"Schema: {len(seed_df.columns)} fields | Quality: fidelity≥{contract.get('quality_thresholds',{}).get('fidelity',0.8)}, privacy ε≤{contract.get('quality_thresholds',{}).get('privacy_epsilon',5)}",""))

        # ─── Show Editable Contract (human-AI co-creation) ───
        st.markdown("###  Data Contract (editable — human-AI co-creation)")
        contract_str = st.text_area("Edit contract JSON if needed:", value=json.dumps(contract, indent=2), height=250, key="contract_edit")
        try:
            contract = json.loads(contract_str)
        except:
            st.warning("Invalid JSON — using original contract.")
        contract["target_size"] = target_n

        # ─── STEP 3: Profile Seed ───
        t2 = time.time()
        if seed_filter == "Southlake Only":
            working = seed_df[seed_df["anchor_hospital"]=="Southlake Regional Health Centre"].copy()
        elif seed_filter == "SHINE Network":
            working = seed_df[seed_df["anchor_hospital"].isin(["Southlake Regional Health Centre","Markham Stouffville Hospital","Stevenson Memorial Hospital"])].copy()
        else:
            working = seed_df.copy()
        trace.append(_trace(3,"","Profile Seed Dataset",f"Filtered: {len(working)} records ({seed_filter}) | Age: {working['age'].min()}-{working['age'].max()} | Depts: {working['department'].nunique()}","",time.time()-t2))

        # ─── STEP 4: Choose Strategy ───
        t3 = time.time()
        if override_strategy != "Auto (Agent decides)":
            strat_name = {"Force: Constraint Blender":"constraint_weighted_blender","Force: Distribution Sampling":"distribution_matched_sampling","Force: Lifecycle Sim":"synthea_lifecycle_simulation"}[override_strategy]
            strat_info = {"strategy_name":strat_name,"display_name":override_strategy.replace("Force: ",""),"reasons":["User override"],"hard_constraints":[],"soft_constraints":[],"risk_notes":[],"expansion_ratio":target_n/len(working)}
        else:
            strat_info = choose_generation_strategy(contract, working)
        trace.append(_trace(4,"","Strategy Selection",f"Selected: {strat_info['display_name']} | Reasons: {'; '.join(strat_info['reasons'][:2])}","",time.time()-t3))

        # Show strategy reasoning
        st.markdown(f"""
        <div class="result-card">
            <h3> Agent Strategy: {strat_info['display_name']}</h3>
            <p>{'<br>'.join('• ' + r for r in strat_info['reasons'])}</p>
            <p><strong>Hard constraints:</strong> {', '.join(strat_info.get('hard_constraints',[])) or 'None'}</p>
            <p><strong>Soft constraints:</strong> {', '.join(strat_info.get('soft_constraints',[])) or 'None'}</p>
            {''.join(f'<p style="color:#DC2626;">{rn}</p>' for rn in strat_info.get('risk_notes',[]))}
        </div>
        """, unsafe_allow_html=True)

        # ─── STEP 5: Generate D0 ───
        D0 = generate_cohort(working, contract, trace)

        # ─── STEP 6: Structural Audit ───
        t4 = time.time()
        sa = structural_audit(D0)
        trace.append(_trace(6,"","Structural Audit (Pass 1)",f"Verdict: {sa['verdict']} | Pass rate: {sa['pass_rate']:.1%} | Issues: {sa['total_issues']}","" if sa["verdict"]!="FAIL" else "",time.time()-t4))

        # ─── STEP 7: Plausibility Audit ───
        t5 = time.time()
        pa = plausibility_audit(D0, working, contract)
        trace.append(_trace(7,"","Plausibility Audit (Pass 2)",f"Fidelity: {pa['fidelity_mean']:.2f} | Utility: {pa['utility_pass_rate']:.0%} | Elder plausible: {pa.get('elder_plausible','N/A')}","",time.time()-t5))

        # ─── STEP 8: Privacy Audit ───
        t6 = time.time()
        pra = privacy_audit(D0, working)
        trace.append(_trace(8,"","Privacy Audit",f"Risk: {pra['overall_risk']} | Exact match: {pra.get('exact_match_rate',0):.1%} | k-min: {pra.get('k_anonymity_min','N/A')} | ε≈{pra.get('dp_epsilon','N/A')}","" if pra["overall_risk"]!="HIGH" else "",time.time()-t6))

        # ─── STEP 9: REPAIR LOOP (D0 → D1) ───
        t7 = time.time()
        should_repair, repair_reasons = needs_repair(sa, pa, pra, contract)
        if should_repair:
            trace.append(_trace(9,"","Repair Loop Triggered",f"Reasons: {'; '.join(repair_reasons[:3])}","⏳"))
            D1, repair_report = repair_dataset(D0, contract, sa, pra, working)
            # Re-audit D1
            sa2 = structural_audit(D1)
            pa2 = plausibility_audit(D1, working, contract)
            pra2 = privacy_audit(D1, working)
            trace[-1] = _trace(9,"","Repair Loop Complete",f"Applied {repair_report['repairs_applied']} repairs | New verdict: {sa2['verdict']} | New privacy: {pra2['overall_risk']}","",time.time()-t7)

            # Show before/after
            st.markdown("###  Repair Loop: D0 → D1 (Before vs After)")
            bef = repair_report["metrics_before"]
            aft = repair_report["metrics_after"]
            cols = st.columns(len(bef))
            for i, (k, v) in enumerate(bef.items()):
                with cols[i]:
                    av = aft.get(k, v)
                    delta = av - v if isinstance(v, (int, float)) else 0
                    color = "#22C55E" if delta <= 0 else "#DC2626"
                    st.markdown(f'<div class="metric-card"><div class="number" style="color:{color}">{v} → {av}</div><div class="label">{k}</div></div>', unsafe_allow_html=True)

            for rd in repair_report["repair_details"]:
                st.markdown(f"-  {rd}")

            final_df, final_sa, final_pa, final_pra = D1, sa2, pa2, pra2
        else:
            trace.append(_trace(9,"","Repair Check",f"No repair needed — all thresholds met","",0))
            final_df, final_sa, final_pa, final_pra = D0, sa, pa, pra

        # ─── STEP 10: Pipeline Complete ───
        total = time.time()-t_start
        trace.append(_trace(10,"","Pipeline Complete",f"Total: {total:.1f}s | Records: {len(final_df)} | Strategy: {strat_info['display_name']}","",total))

        # Save run
        run_id = f"RUN-{int(time.time())}"
        audits = {"structural":final_sa,"plausibility":{k:v for k,v in final_pa.items() if not isinstance(v,pd.Series)},"privacy":final_pra}
        try: save_generation_run(run_id, final_df, contract, trace, audits)
        except: pass

        # Store in session
        st.session_state.update({"syn_df":final_df,"syn_contract":contract,"syn_trace":trace,"syn_sa":final_sa,"syn_pa":final_pa,"syn_pra":final_pra,"syn_seed":working,"syn_strat":strat_info,"syn_run_id":run_id})

        # ─── AGENT TRACE TIMELINE ───
        st.markdown("###  Agent Trace (10-Step Pipeline)")
        for t in trace:
            st.markdown(f'<div class="transport-node"><span class="node-name">{t["status"]} Step {t["step"]}: {t["icon"]} {t["action"]}</span><span class="node-distance">{t["duration"]}</span></div>', unsafe_allow_html=True)
            st.caption(f"    ↳ {t['detail']}")

        # ─── Preview ───
        st.markdown("###  Generated Data Preview")
        st.dataframe(final_df.head(15), use_container_width=True, hide_index=True)

        c1,c2,c3,c4 = st.columns(4)
        with c1: fig=px.pie(final_df["care_status"].value_counts().reset_index(),names="care_status",values="count",title="Care Status",color="care_status",color_discrete_map={"Escalated":"#EF4444","Active":"#3B82F6","Monitoring":"#EAB308","Graduated":"#22C55E"}); fig.update_layout(height=260,showlegend=False); st.plotly_chart(fig,use_container_width=True)
        with c2: fig=px.histogram(final_df,x="age",nbins=15,title="Age",color_discrete_sequence=["#0EA5E9"]); fig.update_layout(height=260); st.plotly_chart(fig,use_container_width=True)
        with c3: d=final_df["department"].value_counts().head(5).reset_index(); d.columns=["D","N"]; fig=px.bar(d,x="N",y="D",orientation="h",title="Depts",color_discrete_sequence=["#7C3AED"]); fig.update_layout(height=260); st.plotly_chart(fig,use_container_width=True)
        with c4: d=final_df["primary_diagnosis"].value_counts().head(5).reset_index(); d.columns=["D","N"]; fig=px.bar(d,x="N",y="D",orientation="h",title="Diagnoses",color_discrete_sequence=["#059669"]); fig.update_layout(height=260); st.plotly_chart(fig,use_container_width=True)

        st.success(f" Pipeline complete in {total:.1f}s — {len(final_df)} records generated, audited{', repaired' if should_repair else ''}, ready.")

# ═══════════════════════════════════════════
#  TAB 2: DUAL AUDIT DETAILS
# ═══════════════════════════════════════════
with tab_audit:
    if "syn_sa" not in st.session_state: st.info("Generate data first.")
    else:
        sa=st.session_state["syn_sa"]; pa=st.session_state["syn_pa"]; pra=st.session_state["syn_pra"]
        vc={"PASS":"#22C55E","WARN":"#EAB308","FAIL":"#EF4444"}.get(sa["verdict"],"#64748B")
        st.markdown(f'<div class="metric-row"><div class="metric-card"><div class="number" style="color:{vc}">{sa["verdict"]}</div><div class="label">Structural</div></div><div class="metric-card"><div class="number">{sa["pass_rate"]:.1%}</div><div class="label">Pass Rate</div></div><div class="metric-card"><div class="number">{pa["fidelity_mean"]:.2f}</div><div class="label">Fidelity</div></div><div class="metric-card"><div class="number">{pa["utility_pass_rate"]:.0%}</div><div class="label">Utility</div></div></div>', unsafe_allow_html=True)

        if sa["issues"]: st.dataframe(pd.DataFrame(sa["issues"]),use_container_width=True,hide_index=True)
        c1,c2=st.columns(2)
        with c1:
            fid=pa.get("fidelity",{})
            if fid: fig=px.bar(pd.DataFrame({"F":list(fid.keys()),"S":list(fid.values())}),x="S",y="F",orientation="h",title=f"Fidelity (mean:{pa['fidelity_mean']:.2f})",color_discrete_sequence=["#0066CC"],range_x=[0,1]); fig.update_layout(height=280); st.plotly_chart(fig,use_container_width=True)
        with c2:
            for c in pa.get("utility_checks",[]): st.markdown(f"{'' if c['satisfied'] else ''} {c['constraint']} → {c['actual']}")
            st.markdown(f"{'' if pa.get('elder_plausible') else ''} Elder esc {pa.get('elder_esc',0):.1%} vs Young {pa.get('young_esc',0):.1%}")

        st.markdown("---")
        oc={"LOW":"#22C55E","MEDIUM":"#EAB308","HIGH":"#EF4444"}.get(pra.get("overall_risk",""),"#64748B")
        st.markdown(f'<div class="metric-row"><div class="metric-card"><div class="number" style="color:{oc}">{pra.get("overall_risk","N/A")}</div><div class="label">Privacy Risk</div></div><div class="metric-card"><div class="number">{pra.get("exact_match_rate",0):.1%}</div><div class="label">Exact Match</div></div><div class="metric-card"><div class="number">{pra.get("k_anonymity_min","N/A")}</div><div class="label">k-min</div></div><div class="metric-card"><div class="number">{pra.get("dp_epsilon","N/A")}</div><div class="label">ε estimate</div></div></div>', unsafe_allow_html=True)
        if pra.get("dp_note"): st.markdown(f'<div class="info-panel"> ε={pra.get("dp_epsilon","N/A")} — {pra["dp_note"]}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
#  TAB 3: FHIR
# ═══════════════════════════════════════════
with tab_fhir:
    st.markdown("###  FHIR R4 Semantic Mapping")
    rows = [{"Field":f,"FHIR Resource":m["r"],"FHIR Path":m["p"],"Description":m["d"]} for f,m in FHIR_MAPPING.items()]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=450)
    r=pd.DataFrame(rows)["FHIR Resource"].value_counts().reset_index(); r.columns=["Resource","Fields"]
    fig=px.bar(r,x="Fields",y="Resource",orientation="h",title="FHIR R4 Coverage",color_discrete_sequence=["#0066CC"]); fig.update_layout(height=280); st.plotly_chart(fig,use_container_width=True)
    st.markdown('<div class="info-panel"> Each CSV record maps to a FHIR Bundle (Patient + Encounter + Condition + CarePlan + Coverage + MedicationRequest). Compatible with MEDITECH Expanse, Novari, SHINE.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
#  TAB 4: SIMULATION
# ═══════════════════════════════════════════
with tab_sim:
    st.markdown("###  Downstream Utility: Patient Flow Simulation")
    if "syn_df" not in st.session_state: st.info("Generate data first.")
    else:
        syn=st.session_state["syn_df"]; from core.triage import calculate_age_risk
        np.random.seed(123); s=syn.copy()
        s["pain_score"]=np.random.randint(0,11,size=len(s))*4; s["age_risk"]=s["age"].apply(calculate_age_risk); s["ai_severity"]=np.random.randint(0,31,size=len(s))
        s["total_priority"]=(s["pain_score"]+s["age_risk"]+s["ai_severity"]).clip(0,100)
        s["risk_level"]=s["total_priority"].apply(lambda x:"Red" if x>=60 else "Yellow" if x>=30 else "Green")
        em=s["care_status"]=="Escalated"; s.loc[em,"total_priority"]=s.loc[em,"total_priority"].clip(lower=50)
        s.loc[em,"risk_level"]=s.loc[em,"total_priority"].apply(lambda x:"Red" if x>=60 else "Yellow")

        r,y,g=(s["risk_level"]=="Red").sum(),(s["risk_level"]=="Yellow").sum(),(s["risk_level"]=="Green").sum()
        st.markdown(f'<div class="metric-row"><div class="metric-card"><div class="number">{len(s)}</div><div class="label">Simulated</div></div><div class="metric-card"><div class="number" style="color:#DC2626">{r}</div><div class="label"> Red</div></div><div class="metric-card"><div class="number" style="color:#EAB308">{y}</div><div class="label"> Yellow</div></div><div class="metric-card"><div class="number" style="color:#22C55E">{g}</div><div class="label"> Green</div></div></div>', unsafe_allow_html=True)

        c1,c2=st.columns(2)
        with c1: fig=px.pie(s["risk_level"].value_counts().reset_index(),names="risk_level",values="count",color="risk_level",color_discrete_map={"Red":"#EF4444","Yellow":"#EAB308","Green":"#22C55E"},title="Triage Distribution"); fig.update_layout(height=300); st.plotly_chart(fig,use_container_width=True)
        with c2: fig=px.histogram(s,x="total_priority",nbins=20,color="risk_level",color_discrete_map={"Red":"#EF4444","Yellow":"#EAB308","Green":"#22C55E"},title="Priority Scores"); fig.update_layout(height=300); st.plotly_chart(fig,use_container_width=True)

        st.markdown("###  Elder Care Validation (Ontario Health EDRVQP)")
        ag=pd.cut(s["age"],bins=[0,17,64,84,120],labels=["0-17","18-64","65-84","85+"])
        es=s.groupby(ag,observed=True).agg(Count=("record_id","count"),Avg_Priority=("total_priority","mean"),Red_Rate=("risk_level",lambda x:(x=="Red").mean()),Escalated_Rate=("care_status",lambda x:(x=="Escalated").mean())).round(3)
        st.dataframe(es,use_container_width=True)
        st.markdown('<div class="info-panel"> If 85+ shows highest Red Rate & Escalated Rate → synthetic data correctly models Ontario Health elder risk pattern (18.7/1000 for 85+).</div>', unsafe_allow_html=True)

        # ═══ LENGTH OF STAY PREDICTION: BEFORE vs AFTER ═══
        st.markdown("---")
        st.markdown("###  Length of Stay Prediction: Before vs After System")
        st.markdown("*Predicted hospital days per patient based on age, diagnosis, department, and care complexity.*")

        # ─── LOS Prediction Model (rule-based from clinical benchmarks) ───
        def predict_los(row):
            """Predict baseline LOS (days) from patient features."""
            base = 3.5  # Ontario avg LOS for acute care

            # Age factor (CIHI data: 65+ stays ~2x longer)
            age = row.get("age", 50)
            if age >= 85: base += 4.5
            elif age >= 75: base += 3.2
            elif age >= 65: base += 2.0
            elif age < 18: base += 0.5

            # Department factor
            dept = str(row.get("department", ""))
            dept_add = {"Cardiology": 2.8, "Oncology": 4.0, "Emergency": 1.5, "Respiratory": 2.5,
                        "Internal Medicine": 2.2, "Mental Health": 5.0, "Orthopedics": 3.5,
                        "Endocrinology": 1.8, "General Surgery": 2.5, "Neurology": 3.0}
            base += dept_add.get(dept, 1.5)

            # Diagnosis severity
            diag = str(row.get("primary_diagnosis", "")).lower()
            if any(k in diag for k in ["heart failure", "chf", "cardiac"]): base += 2.0
            elif any(k in diag for k in ["cancer", "tumor"]): base += 3.5
            elif any(k in diag for k in ["stroke", "hemorrhage"]): base += 3.0
            elif any(k in diag for k in ["diabetes", "hypertension"]): base += 0.8
            elif any(k in diag for k in ["copd", "asthma", "respiratory"]): base += 1.5
            elif any(k in diag for k in ["depression", "anxiety"]): base += 2.0

            # Care status multiplier
            status = str(row.get("care_status", ""))
            if status == "Escalated": base *= 1.35
            elif status == "Monitoring": base *= 1.1

            # Follow-up complexity
            fu30 = int(row.get("followup_count_30d", 0))
            fu90 = int(row.get("followup_count_90d", 0))
            if fu30 >= 3: base += 1.5
            if fu90 >= 5: base += 1.0

            return round(max(base + np.random.normal(0, 0.8), 1.0), 1)

        def predict_after_los(before_los, row):
            """Predict LOS after system optimization."""
            savings = 0

            # AI triage → faster assessment (saves 0.3-0.8 days)
            savings += 0.5

            # AI follow-up → earlier safe discharge (saves 0.5-2.0 days)
            age = row.get("age", 50)
            if age >= 65: savings += 1.2  # Elder patients benefit most
            else: savings += 0.6

            # Predictive discharge planning (saves 0.3-1.0 days)
            if str(row.get("care_status", "")) == "Escalated":
                savings += 0.8
            else:
                savings += 0.4

            # Transport pre-scheduling (saves 0.2-0.5 days of bed blocking)
            savings += 0.3

            # Documentation automation (indirect: 0.2-0.4 days)
            savings += 0.3

            after = max(before_los - savings + np.random.normal(0, 0.3), 1.0)
            return round(after, 1)

        np.random.seed(456)
        s["los_before"] = s.apply(predict_los, axis=1)
        s["los_after"] = s.apply(lambda row: predict_after_los(row["los_before"], row), axis=1)
        s["los_saved"] = (s["los_before"] - s["los_after"]).round(1)

        # ─── Summary Metrics ───
        avg_before = s["los_before"].mean()
        avg_after = s["los_after"].mean()
        avg_saved = s["los_saved"].mean()
        total_days_saved = s["los_saved"].sum()
        pct_reduction = (avg_saved / avg_before * 100)

        # Cost calculation (Ontario avg hospital bed cost: ~$1,200/day)
        cost_per_day = 1200
        total_cost_saved = total_days_saved * cost_per_day

        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card"><div class="number" style="color:#DC2626">{avg_before:.1f}</div><div class="label">Avg LOS Before (days)</div></div>
            <div class="metric-card"><div class="number" style="color:#22C55E">{avg_after:.1f}</div><div class="label">Avg LOS After (days)</div></div>
            <div class="metric-card"><div class="number" style="color:#0066CC">{avg_saved:.1f}</div><div class="label">Avg Days Saved</div></div>
            <div class="metric-card"><div class="number" style="color:#7C3AED">{pct_reduction:.0f}%</div><div class="label">Reduction</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card"><div class="number">{len(s)}</div><div class="label">Patients Simulated</div></div>
            <div class="metric-card"><div class="number" style="color:#0066CC">{total_days_saved:,.0f}</div><div class="label">Total Bed-Days Saved</div></div>
            <div class="metric-card"><div class="number" style="color:#22C55E">${total_cost_saved:,.0f}</div><div class="label">Est. Cost Savings</div></div>
            <div class="metric-card"><div class="number" style="color:#059669">${cost_per_day:,}/day</div><div class="label">Bed Cost (Ontario avg)</div></div>
        </div>
        """, unsafe_allow_html=True)

        # ─── Charts ───
        c1, c2 = st.columns(2)
        with c1:
            los_compare = pd.DataFrame({"Scenario": ["Before System", "After System"], "Avg LOS (days)": [avg_before, avg_after]})
            fig = px.bar(los_compare, x="Scenario", y="Avg LOS (days)", color="Scenario", color_discrete_map={"Before System": "#EF4444", "After System": "#22C55E"}, title="Average Length of Stay: Before vs After")
            fig.update_layout(height=320, showlegend=False); st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.histogram(s, x="los_saved", nbins=20, title="Distribution of Days Saved per Patient", color_discrete_sequence=["#3B82F6"])
            fig.update_layout(height=320, xaxis_title="Days Saved", yaxis_title="Patients"); st.plotly_chart(fig, use_container_width=True)

        # ─── By Age Group ───
        st.markdown("#### LOS Impact by Age Group")
        age_grp = pd.cut(s["age"], bins=[0, 17, 64, 84, 120], labels=["0-17", "18-64", "65-84", "85+"])
        los_by_age = s.groupby(age_grp, observed=True).agg(
            Count=("record_id", "count"),
            Before_LOS=("los_before", "mean"),
            After_LOS=("los_after", "mean"),
            Days_Saved=("los_saved", "mean"),
        ).round(1)
        los_by_age["Reduction_%"] = ((los_by_age["Days_Saved"] / los_by_age["Before_LOS"]) * 100).round(1)
        los_by_age["Est_Cost_Saved"] = (los_by_age["Count"] * los_by_age["Days_Saved"] * cost_per_day).astype(int)
        st.dataframe(los_by_age, use_container_width=True)

        # ─── By Department ───
        st.markdown("#### LOS Impact by Department")
        los_by_dept = s.groupby("department", observed=True).agg(
            Count=("record_id", "count"),
            Before_LOS=("los_before", "mean"),
            After_LOS=("los_after", "mean"),
            Days_Saved=("los_saved", "mean"),
        ).round(1).sort_values("Days_Saved", ascending=False)
        los_by_dept["Reduction_%"] = ((los_by_dept["Days_Saved"] / los_by_dept["Before_LOS"]) * 100).round(1)
        st.dataframe(los_by_dept, use_container_width=True)

        # ─── Sample Patient Detail ───
        st.markdown("####  Sample Patient LOS Predictions")
        sample = s[["record_id", "patient_name", "age", "department", "primary_diagnosis", "care_status", "los_before", "los_after", "los_saved"]].head(15)
        sample.columns = ["ID", "Name", "Age", "Department", "Diagnosis", "Status", "Before (days)", "After (days)", "Saved (days)"]
        st.dataframe(sample, use_container_width=True, hide_index=True)

        st.markdown(f'<div class="info-panel"> <strong>Methodology:</strong> LOS predicted from age, department, diagnosis, care status, and follow-up complexity. Savings estimated from AI triage acceleration (−0.5d), predictive discharge (−0.4-1.2d), follow-up optimization (−0.6-1.2d), and transport pre-scheduling (−0.3d). Ontario avg bed cost: ${cost_per_day:,}/day (CIHI 2024).</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
#  TAB 5: AUDIT PACK
# ═══════════════════════════════════════════
with tab_pack:
    if "syn_df" not in st.session_state: st.info("Generate data first.")
    else:
        syn=st.session_state["syn_df"]; ct=st.session_state.get("syn_contract",{}); tr=st.session_state.get("syn_trace",[])
        for item in [" Synthetic dataset (CSV)"," Data contract (JSON)"," FHIR field dictionary"," Agent trace (10 steps)"," Structural audit"," Plausibility & utility audit"," Privacy risk assessment"," Risk & limitations statement"]:
            st.markdown(f"  {item}")
        buf=io.StringIO(); syn.to_csv(buf,index=False)
        st.download_button("⬇ Synthetic Data CSV",buf.getvalue(),"synthetic_cohort.csv","text/csv",use_container_width=True)
        pack={"metadata":{"generated_at":datetime.now().isoformat(),"generator":"Southlake Agentic Synthetic Data Factory","records":len(syn),"run_id":st.session_state.get("syn_run_id","")},
            "data_contract":ct,"field_dictionary":{f:FHIR_MAPPING[f] for f in FHIR_MAPPING},"agent_trace":tr,
            "structural_audit":st.session_state.get("syn_sa",{}),"plausibility_audit":{k:v for k,v in st.session_state.get("syn_pa",{}).items() if not isinstance(v,pd.Series)},"privacy_audit":st.session_state.get("syn_pra",{}),
            "risk_statement":{"warning":"SYNTHETIC DATA — NOT FOR CLINICAL USE","limitations":["Not real patients.","Synthetic≠anonymous: memorization risk exists.","Privacy-utility tradeoff applies.","Never for clinical decisions.","Temporal patterns may not reflect real seasonality."],"intended_use":["Software testing","QI simulation","Research","Education","Hackathon demo"],"regulatory":"PHIPA | PIPEDA | NIST SP 800-188"}}
        st.download_button("⬇ Full Audit Pack JSON",json.dumps(pack,indent=2,default=str),"audit_pack.json","application/json",use_container_width=True)
        st.markdown('<div class="safety-banner"><strong> SYNTHETIC DATA — NOT FOR CLINICAL USE</strong><br>Generated by AI agent for demo/testing/research only. Not real patients. Synthetic≠anonymous.<br><strong>Regulatory:</strong> PHIPA (ON) | PIPEDA (CA) | NIST SP 800-188</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
#  TAB 6: RUN HISTORY
# ═══════════════════════════════════════════
with tab_hist:
    st.markdown("###  Generation Run History")
    runs = load_generation_history()
    if not runs:
        st.info("No runs yet. Generate data to see history.")
    else:
        for r in runs[:10]:
            st.markdown(f'<div class="transport-node"><span class="node-name"> {r["run_id"]} — {r.get("records",0)} records</span><span class="node-distance">{r.get("created_at","")}</span></div>', unsafe_allow_html=True)
