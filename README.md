# RegTok

![Hackathon](https://img.shields.io/badge/Hackathon-TikTok-blue)
![Python](https://img.shields.io/badge/Language-Python-3776AB)
![LLM](https://img.shields.io/badge/LLM-Google%20Gemini%20Pro%202.5-orange)

**A prototype system that uses a Retrieval-Augmented Generation (RAG) LLM to automatically flag software features that require geo-specific legal compliance logic.**

[🎥 Demo Video](Your-YouTube-Link-Here)

---

## ⚖️ Problem Statement

As TikTok operates globally, every product feature must dynamically satisfy dozens of geographic regulations. Manually tracking which features are impacted by which laws is a significant challenge, leading to:

- Potential legal exposure
- Reactive firefighting
- Manual overhead in scaling feature rollouts

**Goal:** Build a prototype system that utilizes LLM capabilities to flag features requiring geo-specific compliance logic, turning regulatory detection from a blind spot into a traceable, auditable output.

---

## ✨ Our Solution

**GeoCompliance Guardian** is a web application that leverages a Retrieval-Augmented Generation (RAG) architecture:

1. **Retrieval:** Retrieves relevant, up-to-date information from a curated knowledge base of specific regulations (e.g., DSA, GDPR, US state laws).
2. **Reasoning:** Provides the retrieved context to an LLM along with the feature description.
3. **Decision:** Produces accurate, reasoned outputs flagging compliance needs.

---

### Key Features

- **Intelligent Analysis:** Detects potential geo-specific compliance requirements from feature descriptions.
- **Structured Output:** Provides clear `"Yes"`, `"No"`, or `"Uncertain"` flags.
- **Clear Reasoning:** Explains why a feature was flagged, citing retrieved legal context.
- **Regulation Identification:** Lists potential regulations that may apply.
- **Audit-Ready:** Generates traceable outputs suitable for compliance audits.

---

## 🛠️ Tech Stack

- **Language:** Python
- **LLM:** Google Gemini Pro via Google AI Studio API
- **Core Framework:** LangChain for RAG pipeline orchestration
- **Frontend:** Streamlit for interactive web demo
- **Vector Embeddings:** `sentence-transformers` (all-MiniLM-L6-v2)
- **Vector Database:** ChromaDB for local, persistent storage

---

## 🏗️ System Architecture

+---------------------+
| Feature Description |
| (PRD/TRD) |
+----------+----------+
|
v
+---------------------+
| Retrieval Module |
| (Vector DB: Chroma)|
+----------+----------+
|
v
+---------------------+
| LLM Reasoning |
| (Google Gemini Pro)|
+----------+----------+
|
v
+---------------------+
| Structured Output |
| - Flag: Yes/No/? |
| - Reasoning |
| - Related Regulations|
+----------+----------+
|
v
+---------------------+
| Audit & CSV Logging|
+---------------------+
---


## 🚀 Setup & Local Demo

Follow these steps to run GeoCompliance Guardian locally:

### Prerequisites

- Python 3.8+
- Git

### Step 1: Clone the Repository

```bash
git clone [Your-GitHub-Repo-Link-Here]
cd geocompliance-guardian
```
### Step 2: Set Up Python Virtual Environment

macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:
```bash
python -m venv venv
source venv/Scripts/activate 
```
### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Add Your Google AI Studio API Key
Create a `.env` file in the project root:
```env
GOOGLE_API_KEY="your_actual_api_key_here"
```
| Note: `.gitignore` is configured to ignore `.env` already to protect your secret key.

### Step 5 (Optional): Building the Knowledge Base Vector Store
Run this script whenever there is any chances or updates to the knowledge base files
```bash
python prepare_knowledge_base.py
```

### Step 6: Run the streamlit application
```bash
streamlit run app.py
```
Your browser should automatically open the app.

## How to use the app

1) Paste a feature description into the text area (examples in data/test_dataset.csv)
2) Click <b>Check Compliance</b>
3) The system outputs:
   1) Flag: "Yes", "No" or "Uncertain"
   2) Reasoning: Explanation of the decision
   3) Related Regulations: Optional Regulations detected