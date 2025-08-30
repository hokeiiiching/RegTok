import pandas as pd
import json
import os
from compliance_checker import check_feature # Import your existing function

# --- CONFIGURATION ---
INPUT_CSV_PATH = r"C:\Users\..."
OUTPUT_CSV_PATH = r"C:\Users\..."

# Define a generic legal context to be used for all features.
# You can customize this based on your project's specific legal framework.
LEGAL_CONTEXT = "The system must comply with GDPR. Key principles include data minimization, purpose limitation, and requiring explicit consent for processing sensitive data like biometrics (Article 9)."

def process_batch():
    """
    Reads features from an input CSV, processes them, and saves the results to a new CSV.
    """
    # 1. Check if the input file exists
    if not os.path.exists(INPUT_CSV_PATH):
        print(f"❌ Error: Input file not found at '{INPUT_CSV_PATH}'")
        return

    print(f"▶️ Starting batch processing from '{INPUT_CSV_PATH}'...")
    
    # 2. Read the input CSV into a pandas DataFrame
    input_df = pd.read_csv(INPUT_CSV_PATH, encoding='windows-1252')
    
    # List to store the results for each row
    results_list = []

    # 3. Iterate through each row of the input DataFrame
    for index, row in input_df.iterrows():
        feature_name = row['feature_name']
        feature_description = row['feature_description']
        
        # Concatenate the two columns as requested
        combined_input = f"{feature_name}: {feature_description}"
        
        print(f"⚙️ Processing row {index + 1}/{len(input_df)}: '{feature_name}'")
        
        try:
            # 4. Call your existing analysis function
            analysis_result = check_feature(combined_input)
            
            # Parse the JSON string output from the checker
            #analysis_result = json.loads(analysis_json_string)
            
            # 5. Store the results in a dictionary
            result_row = {
                'feature_name': feature_name,
                'feature_description': feature_description,
                'output_flag': analysis_result.get('flag', 'ERROR'),
                'output_reasoning': analysis_result.get('reasoning', 'Could not parse reasoning.')
            }
            results_list.append(result_row)
            
        except Exception as e:
            print(f"❗️ An error occurred on row {index + 1}: {e}")
            # Optionally, add an error entry to the results
            results_list.append({
                'feature_name': feature_name,
                'feature_description': feature_description,
                'output_flag': 'ERROR',
                'output_reasoning': str(e)
            })

    # 6. Convert the list of results into a DataFrame and save to CSV
    if results_list:
        results_df = pd.DataFrame(results_list)
        results_df.to_csv(OUTPUT_CSV_PATH, index=False)
        print(f"✅ Success! Processing complete. Results saved to '{OUTPUT_CSV_PATH}'.")
    else:
        print("⚠️ No results to save.")

# --- Main execution block ---
if __name__ == "__main__":
    process_batch()