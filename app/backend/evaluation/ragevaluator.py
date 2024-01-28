from datasets import Dataset
import pandas as pd
from ragas.llms import LangchainLLM
from ragas import evaluate
from ragas.metrics import (
    context_precision,
    answer_relevancy,
    faithfulness,
)
from datasets import Dataset, Features, Sequence, Value
from langchain_community.chat_models import AzureChatOpenAI
from langchain_community.embeddings import AzureOpenAIEmbeddings

from typing import List, Union


class RagEvaluator:
    def __init__(
        self,
        langchain_openai_client: AzureChatOpenAI,
        langchain_embedding_client: AzureOpenAIEmbeddings,
    ) -> None:
        self.langchain_openai_client = langchain_openai_client
        self.langchain_embedding_client = langchain_embedding_client
        self.ragas_azure_model = LangchainLLM(self.langchain_openai_client)
        self.metrics = [faithfulness, answer_relevancy, context_precision]

        # Set Ragas llm and embedding to use Azure OpenAI
        answer_relevancy.embeddings = langchain_embedding_client
        for m in self.metrics:
            m.__setattr__("llm", self.ragas_azure_model)

    def convert_qa_to_dataset(self, question: str, answer: str, context: list[str]) -> Dataset:
        context.append("")
        qa_dataset = {"question": [question], "answer": [answer], "contexts": [context]}
        return Dataset.from_dict(qa_dataset)

    def evaluate_qa(self, question: str, answer: str, contexts: list[str]) -> dict[str, float]:
        qa_dataset = self.convert_qa_to_dataset(question, answer, contexts)
        result = evaluate(qa_dataset, metrics=self.metrics)
        result = {
            "contextPrecision": result["context_precision"],
            "answerRelevance": result["answer_relevancy"],
            "faithfulness": result["faithfulness"],
        }
        return result
