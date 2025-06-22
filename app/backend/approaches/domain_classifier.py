from typing import List, Dict, Optional, Tuple
from azure.search.documents.aio import SearchClient  # Change to async version
from azure.search.documents.models import VectorizedQuery
from openai import AsyncOpenAI
import json

class DomainClassifier:
    def __init__(
        self,
        search_client: SearchClient,
        openai_client: AsyncOpenAI,
        embeddings_service,
        chatgpt_deployment: str
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.embeddings_service = embeddings_service
        self.chatgpt_deployment = chatgpt_deployment
        
    async def classify_with_context(
        self, 
        question: str, 
        conversation_history: List[Dict] = None
    ) -> Tuple[List[str], float, str]:
        """
        Classify question into domains with confidence score
        Returns: (domains, confidence, reasoning)
        """
        
        # Step 1: Vector search for similar domain patterns
        vector_results = await self._vector_search_domains(question)
        
        # Step 2: Analyze with LLM using domain knowledge
        classification = await self._llm_classification(
            question, 
            vector_results, 
            conversation_history
        )
        
        return classification
        
    async def _vector_search_domains(self, question: str) -> List[Dict]:
        """Search for similar patterns in domain classifier index"""
        # Create embedding for the question
        question_embedding = await self.embeddings_service.create_embeddings([question])
        
        # Search in domain classifier index
        vector_query = VectorizedQuery(
            vector=question_embedding[0],
            k_nearest_neighbors=2,
            fields="embedding"
        )
        
        results = await self.search_client.search(
            search_text=question,
            vector_queries=[vector_query],
            select=["domain", "keywords", "topics", "sample_questions"],
            top=2
        )
        
        domain_matches = []
        # Use proper pagination pattern for async search results
        async for page in results.by_page():
            async for result in page:
                domain_matches.append({
                    "domain": result["domain"],
                    "score": result["@search.score"],
                    "keywords": result.get("keywords", ""),
                    "topics": result.get("topics", ""),
                    "sample_questions": result.get("sample_questions", "")
                })
            
        # Add this debug logging:
        print(f"🔍 Domain search results for '{question}':")
        for match in domain_matches:
            print(f"  - {match['domain']}: score={match['score']:.3f}")
            print(f"    Keywords: {match['keywords'][:100]}...")
            print(f"    Topics: {match['topics'][:100]}...")

        return domain_matches
        
    async def _llm_classification(
        self, 
        question: str,
        vector_results: List[Dict],
        conversation_history: List[Dict] = None
    ) -> Tuple[List[str], float, str]:
        """Use LLM to classify based on domain knowledge"""
        
        # Build context from vector results
        domain_context = "\n".join([
            f"Domain: {r['domain']}\n"
            f"Relevance Score: {r['score']}\n"
            f"Key Topics: {r['topics'][:100] if r['topics'] else 'N/A'}...\n"  # Handle as string
            f"Keywords: {r['keywords'][:100]}...\n"
            f"Similar Questions: {r['sample_questions'][:200]}...\n"
            for r in vector_results
        ])
        
        # Include conversation history if available
        history_context = ""
        if conversation_history:
            history_context = "Previous conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages
                history_context += f"{msg['role']}: {msg['content'][:200]}...\n"
        
        classification_prompt = f"""You are a domain classification expert for Microsoft's technical documentation.

You need to classify questions into one of these domains:

**COSMIC Domain:**
- Container platform for performance and diagnostics
- Keywords: cosmic, container, performance, diagnostics, monitoring, metrics
- Sample questions: "How do I monitor container performance?", "What are cosmic diagnostics?"

**SUBSTRATE Domain:** 
- Infrastructure platform and cloud services
- Keywords: substrate, infrastructure, platform, cloud, services, deployment
- Sample questions: "How to set up substrate infrastructure?", "What is substrate platform?"

**Current Question:** "{question}"

Based on the search results from each domain:
{domain_context}

{history_context}

Analyze the question and determine:
1. Which domain(s) this question belongs to
2. Your confidence level (high/medium/low)  
3. Brief reasoning
4. If the domain is confusing/ambiguous, explain what aspects belong to which domain

Return JSON:
{{
    "domains": ["Cosmic"] or ["Substrate"] or ["Cosmic", "Substrate"],
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of why this belongs to the selected domain(s)",
    "primary_domain": "Cosmic|Substrate|both",
    "domain_breakdown": {{
        "Cosmic": "Aspects of the question related to Cosmic (if any)",
        "Substrate": "Aspects of the question related to Substrate (if any)"
    }},
    "is_ambiguous": true/false,
    "user_friendly_explanation": "A simple explanation for the user about which domain their question relates to"
}}"""

        response = await self.openai_client.chat.completions.create(
            model=self.chatgpt_deployment,
            messages=[{"role": "system", "content": classification_prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Convert confidence to numeric value
        confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
        numeric_confidence = confidence_map.get(result["confidence"], 0.5)
        
        # Print classification decision (for debugging)
        print(f"\n🎯 Classification Decision:")
        print(f"  Question: '{question}'")
        print(f"  Domains: {', '.join(result['domains'])}")
        print(f"  Primary Domain: {result['primary_domain']}")
        print(f"  Confidence: {result['confidence']} ({numeric_confidence:.1%})")
        print(f"  Reasoning: {result['reasoning']}")
        
        if result.get('is_ambiguous', False):
            print(f"\n⚠️  Domain is ambiguous/confusing:")
            if result.get('domain_breakdown'):
                for domain, aspects in result['domain_breakdown'].items():
                    if aspects and aspects != "N/A":
                        print(f"  - {domain}: {aspects}")
        
        # Return user-friendly explanation if available, otherwise use reasoning
        user_explanation = result.get('user_friendly_explanation', result['reasoning'])
        
        return (
            result["domains"],
            numeric_confidence,
            user_explanation
        )