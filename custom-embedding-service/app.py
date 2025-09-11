from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import torch
from transformers import AutoTokenizer, AutoModel
import logging
import numpy as np

from constants import (
    API_KEY,
    MAX_BATCH_SIZE,
    MAX_TEXT_LENGTH,
    MIN_TEXT_LENGTH,
    MAX_TOTAL_CHARS,
    MODEL_NAME,
    MODEL_MAX_LENGTH,
    EMBEDDING_DIMENSIONS,
    MODEL_DESCRIPTION
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def api_key_auth(x_api_key: str | None = Header(default=None)):
    """API key authentication dependency"""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

app = FastAPI(
    title="PatentsBERTa Embedding Service",
    description="Patent-specific BERT embeddings for technical documents",
    version="1.0.0"
)

class EmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=MAX_BATCH_SIZE)
    normalize: bool = True
    
    @field_validator('texts')
    @classmethod
    def validate_texts(cls, v):
        if not v:
            raise ValueError("texts cannot be empty")
        
        total_chars = 0
        for i, text in enumerate(v):
            if not isinstance(text, str):
                raise ValueError(f"Text at index {i} must be a string")
            
            text_len = len(text.strip())
            if text_len < MIN_TEXT_LENGTH:
                raise ValueError(f"Text at index {i} is too short (minimum {MIN_TEXT_LENGTH} characters)")
            
            if text_len > MAX_TEXT_LENGTH:
                raise ValueError(f"Text at index {i} is too long (maximum {MAX_TEXT_LENGTH} characters)")
            
            total_chars += text_len
        
        if total_chars > MAX_TOTAL_CHARS:
            raise ValueError(f"Total request size too large ({total_chars} chars, maximum {MAX_TOTAL_CHARS})")
        
        return v

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str = MODEL_NAME
    dimensions: int = EMBEDDING_DIMENSIONS

# Global model variables
tokenizer = None
model = None

@app.on_event("startup")
async def load_model():
    global tokenizer, model
    try:
        logger.info("Loading PatentsBERTa model...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModel.from_pretrained(MODEL_NAME)
        
        # Set to evaluation mode
        model.eval()
        
        # Move to GPU if available
        if torch.cuda.is_available():
            model = model.cuda()
            logger.info("Model loaded on GPU")
        else:
            logger.info("Model loaded on CPU")
            
        logger.info("PatentsBERTa model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise e

def mean_pooling(model_output, attention_mask):
    """Mean pooling to get sentence embeddings"""
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

@app.post("/embeddings", response_model=EmbeddingResponse, dependencies=[Depends(api_key_auth)])
async def create_embeddings(request: EmbeddingRequest):
    try:
        if not tokenizer or not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Tokenize inputs
        encoded_input = tokenizer(
            request.texts, 
            padding=True, 
            truncation=True, 
            max_length=MODEL_MAX_LENGTH,
            return_tensors='pt'
        )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            encoded_input = {k: v.cuda() for k, v in encoded_input.items()}
        
        # Generate embeddings
        with torch.no_grad():
            model_output = model(**encoded_input)
            embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
            
            # Normalize embeddings if requested
            if request.normalize:
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            # Convert to list
            embeddings_list = embeddings.cpu().numpy().tolist()
        
        return EmbeddingResponse(
            embeddings=embeddings_list,
            model=MODEL_NAME,
            dimensions=len(embeddings_list[0]) if embeddings_list else 0
        )
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": tokenizer is not None and model is not None,
        "gpu_available": torch.cuda.is_available()
    }

@app.get("/info")
async def model_info():
    return {
        "model_name": MODEL_NAME,
        "description": MODEL_DESCRIPTION,
        "max_input_length": MODEL_MAX_LENGTH,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "gpu_enabled": torch.cuda.is_available(),
        "limits": {
            "max_batch_size": MAX_BATCH_SIZE,
            "max_text_length": MAX_TEXT_LENGTH,
            "min_text_length": MIN_TEXT_LENGTH,
            "max_total_chars": MAX_TOTAL_CHARS
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
