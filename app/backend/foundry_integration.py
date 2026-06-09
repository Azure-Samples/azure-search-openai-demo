"""
Foundry + Azure OpenAI Integration Example
Demonstrates how to use Microsoft Foundry with the RAG system
and the latest gpt-4o and embedding models
"""

import os
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.openai import AzureOpenAI
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery

# ===== Configuration =====

# Azure OpenAI - Latest Models
OPENAI_CLIENT = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

CHAT_MODEL = os.getenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-3-large")
EMBEDDING_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "1536"))

# Azure Search
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "gptkbindex")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")

# Foundry Settings
FOUNDRY_ENABLED = os.getenv("ENABLE_AGENTIC_KNOWLEDGEBASE", "true").lower() == "true"
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_API_ENDPOINT")

# ===== Foundry Integration =====

class FoundryRAGSystem:
    """
    Unified RAG system with Microsoft Foundry + Azure OpenAI integration
    """

    def __init__(self):
        self.openai_client = OPENAI_CLIENT
        self.chat_model = CHAT_MODEL
        self.embedding_model = EMBEDDING_MODEL
        self.search_endpoint = SEARCH_ENDPOINT
        self.search_index = SEARCH_INDEX
        self.foundry_enabled = FOUNDRY_ENABLED

    def generate_embeddings(self, text: str) -> list[float]:
        """
        Generate embeddings using text-embedding-3-large (1536 dimensions)
        """
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.embedding_model,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    def search_documents(
        self,
        query: str,
        use_vector_search: bool = True,
        use_semantic_search: bool = True,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Hybrid search combining vector + semantic search
        """
        search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.search_index,
            credential=SEARCH_KEY,
        )

        results = []

        if use_vector_search:
            # Vector search with embeddings
            query_embedding = self.generate_embeddings(query)
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k,
                fields="embedding",
            )
            results = search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                select=["id", "title", "content", "source", "score"],
                top=top_k,
            )

        elif use_semantic_search:
            # Semantic search (requires semantic configuration)
            results = search_client.search(
                search_text=query,
                query_type="semantic",
                query_language="en-us",
                semantic_configuration_name="my-semantic-config",
                select=["id", "title", "content", "source", "score"],
                top=top_k,
            )

        return list(results)

    def generate_answer(
        self,
        user_question: str,
        context: list[dict],
        reasoning_effort: str = "medium",
        enable_streaming: bool = True,
    ) -> str:
        """
        Generate answer using gpt-4o with retrieved context
        
        Args:
            user_question: User's question
            context: Retrieved documents from search
            reasoning_effort: "low", "medium", or "high" - gpt-4o advanced reasoning
            enable_streaming: Stream response tokens in real-time
        """

        # Build context string from retrieved documents
        context_text = "\n\n".join(
            [f"Source: {doc['source']}\n{doc['content']}" for doc in context]
        )

        system_prompt = """You are an AI assistant that answers questions based on provided context.
        
Always provide accurate answers grounded in the context. If the answer is not in the context, say so.
Be concise and helpful. Include source references when citing information."""

        user_prompt = f"""Context:
{context_text}

Question: {user_question}

Answer based only on the provided context. If information is not available, indicate that."""

        # Call gpt-4o with advanced reasoning
        response = self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
            stream=enable_streaming,
        )

        if enable_streaming:
            # Stream response
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    print(chunk.choices[0].delta.content, end="", flush=True)
            print()  # Newline after streaming
            return full_response
        else:
            return response.choices[0].message.content

    async def agentic_rag_query(
        self,
        user_question: str,
        use_query_rewriting: bool = True,
        num_retrieval_attempts: int = 1,
    ) -> dict:
        """
        Agentic RAG with query rewriting and iterative retrieval (Foundry integration)
        """

        # Step 1: Optionally rewrite query for better search
        if use_query_rewriting:
            rewrite_prompt = f"""Rewrite this question to improve search results:
Question: {user_question}

Rewritten question (make it more specific and search-friendly):"""

            rewrite_response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0.3,
                max_tokens=200,
            )
            search_query = rewrite_response.choices[0].message.content
        else:
            search_query = user_question

        # Step 2: Retrieve documents
        documents = self.search_documents(
            query=search_query, use_vector_search=True, top_k=5
        )

        if not documents:
            return {
                "question": user_question,
                "answer": "I could not find relevant information to answer your question.",
                "documents": [],
                "reasoning": "No documents found",
            }

        # Step 3: Generate answer with context
        answer = self.generate_answer(
            user_question=user_question,
            context=documents,
            reasoning_effort="medium",
            enable_streaming=False,
        )

        return {
            "question": user_question,
            "rewritten_query": search_query if use_query_rewriting else None,
            "answer": answer,
            "documents": documents,
            "num_documents": len(documents),
        }


# ===== Usage Example =====

if __name__ == "__main__":
    import asyncio

    # Initialize the RAG system
    rag = FoundryRAGSystem()

    print(f"Chat Model: {rag.chat_model}")
    print(f"Embedding Model: {rag.embedding_model}")
    print(f"Foundry Enabled: {rag.foundry_enabled}")
    print("")

    # Example 1: Simple Q&A with context
    print("=== Example 1: Simple Q&A ===")
    question = "What are the company benefits?"
    documents = rag.search_documents(question, top_k=3)

    if documents:
        print(f"Found {len(documents)} documents")
        answer = rag.generate_answer(question, documents)
        print(f"Answer: {answer}\n")

    # Example 2: Agentic RAG with query rewriting
    print("=== Example 2: Agentic RAG ===")
    result = asyncio.run(
        rag.agentic_rag_query(
            "Tell me about health insurance coverage",
            use_query_rewriting=True,
        )
    )

    print(f"Original Question: {result['question']}")
    print(f"Rewritten Query: {result['rewritten_query']}")
    print(f"Answer: {result['answer']}")
    print(f"Source Documents: {result['num_documents']}")
