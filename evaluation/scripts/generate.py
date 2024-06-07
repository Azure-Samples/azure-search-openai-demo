import json
import logging
import math
import random
from pathlib import Path

from azure.ai.generative.synthetic.qa import QADataGenerator, QAType
from azure.search.documents import SearchClient

from . import service_setup

logger = logging.getLogger("scripts")


def generate_test_qa_data(
    openai_config: dict,
    search_client: SearchClient,
    num_questions_total: int,
    num_questions_per_source: int,
    output_file: Path,
):
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

    logger.info("Writing %d questions to %s", len(qa), output_file)
    directory = Path(output_file).parent
    if not directory.exists():
        directory.mkdir(parents=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for item in qa:
            f.write(json.dumps(item) + "\n")


def generate_based_on_questions(openai_client, model: str, qa: list, num_questions: int, prompt: str):
    existing_questions = ""
    if qa:
        qa = random.sample(qa, len(qa))  # Shuffle questions for some randomness
        existing_questions = "\n".join([item["question"] for item in qa])

    gpt_response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": f"{prompt} Only generate {num_questions} TOTAL. Separate each question by a new line. \n{existing_questions}",  # noqa: E501
            }
        ],
        n=1,
        max_tokens=num_questions * 50,
        temperature=0.3,
    )

    qa = []
    for message in gpt_response.choices[0].message.content.split("\n")[0:num_questions]:
        qa.append({"question": message, "truth": f"Generated from this prompt: {prompt}"})
    return qa


def generate_dontknows_qa_data(openai_config: dict, num_questions_total: int, input_file: Path, output_file: Path):
    logger.info("Generating off-topic questions based on %s", input_file)
    with open(input_file, encoding="utf-8") as f:
        qa = [json.loads(line) for line in f.readlines()]

    openai_client = service_setup.get_openai_client(openai_config)
    dontknows_qa = []
    num_questions_each = math.ceil(num_questions_total / 4)
    dontknows_qa += generate_based_on_questions(
        openai_client,
        openai_config["model"],
        qa,
        num_questions_each,
        f"Given these questions, suggest {num_questions_each} questions that are very related but are not directly answerable by the same sources. Do not simply ask for other examples of the same thing - your question should be standalone.",  # noqa: E501
    )
    dontknows_qa += generate_based_on_questions(
        openai_client,
        openai_config["model"],
        qa,
        num_questions_each,
        f"Given these questions, suggest {num_questions_each} questions with similar keywords that are about publicly known facts.",  # noqa: E501
    )
    dontknows_qa += generate_based_on_questions(
        openai_client,
        openai_config["model"],
        qa,
        num_questions_each,
        f"Given these questions, suggest {num_questions_each} questions that are not related to these topics at all but have well known answers.",  # noqa: E501
    )
    remaining = num_questions_total - len(dontknows_qa)
    dontknows_qa += generate_based_on_questions(
        openai_client,
        openai_config["model"],
        qa=None,
        num_questions=remaining,
        prompt=f"Suggest {remaining} questions that are nonsensical, and would result in confusion if you asked it.",  # noqa: E501
    )

    logger.info("Writing %d off-topic questions to %s", len(dontknows_qa), output_file)
    directory = Path(output_file).parent
    if not directory.exists():
        directory.mkdir(parents=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for item in dontknows_qa:
            f.write(json.dumps(item) + "\n")
