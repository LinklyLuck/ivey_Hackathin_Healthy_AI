import streamlit as st
import pandas as pd
from datetime import datetime
from utils.styles import inject_css
from utils.storage import load_patients, append_row_csv, get_next_id, now_str
from utils.ai_client import ai_extract_registration

inject_css()

st.markdown("""
<div class="hero-card" style="background: linear-gradient(135deg, #0052A5 0%, #2563EB 100%);">
    <h1> AI-Assisted Registration</h1>
    <p>Reduce front-desk administrative burden by converting conversational input into structured patient records.</p>
</div>
""", unsafe_allow_html=True)

if "ai_extracted" not in st.session_state:
    st.session_state.ai_extracted = None

tab1, tab2 = st.tabs([" AI-Assisted Entry", " Manual Form"])

with tab1:
    st.markdown("""
    <div class="info-panel">
         <strong>How it works:</strong> Type your information naturally — the AI will extract structured fields automatically.
        You can review and edit before submitting.
    </div>
    """, unsafe_allow_html=True)

    user_input = st.text_area(
        "Tell us about yourself (name, date of birth, contact info, insurance, allergies, medical history):",
        placeholder="Example: My name is John Smith, born March 15 1965. My phone is 905-555-1234 and email john@email.com. I live at 42 Main St, Newmarket ON. I have OHIP, number 1234-567-890. I'm allergic to penicillin. I have a history of high blood pressure and type 2 diabetes. My emergency contact is Jane Smith at 905-555-5678.",
        height=150,
    )

    if st.button(" Extract with AI", type="primary") and user_input.strip():
        with st.spinner("AI is analyzing your input..."):
            result = ai_extract_registration(user_input)
        if result:
            st.session_state.ai_extracted = result
            if result.get("response_message"):
                st.info(result["response_message"])
        else:
            st.warning("AI extraction unavailable. Please use the Manual Form tab.")

    if st.session_state.ai_extracted:
        data = st.session_state.ai_extracted
        st.markdown("### Review Extracted Information")

        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=data.get("full_name") or "", key="ai_name")
            dob = st.date_input("Date of Birth", value=None, key="ai_dob")
            phone = st.text_input("Phone", value=data.get("phone") or "", key="ai_phone")
            email = st.text_input("Email", value=data.get("email") or "", key="ai_email")
            address = st.text_input("Address", value=data.get("address") or "", key="ai_addr")
        with col2:
            ins_types = ["OHIP", "UHIP", "Other"]
            ins_val = data.get("insurance_type", "OHIP")
            ins_idx = ins_types.index(ins_val) if ins_val in ins_types else 0
            insurance_type = st.selectbox("Insurance Type", ins_types, index=ins_idx, key="ai_ins_type")
            insurance_number = st.text_input("Insurance Number", value=data.get("insurance_number") or "", key="ai_ins_num")
            allergies = st.text_area("Allergies", value=data.get("allergies") or "None", key="ai_allergy", height=68)
            pmh = st.text_area("Past Medical History", value=data.get("past_medical_history") or "None", key="ai_pmh", height=68)
            emergency_contact = st.text_input("Emergency Contact", value=data.get("emergency_contact") or "", key="ai_emerg")

        missing = data.get("missing_fields", [])
        if missing:
            st.warning(f" Missing fields: {', '.join(missing)}")

        consent = st.checkbox("I consent that this system is for information collection and workflow support only.", key="ai_consent")

        if st.button(" Confirm & Register", type="primary", key="ai_submit"):
            if not consent:
                st.error("Please provide consent.")
            elif not full_name:
                st.error("Full name is required.")
            else:
                pid = get_next_id("P", "patients.csv", "patient_id")
                try:
                    age = (datetime.now() - pd.to_datetime(dob)).days // 365
                except:
                    age = 0
                row = {
                    "patient_id": pid, "full_name": full_name, "dob": dob, "age": age,
                    "phone": phone, "email": email, "address": address,
                    "insurance_type": insurance_type, "insurance_number": insurance_number,
                    "allergies": allergies, "past_medical_history": pmh,
                    "emergency_contact": emergency_contact, "emergency_phone": "",
                    "registered_at": now_str(),
                }
                append_row_csv("patients.csv", row)
                st.success(f" Registration successful! Patient ID: **{pid}**")
                st.session_state.ai_extracted = None

with tab2:
    with st.form("manual_registration"):
        col1, col2 = st.columns(2)
        with col1:
            m_name = st.text_input("Full Name *")
            m_dob = st.date_input("Date of Birth *", value=datetime(1990, 1, 1), min_value=datetime(1920, 1, 1))
            m_phone = st.text_input("Phone Number *")
            m_email = st.text_input("Email")
            m_address = st.text_input("Address")
        with col2:
            m_ins_type = st.selectbox("Insurance Type", ["OHIP", "UHIP", "Other"])
            m_ins_num = st.text_input("Insurance Number")
            m_allergies = st.text_area("Known Allergies", value="None", height=68)
            m_pmh = st.text_area("Past Medical History", value="None", height=68)
            m_emerg = st.text_input("Emergency Contact (Name & Phone)")
        m_consent = st.checkbox("I consent that this system is for information collection and workflow support only.")
        m_submit = st.form_submit_button("Register Patient", type="primary")

    if m_submit:
        if not m_consent:
            st.error("Please provide consent.")
        elif not m_name:
            st.error("Full name is required.")
        else:
            pid = get_next_id("P", "patients.csv", "patient_id")
            age = (datetime.now() - datetime.combine(m_dob, datetime.min.time())).days // 365
            row = {
                "patient_id": pid, "full_name": m_name, "dob": m_dob.strftime("%Y-%m-%d"), "age": age,
                "phone": m_phone, "email": m_email, "address": m_address,
                "insurance_type": m_ins_type, "insurance_number": m_ins_num,
                "allergies": m_allergies, "past_medical_history": m_pmh,
                "emergency_contact": m_emerg, "emergency_phone": "", "registered_at": now_str(),
            }
            append_row_csv("patients.csv", row)
            st.success(f" Registration successful! Patient ID: **{pid}**")
