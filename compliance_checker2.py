import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Part 1: Retrieval (Your Existing Code) ---

# Initialize the embedding model.
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def find_relevant_laws(feature_description: str, collection_name: str, n_results: int = 3) -> list:
    """
    Embeds a feature description and queries ChromaDB for relevant legal text chunks.
    Returns a list of the document texts.
    """
    try:
        # --- MODIFIED: Connect to your ChromaDB Cloud instance ---
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
        
        # Get the collection from the cloud
        collection = cloud_client.get_collection(name=collection_name)

    except (ValueError, Exception) as e:
        print(f"Error: {e}")
        return None


    # Embed the input feature description
    query_embedding = embedding_model.encode(feature_description).tolist()

    # Search the ChromaDB vector store
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    # Return only the text of the documents found
    return results.get('documents', [[]])[0]

# --- Part 2: Synthesis (New Add-on) ---

# Initialize the Gemini client
# It will automatically look for the GOOGLE_API_KEY environment variable
try:
    gemini_client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    print("Please ensure your GOOGLE_API_KEY environment variable is set.")
    gemini_client = None

def check_feature(feature_description: str) -> dict:
    """
    Checks a feature for compliance by retrieving relevant regulations and using an LLM to synthesize an answer.
    
    Args:
        feature_description (str): The description of the product feature.

    Returns:
        dict: A dictionary with 'flag', 'reasoning', and 'related_regulations'.
    """

    if not gemini_client:
        return {
            "flag": "Error",
            "reasoning": "Gemini client could not be initialized. Check API key.",
            "related_regulations": []
        }

    # 1. Retrieve relevant context from the vector database
    print("Step 1: Searching for relevant regulations in the knowledge base...")
    relevant_chunks = find_relevant_laws(
        feature_description, 
        collection_name="regulatory_docs" # Assumes this is your collection name
    )
    
    context = "\n\n---\n\n".join(relevant_chunks)
    if not context:
        print("No relevant documents found in the vector database.")
        context = "No specific regulatory documents were found for context."

    # 2. Augment a prompt with the context and generate a response
    system_prompt = """
    You are an expert compliance officer for a tech company. Your task is to analyze a product feature description and determine if it requires geo-specific compliance logic (e.g., age gates, data localization, content restrictions for a specific country or state).

    Analyze the provided "Product Feature" and the "Relevant Legal Texts". Based on this analysis, you must provide a structured response in JSON format.

    The JSON output must have three keys:
    1.  "flag": A single string. Must be one of "Yes", "No", or "Uncertain".
        - "Yes": Use if there is a clear indication that a law or regulation requires specific logic for a geographic region.
        - "No": Use if the feature seems generic and has no obvious connection to geographically-specific regulations mentioned.
        - "Uncertain": Use if the feature is ambiguous or the provided texts hint at complexity that requires human review.
    2.  "reasoning": A concise, one-sentence explanation for your flag.
    3.  "related_regulations": A list of strings containing the names of specific regulations mentioned in the legal texts that are relevant (e.g., ["GDPR", "Utah S.B. 152"]). If none are relevant, provide an empty list [].
    """

    user_prompt = f"""
    Here is the information to analyze:

    ## Product Feature:
    "{feature_description}"

    ## Relevant Legal Texts:
    "{context}"

    Now, provide your analysis in the required JSON format.
    """

    print("Step 2: Sending request to LLM for analysis...")
    try:
        # For Gemini, combine system and user prompt for a single generate_content call
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-pro", # Make sure to specify the model here
            contents=full_prompt,  # Pass the combined prompt string directly
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type= "application/json"
            )
        )
        
        # 3. Parse the response
        result_json = response.text 
        result_dict = json.loads(result_json)
        print("Step 3: Analysis complete.")
        return result_dict

    except Exception as e:
        print(f"An error occurred during LLM analysis: {e}")
        return {
            "flag": "Error",
            "reasoning": f"An exception occurred during analysis: {e}",
            "related_regulations": []
        }


if __name__ == "__main__":
    # product_feature = "The app will now include a feature to let users under 16 in Europe create a profile."
    product_feature = input("Enter a product feature description to check for compliance: ")

    # This is the main function you will call from your Streamlit app
    analysis_result = check_feature(product_feature)

    # Print the final, structured result
    print("\n--- Compliance Analysis Result ---")
    print(f"🚩 Flag: {analysis_result.get('flag')}")
    print(f"🤔 Reasoning: {analysis_result.get('reasoning')}")
    print(f"📜 Related Regulations: {analysis_result.get('related_regulations')}")