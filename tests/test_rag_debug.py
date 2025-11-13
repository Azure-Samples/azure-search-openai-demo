"""
Debug RAG Responses

Tests and debugs why RAG is returning "I don't know" responses.
"""

import asyncio
import aiohttp
import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "backend"))

# Load environment
from load_azd_env import load_azd_env
load_azd_env()


async def debug_rag_query(query: str, backend_url: str = "http://localhost:50505"):
    """Debug a RAG query to see what's happening."""
    print("=" * 70)
    print(f"DEBUGGING RAG QUERY: {query}")
    print("=" * 70)
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ],
            "context": {
                "overrides": {
                    "retrieval_mode": "hybrid",
                    "top": 5,  # Get more results
                    "send_text_sources": True
                }
            }
        }
        
        print(f"\n1. Sending query to backend...")
        print(f"   URL: {backend_url}/chat")
        print(f"   Query: {query}")
        
        try:
            async with session.post(
                f"{backend_url}/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract response components
                    answer = data.get("message", {}).get("content", "")
                    context = data.get("context", {})
                    data_points = context.get("data_points", {})
                    text_sources = data_points.get("text", [])
                    citations = data_points.get("citations", [])
                    thoughts = context.get("thoughts", [])
                    
                    print(f"\n2. RESPONSE ANALYSIS:")
                    print(f"   Answer: {answer}")
                    print(f"   Answer length: {len(answer)} characters")
                    print(f"   Citations found: {len(citations)}")
                    print(f"   Text sources retrieved: {len(text_sources)}")
                    
                    # Show search query
                    if thoughts:
                        print(f"\n3. SEARCH PROCESS:")
                        for i, thought in enumerate(thoughts, 1):
                            title = thought.get("title", "")
                            description = thought.get("description", "")
                            if "search query" in title.lower() or "query" in title.lower():
                                print(f"   {i}. {title}: {description}")
                    
                    # Show retrieved documents
                    if text_sources:
                        print(f"\n4. RETRIEVED DOCUMENTS:")
                        for i, source in enumerate(text_sources[:3], 1):  # Show first 3
                            # Handle both dict and string formats
                            if isinstance(source, dict):
                                sourcepage = source.get("sourcepage", "unknown")
                                content = source.get("content", "")
                            else:
                                # String format: "filename.pdf#page=1: content here"
                                if ":" in str(source):
                                    parts = str(source).split(":", 1)
                                    sourcepage = parts[0] if parts else "unknown"
                                    content = parts[1] if len(parts) > 1 else ""
                                else:
                                    sourcepage = "unknown"
                                    content = str(source)
                            
                            content_preview = content[:200] if content else "(empty)"
                            print(f"   {i}. {sourcepage}")
                            print(f"      Content preview: {content_preview}...")
                            print(f"      Content length: {len(content)} characters")
                            
                            # Check if content is relevant
                            query_lower = query.lower()
                            content_lower = content.lower()
                            query_words = [w for w in query_lower.split() if len(w) > 2]
                            if query_lower in content_lower or any(word in content_lower for word in query_words):
                                print(f"      [RELEVANT] Contains query terms")
                            else:
                                print(f"      [NOT RELEVANT] Doesn't contain query terms")
                    else:
                        print(f"\n4. RETRIEVED DOCUMENTS: None found")
                    
                    # Analyze why "I don't know"
                    if "don't know" in answer.lower() or "i don't know" in answer.lower():
                        print(f"\n5. WHY 'I DON'T KNOW'?")
                        if not text_sources:
                            print("   ❌ No documents retrieved from search")
                        elif len(text_sources) > 0:
                            print("   ⚠️  Documents retrieved but content may not be relevant")
                            print("   ⚠️  LLM is following prompt: 'say you don't know if sources don't contain answer'")
                            
                            # Check content relevance
                            relevant_count = 0
                            for source in text_sources:
                                # Handle both dict and string formats
                                if isinstance(source, dict):
                                    content = source.get("content", "").lower()
                                else:
                                    # String format: "filename.pdf#page=1: content here"
                                    if ":" in str(source):
                                        content = str(source).split(":", 1)[1].lower() if len(str(source).split(":", 1)) > 1 else ""
                                    else:
                                        content = str(source).lower()
                                
                                query_words = [w for w in query.lower().split() if len(w) > 3]
                                if any(word in content for word in query_words):
                                    relevant_count += 1
                            
                            print(f"   📊 Relevance: {relevant_count}/{len(text_sources)} sources contain query terms")
                            
                            if relevant_count == 0:
                                print("   💡 SOLUTION: Index documents that contain information about the query topic")
                                print("   💡 Or try a different query related to your indexed documents")
                    
                    # Show citations
                    if citations:
                        print(f"\n6. CITATIONS:")
                        for i, citation in enumerate(citations[:5], 1):
                            print(f"   {i}. {citation}")
                    
                    return {
                        "answer": answer,
                        "citations": citations,
                        "text_sources": text_sources,
                        "thoughts": thoughts
                    }
                else:
                    error_text = await response.text()
                    print(f"\n[ERROR] Backend returned status {response.status}")
                    print(f"Error: {error_text[:500]}")
                    return None
        except Exception as e:
            print(f"\n[ERROR] Request failed: {e}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """Run debug tests."""
    queries = [
        "What is RAG?",
        "Explain vector search",
        "What documents are in the index?"
    ]
    
    for query in queries:
        result = await debug_rag_query(query)
        print("\n" + "=" * 70 + "\n")
        
        if result and result.get("text_sources"):
            # Try a query that might match the actual documents
            print("💡 TIP: Try asking about topics in your indexed documents:")
            print("   - Check what documents you have indexed")
            print("   - Ask questions related to those document topics")
            break


if __name__ == "__main__":
    asyncio.run(main())

