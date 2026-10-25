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
    page_title="Enterprise BI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Bespoke Clean UI Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Hide Streamlit default chrome */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    
    .stApp {
        background-color: #0b0d11;
        color: #e4e4e7;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 880px;
    }
    
    /* Dataset Manager Card */
    .dataset-box {
        background: #12161f;
        border: 1px solid #222938;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 24px;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        display: inline-block;
        margin-right: 8px;
    }
    
    .badge-pill {
        background: #1e2533;
        color: #93c5fd;
        border: 1px solid #2e3a50;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        margin-left: 8px;
    }
    
    div[data-testid="stButton"] > button {
        background-color: #141820;
        border: 1px solid #232936;
        border-radius: 8px;
        color: #d4d4d8;
        font-size: 13.5px;
        font-weight: 400;
        text-align: left;
        padding: 12px 16px;
        width: 100%;
        transition: all 0.15s ease-in-out;
    }
    
    div[data-testid="stButton"] > button:hover {
        background-color: #1a202c;
        border-color: #3b4252;
        color: #ffffff;
    }
    
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 12px 0 !important;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        background-color: #11141a !important;
        border: 1px solid #1f242e !important;
        border-radius: 6px !important;
    }
    
    div[data-testid="stChatInput"] {
        border-radius: 8px;
        border: 1px solid #272d3b;
        background-color: #141820;
    }
</style>
""", unsafe_allow_html=True)

# 3. Callback handler to reliably capture generated SQL
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

# 4. Session State initialization
if "active_source" not in st.session_state:
    st.session_state["active_source"] = "default"  # "default" or "custom"
if "active_db_uri" not in st.session_state:
    st.session_state["active_db_uri"] = "sqlite:///enterprise.db"
if "dataset_name" not in st.session_state:
    st.session_state["dataset_name"] = "enterprise.db"
if "preview_df" not in st.session_state:
    st.session_state["preview_df"] = None
if "custom_table_names" not in st.session_state:
    st.session_state["custom_table_names"] = []
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Hello! I am your AI Business Intelligence analyst. I can answer any question about your data—calculating aggregations, discovering trends, or finding specific records. You can explore the pre-loaded 10,000 enterprise orders below, or upload your own CSV or SQLite file at the top!"}
    ]

# 5. Connect Database & Conversational Agent
@st.cache_resource(show_spinner=False)
def get_conversational_agent(uri: str):
    try:
        db = SQLDatabase.from_uri(uri)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        prefix = """You are an expert, conversational Business Intelligence analyst.
You have access to a structured database and a set of SQL tools.
Your goal is to answer ANY question the user asks about the active dataset accurately, insightfully, and conversationally.

IMPORTANT BEHAVIORAL INSTRUCTIONS:
1. GREETINGS & CASUAL QUESTIONS:
   If the user says 'hi', 'hello', 'who are you', or asks what you can do, greet them warmly and naturally. Mention the currently loaded dataset and suggest 2 or 3 interesting questions they can ask. Do NOT dump raw schemas or table columns unless explicitly requested.
2. ANSWERING DATA QUESTIONS:
   - For ANY analytical, statistical, filtering, or aggregative question: write and execute an optimized SQL query.
   - Present the answer clearly in plain English first with neatly formatted numbers (e.g. $1,450.00, 24 orders).
   - If relevant, provide a brief analytical takeaway or suggest a logical next step (e.g., 'Would you like to break this down by region or date?').
3. UNSEEN DATA & SCHEMAS:
   - You can tackle any dataset! Always check the available tables and columns using your tools, and write custom queries for whatever columns exist in the active database.
