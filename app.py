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

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Data Explorer | Business Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Bespoke, Minimalist, Human-Designed UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Hide Streamlit default header & deploy button */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* App background */
    .stApp {
        background-color: #0b0d11;
        color: #e4e4e7;
    }
    
    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 880px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f1217;
        border-right: 1px solid #1e222b;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
        padding-left: 1.25rem;
        padding-right: 1.25rem;
    }
    
    .sidebar-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #71717a;
        margin-bottom: 8px;
    }
    
    /* Source connection card */
    .source-card {
        background: #141820;
        border: 1px solid #232936;
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 16px;
    }
    
    .source-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    
    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10b981;
        flex-shrink: 0;
    }
    
    .source-name {
        font-size: 13px;
        font-weight: 600;
        color: #f4f4f5;
    }
    
    .source-meta {
        font-size: 12px;
        color: #71717a;
        padding-left: 15px;
    }
    
    .table-badge {
        display: inline-block;
        background: #181c25;
        border: 1px solid #272d3b;
        color: #a1a1aa;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        margin: 3px 4px 3px 0;
    }
    
    /* Header typography */
    .app-title {
        font-size: 24px;
        font-weight: 600;
        letter-spacing: -0.025em;
        color: #fafafa;
        margin: 0 0 4px 0;
    }
    
    .app-subtitle {
        font-size: 14px;
        color: #71717a;
        margin: 0 0 24px 0;
    }
    
    .section-label {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #52525b;
        margin-bottom: 12px;
    }
    
    /* Query suggestion cards */
    div[data-testid="stButton"] > button {
        background-color: #141820;
        border: 1px solid #232936;
        border-radius: 8px;
        color: #d4d4d8;
        font-size: 13.5px;
        font-weight: 400;
        text-align: left;
        padding: 14px 16px;
        width: 100%;
        transition: all 0.15s ease-in-out;
        box-shadow: none;
    }
    
    div[data-testid="stButton"] > button:hover {
        background-color: #1a202c;
        border-color: #3b4252;
        color: #ffffff;
    }
    
    /* Attach data popover button */
    div[data-testid="stPopover"] > button {
        background-color: #181c26 !important;
        border: 1px solid #2b3242 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 6px 14px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: #222836 !important;
        border-color: #3f475c !important;
        color: #ffffff !important;
    }
    
    /* Attached file badge */
    .attached-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(56, 189, 248, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #38bdf8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
    }
    
    /* Clear button */
    .clear-btn button {
        background: transparent !important;
        border: 1px solid #272d3b !important;
        color: #71717a !important;
        font-size: 12px !important;
        padding: 6px 12px !important;
        border-radius: 6px !important;
    }
    .clear-btn button:hover {
        color: #e4e4e7 !important;
        border-color: #3f3f46 !important;
    }
    
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 12px 0 !important;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12.5px !important;
        background-color: #11141a !important;
        border: 1px solid #1f242e !important;
        border-radius: 6px !important;
    }
    
    div[data-testid="stChatInput"] {
        border-radius: 8px;
        border: 1px solid #272d3b;
        background-color: #141820;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #3f4656;
    }
</style>
""", unsafe_allow_html=True)

# Custom callback to capture SQL
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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Session state setup
if "custom_db_uri" not in st.session_state:
    st.session_state["custom_db_uri"] = None
if "custom_db_label" not in st.session_state:
    st.session_state["custom_db_label"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Resolve active database URI
if st.session_state["custom_db_uri"]:
    active_db_uri = st.session_state["custom_db_uri"]
    db_display_name = st.session_state["custom_db_label"]
else:
    active_db_uri = "sqlite:///enterprise.db"
    db_display_name = "enterprise.db"

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown('<div class="sidebar-label">Data Connection</div>', unsafe_allow_html=True)
    
    # Active connection indicator
    meta_subtext = "Active Database"
    if active_db_uri == "sqlite:///enterprise.db":
        meta_subtext = "Default • 10,268 records"
    elif st.session_state["custom_db_label"]:
        meta_subtext = "Custom Uploaded Data"

    st.markdown(f"""
    <div class="source-card">
        <div class="source-row">
            <span class="status-dot"></span>
            <span class="source-name">{db_display_name}</span>
        </div>
        <div class="source-meta">{meta_subtext}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state["custom_db_uri"]:
        if st.button("↺ Switch back to Enterprise DB", use_container_width=True):
            st.session_state["custom_db_uri"] = None
            st.session_state["custom_db_label"] = None
            st.session_state["messages"] = []
            st.rerun()

    # Remote URI connection
    with st.expander("Connect via Remote URI", expanded=False):
        uri_input = st.text_input("Database URI", placeholder="postgresql://user:pass@host/db")
        if st.button("Connect URI", use_container_width=True):
            if uri_input:
                st.session_state["custom_db_uri"] = uri_input
                st.session_state["custom_db_label"] = "Remote Database"
                st.session_state["messages"] = []
                st.rerun()

    # OpenAI Key
    if not os.environ.get("OPENAI_API_KEY"):
        st.markdown('<div class="sidebar-label" style="margin-top:20px;">OpenAI API Key</div>', unsafe_allow_html=True)
        key_input = st.text_input("API Key", type="password", placeholder="sk-...", label_visibility="collapsed")
        if key_input:
            os.environ["OPENAI_API_KEY"] = key_input

