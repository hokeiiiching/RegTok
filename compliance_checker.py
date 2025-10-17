import os
import json
import re
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

from dotenv import load_dotenv

from database_utils import init_db, save_analysis, fetch_corrected_examples

# Load environment variables from a .env file for secure credential management.
load_dotenv()

# Initialize the sentence transformer model for creating vector embeddings.
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def find_relevant_laws(feature_description: str, collection_name: str, n_results: int = 3) -> list:
    """Embeds a feature description and queries ChromaDB for relevant legal texts.

    This function connects to a ChromaDB cloud instance, converts the input text
    into a vector embedding, and retrieves the most similar document chunks
    along with their associated metadata, which is crucial for citations.

    Args:
        feature_description: The string description of the product feature.
        collection_name: The name of the ChromaDB collection to query.
        n_results: The number of relevant documents to retrieve.

    Returns:
        A list of tuples, where each tuple contains the document text and its
        corresponding metadata dictionary, e.g., [('text', {'source': 'GDPR'})].
        Returns an empty list if an error occurs or no results are found.
    """
    try:
        # Establish connection to the ChromaDB cloud service using environment variables.
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

    # Convert the user's query into a vector embedding for semantic search.
    query_embedding = embedding_model.encode(feature_description).tolist()
    
    # Query the collection for the most relevant documents and their metadata.
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['metadatas', 'documents'] # Ensure both documents and metadata are returned.
    )
    
    # Combine the retrieved documents and metadata into a structured list.
    docs = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    
    # Gracefully handle cases where documents or metadata might be missing in the results.
    return list(zip(docs, metadatas)) if docs and metadatas else []

# --- Language Model and Prompting Setup ---

# Initialize the Gemini client for generative AI capabilities.
try:
    gemini_client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    gemini_client = None

def expand_query_from_file(user_query: str) -> str:
    """Expands technical terms in a user query with simpler explanations.

    This function reads a local CSV file containing a mapping of terms to
    explanations. It then substitutes any occurrences of these terms in the
    user's query to provide more context for the language model.

    Args:
        user_query: The original query string from the user.

    Returns:
        The query string with technical terms replaced by their explanations.
    """
    file_path = "/Users/kc/Work/RegTok/Terminologies.csv"
    try:
        mapping_df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
    except FileNotFoundError:
        return user_query
    if 'term' not in mapping_df.columns or 'explanation' not in mapping_df.columns:
        return user_query
    expanded_query = user_query.lower()
    for _, row in mapping_df.iterrows():
        # Use regex for whole-word matching to avoid replacing parts of other words.
        pattern = r'\b' + re.escape(row['term'].lower()) + r'\b'
        expanded_query = re.sub(pattern, row['explanation'].lower(), expanded_query)
    return expanded_query

def check_feature(feature_description: str) -> dict:
    """Analyzes a product feature for compliance using an LLM and vector search.

    This function orchestrates the entire compliance check process. It expands the
    user query, retrieves relevant legal context from a vector database, fetches
    high-quality examples, and constructs a detailed prompt for the Gemini model.
    The final output is a structured JSON analysis.

    Args:
        feature_description: The description of the product feature to be analyzed.

    Returns:
        A dictionary containing the compliance analysis, including a flag,
        reasoning, list of related regulations, and source citations.
    """
    expanded_query = expand_query_from_file(feature_description)
    if not gemini_client:
        return {"flag": "Error", "reasoning": "Gemini client not initialized.", "related_regulations": [], "citations": []}

    # Step 1: Retrieve relevant legal documents from the vector database.
    print("Step 1: Searching for relevant regulations and sources...")
    relevant_chunks_with_meta = find_relevant_laws(expanded_query, collection_name="regulatory_docs")
    
    # Construct the context string, embedding the source of each legal document.
    # This ensures the LLM can trace its reasoning back to specific source texts.
    context_parts = []
    if relevant_chunks_with_meta:
        for doc, meta in relevant_chunks_with_meta:
            # The 'source' key in the metadata is crucial for generating citations.
            source = meta.get('source', 'Unknown Source')
            context_parts.append(f"Source Document: [{source}]\nContent: {doc}\n---")
        context = "\n".join(context_parts)
    else:
        context = "No specific regulatory documents were found for context."

    # Step 2: Fetch human-corrected "Golden Examples" for few-shot prompting.
    # These examples guide the model to produce a more accurate and well-formatted response.
    print("Step 2: Fetching diverse, human-corrected examples...")
    golden_examples = fetch_corrected_examples()
    examples_prompt_section = ""
    if golden_examples:
        examples_str = "\n".join([f"### Example:\nProduct Feature: \"{ex['feature']}\"\nCorrect Analysis:\n{ex['correct_analysis']}" for ex in golden_examples])
        examples_prompt_section = f"Here are some high-quality examples of correct analyses:\n{examples_str}\n---"
        
    # The system prompt instructs the LLM on its role, the context, and the required output format.
    # Explicitly requiring a "citations" key in the JSON response forces the model to cite its sources.
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

    # The user prompt combines the specific feature and the retrieved context for the LLM's analysis.
    user_prompt = f"""
## Product Feature:
"{expanded_query}"

## Relevant Legal Texts:
"{context}"

Provide your analysis in the required JSON format.
"""

    print("Step 3: Sending enhanced prompt with citation requirement to LLM...")
    try:
        # Combine system and user prompts to form the complete request.
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        # Make the API call to the Gemini model, configured to return JSON and include thought processes.
        response = gemini_client.models.generate_content(
            model="gemini-2.5-pro", contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1, 
                response_mime_type="application/json", 
                thinking_config=types.ThinkingConfig(include_thoughts=True))
        )
        
        # Parse the response, separating the model's thought process from the final JSON output.
        result_dict, thought_text = {}, ""
        for part in response.candidates[0].content.parts:
            if part.thought:
                thought_text += part.text
            else:
                result_dict = json.loads(part.text)

        # Append the thought process and expanded query to the result for better traceability.
        result_dict['thought'] = thought_text
        result_dict['expanded_query'] = expanded_query
        print("Step 4: Analysis with citations complete.")
        return result_dict

    except Exception as e:
        print(f"An error occurred during LLM analysis: {e}")
        return {"flag": "Error", "reasoning": f"An exception occurred: {e}", "related_regulations": [], "citations": [], "expanded_query": expanded_query}

# --- Script Execution ---
if __name__ == "__main__":
    # This block serves as the main entry point when the script is executed directly.
    init_db()
    product_feature = input("Enter a product feature description to check for compliance: ")
    analysis_result = check_feature(product_feature)
    if analysis_result:
        # Persist the analysis result to the database for future reference and model improvement.
        save_analysis(analysis_result, product_feature)

    # Display the final analysis to the user.
    print("\n--- Compliance Analysis Result ---")
    print(f"🚩 Flag: {analysis_result.get('flag')}")
    print(f"🤔 Reasoning: {analysis_result.get('reasoning')}")
    print(f"📜 Related Regulations: {analysis_result.get('related_regulations')}")
    print(f"🧠 Thoughts: {analysis_result.get('thought')}")
    print(f"💬 Expanded Query: {analysis_result.get('expanded_query')}")