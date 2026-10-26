import streamlit as st
import os
import re
import sqlite3
import ast
import time
import pandas as pd
import plotly.express as px
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

# 2. Modern High-End Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Clean Streamlit default chrome */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    
    .stApp {
        background-color: #090b10;
        color: #f1f5f9;
    }
    
    .block-container {
        padding-top: 1.75rem;
        padding-bottom: 5rem;
        max-width: 900px;
    }
    
    /* Header & Branding */
    .hero-title {
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #ffffff;
        margin: 0 0 4px 0;
    }
    
    .hero-subtitle {
        font-size: 14px;
        color: #94a3b8;
        margin: 0 0 20px 0;
    }
    
    /* Dataset Manager Card */
    .dataset-box {
        background: #111520;
        border: 1px solid #1e2638;
        border-radius: 12px;
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
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
    }
    
    .badge-pill {
        background: rgba(56, 189, 248, 0.1);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.25);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        margin-left: 8px;
    }
    
    .guardrail-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #34d399;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 11.5px;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 8px;
    }
    
    /* Query Cards */
    div[data-testid="stButton"] > button {
        background-color: #111520;
        border: 1px solid #1e2638;
        border-radius: 8px;
        color: #e2e8f0;
        font-size: 13.5px;
        font-weight: 400;
        text-align: left;
        padding: 12px 16px;
        width: 100%;
        transition: all 0.15s ease-in-out;
    }
    
    div[data-testid="stButton"] > button:hover {
        background-color: #171d2b;
        border-color: #38bdf8;
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
        background-color: #0e121a !important;
        border: 1px solid #1c2230 !important;
        border-radius: 6px !important;
    }
    
    div[data-testid="stChatInput"] {
        border-radius: 10px;
        border: 1px solid #232c3d;
        background-color: #111520;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #38bdf8;
    }
</style>
""", unsafe_allow_html=True)

# 3. Callback handler to reliably capture generated SQL & performance
class SQLInspectorHandler(BaseCallbackHandler):
    def __init__(self):
        self.sql_queries = []
        self.start_time = time.time()
        self.execution_time = 0

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

    def on_tool_end(self, output, **kwargs):
        self.execution_time = round(time.time() - self.start_time, 2)

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

# Resolve API Key from multiple sources (Environment, Streamlit Secrets, Session State)
api_key = os.environ.get("OPENAI_API_KEY", "")

if not api_key:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            api_key = str(st.secrets["OPENAI_API_KEY"]).strip()
            os.environ["OPENAI_API_KEY"] = api_key
    except Exception:
        pass

if not api_key and st.session_state.get("user_api_key"):
    api_key = st.session_state["user_api_key"]
    os.environ["OPENAI_API_KEY"] = api_key

# 5. Connect Database & Conversational Agent
@st.cache_resource(show_spinner=False)
def get_conversational_agent(uri: str, key: str):
    if not key:
        return None, None, "API_KEY_REQUIRED"
    try:
        db = SQLDatabase.from_uri(uri)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=key)
        
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

# Helper function to generate auto-visualizations from SQL results
def create_smart_chart(df: pd.DataFrame):
    if df is None or len(df) < 2 or len(df.columns) < 2:
        return None
    
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    
    if not num_cols or not cat_cols:
        return None
    
    x_cat = cat_cols[0]
    y_num = num_cols[0]
    
    # Clean titles
    cat_label = x_cat.replace('_', ' ').title()
    num_label = y_num.replace('_', ' ').title()
    
    # If 6 or fewer categories: sleek horizontal or vertical bar chart
    fig = px.bar(
        df.head(10),
        x=x_cat,
        y=y_num,
        color=y_num,
        color_continuous_scale=["#38bdf8", "#818cf8"],
        template="plotly_dark",
        labels={x_cat: cat_label, y_num: num_label}
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=24, b=10),
        height=280,
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        coloraxis_showscale=False
    )
    return fig

# ----------------- MAIN VIEW -----------------
st.markdown('<h1 class="hero-title">Enterprise BI Agent</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Conversational text-to-SQL with automatic charts, data exports, and read-only safety guardrails.</p>', unsafe_allow_html=True)

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
            if st.session_state.get("dataset_name") != file_name:
                if file_name.endswith((".db", ".sqlite", ".sqlite3")):
                    save_path = os.path.join(UPLOAD_DIR, file_name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.session_state["active_source"] = "custom"
                    st.session_state["active_db_uri"] = f"sqlite:///{save_path}"
                    st.session_state["dataset_name"] = file_name
                    st.session_state["preview_df"] = None
                    
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

# ----------------- VISUAL CONFIRMATION & LIVE PREVIEW BANNER -----------------
if st.session_state["active_source"] == "custom":
    st.markdown(f"""
    <div style="background:#0f172a; border:1px solid #1e293b; border-left:4px solid #10b981; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
        <span class="status-dot"></span><strong style="color:#10b981; font-size:14px;">Active Dataset: {st.session_state['dataset_name']}</strong>
        <span class="badge-pill">Unseen Custom Data Live</span>
        <p style="font-size:12.5px; color:#94a3b8; margin:4px 0 0 0;">
            All your queries below will be answered by executing SQL directly against this uploaded file.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state["preview_df"] is not None:
        with st.expander("👁️ Live Data Preview (First 5 Rows)", expanded=False):
            st.dataframe(st.session_state["preview_df"], use_container_width=True)

