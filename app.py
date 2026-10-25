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
    initial_sidebar_state="expanded"
)

# 2. Bespoke Clean Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Clean Streamlit chrome */
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
        max-width: 860px;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #0f1217;
        border-right: 1px solid #1e222b;
    }
    
    /* Status banner for active dataset */
    .dataset-banner {
        background: #131720;
        border: 1px solid #232a38;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 20px;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        display: inline-block;
        margin-right: 8px;
    }
    
    .badge {
        background: #1e2533;
        color: #93c5fd;
        border: 1px solid #2e3a50;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        margin-left: 8px;
    }
    
    .sidebar-section {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #71717a;
        margin-top: 18px;
        margin-bottom: 8px;
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
    
    .table-pill {
        display: inline-block;
        background: #181c25;
        border: 1px solid #272d3b;
        color: #a1a1aa;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        margin: 2px 4px 2px 0;
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
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Hello! I am your Business Intelligence agent. I'm currently connected to the **enterprise.db** database with 10,000 synthetic customer, product, and sales records. Ask me any business question or upload your own dataset to begin!"}
    ]

# 5. Sidebar: File Upload & Controls
with st.sidebar:
    st.markdown('<div class="sidebar-section">Active Data Connection</div>', unsafe_allow_html=True)
    
    # Switcher button if custom is loaded
    if st.session_state["active_source"] == "custom":
        st.markdown(f"""
        <div style="background:#131720; border:1px solid #232a38; border-radius:6px; padding:10px 12px; margin-bottom:12px;">
            <span class="status-dot"></span><strong>{st.session_state['dataset_name']}</strong><br/>
            <span style="font-size:12px; color:#10b981;">Custom Dataset Active</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("↺ Switch to Demo Enterprise DB", use_container_width=True):
            st.session_state["active_source"] = "default"
            st.session_state["active_db_uri"] = "sqlite:///enterprise.db"
            st.session_state["dataset_name"] = "enterprise.db"
            st.session_state["preview_df"] = None
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Switched back to the default **enterprise.db** database (10,000 records). What would you like to analyze?"}
            ]
            st.rerun()
    else:
        st.markdown("""
        <div style="background:#131720; border:1px solid #232a38; border-radius:6px; padding:10px 12px; margin-bottom:12px;">
            <span class="status-dot"></span><strong>enterprise.db</strong><br/>
            <span style="font-size:12px; color:#94a3b8;">Pre-loaded Warehouse (10k Orders)</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">Upload Custom Dataset</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload a CSV or SQLite database",
        type=["csv", "db", "sqlite", "sqlite3"],
        help="Upload any CSV file or SQLite database to query unseen data"
    )

    if uploaded_file is not None:
        file_name = uploaded_file.name
        # Check if already active to avoid re-triggering
        if st.session_state["dataset_name"] != file_name:
            if file_name.endswith((".db", ".sqlite", ".sqlite3")):
                save_path = os.path.join(UPLOAD_DIR, file_name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state["active_source"] = "custom"
                st.session_state["active_db_uri"] = f"sqlite:///{save_path}"
                st.session_state["dataset_name"] = file_name
                st.session_state["preview_df"] = None
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": f"✅ Successfully loaded custom database **{file_name}**! The agent has dynamically inspected the schema and is ready to answer questions about this dataset."
                })
                st.rerun()
            elif file_name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                # Sanitize column names
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
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": f"✅ Successfully uploaded and parsed **{file_name}**! Created table **`{clean_table_name}`** with **{len(df):,} rows** and **{len(df.columns)} columns**. What questions would you like to explore?"
                })
                st.rerun()

    # Reset button
    st.markdown('<div class="sidebar-section">Controls</div>', unsafe_allow_html=True)
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state["messages"] = [
            {"role": "assistant", "content": f"Chat cleared. I'm connected to **{st.session_state['dataset_name']}**. How can I help you analyze this data?"}
        ]
        st.rerun()

