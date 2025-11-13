import json
from collections import namedtuple
from io import BytesIO
from typing import Optional

import aiohttp
import openai.types
from azure.cognitiveservices.speech import ResultReason
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.pipeline.transport import (
    AioHttpTransportResponse,
    AsyncHttpTransport,
    HttpRequest,
)
from azure.search.documents.agent.models import (
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentModelQueryPlanningActivityRecord,
    KnowledgeAgentRetrievalResponse,
    KnowledgeAgentSearchIndexActivityArguments,
    KnowledgeAgentSearchIndexActivityRecord,
    KnowledgeAgentSearchIndexReference,
)
from azure.search.documents.models import (
    VectorQuery,
)
from azure.storage.blob import BlobProperties

MOCK_EMBEDDING_DIMENSIONS = 1536
MOCK_EMBEDDING_MODEL_NAME = "text-embedding-ada-002"
TEST_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00"
    b"\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac\xfc\xcf\xf0\xbf\x1e\x00\x06\x83\x02\x7f\x94\xad"
    b"\xd0\xeb\x00\x00\x00\x00IEND\xaeB`\x82"
)

MockToken = namedtuple("MockToken", ["token", "expires_on", "value"])


class MockAzureCredential(AsyncTokenCredential):

    async def get_token(self, *scopes, **kwargs):  # accept claims, enable_cae, etc.
        # Return a simple mock token structure with required attributes
        return MockToken("mock-token", 9999999999, "mock-token")


class MockAzureCredentialExpired(AsyncTokenCredential):

    def __init__(self):
        self.access_number = 0

    async def get_token(self, *scopes, **kwargs):
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
        return TEST_PNG_BYTES

    async def readinto(self, buffer: BytesIO):
        buffer.write(b"test")


class MockContentReader:
    """Mock content reader for aiohttp.ClientResponse"""
    def __init__(self, body_bytes):
        self._body = body_bytes
        self._offset = 0
        self._exception = None

    async def read(self, n=-1):
        if n == -1:
            result = self._body[self._offset:]
            self._offset = len(self._body)
        else:
            result = self._body[self._offset:self._offset + n]
            self._offset += len(result)
        return result

    def exception(self):
        return self._exception

    def set_exception(self, exc):
        self._exception = exc


class MockAiohttpClientResponse404(aiohttp.ClientResponse):
    def __init__(self, url, body_bytes, headers=None):
        self._body = body_bytes
        self._headers = headers
        self._cache = {}
        self.status = 404
        self.reason = "Not Found"
        self._url = url
        self._loop = None
        self.content = MockContentReader(body_bytes)


class MockAiohttpClientResponse(aiohttp.ClientResponse):
    def __init__(self, url, body_bytes, headers=None):
        self._body = body_bytes
        self._headers = headers
        self._cache = {}
        self.status = 200
        self.reason = "OK"
        self._url = url
        self._loop = None
        self.content = MockContentReader(body_bytes)


