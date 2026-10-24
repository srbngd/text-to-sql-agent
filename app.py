import streamlit as st
import os
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

from dotenv import load_dotenv
load_dotenv()

# Setup API Key
if not os.environ.get("OPENAI_API_KEY"):
    st.error("Please set the OPENAI_API_KEY in your environment or .env file.")

st.set_page_config(page_title="Text-to-SQL BI Agent", page_icon="📊", layout="wide")
st.title("📊 Enterprise BI Agent")

# Connect Database & LLM
@st.cache_resource
def setup_agent():
    db = SQLDatabase.from_uri("sqlite:///enterprise.db")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)

agent_executor = setup_agent()

# Chat Interface
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you analyze the enterprise database today?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Ask a business question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        st_callback = StreamlitCallbackHandler(st.container())
        response = agent_executor.invoke(
            {"input": prompt},
            {"callbacks": [st_callback]}
        )
        st.write(response["output"])
        st.session_state.messages.append({"role": "assistant", "content": response["output"]})