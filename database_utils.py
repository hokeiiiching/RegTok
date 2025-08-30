# database_utils.py (Corrected and Resilient)

import sqlite3
import datetime
import pandas as pd
import json

DATABASE_NAME = "audit_log.db"

def init_db():
    """
    Initializes the database.
    Creates the 'analysis_log' table with all required columns for analysis and feedback.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
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
            human_feedback_reasoning TEXT
        )
        """)
        conn.commit()
        print("Database initialized successfully with the correct schema.")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

def save_analysis(result_dict: dict, original_query: str) -> int:
    """
    Saves a single analysis result to the SQLite database with a 'pending_review' status.
    """
    last_id = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        timestamp = datetime.datetime.now()
        flag = result_dict.get('flag', 'Error')
        reasoning = result_dict.get('reasoning', '')
        regulations = ", ".join(result_dict.get('related_regulations', []))
        thought = result_dict.get('thought', '')
        expanded_query = result_dict.get('expanded_query', original_query)
        status = 'pending_review'
        
        cursor.execute("""
        INSERT INTO analysis_log (
            timestamp, original_query, expanded_query, flag, reasoning, 
            related_regulations, thought_process, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, original_query, expanded_query, flag, reasoning, regulations, thought, status))
        
        last_id = cursor.lastrowid
        conn.commit()
        print(f"Successfully saved analysis (ID: {last_id}) to the audit log.")
    except sqlite3.Error as e:
        print(f"Failed to save analysis to database: {e}")
    finally:
        if conn:
            conn.close()
    return last_id

def update_feedback(log_id: int, status: str, corrected_flag: str = None, corrected_reasoning: str = None):
    """
    Updates an existing log entry with human feedback.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE analysis_log 
        SET status = ?, human_feedback_flag = ?, human_feedback_reasoning = ?
        WHERE id = ?
        """, (status, corrected_flag, corrected_reasoning, log_id))
        
        conn.commit()
        print(f"Successfully updated feedback for log ID: {log_id} with status '{status}'.")
    except sqlite3.Error as e:
        print(f"Failed to update feedback in database: {e}")
    finally:
        if conn:
            conn.close()

def fetch_all_logs() -> pd.DataFrame:
    """
    Fetches all records, creates a new consolidated 'human_feedback' column,
    and returns a clean DataFrame for display. This version is resilient to an empty database.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        df = pd.read_sql_query("SELECT * FROM analysis_log ORDER BY timestamp DESC", conn)

        # --- RESILIENCY FIX ---
        # If the DataFrame is empty (e.g., new database), return it immediately
        # to avoid trying to access columns that might not exist in an empty frame.
        if df.empty:
            return pd.DataFrame(columns=[
                'timestamp', 'original_query', 'flag', 'reasoning', 
                'status', 'human_feedback', 'related_regulations', 'id'
            ])

        # Define a helper function to apply to each row of the DataFrame
        def determine_feedback(row):
            if row['status'] == 'approved':
                return 'Approved'
            elif row['status'] == 'corrected':
                # Return the reasoning, or a blank string if it's missing (robustness)
                return row['human_feedback_reasoning'] if pd.notna(row['human_feedback_reasoning']) else ''
            else: # Covers 'pending_review' and any other states
                return ''

        # Apply the function to create the new consolidated column
        df['human_feedback'] = df.apply(determine_feedback, axis=1)

        # Define the final order and selection of columns for the UI
        column_order = [
            'timestamp', 'original_query', 'flag', 'reasoning', 
            'status', 'human_feedback', 'related_regulations', 'id'
        ]
        
        # Return only the desired columns, in the specified order
        return df[column_order]

    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"Error fetching logs from database: {e}")
        # Return an empty DataFrame on error
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def fetch_corrected_examples(n_examples: int = 2) -> list:
    """ Fetches human-corrected examples for few-shot prompting. """
    examples = []
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT original_query, human_feedback_flag, human_feedback_reasoning, related_regulations
        FROM analysis_log
        WHERE status = 'corrected' AND human_feedback_flag IS NOT NULL AND human_feedback_reasoning IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT ?
        """, (n_examples,))
        
        rows = cursor.fetchall()
        
        for row in rows:
            correct_analysis = {
                "flag": row[1],
                "reasoning": row[2],
                "related_regulations": [reg.strip() for reg in row[3].split(',')] if row[3] else []
            }
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