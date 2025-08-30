import sqlite3
import datetime
import pandas as pd
import json

DATABASE_NAME = "audit_log.db"

def init_db():
    """Initializes the database with the new 'citations' column."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        # --- MODIFIED SCHEMA: Added the 'citations' column ---
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
        print("Database initialized with citation support.")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

def save_analysis(result_dict: dict, original_query: str) -> int:
    """Saves analysis results, including the new citations field."""
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
        # --- MODIFIED: Convert the citations list to a string for storage ---
        citations = ", ".join(result_dict.get('citations', []))
        
        cursor.execute("""
        INSERT INTO analysis_log (
            timestamp, original_query, expanded_query, flag, reasoning, 
            related_regulations, thought_process, status, citations
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, original_query, expanded_query, flag, reasoning, regulations, thought, status, citations))
        
        last_id = cursor.lastrowid
        conn.commit()
        print(f"Successfully saved analysis with citations (ID: {last_id}).")
    except sqlite3.Error as e:
        print(f"Failed to save analysis to database: {e}")
    finally:
        if conn:
            conn.close()
    return last_id

def fetch_all_logs() -> pd.DataFrame:
    """Fetches all records and includes the new 'citations' column."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        df = pd.read_sql_query("SELECT * FROM analysis_log ORDER BY timestamp DESC", conn)

        if df.empty:
            return pd.DataFrame(columns=[
                'timestamp', 'original_query', 'flag', 'reasoning', 
                'status', 'human_feedback', 'citations', 'related_regulations'
            ])

        def determine_feedback(row):
            if row['status'] == 'approved': return 'Approved'
            elif row['status'] == 'corrected': return row['human_feedback_reasoning'] if pd.notna(row['human_feedback_reasoning']) else ''
            else: return ''
        df['human_feedback'] = df.apply(determine_feedback, axis=1)

        # --- MODIFIED: Add 'citations' to the final column list ---
        column_order = [
            'timestamp', 'original_query', 'flag', 'reasoning', 
            'status', 'human_feedback', 'citations', 'related_regulations'
        ]
        
        return df[column_order]

    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"Error fetching logs from database: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# (update_feedback and fetch_corrected_examples functions remain unchanged)
def update_feedback(log_id: int, status: str, corrected_flag: str = None, corrected_reasoning: str = None):
    # This function doesn't need to change as it doesn't handle citations
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE analysis_log 
        SET status = ?, human_feedback_flag = ?, human_feedback_reasoning = ?
        WHERE id = ?
        """, (status, corrected_flag, corrected_reasoning, log_id))
        conn.commit()
    finally:
        if conn: conn.close()
        
def fetch_corrected_examples(n_examples: int = 2) -> list:
    """
    Fetches a diverse, high-quality set of human-corrected examples from the database.
    This corrected version INCLUDES the citations field in the examples.
    """
    examples = []
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # --- CORRECTED SQL QUERY: Now selects the 'citations' column ---
        # Fetch the most recent 'corrected' entry with a "Yes" flag
        cursor.execute("""
        SELECT original_query, human_feedback_flag, human_feedback_reasoning, related_regulations, citations
        FROM analysis_log
        WHERE status = 'corrected' AND human_feedback_flag = 'Yes'
        ORDER BY timestamp DESC
        LIMIT 1
        """)
        yes_example = cursor.fetchone()

        # Fetch the most recent 'corrected' entry with a "No" flag
        cursor.execute("""
        SELECT original_query, human_feedback_flag, human_feedback_reasoning, related_regulations, citations
        FROM analysis_log
        WHERE status = 'corrected' AND human_feedback_flag = 'No'
        ORDER BY timestamp DESC
        LIMIT 1
        """)
        no_example = cursor.fetchone()
        
        # Process the fetched examples if they exist
        for row in [yes_example, no_example]:
            if row:
                # --- CORRECTED DICTIONARY: Now builds the 'citations' list ---
                correct_analysis = {
                    "flag": row[1],
                    "reasoning": row[2],
                    "related_regulations": [reg.strip() for reg in row[3].split(',')] if row[3] else [],
                    "citations": [cite.strip() for cite in row[4].split(',')] if row[4] else []
                }
                examples.append({
                    "feature": row[0],
                    "correct_analysis": json.dumps(correct_analysis, indent=4)
                })

        print(f"Fetched {len(examples)} diverse and complete corrected examples for few-shot prompting.")
        return examples
        
    except sqlite3.Error as e:
        print(f"Error fetching corrected examples from database: {e}")
        return [] # Return empty list on error
    finally:
        if conn:
            conn.close()

def reset_database():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS analysis_log")
        conn.commit()
    finally:
        if conn: conn.close()
    init_db()