# Connect database & load agent
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

db_instance, agent_instance, conn_err = load_db_and_agent(active_db_uri)

# Render tables in sidebar
with st.sidebar:
    if conn_err:
        st.error(f"Connection failed: {conn_err}")
    elif db_instance:
        table_names = db_instance.get_usable_table_names()
        st.markdown('<div class="sidebar-label" style="margin-top:16px;">Tables in Schema</div>', unsafe_allow_html=True)
        badges_html = "".join([f'<span class="table-badge">{t}</span>' for t in table_names])
        st.markdown(badges_html, unsafe_allow_html=True)
        
        with st.expander("Schema details", expanded=False):
            st.code(db_instance.get_table_info()[:800] + ("..." if len(db_instance.get_table_info()) > 800 else ""), language="sql")

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- MAIN VIEW -----------------
st.markdown('<h1 class="app-title">Enterprise BI Agent</h1>', unsafe_allow_html=True)
st.markdown('<p class="app-subtitle">Query structured relational databases using natural language.</p>', unsafe_allow_html=True)

# Main action toolbar with Add / Upload Icon Popover
col_attach, col_status = st.columns([1.3, 4])

with col_attach:
    with st.popover("＋ Attach Data (.db, .csv)", help="Upload a SQLite database file or CSV spreadsheets"):
        st.markdown("#### Upload Custom Database")
        st.caption("Upload a `.db`, `.sqlite`, or one or more `.csv` files to query with SQL.")
        
        uploaded_files = st.file_uploader(
            "Select files",
            type=["db", "sqlite", "sqlite3", "csv"],
            accept_multiple_files=True,
            key="main_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            # Check if any .db or .sqlite uploaded
            db_files = [f for f in uploaded_files if f.name.endswith(('.db', '.sqlite', '.sqlite3'))]
            csv_files = [f for f in uploaded_files if f.name.endswith('.csv')]
            
            if db_files:
                target_db = db_files[0]
                dest = os.path.join(UPLOAD_DIR, target_db.name)
                with open(dest, "wb") as f:
                    f.write(target_db.getbuffer())
                st.session_state["custom_db_uri"] = f"sqlite:///{dest}"
                st.session_state["custom_db_label"] = target_db.name
                st.session_state["messages"] = []
                st.success(f"Connected to {target_db.name}")
                st.rerun()
            elif csv_files:
                csv_db_path = os.path.join(UPLOAD_DIR, "csv_warehouse.db")
                if os.path.exists(csv_db_path):
                    try:
                        os.remove(csv_db_path)
                    except Exception:
                        pass
                conn = sqlite3.connect(csv_db_path)
                table_names_created = []
                for f in csv_files:
                    tname = re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(f.name)[0])
                    df = pd.read_csv(f)
                    df.to_sql(tname, conn, if_exists="replace", index=False)
                    table_names_created.append(tname)
                conn.close()
                st.session_state["custom_db_uri"] = f"sqlite:///{csv_db_path}"
                st.session_state["custom_db_label"] = f"{', '.join(table_names_created)} (CSV)"
                st.session_state["messages"] = []
                st.success(f"Loaded {len(table_names_created)} table(s)")
                st.rerun()

with col_status:
    if st.session_state["custom_db_label"]:
        st.markdown(f"""
        <div style="padding-top: 4px;">
            <span class="attached-badge">📎 Attached: {st.session_state['custom_db_label']}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding-top: 7px; font-size: 13px; color: #71717a;">
            Using pre-loaded Enterprise Database (10,000 orders)
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

prompt_to_run = None

# If chat is empty, show clean, understated query suggestions
if len(st.session_state["messages"]) == 0:
    st.markdown('<div class="section-label">Suggested Questions</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Top 3 customers by total spend", use_container_width=True):
            prompt_to_run = "Can you list the top 3 customers by their total spend, and include their customer segment?"
        if st.button("Top 5 best-selling products by volume", use_container_width=True):
            prompt_to_run = "What are the top 5 most popular products by total quantity ordered?"

    with col2:
        if st.button("Highest revenue product category", use_container_width=True):
            prompt_to_run = "Which product category generated the highest total revenue, and what was that amount?"
        if st.button("Order volume comparison: 2025 vs 2026", use_container_width=True):
            prompt_to_run = "How many total orders were placed in 2025 compared to 2026?"

# Render conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg and msg["sql"]:
            with st.expander("View generated SQL", expanded=False):
                st.code(msg["sql"], language="sql")

# Chat input at bottom
user_input = st.chat_input("Ask a question about your data...")
if user_input:
    prompt_to_run = user_input

# Handle query execution
if prompt_to_run:
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("OpenAI API key is missing. Add it in the sidebar.")
    elif not agent_instance:
        st.error("No active database connection found.")
    else:
        # Display user question
        st.session_state["messages"].append({"role": "user", "content": prompt_to_run})
        with st.chat_message("user"):
            st.markdown(prompt_to_run)

        # Assistant thinking & execution
        with st.chat_message("assistant"):
            handler = SQLInspectorHandler()
            with st.spinner("Generating SQL query and retrieving data..."):
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
                with st.expander("View generated SQL", expanded=False):
                    st.code(executed_sql, language="sql")

            st.session_state["messages"].append({
                "role": "assistant",
                "content": answer,
                "sql": executed_sql
            })