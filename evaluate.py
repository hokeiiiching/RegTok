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
    Orchestrates the compliance evaluation process for product features.

    This function reads feature data from a CSV, processes each feature through
    an external compliance checker, and consolidates the results into a new CSV.
    It includes error handling for file operations and uses a progress bar
    for user feedback during batch processing.
    """
    print(f"Starting evaluation of '{INPUT_CSV_PATH}'...")

    # 1. Read the input test dataset into a pandas DataFrame.
    #    Includes robust error handling for file existence and required columns.
    try:
        df = pd.read_csv(INPUT_CSV_PATH)
        if not all(col in df.columns for col in [NAME_COLUMN, DESCRIPTION_COLUMN]):
            print(f"Error: Input CSV must contain '{NAME_COLUMN}' and '{DESCRIPTION_COLUMN}' columns. Aborting.")
            return
    except FileNotFoundError:
        print(f"Error: The file '{INPUT_CSV_PATH}' was not found. Please create it. Aborting.")
        return

    results = [] # Initialize a list to store the processed results for all features.
    
    # Iterate through each feature in the DataFrame with a progress bar.
    # tqdm provides visual feedback on processing progress.
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing Features"):
        feature_name = row[NAME_COLUMN]       # Extract the feature name.
        feature_desc = row[DESCRIPTION_COLUMN] # Extract the feature description.
        
        # 2. Combine the feature name and description into a single string.
        #    This provides maximum context for the compliance checker.
        full_feature_text = f"Title: {feature_name}\n\nDescription: {feature_desc}"
        
        print(f"\nProcessing feature #{index + 1}: '{feature_name}'")
        
        # 3. Invoke the external compliance analysis function.
        #    'check_feature' is expected to return the analysis result (dict)
        #    and a process log (which is currently unused but kept for compatibility).
        analysis_result, process_log = check_feature(full_feature_text)

        # 4. Construct a dictionary for the current feature's results
        #    and append it to the results list. Default values are used
        #    if a key is missing from 'analysis_result' to prevent errors.
        result_row = {
            "feature_name": feature_name,
            "flag": analysis_result.get("flag", "Error"), # e.g., "RED", "AMBER", "GREEN"
            "reasoning": analysis_result.get("reasoning", "An error occurred during analysis."),
            "related_regulations": ", ".join(analysis_result.get("related_regulations", [])), # Joins list of regs into a string
            "ai_thought_process": analysis_result.get("thought", ""), # Detailed thought process from AI, if available
            "original_description": feature_desc # Retain the original description for auditing/reference
        }
        results.append(result_row)
        
        # Introduce a small delay to avoid rate limiting or high CPU usage,
        # especially useful when interacting with external APIs.
        time.sleep(1) 

    # 5. After processing all features, convert the list of results into a DataFrame
    #    and write it to the specified output CSV file.
    print("\nEvaluation complete. Saving results...")
    results_df = pd.DataFrame(results)
    
    # Define the precise order of columns for the final output CSV.
    # This ensures consistency in the submission file format.
    output_columns = [
        'feature_name', 
        'flag', 
        'reasoning', 
        'related_regulations', 
        'ai_thought_process',
        'original_description'
    ]
    results_df = results_df[output_columns]

    results_df.to_csv(OUTPUT_CSV_PATH, index=False) # 'index=False' prevents writing DataFrame index as a column.
    
    print(f"Successfully saved results to '{OUTPUT_CSV_PATH}'.")
    print("--- Script Finished ---")


if __name__ == "__main__":
    # Entry point for script execution.
    # Calls the main evaluation function when the script is run directly.
    run_evaluation()