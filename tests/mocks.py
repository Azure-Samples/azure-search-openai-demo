import json
from collections import namedtuple
from typing import Optional

from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.models import (
    VectorQuery,
)
from azure.storage.blob import BlobProperties

MockToken = namedtuple("MockToken", ["token", "expires_on", "value"])


class MockAzureCredential(AsyncTokenCredential):
    async def get_token(self, uri):
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


class MockKeyVaultSecret:
    def __init__(self, value):
        self.value = value


class MockKeyVaultSecretClient:
    async def get_secret(self, secret_name):
        return MockKeyVaultSecret("mysecret")


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
            vector_queries and any([vector.fields == "imageEmbedding" for vector in vector_queries])
        ):
            self.data = [
                [
                    {
                        "category": None,
                        "sourcefile": "Financial Market Analysis Report 2023.pdf",
                        "image_embedding": [
                            -0.86035156,
                            1.3310547,
                            3.9804688,
                            -0.6425781,
                            -2.7246094,
                            -1.6308594,
                            -0.69091797,
                            -2.2539062,
                            -0.09942627,
                        ],
                        "content": "3</td><td>1</td></tr></table>\nFinancial markets are interconnected, with movements in one segment often influencing others. This section examines the correlations between stock indices, cryptocurrency prices, and commodity prices, revealing how changes in one market can have ripple effects across the financial ecosystem.Impact of Macroeconomic Factors\nImpact of Interest Rates, Inflation, and GDP Growth on Financial Markets\n5\n4\n3\n2\n1\n0\n-1 2018 2019\n-2\n-3\n-4\n-5\n2020\n2021 2022 2023\nMacroeconomic factors such as interest rates, inflation, and GDP growth play a pivotal role in shaping financial markets. This section analyzes how these factors have influenced stock, cryptocurrency, and commodity markets over recent years, providing insights into the complex relationship between the economy and financial market performance.\n-Interest Rates % -Inflation Data % GDP Growth % :unselected: :unselected:Future Predictions and Trends\nRelative Growth Trends for S&P 500, Bitcoin, and Oil Prices (2024 Indexed to 100)\n2028\nBased on historical data, current trends, and economic indicators, this section presents predictions ",
                        "id": "file-Financial_Market_Analysis_Report_2023_pdf-46696E616E6369616C204D61726B657420416E616C79736973205265706F727420323032332E706466-page-14",
                        "sourcepage": "Financial Market Analysis Report 2023-6.png",
                        "embedding": [
                            -0.012668486,
                            -0.02251158,
                            0.008822813,
                            -0.02531081,
                            -0.014493219,
                            -0.019503059,
                            -0.015605063,
                            -0.0141138835,
                            -0.019699266,
                            ...,
                        ],
                        "@search.score": 0.04972677677869797,
                        "@search.reranker_score": 3.1704962253570557,
                        "@search.highlights": None,
                        "@search.captions": None,
                    }
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

    def by_page(self):
        return self


class MockResponse:
    def __init__(self, text, status):
        self.text = text
        self.status = status

    async def text(self):
        return self._text

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self

    async def json(self):
        return json.loads(self.text)


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
