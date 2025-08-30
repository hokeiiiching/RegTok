import sqlite3
import datetime
import pandas as pd
import json

# --- Constants ---
# Defines the filename for the SQLite database.
DATABASE_NAME = "audit_log.db"

def init_db():
    """
    Initializes the database connection and creates the 'analysis_log' table if it doesn't exist.
    
    This function defines the schema for storing analysis results, including user queries,
    model outputs, status, and human feedback. It ensures the database is ready for logging.
    """
    conn = None # Initialize conn to None to ensure it's available in the finally block.
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        # The schema is defined with 'IF NOT EXISTS' to prevent errors on subsequent runs.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            original_query TEXT NOT NULL,
            expanded_query TEXT,
            flag TEXT,
            reasoning TEXT,
            related_regulations TEXT,
            thought_process TEXT,
            status TEXT NOT NULL,
            human_feedback_flag TEXT,
            human_feedback_reasoning TEXT,
            citations TEXT 
        )
        """)
        conn.commit()
        print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        # Ensure the database connection is always closed, even if errors occur.
        if conn:
            conn.close()

def save_analysis(result_dict: dict, original_query: str) -> int:
    """
    Saves the results of a single analysis to the 'analysis_log' table.

    Args:
        result_dict (dict): A dictionary containing the analysis output from the model.
        original_query (str): The user's original, unmodified query string.

    Returns:
        int: The ID of the newly inserted database row, or None if an error occurred.
    """
    last_id = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Prepare data for insertion, providing default values for missing keys.
        timestamp = datetime.datetime.now()
        flag = result_dict.get('flag', 'Error')
        reasoning = result_dict.get('reasoning', '')
        # Serialize list of regulations into a comma-separated string for DB storage.
        regulations = ", ".join(result_dict.get('related_regulations', []))
        thought = result_dict.get('thought', '')
        expanded_query = result_dict.get('expanded_query', original_query)
        status = 'pending_review' # All new entries require human review.
        # Serialize list of citations into a comma-separated string for DB storage.
        citations = ", ".join(result_dict.get('citations', []))
        
        cursor.execute("""
        INSERT INTO analysis_log (
            timestamp, original_query, expanded_query, flag, reasoning, 
            related_regulations, thought_process, status, citations
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, original_query, expanded_query, flag, reasoning, regulations, thought, status, citations))
        
        last_id = cursor.lastrowid # Retrieve the primary key of the new record.
        conn.commit()
        print(f"Successfully saved analysis (ID: {last_id}).")
    except sqlite3.Error as e:
        print(f"Failed to save analysis to database: {e}")
    finally:
        if conn:
            conn.close()
    return last_id

def fetch_all_logs() -> pd.DataFrame:
    """
    Fetches all records from the 'analysis_log' table and formats them into a pandas DataFrame.

    Returns:
        pd.DataFrame: A DataFrame containing the formatted log data, sorted by timestamp.
                      Returns an empty DataFrame on error or if no logs exist.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        # Fetch all data, ordering by the most recent entries first.
        df = pd.read_sql_query("SELECT * FROM analysis_log ORDER BY timestamp DESC", conn)

        # If the database is empty, return a correctly structured empty DataFrame.
        if df.empty:
            return pd.DataFrame(columns=[
                'timestamp', 'original_query', 'flag', 'reasoning', 
                'status', 'human_feedback', 'citations', 'related_regulations'
            ])

        # A helper function to derive a user-friendly feedback summary column.
        def determine_feedback(row):
            if row['status'] == 'approved': return 'Approved'
            elif row['status'] == 'corrected': return row['human_feedback_reasoning'] if pd.notna(row['human_feedback_reasoning']) else ''
            else: return ''
        df['human_feedback'] = df.apply(determine_feedback, axis=1)

        # Define a specific column order for consistent presentation in the UI.
        column_order = [
            'timestamp', 'original_query', 'flag', 'reasoning', 
            'status', 'human_feedback', 'citations', 'related_regulations'
        ]
        
        # Return only the specified columns in the desired order.
        return df[column_order]

    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"Error fetching logs from database: {e}")
        return pd.DataFrame() # Return an empty DataFrame on failure.
    finally:
        if conn:
            conn.close()

def update_feedback(log_id: int, status: str, corrected_flag: str = None, corrected_reasoning: str = None):
    """
    Updates a specific log entry with human-provided feedback.

    Args:
        log_id (int): The primary key of the log entry to update.
        status (str): The new status ('approved' or 'corrected').
        corrected_flag (str, optional): The corrected flag, if applicable.
        corrected_reasoning (str, optional): The corrected reasoning, if applicable.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE analysis_log 
        SET status = ?, human_feedback_flag = ?, human_feedback_reasoning = ?
        WHERE id = ?
        """, (status, corrected_flag, corrected_reasoning, log_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating feedback in database: {e}")
    finally:
        if conn: conn.close()
        
def fetch_corrected_examples(n_examples: int = 2) -> list:
    """
    Fetches a diverse set of human-corrected examples for use in few-shot prompting.
    
    This function retrieves the most recent 'corrected' entry for both 'Yes' and 'No' flags
    to provide the model with varied, high-quality examples.

    Args:
        n_examples (int): The number of diverse examples to fetch (currently hardcoded to 2).

    Returns:
        list: A list of formatted example dictionaries, ready for use in a prompt.
              Returns an empty list on error.
    """
    examples = []
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Query for the most recent corrected example where the human feedback was 'Yes'.
        cursor.execute("""
        SELECT original_query, human_feedback_flag, human_feedback_reasoning, related_regulations, citations
        FROM analysis_log
        WHERE status = 'corrected' AND human_feedback_flag = 'Yes'
        ORDER BY timestamp DESC
        LIMIT 1
        """)
        yes_example = cursor.fetchone()

        # Query for the most recent corrected example where the human feedback was 'No'.
        cursor.execute("""
        SELECT original_query, human_feedback_flag, human_feedback_reasoning, related_regulations, citations
        FROM analysis_log
        WHERE status = 'corrected' AND human_feedback_flag = 'No'
        ORDER BY timestamp DESC
        LIMIT 1
        """)
        no_example = cursor.fetchone()
        
        # Process the fetched rows into a structured dictionary format.
        for row in [yes_example, no_example]:
            if row:
                # Reconstruct the dictionary, deserializing string fields back into lists.
                correct_analysis = {
                    "flag": row[1],
                    "reasoning": row[2],
                    "related_regulations": [reg.strip() for reg in row[3].split(',')] if row[3] else [],
                    "citations": [cite.strip() for cite in row[4].split(',')] if row[4] else []
                }
                # Format the final output structure for the few-shot prompt.
                examples.append({
                    "feature": row[0],
                    "correct_analysis": json.dumps(correct_analysis, indent=4)
                })

        print(f"Fetched {len(examples)} corrected examples for few-shot prompting.")
        return examples
        
    except sqlite3.Error as e:
        print(f"Error fetching corrected examples from database: {e}")
        return []
    finally:
        if conn:
            conn.close()

def reset_database():
    """
    Drops the 'analysis_log' table completely and re-initializes it.
    
    Warning: This is a destructive operation and will result in the loss of all logged data.
    It should be used with caution, primarily for testing or development purposes.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS analysis_log")
        conn.commit()
        print("Database has been reset.")
    except sqlite3.Error as e:
        print(f"Error resetting database: {e}")
    finally:
        if conn: conn.close()
    # Re-create the table with the correct schema after dropping it.
    init_db()