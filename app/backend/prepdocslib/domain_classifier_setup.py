import os
import re
import json
import asyncio
from typing import List, Dict, Optional
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
        self._credential = None  # Add this to track the credential
        
    def create_domain_classifier_index(self):
        """Create a specialized index for domain classification"""
        index_name = "domain-classifier-index"
        
        # Get the actual embedding dimensions from the environment
        embedding_dimensions = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "1536"))
        print(f"Creating index with embedding dimensions: {embedding_dimensions}")
        
        # Check if index already exists
        try:
            existing_index = self.search_client.get_index(index_name)
            # Check if embedding dimensions match
            existing_embedding_field = next((f for f in existing_index.fields if f.name == "embedding"), None)
            if existing_embedding_field and hasattr(existing_embedding_field, 'vector_search_dimensions'):
                if existing_embedding_field.vector_search_dimensions == embedding_dimensions:
                    print(f"Index '{index_name}' already exists with correct dimensions. Using existing index.")
                    return index_name
                else:
                    print(f"Index '{index_name}' exists with different dimensions ({existing_embedding_field.vector_search_dimensions}). Deleting and recreating...")
                    self.search_client.delete_index(index_name)
            else:
                print(f"Index '{index_name}' exists but couldn't verify dimensions. Recreating...")
                self.search_client.delete_index(index_name)
        except Exception as e:
            print(f"Index '{index_name}' doesn't exist. Creating new index...")
    
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="domain", type=SearchFieldDataType.String, facetable=True, filterable=True),
            SearchableField(name="sample_questions", type=SearchFieldDataType.String),
            SearchableField(name="keywords", type=SearchFieldDataType.String),
            SearchableField(name="description", type=SearchFieldDataType.String),
            # Change topics to a simple searchable string field instead of collection
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
        
        # create_or_update_index is synchronous
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
                self._credential = DefaultAzureCredential()  # Store the credential
                token_provider = get_bearer_token_provider(
                    self._credential,
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
        
    async def extract_domain_characteristics(self, file_paths: List[str], category: str) -> Dict:
        """Extract domain characteristics from documents"""
        all_content = []
        topics = set()
        
        # Filter out non-document files - include all supported formats from prepdocs.py
        valid_extensions = ['.txt', '.md', '.docx', '.pdf', '.doc', '.html', '.csv', '.json', 
                          '.pptx', '.xlsx']
        
        # Filter to only actual files (not directories) and exclude .md5 files
        document_paths = [
            fp for fp in file_paths 
            if os.path.isfile(fp) 
            and not fp.endswith('.md5')
            and any(fp.lower().endswith(ext) for ext in valid_extensions)
        ]
        
        if not document_paths:
            print(f"No valid documents found for {category}")
            return {
                "domain": category,
                "sample_questions": [f"What is {category}?", f"How does {category} work?"],
                "keywords": [category.lower()],
                "topics": [category],
                "description": f"Documents related to {category}"
            }
        
        print(f"Processing {len(document_paths)} documents for {category}")
        
        # Read and analyze documents
        for file_path in document_paths[:10]:  # Limit to first 10 documents
            try:
                print(f"Processing: {os.path.basename(file_path)}")
                content = await self.read_file(file_path)
                if content and len(content.strip()) > 50:  # Only process non-empty content
                    all_content.append(content)
                    
                    # Extract topics using LLM
                    extracted_topics = await self.extract_topics(content)
                    topics.update(extracted_topics)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        if not all_content:
            print(f"No content extracted from {category} documents")
            return {
                "domain": category,
                "sample_questions": [f"What is {category}?", f"How does {category} work?"],
                "keywords": [category.lower()],
                "topics": [category],
                "description": f"Documents related to {category}"
            }
        
        # Generate sample questions and keywords
        sample_questions = await self.generate_sample_questions(all_content[:5])  # Use first 5 docs
        keywords = await self.extract_keywords(all_content)
        
        return {
            "domain": category,
            "sample_questions": sample_questions,
            "keywords": keywords,
            "topics": list(topics)[:20],  # Limit topics
            "description": f"Documents related to {category} - {', '.join(list(topics)[:5])}"
        }
    
    async def populate_classifier_index(self, cosmic_docs: List[str], substrate_docs: List[str]):
        """Populate the classifier index with domain information"""
        index_name = "domain-classifier-index"
        
        # Create a synchronous SearchClient for the index (matching prepdocs.py pattern)
        search_endpoint = self.search_client._endpoint
        credential = self.search_client._credential
        
        # Use synchronous SearchClient instead of async
        from azure.search.documents import SearchClient
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Extract characteristics for each domain
        cosmic_chars = await self.extract_domain_characteristics(cosmic_docs, "Cosmic")
        substrate_chars = await self.extract_domain_characteristics(substrate_docs, "Substrate")
        
        # Create embeddings for each domain
        cosmic_text = json.dumps(cosmic_chars)
        substrate_text = json.dumps(substrate_chars)
        
        # Get embeddings - ensure we get the vector array directly
        cosmic_embedding_response = await self.embeddings_service.create_embeddings([cosmic_text])
        substrate_embedding_response = await self.embeddings_service.create_embeddings([substrate_text])
        
        # Extract the embedding vector from the response
        cosmic_embedding = cosmic_embedding_response[0] if isinstance(cosmic_embedding_response, list) else cosmic_embedding_response.data[0].embedding
        substrate_embedding = substrate_embedding_response[0] if isinstance(substrate_embedding_response, list) else substrate_embedding_response.data[0].embedding
        
        # Ensure embeddings are lists of floats
        if not isinstance(cosmic_embedding, list):
            cosmic_embedding = list(cosmic_embedding)
        if not isinstance(substrate_embedding, list):
            substrate_embedding = list(substrate_embedding)
        
        # Verify embedding dimensions match expected dimensions
        expected_dims = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "1536"))
        print(f"Expected embedding dimensions: {expected_dims}")
        print(f"Actual cosmic embedding dimensions: {len(cosmic_embedding)}")
        print(f"Actual substrate embedding dimensions: {len(substrate_embedding)}")
        
        # Upload to index - convert topics list to comma-separated string
        documents = [
            {
                "id": "cosmic-domain",
                "domain": "Cosmic",
                "sample_questions": "\n".join(cosmic_chars.get("sample_questions", [])),
                "keywords": ", ".join(cosmic_chars.get("keywords", [])),
                "topics": ", ".join(cosmic_chars.get("topics", [])),  # Convert list to string
                "description": cosmic_chars.get("description", ""),
                "embedding": cosmic_embedding
            },
            {
                "id": "substrate-domain", 
                "domain": "Substrate",
                "sample_questions": "\n".join(substrate_chars.get("sample_questions", [])),
                "keywords": ", ".join(substrate_chars.get("keywords", [])),
                "topics": ", ".join(substrate_chars.get("topics", [])),  # Convert list to string
                "description": substrate_chars.get("description", ""),
                "embedding": substrate_embedding
            }
        ]
        
        # Upload documents using synchronous client (matching prepdocs.py pattern)
        try:
            # Use synchronous upload_documents
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
        finally:
            # Synchronous client doesn't need to be closed explicitly
            pass

    async def read_file(self, file_path: str) -> str:
        """Read content from a file, handling different file types using the same approach as prepdocs.py"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.docx':
                # Use the same DocxHyperlinkParser as prepdocs.py
                from prepdocslib.docxparser import DocxHyperlinkParser
                
                try:
                    # Create parser instance
                    parser = DocxHyperlinkParser()
                    
                    # Parse the document
                    with open(file_path, 'rb') as f:
                        pages = []
                        async for page in parser.parse(f):
                            pages.append(page.text if page.text else "")
                    
                    # Return combined text from all pages
                    return '\n'.join(pages)
                    
                except Exception as e:
                    print(f"Error parsing DOCX file {file_path}: {e}")
                    # Fallback: try to read as text
                    try:
                        from prepdocslib.textparser import TextParser
                        parser = TextParser()
                        with open(file_path, 'rb') as f:
                            pages = []
                            async for page in parser.parse(f):
                                pages.append(page.text)
                            return '\n'.join(pages)
                    except:
                        return ""
                        
            elif file_extension == '.pdf':
                # Handle PDF files using the same approach as prepdocs.py
                try:
                    # Check if local PDF parser should be used
                    use_local_pdf_parser = os.getenv("USE_LOCAL_PDF_PARSER", "false").lower() != "false"
                    
                    if use_local_pdf_parser or os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE") is None:
                        from prepdocslib.pdfparser import LocalPdfParser
                        parser = LocalPdfParser()
                    else:
                        # Use Document Intelligence parser if available
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
                    print(f"Error reading PDF file {file_path}: {e}")
                    return ""
                    
            elif file_extension == '.html':
                # Handle HTML files
                try:
                    from prepdocslib.htmlparser import LocalHTMLParser
                    parser = LocalHTMLParser()
                    with open(file_path, 'rb') as f:
                        pages = []
                        async for page in parser.parse(f):
                            pages.append(page.text)
                        return '\n'.join(pages)
                except Exception as e:
                    print(f"Error reading HTML file {file_path}: {e}")
                    return ""
                    
            elif file_extension == '.csv':
                # Handle CSV files
                try:
                    from prepdocslib.csvparser import CsvParser
                    parser = CsvParser()
                    with open(file_path, 'rb') as f:
                        pages = []
                        async for page in parser.parse(f):
                            pages.append(page.text)
                        return '\n'.join(pages)
                except Exception as e:
                    print(f"Error reading CSV file {file_path}: {e}")
                    return ""
                    
            elif file_extension == '.json':
                # Handle JSON files
                try:
                    from prepdocslib.jsonparser import JsonParser
                    parser = JsonParser()
                    with open(file_path, 'rb') as f:
                        pages = []
                        async for page in parser.parse(f):
                            pages.append(page.text)
                        return '\n'.join(pages)
                except Exception as e:
                    print(f"Error reading JSON file {file_path}: {e}")
                    return ""
                    
            elif file_extension in ['.txt', '.md']:
                # Handle text and markdown files
                try:
                    from prepdocslib.textparser import TextParser
                    parser = TextParser()
                    with open(file_path, 'rb') as f:
                        pages = []
                        async for page in parser.parse(f):
                            pages.append(page.text)
                        return '\n'.join(pages)
                except Exception as e:
                    print(f"Error reading text file {file_path}: {e}")
                    return ""
                    
            else:
                # Default to text file reading with encoding handling
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    return ""
                    
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""
    
    async def extract_topics(self, content: str) -> List[str]:
        """Extract topics from content using LLM"""
        # Skip if content is empty
        if not content or len(content.strip()) < 50:
            return []
        
        # Increased content length for models with larger context windows
        max_content_length = 90000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        try:
            # Get the chat model deployment
            model_deployment = os.environ.get("AZURE_OPENAI_GPT4_DEPLOYMENT", 
                                            os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT"))
            
            if not model_deployment:
                print("No chat model deployment found, using fallback extraction")
                return self._fallback_topic_extraction(content)
            
            # Get LLM client
            client = self._get_llm_client()
            if not client:
                print("Failed to create LLM client, using fallback extraction")
                return self._fallback_topic_extraction(content)
            
            prompt = f"""Analyze the following technical document content and extract the main topics, technologies, and themes.
