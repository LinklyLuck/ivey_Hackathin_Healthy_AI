"""
Southlake — AI Client (DeepSeek unified)
All AI calls go through DeepSeek API (OpenAI-compatible).
"""
import json
import os
import streamlit as st
from openai import OpenAI

# ═══════════════════════════════════════════
#  PUT YOUR API KEY HERE
# ═══════════════════════════════════════════
API_KEY = "sk-b2529389ef1544708fd9804ab0f521ca"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
# ═══════════════════════════════════════════

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str | None:
    """Call AI for structured tasks (registration, triage, followup, summary)."""
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.warning(f"AI API call failed: {e}. Using rule-based fallback.")
        return None


# ──────────────────────────────────────────────
#  MODULE A: AI-Assisted Registration
# ──────────────────────────────────────────────

REGISTRATION_SYSTEM = """You are a friendly hospital registration assistant at Southlake Regional Health Centre in Newmarket, Ontario. 
Your job is to help patients complete their registration by extracting structured information from their natural language input.

IMPORTANT RULES:
- You are NOT a doctor. Never provide medical advice.
- Be warm, professional, and concise.
- If the patient provides information, extract it. If info is missing, ask for it politely.
- Always respond in English.

Output a JSON object with these fields (use null for missing):
{
  "full_name": string,
  "dob": string (YYYY-MM-DD),
  "phone": string,
  "email": string,
  "address": string,
  "insurance_type": "OHIP" | "UHIP" | "Other",
  "insurance_number": string,
  "allergies": string,
  "past_medical_history": string,
  "emergency_contact": string,
  "missing_fields": [list of fields still needed],
  "response_message": string (friendly message to patient)
}"""


def ai_extract_registration(user_input: str) -> dict | None:
    """Extract registration fields from natural language input."""
    result = _call_claude(
        REGISTRATION_SYSTEM,
        f"Patient says: {user_input}\n\nExtract all available registration information and identify what's still missing.",
    )
    if result is None:
        return None
    try:
        # Try to parse JSON from response
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ──────────────────────────────────────────────
#  MODULE B: Emergency Pre-Triage AI Questioning
# ──────────────────────────────────────────────

TRIAGE_SYSTEM = """You are a medical intake AI assistant at Southlake Regional Health Centre Emergency Department.
Your job is to ask structured follow-up questions based on the patient's chief complaint to help the triage team.

IMPORTANT RULES:
- You are NOT making a diagnosis. You are collecting information for the triage nurse.
- Ask 5-7 focused yes/no or numeric questions relevant to the complaint.
- Include pain scale (0-10) if applicable.
- Flag any potential red-flag symptoms.
- Be empathetic but efficient.

Output a JSON object:
{
  "symptom_category": string (e.g., "cardiac", "respiratory", "musculoskeletal", "dermatology", "abdominal", "mental_health", "neurology", "infection", "urology", "general"),
  "suggested_department": string,
  "questions": [
    {"id": "q1", "text": string, "type": "yes_no" | "scale_0_10" | "duration" | "text"},
    ...
  ],
  "red_flags_detected": [list of concerning symptoms mentioned],
  "initial_assessment": string (brief clinical note for triage nurse)
}"""


def ai_generate_triage_questions(chief_complaint: str, age: int, medical_history: str = "") -> dict | None:
    """Generate intelligent triage questions based on complaint."""
    prompt = f"""Patient Information:
- Age: {age}
- Chief Complaint: {chief_complaint}
- Past Medical History: {medical_history if medical_history else "Not provided"}

Generate appropriate triage follow-up questions."""
    
    result = _call_claude(TRIAGE_SYSTEM, prompt)
    if result is None:
        return None
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ──────────────────────────────────────────────
#  MODULE C: Smart Follow-Up Questionnaire Generation
# ──────────────────────────────────────────────

FOLLOWUP_SYSTEM = """You are a follow-up care AI assistant at Southlake Regional Health Centre.
Your job is to generate a personalized follow-up questionnaire based on the patient's discharge summary.

IMPORTANT RULES:
- Generate 5-8 questions that directly relate to the discharge instructions and diagnosis.
- Focus on measurable indicators (vital signs, symptom changes, medication compliance, wound healing, activity level).
- Be patient-friendly in language.
- DO NOT include pain scale (0-10) questions — this is already asked by default in the system.
- DO NOT include generic questions about pain levels — focus on condition-specific follow-up.

Output a JSON object:
{
  "questionnaire_title": string,
  "questions": [
    "Question 1 text here?",
    "Question 2 text here?",
    ...
  ],
  "monitoring_summary": string (brief note about what to watch for)
}

Each question must be a plain text string, NOT a nested object."""


