GeoCompliance Guardian
A prototype system that uses a Retrieval-Augmented Generation (RAG) LLM to automatically flag software features that require geo-specific legal compliance logic.
This project was built for the TikTok Hackathon to address the challenge of scaling global feature rollouts while ensuring compliance with dozens of geographic regulations.
🎥 Demo Video
[Link to your 3-minute YouTube demo video will go here]
⚖️ Problem Statement
As TikTok operates globally, every product feature must dynamically satisfy dozens of geographic regulations. Manually tracking which features are impacted by which laws is a significant challenge, leading to potential legal exposure, reactive firefighting, and manual overhead. This project aims to build a prototype that utilizes LLM capabilities to flag features requiring geo-specific compliance logic, turning regulatory detection from a blind spot into a traceable, auditable output.
✨ Our Solution
GeoCompliance Guardian is a web application that uses a Retrieval-Augmented Generation (RAG) architecture. Instead of relying on a generic LLM's knowledge, the system first retrieves relevant, up-to-date information from a curated knowledge base of specific regulations (e.g., DSA, GDPR, US state laws). This context is then provided to the LLM along with the feature description, enabling it to make a highly accurate and reasoned determination.
Key Features
Intelligent Analysis: Analyzes feature descriptions to detect potential needs for geo-specific compliance logic.
Structured Output: Provides a clear "Yes," "No," or "Uncertain" flag for each feature.
Clear Reasoning: Explains why a feature was flagged, citing the retrieved legal context.
Regulation Identification: Lists the potential regulations that may apply.
Audit-Ready: The output provides a clear, traceable record for compliance audits.
🛠️ Tech Stack
Language: Python
LLM: Google Gemini Pro via Google AI Studio API
Core Framework: LangChain for RAG pipeline orchestration
Frontend: Streamlit for the interactive web demo
Vector Embeddings: sentence-transformers (all-MiniLM-L6-v2)
Vector Database: ChromaDB for local, persistent storage
🚀 How to Set Up and Run a Local Demo
Follow these steps to get the GeoCompliance Guardian running on your local machine.
Prerequisites
Python 3.8+ installed
Git installed
Step 1: Clone the Repository
Open your terminal and clone the public GitHub repository:
code
Bash
git clone [Your-GitHub-Repo-Link-Here]
cd geocompliance-guardian
Step 2: Set Up the Python Virtual Environment
Create and activate a virtual environment to manage project dependencies.
On macOS / Linux:
code
Bash
python3 -m venv venv
source venv/bin/activate
```*   **On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
Step 3: Install All Dependencies
Install all the required libraries using the requirements.txt file.
code
Bash
pip install -r requirements.txt
Step 4: Add Your Google API Key
The application requires a Google Gemini API key to function.
Create a file named .env in the root of the project directory.
Add your API key to this file in the following format:
code
Code
GOOGLE_API_KEY="your_actual_api_key_here"
IMPORTANT: The .gitignore file is configured to ignore .env, so your secret key will not be committed to Git.
Step 5: Build the Knowledge Base Vector Store
Before running the app, you need to process the legal documents in the knowledge_base folder and create the local vector database.
Run the following script:
code
Bash
python prepare_knowledge_base.py
This will create a chroma_db_store directory in your project folder. You only need to run this script once, or whenever you update the files in the knowledge_base folder.
Step 6: Run the Streamlit Application
You are now ready to launch the web application!
code
Bash
streamlit run app.py
Your web browser should automatically open a new tab with the running application. If not, your terminal will provide a local URL (usually http://localhost:8501) that you can visit.
📖 How to Use the App
Once the app is running, you will see a text area.
Paste a feature description into the text area (you can find examples in the data/test_dataset.csv file).
Click the "Check Compliance" button.
The system will process the request and display the results: the Flag, the Reasoning, and any Related Regulations.