import logging
from pathlib import Path

from azure.ai.generative.synthetic.qa import QADataGenerator, QAType
from azure.search.documents import SearchClient
from openai_messages_token_helper import get_token_limit
from promptflow.core import ModelConfiguration

from evaluation import service_setup
from evaluation.utils import load_jsonl, save_jsonl

logger = logging.getLogger("evaluation")


def generate_test_qa_data(
    openai_config: dict,
    search_client: SearchClient,
    num_questions_total: int,
    num_questions_per_source: int,
    output_file: Path,
):
    """Generate test QA data based on search results."""
    logger.info(
        "Generating %d questions total, %d per source, based on search results",
        num_questions_total,
        num_questions_per_source,
    )

    qa_generator = QADataGenerator(model_config=openai_config)

    r = search_client.search("", top=1000)
    qa: list[dict] = []
    for doc in r:
        if len(qa) > num_questions_total:
            break
        logger.info("Processing search document %s", doc["sourcepage"])
        text = doc["content"]

        result = qa_generator.generate(
            text=text,
            qa_type=QAType.LONG_ANSWER,
            num_questions=num_questions_per_source,
        )

        for question, answer in result["question_answers"]:
            citation = f"[{doc['sourcepage']}]"
            qa.append({"question": question, "truth": answer + citation})

    logger.info("Writing %d questions to '%s'", len(qa), output_file)
    save_jsonl(qa, output_file)


def generate_test_qa_answer(
    openai_config: ModelConfiguration,
    question_path: Path,
    output_file: Path,
):
    """Generate answers for test QA data to use for evaluation on Azure AI Studio."""
    logger.info("Generating answers based on the quesion of %s", question_path)

    openai_client = service_setup.get_openai_client(openai_config)

    questions = load_jsonl(question_path)
    for question in questions:
        response = openai_client.chat.completions.create(
            model=openai_config.model,
            messages=[
                {
                    "role": "user",
                    "content": f"{question['question']}",
                }
            ],
            n=1,
            max_tokens=get_token_limit(openai_config.model),
            temperature=0.3,
        )
        question["answer"] = response.choices[0].message.content.split("\n")[0]

    logger.info("Writing %d questions with answer to %s", len(questions), output_file)
    save_jsonl(questions, output_file)