def ai_generate_followup_questionnaire(discharge_summary: str, diagnosis: str, medications: str) -> dict | None:
    """Generate personalized follow-up questions from discharge summary."""
    prompt = f"""Discharge Summary:
- Diagnosis: {diagnosis}
- Medications: {medications}
- Instructions: {discharge_summary}

Generate a personalized follow-up questionnaire for the patient's post-discharge check-in."""
    
    result = _call_claude(FOLLOWUP_SYSTEM, prompt, max_tokens=1500)
    if result is None:
        return None
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ──────────────────────────────────────────────
#  MODULE D: Clinical Summary Generation
# ──────────────────────────────────────────────

SUMMARY_SYSTEM = """You are a clinical documentation AI at Southlake Regional Health Centre.
Your job is to create a concise, structured clinical summary for the receiving physician.

IMPORTANT:
- Use professional medical terminology.
- Be concise and factual.
- Never make a diagnosis — only summarize collected information.
- Flag red-flag symptoms prominently.

Output a JSON object:
{
  "clinical_summary": string (2-3 sentence structured summary),
  "key_findings": [list of important findings],
  "red_flags": [list of red-flag symptoms if any],
  "recommended_urgency": "Non-urgent" | "Semi-urgent" | "Urgent" | "Emergency",
  "handoff_note": string (brief note for the next clinician)
}"""


def ai_generate_clinical_summary(
    patient_name: str,
    age: int,
    chief_complaint: str,
    answers: dict,
    medical_history: str = "",
) -> dict | None:
    """Generate a clinical summary for doctor handoff."""
    prompt = f"""Patient: {patient_name}, Age: {age}
Chief Complaint: {chief_complaint}
Past Medical History: {medical_history if medical_history else "Not provided"}
Collected Answers: {json.dumps(answers, indent=2)}

Generate a clinical summary for the receiving physician."""
    
    result = _call_claude(SUMMARY_SYSTEM, prompt)
    if result is None:
        return None
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ──────────────────────────────────────────────
#  MODULE E: Follow-Up Risk Analysis
# ──────────────────────────────────────────────

RISK_ANALYSIS_SYSTEM = """You are a post-discharge risk analysis AI at Southlake Regional Health Centre.
Your job is to analyze a patient's follow-up questionnaire answers and provide a risk assessment.

IMPORTANT:
- Compare answers against discharge parameters and normal ranges.
- Identify concerning trends.
- Recommend specific actions for the clinical team.
- Never make a final clinical decision — recommend review.

Output a JSON object:
{
  "risk_assessment": string (2-3 sentence analysis),
  "concerning_findings": [list of specific concerns],
  "risk_level": "Green" | "Yellow" | "Red",
  "confidence": "High" | "Medium" | "Low",
  "recommended_actions": [list of specific action items],
  "escalation_reason": string (if Red, explain why)
}"""


def ai_analyze_followup_risk(
    diagnosis: str,
    discharge_instructions: str,
    followup_answers: dict,
) -> dict | None:
    """Analyze follow-up answers and assess risk level."""
    prompt = f"""Original Diagnosis: {diagnosis}
Discharge Instructions: {discharge_instructions}
Patient Follow-Up Answers: {json.dumps(followup_answers, indent=2)}

Analyze the patient's current status and assess risk level."""
    
    result = _call_claude(RISK_ANALYSIS_SYSTEM, prompt)
    if result is None:
        return None
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ──────────────────────────────────────────────
#  Fallback rule-based functions
# ──────────────────────────────────────────────

