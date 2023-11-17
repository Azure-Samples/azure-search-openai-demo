import json
import os
from pathlib import Path

from azure.ai.generative.synthetic.qa import QADataGenerator, QAType
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents import SearchClient


def generate_test_qa_data(num_questions_total: int, num_questions_per_source: int, output_file: str):
    azure_credential = AzureDeveloperCliCredential()

    aoai_config = {
        "api_type": "azure_ad",
        "api_base": f"https://{os.environ['AZURE_OPENAI_SERVICE']}.openai.azure.com",
        "api_key": azure_credential.get_token("https://cognitiveservices.azure.com/.default").token,
        "api_version": "2023-07-01-preview",
        "deployment": os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"],
        "model": os.environ["AZURE_OPENAI_EVALGPT_MODEL"],
    }

    qa_generator = QADataGenerator(model_config=aoai_config)

    search_client = SearchClient(
        endpoint=f"https://{os.environ['AZURE_SEARCH_SERVICE']}.search.windows.net/",
        index_name=os.environ["AZURE_SEARCH_INDEX"],
        credential=azure_credential,
    )
    r = search_client.search("", top=1000)
    qa = []
    for doc in r:
        if len(qa) > num_questions_total:
            break
        print("Processing doc", doc["sourcepage"])
        text = doc["content"]

        result = qa_generator.generate(
            text=text,
            qa_type=QAType.LONG_ANSWER,
            num_questions=num_questions_per_source,
        )

        for question, answer in result["question_answers"]:
            citation = f"[{doc['sourcepage']}]"
            qa.append({"question": question, "answer": answer + citation})

    parent_dir = Path(__file__).parent.absolute()
    with open(Path(parent_dir) / output_file, "w") as f:
        for item in qa:
            f.write(json.dumps(item) + "\n")


if __name__ == "__main__":
    generate_test_qa_data(num_questions_total=5, num_questions_per_source=5, output_file="input/qa2.jsonl")
