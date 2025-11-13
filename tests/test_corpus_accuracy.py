"""
Test Corpus Document Retrieval and Citation Accuracy

This script tests if the RAG system correctly retrieves information from
corpus documents and provides accurate citations.
"""

import asyncio
import aiohttp
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "backend"))

# Load environment
from load_azd_env import load_azd_env
load_azd_env()


async def test_corpus_query(
    query: str,
    expected_documents: List[str] = None,
    backend_url: str = "http://localhost:50505",
    use_corpus_only: bool = True
) -> Dict[str, Any]:
    """
    Test a query to verify corpus document retrieval and citations.
    
    Args:
        query: The question to ask
        expected_documents: List of document names that should be cited (optional)
        backend_url: Backend API URL
        use_corpus_only: If True, force RAG-only mode (no web search)
    """
    print("=" * 80)
    print(f"TESTING CORPUS QUERY: {query}")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        # Force RAG-only mode to test corpus retrieval
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ],
            "context": {
                "overrides": {
                    "mode": "rag" if use_corpus_only else "hybrid",  # Force corpus-only
                    "retrieval_mode": "hybrid",  # Use both text and vector search
                    "top": 5,  # Get more results
                    "send_text_sources": True
                }
            }
        }
        
        print(f"\n[INFO] Query: {query}")
        print(f"[INFO] Mode: {'RAG-only (corpus)' if use_corpus_only else 'Hybrid (corpus + web)'}")
        
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
                    
                    print(f"\n[RESPONSE]")
                    print(f"Answer ({len(answer)} characters):")
                    print("-" * 80)
                    print(answer)
                    print("-" * 80)
                    
                    # Analyze sources
                    corpus_sources = []
                    web_sources = []
                    
                    for source in text_sources:
                        if isinstance(source, str):
                            # Check if it's a web source (URL) or corpus source (filename)
                            if source.startswith("http://") or source.startswith("https://"):
                                web_sources.append(source)
                            else:
                                corpus_sources.append(source)
                    
                    print(f"\n[SOURCES ANALYSIS]")
                    print(f"Total text sources: {len(text_sources)}")
                    print(f"Corpus sources: {len(corpus_sources)}")
                    print(f"Web sources: {len(web_sources)}")
                    
                    # Show corpus sources
                    if corpus_sources:
                        print(f"\n[CORPUS SOURCES]")
                        for i, source in enumerate(corpus_sources[:5], 1):
                            # Extract document name
                            if ":" in source:
                                doc_name = source.split(":")[0]
                                content_preview = source.split(":", 1)[1][:150] if len(source.split(":", 1)) > 1 else ""
                            else:
                                doc_name = source
                                content_preview = ""
                            
                            print(f"  {i}. {doc_name}")
                            if content_preview:
                                print(f"     Preview: {content_preview}...")
                    else:
                        print(f"\n[WARNING] No corpus sources found!")
                    
                    # Show web sources
                    if web_sources:
                        print(f"\n[WEB SOURCES]")
                        for i, source in enumerate(web_sources[:3], 1):
                            url = source.split(":")[0] if ":" in source else source
                            print(f"  {i}. {url}")
                    
                    # Show citations
                    print(f"\n[CITATIONS]")
                    print(f"Total citations: {len(citations)}")
                    corpus_citations = [c for c in citations if not c.startswith("http")]
                    web_citations = [c for c in citations if c.startswith("http")]
                    
                    if corpus_citations:
                        print(f"Corpus citations ({len(corpus_citations)}):")
                        for i, cit in enumerate(corpus_citations[:10], 1):
                            print(f"  {i}. {cit}")
                    
                    if web_citations:
                        print(f"Web citations ({len(web_citations)}):")
                        for i, cit in enumerate(web_citations[:5], 1):
                            print(f"  {i}. {cit}")
                    
                    # Verify expected documents
                    if expected_documents:
                        print(f"\n[VERIFICATION]")
                        print(f"Expected documents: {expected_documents}")
                        found_docs = []
                        for expected_doc in expected_documents:
                            # Check if expected doc is in any citation or source
                            for cit in citations:
                                if expected_doc.lower() in cit.lower():
                                    found_docs.append(expected_doc)
                                    break
                            if expected_doc not in found_docs:
                                for source in corpus_sources:
                                    if expected_doc.lower() in source.lower():
                                        found_docs.append(expected_doc)
                                        break
                        
                        if len(found_docs) == len(expected_documents):
                            print(f"[PASS] All expected documents found: {found_docs}")
                        else:
                            missing = set(expected_documents) - set(found_docs)
                            print(f"[PARTIAL] Found: {found_docs}")
                            print(f"[MISSING] Not found: {missing}")
                    
                    # Check if answer uses corpus citations
                    print(f"\n[ACCURACY CHECK]")
                    if corpus_citations:
                        # Extract citations actually used in the answer text
                        citations_used_in_answer = []
                        answer_lower = answer.lower()
                        
                        for cit in corpus_citations:
                            # Check if citation appears in answer (format: [doc.pdf#page=1])
                            cit_in_answer = f"[{cit}]" in answer or cit in answer
                            if cit_in_answer:
                                citations_used_in_answer.append(cit)
                        
                        # Check if all citations are relevant
                        if expected_documents:
                            expected_doc_names = [doc.split("#")[0].split("/")[-1] if "#" in doc else doc.split("/")[-1] for doc in expected_documents]
                            irrelevant_citations = []
                            
                            for cit in citations_used_in_answer:
                                cit_doc_name = cit.split("#")[0].split("/")[-1] if "#" in cit else cit.split("/")[-1]
                                # Check if this citation matches any expected document
                                is_relevant = any(exp_doc.lower() in cit_doc_name.lower() or cit_doc_name.lower() in exp_doc.lower() for exp_doc in expected_doc_names)
                                if not is_relevant:
                                    irrelevant_citations.append(cit)
                            
                            if irrelevant_citations:
                                print(f"[FAIL] Answer includes irrelevant citations: {irrelevant_citations}")
                                print(f"       Expected only: {expected_documents}")
                                print(f"       Citations in answer: {citations_used_in_answer}")
                            else:
                                print(f"[PASS] Answer only cites relevant documents")
                                print(f"       Citations used: {citations_used_in_answer}")
                        else:
                            # No expected documents, just check if citations are in answer
                            if citations_used_in_answer:
                                print(f"[PASS] Answer includes corpus citations: {citations_used_in_answer}")
                            else:
                                print(f"[WARN] Answer may not be citing corpus sources properly")
                                print(f"       Available citations: {corpus_citations[:3]}")
                    else:
                        print(f"[WARN] No corpus citations found - answer may be from web or generic")
                    
                    # Check for "I don't know"
                    if "don't know" in answer.lower() or "i don't know" in answer.lower():
                        if corpus_sources:
                            print(f"[WARN] Answer says 'I don't know' but corpus sources were found")
                            print(f"       This may indicate the sources don't contain relevant information")
                        else:
                            print(f"[INFO] Answer says 'I don't know' and no corpus sources found")
                    
                    return {
                        "query": query,
                        "answer": answer,
                        "corpus_sources": corpus_sources,
                        "web_sources": web_sources,
                        "corpus_citations": corpus_citations,
                        "web_citations": web_citations,
                        "text_sources": text_sources,
                        "citations": citations,
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


async def list_indexed_documents(backend_url: str = "http://localhost:50505") -> List[str]:
    """Try to get a list of documents in the index."""
    print("\n" + "=" * 80)
    print("ATTEMPTING TO LIST INDEXED DOCUMENTS")
    print("=" * 80)
    
    # Try asking what documents are in the index
    result = await test_corpus_query(
        "What documents are in the knowledge base? List all document names.",
        backend_url=backend_url,
        use_corpus_only=True
    )
    
    if result and result.get("corpus_sources"):
        # Extract document names from sources
        doc_names = set()
        for source in result["corpus_sources"]:
            if ":" in source:
                doc_name = source.split(":")[0].strip()
                if doc_name and not doc_name.startswith("http"):
                    doc_names.add(doc_name)
        
        if doc_names:
            print(f"\n[FOUND DOCUMENTS]")
            for i, doc in enumerate(sorted(doc_names), 1):
                print(f"  {i}. {doc}")
            return list(doc_names)
    
    return []


async def main():
    """Run corpus accuracy tests."""
    backend_url = os.getenv("BACKEND_URL", "http://localhost:50505")
    
    print("\n" + "=" * 80)
    print("CORPUS DOCUMENT RETRIEVAL AND CITATION ACCURACY TEST")
    print("=" * 80)
    
    # First, try to discover what documents are indexed
    print("\n[STEP 1] Discovering indexed documents...")
    indexed_docs = await list_indexed_documents(backend_url)
    
    # Test queries - customize these based on your documents
    # Format: {"query": "your question", "expected_docs": ["Document1.pdf", "Document2.pdf"], "description": "what this tests"}
    test_queries = [
        {
            "query": "What documents are in the knowledge base?",
            "expected_docs": None,  # Will be set after discovery
            "description": "List all documents"
        },
        # ADD YOUR CUSTOM TEST QUERIES HERE:
        # Example tests based on your documents:
        {
            "query": "What is the code review process?",
            "expected_docs": ["Code_Review_Checklist.pdf"],
            "description": "Test retrieval from Code Review Checklist"
        },
        {
            "query": "What is the release validation process?",
            "expected_docs": ["Release_Validation_Process.pdf"],
            "description": "Test retrieval from Release Validation Process"
        },
        {
            "query": "Summarize what is code review documents saying",
            "expected_docs": ["Code_Review_Checklist.pdf"],
            "description": "Test summarization of Code Review Checklist"
        },
        # Add more queries that match content in your documents:
        # {
        #     "query": "What are the requirements for X?",
        #     "expected_docs": ["YourDocument.pdf"],
        #     "description": "Test specific information retrieval"
        # },
    ]
    
    # If we found documents, add a test query
    if indexed_docs:
        # Use the first document as an example
        first_doc = indexed_docs[0]
        doc_topic = first_doc.replace(".pdf", "").replace("_", " ").replace("-", " ")
        test_queries.append({
            "query": f"What information is in {first_doc}?",
            "expected_docs": [first_doc],
            "description": f"Test retrieval from {first_doc}"
        })
    
    print(f"\n[STEP 2] Running {len(test_queries)} test queries...")
    print()
    
    results = []
    for i, test in enumerate(test_queries, 1):
        print(f"\n[TEST {i}/{len(test_queries)}] {test['description']}")
        result = await test_corpus_query(
            test["query"],
            expected_documents=test.get("expected_docs"),
            backend_url=backend_url,
            use_corpus_only=True  # Test corpus-only first
        )
        results.append(result)
        print()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    tests_with_corpus = sum(1 for r in results if r and r.get("corpus_sources"))
    tests_with_citations = sum(1 for r in results if r and r.get("corpus_citations"))
    
    print(f"Total tests: {total_tests}")
    print(f"Tests with corpus sources: {tests_with_corpus}/{total_tests}")
    print(f"Tests with corpus citations: {tests_with_citations}/{total_tests}")
    
    if tests_with_corpus < total_tests:
        print(f"\n[WARNING] {total_tests - tests_with_corpus} tests did not retrieve corpus sources")
        print("          This may indicate:")
        print("          - Documents are not indexed")
        print("          - Queries don't match document content")
        print("          - Search index needs to be rebuilt")
    
    print("\n[RECOMMENDATIONS]")
    print("1. Verify your documents are indexed in Azure AI Search")
    print("2. Check that queries match the content in your documents")
    print("3. Review the corpus sources shown above to verify retrieval accuracy")
    print("4. Check citations in answers to ensure they point to correct documents")


if __name__ == "__main__":
    asyncio.run(main())

