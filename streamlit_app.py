import streamlit as st
import json
import pandas as pd
from openai import OpenAI
import os

# -------------------------------
# Cache data loading functions
# -------------------------------
@st.cache_data
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def load_hotline(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    if 'type' in df.columns:
        df['type'] = df['type'].str.strip().str.lower()
    return df

# -------------------------------
# File paths
# -------------------------------
DATA_DIR              = "Data"
SYMPTOM_ONTOLOGY_PATH = os.path.join(DATA_DIR, "symptom_ontology.json")
COPING_SKILLS_PATH    = os.path.join(DATA_DIR, "coping_skills.json")
HOTLINE_PATH          = os.path.join(DATA_DIR, "Hotline_Warmline_Data.csv")
SCHIZO_PATH           = os.path.join(DATA_DIR, "schizophrenia spectrum and other psychotic disorders.json")
DEPRESS_PATH          = os.path.join(DATA_DIR, "depressive disorders.json")
BIPOLAR_PATH          = os.path.join(DATA_DIR, "bipolar and related disorders.json")
GLOSSARY_PATH         = os.path.join(DATA_DIR, "glossary of technical terms.json")

# -------------------------------
# Utility Functions
# -------------------------------
def extract_symptoms(user_input, symptom_list):
    return [sym for sym in symptom_list if sym.lower() in user_input.lower()]

def get_symptom_tags(symptoms, ontology):
    tags = set()
    for sym in symptoms:
        tags.update(ontology.get(sym, []))
    return list(tags)

def match_skills(tags, skill_list):
    matches = []
    for skill in skill_list:
        if set(skill.get("tags", [])) & set(tags):
            matches.append(skill)
    return matches

def detect_crisis(text):
    crisis_keywords = ["suicide", "kill myself", "hurt myself", "ending my life"]
    return any(word in text.lower() for word in crisis_keywords)

# -------------------------------
# Load Data
# -------------------------------
symptom_ontology = load_json(SYMPTOM_ONTOLOGY_PATH)
coping_skills     = load_json(COPING_SKILLS_PATH)
schizo_data       = load_json(SCHIZO_PATH)
depressive_data   = load_json(DEPRESS_PATH)
bipolar_data      = load_json(BIPOLAR_PATH)
glossary          = load_json(GLOSSARY_PATH)
hotline_df        = load_hotline(HOTLINE_PATH)

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("💬 Chat to Cope")
st.write(
    "You can input your current troubles or feelings, "
    "and we will identify possible symptoms for you and recommend suitable coping strategies and resources."
)

# Store API key in session state after user inputs it once
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if not st.session_state.api_key:
    openai_api_key = st.text_input("🔐 Enter your OpenAI API Key", type="password")
    if openai_api_key:
        st.session_state.api_key = openai_api_key
        st.rerun()  # Refresh the UI to hide input box
else:
    client = OpenAI(api_key=st.session_state.api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # New user input
    if prompt := st.chat_input("What is up?"):
        # Save and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 1. Local symptom matching (optional)
        SYMPTOM_LIST = list(
            set(symptom_ontology.keys()) |
            set(schizo_data.keys()) |
            set(depressive_data.keys()) |
            set(bipolar_data.keys())
        )
        glossary_str = "\n".join(f"- {k}: {v}" for k, v in list(glossary.items()))
        symptoms          = extract_symptoms(prompt, SYMPTOM_LIST)
        tags              = get_symptom_tags(symptoms, symptom_ontology)
        recommended_skills = match_skills(tags, coping_skills)

        # 2. Choose resource type based on crisis keywords
        if detect_crisis(prompt):
            df = hotline_df[hotline_df["type"] == "hotline"]
        else:
            df = hotline_df[hotline_df["type"] == "warmline"]

        # 3. Build GPT context
        system_prompt = (
            "You are a compassionate mental health assistant. "
            "Here are definitions of technical terms you might use:\n"
             f"{glossary_str}\n\n"
            "Given the user's emotional concerns and any identified symptoms, "
            "explain the issues in gentle language, then introduce 2–3 coping strategies clearly, "
            "and end with an encouraging, warm tone."
        )
        skills_text = "\n".join(
            f"- {s['skill']}: {s['description']}" for s in recommended_skills[:3]
        ) or "No specific skills matched."

        explanatory_defs = "\n".join([
            f"- {sym}: {schizo_data.get(sym) or depressive_data.get(sym) or bipolar_data.get(sym)}"
            for sym in symptoms
            if schizo_data.get(sym) or depressive_data.get(sym) or bipolar_data.get(sym)
        ])

        user_prompt = f"""
        The user said: "{prompt}"

        Detected symptoms: {', '.join(symptoms) if symptoms else 'None'}

        Definitions:
        {explanatory_defs}

        Recommended coping skills:
        {skills_text}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        # 4. Call OpenAI to complete the conversation
        completion = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages
        )
        gpt_response = completion.choices[0].message.content.strip()

        # 5. Decide whether to append resources based on "detect_crisis or locally detected symptoms"
        if detect_crisis(prompt) or symptoms:
            resource = df.iloc[0].to_dict() if not df.empty else {"name": "No resource available", "phone number": ""}
            full_response = (
                gpt_response
                + f"\n\n### 📞 Suggested Resource:\n{resource['name']} – {resource['phone number']}"
            )
        else:
            full_response = gpt_response

        # 6. Display and save assistant reply
        with st.chat_message("assistant"):
            st.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})