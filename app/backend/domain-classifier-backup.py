import os
import re
import json
import asyncio
from typing import List, Dict, Optional, Union
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchFieldDataType
)

class DomainClassifierSetup:
    def __init__(self, search_client: SearchIndexClient, embeddings_service):
        self.search_client = search_client
        self.embeddings_service = embeddings_service
        self._llm_client = None
        
    def create_domain_classifier_index(self):
        """Create a specialized index for domain classification"""
        index_name = "domain-classifier-index"
        
        # Get the actual embedding dimensions from the environment
        embedding_dimensions = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "1536"))
        print(f"Creating index with embedding dimensions: {embedding_dimensions}")
        
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="domain", type=SearchFieldDataType.String, facetable=True, filterable=True),
            SearchableField(name="sample_questions", type=SearchFieldDataType.String),
            SearchableField(name="keywords", type=SearchFieldDataType.String),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchableField(name="topics", type=SearchFieldDataType.String),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=embedding_dimensions,
                vector_search_profile_name="myHnswProfile"
            )
        ]
        
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
            profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
        )
        
        semantic_config = SemanticConfiguration(
            name="default",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="domain"),
                content_fields=[SemanticField(field_name="description")]
            )
        )
        
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config])
        )
        
        self.search_client.create_or_update_index(index)
        return index_name
    
    def _get_llm_client(self):
        """Get or create LLM client for chat completions"""
        if self._llm_client is not None:
            return self._llm_client
            
        from openai import AsyncAzureOpenAI
        
        # Get configuration
        model_deployment = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "chat")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-06-01"
        
        print(f"DEBUG: Azure OpenAI Endpoint: {endpoint}")
        print(f"DEBUG: Model Deployment: {model_deployment}")
        print(f"DEBUG: API Version: {api_version}")
        
        if not endpoint:
            print("Error: AZURE_OPENAI_ENDPOINT is not set")
            return None
        
        try:
            api_key = os.environ.get("AZURE_OPENAI_API_KEY_OVERRIDE")
            
            if api_key:
                print("AZURE_OPENAI_API_KEY_OVERRIDE found, using as api_key for Azure OpenAI client")
                self._llm_client = AsyncAzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=endpoint,
                    api_version=api_version,
                    max_retries=3,
                    timeout=60.0
                )
                print("DEBUG: LLM client created with API key")
            else:
                from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
                
                print("Using Azure credential (passwordless authentication) for Azure OpenAI client")
                azure_credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    azure_credential,
                    "https://cognitiveservices.azure.com/.default"
                )
                
                self._llm_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=api_version,
                    max_retries=3,
                    timeout=60.0
                )
                print("DEBUG: LLM client created with Managed Identity")
                
        except Exception as e:
            print(f"Error creating LLM client: {e}")
            import traceback
            traceback.print_exc()
            return None
                
        return self._llm_client
    
    def _get_model_deployment(self) -> Optional[str]:
        """Get the chat model deployment name"""
        return os.environ.get("AZURE_OPENAI_GPT4_DEPLOYMENT", 
                            os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT"))
    
    async def _call_llm_with_retry(self, prompt: str, system_prompt: str, 
                                  temperature: float = 0.3, max_tokens: int = 500) -> Optional[str]:
        """Generic method to call LLM with retry logic"""
        model_deployment = self._get_model_deployment()
        if not model_deployment:
            return None
            
        client = self._get_llm_client()
        if not client:
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=model_deployment,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise e
        return None
    
    def _parse_json_response(self, response_text: str, fallback_pattern: str = r'"([^"]+)"') -> List[str]:
        """Parse JSON response with fallback"""
        try:
            import json
            result = json.loads(response_text)
            if isinstance(result, list):
                return [item for item in result if item and isinstance(item, str)]
        except:
            # Fallback: extract using regex
            matches = re.findall(fallback_pattern, response_text)
            if matches:
                return matches
            # Further fallback: split by newlines
            return [line.strip() for line in response_text.split('\n') if line.strip()]
        return []
        
    async def extract_domain_characteristics(self, file_paths: List[str], category: str) -> Dict:
        """Extract domain characteristics from documents"""
        all_content = []
        topics = set()
        
        # Filter out non-document files
        valid_extensions = ['.txt', '.md', '.docx', '.pdf', '.doc', '.html', '.csv', '.json', 
                          '.pptx', '.xlsx']
        
        document_paths = [
            fp for fp in file_paths 
            if os.path.isfile(fp) 
            and not fp.endswith('.md5')
            and any(fp.lower().endswith(ext) for ext in valid_extensions)
        ]
        
        if not document_paths:
            print(f"No valid documents found for {category}")
            return self._get_default_characteristics(category)
        
        print(f"Processing {len(document_paths)} documents for {category}")
        
        # Read and analyze documents
        for file_path in document_paths[:10]:  # Limit to first 10 documents
            try:
                print(f"Processing: {os.path.basename(file_path)}")
                content = await self.read_file(file_path)
                if content and len(content.strip()) > 50:
                    all_content.append(content)
                    extracted_topics = await self.extract_topics(content)
                    topics.update(extracted_topics)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        if not all_content:
            print(f"No content extracted from {category} documents")
            return self._get_default_characteristics(category)
        
        # Generate sample questions and keywords
        sample_questions = await self.generate_sample_questions(all_content[:5])
        keywords = await self.extract_keywords(all_content)
        
        return {
            "domain": category,
            "sample_questions": sample_questions,
            "keywords": keywords,
            "topics": list(topics)[:20],
            "description": f"Documents related to {category} - {', '.join(list(topics)[:5])}"
        }
    
    def _get_default_characteristics(self, category: str) -> Dict:
        """Get default characteristics for a category"""
        return {
            "domain": category,
            "sample_questions": [f"What is {category}?", f"How does {category} work?", f"What are the key features of {category}?"],
            "keywords": [category.lower()],
            "topics": [category],
            "description": f"Documents related to {category}"
        }
    
    async def populate_classifier_index(self, cosmic_docs: List[str], substrate_docs: List[str]):
        """Populate the classifier index with domain information"""
        index_name = "domain-classifier-index"
        
        # Create a synchronous SearchClient for the index
        search_client = SearchClient(
            endpoint=self.search_client._endpoint,
            index_name=index_name,
            credential=self.search_client._credential
        )
        
        # Extract characteristics for each domain
        cosmic_chars = await self.extract_domain_characteristics(cosmic_docs, "Cosmic")
        substrate_chars = await self.extract_domain_characteristics(substrate_docs, "Substrate")
        
        # Create embeddings for each domain
        embeddings = await self._create_embeddings_for_domains(cosmic_chars, substrate_chars)
        if not embeddings:
            print("Failed to create embeddings")
            return
            
        cosmic_embedding, substrate_embedding = embeddings
        
        # Verify embedding dimensions
        expected_dims = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "1536"))
        print(f"Expected embedding dimensions: {expected_dims}")
        print(f"Actual cosmic embedding dimensions: {len(cosmic_embedding)}")
        print(f"Actual substrate embedding dimensions: {len(substrate_embedding)}")
        
        # Upload to index
        documents = [
            self._create_document("cosmic-domain", cosmic_chars, cosmic_embedding),
            self._create_document("substrate-domain", substrate_chars, substrate_embedding)
        ]
        
        try:
            result = search_client.upload_documents(documents=documents)
            print(f"\nUploaded {len(documents)} domain classifier documents")
            for r in result:
                if hasattr(r, 'succeeded'):
                    print(f"Document {r.key}: {r.succeeded}")
                else:
                    print(f"Document uploaded: {r}")
        except Exception as e:
            print(f"Error uploading documents: {e}")
            import traceback
            traceback.print_exc()

    async def _create_embeddings_for_domains(self, cosmic_chars: Dict, substrate_chars: Dict) -> Optional[tuple]:
        """Create embeddings for domain characteristics"""
        cosmic_text = json.dumps(cosmic_chars)
        substrate_text = json.dumps(substrate_chars)
        
        try:
            cosmic_response = await self.embeddings_service.create_embeddings([cosmic_text])
            substrate_response = await self.embeddings_service.create_embeddings([substrate_text])
            
            # Extract embeddings
            cosmic_embedding = self._extract_embedding(cosmic_response)
            substrate_embedding = self._extract_embedding(substrate_response)
            
            return (cosmic_embedding, substrate_embedding)
        except Exception as e:
            print(f"Error creating embeddings: {e}")
            return None
    
    def _extract_embedding(self, response) -> List[float]:
        """Extract embedding vector from response"""
        if isinstance(response, list):
            embedding = response[0]
        else:
            embedding = response.data[0].embedding
            
        if not isinstance(embedding, list):
            embedding = list(embedding)
            
        return embedding
    
    def _create_document(self, doc_id: str, characteristics: Dict, embedding: List[float]) -> Dict:
        """Create a document for indexing"""
        return {
            "id": doc_id,
            "domain": characteristics["domain"],
            "sample_questions": "\n".join(characteristics.get("sample_questions", [])),
            "keywords": ", ".join(characteristics.get("keywords", [])),
            "topics": ", ".join(characteristics.get("topics", [])),
            "description": characteristics.get("description", ""),
            "embedding": embedding
        }

    async def read_file(self, file_path: str) -> str:
        """Read content from a file using appropriate parser"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        parser_map = {
            '.docx': lambda: self._read_docx(file_path),
            '.pdf': lambda: self._read_pdf(file_path),
            '.html': lambda: self._read_with_parser(file_path, 'htmlparser', 'LocalHTMLParser'),
            '.csv': lambda: self._read_with_parser(file_path, 'csvparser', 'CsvParser'),
            '.json': lambda: self._read_with_parser(file_path, 'jsonparser', 'JsonParser'),
            '.txt': lambda: self._read_with_parser(file_path, 'textparser', 'TextParser'),
            '.md': lambda: self._read_with_parser(file_path, 'textparser', 'TextParser')
        }
        
        reader = parser_map.get(file_extension)
        if reader:
            try:
                return await reader()
            except Exception as e:
                print(f"Error reading {file_extension} file {file_path}: {e}")
                return ""
        else:
            # Default text reading
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return ""
    
    async def _read_with_parser(self, file_path: str, module_name: str, class_name: str) -> str:
        """Generic method to read files with parsers"""
        try:
            module = __import__(f'prepdocslib.{module_name}', fromlist=[class_name])
            parser_class = getattr(module, class_name)
            parser = parser_class()
            
            with open(file_path, 'rb') as f:
                pages = []
                async for page in parser.parse(f):
                    pages.append(page.text if hasattr(page, 'text') else str(page))
                return '\n'.join(pages)
        except Exception as e:
            print(f"Error using {class_name}: {e}")
            return ""
    
    async def _read_docx(self, file_path: str) -> str:
        """Read DOCX files"""
        return await self._read_with_parser(file_path, 'docxparser', 'DocxHyperlinkParser')
    
    async def _read_pdf(self, file_path: str) -> str:
        """Read PDF files"""
        use_local_pdf_parser = os.getenv("USE_LOCAL_PDF_PARSER", "false").lower() != "false"
        
        if use_local_pdf_parser or os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE") is None:
            return await self._read_with_parser(file_path, 'pdfparser', 'LocalPdfParser')
        else:
            # Use Document Intelligence parser
            try:
                from prepdocslib.pdfparser import DocumentAnalysisParser
                from azure.identity import DefaultAzureCredential
                
                doc_int_service = os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE")
                credential = DefaultAzureCredential()
                
                parser = DocumentAnalysisParser(
                    endpoint=f"https://{doc_int_service}.cognitiveservices.azure.com/",
                    credential=credential
                )
                
                with open(file_path, 'rb') as f:
                    pages = []
                    async for page in parser.parse(f):
                        pages.append(page.text)
                    return '\n'.join(pages)
            except Exception as e:
                print(f"Error using Document Intelligence: {e}")
                return ""
    
    async def extract_topics(self, content: str) -> List[str]:
        """Extract topics from content using LLM"""
        if not content or len(content.strip()) < 50:
            return []
        
        max_content_length = 90000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Analyze the following technical document content and extract the main topics, technologies, and themes.
Focus on specific technical concepts, tools, platforms, and processes mentioned.
Return 10-15 specific topics as a JSON array of strings.
Be specific - instead of generic terms like "monitoring", use specific terms like "Azure Monitor" or "performance telemetry".

Document content:
{content}

Example output format: ["Azure Kubernetes Service", "container orchestration", "microservices architecture", "CI/CD pipelines", "load balancing"]
"""
        
        try:
            response = await self._call_llm_with_retry(
                prompt, 
                "You are a technical documentation analyst. Extract specific, concrete topics from technical documents.",
                temperature=0.3,
                max_tokens=500
            )
            
            if response:
                topics = self._parse_json_response(response)
                return topics[:15]
        except Exception as e:
            print(f"Error extracting topics with LLM: {e}")
        
        return self._fallback_topic_extraction(content)
    
    def _fallback_topic_extraction(self, content: str) -> List[str]:
        """Fallback topic extraction with domain-specific keywords"""
        topics = []
        
        domain_keywords = {
            "cosmic": ["cosmic", "watson", "performance monitoring", "diagnostics", "telemetry",
                      "container platform", "microservices", "kubernetes", "docker", "orchestration"],
            "substrate": ["substrate", "infrastructure", "cloud platform", "azure", "deployment",
                         "virtual machines", "networking", "storage", "security", "compliance"]
        }
        
        content_lower = content.lower()
        
        # Check for domain-specific keywords
        for keywords in domain_keywords.values():
            for keyword in keywords:
                if keyword in content_lower:
                    topics.append(keyword.title())
        
        # Extract capitalized phrases
        import re
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', content)
        topics.extend(list(set(capitalized_phrases))[:5])
        
        return list(set(topics))[:10]
    
    async def generate_sample_questions(self, contents: List[str]) -> List[str]:
        """Generate sample questions using LLM based on actual document content"""
        if not contents:
            return ["What are the key features?", "How do I configure this?", "What are common issues?"]
            
        combined_content = "\n\n---\n\n".join(contents[:5])
        max_content_length = 90000
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "..."
        
        prompt = f"""Based on the following technical documentation content, generate 7-10 realistic questions that users would ask.
The questions should be specific to the actual content, mentioning specific features, tools, or processes described in the documents.
Include a mix of how-to questions, troubleshooting questions, and conceptual questions.
Return only the questions as a JSON array of strings.

Document content:
{combined_content}

Example output format: ["How do I configure Watson monitoring for my Cosmic deployment?", "What are the performance tuning options for Substrate?", "How can I troubleshoot connection issues in the platform?"]
"""
        
        try:
            response = await self._call_llm_with_retry(
                prompt,
                "You are a technical support expert. Generate realistic questions users would ask about the documented technology.",
                temperature=0.7,
                max_tokens=600
            )
            
            if response:
                questions = self._parse_json_response(response, r'"([^"]+\?)"')
                return [q for q in questions if '?' in q][:10]
        except Exception as e:
            print(f"Error generating questions with LLM: {e}")
            
        return self._generate_fallback_questions(contents)
    
    def _generate_fallback_questions(self, contents: List[str]) -> List[str]:
        """Generate context-aware fallback questions"""
        combined = " ".join(contents[:2])[:1000].lower() if contents else ""
        
        question_templates = {
            "cosmic": [
                "How do I set up Cosmic monitoring for my application?",
                "What are the performance metrics available in Cosmic?",
                "How can I troubleshoot Cosmic deployment issues?"
            ],
            "substrate": [
                "How do I configure Substrate infrastructure?",
                "What are the security best practices for Substrate?",
                "How can I scale my Substrate deployment?"
            ],
            "error": ["How do I diagnose and fix common errors?"],
            "performance": ["What are the performance optimization techniques?"],
            "config": ["What are the initial configuration steps?"]
        }
        
        questions = []
        for keyword, template_questions in question_templates.items():
            if keyword in combined:
                questions.extend(template_questions)
        
        if not questions:
            questions = [
                "What are the key features?",
                "How do I get started?",
                "What are the best practices?"
            ]
        
        return questions[:7]
    
    async def extract_keywords(self, contents: List[str]) -> List[str]:
        """Extract keywords from contents using LLM"""
        if not contents:
            return ["technical", "documentation", "system"]
            
        combined_content = "\n\n".join(contents[:8])
        max_content_length = 90000
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "..."
        
        prompt = f"""Extract 20-30 important technical keywords and key phrases from the following documentation.
Focus on:
- Product names and features
- Technical terms and technologies
- Platform-specific concepts
- Tools and services mentioned
- Important processes or methodologies

Avoid generic terms. Be specific to the actual content.
Return only the keywords as a JSON array of strings.

Document content:
{combined_content}

Example output format: ["Azure Kubernetes Service", "Watson Analytics", "container orchestration", "performance telemetry", "microservice deployment"]
"""
        
        try:
            response = await self._call_llm_with_retry(
                prompt,
                "You are a technical keyword extraction expert. Extract specific, meaningful keywords from technical documentation.",
                temperature=0.3,
                max_tokens=500
            )
            
            if response:
                keywords = self._parse_json_response(response)
                return list(set(keywords))[:30]
        except Exception as e:
            print(f"Error extracting keywords with LLM: {e}")
            
        return self._enhanced_keyword_extraction(contents)
    
    def _enhanced_keyword_extraction(self, contents: List[str]) -> List[str]:
        """Enhanced fallback keyword extraction"""
        import re
        
        keywords = set()
        
        for content in contents[:3]:
            # Extract various patterns
            patterns = [
                r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b',  # Capitalized phrases
                r'"([^"]+)"',  # Quoted text
                r'\b\w+[-]\w+\b|\b\w+\d+\w*\b'  # Technical terms
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if pattern == r'"([^"]+)"':
                    keywords.update([m for m in matches if len(m.split()) <= 3])
                else:
                    keywords.update(matches)
        
        # Filter and clean keywords
        stopwords = self._get_stopwords()
        cleaned_keywords = [
            kw.strip() for kw in keywords
            if len(kw.strip()) > 3 and len(kw.split()) <= 3 
            and kw.lower() not in stopwords
        ]
        
        # Sort by length and alphabetically
        cleaned_keywords.sort(key=lambda x: (-len(x.split()), x))
        
        return cleaned_keywords[:20]
    
    def _get_stopwords(self) -> set:
        """Get common stopwords to filter out"""
        return {
            "the", "is", "at", "which", "on", "and", "a", "an", "as", "are", 
            "was", "were", "been", "have", "has", "had", "do", "does", "did", 
            "will", "would", "should", "could", "may", "might", "must", "can", 
            "to", "of", "in", "for", "with", "from", "this", "that", "these", 
            "those", "then", "than", "when", "where", "what", "how", "why"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        if self._llm_client:
            try:
                await self._llm_client.close()
            except:
                pass
            self._llm_client = None