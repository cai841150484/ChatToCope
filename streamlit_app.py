import streamlit as st  
import json            
import pandas as pd    
from openai import OpenAI
import os             

# -------------------------------
# Cache data loading functions
# Use Streamlit's caching to avoid reloading data on every interaction, improving performance.
# -------------------------------
@st.cache_data # Decorator to cache the output of this function
def load_json(path):
    # Opens and reads a JSON file, returning its content as a Python dictionary or list.
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data # Decorator to cache the output of this function
def load_hotline(path):
    # Reads hotline data from a CSV file into a pandas DataFrame.
    df = pd.read_csv(path)
    # Cleans column names: removes leading/trailing whitespace and converts to lowercase.
    df.columns = df.columns.str.strip().str.lower()
    # Cleans the 'type' column if it exists: removes whitespace and converts to lowercase.
    if 'type' in df.columns:
        df['type'] = df['type'].str.strip().str.lower()
    return df

# -------------------------------
# Define constants for file paths
# Makes the code cleaner and easier to manage if file locations change.
# -------------------------------
DATA_DIR              = "Data" # Directory containing all data files
# Construct full paths to each data file using os.path.join for cross-platform compatibility.
SYMPTOM_ONTOLOGY_PATH = os.path.join(DATA_DIR, "symptom_ontology.json")
COPING_SKILLS_PATH    = os.path.join(DATA_DIR, "coping_skills.json")
HOTLINE_PATH          = os.path.join(DATA_DIR, "Hotline_Warmline_Data.csv")
SCHIZO_PATH           = os.path.join(DATA_DIR, "schizophrenia spectrum and other psychotic disorders.json")
DEPRESS_PATH          = os.path.join(DATA_DIR, "depressive disorders.json")
BIPOLAR_PATH          = os.path.join(DATA_DIR, "bipolar and related disorders.json")
GLOSSARY_PATH         = os.path.join(DATA_DIR, "glossary of technical terms.json")

# -------------------------------
# Utility Functions
# Helper functions to perform specific tasks within the app logic.
# -------------------------------
def extract_symptoms(user_input, symptom_list):
    # Finds symptoms from the predefined 'symptom_list' that are mentioned in the 'user_input'.
    # Comparison is case-insensitive.
    return [sym for sym in symptom_list if sym.lower() in user_input.lower()]

def get_symptom_tags(symptoms, ontology):
    # Looks up identified 'symptoms' in the 'ontology' dictionary
    # and collects all associated tags into a set (to avoid duplicates), then returns as a list.
    tags = set()
    for sym in symptoms:
        tags.update(ontology.get(sym, [])) # .get(sym, []) avoids errors if a symptom isn't in the ontology
    return list(tags)

def match_skills(tags, skill_list):
    # Finds coping skills from the 'skill_list' whose tags overlap with the input 'tags'.
    matches = []
    for skill in skill_list:
        # Checks for intersection between the skill's tags and the user's symptom tags.
        if set(skill.get("tags", [])) & set(tags):
            matches.append(skill)
    return matches

def detect_crisis(text):
    # Checks if the input 'text' contains any predefined crisis keywords.
    # Used to determine if emergency resources (hotlines) should be prioritized.
    crisis_keywords = ["suicide", "kill myself", "hurt myself", "ending my life"]
    # Returns True if any keyword is found (case-insensitive), False otherwise.
    return any(word in text.lower() for word in crisis_keywords)

# -------------------------------
# Load Data at startup
# Loads all necessary data files using the cached functions defined earlier.
# -------------------------------
symptom_ontology  = load_json(SYMPTOM_ONTOLOGY_PATH) # Maps symptoms to tags
coping_skills     = load_json(COPING_SKILLS_PATH)    # List of coping skills with descriptions and tags
schizo_data       = load_json(SCHIZO_PATH)           # Glossary specific to schizophrenia spectrum disorders
depressive_data   = load_json(DEPRESS_PATH)          # Glossary specific to depressive disorders
bipolar_data      = load_json(BIPOLAR_PATH)          # Glossary specific to bipolar and related disorders
glossary          = load_json(GLOSSARY_PATH)         # General glossary of technical terms
hotline_df        = load_hotline(HOTLINE_PATH)       # DataFrame containing hotline and warmline information

# -------------------------------
# Streamlit UI Setup
# Configures the web application's appearance and initial state.
# -------------------------------
st.title("💬 Chat to Cope") # Sets the main title of the app
st.write( # Displays introductory text to the user
    "You can input your current troubles or feelings, "
    "and we will identify possible symptoms for you and recommend suitable coping strategies and resources."
)

# Manage OpenAI API Key using Streamlit's session state to persist it across interactions.
if "api_key" not in st.session_state:
    st.session_state.api_key = "" # Initialize if not already set

