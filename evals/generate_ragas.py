import json
import logging
import os
import pathlib
import re

import rich
from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from dotenv_azd import load_azd_env
from langchain_core.documents import Document as LCDocument
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.graph import KnowledgeGraph, Node, NodeType
from ragas.testset.transforms import apply_transforms, default_transforms

logger = logging.getLogger("evals")

load_azd_env()
root_dir = pathlib.Path(__file__).parent.parent


def get_azure_credential():
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    if AZURE_TENANT_ID:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential with tenant_id %s", AZURE_TENANT_ID)
        azure_credential = AzureDeveloperCliCredential(tenant_id=AZURE_TENANT_ID, process_timeout=60)
    else:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential for home tenant")
        azure_credential = AzureDeveloperCliCredential(process_timeout=60)
    return azure_credential


def get_search_documents(azure_credential) -> str:
    search_client = SearchClient(
        endpoint=f"https://{os.getenv('AZURE_SEARCH_SERVICE')}.search.windows.net",
        index_name=os.getenv("AZURE_SEARCH_INDEX"),
        credential=azure_credential,
    )
    search_results = search_client.search(search_text="*", top=1000)
    return [result for result in search_results]


azure_credential = get_azure_credential()
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "2024-06-01"
azure_endpoint = f"https://{os.getenv('AZURE_OPENAI_SERVICE')}.openai.azure.com"
azure_ad_token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
generator_llm = LangchainLLMWrapper(
    AzureChatOpenAI(
        openai_api_version=azure_openai_api_version,
        azure_endpoint=azure_endpoint,
        azure_ad_token_provider=azure_ad_token_provider,
        azure_deployment=os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT"),
        model=os.environ["AZURE_OPENAI_EVAL_MODEL"],
        validate_base_url=False,
    )
)

# init the embeddings for answer_relevancy, answer_correctness and answer_similarity
generator_embeddings = LangchainEmbeddingsWrapper(
    AzureOpenAIEmbeddings(
        openai_api_version=azure_openai_api_version,
        azure_endpoint=azure_endpoint,
        azure_ad_token_provider=azure_ad_token_provider,
        azure_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
        model=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
    )
)

# Let's make a knowledge_graph from Azure AI Search documents
search_docs = get_search_documents(azure_credential)

# create the transforms
transforms = default_transforms(
    documents=[LCDocument(page_content=doc["content"]) for doc in search_docs],
    llm=generator_llm,
    embedding_model=generator_embeddings,
)

# convert the documents to Ragas nodes
nodes = []
for doc in search_docs:
    content = doc["content"]
    citation = doc["sourcepage"]
    node = Node(
        type=NodeType.DOCUMENT,
        properties={
            "page_content": f"[[{citation}]]: {content}",
            "document_metadata": {"citation": citation},
        },
    )
    nodes.append(node)

kg = KnowledgeGraph(nodes=nodes)
apply_transforms(kg, transforms)

generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings, knowledge_graph=kg)
dataset = generator.generate(testset_size=10, with_debugging_logs=True)

qa_pairs = []
for sample in dataset.samples:
    rich.print(sample)
    question = sample.eval_sample.user_input
    truth = sample.eval_sample.reference
    # Grab the citation in square brackets from the reference_contexts and add it to the truth
    citations = []
    for context in sample.eval_sample.reference_contexts:
        match = re.search(r"\[\[(.*?)\]\]", context)
        if match:
            citation = match.group(1)
            citations.append(f"[{citation}]")
    truth += " " + " ".join(citations)
    qa_pairs.append({"question": question, "truth": truth})

with open(root_dir / "ground_truth_ragas.jsonl", "a") as f:
    for qa_pair in qa_pairs:
        f.write(json.dumps(qa_pair) + "\n")
