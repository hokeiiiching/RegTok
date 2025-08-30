import streamlit as st
from compliance_checker import check_feature
from database_utils import init_db, save_analysis, fetch_all_logs, update_feedback, reset_database
import time

# --- 1. Page Configuration ---
# Set the configuration for the Streamlit page. This should be the first Streamlit
# command in the script. It defines the tab title, icon, layout, and sidebar state.
st.set_page_config(
    page_title="RegTok - Automate Geo-Regulation with LLM",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. Session State Initialization ---
# Initialize Streamlit's session state to manage variables across reruns.
# This is crucial for maintaining state, such as the most recent analysis result
# and UI visibility flags, as the user interacts with the application.
if 'last_result' not in st.session_state:
    st.session_state['last_result'] = None
if 'last_analysis_id' not in st.session_state:
    st.session_state['last_analysis_id'] = None
if 'show_correction_form' not in st.session_state:
    st.session_state['show_correction_form'] = False

# --- 3. Custom CSS for Styling ---
# Inject custom CSS to override default Streamlit styles for a more branded
# and polished user interface. Using `unsafe_allow_html=True` is necessary
# to render the raw HTML and CSS.
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
    /* Dynamically applied classes for result cards based on the AI's flag */
    .result-card-yes { border-color: #d9534f; } /* Red for "Yes" */
    .result-card-no { border-color: #5cb85c; } /* Green for "No" */
    .result-card-uncertain { border-color: #f0ad4e; } /* Yellow for "Uncertain" */
    .result-card-error { border-color: #b0b0b0; } /* Grey for "Error" */
</style>
""", unsafe_allow_html=True)


# --- 4. UI Layout ---

# Application header and title.
st.markdown('<h1 class="title">⚖️ RegTok</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Specialized LLM capabilities to flag features that require geo-specific logic, reducing your business overheads</p>', unsafe_allow_html=True)
st.write("") 

# Ensure the database is initialized on the first run of the application.
init_db()

# Main input area for the user to describe the product feature.
feature_description = st.text_area(
    "Enter the feature description, PRD, or technical document text here:",
    height=150,
    placeholder="e.g., 'This feature uses a user's location to enforce France's copyright rules' or 'An age gate is required for users in Utah under 18.'"
)

# Organize the main action button in the center column for better visual balance.
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    # This button triggers the core compliance analysis workflow.
    if st.button("Check Compliance", use_container_width=True):
        if feature_description:
            # Display a spinner to indicate that a process is running in the background.
            with st.spinner('Analyzing compliance and finding sources...'):
                result = check_feature(feature_description)
                log_id = save_analysis(result, feature_description)
                # Store the result and its database ID in the session state.
                # This makes the data available for display and feedback after Streamlit's rerun.
                st.session_state['last_result'] = result
                st.session_state['last_analysis_id'] = log_id
                st.session_state['show_correction_form'] = False
        else:
            st.warning("Please enter a feature description to analyze.")


# --- 5. Display Result and Human-in-the-Loop (HITL) Feedback Section ---

# This entire section is conditional and only renders if a result exists in the session state.
if st.session_state['last_result']:
    result = st.session_state['last_result']
    st.subheader("Analysis Result")

    # Unpack the analysis results from the dictionary with default fallbacks.
    flag = result.get("flag", "Error")
    reasoning = result.get("reasoning", "No reasoning provided.")
    regulations = result.get("related_regulations", [])
    thought = result.get("thought")
    expanded_query = result.get("expanded_query")
    citations = result.get("citations", [])

    # Map the AI's flag to specific display properties (CSS class, icon, text) for clarity.
    flag_map = {
        "Yes": {"class": "result-card-yes", "icon": "🚨", "text": "Compliance Logic Required"},
        "No": {"class": "result-card-no", "icon": "✅", "text": "No Compliance Logic Required"},
        "Uncertain": {"class": "result-card-uncertain", "icon": "❓", "text": "Uncertain - Human Review Needed"},
        "Error": {"class": "result-card-error", "icon": "❌", "text": "Error During Analysis"}
    }
    
    display_info = flag_map.get(flag, flag_map["Error"])

    # Display the primary result in a styled, color-coded card.
    st.markdown(f"""
    <div class="result-card {display_info['class']}">
        <h3 style="margin-bottom: 15px;">{display_info['icon']} Flag: {display_info['text']}</h3>
        <p><strong>Reasoning:</strong> {reasoning}</p>
    </div>
    """, unsafe_allow_html=True)

    # Display supplementary information from the analysis below the main result card.
    if citations:
        st.info(f"**🔗 Source Citations:** {', '.join(citations)}")

    if expanded_query and expanded_query.lower() != feature_description.lower():
        st.info(f"**🤖 Expanded Query:** The initial query was expanded for better analysis:\n\n> {expanded_query}")

    if regulations:
        st.info(f"**📜 Potential Related Regulations:** {', '.join(regulations)}")
        
    if thought:
        with st.expander("Click to see the AI's thought process"):
            st.info(thought)

    # --- Human-in-the-Loop (HITL) Feedback UI ---
    # This section allows users to approve or correct the AI's analysis,
    # providing valuable data for fine-tuning and evaluation.
    st.write("---")
    st.markdown("#### Is this analysis correct?")
    
    feedback_cols = st.columns(8)
    with feedback_cols[0]:
        if st.button("✔️ Approve"):
            update_feedback(st.session_state['last_analysis_id'], status='approved')
            st.success("Feedback saved! Analysis has been approved.")
            # Clear the session state and rerun to reset the UI to its initial state.
            st.session_state['last_result'] = None
            st.session_state['last_analysis_id'] = None
            st.rerun()

    with feedback_cols[1]:
        if st.button("✏️ Edit"):
            # Set a flag in session state to reveal the correction form.
            st.session_state['show_correction_form'] = True

    # The correction form is conditionally displayed based on the session state flag.
    if st.session_state.get('show_correction_form'):
        # Using `st.form` groups inputs and requires a single submit button,
        # preventing the app from rerunning on every widget interaction.
        with st.form("correction_form"):
            st.warning("Please provide the correct analysis.")
            corrected_flag = st.selectbox(
                "Correct Flag:",
                options=["Yes", "No", "Uncertain"],
                index=["Yes", "No", "Uncertain"].index(flag) if flag in ["Yes", "No", "Uncertain"] else 0
            )
            corrected_reasoning = st.text_area(
                "Correct Reasoning:"
            )
            
            submitted = st.form_submit_button("Submit Correction")
            if submitted:
                update_feedback(
                    st.session_state['last_analysis_id'],
                    status='corrected',
                    corrected_flag=corrected_flag,
                    corrected_reasoning=corrected_reasoning
                )
                st.success("Thank you! Your correction has been saved.")
                # Clear session state and rerun to reset the UI.
                st.session_state['last_result'] = None
                st.session_state['last_analysis_id'] = None
                st.session_state['show_correction_form'] = False
                st.rerun()


# --- 6. Audit Log Display ---
# This section provides a historical log of all past analyses and their feedback status.
st.write("---")

# Use columns to align the header and the reset button neatly.
log_header_cols = st.columns([3, 1])
with log_header_cols[0]:
    st.subheader("📜 Analysis History (Audit Log)")
with log_header_cols[1]:
    # This button allows for a complete reset of the application's data.
    if st.button("🗑️ Clear History", use_container_width=True):
        reset_database()
        # Also clear session memory to remove the currently displayed result card.
        st.session_state['last_result'] = None
        st.session_state['last_analysis_id'] = None
        st.session_state['show_correction_form'] = False
        st.success("Audit log and session memory cleared!")
        time.sleep(1) # A short pause allows the user to read the success message.
        st.rerun()

# Display the log data fetched from the database in a table.
with st.spinner("Loading history..."):
    log_df = fetch_all_logs()

    if not log_df.empty:
        # `st.dataframe` provides an interactive table.
        st.dataframe(
            log_df,
            use_container_width=True,
            hide_index=True,
            # `column_config` is used to customize the display of specific columns.
            column_config={
                "timestamp": st.column_config.DatetimeColumn(
                    "Timestamp",
                    format="YYYY-MM-DD HH:mm:ss",
                ),
                "original_query": "Original Query",
                "flag": "AI Flag",
                "reasoning": "AI Reasoning",
                "status": "Review Status",
                "human_feedback": "Human Feedback",
                "citations": "Source Citations",
                "related_regulations": "Related Regulations"
            }
        )
    else:
        st.info("The audit log is currently empty. Run an analysis to populate it.")