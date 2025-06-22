from typing import Any, Optional
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from azure.search.documents.aio import SearchClient
from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient

class OrchestratorApproach:
    def __init__(
        self,
        cosmic_agent: ChatReadRetrieveReadApproach,
        substrate_agent: ChatReadRetrieveReadApproach,
        openai_client,
        prompt_manager
    ):
        self.cosmic_agent = cosmic_agent
        self.substrate_agent = substrate_agent
        self.openai_client = openai_client
        self.prompt_manager = prompt_manager
        
    async def determine_domain(self, question: str) -> str:
        """Use LLM to determine which domain the question belongs to"""
        prompt = f"""Given this question: "{question}"
        
        Determine if this question is about:
        1. Cosmic - Microsoft's container platform for performance and diagnostics
        2. Substrate - Microsoft's infrastructure platform
        
        Respond with only "cosmic" or "substrate".
        """
        
        response = await self.openai_client.chat.completions.create(
            model=self.openai_deployment,
            messages=[{"role": "system", "content": prompt}],
            temperature=0
        )
        
        domain = response.choices[0].message.content.strip().lower()
        return domain if domain in ["cosmic", "substrate"] else "cosmic"
        
    async def run(
        self,
        messages: list[dict],
        stream: bool = False,
        session_state: Any = None,
        context: dict[str, Any] = {}
    ):
        # Extract the latest user question
        user_question = messages[-1]["content"] if messages else ""
        
        # Determine which domain to use
        domain = await self.determine_domain(user_question)
        
        # Route to appropriate agent
        if domain == "substrate":
            # Add domain context to the messages
            context["overrides"] = context.get("overrides", {})
            context["overrides"]["include_category"] = "Substrate"
            return await self.substrate_agent.run(messages, stream, session_state, context)
        else:
            context["overrides"] = context.get("overrides", {})
            context["overrides"]["include_category"] = "Cosmic"
            return await self.cosmic_agent.run(messages, stream, session_state, context)