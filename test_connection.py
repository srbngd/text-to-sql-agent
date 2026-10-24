from langchain_community.utilities import SQLDatabase

# Connect to the local SQLite database
db = SQLDatabase.from_uri("sqlite:///enterprise.db")

# Print the schema that LangChain will feed to the LLM
print("Available Tables:", db.get_usable_table_names())
print("\nSchema details:\n", db.get_table_info())