"""
Embedding Model Router for selecting appropriate embedding models based on content characteristics.

This router helps choose between:
- Baseline (Azure OpenAI) for general content
- PatentSBERTa for technical/patent-heavy content
- NOMIC for alternative embeddings

Heuristics include:
- Technical keyword detection (patents, engineering, scientific terms)
- Code presence analysis
- Image density analysis (from metadata)
- Patent-specific indicators
- Metadata-based routing hints
"""

import re
from typing import Dict, Any, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EmbeddingModel(str, Enum):
    """Available embedding models."""
    BASELINE = "baseline"  # Azure OpenAI
    PATENTSBERTA = "patentsberta"  # Domain-specific
    NOMIC = "nomic"  # Alternative provider


class EmbeddingRouter:
    """
    Router for selecting embedding models based on content analysis.
    
    Uses heuristics to determine if content is technical/patent-heavy and would benefit
    from PatentSBERTa embeddings, which are specialized for technical and patent content.
    """
    
    # Technical keywords that indicate patent/technical content
    PATENT_KEYWORDS: Set[str] = {
        "patent", "patents", "patented", "patentee", "patentability",
        "invention", "inventor", "inventive", "prior art", "novelty",
        "claim", "claims", "embodiment", "embodiments", "specification",
        "application", "filing", "disclosure", "provisional", "non-provisional",
        "uspto", "european patent", "pct", "international application"
    }
    
    # Engineering and technical terms
    TECHNICAL_KEYWORDS: Set[str] = {
        "algorithm", "circuit", "circuitry", "component", "assembly",
        "mechanism", "apparatus", "device", "system", "method",
        "process", "technique", "implementation", "configuration",
        "module", "interface", "protocol", "architecture", "framework",
        "semiconductor", "microprocessor", "controller", "processor",
        "sensor", "actuator", "transducer", "transmitter", "receiver",
        "synthesis", "analysis", "optimization", "calibration", "validation"
    }
    
    # Scientific and research terms
    SCIENTIFIC_KEYWORDS: Set[str] = {
        "hypothesis", "experiment", "experimental", "empirical",
        "theoretical", "methodology", "research", "study", "analysis",
        "synthesis", "compound", "molecule", "reaction", "catalyst",
        "polymer", "crystal", "lattice", "quantum", "nanotechnology"
    }
    
    # Code-related patterns
    CODE_PATTERNS: Set[str] = {
        "def ", "function", "class ", "import ", "from ", "return ",
        "if __name__", "public ", "private ", "static ", "void ", "int ",
        "const ", "let ", "var ", "async ", "await ", "=>", "->",
        "namespace", "using ", "#include", "package ", "interface ",
        "extends", "implements", "try", "catch", "finally", "throw"
    }
    
    # Code file extensions
    CODE_FILE_EXTENSIONS: Set[str] = {
        ".py", ".js", ".java", ".go", ".php", ".rb", ".cpp", ".c",
        ".ts", ".tsx", ".jsx", ".sql", ".sh", ".yaml", ".yml", ".json",
        ".md", ".xml", ".html", ".css", ".scss", ".less", ".vue", ".svelte"
    }
    
    def __init__(
        self, 
        baseline_deployment: str, 
        patentsberta_endpoint: Optional[str] = None,
        nomic_endpoint: Optional[str] = None,
        nomic_api_key: Optional[str] = None,
        enable_heuristics: bool = True
    ):
        """
        Initialize embedding router.
        
        Args:
            baseline_deployment: Azure OpenAI embedding deployment name
            patentsberta_endpoint: Optional PatentSBERTa service endpoint
            nomic_endpoint: Optional NOMIC service endpoint (for code/multimodal)
            nomic_api_key: Optional NOMIC API key
            enable_heuristics: Enable intelligent routing (default: True)
        """
        self.baseline_deployment = baseline_deployment
        self.patentsberta_endpoint = patentsberta_endpoint
        self.nomic_endpoint = nomic_endpoint
        self.nomic_api_key = nomic_api_key
        self.enable_heuristics = enable_heuristics
        
        # Pre-compile regex patterns for performance
        self._patent_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.PATENT_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self._technical_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.TECHNICAL_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self._scientific_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.SCIENTIFIC_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        # Code pattern detection (multiple patterns)
        self._code_patterns = [re.compile(re.escape(pattern), re.IGNORECASE) for pattern in self.CODE_PATTERNS]
    
    def _analyze_content(self, content: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze content for technical/patent/code indicators.
        
        Args:
            content: Document content to analyze
            content_type: Optional content type hint (file extension, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        if not content or len(content.strip()) == 0:
            return {
                "patent_score": 0.0,
                "technical_score": 0.0,
                "scientific_score": 0.0,
                "code_score": 0.0,
                "total_score": 0.0,
                "is_code_file": False
            }
        
        content_lower = content.lower()
        content_length = len(content)
        word_count = len(content.split())
        
        # Check if file extension indicates code
        is_code_file = False
        if content_type:
            content_type_lower = content_type.lower().strip()
            if content_type_lower.startswith('.'):
                is_code_file = content_type_lower in self.CODE_FILE_EXTENSIONS
            elif any(content_type_lower.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS):
                is_code_file = True
        
        # Count keyword matches
        patent_matches = len(self._patent_pattern.findall(content_lower))
        technical_matches = len(self._technical_pattern.findall(content_lower))
        scientific_matches = len(self._scientific_pattern.findall(content_lower))
        
        # Detect code presence (more sophisticated detection)
        code_matches = sum(1 for pattern in self._code_patterns if pattern.search(content))
        
        # Additional code indicators: brackets, semicolons, etc.
        code_indicators = sum([
            content.count('{'),
            content.count('}'),
            content.count(';'),
            content.count('()'),
            content.count('=>'),
            content.count('->'),
        ])
        
        # Code score combines pattern matches and structural indicators
        code_match_score = (code_matches / max(word_count, 1)) * 100 if word_count > 0 else 0.0
        code_structure_score = min((code_indicators / max(content_length, 1)) * 1000, 50.0)  # Cap at 50
        code_score = code_match_score * 2.0 + code_structure_score * 0.5
        
        # Boost code score if file extension indicates code
        if is_code_file:
            code_score = max(code_score, 25.0)  # Minimum score for code files
        
        # Calculate scores (normalized by word count to avoid bias toward long documents)
        patent_score = (patent_matches / max(word_count, 1)) * 100 if word_count > 0 else 0.0
        technical_score = (technical_matches / max(word_count, 1)) * 100 if word_count > 0 else 0.0
        scientific_score = (scientific_matches / max(word_count, 1)) * 100 if word_count > 0 else 0.0
        
        # Weighted total score
        # Patent keywords are strongest indicator, then technical, then scientific, then code
        total_score = (
            patent_score * 3.0 +  # Patent keywords are most important
            technical_score * 2.0 +
            scientific_score * 1.5 +
            code_score * 1.0
        )
        
        return {
            "patent_score": patent_score,
            "technical_score": technical_score,
            "scientific_score": scientific_score,
            "code_score": code_score,
            "total_score": total_score,
            "patent_matches": patent_matches,
            "technical_matches": technical_matches,
            "scientific_matches": scientific_matches,
            "code_matches": code_matches,
            "code_indicators": code_indicators,
            "is_code_file": is_code_file,
            "word_count": word_count
        }
    
    def _analyze_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract routing hints from metadata.
        
        Args:
            metadata: Optional metadata dictionary
            
        Returns:
            Dictionary with metadata analysis
        """
        if not metadata:
            return {
                "has_routing_hint": False,
                "image_density": 0.0,
                "suggested_model": None
            }
        
        # Check for explicit routing hint
        routing_hint = metadata.get("embedding_model") or metadata.get("preferred_embedding")
        suggested_model = None
        if routing_hint:
            try:
                suggested_model = EmbeddingModel(routing_hint.lower())
            except ValueError:
                logger.warning(f"Invalid routing hint in metadata: {routing_hint}")
        
        # Analyze image density
        image_count = metadata.get("image_count", 0)
        page_count = metadata.get("page_count", 1)
        image_density = (image_count / max(page_count, 1)) * 100 if page_count > 0 else 0.0
        
        # Check for technical indicators in metadata
        category = metadata.get("category", "").lower()
        file_type = metadata.get("file_type", "").lower()
        source_file = metadata.get("sourcefile", "").lower()
        
        # File name or category hints
        is_technical_file = any(
            keyword in category or keyword in source_file
            for keyword in ["patent", "technical", "engineering", "research", "scientific"]
        )
        
        return {
            "has_routing_hint": routing_hint is not None,
            "routing_hint": routing_hint,
            "suggested_model": suggested_model,
            "image_density": image_density,
            "image_count": image_count,
            "page_count": page_count,
            "is_technical_file": is_technical_file,
            "category": category,
            "file_type": file_type
        }
    
    def select_model(
        self,
        content: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EmbeddingModel:
        """
        Select appropriate embedding model based on content characteristics.
        
        Routing logic:
        1. If metadata has explicit routing hint, use it
        2. If PatentSBERTa endpoint not configured, use baseline
        3. Analyze content for technical/patent indicators
        4. Route to PatentSBERTa if score exceeds threshold
        5. Otherwise use baseline
        
        Args:
            content: Document content to analyze
            content_type: Optional content type hint (pdf, txt, etc.)
            metadata: Optional metadata (image_count, code_density, etc.)
            
        Returns:
            Selected embedding model
        """
        # If heuristics disabled, always use baseline
        if not self.enable_heuristics:
            return EmbeddingModel.BASELINE
        
        # If PatentSBERTa endpoint not configured, must use baseline
        if not self.patentsberta_endpoint:
            logger.debug("PatentSBERTa endpoint not configured, using baseline")
            return EmbeddingModel.BASELINE
        
        # Analyze metadata first (explicit hints take priority)
        metadata_analysis = self._analyze_metadata(metadata)
        
        # Check for explicit routing hint in metadata
        if metadata_analysis["has_routing_hint"] and metadata_analysis["suggested_model"]:
            suggested = metadata_analysis["suggested_model"]
            logger.info(f"Using metadata routing hint: {suggested}")
            return suggested
        
        # Analyze content
        content_analysis = self._analyze_content(content, content_type)
        
        # Routing thresholds
        PATENT_THRESHOLD = 5.0  # Score threshold for routing to PatentSBERTa
        STRONG_PATENT_THRESHOLD = 10.0  # Strong indicator threshold
        CODE_THRESHOLD = 15.0  # Score threshold for routing to NOMIC Code
        MULTIMODAL_THRESHOLD = 15.0  # Image density threshold for NOMIC Vision
        
        # Decision logic
        total_score = content_analysis["total_score"]
        patent_score = content_analysis["patent_score"]
        code_score = content_analysis["code_score"]
        is_code_file = content_analysis.get("is_code_file", False)
        
        # Check for code-heavy content → NOMIC Embed Code
        if (self.nomic_endpoint or self.nomic_api_key) and (code_score >= CODE_THRESHOLD or is_code_file):
            logger.info(
                f"Routing to NOMIC Code: code_score={code_score:.2f}, "
                f"is_code_file={is_code_file}"
            )
            return EmbeddingModel.NOMIC
        
        # Check for high image density → NOMIC Vision (if enabled)
        if (self.nomic_endpoint or self.nomic_api_key) and metadata_analysis["image_density"] >= MULTIMODAL_THRESHOLD:
            logger.info(
                f"Routing to NOMIC Vision: image_density={metadata_analysis['image_density']:.2f}"
            )
            return EmbeddingModel.NOMIC
        
        # Strong patent indicators → PatentSBERTa
        if patent_score >= 2.0 or total_score >= STRONG_PATENT_THRESHOLD:
            logger.info(
                f"Routing to PatentSBERTa: patent_score={patent_score:.2f}, "
                f"total_score={total_score:.2f}"
            )
            return EmbeddingModel.PATENTSBERTA
        
        # Moderate technical indicators → PatentSBERTa
        if total_score >= PATENT_THRESHOLD:
            # Also check if metadata suggests technical content
            if metadata_analysis["is_technical_file"]:
                logger.info(
                    f"Routing to PatentSBERTa: total_score={total_score:.2f}, "
                    f"technical_file=True"
                )
                return EmbeddingModel.PATENTSBERTA
        
        # High image density with technical content might benefit from PatentSBERTa
        if metadata_analysis["image_density"] > 10.0 and total_score >= 3.0:
            logger.info(
                f"Routing to PatentSBERTa: image_density={metadata_analysis['image_density']:.2f}, "
                f"total_score={total_score:.2f}"
            )
            return EmbeddingModel.PATENTSBERTA
        
        # Default to baseline
        logger.debug(
            f"Routing to baseline: total_score={total_score:.2f}, "
            f"patent_score={patent_score:.2f}, code_score={code_score:.2f}"
        )
        return EmbeddingModel.BASELINE
    
    def get_deployment_name(self, model: EmbeddingModel) -> str:
        """Get deployment name for selected model."""
        if model == EmbeddingModel.BASELINE:
            return self.baseline_deployment
        elif model == EmbeddingModel.PATENTSBERTA:
            if self.patentsberta_endpoint:
                return self.patentsberta_endpoint
            else:
                logger.warning("PatentSBERTa selected but endpoint not configured, falling back to baseline")
                return self.baseline_deployment
        elif model == EmbeddingModel.NOMIC:
            if self.nomic_endpoint:
                return self.nomic_endpoint
            elif self.nomic_api_key:
                # Using API key, return model identifier
                return "nomic-embed-code-v1"  # Default to code model for now
            else:
                logger.warning("NOMIC selected but endpoint/API key not configured, falling back to baseline")
                return self.baseline_deployment
        else:
            return self.baseline_deployment  # Fallback to baseline
    
    def get_nomic_model_type(self, content_analysis: Dict[str, Any], metadata_analysis: Dict[str, Any]) -> str:
        """Determine which NOMIC model to use based on content analysis."""
        code_score = content_analysis.get("code_score", 0.0)
        is_code_file = content_analysis.get("is_code_file", False)
        image_density = metadata_analysis.get("image_density", 0.0)
        
        # Prioritize code detection
        if code_score >= 15.0 or is_code_file:
            return "nomic-embed-code-v1"
        
        # Then multimodal
        if image_density >= 15.0:
            return "nomic-embed-vision-v1.5"
        
        # Default to text
        return "nomic-embed-text-v1.5"
    
    def get_routing_decision_info(
        self,
        content: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed routing decision information for debugging/monitoring.
        
        Args:
            content: Document content to analyze
            content_type: Optional content type hint
            metadata: Optional metadata
            
        Returns:
            Dictionary with routing decision details
        """
        selected_model = self.select_model(content, content_type, metadata)
        content_analysis = self._analyze_content(content, content_type)
        metadata_analysis = self._analyze_metadata(metadata)
        
        routing_info = {
            "selected_model": selected_model.value,
            "deployment_name": self.get_deployment_name(selected_model),
            "content_analysis": content_analysis,
            "metadata_analysis": metadata_analysis,
            "heuristics_enabled": self.enable_heuristics,
            "patentsberta_configured": self.patentsberta_endpoint is not None,
            "nomic_configured": self.nomic_endpoint is not None or self.nomic_api_key is not None
        }
        
        # Add NOMIC model type if NOMIC is selected
        if selected_model == EmbeddingModel.NOMIC:
            routing_info["nomic_model_type"] = self.get_nomic_model_type(content_analysis, metadata_analysis)
        
        return routing_info

