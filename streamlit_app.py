import streamlit as st  
import json            
import pandas as pd    
from openai import OpenAI
import os     
import textwrap        

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
FINAL_DSM5_PATH       = os.path.join(DATA_DIR, "final_DSM-5_data.json")  # New: Combined DSM-5 data file
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
    """Legacy function, kept for backward compatibility"""
    crisis_keywords = ["suicide", "kill myself", "hurt myself", "ending my life"]
    return any(word in text.lower() for word in crisis_keywords)

# -------------------------------
# Load Data at startup
# Loads all necessary data files using the cached functions defined earlier.
# -------------------------------
symptom_ontology  = load_json(SYMPTOM_ONTOLOGY_PATH) # Maps symptoms to tags
coping_skills     = load_json(COPING_SKILLS_PATH)    # List of coping skills with descriptions and tags
final_dsm5_data   = load_json(FINAL_DSM5_PATH)       # Use combined DSM-5 data file
glossary          = load_json(GLOSSARY_PATH)         # General glossary of technical terms
hotline_df        = load_hotline(HOTLINE_PATH)       # DataFrame containing hotline and warmline information

# Pre-build: symptom list and glossary string
SYMPTOM_LIST = list(set(symptom_ontology.keys()) | set(final_dsm5_data.keys()))
glossary_str = "\n".join(f"- {k}: {v}" for k, v in glossary.items())

# -------------------------------
# Streamlit UI Setup
# Configures the web application's appearance and initial state.
# -------------------------------
st.title("💬 Chat to Cope") # Sets the main title of the app
st.write( # Displays introductory text to the user
    "You can enter your current concerns or feelings, "
    "we will identify potential symptoms and recommend appropriate coping strategies and resources."
)

# Manage OpenAI API Key using Streamlit's session state to persist it across interactions.
if "api_key" not in st.session_state:
    st.session_state.api_key = "" # Initialize if not already set

# Add a session state variable to track if we offered a resource
if "resource_offered" not in st.session_state:
    st.session_state.resource_offered = None

# Only ask for the API key if it hasn't been provided yet.
if not st.session_state.api_key:
    openai_api_key = st.text_input("🔐 Please enter your OpenAI API key", type="password") # Password input box for secure input
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
    if prompt := st.chat_input("What would you like to say?"):
        # 1. Save and display the user's new message.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Check if this is a response to a previous resource offer
        resource_requested = False
        if st.session_state.resource_offered and prompt.lower() in ["yes", "yeah", "sure", "okay", "ok"]:
            # User confirmed they want the resource
            resource_requested = True
            resource_type = st.session_state.resource_offered
        
        else:
            # Modified: Skip local crisis detection and delegate the assessment to the LLM
            # First extract symptoms for skill recommendation
            symptoms = extract_symptoms(prompt, SYMPTOM_LIST)
            tags = get_symptom_tags(symptoms, symptom_ontology)
            recommended_skills = match_skills(tags, coping_skills)
            
            # Initial resource type is none - let LLM decide later
            resource_type = "none"
        
        # 4. Use a preliminary system prompt to evaluate crisis level
        preliminary_system_prompt = textwrap.dedent(f"""
            You are a mental health professional who evaluates the severity of crisis situations.
            You need to analyze the following user message and determine if it represents:
            1) A crisis situation (suicidal ideation, self-harm, immediate danger) - respond with "hotline"
            2) Significant mental health symptoms but no immediate danger - respond with "warmline" 
            3) General concerns with no acute symptoms - respond with "none"
            
            ONLY respond with one word: "hotline", "warmline", or "none".
            Err on the side of caution - if there's any hint of suicidal thoughts or self-harm, choose "hotline".
            """)
            
        preliminary_messages = [
            {"role": "system", "content": preliminary_system_prompt},
            {"role": "user", "content": f"Analyze this message for crisis indicators: \"{prompt}\""}
        ]
            
        # First call to determine resource type
        with st.spinner("Analyzing message..."):
            preliminary_completion = client.chat.completions.create(
                model="gpt-4.1",
                messages=preliminary_messages,
                max_tokens=10  # Short response to save tokens
            )
        
        llm_resource_type = preliminary_completion.choices[0].message.content.strip().lower()
        
        # Validate the response and update resource_type if valid
        if llm_resource_type in ["hotline", "warmline", "none"]:
            resource_type = llm_resource_type
        
        # Now proceed with getting resource information if needed
        resource_info = {}
        if resource_type in ("hotline", "warmline"):
            df_res = hotline_df[hotline_df["type"] == resource_type]
            if not df_res.empty:
                row = df_res.iloc[0]
                resource_info = {
                    "name": row.get("name", ""),
                    "phone": row.get("phone number", ""),
                    "description": row.get("description", "") if "description" in row else ""
                }
            
                # Track that we offered this resource
                st.session_state.resource_offered = resource_type
                
                # If this was a direct request for the resource, make sure to include it
                if resource_requested:
                    resource_instruction = f"""
                    3) CRITICAL: The user has confirmed they want the resource information.
                    You MUST provide the following resource information clearly in your reply:
                    Resource name: {resource_info["name"]}
                    Phone number: {resource_info["phone"]}
                    {f'Description: {resource_info["description"]}' if resource_info.get("description") else ''}
                    """
                else:
                    # Regular resource offering
                    resource_instruction = f"""
                    3) IMPORTANT: You MUST incorporate the following resource information into your reply:
                    Resource name: {resource_info["name"]}
                    Phone number: {resource_info["phone"]}
                    {f'Description: {resource_info["description"]}' if resource_info.get("description") else ''}
                    
                    Include the phone number in your response. Format it naturally but ensure it appears clearly.
                    """

        system_prompt = textwrap.dedent(f"""
            You are a compassionate mental health assistant.
            Here are the definitions of technical terms you might use:
            {glossary_str}

            Guidelines:
            1) Respond in a warm tone, using 2-3 DSM-5 terms to describe coping strategies.
            2) Format your response with proper paragraphs - use a new paragraph for each distinct point or idea.
            3) Keep paragraphs short and readable (3-5 sentences maximum per paragraph).
            4) Determine resource_type:
               - If there is self-harm or suicide risk, choose "hotline"
               - If there are significant symptoms but no self-harm risk, choose "warmline"
               - Otherwise, choose "none"
            {resource_instruction if resource_info else ""}
            
            Please **only** return a JSON object in the following format:
            {{
              "reply": "...your well-formatted reply with proper paragraph breaks (include the resource information naturally if provided)...",
              "resource_type": "hotline|warmline|none"
            }}
            """)

        # Format skill recommendations and symptom definitions
        skills_text = "\n".join(
            f"- {s['skill']}: {s['description']}" for s in recommended_skills[:3]
        ) or "No specific coping skills matched."

        explanatory_defs = "\n".join([
            f"- {sym}: {final_dsm5_data.get(sym)}"
            for sym in symptoms
            if final_dsm5_data.get(sym)
        ])

        # User prompt
        user_prompt = f"""
        User says: "{prompt}"

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

        # 5. Call OpenAI to get a response
        with st.spinner("Generating response, please wait..."):
            completion = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages
            )
        raw = completion.choices[0].message.content.strip()
        
        # 6. Parse JSON output
        try:
            result = json.loads(raw)
            full_response = result.get("reply", raw)  # Use the complete reply generated by the LLM (including resource information)
            resource_type = result.get("resource_type", "none")
        except json.JSONDecodeError:
            full_response = raw
            resource_type = "none"
        
        # No longer need to manually append resource information, as the LLM has incorporated it into the reply
        
        # 7. Display and store
        with st.chat_message("assistant"):
            st.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})