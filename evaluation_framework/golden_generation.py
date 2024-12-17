"""
Synthetic data generator using Azure OpenAI for embeddings and text generation.
"""
# syntheiser class instance requires a n OPENAI_API_KEY to be set in the environment variables
import os
os.environ["OPENAI_API_KEY"] = "default key"

from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, Dict

from quart import Quart
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import (
    ContextConstructionConfig,
    FiltrationConfig,
)

from models import ConfigLoader, ModelFactory
from eval_config import EvalConfig

SaveFormat = Literal['json', 'csv']
load_dotenv()

@dataclass
class SynthesizerConfig:
    """Configuration for synthetic data generation."""
    max_contexts: int
    chunk_size: int
    chunk_overlap: int
    save_format: SaveFormat
    save_path: Path
    synt_quality: float
    max_quality_retries: int
    context_quality_threshold: float
    context_similarity_threshold: float
    max_construction_retries: int

    @classmethod
    def from_eval_config(cls, eval_config: EvalConfig) -> 'SynthesizerConfig':
        """Create SynthesizerConfig from EvalConfig"""
        config = eval_config.synthesizer_config
        max_items = eval_config.synthetic_data["goldens_per_context"]
        return cls(
            max_contexts=max_items,
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            save_format=config["save_format"],
            save_path=eval_config.paths["synthetic_data"],
            synt_quality=config["synt_quality"],
            max_quality_retries=config["max_quality_retries"],
            context_quality_threshold=config["context_quality_threshold"],
            context_similarity_threshold=config["context_similarity_threshold"],
            max_construction_retries=config["max_construction_retries"]
        )

class SyntheticDataGenerator:
    """Main class for generating synthetic training data."""
    
    def __init__(self,
                 config: SynthesizerConfig,
                 app_config: Optional[Quart] = None):
        self.config = config
        if app_config:
            self.llm_model, self.embedder = ModelFactory.from_app_config(app_config)
        else:
            llm_config = ConfigLoader.load_llm_config()
            embedding_config = ConfigLoader.load_embed_config()
            
            # Initialize models
            self.embedder = ModelFactory.create_embedder(embedding_config)
            self.llm_model = ModelFactory.create_llm_model(llm_config)
        
        # Initialize synthesizer
        self.synthesizer = Synthesizer(
            model=self.llm_model,
            filtration_config=FiltrationConfig(critic_model=self.llm_model,
                                               synthetic_input_quality_threshold=self.config.synt_quality,
                                               max_quality_retries=self.config.max_quality_retries)
        )   
    
    def generate(self,
                 data: List[str],
                 gen_from_docs: bool) -> None:
        """Generate synthetic data from provided documents."""
        context_config = ContextConstructionConfig(
            max_contexts_per_document=self.config.max_contexts,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            embedder=self.embedder,
            critic_model=self.llm_model,
            context_quality_threshold=self.config.context_quality_threshold,
            context_similarity_threshold=self.config.context_similarity_threshold,
            max_retries=self.config.max_construction_retries
        )

        if gen_from_docs:
            # Convert relative paths to absolute
            abs_paths = [str(Path(doc_path).resolve()) for doc_path in data]
            goldens = self.synthesizer.generate_goldens_from_docs(
                document_paths=abs_paths,
                context_construction_config=context_config
            )
        else:
            goldens = self.synthesizer.generate_goldens_from_contexts(
                contexts=data,
                max_goldens_per_context=context_config.max_contexts_per_document
            )
        
        self.save_results()
        return goldens
    
    
    def save_results(self) -> None:
        """Save generated synthetic data."""
        if not isinstance(self.config.save_format, str) or \
           self.config.save_format not in ('json', 'csv'):
            raise ValueError(
                f"save_format must be either 'json' or 'csv', "
                f"got {self.config.save_format}"
            )
        
        self.config.save_path.mkdir(parents=True, exist_ok=True)

        self.synthesizer.save_as(
            file_type=self.config.save_format,
            directory=self.config.save_path
        )

async def synthetaze_data(
    documents: List[str],
    eval_config: EvalConfig,
    app_config: Optional[Quart] = None,
    gen_from_docs: bool = True
) -> List[Dict]:
    """
    Generate synthetic data from provided documents or contexts.
    
    Args:
        documents: List of document paths or already created contexts
        eval_config: Evaluation configuration containing synthesizer settings
        app_config: Optional Quart app configuration
        gen_from_docs: Whether to generate data from documents or contexts
    """
    custom_config = SynthesizerConfig.from_eval_config(eval_config)
    generator = SyntheticDataGenerator(custom_config, app_config)
    goldens = generator.generate(documents, gen_from_docs=gen_from_docs)
    return [g.model_dump() for g in goldens]
