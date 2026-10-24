import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from dotenv import load_dotenv

load_dotenv()

# 1. Define what each table actually holds in plain English
table_metadata = [
    Document(page_content="Contains customer details, company names, segments (Enterprise, Mid-Market), and signup dates.", metadata={"table": "Customers"}),
    Document(page_content="Contains software and service products offered by the company, including categories and prices.", metadata={"table": "Products"}),
    Document(page_content="Contains transactional sales data, linking customers to products with quantities and order dates.", metadata={"table": "Orders"}),
]

# 2. Initialize the OpenAI embedding model
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 3. Build and save the local vector database
vectorstore = Chroma.from_documents(
    documents=table_metadata, 
    embedding=embeddings,
    persist_directory="./chroma_db"
)

print("Semantic schema router built successfully in ./chroma_db")