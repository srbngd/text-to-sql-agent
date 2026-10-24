import streamlit as st
import os
import re
import sqlite3
import ast
import pandas as pd
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.callbacks import BaseCallbackHandler

# 1. Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Text-to-SQL Business Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS for a modern, sleek, intuitive UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main container clean spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1000px;
    }
    
    /* Top Header Badge Styling */
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #38bdf8;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        margin-bottom: 0.75rem;
    }
    
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 8px;
        background: #111827;
        border: 1px solid #1f2937;
        font-size: 0.85rem;
        color: #e5e7eb;
        margin-bottom: 1rem;
        width: 100%;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 10px #10b981;
        display: inline-block;
    }
    
    /* Question card buttons */
    div[data-testid="stButton"] > button {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: #141923;
        color: #f3f4f6;
        padding: 0.75rem 1rem;
        font-size: 0.9rem;
        font-weight: 500;
        text-align: left;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    
    div[data-testid="stButton"] > button:hover {
        border-color: #38bdf8;
        background: #1e293b;
        color: #ffffff;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(56, 189, 248, 0.15);
    }
    
    /* Code blocks */
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Chat message spacing */
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Callback handler to capture executed SQL cleanly
class SQLInspectorHandler(BaseCallbackHandler):
    def __init__(self):
        self.sql_queries = []

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "")
        if "sql_db_query" in name or "sql" in name.lower():
            query_text = None
            if isinstance(input_str, dict):
                query_text = input_str.get("query")
            elif isinstance(input_str, str):
                try:
                    parsed = ast.literal_eval(input_str)
                    if isinstance(parsed, dict) and "query" in parsed:
                        query_text = parsed["query"]
                except Exception:
                    query_text = input_str
            if query_text and query_text not in self.sql_queries:
                self.sql_queries.append(query_text.strip())

# Setup local storage directory for uploaded DBs
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 3. Sidebar: Simple & Intuitive Configuration
with st.sidebar:
    st.markdown("### 🗄️ Database Source")
    
    source_type = st.selectbox(
        "Select active data source",
        [
            "🏢 Demo Enterprise Warehouse (10,000 Records)",
            "💾 Upload SQLite DB (.db, .sqlite)",
            "📄 Upload CSV Files (Auto-Warehouse)",
            "🔗 Remote Database Connection URI"
        ],
        index=0,
        label_visibility="collapsed"
    )

    active_db_uri = None
    db_display_name = ""

    if source_type == "🏢 Demo Enterprise Warehouse (10,000 Records)":
        active_db_uri = "sqlite:///enterprise.db"
        db_display_name = "enterprise.db"

    elif source_type == "💾 Upload SQLite DB (.db, .sqlite)":
        uploaded_db = st.file_uploader(
            "Upload SQLite File",
            type=["db", "sqlite", "sqlite3"],
            help="Upload your SQLite database"
        )
        if uploaded_db:
            dest = os.path.join(UPLOAD_DIR, uploaded_db.name)
            with open(dest, "wb") as f:
                f.write(uploaded_db.getbuffer())
            active_db_uri = f"sqlite:///{dest}"
            db_display_name = uploaded_db.name
        else:
            st.info("Upload a `.db` or `.sqlite` file above.")

    elif source_type == "📄 Upload CSV Files (Auto-Warehouse)":
        uploaded_csvs = st.file_uploader(
            "Upload CSV File(s)",
            type=["csv"],
            accept_multiple_files=True,
            help="Each CSV file will become a queryable table"
        )
        if uploaded_csvs:
            csv_db_path = os.path.join(UPLOAD_DIR, "csv_warehouse.db")
            if os.path.exists(csv_db_path):
                try:
                    os.remove(csv_db_path)
                except Exception:
                    pass
            conn = sqlite3.connect(csv_db_path)
            created_tables = []
            for f in uploaded_csvs:
                tname = re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(f.name)[0])
                df = pd.read_csv(f)
                df.to_sql(tname, conn, if_exists="replace", index=False)
                created_tables.append(tname)
            conn.close()
            active_db_uri = f"sqlite:///{csv_db_path}"
            db_display_name = f"CSV Warehouse ({len(created_tables)} tables)"
        else:
            st.info("Upload CSV files to convert into a SQL warehouse.")

    elif source_type == "🔗 Remote Database Connection URI":
        uri = st.text_input("Database URI", value="sqlite:///enterprise.db")
        if uri:
            active_db_uri = uri
            db_display_name = "Remote SQL DB"

    # API Key check in sidebar
    if not os.environ.get("OPENAI_API_KEY"):
        st.markdown("---")
        st.markdown("### 🔑 API Key Required")
        key_input = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
        if key_input:
            os.environ["OPENAI_API_KEY"] = key_input

