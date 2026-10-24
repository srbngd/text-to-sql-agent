import streamlit as st
import os
import re
import sqlite3
import pandas as pd
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# 1. Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Autonomous Text-to-SQL BI Agent",
    page_icon="📊",
    layout="wide"
)

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 2. Sidebar Configuration: Database Source
st.sidebar.title("⚙️ Database Settings")

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    custom_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Enter your sk-... API key")
    if custom_key:
        os.environ["OPENAI_API_KEY"] = custom_key
        api_key = custom_key

db_source = st.sidebar.radio(
    "Choose Database Source:",
    [
        "🏢 Default Enterprise Warehouse (10k records)",
        "💾 Upload SQLite Database (.db, .sqlite)",
        "📄 Upload CSV File(s)",
        "🔗 Connect via Database URI"
    ]
)

active_db_uri = None
db_label = ""

if db_source == "🏢 Default Enterprise Warehouse (10k records)":
    active_db_uri = "sqlite:///enterprise.db"
    db_label = "enterprise.db (Default 10,000 Records)"

elif db_source == "💾 Upload SQLite Database (.db, .sqlite)":
    uploaded_db = st.sidebar.file_uploader(
        "Upload a SQLite Database file",
        type=["db", "sqlite", "sqlite3"],
        help="Upload any standard SQLite database file"
    )
    if uploaded_db is not None:
        save_path = os.path.join(UPLOAD_DIR, uploaded_db.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_db.getbuffer())
        active_db_uri = f"sqlite:///{save_path}"
        db_label = f"Uploaded DB: {uploaded_db.name}"
    else:
        st.sidebar.info("Please upload a .db or .sqlite file to begin.")

elif db_source == "📄 Upload CSV File(s)":
    uploaded_csvs = st.sidebar.file_uploader(
        "Upload one or more CSV files",
        type=["csv"],
        accept_multiple_files=True,
        help="Each CSV file will be converted into a queryable SQL table"
    )
    if uploaded_csvs:
        csv_db_path = os.path.join(UPLOAD_DIR, "uploaded_csv_warehouse.db")
        # Remove previous CSV database to reload cleanly
        if os.path.exists(csv_db_path):
            try:
                os.remove(csv_db_path)
            except Exception:
                pass
        
        conn = sqlite3.connect(csv_db_path)
        table_names = []
        for csv_file in uploaded_csvs:
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(csv_file.name)[0])
            df = pd.read_csv(csv_file)
            df.to_sql(clean_name, conn, if_exists="replace", index=False)
            table_names.append(clean_name)
        conn.close()

        active_db_uri = f"sqlite:///{csv_db_path}"
        db_label = f"CSV Warehouse ({', '.join(table_names)})"
    else:
        st.sidebar.info("Upload CSV files to automatically construct a SQL warehouse.")

elif db_source == "🔗 Connect via Database URI":
    uri_input = st.sidebar.text_input(
        "Database Connection URI",
        value="sqlite:///enterprise.db",
        help="e.g. postgresql://user:password@localhost:5432/dbname or sqlite:///path/to/db.sqlite"
    )
    if uri_input:
        active_db_uri = uri_input
        db_label = f"Remote URI: {uri_input}"

# 3. Agent Initializer function
@st.cache_resource(show_spinner=False)
def get_sql_agent(uri: str):
    try:
        db = SQLDatabase.from_uri(uri)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = create_sql_agent(
            llm=llm,
            db=db,
            agent_type="openai-tools",
            verbose=True
        )
        return agent, db, None
    except Exception as e:
        return None, None, str(e)

# Sidebar Schema Inspector & Controls
if active_db_uri:
    agent_executor, db_instance, err = get_sql_agent(active_db_uri)
    if err:
        st.sidebar.error(f"Failed to connect: {err}")
    elif db_instance:
        st.sidebar.success(f"🟢 Connected: {db_label}")
        with st.sidebar.expander("📋 Inspect Database Schema", expanded=False):
            tables = db_instance.get_usable_table_names()
            st.write(f"**Available Tables ({len(tables)}):**")
            for t in tables:
                st.markdown(f"- `{t}`")
            try:
                st.code(db_instance.get_table_info(), language="sql")
            except Exception:
                pass
else:
    agent_executor = None

if st.sidebar.button("🧹 Clear Chat History", use_container_width=True):
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Chat history cleared. How can I help you analyze your data?"}
    ]
    st.rerun()

# 4. Main Chat Interface
st.title("📊 Autonomous Text-to-SQL BI Agent")
st.caption("Powered by LangChain ReAct Execution Loop & OpenAI")

if not os.environ.get("OPENAI_API_KEY"):
    st.warning("⚠️ OpenAI API Key is missing. Please enter your API key in the sidebar or add it to `.env`.")

# Track active database in session state to notify on switch
if "current_db" not in st.session_state:
    st.session_state["current_db"] = active_db_uri
elif st.session_state["current_db"] != active_db_uri:
    st.session_state["current_db"] = active_db_uri
    st.session_state["messages"] = [
        {"role": "assistant", "content": f"Switched active database to **{db_label}**. What business questions would you like to ask?"}
    ]

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": f"Connected to **{db_label}**. How can I assist you with your business analytics today?"}
    ]

# Display conversation messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# User Input Handling
if prompt := st.chat_input("Ask a business question... (e.g. 'List the top 3 customers by total spend')"):
    if not active_db_uri or not agent_executor:
        st.error("No active database connected. Please select or upload a database in the sidebar.")
    elif not os.environ.get("OPENAI_API_KEY"):
        st.error("OpenAI API key required. Please enter it in the sidebar.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing schema and generating SQL query..."):
                try:
                    st_callback = StreamlitCallbackHandler(st.container())
                    response = agent_executor.invoke(
                        {"input": prompt},
                        {"callbacks": [st_callback]}
                    )
                    output_text = response["output"]
                except Exception:
                    try:
                        response = agent_executor.invoke({"input": prompt})
                        output_text = response["output"]
                    except Exception as e:
                        output_text = f"An error occurred while executing the query: `{str(e)}`"
            
            st.write(output_text)
            st.session_state.messages.append({"role": "assistant", "content": output_text})