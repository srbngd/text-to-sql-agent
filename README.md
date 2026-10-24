# Autonomous Text-to-SQL Business Intelligence Agent 📊

**Author:** Shiv Raj Bangad  
**Term:** Fall 2026 Independent Study (Purdue University)  
**Advisor:** Dr. Gary Mercado  

## Project Overview
This repository contains the codebase for an Autonomous Text-to-SQL Business Intelligence Agent. The system democratizes enterprise data access by allowing non-technical stakeholders to ask complex business questions in plain English. The agent translates these queries into optimized SQL, executes them against a relational database, and returns human-readable summaries.

## System Architecture
* **Database:** SQLite (`enterprise.db`) containing 10,000+ synthetic transactional records.
* **Orchestration:** LangChain (`create_sql_agent`) operating on a ReAct (Reasoning and Acting) loop.
* **LLM Backend:** OpenAI API (`gpt-3.5-turbo` / `gpt-4o-mini`).
* **Semantic Router:** ChromaDB vector database used to dynamically retrieve relevant table schemas and bypass token limits.
* **Frontend:** Streamlit web application.

## Repository Contents
* `create_db.py` & `generate_data.py`: Scripts used to engineer the database and scale to 10,000+ enterprise records.
* `build_router.py`: Constructs the ChromaDB vector store for semantic schema routing.
* `run_agent.py`: The core LangChain ReAct execution loop.
* `app.py`: The interactive Streamlit dashboard.
* `requirements.txt`: Python package dependencies.

## How to Run Locally
1. **Clone the repository and navigate to the project directory:**
   ```bash
   git clone https://github.com/your-username/text-to-sql-agent.git
   cd text-to-sql-agent
   ```

2. **Activate your virtual environment and install dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Add your API Key:**
   Ensure you set your OpenAI API key in `app.py` or export it in your environment:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. **Launch the Application:**
   ```bash
   python3 -m streamlit run app.py
   ```
