
MODELS_2_LIMITS = {
  "gpt-35-turbo" : 4000,
  "gpt-35-turbo" : 4000,
  "gpt-35-turbo-16k" : 16000,
  "gpt-3.5-turbo-16k" : 16000,
  "gpt-4" : 8100,
  "gpt-4-32k" : 32000
}

def get_token_limit(modelid: str) -> int:
  if modelid not in MODELS_2_LIMITS:
    raise ValueError("Expected Model Gpt-35-turbo and above")
  return MODELS_2_LIMITS.get(modelid)