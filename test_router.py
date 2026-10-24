import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv

load_dotenv()
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Load the local vector database
vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# Test a business user's question
question = "How many SaaS licenses did we sell in August?"
print(f"Question: {question}\n")

# Retrieve the most relevant table based on meaning, not exact keyword matches
retrieved_docs = vectorstore.similarity_search(question, k=3)
print(f"The AI determined the necessary table is: {retrieved_docs[0].metadata['table']}")