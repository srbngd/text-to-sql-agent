import os
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent

from dotenv import load_dotenv

# 1. Load the API key from .env or environment
load_dotenv()
# 2. Connect to your local SQLite database
db = SQLDatabase.from_uri("sqlite:///enterprise.db")

# 3. Initialize the LLM (Temperature 0 ensures factual, non-creative SQL generation)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 4. Create the SQL Agent (combines the LLM and the Database)
agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)

# 5. Define a plain-English business question
question = "Which customer bought the most consulting hours?"
print(f"User Question: {question}\n")

# 6. Run the agent and print the final answer
response = agent_executor.invoke({"input": question})
print(f"\nFinal Answer: {response['output']}")