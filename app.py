import streamlit as st
from compliance_checker import check_feature # Import your updated backend logic
from database_utils import init_db, save_analysis, fetch_all_logs

# --- Page Configuration ---
st.set_page_config(
    page_title="RegTok - Automate Geo-Regulation with LLM to reduce your business overheads",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for Styling (No changes needed here) ---
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Title style */
    .title {
        font-family: 'monospace', sans-serif;
        color: #FF4B4B; /* TikTok red */
        text-align: center;
        padding: 20px;
        font-size: 3rem;
        font-weight: bold;
    }
    /* Subtitle style */
    .subtitle {
        text-align: center;
        color: #A0A0A0;
        margin-bottom: 30px;
    }
    /* Button style */
    .stButton>button {
        border-radius: 20px;
        border: 2px solid #FF4B4B;
        color: #FF4B4B;
        background-color: transparent;
        padding: 10px 25px;
        font-weight: bold;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }
    .stTextArea textarea {
        background-color: #161a25;
        border-radius: 10px;
    }
    /* Result card styling */
    .result-card {
        background-color: #161a25;
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid;
        margin-top: 20px;
    }
    .result-card-yes { border-color: #d9534f; }
    .result-card-no { border-color: #5cb85c; }
    .result-card-uncertain { border-color: #f0ad4e; }
    .result-card-error { border-color: #b0b0b0; }
</style>
""", unsafe_allow_html=True)


# --- UI Layout ---

st.markdown('<h1 class="title">⚖️ RegTok</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Automate Geo-Regulation to save on your business overheads</p>', unsafe_allow_html=True)
st.write("") 

# Input Area
feature_description = st.text_area(
    "Enter the feature description, PRD, or technical document text here:",
    height=150,
    placeholder="e.g., 'This feature reads user location to enforce France's copyright rules' or 'An age gate is required for users in Utah under 18.'"
)

# Button
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    check_button = st.button("Check Compliance", use_container_width=True)

st.write("")

# Create DB file on first run
init_db()


# --- Logic and Output ---
if check_button and feature_description:
    with st.spinner('Analyzing compliance requirements... This may take a moment.'):
        result = check_feature(feature_description)
        # Save result to DB right after getting it
        if result:
            save_analysis(result, feature_description)
    
    st.subheader("Analysis Result")

    flag = result.get("flag", "Error")
    reasoning = result.get("reasoning", "No reasoning provided.")
    regulations = result.get("related_regulations", [])
    # --- ADDITION: Get the thoughts from the result ---
    thought = result.get("thought")

    # Determine card style and icon based on flag
    if flag == "Yes":
        card_class = "result-card-yes"
        icon = "🚨"
        flag_text = "Compliance Logic Required"
    elif flag == "No":
        card_class = "result-card-no"
        icon = "✅"
        flag_text = "No Compliance Logic Required"
    elif flag == "Uncertain":
        card_class = "result-card-uncertain"
        icon = "❓"
        flag_text = "Uncertain - Human Review Needed"
    else: # Error
        card_class = "result-card-error"
        icon = "❌"
        flag_text = "Error During Analysis"

    # Display the result in our custom styled card
    st.markdown(f"""
    <div class="result-card {card_class}">
        <h3 style="margin-bottom: 15px;">{icon} Flag: {flag_text}</h3>
        <p><strong>Reasoning:</strong> {reasoning}</p>
    </div>
    """, unsafe_allow_html=True)

    # Display related regulations if any
    if regulations:
        st.info(f"**Potential Related Regulations:** {', '.join(regulations)}")
        
    # --- ADDITION: Display the thoughts in a clickable expander box ---
    if thought:
        with st.expander("Click to see the AI's thought process"):
            st.info(thought)

elif check_button and not feature_description:
    st.warning("Please enter a feature description to analyze.")

# --- ADDITION: Display the Audit Log at the bottom of the page ---
st.write("---")
st.subheader("📜 Analysis History (Audit Log)")

with st.spinner("Loading history..."):
    log_df = fetch_all_logs()

    if not log_df.empty:
        # Make the dataframe more human-readable
        display_df = log_df.rename(columns={
            'timestamp': 'Date & Time',
            'feature_description': 'Feature Description',
            'flag': 'Flag',
            'reasoning': 'Reasoning',
            'related_regulations': 'Related Regulations'
        })
        
        # Select the columns you want to show in the main view
        st.dataframe(
            display_df[['Date & Time', 'Feature Description', 'Flag', 'Reasoning', 'Related Regulations']],
            use_container_width=True,
            hide_index=True
        )

        # Optionally, show the detailed 'thought_process' in an expander
        with st.expander("Click here to see the full log with AI thought processes"):
             st.dataframe(log_df, use_container_width=True, hide_index=True)

    else:
        st.info("The audit log is currently empty. Run an analysis to populate it.")