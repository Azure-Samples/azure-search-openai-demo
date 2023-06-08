from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
import os
os.environ["OPENAI_API_KEY"] = 'cd65dd2883b2488da01f9d281a0d8256'
print("Hi")
documents = SimpleDirectoryReader('data.txt').load_data()
print("Hi2")
print(documents)
index = GPTVectorStoreIndex.from_documents(documents)
print("Hi3")
query_engine = index.as_query_engine()
print("Hi4")
response = query_engine.query("What is the name of the boy?")
print(response)