Focus on specific technical concepts, tools, platforms, and processes mentioned.
Return 10-15 specific topics as a JSON array of strings.
Be specific - instead of generic terms like "monitoring", use specific terms like "Azure Monitor" or "performance telemetry".

Document content:
{content}

Example output format: ["Azure Kubernetes Service", "container orchestration", "microservices architecture", "CI/CD pipelines", "load balancing"]
"""
            
            # Add retry logic for connection issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await client.chat.completions.create(
                        model=model_deployment,
                        messages=[
                            {"role": "system", "content": "You are a technical documentation analyst. Extract specific, concrete topics from technical documents."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=500,
                        timeout=30  # Add timeout
                    )
                    break
                except Exception as e:
                    error_message = str(e)
                    if attempt < max_retries - 1:
                        print(f"Retry {attempt + 1}/{max_retries} after error: {error_message}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
            
            # Parse the response
            topics_text = response.choices[0].message.content.strip()
            try:
                import json
                topics = json.loads(topics_text)
                if isinstance(topics, list):
                    return [t for t in topics if t and isinstance(t, str)][:15]
            except:
                # Fallback: extract from response text
                import re
                topics = re.findall(r'"([^"]+)"', topics_text)
                if not topics:
                    topics = [t.strip() for t in topics_text.split('\n') if t.strip() and not t.strip().startswith('[')]
                return [t for t in topics if t][:15]
                
        except Exception as e:
            print(f"Error extracting topics with LLM: {e}")
            return self._fallback_topic_extraction(content)
    
    def _fallback_topic_extraction(self, content: str) -> List[str]:
        """Fallback topic extraction with domain-specific keywords"""
        topics = []
        
        # Domain-specific keyword patterns
        cosmic_keywords = [
            "cosmic", "watson", "performance monitoring", "diagnostics", "telemetry",
            "container platform", "microservices", "kubernetes", "docker", "orchestration"
        ]
        substrate_keywords = [
            "substrate", "infrastructure", "cloud platform", "azure", "deployment",
            "virtual machines", "networking", "storage", "security", "compliance"
        ]
        
        content_lower = content.lower()
        
        # Check for domain-specific keywords
        for keyword in cosmic_keywords + substrate_keywords:
            if keyword in content_lower:
                topics.append(keyword.title())
        
        # Extract capitalized multi-word phrases (likely product/feature names)
        import re
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', content)
        topics.extend(list(set(capitalized_phrases))[:5])
        
        return list(set(topics))[:10]
    
    async def generate_sample_questions(self, contents: List[str]) -> List[str]:
        """Generate sample questions using LLM based on actual document content"""
        if not contents:
            return ["What are the key features?", "How do I configure this?", "What are common issues?"]
            
        # Combine and truncate contents
        combined_content = "\n\n---\n\n".join(contents[:5])
        max_content_length = 90000
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "..."
        
        try:
            # Get the chat model deployment
            model_deployment = os.environ.get("AZURE_OPENAI_GPT4_DEPLOYMENT", 
                                            os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT"))
            
            if not model_deployment:
                return self._generate_fallback_questions(contents)
            
            # Get LLM client
            client = self._get_llm_client()
            
            prompt = f"""Based on the following technical documentation content, generate 7-10 realistic questions that users would ask.
