import streamlit as st
from compliance_checker import check_feature
# --- MODIFIED: Import the new reset function ---
from database_utils import init_db, save_analysis, fetch_all_logs, update_feedback, reset_database
import time

# --- Page Configuration (no changes) ---
st.set_page_config(
    page_title="RegTok - Automate Geo-Regulation with LLM",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Session State and CSS (no changes) ---
if 'last_result' not in st.session_state:
    st.session_state['last_result'] = None
if 'last_analysis_id' not in st.session_state:
    st.session_state['last_analysis_id'] = None
if 'show_correction_form' not in st.session_state:
    st.session_state['show_correction_form'] = False

st.markdown("""
<style>
    /* (CSS is unchanged) */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .title { font-family: 'monospace', sans-serif; color: #FF4B4B; text-align: center; padding: 20px; font-size: 3rem; font-weight: bold; }
    .subtitle { text-align: center; color: #A0A0A0; margin-bottom: 30px; }
    .stButton>button { border-radius: 20px; border: 2px solid #FF4B4B; color: #FF4B4B; background-color: transparent; padding: 10px 25px; font-weight: bold; transition: all 0.3s ease-in-out; }
    .stButton>button:hover { background-color: #FF4B4B; color: white; border-color: #FF4B4B; }
    .stTextArea textarea { background-color: #161a25; border-radius: 10px; }
    .result-card { background-color: #161a25; padding: 25px; border-radius: 15px; border-left: 5px solid; margin-top: 20px; }
    .result-card-yes { border-color: #d9534f; }
    .result-card-no { border-color: #5cb85c; }
    .result-card-uncertain { border-color: #f0ad4e; }
    .result-card-error { border-color: #b0b0b0; }
</style>
""", unsafe_allow_html=True)

# --- UI Layout (no changes until the audit log section) ---
st.markdown('<h1 class="title">⚖️ RegTok</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Automate Geo-Regulation to save on your business overheads</p>', unsafe_allow_html=True)
st.write("") 

init_db()

feature_description = st.text_area(
    "Enter the feature description, PRD, or technical document text here:",
    height=150,
    placeholder="e.g., 'This feature uses a user's location to enforce France's copyright rules' or 'An age gate is required for users in Utah under 18.'"
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button("Check Compliance", use_container_width=True):
        if feature_description:
            with st.spinner('Analyzing compliance requirements...'):
                result = check_feature(feature_description)
                log_id = save_analysis(result, feature_description)
                st.session_state['last_result'] = result
                st.session_state['last_analysis_id'] = log_id
                st.session_state['show_correction_form'] = False
        else:
            st.warning("Please enter a feature description to analyze.")

# --- Display Result and HITL (no changes) ---
if st.session_state['last_result']:
    result = st.session_state['last_result']
    st.subheader("Analysis Result")

    flag = result.get("flag", "Error")
    reasoning = result.get("reasoning", "No reasoning provided.")
    regulations = result.get("related_regulations", [])
    thought = result.get("thought")
    expanded_query = result.get("expanded_query")

    flag_map = {
        "Yes": {"class": "result-card-yes", "icon": "🚨", "text": "Compliance Logic Required"},
        "No": {"class": "result-card-no", "icon": "✅", "text": "No Compliance Logic Required"},
        "Uncertain": {"class": "result-card-uncertain", "icon": "❓", "text": "Uncertain - Human Review Needed"},
        "Error": {"class": "result-card-error", "icon": "❌", "text": "Error During Analysis"}
    }
    display_info = flag_map.get(flag, flag_map["Error"])

    st.markdown(f"""
    <div class="result-card {display_info['class']}">
        <h3 style="margin-bottom: 15px;">{display_info['icon']} Flag: {display_info['text']}</h3>
        <p><strong>Reasoning:</strong> {reasoning}</p>
    </div>
    """, unsafe_allow_html=True)

    if expanded_query and expanded_query.lower() != feature_description.lower():
        st.info(f"**🤖 Expanded Query:** {expanded_query}")

    if regulations:
        st.info(f"**📜 Potential Related Regulations:** {', '.join(regulations)}")
        
    if thought:
        with st.expander("Click to see the AI's thought process"):
            st.info(thought)

    st.write("---")
    st.markdown("#### Is this analysis correct?")
    
    feedback_cols = st.columns(8)
    with feedback_cols[0]:
        if st.button("✔️ Approve"):
            update_feedback(st.session_state['last_analysis_id'], status='approved')
            st.success("Feedback saved! Analysis has been approved.")
            st.session_state['last_result'] = None
            st.session_state['last_analysis_id'] = None
            st.rerun()

    with feedback_cols[1]:
        if st.button("✏️ Edit"):
            st.session_state['show_correction_form'] = True

    if st.session_state.get('show_correction_form'):
        with st.form("correction_form"):
            st.warning("Please provide the correct analysis.")
            corrected_flag = st.selectbox("Correct Flag:", options=["Yes", "No", "Uncertain"], index=["Yes", "No", "Uncertain"].index(flag) if flag in ["Yes", "No", "Uncertain"] else 0)
            corrected_reasoning = st.text_area("Correct Reasoning:")
            
            submitted = st.form_submit_button("Submit Correction")
            if submitted:
                update_feedback(st.session_state['last_analysis_id'], status='corrected', corrected_flag=corrected_flag, corrected_reasoning=corrected_reasoning)
                st.success("Thank you! Your correction has been saved.")
                st.session_state['last_result'] = None
                st.session_state['last_analysis_id'] = None
                st.session_state['show_correction_form'] = False
                st.rerun()

# --- MODIFIED AUDIT LOG DISPLAY SECTION ---
st.write("---")

# Use columns to place the title and reset button on the same line
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("📜 Analysis History (Audit Log)")
with col2:
    if st.button("🗑️ Clear History", use_container_width=True):
        # 1. Call the function to reset the database
        reset_database()
        
        # 2. Clear the current session memory to remove any displayed result card
        st.session_state['last_result'] = None
        st.session_state['last_analysis_id'] = None
        st.session_state['show_correction_form'] = False
        
        # 3. Show a confirmation message
        st.success("Audit log and session memory cleared!")
        
        # 4. Pause briefly so the user can see the message, then rerun the app
        time.sleep(1)
        st.rerun()

# The rest of the log display logic is the same
with st.spinner("Loading history..."):
    log_df = fetch_all_logs()

    if not log_df.empty:
        st.dataframe(
            log_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm:ss"),
                "original_query": "Original Query",
                "flag": "AI Flag",
                "reasoning": "AI Reasoning",
                "status": "Review Status",
                "human_feedback": "Human Feedback"
            }
        )
    else:
        st.info("The audit log is currently empty. Run an analysis to populate it.")