"""
        agent = create_sql_agent(
            llm=llm,
            db=db,
            agent_type="openai-tools",
            prefix=prefix,
            verbose=False
        )
        return db, agent, None
    except Exception as e:
        return None, None, str(e)

# ----------------- MAIN VIEW -----------------
st.markdown('<h1 style="font-size:24px; font-weight:600; margin-bottom:4px; color:#fafafa;">Enterprise BI Agent</h1>', unsafe_allow_html=True)
st.markdown('<p style="font-size:14px; color:#71717a; margin-bottom:16px;">Ask questions in plain English across the default warehouse or any custom dataset you upload.</p>', unsafe_allow_html=True)

# ----------------- PROMINENT DATASET MANAGER (VISIBLE ON SCREEN) -----------------
with st.container():
    tab_default, tab_upload = st.tabs(["🏢 Pre-Loaded Enterprise DB (10,000 Records)", "📁 Upload Custom Dataset (.csv, .sqlite, .db)"])

    # TAB 1: DEFAULT ENTERPRISE DATASET
    with tab_default:
        col_info, col_btn = st.columns([4, 1.5])
        with col_info:
            is_active = (st.session_state["active_source"] == "default")
            dot = '<span class="status-dot"></span>' if is_active else '<span style="color:#71717a;">○ </span>'
            status_text = '<strong style="color:#ffffff;">Active Dataset: enterprise.db</strong>' if is_active else '<span style="color:#a1a1aa;">enterprise.db</span>'
            st.markdown(f"""
            <div style="padding-top:6px;">
                {dot}{status_text} <span class="badge-pill">10,000 Orders</span>
                <p style="font-size:12.5px; color:#71717a; margin:4px 0 0 0;">
                    Scaled relational tables: <code>Customers</code> (250), <code>Products</code> (18), <code>Orders</code> (10,000).
                </p>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if not is_active:
                if st.button("Use Enterprise DB", key="btn_use_default"):
                    st.session_state["active_source"] = "default"
                    st.session_state["active_db_uri"] = "sqlite:///enterprise.db"
                    st.session_state["dataset_name"] = "enterprise.db"
                    st.session_state["preview_df"] = None
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": "Switched back to the default **enterprise.db** (10,000 synthetic records across Customers, Products, and Orders). How can I assist you with this data?"
                    })
                    st.rerun()

    # TAB 2: UPLOAD CUSTOM DATASET
    with tab_upload:
        st.markdown("**Upload any CSV or SQLite database file:**")
        uploaded_file = st.file_uploader(
            "Upload file",
            type=["csv", "db", "sqlite", "sqlite3"],
            key="direct_file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            file_name = uploaded_file.name
            # If new file uploaded, process immediately
            if st.session_state.get("dataset_name") != file_name:
                if file_name.endswith((".db", ".sqlite", ".sqlite3")):
                    save_path = os.path.join(UPLOAD_DIR, file_name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.session_state["active_source"] = "custom"
                    st.session_state["active_db_uri"] = f"sqlite:///{save_path}"
                    st.session_state["dataset_name"] = file_name
                    st.session_state["preview_df"] = None
                    
                    # Discover table names
                    conn = sqlite3.connect(save_path)
                    c = conn.cursor()
                    tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                    conn.close()
                    st.session_state["custom_table_names"] = tables
                    
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": f"✅ **Dataset Connected:** Successfully loaded `{file_name}` with tables: {', '.join([f'`{t}`' for t in tables])}. The agent is now actively querying this custom database!"
                    })
                    st.rerun()

                elif file_name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                    # Clean columns
                    df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', str(c)).strip() for c in df.columns]
                    clean_table_name = re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(file_name)[0]).lower()
                    
                    db_path = os.path.join(UPLOAD_DIR, f"{clean_table_name}.db")
                    conn = sqlite3.connect(db_path)
                    df.to_sql(clean_table_name, conn, if_exists="replace", index=False)
                    conn.close()

                    st.session_state["active_source"] = "custom"
                    st.session_state["active_db_uri"] = f"sqlite:///{db_path}"
                    st.session_state["dataset_name"] = file_name
                    st.session_state["preview_df"] = df.head(5)
                    st.session_state["custom_table_names"] = [clean_table_name]

                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": f"✅ **Dataset Connected:** Successfully uploaded and parsed `{file_name}`! Created table **`{clean_table_name}`** with **{len(df):,} rows** and **{len(df.columns)} columns**. What questions would you like to explore on this data?"
                    })
                    st.rerun()

