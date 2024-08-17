from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class ModelConfig:
    model_name: str
    display_name: str
    template_path: Path
    type: str  # ["openai", "hf"]
    identifier: Optional[str] = None


MODEL_CONFIGS: Dict[str, Union[ModelConfig, dict[str, ModelConfig]]] = {
    # OpenAI Configs
    "GPT 3.5 Turbo": {
        "openai": ModelConfig(
            model_name="gpt-3.5-turbo", display_name="GPT 3.5 Turbo", template_path=BASE_DIR / "openai", type="openai"
        ),
        "azure": ModelConfig(
            model_name="gpt-35-turbo", display_name="GPT 3.5 Turbo", template_path=BASE_DIR / "openai", type="openai"
        ),
    },
    # Hugging Face
    "Mistral AI 7B": ModelConfig(
        model_name="mistralai/Mistral-7B-Instruct-v0.3",
        display_name="Mistral AI 7B",
        template_path=BASE_DIR / "hf_mistralai",
        type="hf",
        identifier="mistralai/Mistral-7B-Instruct-v0.3",
    ),
    "Phi 3 Mini 4K": ModelConfig(
        model_name="microsoft/Phi-3-mini-4k-instruct",
        display_name="Phi 3 Mini 4K",
        template_path=BASE_DIR / "hf_phi3_mini_4k",
        type="hf",
        identifier="microsoft/Phi-3-mini-4k-instruct",
    ),
    "Llama 3 8B Instruct": ModelConfig(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        display_name="Llama 3 8B Instruct",
        template_path=BASE_DIR / "hf_llama",
        type="hf",
        identifier="meta-llama/Meta-Llama-3-8B-Instruct",
    ),
    "Llama 3 70B Instruct": ModelConfig(
        model_name="meta-llama/Meta-Llama-3-70B-Instruct",
        display_name="Llama 3 70B Instruct",
        template_path=BASE_DIR / "hf_llama",
        type="hf",
        identifier="meta-llama/Meta-Llama-3-70B-Instruct",
    ),
}


def get_supported_models(openai_deployment: dict) -> dict[str, ModelConfig]:
    """Get the supported Hugging Face and OpenAI models.

    This function returns a dictionary of the supported models, including the Hugging Face ones
    and the specified OpenAI deployment, in 2 steps:
    1. Retrieve the supported Hugging Face models.
    2. Retrieve the specified OpenAI model, by looking through the model configurations for the one
       that matches the specified deployment type and model name.

    The deployment type of the OpenAI model can be either "azure" or "openai", depending on whether
    the model is deployed on Azure or openai.com.

    Args:
        openai_deployment (dict): A dictionary containing the deployment type ("azure"/"openai"),
            model name, and deployment name.
    Returns:
        dict[str]: A dictionary of supported models.
    """
    supported_models = {}

    # Retrieve Hugging Face models
    for key, model in MODEL_CONFIGS.items():
        if isinstance(model, ModelConfig) and model.type == "hf":
            supported_models[key] = model

    # Retrieve specified OpenAI model
    deployment_type, model_name, deployment_name = (
        openai_deployment["type"],
        openai_deployment["model_name"],
        openai_deployment["deployment_name"],
    )
    for key, model_config in MODEL_CONFIGS.items():
        if isinstance(model_config, dict):
            openai_model = model_config.get(deployment_type)
            if openai_model and openai_model.model_name == model_name:
                openai_model.identifier = deployment_name if deployment_type == "azure" else model_name
                supported_models[key] = openai_model
                break

    return supported_models
