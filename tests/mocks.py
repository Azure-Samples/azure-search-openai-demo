import json
from collections import namedtuple
from io import BytesIO
from typing import Optional

import openai.types
from azure.cognitiveservices.speech import ResultReason
from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.agent.models import (
    KnowledgeAgentAzureSearchDocReference,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentModelQueryPlanningActivityRecord,
    KnowledgeAgentRetrievalResponse,
    KnowledgeAgentSearchActivityRecord,
    KnowledgeAgentSearchActivityRecordQuery,
)
from azure.search.documents.models import (
    VectorQuery,
)
from azure.storage.blob import BlobProperties

MOCK_EMBEDDING_DIMENSIONS = 1536
MOCK_EMBEDDING_MODEL_NAME = "text-embedding-ada-002"

MockToken = namedtuple("MockToken", ["token", "expires_on", "value"])


class MockAzureCredential(AsyncTokenCredential):

    async def get_token(self, uri):
        return MockToken("", 9999999999, "")


class MockAzureCredentialExpired(AsyncTokenCredential):

    def __init__(self):
        self.access_number = 0

    async def get_token(self, uri):
        self.access_number += 1
        if self.access_number == 1:
            return MockToken("", 0, "")
        else:
            return MockToken("", 9999999999, "")


class MockBlobClient:
    async def download_blob(self):
        return MockBlob()


