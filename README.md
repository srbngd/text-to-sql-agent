# Autonomous Text-to-SQL Business Intelligence Agent 📊

**Author:** Shiv Raj Bangad  
**Term:** Fall 2026 Independent Study (Purdue University)  
**Advisor:** Dr. Gary Mercado  

## Project Overview
This repository contains the codebase for an Autonomous Text-to-SQL Business Intelligence Agent. The system democratizes enterprise data access by allowing non-technical stakeholders to ask complex business questions in plain English. The agent translates these queries into optimized SQL, executes them against a relational database, and returns human-readable summaries.

## System Architecture
* **Database:** Multi-source support including default SQLite (`enterprise.db`) with 10,000+ synthetic transactional records, custom SQLite (`.db`/`.sqlite`) file uploads, CSV-to-SQL auto-warehouses, and custom connection URIs (PostgreSQL, MySQL, etc.).
* **Orchestration:** LangChain (`create_sql_agent`) operating on a ReAct (Reasoning and Acting) loop.
* **LLM Backend:** OpenAI API (`gpt-4o-mini`).
* **Semantic Router:** ChromaDB vector database used to dynamically retrieve relevant table schemas and bypass token limits.
* **Frontend:** Interactive Streamlit dashboard with real-time thought observation and schema inspection.

## Features
- 💬 **Plain-English Querying:** Converts natural language questions directly into optimized SQL.
- 🔄 **Multi-Database Support:**
  - **Pre-loaded Warehouse:** 10,000+ synthetic enterprise sales records across `Customers`, `Products`, and `Orders`.
  - **Custom SQLite Upload:** Drag and drop any `.db` or `.sqlite` database file.
  - **CSV Auto-Warehouse:** Upload one or more CSV files; the agent automatically structures them into SQL tables.
  - **Database URI Connection:** Connect directly to remote databases using standard SQL URIs.
- 🔍 **Schema Inspector:** View available tables, columns, and data types before querying.
- ⚙️ **Autonomous Error Recovery:** LLM inspects dialect and self-corrects invalid SQL queries via ReAct tracebacks.

## Repository Contents
* `create_db.py` & `generate_data.py`: Scripts used to engineer the database and scale to 10,000+ enterprise records.
* `build_router.py`: Constructs the ChromaDB vector store for semantic schema routing.
* `run_agent.py`: The core LangChain ReAct execution loop.
* `app.py`: The interactive Streamlit dashboard with custom database uploads.
* `requirements.txt`: Python package dependencies.

## How to Run Locally
1. **Clone the repository and navigate to the project directory:**
   ```bash
   git clone https://github.com/srbngd/text-to-sql-agent.git
   cd text-to-sql-agent
   ```

2. **Activate your virtual environment and install dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure your API Key:**
   Create a `.env` file or export your key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. **Launch the Application:**
   ```bash
   python3 -m streamlit run app.py
   ```
