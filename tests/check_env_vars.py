"""
Check Environment Variables

Verifies which environment variables are set and which are missing.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "backend"))

def load_env_files():
    """Try to load environment variables from azd and local .env files."""
    loaded_files = []
    from dotenv import load_dotenv
    
    # Try azd environment first (as the app does)
    azd_env_path = None
    try:
        result = subprocess.run("azd env list -o json", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            env_json = json.loads(result.stdout)
            for entry in env_json:
                if entry.get("IsDefault"):
                    env_file_path = entry.get("DotEnvPath")
                    if env_file_path and os.path.exists(env_file_path):
                        azd_env_path = env_file_path
                        load_dotenv(env_file_path, override=True)
                        loaded_files.append(env_file_path)
                        break
    except Exception:
        pass
    
    # Also check app/backend/.env (for checking purposes, even though azd takes precedence)
    backend_env = Path(__file__).parent.parent / "app" / "backend" / ".env"
    if backend_env.exists():
        # Load without override to see what's in .env (azd vars already loaded)
        # But we need to check what's actually set, so load it
        if not azd_env_path:  # Only load if azd wasn't found
            load_dotenv(backend_env, override=True)
        else:
            # Load to see what's there, but azd takes precedence
            load_dotenv(backend_env, override=False)
        loaded_files.append(str(backend_env))
    
    return loaded_files if loaded_files else None

def check_env_vars():
    """Check all required and optional environment variables."""
    
    print("=" * 70)
    print("ENVIRONMENT VARIABLES STATUS CHECK")
    print("=" * 70)
    
    # Try to load environment files (azd first, then .env)
    loaded_files = load_env_files()
    if loaded_files:
        print(f"[INFO] Loaded environment from:")
        for f in loaded_files:
            print(f"  - {f}")
        print("[NOTE] The app loads env vars in this order: azd env -> app/backend/.env -> shell")
    else:
        print("[INFO] No environment files found - checking current shell environment only")
        print("[NOTE] The app loads env vars from azd or .env at runtime")
    print()
    
    # Required for core functionality
    required_core = {
        "AZURE_STORAGE_ACCOUNT": "Azure Storage Account name",
        "AZURE_STORAGE_CONTAINER": "Azure Storage Container name",
        "AZURE_SEARCH_SERVICE": "Azure AI Search service name",
        "AZURE_SEARCH_INDEX": "Azure AI Search index name",
        "AZURE_OPENAI_CHATGPT_MODEL": "OpenAI ChatGPT model name",
    }
    
    # Optional but important
    optional_important = {
        "AZURE_OPENAI_SERVICE": "Azure OpenAI service name",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "Azure OpenAI ChatGPT deployment",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "Azure OpenAI Embedding deployment",
        "AZURE_OPENAI_EMB_MODEL_NAME": "Embedding model name",
        "AZURE_OPENAI_EMB_DIMENSIONS": "Embedding dimensions",
        "AZURE_SEARCH_KEY": "Azure Search API key",
        "AZURE_OPENAI_API_KEY": "Azure OpenAI API key",
    }
    
    # Feature flags
    feature_flags = {
        "OCR_PROVIDER": "OCR provider (ollama, azure_document_intelligence, none)",
        "OCR_ON_INGEST": "Run OCR during ingestion (true/false)",
        "ENABLE_WEB_SEARCH": "Enable web search (true/false)",
        "SERPER_API_KEY": "Serper API key for web search",
        "REDIS_URL": "Redis cache URL",
        "ENABLE_NOMIC_EMBEDDINGS": "Enable NOMIC embeddings (true/false)",
        "NOMIC_API_KEY": "NOMIC API key",
    }
    
    # OCR specific
    ocr_vars = {
        "OLLAMA_BASE_URL": "Ollama base URL",
        "OLLAMA_OCR_MODEL": "Ollama OCR model name",
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "Azure Document Intelligence endpoint",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY": "Azure Document Intelligence key",
    }
    
    # Authentication
    auth_vars = {
        "AZURE_USE_AUTHENTICATION": "Enable authentication (true/false)",
        "AZURE_TENANT_ID": "Azure Tenant ID",
        "AZURE_SERVER_APP_ID": "Azure Server App ID",
        "AZURE_SERVER_APP_SECRET": "Azure Server App Secret",
        "AZURE_CLIENT_APP_ID": "Azure Client App ID",
    }
    
    def check_section(name, vars_dict, required=False):
        """Check a section of environment variables."""
        print(f"\n{name}:")
        print("-" * 70)
        set_count = 0
        missing = []
        
        for var, description in vars_dict.items():
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if "KEY" in var or "SECRET" in var or "PASSWORD" in var:
                    display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                else:
                    display_value = value
                print(f"  [SET]   {var:40} = {display_value}")
                set_count += 1
            else:
                status = "[REQUIRED - MISSING]" if required else "[OPTIONAL - NOT SET]"
                print(f"  {status} {var:40} - {description}")
                if required:
                    missing.append(var)
        
        return set_count, len(vars_dict), missing
    
    # Check all sections
    core_set, core_total, core_missing = check_section("CORE REQUIRED VARIABLES", required_core, required=True)
    opt_set, opt_total, _ = check_section("OPTIONAL IMPORTANT VARIABLES", optional_important)
    feat_set, feat_total, _ = check_section("FEATURE FLAGS", feature_flags)
    ocr_set, ocr_total, _ = check_section("OCR CONFIGURATION", ocr_vars)
    auth_set, auth_total, _ = check_section("AUTHENTICATION", auth_vars)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Core Required:     {core_set}/{core_total} set")
    print(f"Optional Important: {opt_set}/{opt_total} set")
    print(f"Feature Flags:     {feat_set}/{feat_total} set")
    print(f"OCR Config:        {ocr_set}/{ocr_total} set")
    print(f"Authentication:    {auth_set}/{auth_total} set")
    
    total_set = core_set + opt_set + feat_set + ocr_set + auth_set
    total_vars = core_total + opt_total + feat_total + ocr_total + auth_total
    
    print(f"\nOverall: {total_set}/{total_vars} variables set")
    
    if core_missing:
        print(f"\n[CRITICAL] Missing required variables: {', '.join(core_missing)}")
        print("The application will NOT work without these!")
        return False
    
    # Check feature status
    print("\n" + "=" * 70)
    print("FEATURE STATUS")
    print("=" * 70)
    
    ocr_provider = os.getenv("OCR_PROVIDER", "none").lower()
    web_search = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
    serper_key = os.getenv("SERPER_API_KEY")
    redis_url = os.getenv("REDIS_URL")
    nomic_enabled = os.getenv("ENABLE_NOMIC_EMBEDDINGS", "false").lower() == "true"
    nomic_key = os.getenv("NOMIC_API_KEY")
    
    print(f"OCR:                {'[ENABLED]' if ocr_provider != 'none' else '[DISABLED]'}")
    if ocr_provider == "ollama":
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        print(f"  - Ollama URL:     {ollama_url}")
    elif ocr_provider == "azure_document_intelligence":
        di_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        print(f"  - DI Endpoint:    {'[SET]' if di_endpoint else '[NOT SET]'}")
    
    print(f"Web Search:         {'[ENABLED]' if web_search and serper_key else '[DISABLED]'}")
    if web_search and not serper_key:
        print("  - WARNING: ENABLE_WEB_SEARCH=true but SERPER_API_KEY not set")
    
    print(f"Redis Cache:        {'[ENABLED]' if redis_url else '[DISABLED - using in-memory]'}")
    print(f"NOMIC Embeddings:   {'[ENABLED]' if nomic_enabled and nomic_key else '[DISABLED]'}")
    if nomic_enabled and not nomic_key:
        print("  - WARNING: ENABLE_NOMIC_EMBEDDINGS=true but NOMIC_API_KEY not set")
    
    print("\n" + "=" * 70)
    
    if core_missing:
        return False
    return True

if __name__ == "__main__":
    success = check_env_vars()
    sys.exit(0 if success else 1)

