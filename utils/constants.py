"""
Southlake Medical AI Agent — Constants & Configuration
"""

# ─── Transport Pickup Nodes ───
TRANSPORT_NODES = [
    {"name": "The Roxborough", "distance": "Across from hospital, walking distance", "drive_min": 1, "lat": 44.0570, "lng": -79.4615},
    {"name": "Southlake Care Village", "distance": "3 min drive", "drive_min": 3, "lat": 44.0530, "lng": -79.4580},
    {"name": "Amica Newmarket", "distance": "10 min drive", "drive_min": 10, "lat": 44.0445, "lng": -79.4720},
    {"name": "Sunrise of Aurora", "distance": "15 min drive", "drive_min": 15, "lat": 44.0065, "lng": -79.4505},
    {"name": "Delmanor Aurora", "distance": "20 min drive", "drive_min": 20, "lat": 43.9945, "lng": -79.4625},
]

SOUTHLAKE_HOSPITAL = {"name": "Southlake Regional Health Centre", "lat": 44.0592, "lng": -79.4613}

# ─── Departments ───
DEPARTMENTS = [
    "Internal Medicine",
    "General Surgery",
    "Orthopedics",
    "Dermatology",
    "Cardiology / Emergency",
    "Mental Health",
    "Emergency",
    "Respirology",
    "Urology",
    "Neurology / Stroke",
]

# ─── Risk Levels ───
RISK_COLORS = {
    "Green": "#28a745",
    "Yellow": "#ffc107",
    "Red": "#dc3545",
}

# ─── Red-flag symptom keywords ───
RED_FLAG_KEYWORDS = [
    "chest pain with breathing difficulty",
    "severe shortness of breath",
    "stroke-like symptoms",
    "loss of consciousness",
    "uncontrolled bleeding",
    "high fever with altered mental status",
    "inability to bear weight after trauma",
    "sudden confusion",
    "facial droop",
    "sudden severe headache",
]

# ─── Age risk scoring table ───
AGE_RISK_TABLE = [
    (0, 17, 12),
    (18, 64, 8),
    (65, 74, 15),
    (75, 84, 22),
    (85, 120, 30),
]

# ─── Priority band thresholds ───
PRIORITY_GREEN_MAX = 29
PRIORITY_YELLOW_MAX = 59
# 60+ = Red

# ─── Follow-up risk thresholds ───
FOLLOWUP_GREEN_MAX = 19
FOLLOWUP_YELLOW_MAX = 49
# 50+ = Red

# ─── Symptom category templates for AI ───
SYMPTOM_CATEGORIES = {
    "cardiac": {
        "label": "Cardiac / Chest Pain",
        "keywords": ["chest", "heart", "palpitation", "angina"],
        "department": "Cardiology / Emergency",
    },
    "respiratory": {
        "label": "Respiratory",
        "keywords": ["breath", "cough", "wheeze", "asthma", "COPD"],
        "department": "Respirology",
    },
    "musculoskeletal": {
        "label": "Musculoskeletal / Orthopedic",
        "keywords": ["leg", "knee", "bone", "fracture", "sprain", "joint", "back pain", "shoulder"],
        "department": "Orthopedics",
    },
    "dermatology": {
        "label": "Skin / Dermatology",
        "keywords": ["rash", "skin", "itch", "lesion", "wound"],
        "department": "Dermatology",
    },
    "abdominal": {
        "label": "Abdominal / GI",
        "keywords": ["stomach", "abdomen", "nausea", "vomit", "diarrhea"],
        "department": "General Surgery",
    },
    "mental_health": {
        "label": "Mental Health",
        "keywords": ["anxiety", "depression", "panic", "mental", "stress", "sleep"],
        "department": "Mental Health",
    },
    "neurology": {
        "label": "Neurological",
        "keywords": ["headache", "dizziness", "numbness", "tingling", "confusion", "speech"],
        "department": "Neurology / Stroke",
    },
    "infection": {
        "label": "Infection / Fever",
        "keywords": ["fever", "infection", "sore throat", "flu"],
        "department": "Internal Medicine",
    },
    "urology": {
        "label": "Urological",
        "keywords": ["urine", "blood in urine", "urinary", "kidney"],
        "department": "Urology",
    },
}