# Connect to database & create agent
@st.cache_resource(show_spinner=False)
def load_db_and_agent(uri: str):
    try:
        db = SQLDatabase.from_uri(uri)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = create_sql_agent(
            llm=llm,
            db=db,
            agent_type="openai-tools",
            verbose=False
        )
        return db, agent, None
    except Exception as e:
        return None, None, str(e)

db_instance = None
agent_instance = None

if active_db_uri:
    db_instance, agent_instance, conn_err = load_db_and_agent(active_db_uri)

with st.sidebar:
    if conn_err:
        st.error(f"Connection Error: {conn_err}")
    elif db_instance:
        table_names = db_instance.get_usable_table_names()
        st.markdown(f"""
        <div class="status-pill">
            <span class="pulse-dot"></span>
            <div>
                <strong style="color:#ffffff;">{db_display_name}</strong><br/>
                <span style="color:#9ca3af; font-size:0.75rem;">Connected • {len(table_names)} Tables Available</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 Inspect Tables & Columns", expanded=False):
            for t in table_names:
                st.markdown(f"**`{t}`**")
            st.divider()
            st.caption("Schema Preview:")
            st.code(db_instance.get_table_info()[:800] + ("..." if len(db_instance.get_table_info()) > 800 else ""), language="sql")

    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# 4. Main Page Header
st.markdown("""
<div class="hero-badge">⚡ Autonomous Business Intelligence</div>
<h1 style="margin-top:0; margin-bottom:0.25rem; font-size:2rem; font-weight:700;">Text-to-SQL Analytics Agent</h1>
<p style="color:#94a3b8; font-size:1rem; margin-bottom:1.5rem;">
Ask questions in plain English. The agent reasons, generates validated SQL, and extracts actionable insights instantly.
</p>
""", unsafe_allow_html=True)

# Track database switch
if "last_db" not in st.session_state:
    st.session_state["last_db"] = active_db_uri
elif st.session_state["last_db"] != active_db_uri:
    st.session_state["last_db"] = active_db_uri
    st.session_state["messages"] = []

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Quick suggestion prompt to run
prompt_to_run = None

# If chat is empty, show intuitive sample query cards
if len(st.session_state["messages"]) == 0:
    st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#e2e8f0; margin-bottom:0.5rem;'>💡 Suggested Questions to Get Started:</p>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏆 Top 3 Customers by Total Spend\n\n*(Multi-table JOIN & aggregation)*", use_container_width=True):
            prompt_to_run = "Can you list the top 3 customers by their total spend, and include their customer segment?"
        if st.button("📦 Top 5 Best-Selling Products\n\n*(Quantity ordered volume)*", use_container_width=True):
            prompt_to_run = "What are the top 5 most popular products by total quantity ordered?"

    with col2:
        if st.button("💰 Highest Revenue Product Category\n\n*(Category revenue aggregation)*", use_container_width=True):
            prompt_to_run = "Which product category generated the highest total revenue, and what was that amount?"
        if st.button("📈 2025 vs 2026 Order Trends\n\n*(Time-series order volume count)*", use_container_width=True):
            prompt_to_run = "How many total orders were placed in 2025 compared to 2026?"

# Display existing chat messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg and msg["sql"]:
            with st.expander("🔍 View Generated SQL Query", expanded=False):
                st.code(msg["sql"], language="sql")

# Text chat input
user_chat = st.chat_input("Ask a question about your data... (e.g., 'What were total sales last month?')")
if user_chat:
    prompt_to_run = user_chat

# Execute query if triggered via card click or chat bar
if prompt_to_run:
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("Please provide an OpenAI API key in the sidebar.")
    elif not agent_instance:
        st.error("No database is currently connected.")
    else:
        # 1. Display User Message
        st.session_state["messages"].append({"role": "user", "content": prompt_to_run})
        with st.chat_message("user"):
            st.markdown(prompt_to_run)

        # 2. Assistant Thinking & Execution
        with st.chat_message("assistant"):
            handler = SQLInspectorHandler()
            with st.spinner("🤖 Translating query to SQL & querying database..."):
                try:
                    res = agent_instance.invoke(
                        {"input": prompt_to_run},
                        {"callbacks": [handler]}
                    )
                    answer = res["output"]
                except Exception as e:
                    answer = f"Error processing query: {str(e)}"

            st.markdown(answer)
            executed_sql = "\n\n".join(handler.sql_queries) if handler.sql_queries else None
            if executed_sql:
                with st.expander("🔍 View Generated SQL Query", expanded=False):
                    st.code(executed_sql, language="sql")

            # Save in history
            st.session_state["messages"].append({
                "role": "assistant",
                "content": answer,
                "sql": executed_sql
            })