def fallback_triage_questions(chief_complaint: str) -> list[dict]:
    """Rule-based fallback for triage questions."""
    complaint = chief_complaint.lower()
    
    base_questions = [
        {"id": "pain", "text": "Rate your pain on a scale of 0-10", "type": "scale_0_10"},
    ]
    
    if any(w in complaint for w in ["leg", "knee", "bone", "sprain", "joint", "back"]):
        return base_questions + [
            {"id": "walk", "text": "Are you able to walk normally?", "type": "yes_no"},
            {"id": "swell", "text": "Is there visible swelling?", "type": "yes_no"},
            {"id": "injury", "text": "Was there a recent injury or fall?", "type": "yes_no"},
            {"id": "fever", "text": "Do you have a fever?", "type": "yes_no"},
            {"id": "duration", "text": "How long have you had this pain?", "type": "text"},
        ]
    elif any(w in complaint for w in ["chest", "heart", "palpitation"]):
        return base_questions + [
            {"id": "breath", "text": "Are you having difficulty breathing?", "type": "yes_no"},
            {"id": "sweat", "text": "Are you experiencing cold sweats?", "type": "yes_no"},
            {"id": "arm", "text": "Is the pain radiating to your arm, jaw, or back?", "type": "yes_no"},
            {"id": "sudden", "text": "Did the symptoms come on suddenly?", "type": "yes_no"},
            {"id": "history", "text": "Do you have a history of heart disease?", "type": "yes_no"},
        ]
    elif any(w in complaint for w in ["breath", "cough", "wheeze"]):
        return base_questions + [
            {"id": "rest_breath", "text": "Are you short of breath at rest?", "type": "yes_no"},
            {"id": "lie_flat", "text": "Can you lie flat without difficulty?", "type": "yes_no"},
            {"id": "fever", "text": "Do you have a fever?", "type": "yes_no"},
            {"id": "sputum", "text": "Are you coughing up phlegm? What color?", "type": "text"},
            {"id": "oxygen", "text": "Do you have a pulse oximeter reading?", "type": "text"},
        ]
    elif any(w in complaint for w in ["rash", "skin", "itch"]):
        return base_questions + [
            {"id": "itch", "text": "Is the rash itchy?", "type": "yes_no"},
            {"id": "spread", "text": "Is it spreading?", "type": "yes_no"},
            {"id": "fever", "text": "Do you have a fever?", "type": "yes_no"},
            {"id": "discharge", "text": "Is there any discharge or oozing?", "type": "yes_no"},
            {"id": "new_exposure", "text": "Any new medications, foods, or products recently?", "type": "yes_no"},
        ]
    elif any(w in complaint for w in ["stomach", "abdomen", "nausea", "vomit"]):
        return base_questions + [
            {"id": "location", "text": "Where exactly is the pain?", "type": "text"},
            {"id": "nausea", "text": "Are you experiencing nausea or vomiting?", "type": "yes_no"},
            {"id": "fever", "text": "Do you have a fever?", "type": "yes_no"},
            {"id": "appetite", "text": "Have you lost your appetite?", "type": "yes_no"},
            {"id": "blood", "text": "Is there any blood in your stool?", "type": "yes_no"},
        ]
    elif any(w in complaint for w in ["anxiety", "depression", "panic", "mental", "stress"]):
        return [
            {"id": "frequency", "text": "How often are you experiencing these symptoms?", "type": "text"},
            {"id": "sleep", "text": "Is your sleep affected?", "type": "yes_no"},
            {"id": "appetite", "text": "Has your appetite changed?", "type": "yes_no"},
            {"id": "work", "text": "Is it affecting your daily activities or work?", "type": "yes_no"},
            {"id": "support", "text": "Do you have a support system (family, friends)?", "type": "yes_no"},
            {"id": "safety", "text": "Do you feel safe?", "type": "yes_no"},
        ]
    else:
        return base_questions + [
            {"id": "duration", "text": "How long have you had this symptom?", "type": "text"},
            {"id": "daily", "text": "Is it affecting your daily activities?", "type": "yes_no"},
            {"id": "worse", "text": "Has it been getting worse?", "type": "yes_no"},
            {"id": "fever", "text": "Do you have a fever?", "type": "yes_no"},
            {"id": "conditions", "text": "Do you have any pre-existing conditions?", "type": "yes_no"},
        ]


def fallback_department(chief_complaint: str) -> str:
    """Rule-based department routing fallback."""
    from utils.constants import SYMPTOM_CATEGORIES
    complaint = chief_complaint.lower()
    for cat_key, cat in SYMPTOM_CATEGORIES.items():
        for kw in cat["keywords"]:
            if kw.lower() in complaint:
                return cat["department"]
    return "Emergency"


# ──────────────────────────────────────────────
#  GPT-4o-mini Live Doctor Chat
# ──────────────────────────────────────────────

def call_gpt_chat(system_prompt: str, messages: list[dict], max_tokens: int = 600) -> str | None:
    """Call AI for live doctor chat."""
    try:
        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            role = "user" if m["role"] in ("user", "patient") else "assistant"
            api_messages.append({"role": role, "content": m["content"]})
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.warning(f"AI chat error: {e}")
        return None


def gpt_generate_report(system_prompt: str, user_prompt: str) -> str | None:
    """Call AI for structured report/contract generation."""
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.warning(f"AI report error: {e}")
        return None
