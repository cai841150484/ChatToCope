# 🧠 Chat to Cope: An AI-Powered Mental Health Assistant

**Chat to Cope** is a clinically grounded, context-aware conversational AI system designed to support early psychosis recovery. It delivers empathetic interactions, interprets user-reported symptoms, recommends coping strategies, and escalates crisis situations when necessary.

Built with **Streamlit**, powered by **OpenAI GPT-4.1**, and enriched by structured data from **DSM-5**, the **EPPIC Recovery Handbook**, and verified **hotline/warmline** contacts.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

---

## 💡 Key Features

- **🧠 Symptom Recognition**  
  Detects and categorizes symptoms using DSM-5 and a semantic symptom ontology.

- **🛠️ Coping Skill Recommendation**  
  Matches symptoms to relevant strategies from the EPPIC Recovery Handbook.

- **🚨 Crisis Detection & Escalation**  
  Uses GPT-4.1 to assess urgency and provide appropriate hotline/warmline resources.

- **💬 Empathetic AI Interaction**  
  GPT-4.1 generates context-sensitive, psychologically grounded support replies.

---

## 📁 Dataset Overview

| File                                | Description                                                         |
|-------------------------------------|---------------------------------------------------------------------|
| `final_DSM-5_data.json`             | Standardized DSM-5 symptom definitions                              |
| `symptom_ontology.json`             | Maps symptoms to semantic tags (e.g., cognitive, affective)         |
| `glossary of technical terms.json`  | Definitions of psychiatric terms used in LLM system prompts         |
| `coping_skills.json`                | Structured coping strategies from the EPPIC Recovery Handbook       |
| `Hotline_Warmline_Data.csv`         | Verified national crisis hotline and peer warmline contact data     |

---
### How to run it on your own machine

1. Install the requirements
   ```
   $ pip install -r requirements.txt
   ```
3. Run the app
   ```
   $ streamlit run streamlit_app.py
   ```