class MockBlob:
    def __init__(self):
        self.properties = BlobProperties(
            name="Financial Market Analysis Report 2023-7.png", content_settings={"content_type": "image/png"}
        )

    async def readall(self):
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac\xfc\xcf\xf0\xbf\x1e\x00\x06\x83\x02\x7f\x94\xad\xd0\xeb\x00\x00\x00\x00IEND\xaeB`\x82"

    async def readinto(self, buffer: BytesIO):
        buffer.write(b"test")


class MockAsyncPageIterator:
    def __init__(self, data):
        self.data = data

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.data:
            raise StopAsyncIteration
        return self.data.pop(0)  # This should be a list of dictionaries.


class MockCaption:
    def __init__(self, text, highlights=None, additional_properties=None):
        self.text = text
        self.highlights = highlights or []
        self.additional_properties = additional_properties or {}


class MockAsyncSearchResultsIterator:
    def __init__(self, search_text, vector_queries: Optional[list[VectorQuery]]):
        if search_text == "interest rates" or (
            vector_queries and any([vector.fields == "images/embeddings" for vector in vector_queries])
        ):
            self.data = [
                [
                    {
                        "id": "file-Financial_Market_Analysis_Report_2023_pdf-46696E616E6369616C204D61726B657420416E616C79736973205265706F727420323032332E706466-page-7",
                        "content": ' This\nsection examines the correlations between stock indices, cryptocurrency prices, and commodity prices,\nrevealing how changes in one market can have ripple effects across the financial ecosystem.### Impact of Macroeconomic Factors\n\n\n<figure><figcaption>Impact of Interest Rates, Inflation, and GDP Growth on Financial Markets<br>The image is a line graph titled "on Financial Markets" displaying data from 2018 to 2023. It tracks three variables: Interest Rates %, Inflation Data %, and GDP Growth %, each represented by a different colored line (blue for Interest Rates, orange for Inflation Data, and gray for GDP Growth). Interest Rates % start around 2% in 2018, dip to about 0.25% in 2021, then rise to 1.5% in 2023. Inflation Data % begin at approximately 1.9% in 2018, rise to a peak near 3.4% in 2022, and then decrease to 2.5% in 2023. GDP Growth % shows significant fluctuations, starting at 3% in 2018, plunging to almost -4% in 2020, then rebounding to around 4.5% in 2021 before gradually declining to around 2.8% in 2023.</figcaption></figure>\n\n\nMacroeconomic factors such as interest\nrates, inflation, and GDP growth play a\npivotal role in shaping financial markets.',
                        "category": None,
                        "sourcepage": "Financial Market Analysis Report 2023.pdf#page=7",
                        "sourcefile": "Financial Market Analysis Report 2023.pdf",
                        "oids": None,
                        "groups": None,
                        "captions": [],
                        "score": 0.03333333507180214,
                        "reranker_score": 3.207321882247925,
                        "search_agent_query": None,
                        "images": [],
                    },
                    {
                        "id": "file-Financial_Market_Analysis_Report_2023_pdf-46696E616E6369616C204D61726B657420416E616C79736973205265706F727420323032332E706466-page-8",
                        "content": "</figcaption></figure>\n\n\nMacroeconomic factors such as interest\nrates, inflation, and GDP growth play a\npivotal role in shaping financial markets.\nThis section analyzes how these factors\nhave influenced stock, cryptocurrency,\nand commodity markets over recent\nyears, providing insights into the\ncomplex relationship between the\neconomy and financial market\nperformance.## Future Predictions and Trends\n\n\n<figure><figcaption>Relative Growth Trends for S&P 500, Bitcoin, and Oil Prices (2024 Indexed to 100)<br>This horizontal bar chart shows prices indexed to 100 for the years 2024 to 2028. It compares the prices of Oil, Bitcoin, and the S&P 500 across these years. In 2024, all three have an index value of 100. From 2025 to 2028, all three generally increase, with Bitcoin consistently having the highest index value, followed closely by the S&P 500 and then Oil. The chart uses grey bars for Oil, orange bars for Bitcoin, and blue bars for the S&P 500.</figcaption></figure>\n\n\nBased on historical data, current trends,\nand economic indicators, this section\npresents predictions for the future of\nfinancial markets.",
                        "category": None,
                        "sourcepage": "Financial Market Analysis Report 2023.pdf#page=8",
                        "sourcefile": "Financial Market Analysis Report 2023.pdf",
                        "oids": None,
                        "groups": None,
                        "captions": [],
                        "score": 0.04945354908704758,
                        "reranker_score": 2.573531150817871,
                        "search_agent_query": None,
                        "images": [
                            {
                                "url": "https://sticygqdubf4x6w.blob.core.windows.net/images/Financial%20Market%20Analysis%20Report%202023.pdf/page7/figure8_1.png",
                                "description": '<figure><figcaption>Impact of Interest Rates, Inflation, and GDP Growth on Financial Markets<br>The image is a line graph titled "on Financial Markets" displaying data from 2018 to 2023. It tracks three variables: Interest Rates %, Inflation Data %, and GDP Growth %, each represented by a different colored line (blue for Interest Rates, orange for Inflation Data, and gray for GDP Growth). Interest Rates % start around 2% in 2018, dip to about 0.25% in 2021, then rise to 1.5% in 2023. Inflation Data % begin at approximately 1.9% in 2018, rise to a peak near 3.4% in 2022, and then decrease to 2.5% in 2023. GDP Growth % shows significant fluctuations, starting at 3% in 2018, plunging to almost -4% in 2020, then rebounding to around 4.5% in 2021 before gradually declining to around 2.8% in 2023.</figcaption></figure>',
                                "boundingbox": [63.1008, 187.9416, 561.3408000000001, 483.5088],
                            }
                        ],
                    },
                    {
                        "id": "file-Financial_Market_Analysis_Report_2023_pdf-46696E616E6369616C204D61726B657420416E616C79736973205265706F727420323032332E706466-page-1",
                        "content": 'advanced data\nanalytics to present a clear picture of the complex interplay between\ndifferent financial markets and their potential trajectories## Introduction to Financial Markets\n\n\n<figure><figcaption>Global Financial Market Distribution (2023)<br>The pie chart features four categories: Stocks, Bonds, Cryptocurrencies, and Commodities. Stocks take up the largest portion of the chart, represented in blue, accounting for 40%. Bonds are the second largest, shown in orange, making up 25%. Cryptocurrencies are depicted in gray and cover 20% of the chart. Commodities are the smallest segment, shown in yellow, comprising 15%.</figcaption></figure>\n\n\nThe global financial market is a vast and intricate network of\nexchanges, instruments, and assets, ranging from traditional stocks\nand bonds to modern cryptocurrencies and commodities. Each\nsegment plays a crucial role in the overall economy, and their\ninteractions can have profound effects on global financial stability.\nThis section provides an overview of these segments and sets the\nstage for a detailed analysis## Stock Market Overview\n\n\n<figure><figcaption><br>The image is a line graph titled "5-Year Trend of the S&P 500 Index.',
                        "category": None,
                        "sourcepage": "Financial Market Analysis Report 2023.pdf#page=2",
                        "sourcefile": "Financial Market Analysis Report 2023.pdf",
                        "oids": None,
                        "groups": None,
                        "captions": [],
                        "score": 0.0317540317773819,
                        "reranker_score": 1.8846203088760376,
                        "search_agent_query": None,
                        "images": [
                            {
                                "url": "https://sticygqdubf4x6w.blob.core.windows.net/images/Financial%20Market%20Analysis%20Report%202023.pdf/page7/figure8_1.png",
                                "description": '<figure><figcaption>Impact of Interest Rates, Inflation, and GDP Growth on Financial Markets<br>The image is a line graph titled "on Financial Markets" displaying data from 2018 to 2023. It tracks three variables: Interest Rates %, Inflation Data %, and GDP Growth %, each represented by a different colored line (blue for Interest Rates, orange for Inflation Data, and gray for GDP Growth). Interest Rates % start around 2% in 2018, dip to about 0.25% in 2021, then rise to 1.5% in 2023. Inflation Data % begin at approximately 1.9% in 2018, rise to a peak near 3.4% in 2022, and then decrease to 2.5% in 2023. GDP Growth % shows significant fluctuations, starting at 3% in 2018, plunging to almost -4% in 2020, then rebounding to around 4.5% in 2021 before gradually declining to around 2.8% in 2023.</figcaption></figure>',
                                "boundingbox": [63.1008, 187.9416, 561.3408000000001, 483.5088],
                            }
                        ],
                    },
                ]
            ]
        else:
            self.data = [
                [
                    {
                        "sourcepage": "Benefit_Options-2.pdf",
                        "sourcefile": "Benefit_Options.pdf",
                        "content": "There is a whistleblower policy.",
                        "embedding": [],
                        "category": None,
                        "id": "file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-2",
                        "@search.score": 0.03279569745063782,
                        "@search.reranker_score": 3.4577205181121826,
                        "@search.highlights": None,
                        "@search.captions": [MockCaption("Caption: A whistleblower policy.")],
                    },
                ]
            ]

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.data:
            raise StopAsyncIteration
        return MockAsyncPageIterator(self.data.pop(0))

    async def get_count(self):
        return len(self.data)

    def by_page(self):
        return self


class MockResponse:
    def __init__(self, status, text=None, headers=None):
        self._text = text or ""
        self.status = status
        self.headers = headers or {}

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self

    async def text(self):
        return self._text

    async def json(self):
        return json.loads(self._text)

    def raise_for_status(self):
        if self.status != 200:
            raise Exception(f"HTTP status {self.status}")


class MockEmbeddingsClient:
    def __init__(self, create_embedding_response: openai.types.CreateEmbeddingResponse):
        self.create_embedding_response = create_embedding_response

    async def create(self, *args, **kwargs) -> openai.types.CreateEmbeddingResponse:
        return self.create_embedding_response


class MockClient:
    def __init__(self, embeddings_client):
        self.embeddings = embeddings_client


def mock_computervision_response():
    return MockResponse(
        status=200,
        text=json.dumps(
            {
                "vector": [
                    0.011925711,
                    0.023533698,
                    0.010133852,
                    0.0063544377,
                    -0.00038590943,
                    0.0013952175,
                    0.009054946,
                    -0.033573493,
                    -0.002028305,
                ],
                "modelVersion": "2022-04-11",
            }
        ),
    )


def mock_retrieval_response():
    return KnowledgeAgentRetrievalResponse(
        response=[
            KnowledgeAgentMessage(
                role="assistant",
                content=[
                    KnowledgeAgentMessageTextContent(
                        text=r'[{"ref_id":0,"title":"Benefit_Options-2.pdf","content":"There is a whistleblower policy."}]'
                    )
                ],
            )
        ],
        activity=[
            KnowledgeAgentModelQueryPlanningActivityRecord(id=0, input_tokens=10, output_tokens=20, elapsed_ms=200),
            KnowledgeAgentSearchActivityRecord(
                id=1,
                target_index="index",
                query=KnowledgeAgentSearchActivityRecordQuery(search="whistleblower query"),
                count=10,
                elapsed_ms=50,
            ),
        ],
        references=[
            KnowledgeAgentAzureSearchDocReference(
                id=0,
                activity_source=1,
                doc_key="Benefit_Options-2.pdf",
                source_data={"content": "There is a whistleblower policy.", "sourcepage": "Benefit_Options-2.pdf"},
            )
        ],
    )


class MockAudio:
    def __init__(self, audio_data):
        self.audio_data = audio_data
        self.reason = ResultReason.SynthesizingAudioCompleted

    def read(self):
        return self.audio_data


class MockSpeechSynthesisCancellationDetails:
    def __init__(self):
        self.reason = "Canceled"
        self.error_details = "The synthesis was canceled."


class MockAudioCancelled:
    def __init__(self, audio_data):
        self.audio_data = audio_data
        self.reason = ResultReason.Canceled
        self.cancellation_details = MockSpeechSynthesisCancellationDetails()

    def read(self):
        return self.audio_data


class MockAudioFailure:
    def __init__(self, audio_data):
        self.audio_data = audio_data
        self.reason = ResultReason.NoMatch

    def read(self):
        return self.audio_data


class MockSynthesisResult:
    def __init__(self, result):
        self.__result = result

    def get(self):
        return self.__result


def mock_speak_text_success(self, text):
    return MockSynthesisResult(MockAudio("mock_audio_data"))


def mock_speak_text_cancelled(self, text):
    return MockSynthesisResult(MockAudioCancelled("mock_audio_data"))


def mock_speak_text_failed(self, text):
    return MockSynthesisResult(MockAudioFailure("mock_audio_data"))