# Only ask for the API key if it hasn't been provided yet.
if not st.session_state.api_key:
    openai_api_key = st.text_input("🔐 Enter your OpenAI API Key", type="password") # Password input for security
    if openai_api_key:
        st.session_state.api_key = openai_api_key # Store the key in session state
        st.rerun()  # Rerun the script to update the UI (hide input box, enable chat)
else:
    # If the API key is available, initialize the OpenAI client.
    client = OpenAI(api_key=st.session_state.api_key)

    # Initialize chat history in session state if it doesn't exist.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display past messages from the chat history.
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): # Display messages with appropriate sender icon (user/assistant)
            st.markdown(msg["content"]) # Render message content (supports Markdown)

    # Handle new user input via the chat input box at the bottom.
    if prompt := st.chat_input("What is up?"):
        # 1. Save and display the user's new message.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Perform local analysis based on user input.
        # Combine keys from all disorder glossaries and the symptom ontology into one master list for matching.
        SYMPTOM_LIST = list(
            set(symptom_ontology.keys()) |
            set(schizo_data.keys()) |
            set(depressive_data.keys()) |
            set(bipolar_data.keys())
        )
        # Format the general glossary for inclusion in the GPT prompt.
        glossary_str = "\n".join(f"- {k}: {v}" for k, v in list(glossary.items()))
        # Extract potential symptoms mentioned by the user.
        symptoms          = extract_symptoms(prompt, SYMPTOM_LIST)
        # Get associated tags for the extracted symptoms.
        tags              = get_symptom_tags(symptoms, symptom_ontology)
        # Find coping skills relevant to the identified tags.
        recommended_skills = match_skills(tags, coping_skills)

        # 3. Select appropriate resource type (Hotline vs. Warmline).
        if detect_crisis(prompt):
            # If crisis keywords are detected, filter for hotlines.
            df = hotline_df[hotline_df["type"] == "hotline"]
        else:
            # Otherwise, filter for warmlines (less urgent support).
            df = hotline_df[hotline_df["type"] == "warmline"]

        # 4. Construct the prompts for the OpenAI API call.
        # System prompt defines the AI's role, personality, and provides general context (glossary).
        system_prompt = (
            "You are a compassionate mental health assistant. "
            "Here are definitions of technical terms you might use:\n"
             f"{glossary_str}\n\n"
            "Given the user's emotional concerns and any identified symptoms, "
            "explain the issues in gentle language, then introduce 2–3 coping strategies clearly, "
            "and end with an encouraging, warm tone."
        )
        # Format the recommended skills for the prompt. Limit to top 3.
        skills_text = "\n".join(
            f"- {s['skill']}: {s['description']}" for s in recommended_skills[:3]
        ) or "No specific skills matched." # Provide fallback text if no skills match.

        # Get definitions for the specific symptoms detected in the user's input.
        explanatory_defs = "\n".join([
            f"- {sym}: {schizo_data.get(sym) or depressive_data.get(sym) or bipolar_data.get(sym)}"
            for sym in symptoms
            # Only include definitions if found in one of the disorder glossaries.
            if schizo_data.get(sym) or depressive_data.get(sym) or bipolar_data.get(sym)
        ])

        # User prompt combines the user's message with the results of the local analysis.
        user_prompt = f"""
        The user said: "{prompt}"

        Detected symptoms: {', '.join(symptoms) if symptoms else 'None'}

        Definitions:
        {explanatory_defs}

        Recommended coping skills:
        {skills_text}
        """
        # Structure the messages for the OpenAI API (system role + user role).
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        # 5. Call the OpenAI API to generate the assistant's response.
        completion = client.chat.completions.create(
            model="gpt-4.1", # Specify the GPT model to use
            messages=messages # Pass the constructed messages
        )
        # Extract the text content from the API response.
        gpt_response = completion.choices[0].message.content.strip()

        # 6. Append resource information if needed.
        # Add hotline/warmline info if crisis detected OR if specific symptoms were locally identified.
        if detect_crisis(prompt) or symptoms:
            # Select the first available resource from the filtered DataFrame.
            resource = df.iloc[0].to_dict() if not df.empty else {"name": "No resource available", "phone number": ""}
            # Combine the GPT response with the resource information.
            full_response = (
                gpt_response
                + f"\n\n### 📞 Suggested Resource:\n{resource['name']} – {resource['phone number']}"
            )
        else:
            # If no crisis or specific symptoms, just use the GPT response.
            full_response = gpt_response

        # 7. Display the assistant's final response and save it to chat history.
        with st.chat_message("assistant"):
            st.markdown(full_response) # Display the response in the chat interface
        st.session_state.messages.append({"role": "assistant", "content": full_response}) # Add to history