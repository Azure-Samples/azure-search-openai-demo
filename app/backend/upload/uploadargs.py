import os

def get_upload_args(args):
    args.storageaccount = os.environ["AZURE_STORAGE_ACCOUNT"]
    args.storageresourcegroup = os.environ["AZURE_STORAGE_CONTAINER"]
    args.searchservice = os.environ["AZURE_SEARCH_SERVICE"]
    args.index = os.environ["AZURE_SEARCH_INDEX"]
    args.openaihost = os.getenv("OPENAI_HOST", "azure")
    args.openaimodelname = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002")
    args.openaiservice = os.getenv("AZURE_OPENAI_SERVICE")
    args.openaideployment = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT") if args.openaihost == "azure" else None
    args.openaikey = os.getenv("OPENAI_API_KEY")
    args.openaiorg = os.getenv("OPENAI_ORGANIZATION")
    args.formrecognizerservice = os.getenv("AZURE_FORMRECOGNIZER_SERVICE")
    args.formrecognizerkey = None
    args.storagekey = None
    args.container = os.getenv("AZURE_STORAGE_CONTAINER", None)
    args.subscriptionid = os.getenv("AZURE_SUBSCRIPTION_ID", None)
    args.datalakestorageaccount = os.getenv("AZURE_ADLS_GEN2_STORAGE_ACCOUNT", None)
    args.datalakefilesystempath = os.getenv("ADLS_GEN2_FILESYSTEM_PATH", None)
    args.datalakefilesystem = os.getenv("ADLS_GEN2_FILESYSTEM", None)
    args.useacls = os.getenv("AZURE_USE_AUTHENTICATION", None)
    args.searchanalyzername = os.getenv("AZURE_SEARCH_ANALYZER_NAME", None)
    args.visionendpoint = os.getenv("AZURE_VISION_ENDPOINT", None)
    args.visionkey = os.getenv("AZURE_VISION_KEY", None)
    args.keyvaultname = os.getenv("AZURE_KEY_VAULT_NAME", None)
    args.visionsecretname = os.getenv("VISION_SECRET_NAME", None)
    args.searchsecretname = os.getenv("AZURE_SEARCH_SECRET_NAME", None)
    args.searchimages = True if os.getenv("USE_GPT4V") else None
    args.novectors = True if os.getenv("USE_VECTORS") == False else None
    args.localpdfparser = True if os.getenv("USE_LOCAL_PDF_PARSER") else None
    args.tenantid = os.getenv("AZURE_TENANT_ID", None)
    args.useintvectorization = os.getenv("USE_FEATURE_INT_VECTORIZATION", None)
    args.verbose = None
    args.disablebatchvectors = None
    args.removeall = None
    args.remove = None
    args.category = None
    args.searchkey = None
    
    return args