class MockTransport(AsyncHttpTransport):
    async def send(self, request: HttpRequest, **kwargs) -> AioHttpTransportResponse:
        return AioHttpTransportResponse(
            request,
            MockAiohttpClientResponse(
                request.url,
                TEST_PNG_BYTES,
                {
                    "Content-Type": "application/octet-stream",
                    "Content-Range": "bytes 0-27/28",
                    "Content-Length": "28",
                },
            ),
        )

    async def __aexit__(self, *args):
        pass

    async def open(self):
        pass  # pragma: no cover

    async def close(self):
        pass  # pragma: no cover


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
        if search_text == "westbrae nursery logo" and (
            vector_queries and any([vector.fields == "images/embedding" for vector in vector_queries])
        ):
            self.data = [
                [
                    {
                        "id": "file-westbrae_jun28_pdf-77657374627261655F6A756E32382E7064667B276F696473273A205B2766653437353262612D623565652D343531632D623065312D393332316664663365353962275D7D-page-0",
                        "content": '<figure><figcaption>1.1 <br>The image displays the Gmail logo. It consists of a stylized letter "M" with four colors: red, blue, green, and yellow. To the right of the "M" is the word "Gmail" written in gray text. The design is modern and clean. The colors used are characteristic of Google\'s branding.</figcaption></figure>\n\n\nPamela Fox <pamela.fox@gmail.com>\n\nReceipt / Tax invoice (#2-108442)\n\nWestbrae Nursery <no-reply@email.lightspeedhq.com>\nReply-To: jeff@westbrae-nursery.com\nTo: pamela.fox@gmail.com\n\nSat, Jun 28, 2025 at 1:21 PM\n\n\n<figure><figcaption>1.2 <br>The image shows the logo of Westbrae Nursery. The logo features three daffodil flowers on the left side. The text "Westbrae" is positioned to the right of the flowers. Below "Westbrae" is the word "Nursery." The design is simple and rendered in black and white.</figcaption></figure>\n\n\nAn Employee-Owned Co-op\n1272 Gilman St, Berkeley, CA 94706\n510-526-5517\n\nMain Outlet\n\nReceipt / Tax Invoice #2-108442 28 Jun 2025 1:21pm\n\n\n<figure><table><tr><td>1 Gopher Baskets</td><td>@ $7.',
                        "category": None,
                        "sourcepage": "westbrae_jun28.pdf#page=1",
                        "sourcefile": "westbrae_jun28.pdf",
                        "oids": ["OID_X"],
                        "groups": [],
                        "captions": [],
                        "score": 0.05000000447034836,
                        "reranker_score": 3.2427687644958496,
                        "search_agent_query": None,
                        "images": [
                            {
                                "url": "https://userst5gj4l5eootrlo.dfs.core.windows.net/user-content/OID_X/images/westbrae_jun28.pdf/page_0/figure1_1.png",
                                "description": '<figure><figcaption>1.1 <br>The image displays the Gmail logo. It consists of a stylized letter "M" with four colors: red, blue, green, and yellow. To the right of the "M" is the word "Gmail" written in gray text. The design is modern and clean. The colors used are characteristic of Google\'s branding.</figcaption></figure>',
                                "boundingbox": [32.99, 43.65, 126.14, 67.72],
                            },
                            {
                                "url": "https://userst5gj4l5eootrlo.dfs.core.windows.net/user-content/OID_X/images/westbrae_jun28.pdf/page_0/figure1_2.png",
                                "description": '<figure><figcaption>1.2 <br>The image shows the logo of Westbrae Nursery. The logo features three daffodil flowers on the left side. The text "Westbrae" is positioned to the right of the flowers. Below "Westbrae" is the word "Nursery." The design is simple and rendered in black and white.</figcaption></figure>',
                                "boundingbox": [40.76, 163.42, 347.1, 354.15],
                            },
                        ],
                    },
                    {
                        "id": "file-westbrae_jun28_pdf-77657374627261655F6A756E32382E7064667B276F696473273A205B2766653437353262612D623565652D343531632D623065312D393332316664663365353962275D7D-page-1",
                        "content": "</figcaption></figure>\n\n\nAn Employee-Owned Co-op\n1272 Gilman St, Berkeley, CA 94706\n510-526-5517\n\nMain Outlet\n\nReceipt / Tax Invoice #2-108442 28 Jun 2025 1:21pm\n\n\n<figure><table><tr><td>1 Gopher Baskets</td><td>@ $7.99</td><td>$7.99</td></tr><tr><td>1 qt</td><td></td><td></td></tr><tr><td rowSpan=2>1 Gopher Baskets 1 gal</td><td>@ $14.99</td><td>$14.99</td></tr><tr><td></td><td></td></tr><tr><td>1 Edible 4.99</td><td>@ $4.99</td><td>$4.99</td></tr><tr><td>4 Color 11.99</td><td>@ $11.99</td><td>$47.96</td></tr><tr><td>1 Edible $6.99</td><td>@ $6.99</td><td>$6.99</td></tr><tr><td>Subtotal</td><td></td><td>$82.",
                        "category": None,
                        "sourcepage": "westbrae_jun28.pdf#page=1",
                        "sourcefile": "westbrae_jun28.pdf",
                        "oids": ["OID_X"],
                        "groups": [],
                        "captions": [],
                        "score": 0.04696394503116608,
                        "reranker_score": 1.8582123517990112,
                        "search_agent_query": None,
                        "images": [
                            {
                                "url": "https://userst5gj4l5eootrlo.dfs.core.windows.net/user-content/OID_X/images/westbrae_jun28.pdf/page_0/figure1_1.png",
                                "description": '<figure><figcaption>1.1 <br>The image displays the Gmail logo. It consists of a stylized letter "M" with four colors: red, blue, green, and yellow. To the right of the "M" is the word "Gmail" written in gray text. The design is modern and clean. The colors used are characteristic of Google\'s branding.</figcaption></figure>',
                                "boundingbox": [32.99, 43.65, 126.14, 67.72],
                            },
                            {
                                "url": "https://userst5gj4l5eootrlo.dfs.core.windows.net/user-content/OID_X/images/westbrae_jun28.pdf/page_0/figure1_2.png",
                                "description": '<figure><figcaption>1.2 <br>The image shows the logo of Westbrae Nursery. The logo features three daffodil flowers on the left side. The text "Westbrae" is positioned to the right of the flowers. Below "Westbrae" is the word "Nursery." The design is simple and rendered in black and white.</figcaption></figure>',
                                "boundingbox": [40.76, 163.42, 347.1, 354.15],
                            },
                        ],
                    },
                    {
                        "id": "file-westbrae_jun28_pdf-77657374627261655F6A756E32382E7064667B276F696473273A205B2766653437353262612D623565652D343531632D623065312D393332316664663365353962275D7D-page-4",
                        "content": "\n\nIf you have any questions about how to take care of the plants you purchase\nor if they start to show symptoms of ill health, please, give us a call (510-526-\n5517)\n\nreceipt.pdf\n50K",
                        "category": None,
                        "sourcepage": "westbrae_jun28.pdf#page=2",
                        "sourcefile": "westbrae_jun28.pdf",
                        "oids": ["OID_X"],
                        "groups": [],
                        "captions": [],
                        "score": 0.016393441706895828,
                        "reranker_score": 1.7518715858459473,
                        "search_agent_query": None,
                        "images": [],
                    },
                ]
            ]
        elif search_text == "interest rates" or (
            vector_queries and any([vector.fields == "images/embedding" for vector in vector_queries])
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


def mock_vision_response():
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
            KnowledgeAgentSearchIndexActivityRecord(
                id=1,
                knowledge_source_name="index",
                search_index_arguments=KnowledgeAgentSearchIndexActivityArguments(search="whistleblower query"),
                count=10,
                elapsed_ms=50,
            ),
        ],
        references=[
            KnowledgeAgentSearchIndexReference(
                id=0,
                activity_source=1,
                doc_key="file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-2",
                reranker_score=3.4577205181121826,
                source_data={
                    "id": "file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-2",
                    "content": "There is a whistleblower policy.",
                    "sourcepage": "Benefit_Options-2.pdf",
                    "sourcefile": "Benefit_Options.pdf",
                },
            )
        ],
    )


