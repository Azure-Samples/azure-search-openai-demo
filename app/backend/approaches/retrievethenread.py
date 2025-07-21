from typing import Any, Optional, cast

from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from approaches.approach import Approach, DataPoints, ExtraInfo, ThoughtStep
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper


class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the AI Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    def __init__(
        self,
        *,
        search_client: SearchClient,
        search_index_name: str,
        agent_model: Optional[str],
        agent_deployment: Optional[str],
        agent_client: KnowledgeAgentRetrievalClient,
        auth_helper: AuthenticationHelper,
        openai_client: AsyncOpenAI,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        embedding_model: str,
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_dimensions: int,
        embedding_field: str,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        prompt_manager: PromptManager,
        reasoning_effort: Optional[str] = None,
    ):
        self.search_client = search_client
        self.search_index_name = search_index_name
        self.agent_model = agent_model
        self.agent_deployment = agent_deployment
        self.agent_client = agent_client
        self.chatgpt_deployment = chatgpt_deployment
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_field = embedding_field
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.prompt_manager = prompt_manager
        self.answer_prompt = self.prompt_manager.load_prompt("ask_answer_question.prompty")
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True

    async def run(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> dict[str, Any]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        use_agentic_retrieval = True if overrides.get("use_agentic_retrieval") else False
        q = messages[-1]["content"]
        if not isinstance(q, str):
            raise ValueError("The most recent message content must be a string.")

        if use_agentic_retrieval:
            extra_info = await self.run_agentic_retrieval_approach(messages, overrides, auth_claims)
        else:
            extra_info = await self.run_search_approach(messages, overrides, auth_claims)

        # Process results
        messages = self.prompt_manager.render_prompt(
            self.answer_prompt,
            self.get_system_prompt_variables(overrides.get("prompt_template"))
            | {"user_query": q, "text_sources": extra_info.data_points.text},
        )

        chat_completion = cast(
            ChatCompletion,
            await self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages=messages,
                overrides=overrides,
                response_token_limit=self.get_response_token_limit(self.chatgpt_model, 1024),
            ),
        )
        extra_info.thoughts.append(
            self.format_thought_step_for_chatcompletion(
                title="Prompt to generate answer",
                messages=messages,
                overrides=overrides,
                model=self.chatgpt_model,
                deployment=self.chatgpt_deployment,
                usage=chat_completion.usage,
            )
        )
        return {
            "message": {
                "content": chat_completion.choices[0].message.content,
                "role": chat_completion.choices[0].message.role,
            },
            "context": extra_info,
            "session_state": session_state,
        }

    async def run_search_approach(
        self, messages: list[ChatCompletionMessageParam], overrides: dict[str, Any], auth_claims: dict[str, Any]
    ):
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_query_rewriting = True if overrides.get("query_rewriting") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top", 15)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        filter = self.build_filter(overrides, auth_claims)
        q = str(messages[-1]["content"])

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors: list[VectorQuery] = []
        if use_vector_search:
            vectors.append(await self.compute_text_embedding(q))

        results = await self.search(
            top,
            q,
            filter,
            vectors,
            use_text_search,
            use_vector_search,
            use_semantic_ranker,
            use_semantic_captions,
            minimum_search_score,
            minimum_reranker_score,
            use_query_rewriting,
        )

        # Si no hay resultados en Azure Search, intentar SharePoint
        if not results and self._is_pilot_related_query(q):
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("No se encontraron resultados en Azure Search, probando SharePoint...")
                
                sharepoint_results = await self._search_sharepoint_files(q, top=overrides.get("top", 15))
                if sharepoint_results:
                    # Convertir resultados de SharePoint al formato de text_sources
                    sharepoint_text_sources = []
                    for result in sharepoint_results:
                        if result.get('content'):
                            sharepoint_text_sources.append(result['content'])
                    
                    if sharepoint_text_sources:
                        return ExtraInfo(
                            DataPoints(text=sharepoint_text_sources),
                            thoughts=[
                                ThoughtStep(
                                    "Search using user query",
                                    q,
                                    {
                                        "use_semantic_captions": use_semantic_captions,
                                        "use_semantic_ranker": use_semantic_ranker,
                                        "use_query_rewriting": use_query_rewriting,
                                        "top": top,
                                        "filter": filter,
                                        "use_vector_search": use_vector_search,
                                        "use_text_search": use_text_search,
                                        "fallback_to_sharepoint": True,
                                    },
                                ),
                                ThoughtStep(
                                    "SharePoint fallback search",
                                    f"Found {len(sharepoint_results)} documents in SharePoint PILOTOS folder",
                                    {"query": q, "sources": [r.get('name', 'Unknown') for r in sharepoint_results]}
                                ),
                            ],
                        )
            except Exception as e:
                logger.error(f"Error en SharePoint fallback: {e}")
                # Continuar con resultados vacíos de Azure Search si SharePoint falla

        text_sources = self.get_sources_content(results, use_semantic_captions, use_image_citation=False)

        return ExtraInfo(
            DataPoints(text=text_sources),
            thoughts=[
                ThoughtStep(
                    "Search using user query",
                    q,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "use_query_rewriting": use_query_rewriting,
                        "top": top,
                        "filter": filter,
                        "use_vector_search": use_vector_search,
                        "use_text_search": use_text_search,
                    },
                ),
                ThoughtStep(
                    "Search results",
                    [result.serialize_for_results() for result in results],
                ),
            ],
        )

    async def run_agentic_retrieval_approach(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
    ):
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0)
        search_index_filter = self.build_filter(overrides, auth_claims)
        top = overrides.get("top", 15)
        max_subqueries = overrides.get("max_subqueries", 10)
        results_merge_strategy = overrides.get("results_merge_strategy", "interleaved")
        # 50 is the amount of documents that the reranker can process per query
        max_docs_for_reranker = max_subqueries * 50

        response, results = await self.run_agentic_retrieval(
            messages,
            self.agent_client,
            search_index_name=self.search_index_name,
            top=top,
            filter_add_on=search_index_filter,
            minimum_reranker_score=minimum_reranker_score,
            max_docs_for_reranker=max_docs_for_reranker,
            results_merge_strategy=results_merge_strategy,
        )

        text_sources = self.get_sources_content(results, use_semantic_captions=False, use_image_citation=False)

        extra_info = ExtraInfo(
            DataPoints(text=text_sources),
            thoughts=[
                ThoughtStep(
                    "Use agentic retrieval",
                    messages,
                    {
                        "reranker_threshold": minimum_reranker_score,
                        "max_docs_for_reranker": max_docs_for_reranker,
                        "results_merge_strategy": results_merge_strategy,
                        "filter": search_index_filter,
                    },
                ),
                ThoughtStep(
                    f"Agentic retrieval results (top {top})",
                    [result.serialize_for_results() for result in results],
                    {
                        "query_plan": (
                            [activity.as_dict() for activity in response.activity] if response.activity else None
                        ),
                        "model": self.agent_model,
                        "deployment": self.agent_deployment,
                    },
                ),
            ],
        )
        return extra_info

    def _is_pilot_related_query(self, query: str) -> bool:
        """
        Detecta si la consulta está relacionada con pilotos de aerolíneas o documentos de la carpeta Pilotos
        También detecta consultas generales sobre documentos disponibles
        """
        pilot_keywords = [
            "piloto", "pilotos", "pilot", "pilots",
            "capitán", "capitan", "captain", "comandante",
            "aerolínea", "aerolinea", "airline", "aviación", "aviation",
            "vuelo", "vuelos", "flight", "flights",
            "cabina", "cockpit", "tripulación", "crew",
            "aviador", "aviadores", "aviator", "aviators",
            "licencia de piloto", "certificación", "certificaciones", "entrenamiento",
            "instructor de vuelo", "flight instructor"
        ]
        
        # Patrones de consultas generales sobre documentos
        general_document_patterns = [
            "qué documentos tienes", "que documentos tienes",
            "documentos disponibles", "documentos que tienes",
            "archivos disponibles", "archivos que tienes",
            "qué archivos tienes", "que archivos tienes",
            "muestra documentos", "muestra archivos",
            "lista de documentos", "lista de archivos",
            "documentos de", "archivos de",
            "qué información tienes", "que información tienes",
            "información disponible", "datos disponibles",
            "what documents", "available documents", "show me documents",
            "list documents", "list files", "available files"
        ]
        
        query_lower = query.lower()
        
        # Primero verificar si es una consulta específica sobre pilotos
        if any(keyword in query_lower for keyword in pilot_keywords):
            return True
            
        # Luego verificar si es una consulta general sobre documentos
        # (para Volaris, asumir que documentos generales = documentos de pilotos)
        if any(pattern in query_lower for pattern in general_document_patterns):
            return True
            
        return False

    async def _search_sharepoint_files(self, query: str, top: int = 25) -> list[dict]:
        """
        Busca archivos EXCLUSIVAMENTE en la carpeta 'PILOTOS' de SharePoint
        """
        try:
            # Importar las funciones directas de Graph API
            from core.graph import get_access_token, get_drive_id, list_pilotos_files, get_file_content
            import os
            
            # Paso 1: Obtener token de acceso
            token = get_access_token()
            
            # Paso 2: Obtener el drive ID
            site_id = os.getenv("SHAREPOINT_SITE_ID")
            drive_id = get_drive_id(site_id, token)
            
            # Paso 3: Listar archivos en la carpeta PILOTOS
            files = list_pilotos_files(drive_id, token)
            
            results = []
            for file in files[:top]:  # Limitar a top resultados
                try:
                    file_name = file.get('name', 'Unknown')
                    file_id = file.get('id', '')
                    
                    # Obtener contenido del archivo para mejor contexto
                    try:
                        content = get_file_content(drive_id, file_id, token)
                        if content and len(content.strip()) > 0:
                            results.append({
                                'name': file_name,
                                'content': content[:2000],  # Limitar contenido
                                'source': 'SharePoint PILOTOS',
                                'url': file.get('webUrl', '')
                            })
                    except Exception as content_error:
                        # Si no se puede leer el contenido, al menos incluir el nombre
                        results.append({
                            'name': file_name,
                            'content': f"Documento encontrado: {file_name} (contenido no accesible)",
                            'source': 'SharePoint PILOTOS',
                            'url': file.get('webUrl', '')
                        })
                        print(f"No se pudo leer contenido de {file_name}: {content_error}")
                        
                except Exception as file_error:
                    print(f"Error procesando archivo: {file_error}")
                    continue
            
            print(f"SharePoint search returned {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            print(f"Error en búsqueda SharePoint: {e}")
            return []
