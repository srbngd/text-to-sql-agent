# Autonomous "Text-to-SQL" Business Intelligence Agent

**Student Name:** Shiv Raj Bangad  
**Supervising Faculty:** Dr. Gary Mercado  
**Course:** Independent Study (2 Credits) – Fall 2026  

---

### 1. Abstract

As enterprise data environments scale, non-technical business stakeholders increasingly rely on data engineering teams to write SQL queries for routine reporting, creating significant operational bottlenecks. This independent study addresses this inefficiency by developing an Autonomous Text-to-SQL Business Intelligence Agent. Utilizing Large Language Models (LLMs) orchestrated via LangChain, the system translates natural language queries into optimized, executable SQL. By combining a ReAct (Reasoning and Acting) execution loop with a semantic schema router built on ChromaDB, the agent securely navigates relational databases to retrieve, aggregate, and summarize data. Deployed via a Streamlit web interface, this project successfully demonstrates a scalable approach to democratizing enterprise data access, resolving traditional Business Intelligence reporting delays.

---

### 2. Background and Problem Statement

Modern analytical pipelines increasingly rely on data engineers to extract structured insights to answer routine business questions. The standard workflow—where a sales manager submits a ticket for a report and waits days for an analyst to write the SQL—is computationally inefficient and operationally slow. Moving these workflows from manual scripting to automated, production-ready systems presents engineering bottlenecks: high inference latency, context-window limitations, and the challenge of surfacing insights to non-technical stakeholders in real time. This project solves this by building an AI-powered agent that translates natural language questions into optimized SQL queries, executes them securely, and summarizes the results instantly.

---

### 3. System Architecture and Scope of Work

The foundation of the agent was constructed in a local Python virtual environment (`venv`) on macOS to simulate a secure, firewalled enterprise architecture. The end-to-end pipeline consists of the following components:

* **Data & Environment:** A local SQLite database (`enterprise.db`) was engineered to simulate a production data warehouse (such as PostgreSQL or BigQuery). It contains scaled relational tables (`Customers`, `Products`, `Orders`) populated with 10,000 synthetically generated transactional records.
* **LLM Orchestration:** LangChain was utilized to bridge the database and the OpenAI API. The agent was configured using LangChain’s `create_sql_agent` toolkit operating on a ReAct framework. When a user submits a query, the AI inspects the database dialect, writes the SQL, executes it locally, observes the raw data output, and translates the structured data back into a human-readable summary.
* **Autonomous Error Recovery:** If the LLM generates invalid SQL syntax, it reads the traceback error and rewrites the query before returning a response to the user.

---

### 4. Semantic Routing for Context Window Optimization

A primary limitation of standard Text-to-SQL generation is the LLM context window. Passing an entire enterprise database schema containing hundreds of tables into a prompt is computationally inefficient and exceeds token limits.

To resolve this, a Semantic Schema Router was implemented. Using ChromaDB and OpenAI’s `text-embedding-3-small` model, plain-English metadata descriptions of each database table were embedded into a local vector space. When a user asks a question, the agent performs a similarity search against the vector database first, retrieving only the schemas of the tables most relevant to the user's intent. This modular retrieval-augmented generation (RAG) approach ensures the LLM receives highly targeted schema context, minimizing token consumption and latency.

---

### 5. Benchmarking & Results

The system was deployed into a local web application using Streamlit (`app.py`). To benchmark the agent's performance, it was subjected to complex, multi-table queries that required advanced `JOIN` operations and aggregations.

#### Test Case 1: Complex Aggregation

* **Query:** "Can you list the top 3 customers by their total spend, and include their customer segment?"
* **Result:** The agent successfully retrieved the `Customers`, `Orders`, and `Products` schemas, applied the correct multiplier (`price * quantity`), grouped by customer name, and returned the top three results accurately. *(See Figure 1)*

![Figure 1: Agent executing a multi-table JOIN and aggregation](figure1_top_customers.png)

*Figure 1: Agent executing a multi-table JOIN and aggregation.*

#### Test Case 2: Conditional Filtering

* **Query:** "Which product category generated the highest total revenue, and what was that amount?"
* **Result:** The agent effectively linked product IDs to transactional quantities, summarized the revenue, and translated the highest value into a natural language response. *(See Figure 2)*

![Figure 2: Agent filtering and aggregating revenue by category](figure2_category_revenue.png)

*Figure 2: Agent filtering and aggregating revenue by category.*

---

### 6. Business Impact & Final Outcomes

The deployment of this autonomous BI agent offers substantial enterprise value. By abstracting the SQL generation process behind an intuitive conversational interface, non-technical stakeholders—such as sales managers and marketing executives—can perform real-time data analysis without writing code. This system effectively eliminates the traditional reporting ticketing queue, saving data engineering and analytics teams hundreds of hours in ad-hoc query requests while accelerating data-driven decision-making across the organization. The successful completion of this pipeline demonstrates the integration of modern LLMs within a robust analytical framework, fulfilling all objectives set forth in the Fall 2026 Independent Study Plan.
