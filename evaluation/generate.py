from azure.ai.generative.synthetic.qa import QADataGenerator, QAType
from azure.search.documents.aio import SearchClient


def generate_test_qa_data(
    openai_params, chatgpt_deployment, chatgpt_model, search_creds, search_service, search_index, filename=None
):
    import json

    model_config = dict(
        api_type=openai_params.api_type,
        api_base=openai_params.api_base,
        api_key=openai_params.api_key,
        deployment=chatgpt_deployment,
        model=chatgpt_model,
        max_tokens=2000,
    )
    qa_generator = QADataGenerator(model_config=model_config)

    search_client = SearchClient(
        endpoint=f"https://{search_service}.search.windows.net/", index_name=search_index, credential=search_creds
    )
    r = search_client.search("", top=1)
    qa = []
    for doc in r:
        print("Processing doc", doc["sourcepage"])
        text = doc["content"]

        result = qa_generator.generate(
            text=text,
            qa_type=QAType.CONVERSATION,
            num_questions=5,
        )

        for question, answer in result["question_answers"]:
            citation = f"[{doc['sourcepage']}]"
            qa.append({"question": question, "answer": answer + citation})

    # Save qa to jsonl
    with open("qa_multiturn.jsonl", "w") as f:
        for item in qa:
            f.write(json.dumps(item) + "\n")
