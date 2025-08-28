import os
import json
import chromadb
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser

# --- CONFIGURATION ---
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "regulatory_docs"

def get_rag_chain():
    """
    Initializes all components and builds a complete RAG chain.
    This is the core of the backend logic.
    """
    # Load environment variables from .env file
    load_dotenv()

    # 1. --- Initialize the LLM using the LangChain wrapper ---
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("Error: GOOGLE_API_KEY not found in .env file.")
    
    # Use the LangChain wrapper for Google's model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=google_api_key,
        convert_system_message_to_human=True, # Important for some models
        response_mime_type="application/json" # Ask Gemini to output JSON directly
    )

    # 2. --- Initialize Embeddings and Retriever ---
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'}
    )
    
    # Connect to ChromaDB Cloud
    chroma_api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    database = os.getenv("CHROMA_DATABASE")
    if not all([chroma_api_key, tenant, database]):
        raise ValueError("ChromaDB credentials not found in .env file.")
    
    cloud_client = chromadb.CloudClient(api_key=chroma_api_key, tenant=tenant, database=database)
    
    vector_store = Chroma(
        client=cloud_client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )
    
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    # 3. --- Define the Prompt Template ---
    template = """
    You are an expert AI assistant for TikTok's legal and compliance team. Your task is to analyze a feature description and determine if it requires region-specific legal compliance logic, based ONLY on the provided legal context.

    **LEGAL CONTEXT:**
    {context}

    **FEATURE DESCRIPTION:**
    {feature_description}

    **INSTRUCTIONS:**
    1.  Analyze the feature description against the provided legal context.
    2.  Distinguish between a legal requirement and a business decision (e.g., 'market testing' is a business decision).
    3.  If the description is ambiguous, flag it as "Uncertain".
    4.  Provide your output as a single, valid JSON object with three keys and NO other text or explanation.

    **JSON OUTPUT:**
    {{
        "flag": "One of 'Yes', 'No', or 'Uncertain'",
        "reasoning": "A concise explanation for your decision.",
        "related_regulations": ["List of applicable regulations or an empty list"]
    }}
    """
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "feature_description"]
    )
    
    # 4. --- Define the Output Parser ---
    # This will automatically parse the LLM's JSON string into a Python dictionary
    parser = JsonOutputParser()

    # 5. --- Assemble the RAG Chain ---
    # This is now a seamless, end-to-end LangChain pipeline
    rag_chain = (
        {"context": retriever, "feature_description": RunnablePassthrough()}
        | prompt
        | llm
        | parser
    )
    
    return rag_chain

# --- Main Function to be called by the UI ---
# We initialize the chain once to be reused
try:
    rag_chain = get_rag_chain()
except Exception as e:
    rag_chain = None
    initialization_error = e

def check_feature(feature_description: str) -> dict:
    """
    Analyzes a feature description and returns a compliance check result.
    """
    if rag_chain is None:
        return {
            "flag": "Error",
            "reasoning": f"Failed to initialize the RAG chain: {str(initialization_error)}",
            "related_regulations": []
        }
        
    try:
        # The invoke method now runs the entire chain and returns the parsed JSON
        result = rag_chain.invoke(feature_description)
        return result
    except Exception as e:
        print(f"An error occurred in check_feature: {e}")
        return {
            "flag": "Error",
            "reasoning": f"An unexpected error occurred during analysis: {str(e)}",
            "related_regulations": []
        }