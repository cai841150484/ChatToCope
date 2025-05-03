# 🧠 Chat to Cope: An AI-Powered Mental Health Assistant

A clinically grounded, context-sensitive conversational AI system designed to support early psychosis recovery through empathetic interaction, symptom interpretation, coping skill guidance, and crisis escalation.  
Built with **Streamlit**, powered by **OpenAI GPT-4.1**, and enriched by structured datasets from **DSM-5**, the **EPPIC Recovery Handbook**, and verified **hotline/warmline** resources.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

---

## 💡 Key Features

- **Symptom Recognition**  
  Extracts and categorizes mental health symptoms using DSM-5 and a semantic symptom ontology.

- **Coping Skill Matching**  
  Recommends evidence-based recovery strategies tailored to user symptoms, sourced from the EPPIC Recovery Handbook.

- **Crisis Triage & Escalation**  
  Detects urgent situations and suggests hotline or warmline resources for immediate or peer-based support.

- **Empathetic AI Response**  
  Uses OpenAI GPT-4.1 to generate supportive, personalized responses in a safe and structured format.

---

## 📁 Dataset Structure

- `final_DSM-5_data.json` – Standardized DSM-5 symptom definitions  
- `symptom_ontology.json` – Semantic mapping of symptoms to tags (e.g., cognitive, affective)  
- `glossary of technical terms.json` – Definitions of psychiatric terms for model grounding  
- `coping_skills.json` – Structured coping strategies annotated with tags  
- `Hotline_Warmline_Data.csv` – Verified mental health crisis contacts (hotlines and warmlines)

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/chat-to-cope.git
cd chat-to-cope
