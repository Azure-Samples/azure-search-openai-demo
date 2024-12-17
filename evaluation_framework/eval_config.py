from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel, Field

class EvalConfig(BaseModel):
    """Evaluation configuration"""
    max_concurrent: int = Field(default=1, description="Maximum concurrent evaluations")
    throttle_value: int = Field(default=30, description="API throttling value")
    # Paths
    paths: Dict[str, Path] = Field(
        default={
            "test_cases": Path("eval_data/test_cases.json"),
            "eval_results": Path("eval_data/results.json"),
            "custom_metrics": Path("eval_data/custom_metrics.json"),
            "synthetic_data": Path("synthetic_data"),
            "synthetic_data_answered": Path("synthetic_data/synthetic_data_answered.json"),
            # Added test paths
            "test_config": Path("eval_config.json"),
            "test_cases_dummy": Path("eval_data/test_cases.json"),
            "test_cases_rag": Path("eval_data/test_cases.json")
        }
    )
    doc_retrieval_chunk_config: Dict[str, Any] = Field(
        default={
            "top_k": 1,
            "chunk_size": 150,
            "chunk_overlap": 50,
            "max_contexts": 1
        }
    )
    eval_pipeline: Dict[str, Any] = Field(
        default={
            "generate_synthetic_data": True,
            "use_test_cases": True
        }
    )
    synthetic_data: Dict[str, Any] = Field(
        default={
            "goldens_per_context": 1,
            "num_retrieved_contexts": 5,
        }
    )
    # Added synthesizer configuration
    synthesizer_config: Dict[str, Any] = Field(
        default={
            "chunk_size": 300,
            "chunk_overlap": 50,
            "save_format": "json",
            "synt_quality": 0.5,
            "max_quality_retries": 3,
            "context_quality_threshold": 0.5,
            "context_similarity_threshold": 0.5,
            "max_construction_retries": 3
        }
    )

    deepeval_config: Dict[str, Any] = Field(
        default={
            "write_cache": False,   
            "DEEPEVAL_TELEMETRY_OPT_OUT": "YES"
        }
    )
    
    @classmethod
    def from_file(cls, config_path: Path) -> "EvalConfig":
        """Load config from file"""
        if not config_path or not config_path.exists():
            return cls()
        return cls.model_validate_json(config_path.read_text())