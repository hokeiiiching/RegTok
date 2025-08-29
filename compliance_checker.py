import os
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# --- NEW: Load environment variables ---
load_dotenv()

# Initialize the embedding model.
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def find_relevant_laws(feature_description: str, collection_name: str, n_results: int = 5) -> dict:
    """
    Embeds a feature description and queries ChromaDB for relevant legal text chunks.
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

    # 2. Embed the input feature description into a vector
    print(f"Embedding query: '{feature_description}'")
    query_embedding = embedding_model.encode(feature_description).tolist()

    # 3. Search the ChromaDB vector store
    print(f"Searching for the top {n_results} most relevant legal texts...")
    results = collection.query(
        query_embeddings=[query_embedding], 
        n_results=n_results
    )

    return results

# --- Example Usage ---
if __name__ == "__main__":
    product_feature = input("Enter a product feature description to search for relevant laws: ")
    my_collection = "regulatory_docs"
    relevant_chunks = find_relevant_laws(product_feature, my_collection, n_results=3)

    if relevant_chunks:
        print("\n--- Search Results ---")
        for i, doc in enumerate(relevant_chunks['documents'][0]):
            distance = relevant_chunks['distances'][0][i]
            doc_id = relevant_chunks['ids'][0][i]
            
            print(f"\n📄 Result {i+1} (Distance: {distance:.4f})")
            print(f"   ID: {doc_id}")
            print(f"   Text: {doc[:300]}...")