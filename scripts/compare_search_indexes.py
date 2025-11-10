"""Compare documents across two Azure AI Search indexes using azd credentials."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.aio import SearchClient

from load_azd_env import load_azd_env

logger = logging.getLogger("scripts")

IndexKey = tuple[str | None, str | None]


@dataclass
class IndexComparisonResult:
    """Holds summary data for one index."""

    index_name: str
    total_documents: int
    keys: set[IndexKey]
    documents_by_key: dict[IndexKey, list[dict[str, Any]]] = field(default_factory=dict)


async def collect_index_documents(
    *, endpoint: str, credential: AsyncTokenCredential, index_name: str
) -> IndexComparisonResult:
    """Collect all documents grouped by (sourcefile, sourcepage) pairs for the specified index."""

    keys: set[IndexKey] = set()
    documents_by_key: dict[IndexKey, list[dict[str, Any]]] = {}
    total_documents = 0

    async with SearchClient(endpoint=endpoint, index_name=index_name, credential=credential) as client:
        results = await client.search(
            search_text="",
            select="*",
            include_total_count=True,
        )
        async for doc in results:
            document = cast(Mapping[str, Any], doc)
            total_documents += 1
            sourcefile = document.get("sourcefile")
            sourcepage = document.get("sourcepage")
            key = (sourcefile, sourcepage)
            keys.add(key)
            if key not in documents_by_key:
                documents_by_key[key] = []
            documents_by_key[key].append(dict(document))

    return IndexComparisonResult(
        index_name=index_name, total_documents=total_documents, keys=keys, documents_by_key=documents_by_key
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Compare documents across two Azure AI Search indexes using sourcefile/sourcepage pairs.",
    )
    parser.add_argument("first_index", help="Name of the first search index to compare.")
    parser.add_argument("second_index", help="Name of the second search index to compare.")
    return parser.parse_args()


def build_endpoint(service_name: str) -> str:
    """Return the full endpoint URL for the Azure AI Search service."""

    return f"https://{service_name}.search.windows.net"


async def compare_indexes(
    *, first_index: str, second_index: str, endpoint: str, credential: AsyncTokenCredential
) -> None:
    """Fetch documents from both indexes and report detailed field differences."""

    first_result, second_result = await asyncio.gather(
        collect_index_documents(endpoint=endpoint, credential=credential, index_name=first_index),
        collect_index_documents(endpoint=endpoint, credential=credential, index_name=second_index),
    )

    missing_from_second = first_result.keys - second_result.keys
    missing_from_first = second_result.keys - first_result.keys

    logger.info(
        "Index '%s': %d docs, %d unique source pairs",
        first_result.index_name,
        first_result.total_documents,
        len(first_result.keys),
    )
    logger.info(
        "Index '%s': %d docs, %d unique source pairs",
        second_result.index_name,
        second_result.total_documents,
        len(second_result.keys),
    )

    def format_missing(pairs: Iterable[IndexKey]) -> str:
        return "\n".join(
            f"  sourcefile={sourcefile or '<none>'}, sourcepage={sourcepage or '<none>'}"
            for sourcefile, sourcepage in sorted(pairs)
        )

    if missing_from_second:
        logger.warning(
            "Pairs present in '%s' but missing in '%s':\n%s",
            first_index,
            second_index,
            format_missing(missing_from_second),
        )
    if missing_from_first:
        logger.warning(
            "Pairs present in '%s' but missing in '%s':\n%s",
            second_index,
            first_index,
            format_missing(missing_from_first),
        )

    # Compare common keys for field differences
    common_keys = first_result.keys & second_result.keys
    if common_keys:
        logger.info("Comparing %d common source pairs for field differences...", len(common_keys))
        differences_found = False

        for key in sorted(common_keys):
            first_docs = first_result.documents_by_key[key]
            second_docs = second_result.documents_by_key[key]

            if len(first_docs) != len(second_docs):
                differences_found = True
                logger.warning("\n=== MISMATCH for sourcefile=%s, sourcepage=%s ===", key[0], key[1])
                logger.warning(
                    "  Document count: %s has %d chunks, %s has %d chunks",
                    first_index,
                    len(first_docs),
                    second_index,
                    len(second_docs),
                )

            # Compare field sets and values for each document pair
            for idx, (doc1, doc2) in enumerate(zip(first_docs, second_docs)):
                fields1 = set(doc1.keys())
                fields2 = set(doc2.keys())

                missing_fields_in_second = fields1 - fields2
                missing_fields_in_first = fields2 - fields1

                has_field_diff = missing_fields_in_second or missing_fields_in_first
                has_value_diff = False
                value_diffs: list[tuple[str, Any, Any]] = []
                embedding_diffs: list[tuple[str, int | None, int | None]] = []

                # Get common fields first
                common_fields = fields1 & fields2

                # Compare embedding fields separately (dimension only, not values)
                for field_name in sorted(common_fields):
                    if "embedding" in field_name.lower():
                        val1 = doc1[field_name]
                        val2 = doc2[field_name]
                        dim1 = len(val1) if isinstance(val1, list) else None
                        dim2 = len(val2) if isinstance(val2, list) else None
                        if dim1 != dim2:
                            embedding_diffs.append((field_name, dim1, dim2))

                # Compare values for common fields (excluding embeddings and large fields)
                for field_name in sorted(common_fields):
                    # Skip embedding fields and other large binary/array fields
                    if "embedding" in field_name.lower() or field_name.startswith("@search"):
                        continue

                    val1 = doc1[field_name]
                    val2 = doc2[field_name]

                    # Special handling for images field
                    if field_name == "images":
                        if isinstance(val1, list) and isinstance(val2, list):
                            if len(val1) != len(val2):
                                has_value_diff = True
                                value_diffs.append((field_name, val1, val2))
                            elif len(val1) > 0:
                                # Compare first image's non-embedding fields
                                img1_keys = set(val1[0].keys()) - {"embedding"}
                                img2_keys = set(val2[0].keys()) - {"embedding"}
                                if img1_keys != img2_keys:
                                    has_value_diff = True
                                    value_diffs.append((field_name, val1, val2))
                                # Check image embedding dimensions
                                for img_idx, (img1, img2) in enumerate(zip(val1, val2)):
                                    if "embedding" in img1 and "embedding" in img2:
                                        emb1 = img1["embedding"]
                                        emb2 = img2["embedding"]
                                        dim1 = len(emb1) if isinstance(emb1, list) else None
                                        dim2 = len(emb2) if isinstance(emb2, list) else None
                                        if dim1 != dim2:
                                            embedding_diffs.append((f"images[{img_idx}].embedding", dim1, dim2))
                        elif val1 != val2:
                            has_value_diff = True
                            value_diffs.append((field_name, val1, val2))
                    # Special handling for content field - normalize whitespace
                    elif field_name == "content":
                        normalized1 = " ".join(str(val1).split()) if val1 else ""
                        normalized2 = " ".join(str(val2).split()) if val2 else ""
                        if normalized1 != normalized2:
                            has_value_diff = True
                            value_diffs.append((field_name, val1, val2))
                    elif val1 != val2:
                        has_value_diff = True
                        value_diffs.append((field_name, val1, val2))

                if has_field_diff or has_value_diff or embedding_diffs:
                    differences_found = True
                    logger.warning(
                        "\n=== DIFFERENCE for sourcefile=%s, sourcepage=%s (chunk %d) ===", key[0], key[1], idx
                    )

                    if missing_fields_in_second:
                        logger.warning("  Fields only in %s: %s", first_index, sorted(missing_fields_in_second))
                    if missing_fields_in_first:
                        logger.warning("  Fields only in %s: %s", second_index, sorted(missing_fields_in_first))

                    if embedding_diffs:
                        for field_name, dim1, dim2 in embedding_diffs:
                            logger.warning("  Embedding field '%s' dimension mismatch:", field_name)
                            logger.warning("    %s: %s dimensions", first_index, dim1)
                            logger.warning("    %s: %s dimensions", second_index, dim2)

                    for field_name, val1, val2 in value_diffs:
                        logger.warning("  Field '%s':", field_name)
                        logger.warning("    %s: %s", first_index, _format_value(val1, field_name))
                        logger.warning("    %s: %s", second_index, _format_value(val2, field_name))

        if not differences_found:
            logger.info("No field differences found for common source pairs.")

    if not missing_from_first and not missing_from_second and not differences_found:
        logger.info("Indexes are identical.")


def _format_value(val: Any, field_name: str | None = None) -> str:
    """Format a field value for logging, truncating if necessary."""
    if val is None:
        return "<none>"
    if isinstance(val, str):
        return val[:200] + "..." if len(val) > 200 else val
    if isinstance(val, list):
        # Special formatting for images field
        if field_name == "images" and len(val) > 0 and isinstance(val[0], dict):
            img_keys = sorted(set(val[0].keys()) - {"embedding"})
            return f"[{len(val)} images with fields: {img_keys}]"
        return f"[{len(val)} items]" if len(val) > 5 else str(val)
    return str(val)


async def main() -> None:
    """Entry point for asynchronous execution."""

    args = parse_args()

    load_azd_env()

    service_name = os.getenv("AZURE_SEARCH_SERVICE")
    if not service_name:
        raise RuntimeError(
            "AZURE_SEARCH_SERVICE must be set. Run 'azd env get-values' or ensure azd environment is loaded."
        )

    endpoint = build_endpoint(service_name)

    tenant_id = os.getenv("AZURE_TENANT_ID")
    credential = AzureDeveloperCliCredential(tenant_id=tenant_id) if tenant_id else AzureDeveloperCliCredential()

    try:
        await compare_indexes(
            first_index=args.first_index,
            second_index=args.second_index,
            endpoint=endpoint,
            credential=credential,
        )
    finally:
        await credential.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.setLevel(logging.DEBUG)

    asyncio.run(main())
