# 🧬 Southlake Agentic Synthetic Data Factory

By Qi Sun and Jia An  
Advisor: Kaiyu Li  

Ivey × Southlake Health Hackathon 2026  

Hackathon project focused on AI-driven healthcare workflows, structured data integration, and prototype system development. The team’s participation was recognized through a follow-up $2,500 scholarship opportunity from Ivey MSc.

> An agentic synthetic data creation and validation service for healthcare — built for the Ivey × Southlake Health Hackathon 2026.

**One-liner:** Turn natural language requirements into auditable, FHIR-mapped healthcare datasets — and prove they work through real hospital operation simulations.

## Core Features

| Feature | Description |
|---------|-------------|
| **Synthetic Data Agent** | 10-step agentic pipeline: NL → Contract → Strategy → Generate → Audit → Repair → Pack |
| **Data Contract Builder** | GPT-4o-mini parses natural language into structured schema, constraints, quality targets |
| **Strategy Selector** | Agent chooses generation method based on constraints (Blender / Distribution / Lifecycle) |
| **Cohort Blender** | Constraint-weighted resampling with hard constraints (escalation rate) + soft constraints |
| **Dual Audit** | Pass 1: Structural (schema, temporal, enum). Pass 2: Plausibility + privacy (k-anonymity, ε, membership) |
| **Repair Loop** | Auto-fix temporal inconsistencies, escalation drift, near-duplicates. Before/after metrics |
| **FHIR R4 Mapping** | 20 fields mapped to HL7 FHIR resources (Patient, Encounter, Condition, CarePlan, etc.) |
| **Simulation Validation** | Generated cohorts run through triage/follow-up/transport engines to prove downstream utility |
| **Audit Pack Export** | CSV + contract + FHIR dictionary + trace + 3 audit reports + risk statement |

## Quick Start

```bash
pip install -r requirements.txt

# Set API keys
export OPENAI_API_KEY="sk-..."       # Contract generation + Live Doctor
export ANTHROPIC_API_KEY="sk-ant-..." # Triage/FollowUp AI modules

streamlit run app.py
```

## Accounts

| Account | Password | Access |
|---------|----------|--------|
| `admin123` | `admin123` | **Synthetic Data Agent** (main demo) |
| `admin` | `admin` | Simulation & Validation workspace |
| `user1/2/3` | `123456` | Downstream patient simulation modules |

## Architecture

```
Layer 1: CORE — Synthetic Data Agent (the product)
  NL Input → Data Contract → Strategy Selection → Cohort Blender
  → Structural Audit → Plausibility Audit → Privacy Audit
  → Repair Loop → FHIR Mapping → Audit Pack

Layer 2: VALIDATION — Downstream Simulation (proves utility)
  Registration Simulation | Triage Validator | Follow-Up Simulation
  Queue Stress Test | Operations Validation

Layer 3: CONTEXT — Southlake's Real Problems
  $14.8M deficit | 63% labour costs | Aging population
  ED overcrowding | Unsafe discharge | DHN transition
```

## Project Structure

```
southlake/
├── app.py                              # Login + navigation router
├── core/
│   ├── synth_contract.py               # NL → data contract
│   ├── synth_strategy.py               # Strategy selection with reasoning
│   ├── synth_repair.py                 # Audit repair loop (D0→D1)
│   ├── triage.py                       # Triage scoring (simulation engine)
│   ├── followup.py / routing.py / transport.py / queue_manager.py
├── utils/
│   ├── ai_client.py                    # Claude + GPT-4o-mini clients
│   ├── auth.py / storage.py / styles.py / chat_store.py
├── views/
│   ├── 10_🧬_Synthetic_Data_Agent.py   # MAIN: Agentic pipeline
│   ├── 1-4: Patient simulation modules
│   ├── 5-9: Validation & stress test modules
├── data/
│   ├── patient_records.csv             # 3,000-record seed dataset
│   ├── runs/                           # Generation run history
```
## Demo Video

Project demo videos are available in the Releases section:

- Demo 1
- Demo 2

## Safety & Compliance

- ⚠️ **Synthetic ≠ Anonymous** — model memorization can leak data. Always audit.
- ⚠️ **Privacy-Utility Tradeoff** — more noise = better privacy, worse fidelity.
- ⚠️ **Never for Clinical Decisions** — testing, training, simulation only.
- 📋 **Regulatory:** PHIPA (Ontario) | PIPEDA (Canada) | NIST SP 800-188
