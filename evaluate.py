import pandas as pd
from tqdm import tqdm
from compliance_checker import check_feature
import time

# --- CONFIGURATION ---
INPUT_CSV_PATH = "test_dataset.csv"
OUTPUT_CSV_PATH = "submission.csv"
NAME_COLUMN = "feature_name"
DESCRIPTION_COLUMN = "feature_description"

def run_evaluation():
    """
    Reads feature names and descriptions from an input CSV, combines them,
    runs compliance checks, and saves the structured results to an output CSV.
    """
    print(f"Starting evaluation of '{INPUT_CSV_PATH}'...")

    # 1. Read the test dataset
    try:
        df = pd.read_csv(INPUT_CSV_PATH)
        if not all(col in df.columns for col in [NAME_COLUMN, DESCRIPTION_COLUMN]):
            print(f"Error: Input CSV must contain '{NAME_COLUMN}' and '{DESCRIPTION_COLUMN}' columns. Aborting.")
            return
    except FileNotFoundError:
        print(f"Error: The file '{INPUT_CSV_PATH}' was not found. Please create it. Aborting.")
        return

    results = []
    # Use tqdm for a progress bar
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing Features"):
        feature_name = row[NAME_COLUMN]
        feature_desc = row[DESCRIPTION_COLUMN]
        
        # 2. Combine name and description for maximum context
        full_feature_text = f"Title: {feature_name}\n\nDescription: {feature_desc}"
        
        print(f"\nProcessing feature #{index + 1}: '{feature_name}'")
        
        # 3. Call your main analysis function
        analysis_result, process_log= check_feature(full_feature_text)

        # 4. Append the results to a list for later saving
        result_row = {
            "feature_name": feature_name,
            "flag": analysis_result.get("flag", "Error"),
            "reasoning": analysis_result.get("reasoning", "An error occurred."),
            "related_regulations": ", ".join(analysis_result.get("related_regulations", [])),
            "ai_thought_process": analysis_result.get("thought", ""),
            "original_description": feature_desc # Keep original for reference
        }
        results.append(result_row)
        time.sleep(1) # Gentle delay for APIs

    # 5. Write the final results to the output CSV
    print("\nEvaluation complete. Saving results...")
    results_df = pd.DataFrame(results)
    
    # Define the final column order for the submission file
    output_columns = [
        'feature_name', 
        'flag', 
        'reasoning', 
        'related_regulations', 
        'ai_thought_process',
        'original_description'
    ]
    results_df = results_df[output_columns]

    results_df.to_csv(OUTPUT_CSV_PATH, index=False)
    
    print(f"Successfully saved results to '{OUTPUT_CSV_PATH}'.")
    print("--- Script Finished ---")


if __name__ == "__main__":
    run_evaluation()