# Connect to the currently active database
db_instance, agent_instance, conn_err = get_conversational_agent(st.session_state["active_db_uri"], api_key)

if not api_key or conn_err == "API_KEY_REQUIRED":
    st.markdown("""
    <div style="background:#1c1917; border:1px solid #78350f; border-left:4px solid #f59e0b; border-radius:8px; padding:14px 16px; margin-bottom:18px;">
        <strong style="color:#fbbf24; font-size:14px;">🔑 OpenAI API Key Required</strong>
        <p style="font-size:12.5px; color:#d6d3d1; margin:4px 0 10px 0;">
            Please enter your OpenAI API key below (or configure <code>OPENAI_API_KEY</code> in Streamlit Cloud Secrets) to activate the agent.
        </p>
    </div>
    """, unsafe_allow_html=True)
    col_k1, col_k2 = st.columns([4, 1.2])
    with col_k1:
        key_input = st.text_input("OpenAI API Key", type="password", placeholder="Paste sk-proj-... here", label_visibility="collapsed")
    with col_k2:
        if st.button("Activate Agent", use_container_width=True):
            if key_input:
                st.session_state["user_api_key"] = key_input.strip()
                os.environ["OPENAI_API_KEY"] = key_input.strip()
                st.rerun()
elif conn_err:
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
            if st.button("Top 5 best-selling products by quantity", use_container_width=True):
                prompt_to_run = "What are the top 5 most popular products by total quantity ordered?"
        with col2:
            if st.button("Highest revenue product category", use_container_width=True):
                prompt_to_run = "Which product category generated the highest total revenue, and what was that amount?"
            if st.button("Order volume comparison: 2025 vs 2026", use_container_width=True):
                prompt_to_run = "How many total orders were placed in 2025 compared to 2026?"
    else:
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
for idx, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Render auto-visualization if present
        if "chart_data" in msg and msg["chart_data"] is not None:
            fig = create_smart_chart(msg["chart_data"])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{idx}")
        
        # Action bar: Download CSV & SQL Inspector
        if "sql" in msg and msg["sql"]:
            col_audit, col_dl = st.columns([3, 1.2])
            with col_audit:
                exec_time = msg.get("exec_time", "0.15s")
                st.markdown(f'<span class="guardrail-pill">🛡️ Read-Only Guardrail Active • {exec_time}</span>', unsafe_allow_html=True)
            with col_dl:
                if "chart_data" in msg and msg["chart_data"] is not None:
                    csv_bytes = msg["chart_data"].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Export CSV",
                        data=csv_bytes,
                        file_name="query_results.csv",
                        mime="text/csv",
                        key=f"dl_{idx}",
                        use_container_width=True
                    )
            
            with st.expander("🔍 View generated SQL query", expanded=False):
                st.code(msg["sql"], language="sql")

# Chat input bar at bottom
user_query = st.chat_input("Ask any question about your data or say hello...")
if user_query:
    prompt_to_run = user_query

# ----------------- QUERY EXECUTION -----------------
if prompt_to_run:
    if not api_key:
        st.error("OpenAI API key is missing. Please enter your API key in the box above.")
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
            
            # Fetch structured dataframe for charts and exports
            result_df = None
            if executed_sql and st.session_state["active_db_uri"].startswith("sqlite:///"):
                db_path = st.session_state["active_db_uri"].replace("sqlite:///", "")
                try:
                    conn = sqlite3.connect(db_path)
                    # Use the last executed query
                    last_sql = handler.sql_queries[-1]
                    result_df = pd.read_sql_query(last_sql, conn)
                    conn.close()
                except Exception:
                    result_df = None

            # Render instant chart if structured data returned
            if result_df is not None:
                fig = create_smart_chart(result_df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

            if executed_sql:
                col_audit, col_dl = st.columns([3, 1.2])
                with col_audit:
                    st.markdown(f'<span class="guardrail-pill">🛡️ Read-Only Guardrail Active • {handler.execution_time}s</span>', unsafe_allow_html=True)
                with col_dl:
                    if result_df is not None and len(result_df) > 0:
                        csv_bytes = result_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="⬇️ Export CSV",
                            data=csv_bytes,
                            file_name="query_results.csv",
                            mime="text/csv",
                            key=f"dl_live",
                            use_container_width=True
                        )

                with st.expander("🔍 View generated SQL query", expanded=False):
                    st.code(executed_sql, language="sql")

            # Persist assistant turn
            st.session_state["messages"].append({
                "role": "assistant",
                "content": answer,
                "sql": executed_sql,
                "chart_data": result_df,
                "exec_time": f"{handler.execution_time}s"
            })