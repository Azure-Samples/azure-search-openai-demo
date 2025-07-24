from collections.abc import Awaitable
from typing import Any, Optional, Union, cast

from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

from approaches.approach import DataPoints, ExtraInfo, ThoughtStep
from approaches.chatapproach import ChatApproach
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper


class ChatReadRetrieveReadApproach(ChatApproach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
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
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
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
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.embedding_field = embedding_field
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.prompt_manager = prompt_manager
        self.query_rewrite_prompt = self.prompt_manager.load_prompt("chat_query_rewrite.prompty")
        self.query_rewrite_tools = self.prompt_manager.load_tools("chat_query_rewrite_tools.json")
        self.answer_prompt = self.prompt_manager.load_prompt("chat_answer_question.prompty")
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True

    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[ExtraInfo, Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]]]:
        use_agentic_retrieval = True if overrides.get("use_agentic_retrieval") else False
        original_user_query = messages[-1]["content"]

        reasoning_model_support = self.GPT_REASONING_MODELS.get(self.chatgpt_model)
        if reasoning_model_support and (not reasoning_model_support.streaming and should_stream):
            raise Exception(
                f"{self.chatgpt_model} does not support streaming. Please use a different model or disable streaming."
            )
        if use_agentic_retrieval:
            extra_info = await self.run_agentic_retrieval_approach(messages, overrides, auth_claims)
        else:
            extra_info = await self.run_search_approach(messages, overrides, auth_claims)

        messages = self.prompt_manager.render_prompt(
            self.answer_prompt,
            self.get_system_prompt_variables(overrides.get("prompt_template"))
            | {
                "include_follow_up_questions": bool(overrides.get("suggest_followup_questions")),
                "past_messages": messages[:-1],
                "user_query": original_user_query,
                "text_sources": extra_info.data_points.text,
            },
        )

        chat_coroutine = cast(
            Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]],
            self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages,
                overrides,
                self.get_response_token_limit(self.chatgpt_model, 1024),
                should_stream,
            ),
        )
        extra_info.thoughts.append(
            self.format_thought_step_for_chatcompletion(
                title="Prompt to generate answer",
                messages=messages,
                overrides=overrides,
                model=self.chatgpt_model,
                deployment=self.chatgpt_deployment,
                usage=None,
            )
        )
        return (extra_info, chat_coroutine)

    async def run_search_approach(
        self, messages: list[ChatCompletionMessageParam], overrides: dict[str, Any], auth_claims: dict[str, Any]
    ):
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        use_query_rewriting = True if overrides.get("query_rewriting") else False
        top = overrides.get("top", 1)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        search_index_filter = self.build_filter(overrides, auth_claims)

        original_user_query = messages[-1]["content"]
        if not isinstance(original_user_query, str):
            raise ValueError("The most recent message content must be a string.")

        query_messages = self.prompt_manager.render_prompt(
            self.query_rewrite_prompt, {"user_query": original_user_query, "past_messages": messages[:-1]}
        )
        tools: list[ChatCompletionToolParam] = self.query_rewrite_tools

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question

        chat_completion = cast(
            ChatCompletion,
            await self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages=query_messages,
                overrides=overrides,
                response_token_limit=self.get_response_token_limit(
                    self.chatgpt_model, 100
                ),  # Setting too low risks malformed JSON, setting too high may affect performance
                temperature=0.0,  # Minimize creativity for search query generation
                tools=tools,
                reasoning_effort="low",  # Minimize reasoning for search query generation
            ),
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors: list[VectorQuery] = []
        if use_vector_search:
            vectors.append(await self.compute_text_embedding(query_text))

        results = await self.search(
            top,
            query_text,
            search_index_filter,
            vectors,
            use_text_search,
            use_vector_search,
            use_semantic_ranker,
            use_semantic_captions,
            minimum_search_score,
            minimum_reranker_score,
            use_query_rewriting,
        )

        # PASO 2.5: Si la consulta está relacionada con pilotos, buscar también en SharePoint
        sharepoint_results = []
        if self._is_pilot_related_query(original_user_query):
            sharepoint_results = await self._search_sharepoint_files(query_text, top)
            print(f"DEBUG: SharePoint search returned {len(sharepoint_results)} results")
            for i, result in enumerate(sharepoint_results):
                print(f"DEBUG: SharePoint result {i+1}: {result.get('content', 'No content')}")

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        text_sources = self.get_sources_content(results, use_semantic_captions, use_image_citation=False)
        print(f"DEBUG: Azure AI Search returned {len(text_sources)} text sources")
        for i, source in enumerate(text_sources[:3]):  # Solo primeros 3
            print(f"DEBUG: Azure source {i+1}: {source[:100]}...")
        
        # Combinar con resultados de SharePoint si los hay
        if sharepoint_results:
            text_sources = self._combine_search_results(text_sources, sharepoint_results)
            print(f"DEBUG: Combined sources total: {len(text_sources)}")

        extra_info = ExtraInfo(
            DataPoints(text=text_sources),
            thoughts=[
                self.format_thought_step_for_chatcompletion(
                    title="Prompt to generate search query",
                    messages=query_messages,
                    overrides=overrides,
                    model=self.chatgpt_model,
                    deployment=self.chatgpt_deployment,
                    usage=chat_completion.usage,
                    reasoning_effort="low",
                ),
                ThoughtStep(
                    "Search using generated search query",
                    query_text,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "use_query_rewriting": use_query_rewriting,
                        "top": top,
                        "filter": search_index_filter,
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
        return extra_info

    async def run_agentic_retrieval_approach(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
    ):
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0)
        search_index_filter = self.build_filter(overrides, auth_claims)
        top = overrides.get("top", 1)
        max_subqueries = overrides.get("max_subqueries", 10)
        results_merge_strategy = overrides.get("results_merge_strategy", "interleaved")
        # 50 is the amount of documents that the reranker can process per query
        max_docs_for_reranker = max_subqueries * 50

        response, results = await self.run_agentic_retrieval(
            messages=messages,
            agent_client=self.agent_client,
            search_index_name=self.search_index_name,
            top=top,
            filter_add_on=search_index_filter,
            minimum_reranker_score=minimum_reranker_score,
            max_docs_for_reranker=max_docs_for_reranker,
            results_merge_strategy=results_merge_strategy,
        )

        # También buscar en SharePoint si la consulta está relacionada con pilotos
        original_user_query = messages[-1]["content"]
        sharepoint_results = []
        if isinstance(original_user_query, str):
            if self._is_pilot_related_query(original_user_query):
                sharepoint_results = await self._search_sharepoint_files(original_user_query, top)

        text_sources = self.get_sources_content(results, use_semantic_captions=False, use_image_citation=False)
        
        # Combinar con resultados de SharePoint si los hay
        if sharepoint_results:
            text_sources = self._combine_search_results(text_sources, sharepoint_results)

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
                        file_content = get_file_content(drive_id, file_id, token)
                        # Limitar contenido para no saturar el contexto
                        if len(file_content) > 1000:
                            file_content = file_content[:1000] + "..."
                    except:
                        file_content = f"Archivo disponible: {file_name}"
                    
                    results.append({
                        'content': file_content,
                        'source': f"SharePoint PILOTOS: {file_name}",
                        'url': file.get('webUrl', ''),
                        'filename': file_name,
                        'lastModified': file.get('lastModifiedDateTime', ''),
                        'score': 1.0  # Puntuación alta para archivos de carpeta PILOTOS
                    })
                    
                except Exception as e:
                    print(f"Error procesando archivo {file.get('name', 'Unknown')}: {e}")
                    # Incluir información básica aunque falle
                    results.append({
                        'content': f"Documento disponible en carpeta PILOTOS: {file.get('name', 'Unknown')}",
                        'source': f"SharePoint PILOTOS: {file.get('name', 'Unknown')}",
                        'url': file.get('webUrl', ''),
                        'filename': file.get('name', 'Unknown'),
                        'score': 0.8
                    })

            print(f"DEBUG: SharePoint PILOTOS search returned {len(results)} results")
            return results
            
        except Exception as e:
            print(f"ERROR: Error buscando en SharePoint PILOTOS: {e}")
            return []

    def _is_pilot_related_query(self, query: str) -> bool:
        """
        Determina si una consulta está relacionada con pilotos
        Para Volaris: TODAS las consultas van a la carpeta PILOTOS
        """
        # Para simplificar: SIEMPRE buscar en PILOTOS
        return True

    def _combine_search_results(self, azure_sources: list[str], sharepoint_results: list[dict]) -> list[str]:
        """
        Combina resultados de Azure AI Search y SharePoint en el formato esperado
        """
        combined_sources = azure_sources.copy()
        
        # Agregar resultados de SharePoint en el formato esperado (string con citación)
        for result in sharepoint_results:
            # Usar la URL real de SharePoint si está disponible, sino usar el source como fallback
            citation_url = result.get('url', '') or result['source']
            
            # Si tenemos una URL real de SharePoint, usarla; sino usar el formato original
            if citation_url and citation_url.startswith('http'):
                # Usar la URL real de SharePoint como citación
                citation = citation_url
            else:
                # Fallback al formato original si no hay URL
                citation = result['source']
            
            content = result['content'].replace("\n", " ").replace("\r", " ")
            combined_sources.append(f"{citation}: {content}")
            
            print(f"DEBUG: SharePoint citation - URL: {citation_url}, Citation: {citation}")
        
        return combined_sources

    async def _process_pdf_from_sharepoint(self, drive_id: str, file_id: str, token: str, file_name: str) -> str:
        """
        Procesa un PDF de SharePoint usando Document Intelligence
        """
        try:
            import requests
            import os
            import asyncio
            import json
            
            # Descargar archivo PDF como bytes
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            pdf_bytes = response.content
            
            # Verificar si Document Intelligence está disponible
            doc_intel_service = os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE")
            if not doc_intel_service:
                return f"[PDF: {file_name}] Document Intelligence no configurado - archivo disponible pero no procesado"
            
            # Usar las credenciales de Azure configuradas
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            token_doc_intel = await credential.get_token("https://cognitiveservices.azure.com/.default")
            
            # Endpoint de Document Intelligence
            endpoint = f"https://{doc_intel_service}.cognitiveservices.azure.com/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview"
            
            # Headers para Document Intelligence
            headers_doc_intel = {
                "Authorization": f"Bearer {token_doc_intel.token}",
                "Content-Type": "application/pdf"
            }
            
            # Enviar PDF para análisis
            response = requests.post(endpoint, headers=headers_doc_intel, data=pdf_bytes)
            
            if response.status_code == 202:
                # Obtener URL de resultado
                operation_location = response.headers.get('Operation-Location')
                if operation_location:
                    # Esperar y obtener resultados
                    await asyncio.sleep(3)  # Espera inicial
                    
                    result_headers = {
                        "Authorization": f"Bearer {token_doc_intel.token}"
                    }
                    
                    for attempt in range(10):  # Máximo 10 intentos
                        result_response = requests.get(operation_location, headers=result_headers)
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            if result_data.get('status') == 'succeeded':
                                # Extraer texto
                                content_text = ""
                                if 'analyzeResult' in result_data and 'content' in result_data['analyzeResult']:
                                    content_text = result_data['analyzeResult']['content']
                                
                                if content_text:
                                    print(f"✅ Document Intelligence procesó {file_name}: {len(content_text)} caracteres")
                                    return content_text
                                break
                            elif result_data.get('status') == 'failed':
                                break
                        
                        await asyncio.sleep(2)  # Esperar antes del siguiente intento
            
            # Si Document Intelligence falla, usar texto básico
            return f"[PDF: {file_name}] Documento disponible en SharePoint - contenido requiere procesamiento manual"
            
        except Exception as e:
            print(f"Error procesando PDF {file_name} con Document Intelligence: {e}")
            return f"[PDF: {file_name}] Error procesando documento - archivo disponible en SharePoint"
    
    async def _get_text_content(self, drive_id: str, file_id: str, token: str) -> str:
        """
        Obtiene contenido de texto de archivos no-PDF
        """
        try:
            import requests
            
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Intentar decodificar como texto
            try:
                return response.text
            except:
                return f"Archivo binario disponible en SharePoint"
                
        except Exception as e:
            print(f"Error obteniendo contenido de texto: {e}")
            return "Contenido no disponible"
