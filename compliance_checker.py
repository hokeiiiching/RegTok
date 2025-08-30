import os
import json
import re
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types
from dotenv import load_dotenv

from database_utils import init_db, save_analysis, fetch_corrected_examples

load_dotenv()

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- MODIFIED: The retriever now fetches metadata for citations ---
def find_relevant_laws(feature_description: str, collection_name: str, n_results: int = 3) -> list:
    """
    Embeds a feature description and queries ChromaDB for relevant legal text chunks.
    
    Returns:
        list: A list of tuples, where each tuple contains (document_text, metadata_dict).
    """
    try:
        # (Connection logic is unchanged)
        print("Connecting to ChromaDB Cloud...")
        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")
        if not all([api_key, tenant, database]):
            raise ValueError("ChromaDB credentials not found.")
        cloud_client = chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)
        collection = cloud_client.get_collection(name=collection_name)
    except Exception as e:
        print(f"Error: {e}")
        return []

    query_embedding = embedding_model.encode(feature_description).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['metadatas', 'documents'] # Explicitly include metadatas
    )
    
    # Combine the documents and metadatas into a list of tuples
    docs = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    
    # Ensure we handle cases where one might be missing
    return list(zip(docs, metadatas)) if docs and metadatas else []

# --- Synthesis Part (LLM and Prompting) ---
try:
    gemini_client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    gemini_client = None

def expand_query_from_file(user_query):
    # (This function is unchanged)
    file_path = "/Users/kc/Work/RegTok/Terminologies.csv"
    try:
        mapping_df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
    except FileNotFoundError:
        return user_query
    if 'term' not in mapping_df.columns or 'explanation' not in mapping_df.columns:
        return user_query
    expanded_query = user_query.lower()
    for _, row in mapping_df.iterrows():
        pattern = r'\b' + re.escape(row['term'].lower()) + r'\b'
        expanded_query = re.sub(pattern, row['explanation'].lower(), expanded_query)
    return expanded_query

def check_feature(feature_description: str) -> dict:
    expanded_query = expand_query_from_file(feature_description)
    if not gemini_client:
        return {"flag": "Error", "reasoning": "Gemini client not initialized.", "related_regulations": [], "citations": []}

    # 1. Retrieve relevant context with metadata
    print("Step 1: Searching for relevant regulations and sources...")
    relevant_chunks_with_meta = find_relevant_laws(expanded_query, collection_name="regulatory_docs")
    
    # --- MODIFIED: Build a context string that includes the source for each chunk ---
    context_parts = []
    if relevant_chunks_with_meta:
        for doc, meta in relevant_chunks_with_meta:
            # Assuming the metadata contains a 'source' key. This is crucial.
            source = meta.get('source', 'Unknown Source')
            context_parts.append(f"Source Document: [{source}]\nContent: {doc}\n---")
        context = "\n".join(context_parts)
    else:
        context = "No specific regulatory documents were found for context."

    # 2. Fetch "Golden Examples" (unchanged)
    print("Step 2: Fetching diverse, human-corrected examples...")
    golden_examples = fetch_corrected_examples()
    examples_prompt_section = ""
    if golden_examples:
        examples_str = "\n".join([f"### Example:\nProduct Feature: \"{ex['feature']}\"\nCorrect Analysis:\n{ex['correct_analysis']}" for ex in golden_examples])
        examples_prompt_section = f"Here are some high-quality examples of correct analyses:\n{examples_str}\n---"
        
    # --- MODIFIED SYSTEM PROMPT: Now requires a "citations" key in the JSON ---
    system_prompt = f"""
You are an expert compliance officer. Your task is to analyze a product feature and determine if it requires geo-specific logic, based on the provided legal texts.

{examples_prompt_section}

First, in your thought process, analyze the user's feature and compare it to the examples provided. 
Then, review the "Relevant Legal Texts". Each text is tagged with a "Source Document".

After your thought process, provide your final analysis as a structured JSON. The JSON must have four keys:
1.  "flag": A single string ("Yes", "No", or "Uncertain").
2.  "reasoning": A concise explanation for your flag. Your reasoning must mention the law that applies.
3.  "related_regulations": A list of strings of specific regulation names (e.g., ["GDPR", "COPPA"]).
4.  "citations": A list of strings containing the exact "Source Document" tags (e.g., ["GDPR Article 8", "Utah S.B. 152 Section 3a"]) you used to arrive at your conclusion. If no source was relevant, provide an empty list [].
"""

    user_prompt = f"""
## Product Feature:
"{expanded_query}"

## Relevant Legal Texts:
"{context}"

Provide your analysis in the required JSON format.
"""

    print("Step 3: Sending enhanced prompt with citation requirement to LLM...")
    try:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = gemini_client.models.generate_content(
            model="gemini-2.5-pro", contents=full_prompt,
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json", thinking_config=types.ThinkingConfig(include_thoughts=True))
        )
        
        result_dict, thought_text = {}, ""
        for part in response.candidates[0].content.parts:
            if part.thought:
                thought_text += part.text
            else:
                result_dict = json.loads(part.text)

        result_dict['thought'] = thought_text
        result_dict['expanded_query'] = expanded_query
        print("Step 4: Analysis with citations complete.")
        return result_dict

    except Exception as e:
        print(f"An error occurred during LLM analysis: {e}")
        return {"flag": "Error", "reasoning": f"An exception occurred: {e}", "related_regulations": [], "citations": [], "expanded_query": expanded_query}

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