import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings # <-- UPDATED IMPORT
from langchain_community.vectorstores import Chroma

# --- CONFIGURATION ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
VECTOR_STORE_DIR = "chroma_db_store"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" # A fast and reliable model

def build_vector_store():
    """
    Loads documents, splits them into chunks, creates text embeddings,
    and stores them in a Chroma vector database.
    """
    print("Starting the vectorization pipeline...")

    # 1. --- LOAD DOCUMENTS ---
    print(f"Loading documents from '{KNOWLEDGE_BASE_DIR}'...")
    loader = DirectoryLoader(KNOWLEDGE_BASE_DIR, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    if not documents:
        print("No documents found. Please add .txt files to the knowledge_base directory.")
        return
    print(f"Loaded {len(documents)} document(s).")

    # 2. --- SPLIT TEXT ---
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
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

    # 4. --- CREATE AND PERSIST VECTOR STORE ---
    if os.path.exists(VECTOR_STORE_DIR):
        print(f"Removing old vector store directory: '{VECTOR_STORE_DIR}'")
        shutil.rmtree(VECTOR_STORE_DIR)

    print(f"Creating and persisting vector store at '{VECTOR_STORE_DIR}'...")
    vectorstore = Chroma.from_documents(
        documents=all_splits,
        embedding=embeddings,
        persist_directory=VECTOR_STORE_DIR
    )
    print("Vector store created successfully!")
    print("\n--- Pipeline Complete ---")
    print(f"Your knowledge base is now ready in the '{VECTOR_STORE_DIR}' directory.")


if __name__ == "__main__":
    build_vector_store()