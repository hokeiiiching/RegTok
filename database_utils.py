import sqlite3
import datetime
import pandas as pd

DATABASE_NAME = "audit_log.db"

def init_db():
    """Initializes the database and creates the 'analysis_log' table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Create table with all the required columns
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            feature_description TEXT NOT NULL,
            flag TEXT,
            reasoning TEXT,
            related_regulations TEXT,
            thought_process TEXT
        )
        """)
        
        conn.commit()
        print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

def save_analysis(result_dict: dict, feature_description: str):
    """Saves a single analysis result to the SQLite database."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Prepare data for insertion
        timestamp = datetime.datetime.now()
        flag = result_dict.get('flag', 'Error')
        reasoning = result_dict.get('reasoning', '')
        # Convert list of regulations to a string for storage
        regulations = ", ".join(result_dict.get('related_regulations', []))
        thought = result_dict.get('thought', '')
        
        cursor.execute("""
        INSERT INTO analysis_log (timestamp, feature_description, flag, reasoning, related_regulations, thought_process)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, feature_description, flag, reasoning, regulations, thought))
        
        conn.commit()
        print("Successfully saved analysis to the audit log.")
    except sqlite3.Error as e:
        print(f"Failed to save analysis to database: {e}")
    finally:
        if conn:
            conn.close()

def fetch_all_logs() -> pd.DataFrame:
    """
    Fetches all records from the analysis_log table and returns them as a pandas DataFrame.
    Returns an empty DataFrame if there's an error or no data.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        # Use pandas to directly read the SQL query into a DataFrame
        df = pd.read_sql_query("SELECT * FROM analysis_log ORDER BY timestamp DESC", conn)
        return df
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"Error fetching logs from database: {e}")
        # Return an empty DataFrame with the expected columns if the table is empty or an error occurs
        return pd.DataFrame(columns=[
            'id', 'timestamp', 'feature_description', 'flag', 
            'reasoning', 'related_regulations', 'thought_process'
        ])
    finally:
        if conn:
            conn.close()