def mock_retrieval_response_with_sorting():
    """Mock response with multiple references for testing sorting"""
    return KnowledgeAgentRetrievalResponse(
        response=[
            KnowledgeAgentMessage(
                role="assistant",
                content=[KnowledgeAgentMessageTextContent(text="Test response")],
            )
        ],
        activity=[
            KnowledgeAgentSearchIndexActivityRecord(
                id=1,
                knowledge_source_name="index",
                search_index_arguments=KnowledgeAgentSearchIndexActivityArguments(search="first query"),
                count=10,
                elapsed_ms=50,
            ),
            KnowledgeAgentSearchIndexActivityRecord(
                id=2,
                knowledge_source_name="index",
                search_index_arguments=KnowledgeAgentSearchIndexActivityArguments(search="second query"),
                count=10,
                elapsed_ms=50,
            ),
        ],
        references=[
            KnowledgeAgentSearchIndexReference(
                id="2",  # Higher ID for testing interleaved sorting
                activity_source=2,
                doc_key="doc2",
                source_data={"id": "doc2", "content": "Content 2", "sourcepage": "page2.pdf"},
                reranker_score=3.7,
            ),
            KnowledgeAgentSearchIndexReference(
                id="1",  # Lower ID for testing interleaved sorting
                activity_source=1,
                doc_key="doc1",
                source_data={"id": "doc1", "content": "Content 1", "sourcepage": "page1.pdf"},
                reranker_score=3.5,
            ),
        ],
    )


def mock_retrieval_response_with_top_limit():
    """Mock response with many references to test top limit during document building"""
    references = []
    for i in range(15):  # More than any reasonable top limit
        references.append(
            KnowledgeAgentSearchIndexReference(
                id=str(i),
                activity_source=1,
                doc_key=f"doc{i}",
                source_data={"id": f"doc{i}", "content": f"Content {i}", "sourcepage": f"page{i}.pdf"},
            )
        )

    return KnowledgeAgentRetrievalResponse(
        response=[
            KnowledgeAgentMessage(
                role="assistant",
                content=[KnowledgeAgentMessageTextContent(text="Test response")],
            )
        ],
        activity=[
            KnowledgeAgentSearchIndexActivityRecord(
                id=1,
                knowledge_source_name="index",
                search_index_arguments=KnowledgeAgentSearchIndexActivityArguments(search="query"),
                count=10,
                elapsed_ms=50,
            ),
        ],
        references=references,
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


# Mock DirectoryClient used in blobmanager.py:AdlsBlobManager
class MockDirectoryClient:
    async def get_directory_properties(self):
        # Return dummy properties to indicate directory exists
        return {"name": "test-directory"}

    async def get_access_control(self):
        # Return a dictionary with the owner matching the auth_client's user_oid
        return {"owner": "OID_X"}  # This should match the user_oid in auth_client

    def get_file_client(self, filename):
        # Return a file client for the given filename
        return MockFileClient(filename)


# Mock FileClient used in blobmanager.py:AdlsBlobManager
class MockFileClient:
    def __init__(self, path_name):
        self.path_name = path_name

    async def download_file(self):
        return MockBlob()


def mock_speak_text_success(self, text):
    return MockSynthesisResult(MockAudio("mock_audio_data"))


def mock_speak_text_cancelled(self, text):
    return MockSynthesisResult(MockAudioCancelled("mock_audio_data"))


def mock_speak_text_failed(self, text):
    return MockSynthesisResult(MockAudioFailure("mock_audio_data"))