# ----------------- VISUAL CONFIRMATION & PREVIEW BANNER -----------------
if st.session_state["active_source"] == "custom":
    st.markdown(f"""
    <div style="background:#0f172a; border:1px solid #1e293b; border-left:4px solid #10b981; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
        <span class="status-dot"></span><strong style="color:#10b981; font-size:14px;">Active Dataset: {st.session_state['dataset_name']}</strong>
        <span class="badge-pill">Unseen Custom Data Active</span>
        <p style="font-size:12.5px; color:#94a3b8; margin:4px 0 0 0;">
            All your questions below will be answered by querying this uploaded file.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state["preview_df"] is not None:
        with st.expander("👁️ Live Data Preview (First 5 Rows)", expanded=True):
            st.dataframe(st.session_state["preview_df"], use_container_width=True)

# Connect to the currently active database
db_instance, agent_instance, conn_err = get_conversational_agent(st.session_state["active_db_uri"])

if conn_err:
    st.error(f"Database connection error: {conn_err}")

# ----------------- SUGGESTED QUESTIONS -----------------
prompt_to_run = None

if len(st.session_state["messages"]) <= 1:
    st.markdown('<p style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:#71717a; margin-bottom:8px;">Suggested Questions</p>', unsafe_allow_html=True)
    
    if st.session_state["active_source"] == "default":
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
    else:
        # Dynamic suggestions for custom uploaded data
        tables = st.session_state.get("custom_table_names", ["data"])
        t0 = tables[0] if tables else "data"
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"How many total rows are in {t0}?", use_container_width=True):
                prompt_to_run = f"How many total rows are in the {t0} table?"
        with col2:
            if st.button(f"Summarize the key metrics of {t0}", use_container_width=True):
                prompt_to_run = f"Provide a breakdown of the key metrics and columns in {t0}."

# ----------------- CHAT CONVERSATION HISTORY -----------------
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg and msg["sql"]:
            with st.expander("View generated SQL query", expanded=False):
                st.code(msg["sql"], language="sql")

# Chat input bar at bottom
user_query = st.chat_input("Ask any question about your data or say hello...")
if user_query:
    prompt_to_run = user_query

# ----------------- QUERY EXECUTION -----------------
if prompt_to_run:
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("OpenAI API key is missing. Add it to .env or environment.")
    elif not agent_instance:
        st.error("No active database connection found.")
    else:
        # 1. Render user message
        st.session_state["messages"].append({"role": "user", "content": prompt_to_run})
        with st.chat_message("user"):
            st.markdown(prompt_to_run)

        # 2. Assistant execution
        with st.chat_message("assistant"):
            handler = SQLInspectorHandler()
            with st.spinner("Analyzing data and generating answer..."):
                # Multi-turn conversation context (last 3 messages) for natural follow-ups
                if len(st.session_state["messages"]) > 2:
                    recent_context = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state["messages"][-4:-1]])
                    full_input = f"Previous conversation context:\n{recent_context}\n\nCurrent user question: {prompt_to_run}"
                else:
                    full_input = prompt_to_run

                try:
                    res = agent_instance.invoke(
                        {"input": full_input},
                        {"callbacks": [handler]}
                    )
                    answer = res["output"]
                except Exception as e:
                    answer = f"I ran into an issue while analyzing the data: `{str(e)}`"

            st.markdown(answer)
            executed_sql = "\n\n".join(handler.sql_queries) if handler.sql_queries else None
            if executed_sql:
                with st.expander("View generated SQL query", expanded=False):
                    st.code(executed_sql, language="sql")

            # Persist assistant turn
            st.session_state["messages"].append({
                "role": "assistant",
                "content": answer,
                "sql": executed_sql
            })