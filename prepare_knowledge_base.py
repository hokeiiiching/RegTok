import os
import chromadb
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- SCRIPT CONFIGURATION ---
# Specifies the directory containing the source text documents for the knowledge base.
KNOWLEDGE_BASE_DIR = "knowledge_base"
# Defines the pre-trained model from Hugging Face to be used for generating text embeddings.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # A fast and efficient sentence-transformer model.
# The designated name for the vector collection within the ChromaDB instance.
COLLECTION_NAME = "regulatory_docs"

def build_vector_store():
    """
    Orchestrates the end-to-end pipeline for building a vector store in ChromaDB Cloud.
    
    This function performs the following steps:
    1. Loads environment variables for ChromaDB credentials.
    2. Scans a local directory to load text documents.
    3. Splits the loaded documents into manageable, overlapping chunks.
    4. Initializes a Hugging Face embedding model.
    5. Connects to a ChromaDB Cloud instance.
    6. Deletes any pre-existing collection with the same name to ensure a fresh start.
    7. Generates embeddings for the text chunks and ingests them into the specified
       ChromaDB collection.
       
    Requires a .env file with CHROMA_API_KEY, CHROMA_TENANT, and CHROMA_DATABASE.
    """
    print("Starting the vectorization pipeline for ChromaDB Cloud...")
    # Load environment variables from a .env file for secure credential management.
    load_dotenv()

    # STEP 1: LOAD DOCUMENTS
    # Recursively load all .txt files from the specified knowledge base directory.
    print(f"Loading documents from '{KNOWLEDGE_BASE_DIR}'...")
    loader = DirectoryLoader(KNOWLEDGE_BASE_DIR, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    if not documents:
        print(f"No documents found in '{KNOWLEDGE_BASE_DIR}'. Aborting.")
        return
    print(f"Loaded {len(documents)} document(s).")

    # STEP 2: SPLIT TEXT INTO CHUNKS
    # Divide the documents into smaller chunks to ensure they fit within the embedding
    # model's context window. Overlap helps maintain contextual continuity between chunks.
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(documents)
    print(f"Split documents into {len(all_splits)} chunks.")

    # STEP 3: INITIALIZE EMBEDDING MODEL
    # Load the specified HuggingFace model for creating vector representations of the text chunks.
    print(f"Initializing embedding model '{EMBEDDING_MODEL_NAME}'...")
    model_kwargs = {'device': 'cpu'} # Explicitly set to use CPU.
    encode_kwargs = {'normalize_embeddings': False} # Normalization can be handled by the vector store if needed.
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    print("Embedding model loaded.")

    # STEP 4: CONNECT TO CHROMADB CLOUD AND STORE VECTORS
    # Establish a connection to the ChromaDB Cloud service and populate the collection.
    print("Connecting to ChromaDB Cloud...")
    try:
        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")

        # Validate that all required credentials are present.
        if not all([api_key, tenant, database]):
            raise ValueError("ChromaDB credentials not found in .env file.")

        # Initialize the ChromaDB Cloud client using credentials from the environment.
        cloud_client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )

        # To ensure a clean state, attempt to delete the collection if it already exists.
        # This prevents duplicating data during subsequent runs of the script.
        print(f"Checking for existing collection '{COLLECTION_NAME}'...")
        try:
            cloud_client.delete_collection(name=COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'.")
        except Exception:
            # An exception is expected if the collection does not exist.
            # This is benign, so we can safely ignore it and proceed.
            print(f"Collection '{COLLECTION_NAME}' does not exist, creating a new one.")
        
        print(f"Creating collection and adding documents to ChromaDB Cloud...")
        # Create embeddings from the document chunks and store them in the cloud collection.
        # This is the main ingestion step.
        vectorstore = Chroma.from_documents(
            documents=all_splits,
            embedding=embeddings,
            client=cloud_client,
            collection_name=COLLECTION_NAME
        )
        print("Documents embedded and stored in ChromaDB Cloud successfully!")

    except Exception as e:
        print(f"An error occurred while connecting to or updating ChromaDB Cloud: {e}")
        return

    print("\n--- Pipeline Complete ---")
    print(f"Your knowledge base is now ready in ChromaDB Cloud under the collection: '{COLLECTION_NAME}'")
    # NOTE: The following line initializes a PersistentClient which is not used.
    # This may be leftover code from a previous implementation.
    client = chromadb.PersistentClient(path="D:/cs/Work/RegTok")


# Standard Python entry point.
# Ensures that the build_vector_store() function is called only when the script is executed directly.
if __name__ == "__main__":
    build_vector_store()