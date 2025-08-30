import os
import json
import re
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- MODIFIED: Import the new example fetcher ---
from database_utils import init_db, save_analysis, fetch_corrected_examples

# Load environment variables from .env file
load_dotenv()

# --- Part 1: Retrieval ---
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def find_relevant_laws(feature_description: str, collection_name: str, n_results: int = 3) -> list:
    """
    Embeds a feature description and queries ChromaDB for relevant legal text chunks.
    """
    try:
        print("Connecting to ChromaDB Cloud...")
        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")

        if not all([api_key, tenant, database]):
            raise ValueError("ChromaDB credentials not found in .env file.")

        cloud_client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )
        collection = cloud_client.get_collection(name=collection_name)
    except (ValueError, Exception) as e:
        print(f"Error: {e}")
        return None

    query_embedding = embedding_model.encode(feature_description).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results.get('documents', [[]])[0]

# --- Part 2: Synthesis ---
try:
    gemini_client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    print("Please ensure your GOOGLE_API_KEY environment variable is set.")
    gemini_client = None

def expand_query_from_file(user_query):
    """Expands a user's query by replacing jargon from a local CSV file."""
    file_path = "/Users/kc/Work/RegTok/Terminologies.csv" # <-- Replace with file path of excel
    try:
        if file_path.endswith('.csv'):
            mapping_df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            mapping_df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file type. Please use a .csv or .xlsx file.")
    except FileNotFoundError:
        return user_query

    if 'term' not in mapping_df.columns or 'explanation' not in mapping_df.columns:
        return user_query
        
    expanded_query = user_query.lower()
    for _, row in mapping_df.iterrows():
        pattern = r'\b' + re.escape(row['term'].lower()) + r'\b'
        expanded_query = re.sub(pattern, row['explanation'].lower(), expanded_query)
    
    print(f"Expanded Query: {expanded_query}")
    return expanded_query

def check_feature(feature_description: str) -> dict:
    """
    Checks a feature for compliance using a RAG pipeline that is dynamically
    improved with few-shot examples from human feedback.
    """
    expanded_query = expand_query_from_file(feature_description)
    if not gemini_client:
        return {
            "flag": "Error",
            "reasoning": "Gemini client could not be initialized. Check API key.",
            "related_regulations": [], "thought": "", "expanded_query": expanded_query
        }

    # 1. Retrieve relevant context from the vector database
    print("Step 1: Searching for relevant regulations in the knowledge base...")
    relevant_chunks = find_relevant_laws(expanded_query, collection_name="regulatory_docs")
    context = "\n\n---\n\n".join(relevant_chunks) if relevant_chunks else "No specific regulatory documents were found for context."

    # --- NEW: Self-Evolving Agent Logic ---
    # 2. Fetch "Golden Examples" from the database based on human corrections.
    print("Step 2: Fetching human-corrected examples to improve accuracy...")
    golden_examples = fetch_corrected_examples(n_examples=2)
    
    examples_prompt_section = ""
    if golden_examples:
        # Format the examples into a string to be injected into the prompt.
        examples_str = "\n".join([
            f"### Example:\nProduct Feature: \"{ex['feature']}\"\nCorrect Analysis:\n{ex['correct_analysis']}"
            for ex in golden_examples
        ])
        examples_prompt_section = f"""
Here are some examples of correct analyses based on past human feedback. Use these as a guide to ensure your analysis is accurate and follows the correct format.
{examples_str}
---
"""
    # 3. Augment the system prompt with the golden examples.
    system_prompt = f"""
You are an expert compliance officer for a tech company. Your task is to analyze a product feature description and determine if it requires geo-specific compliance logic (e.g., age gates, data localization, content restrictions for a specific country or state).

Analyze the provided "Product Feature" and the "Relevant Legal Texts". Based on this analysis, you must provide a structured response in JSON format.

The JSON output must have three keys:
1.  "flag": A single string. Must be one of "Yes", "No", or "Uncertain".
2.  "reasoning": A concise, one-sentence explanation for your flag.
3.  "related_regulations": A list of strings of specific regulation names. If none are relevant, provide an empty list [].

{examples_prompt_section}
Now, perform the analysis for the following request.
"""

    user_prompt = f"""
## Product Feature:
"{expanded_query}"

## Relevant Legal Texts:
"{context}"

Provide your analysis in the required JSON format.
"""

    print("Step 3: Sending enhanced prompt to LLM for analysis...")
    try:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(include_thoughts=True)
            )
        )
        
        result_dict, thought_text = {}, ""
        for part in response.candidates[0].content.parts:
            if part.thought:
                thought_text += part.text
            else:
                result_dict = json.loads(part.text)

        result_dict['thought'] = thought_text
        result_dict['expanded_query'] = expanded_query

        print("Step 4: Analysis complete.")
        return result_dict

    except Exception as e:
        print(f"An error occurred during LLM analysis: {e}")
        return {
            "flag": "Error", "reasoning": f"An exception occurred: {e}",
            "related_regulations": [], "thought": "", "expanded_query": expanded_query
        }

if __name__ == "__main__":
    init_db()
    product_feature = input("Enter a product feature description to check for compliance: ")
    analysis_result = check_feature(product_feature)
    if analysis_result:
        save_analysis(analysis_result, product_feature)

    print("\n--- Compliance Analysis Result ---")
    print(f"🚩 Flag: {analysis_result.get('flag')}")
    print(f"🤔 Reasoning: {analysis_result.get('reasoning')}")
    print(f"📜 Related Regulations: {analysis_result.get('related_regulations')}")
    print(f"🧠 Thoughts: {analysis_result.get('thought')}")
    print(f"💬 Expanded Query: {analysis_result.get('expanded_query')}")