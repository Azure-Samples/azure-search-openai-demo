from typing import Any, AsyncGenerator, Union
from approaches.approach import Approach
from approaches.domain_classifier import DomainClassifier

class OrchestratorApproach(Approach):
    def __init__(
        self,
        cosmic_approach,
        substrate_approach,
        domain_classifier: DomainClassifier,
        openai_client,
        prompt_manager
    ):
        self.cosmic_approach = cosmic_approach
        self.substrate_approach = substrate_approach
        self.domain_classifier = domain_classifier
        self.openai_client = openai_client
        self.prompt_manager = prompt_manager
        
    async def run(
        self,
        messages: list[dict],
        stream: bool = False,
        session_state: Any = None,
        context: dict[str, Any] = {}
    ) -> Union[dict[str, Any], AsyncGenerator[dict[str, Any], None]]:
        """
        Main entry point for the orchestrator approach.
        Returns a dict for non-streaming, or an async generator for streaming.
        """
        if stream:
            return self._run_stream_internal(messages, session_state, context)
        else:
            return await self._run_non_stream(messages, session_state, context)
    
    async def run_stream(
        self,
        messages: list[dict],
        session_state: Any = None,
        context: dict[str, Any] = {}
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream implementation - returns an async generator.
        This matches the pattern used by other approaches.
        """
        return self._run_stream_internal(messages, session_state, context)
    
    async def _run_stream_internal(
        self,
        messages: list[dict],
        session_state: Any = None,
        context: dict[str, Any] = {}
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Internal streaming implementation - this is the actual async generator.
        """
        # Check if user has explicitly selected a category
        user_category = context.get("overrides", {}).get("include_category", "")
        
        if user_category and user_category != "":
            # User specified a category, use it directly
            if user_category == "Cosmic":
                async for chunk in await self.cosmic_approach.run_stream(messages, session_state, context):
                    yield chunk
                return
            elif user_category == "Substrate":
                async for chunk in await self.substrate_approach.run_stream(messages, session_state, context):
                    yield chunk
                return
        
        # Extract the latest user question
        user_question = messages[-1]["content"] if messages else ""
        
        # Get domain classification with context
        domains, confidence, reasoning = await self.domain_classifier.classify_with_context(
            user_question,
            messages[:-1]  # Pass conversation history
        )
        
        # Handle based on classification results
        if len(domains) == 1:
            # Single domain detected
            domain = domains[0]
            context["overrides"] = context.get("overrides", {})
            context["overrides"]["include_category"] = domain
            
            approach = self.cosmic_approach if domain == "Cosmic" else self.substrate_approach
            
            # Yield classification info first
            yield {
                "thoughts": f"Domain Classification: {domain} (Confidence: {confidence})\nReasoning: {reasoning}"
            }
            
            # Then stream from the selected approach
            async for chunk in await approach.run_stream(messages, session_state, context):
                yield chunk
                
        elif len(domains) == 2 and confidence < 0.8:  # Use numeric threshold instead of string
            # Ambiguous - search both domains
            yield {
                "answer": f"I found relevant information in both {' and '.join(domains)} domains:\n\n",
                "thoughts": f"Classification: Multiple domains (Confidence: {confidence})\n{reasoning}"
            }
            
            # Run both approaches
            for domain in domains:
                yield {"answer": f"\n## {domain}\n"}
                
                approach = self.cosmic_approach if domain == "Cosmic" else self.substrate_approach
                domain_context = context.copy()
                domain_context["overrides"] = domain_context.get("overrides", {}).copy()
                domain_context["overrides"]["include_category"] = domain
                
                async for chunk in await approach.run_stream(messages, session_state, domain_context):
                    yield chunk
                
                if domain != domains[-1]:
                    yield {"answer": "\n\n---\n"}
                    
        else:
            # Low confidence or no clear domain
            yield {
                "answer": f"I'm not sure which domain you're asking about. Your question could relate to:\n\n"
                         f"- **Cosmic**: Microsoft's container platform for performance and diagnostics\n"
                         f"- **Substrate**: Microsoft's infrastructure platform\n\n"
                         f"Could you please specify which one you're interested in, or shall I provide information about both?",
                "thoughts": f"Classification confidence was low. Domains detected: {', '.join(domains)}",
                "data_points": [],
                "citation_lookup": {},
                "thought_chain": [{
                    "title": "Domain Classification",
                    "description": reasoning,
                    "domains": domains,
                    "confidence": confidence
                }]
            }
    
    async def _run_non_stream(
        self,
        messages: list[dict],
        session_state: Any = None,
        context: dict[str, Any] = {}
    ) -> dict[str, Any]:
        """
        Non-streaming implementation.
        """
        # Check if user has explicitly selected a category
        user_category = context.get("overrides", {}).get("include_category", "")
        
        if user_category and user_category != "":
            # User specified a category, use it directly
            if user_category == "Cosmic":
                return await self.cosmic_approach.run(messages, False, session_state, context)
            elif user_category == "Substrate":
                return await self.substrate_approach.run(messages, False, session_state, context)
        
        # Extract the latest user question
        user_question = messages[-1]["content"] if messages else ""
        
        # Get domain classification with context
        domains, confidence, reasoning = await self.domain_classifier.classify_with_context(
            user_question,
            messages[:-1]  # Pass conversation history
        )
        
        # Handle based on classification results
        if len(domains) == 1:
            # Single domain detected
            domain = domains[0]
            context["overrides"] = context.get("overrides", {})
            context["overrides"]["include_category"] = domain
            
            approach = self.cosmic_approach if domain == "Cosmic" else self.substrate_approach
            
            result = await approach.run(messages, False, session_state, context)
            # Add classification info to thoughts
            if isinstance(result, dict):
                result["thought_chain"] = result.get("thought_chain", [])
                result["thought_chain"].insert(0, {
                    "title": "Domain Classification",
                    "description": reasoning,
                    "domain": domain,
                    "confidence": confidence
                })
            return result
                
        elif len(domains) == 2 and confidence < 0.8:  # Use numeric threshold instead of string
            # Ambiguous – search both domains
            return await self._handle_multi_domain_query(
                messages, domains, confidence, reasoning, session_state, context
            )
        else:
            # Low confidence or no clear domain
            return await self._handle_unclear_classification(
                messages, domains, confidence, reasoning, session_state, context
            )
    
    async def _handle_multi_domain_query(
        self, messages, domains, confidence, reasoning, session_state, context
    ):
        """Handle queries that might belong to multiple domains (non-streaming)"""
        
        results = {
            "answer": f"I found relevant information in both {' and '.join(domains)} domains:\n\n",
            "thoughts": f"Classification: Multiple domains (Confidence: {confidence})\n{reasoning}",
            "data_points": [],
            "citation_lookup": {},
            "thought_chain": [{
                "title": "Domain Classification",
                "description": reasoning,
                "domains": domains,
                "confidence": confidence
            }]
        }
        
        # Run both approaches
        for domain in domains:
            results["answer"] += f"\n## {domain}\n"
            
            approach = self.cosmic_approach if domain == "Cosmic" else self.substrate_approach
            domain_context = context.copy()
            domain_context["overrides"] = domain_context.get("overrides", {}).copy()
            domain_context["overrides"]["include_category"] = domain
            
            domain_result = await approach.run(messages, False, session_state, domain_context)
            
            if isinstance(domain_result, dict):
                results["answer"] += domain_result.get("answer", "")
                results["data_points"].extend(domain_result.get("data_points", []))
                results["citation_lookup"].update(domain_result.get("citation_lookup", {}))
                results["thought_chain"].extend(domain_result.get("thought_chain", []))
            
            if domain != domains[-1]:
                results["answer"] += "\n\n---\n"
                
        return results

    async def _handle_unclear_classification(
        self, messages, domains, confidence, session_state, context
    ):
        """Handle cases where the domain classification is unclear (non-streaming)"""
        
        return {
            "answer": f"I'm not sure which domain you're asking about. Your question could relate to:\n\n"
                     f"- **Cosmic**: Microsoft's container platform for performance and diagnostics\n"
                     f"- **Substrate**: Microsoft's infrastructure platform\n\n"
                     f"Could you please specify which one you're interested in, or shall I provide information about both?",
            "thoughts": f"Classification confidence was low. Domains detected: {', '.join(domains)}",
            "data_points": [],
            "citation_lookup": {},
            "thought_chain": [{
                "title": "Domain Classification",
                "description": reasoning,
                "domains": domains,
                "confidence": confidence
            }]
        }