The questions should be specific to the actual content, mentioning specific features, tools, or processes described in the documents.
Include a mix of how-to questions, troubleshooting questions, and conceptual questions.
Return only the questions as a JSON array of strings.

Document content:
{combined_content}

Example output format: ["How do I configure Watson monitoring for my Cosmic deployment?", "What are the performance tuning options for Substrate?", "How can I troubleshoot connection issues in the platform?"]
"""
            
            response = await client.chat.completions.create(
                model=model_deployment,
                messages=[
                    {"role": "system", "content": "You are a technical support expert. Generate realistic questions users would ask about the documented technology."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600,
                timeout=30
            )
            
            # Parse the response
            questions_text = response.choices[0].message.content.strip()
            try:
                import json
                questions = json.loads(questions_text)
                if isinstance(questions, list):
                    return [q for q in questions if q and isinstance(q, str) and '?' in q][:10]
            except:
                # Fallback: extract questions from response
                import re
                questions = re.findall(r'"([^"]+\?)"', questions_text)
                if not questions:
                    questions = [line.strip() for line in questions_text.split('\n') if '?' in line]
                return [q.strip('"\'') for q in questions if q][:10]
                
        except Exception as e:
            print(f"Error generating questions with LLM: {e}")
            return self._generate_fallback_questions(contents)
    
    def _generate_fallback_questions(self, contents: List[str]) -> List[str]:
        """Generate context-aware fallback questions"""
        # Extract key terms from content
        combined = " ".join(contents[:2])[:1000].lower() if contents else ""
        
        questions = []
        
        # Check for specific terms and generate relevant questions
        if "cosmic" in combined:
            questions.extend([
                "How do I set up Cosmic monitoring for my application?",
                "What are the performance metrics available in Cosmic?",
                "How can I troubleshoot Cosmic deployment issues?"
            ])
        
        if "substrate" in combined:
            questions.extend([
                "How do I configure Substrate infrastructure?",
                "What are the security best practices for Substrate?",
                "How can I scale my Substrate deployment?"
            ])
        
        # Add generic but relevant questions
        if "error" in combined or "troubleshoot" in combined:
            questions.append("How do I diagnose and fix common errors?")
        
        if "performance" in combined:
            questions.append("What are the performance optimization techniques?")
        
        if "config" in combined or "setup" in combined:
            questions.append("What are the initial configuration steps?")
        
        # Ensure we always return some questions
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
            
        # Combine and truncate contents
        combined_content = "\n\n".join(contents[:8])
        max_content_length = 90000
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "..."
        
        try:
            # Get the chat model deployment
            model_deployment = os.environ.get("AZURE_OPENAI_GPT4_DEPLOYMENT", 
                                            os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT"))
            
            if not model_deployment:
                return self._enhanced_keyword_extraction(contents)
                
            # Get LLM client
            client = self._get_llm_client()
            
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
            
            response = await client.chat.completions.create(
                model=model_deployment,
                messages=[
                    {"role": "system", "content": "You are a technical keyword extraction expert. Extract specific, meaningful keywords from technical documentation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=30
            )
            
            # Parse the response
            keywords_text = response.choices[0].message.content.strip()
            try:
                import json
                keywords = json.loads(keywords_text)
                if isinstance(keywords, list):
                    keywords = list(set([k for k in keywords if k and isinstance(k, str)]))
                    return keywords[:30]
            except:
                # Fallback: extract from response text
                import re
                keywords = re.findall(r'"([^"]+)"', keywords_text)
                if not keywords:
                    keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
                return list(set([k.strip('"\'') for k in keywords if k]))[:30]
                
        except Exception as e:
            print(f"Error extracting keywords with LLM: {e}")
            return self._enhanced_keyword_extraction(contents)
    
    def _enhanced_keyword_extraction(self, contents: List[str]) -> List[str]:
        """Enhanced fallback keyword extraction"""
        import re
        from collections import Counter
        
        keywords = set()
        
        for content in contents[:3]:
            # Extract capitalized words and phrases
            capitalized = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', content)
            keywords.update(capitalized)
            
            # Extract words in quotes
            quoted = re.findall(r'"([^"]+)"', content)
            keywords.update([q for q in quoted if len(q.split()) <= 3])
            
            # Extract technical terms (words with numbers, hyphens, or specific patterns)
            technical = re.findall(r'\b\w+[-]\w+\b|\b\w+\d+\w*\b', content)
            keywords.update(technical)
        
        # Filter and clean keywords
        cleaned_keywords = []
        for kw in keywords:
            kw = kw.strip()
            # Keep only meaningful keywords
            if len(kw) > 3 and len(kw.split()) <= 3 and not kw.lower() in self._get_stopwords():
                cleaned_keywords.append(kw)
        
        # Sort by length and alphabetically to get most specific terms first
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
        print("DomainClassifierSetup cleanup started")
        
        # Close the LLM client first
        if hasattr(self, '_llm_client') and self._llm_client:
            try:
                print("Closing LLM client...")
                await self._llm_client.close()
                print("LLM client closed successfully")
            except Exception as e:
                print(f"Error closing LLM client: {e}")
            finally:
                self._llm_client = None
        
        # Close the credential if it exists
        if hasattr(self, '_credential') and self._credential:
            try:
                print("Closing Azure credential...")
                await self._credential.close()
                print("Azure credential closed successfully")
            except Exception as e:
                print(f"Error closing credential: {e}")
            finally:
                self._credential = None
                
        print("DomainClassifierSetup cleanup completed")