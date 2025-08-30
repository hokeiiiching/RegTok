RegTok

A prototype system that uses a self-evolving, Retrieval-Augmented
Generation (RAG) LLM to automatically flag software features that
require geo-specific legal compliance logic, complete with audit-ready
citations.

🎥 Watch the Demo Video

⚖️ The Problem: Turning a Blind Spot into a Strength

As a global platform like TikTok, every new product feature must
navigate a complex web of geographic regulations---from Brazil's data
localization to GDPR. Manually tracking which features are impacted by
which laws is a monumental challenge that creates significant risk:

⚖️ Legal Exposure: Undetected compliance gaps can lead to fines and
legal action.

🛑 Reactive Firefighting: Scrambling for answers when auditors or
regulators inquire.

🚧 Manual Overhead: Scaling global feature rollouts becomes slow and
inefficient.

This project addresses the official TikTok TechJam 2025 problem
statement: "Build a prototype system that utilizes LLM capabilities to
flag features that require geo-specific compliance logic; turning
regulatory detection from a blind spot into a traceable, auditable
output."

✨ Our Solution: RegTok

RegTok is a web application that provides an intelligent, auditable, and
self-evolving solution to this problem. It uses a sophisticated
architecture to deliver compliance analysis you can trust.

At its core, RegTok analyzes a feature description, retrieves relevant
legal texts from a specialized knowledge base, and uses a powerful Large
Language Model (LLM) to determine if geo-specific logic is required.

Key Features

Source-Backed Citations: Goes beyond just flagging; every analysis links
directly to the specific source document(s) from the knowledge base,
providing bullet-proof evidence for audits.

Self-Evolving Agent: The system learns from human feedback. When an
expert corrects an analysis, that correction is used as a high-quality
"golden example" to make the AI more accurate on future queries using
dynamic few-shot prompting.

Human-in-the-Loop (HITL) Workflow: A complete feedback loop allows
compliance experts to approve or edit the AI's findings. All
interactions are tracked in a persistent audit log.

Jargon Expansion: Automatically expands internal codenames and ambiguous
abbreviations (e.g., "KR") with full explanations before analysis,
closing the context gap for the LLM.

Structured & Actionable Output: Provides a clear "Yes", "No", or
"Uncertain" flag with concise reasoning, a list of potentially related
regulations, and the auditable source citations.

🏗️ System Architecture

RegTok is built on a circular, self-improving RAG pipeline. It doesn't
just provide answers; it learns from them.

code

Code

+---------------------------+

| Feature Description (Input) \|

+-------------+-------------+

              |

              v

+-------------+-------------+ +--------------------------+

|  Query Expansion Module \|-----\>\| Terminologies CSV \|

| (Expands Internal Jargon) \| +--------------------------+

+-------------+-------------+

              |

              v

+-------------+-------------+ +--------------------------+

|   Retrieval Module (RAG) \|-----\>\| Vector DB (Chroma Cloud) \|

| (Finds Relevant Laws) \| \| (Knowledge Base) \|

+-------------+-------------+ +--------------------------+

              |

              v

+-------------+-------------+ +--------------------------+

|   LLM Reasoning (Gemini) \|\<-----\| Human Feedback Examples \|

| (Analyzes & Cites Sources)\| \| (From Audit Log DB) \|

+-------------+-------------+ +------------+-------------+

              |                                  ^

              v                                  |

+-------------+-------------+ \|

|  Structured Output (UI) \| \|

| - Flag, Reasoning, Cites \| \|

+-------------+-------------+ \|

              |                                  |

              v                                  |

+------------------------------------------------+-------------+

|               Human-in-the-Loop Feedback & Audit Log \|

|                       (SQLite Database) \|

+----------------------------------------------------------------+

🛠️ Project Details

This section breaks down the technical components as required by the
hackathon.

Development Tools Used

IDE: Visual Studio Code

Version Control: Git & GitHub

Environment Management: Python venv for dependency isolation

APIs Used

Google Gemini API: The core generative model (gemini-2.5-pro) for
analysis, reasoning, and structured JSON generation.

ChromaDB Cloud API: Used for connecting to the hosted vector database to
retrieve legal documents for the RAG pipeline.

Libraries Used

streamlit: For building the interactive web application and user
interface.

google-generativeai: The official Python SDK for interacting with the
Gemini API.

chromadb-client: The client library for connecting to and querying the
ChromaDB vector store.

sentence-transformers: For generating the high-quality vector embeddings
(all-MiniLM-L6-v2) that power the semantic search.

pandas: Used for data manipulation, particularly for reading the
jargon-mapping CSV and handling the audit log data.

langchain: Utilized in the prepare_knowledge_base.py script for
efficient document loading and text splitting.

python-dotenv: For securely managing API keys and environment variables.

sqlite3: The built-in Python library used for the persistent audit log
database.

Assets Used

knowledge_base/: A directory containing .txt files, where each file
represents a summarized legal document or regulation. This forms the
core knowledge the RAG system retrieves from.

Terminologies.csv: A CSV file that maps internal jargon, codenames, and
abbreviations to their full explanations.

test_dataset.csv: The provided dataset used for batch evaluation with
the evaluate.py script.

Additional Datasets

The primary dataset is the knowledge_base, which was custom-created for
this project by summarizing various legal texts into plain-language .txt
files. This curated dataset is fundamental to the system's ability to
provide accurate and relevant information.

🚀 Setup & Local Demo

Follow these steps to get RegTok running on your local machine.

Prerequisites

Python 3.9+

Git

Step 1: Clone the Repository

code

Bash

git clone https://github.com/your-username/your-repo-name.git

cd your-repo-name

Step 2: Get Your API Keys

You will need two sets of credentials:

Google AI Studio API Key:

Go to Google AI Studio.

Click Get API Key and create a new key.

ChromaDB Cloud Credentials:

Go to the ChromaDB Cloud Console.

Create a free account and a new deployment.

In the "Connection" tab of your deployment, find your API Key, Tenant,
and Database.

Step 3: Set Up the Environment

Create and activate a Python virtual environment:

code

Bash

# macOS / Linux

python3 -m venv venv

source venv/bin/activate

# Windows

python -m venv venv

.`\venv`{=tex}`\Scripts`{=tex}`\activate`{=tex}

Install the required dependencies:

code

Bash

pip install -r requirements.txt

Step 4: Configure Environment Variables

Create a file named .env in the root of the project folder and add your
credentials:

code

Env

# Google AI Studio

GOOGLE_API_KEY="your_google_api_key_here"

# ChromaDB Cloud

CHROMA_API_KEY="your_chroma_api_key_here"

CHROMA_TENANT="your_chroma_tenant_name"

CHROMA_DATABASE="your_chroma_database_name"

Step 5: Prepare Your Knowledge Base

Create a folder named knowledge_base in the project root.

Add your legal documents as .txt files inside this folder. The name of
each file will be used as its source citation.

Step 6: Build the Vector Store

Run the ingestion script to read your knowledge base, create embeddings,
and upload them to your ChromaDB Cloud instance.

code

Bash

python prepare_knowledge_base.py

Step 7: Run the Streamlit App

code

Bash

streamlit run app.py

Your browser will automatically open a new tab with the RegTok
application running.

🏃‍♀️ How to Use the App

Paste a feature description into the main text area.

Click Check Compliance.

The system will output a full analysis, including:

A color-coded Flag (Yes, No, or Uncertain).

Clear Reasoning for its decision.

Source Citations linking back to your knowledge base.

A list of potential Related Regulations.

Provide feedback by clicking Approve or Edit.

View all historical analyses in the Audit Log table.