# 6. Initialize Database and Agent with conversational prompt
@st.cache_resource(show_spinner=False)
def get_conversational_agent(uri: str):
    try:
        db = SQLDatabase.from_uri(uri)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        prefix = """You are a helpful, conversational Business Intelligence analyst.
You translate business questions into accurate SQL, execute them, and explain the answers clearly and conversationally.

IMPORTANT BEHAVIORAL INSTRUCTIONS:
1. GREETINGS & CASUAL CONVERSATION:
   If the user greets you ('hi', 'hello', 'hey', 'what can you do?'), greet them warmly as a friendly BI analyst. Tell them which dataset is currently active, and suggest 2 or 3 quick analytical questions they can ask. DO NOT dump table schemas or column definitions unless specifically asked.
2. ANSWERING DATA QUESTIONS:
   - Provide the direct, human-readable answer first with formatted numbers (e.g. $845,870.00, 10,000 orders).
   - Offer a brief analytical observation or suggest a natural next question to explore.
   - Always be professional, insightful, and conversational.
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

db_instance, agent_instance, conn_err = get_conversational_agent(st.session_state["active_db_uri"])

# Display schema in sidebar
with st.sidebar:
    if conn_err:
        st.error(f"Error: {conn_err}")
    elif db_instance:
        table_names = db_instance.get_usable_table_names()
        st.markdown('<div class="sidebar-section">Available Tables</div>', unsafe_allow_html=True)
        pills = "".join([f'<span class="table-pill">{t}</span>' for t in table_names])
        st.markdown(pills, unsafe_allow_html=True)
        
        with st.expander("Inspect column details", expanded=False):
            st.code(db_instance.get_table_info()[:800], language="sql")

# 7. Main Application Header & Active Dataset Banner
st.markdown('<h1 style="font-size:24px; font-weight:600; margin-bottom:4px; color:#fafafa;">Enterprise BI Agent</h1>', unsafe_allow_html=True)
st.markdown('<p style="font-size:14px; color:#71717a; margin-bottom:16px;">Conversational business intelligence powered by autonomous SQL reasoning.</p>', unsafe_allow_html=True)

# Prominent Visual Status Banner
if st.session_state["active_source"] == "custom":
    st.markdown(f"""
    <div class="dataset-banner">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div>
                <span class="status-dot"></span>
                <strong style="color:#ffffff; font-size:14px;">Active Custom Dataset: {st.session_state['dataset_name']}</strong>
                <span class="badge">Unseen Data Live</span>
            </div>
        </div>
        <p style="font-size:12.5px; color:#94a3b8; margin:6px 0 0 0;">
            The agent is querying your uploaded file in real time. Tables: {', '.join([f'<code>{t}</code>' for t in db_instance.get_usable_table_names()])}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state["preview_df"] is not None:
        with st.expander("👁️ Preview First 5 Rows of Uploaded Data", expanded=False):
            st.dataframe(st.session_state["preview_df"], use_container_width=True)
else:
    st.markdown("""
    <div class="dataset-banner">
        <span class="status-dot"></span>
        <strong style="color:#ffffff; font-size:13.5px;">Active Dataset: Demo Enterprise Warehouse</strong>
        <span class="badge">10,000 Records</span>
        <p style="font-size:12px; color:#71717a; margin:4px 0 0 0;">
            Tables: <code>Customers</code> (250), <code>Products</code> (18), <code>Orders</code> (10,000). Upload custom files via the sidebar anytime.
        </p>
    </div>
    """, unsafe_allow_html=True)

prompt_to_run = None

# If chat has only initial greeting, show starter questions
if len(st.session_state["messages"]) <= 1:
    st.markdown('<div class="sidebar-section" style="margin-top:0;">Suggested Questions</div>', unsafe_allow_html=True)
    
    if st.session_state["active_source"] == "default":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Top 3 customers by total spend", use_container_width=True):
                prompt_to_run = "Can you list the top 3 customers by their total spend, and include their customer segment?"
            if st.button("Top 5 best-selling products by quantity", use_container_width=True):
                prompt_to_run = "What are the top 5 most popular products by total quantity ordered?"
        with col2:
            if st.button("Highest revenue product category", use_container_width=True):
                prompt_to_run = "Which product category generated the highest total revenue, and what was that amount?"
            if st.button("Order volume comparison: 2025 vs 2026", use_container_width=True):
                prompt_to_run = "How many total orders were placed in 2025 compared to 2026?"
    else:
        # Dynamic starter queries for custom data
        col1, col2 = st.columns(2)
        tables = db_instance.get_usable_table_names()
        t0 = tables[0] if tables else "data"
        with col1:
            if st.button(f"How many total rows are in {t0}?", use_container_width=True):
                prompt_to_run = f"How many total rows are in the {t0} table?"
        with col2:
            if st.button(f"Summarize the key metrics of {t0}", use_container_width=True):
                prompt_to_run = f"Provide a summary breakdown of the main numerical columns and categories in {t0}."

# Render conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg and msg["sql"]:
            with st.expander("View generated SQL query", expanded=False):
                st.code(msg["sql"], language="sql")

# Chat input bar
user_query = st.chat_input("Ask a business question or say hello...")
if user_query:
    prompt_to_run = user_query

# 8. Conversational Execution
if prompt_to_run:
    if not os.environ.get("OPENAI_API_KEY"):
        st.error("Please provide an OpenAI API key in the sidebar.")
    elif not agent_instance:
        st.error("No active database connection found.")
    else:
        # Display user message
        st.session_state["messages"].append({"role": "user", "content": prompt_to_run})
        with st.chat_message("user"):
            st.markdown(prompt_to_run)

        # Assistant turn
        with st.chat_message("assistant"):
            handler = SQLInspectorHandler()
            with st.spinner("Analyzing data..."):
                # Pass recent conversation context (last 3 messages) for natural follow-ups
                if len(st.session_state["messages"]) > 2:
                    recent_history = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state["messages"][-4:-1]])
                    full_input = f"Previous conversation context:\n{recent_history}\n\nCurrent user question: {prompt_to_run}"
                else:
                    full_input = prompt_to_run

                try:
                    res = agent_instance.invoke(
                        {"input": full_input},
                        {"callbacks": [handler]}
                    )
                    answer = res["output"]
                except Exception as e:
                    answer = f"I ran into an issue while querying the database: `{str(e)}`"

            st.markdown(answer)
            executed_sql = "\n\n".join(handler.sql_queries) if handler.sql_queries else None
            if executed_sql:
                with st.expander("View generated SQL query", expanded=False):
                    st.code(executed_sql, language="sql")

            # Persist assistant message
            st.session_state["messages"].append({
                "role": "assistant",
                "content": answer,
                "sql": executed_sql
            })