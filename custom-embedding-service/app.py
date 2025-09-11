from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from typing import List
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PatentsBERTa Embedding Service", version="1.0.0")

# API Key authentication
API_KEY = os.getenv("PATENTSBERTA_API_KEY")

def api_key_auth(x_api_key: str | None = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

class EmbeddingRequest(BaseModel):
    texts: List[str]
    normalize: bool = True

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimensions: int

# Global model variables
tokenizer = None
model = None

@app.on_event("startup")
async def load_model():
    global tokenizer, model
    try:
        logger.info("Loading PatentsBERTa model...")
        tokenizer = AutoTokenizer.from_pretrained("AI-Growth-Lab/PatentSBERTa")
        model = AutoModel.from_pretrained("AI-Growth-Lab/PatentSBERTa")
        
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
            max_length=512,
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
            model="AI-Growth-Lab/PatentSBERTa",
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
        "model_name": "AI-Growth-Lab/PatentSBERTa",
        "description": "Patent-specific BERT model for technical document embeddings",
        "max_input_length": 512,
        "embedding_dimensions": 768,
        "gpu_enabled": torch.cuda.is_available()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
