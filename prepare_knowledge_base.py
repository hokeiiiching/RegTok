import os
import chromadb
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- CONFIGURATION ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # A fast and reliable model
COLLECTION_NAME = "regulatory_docs"       # Name for your collection in ChromaDB Cloud

def build_vector_store():
    """
    Loads documents, splits them into chunks, creates text embeddings,
    and stores them in a ChromaDB Cloud database.
    """
    print("Starting the vectorization pipeline for ChromaDB Cloud...")
    load_dotenv()

    # 1. --- LOAD DOCUMENTS ---
    print(f"Loading documents from '{KNOWLEDGE_BASE_DIR}'...")
    loader = DirectoryLoader(KNOWLEDGE_BASE_DIR, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    if not documents:
        print(f"No documents found in '{KNOWLEDGE_BASE_DIR}'. Aborting.")
        return
    print(f"Loaded {len(documents)} document(s).")

    # 2. --- SPLIT TEXT ---
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(documents)
    print(f"Split documents into {len(all_splits)} chunks.")

    # 3. --- INITIALIZE EMBEDDING MODEL ---
    print(f"Initializing embedding model '{EMBEDDING_MODEL_NAME}'...")
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    print("Embedding model loaded.")

    # 4. --- CONNECT TO CHROMADB CLOUD AND STORE VECTORS ---
    print("Connecting to ChromaDB Cloud...")
    try:
        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")

        if not all([api_key, tenant, database]):
            raise ValueError("ChromaDB credentials not found in .env file.")

        # Initialize the cloud client
        cloud_client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )

        # To ensure a fresh start, delete the collection if it already exists
        print(f"Checking for existing collection '{COLLECTION_NAME}'...")
        try:
            cloud_client.delete_collection(name=COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'.")
        except Exception:  # <-- THE FIX IS HERE
            # This will catch any error that occurs when deleting,
            # which is fine because our goal is just to ensure it's gone.
            print(f"Collection '{COLLECTION_NAME}' does not exist, creating a new one.")
        
        print(f"Creating collection and adding documents to ChromaDB Cloud...")
        # This command now sends the embedded chunks to your cloud instance
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
    client = chromadb.PersistentClient(path="D:/cs/Work/RegTok")


if __name__ == "__main__":
    build_vector_store()