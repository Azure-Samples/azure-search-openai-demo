import asyncio
from typing import Any, AsyncGenerator, Optional, TypeVar

from core.authentication import AuthenticationHelper

T = TypeVar('T')

class Utils:
    def build_filter(overrides: dict[str, Any], auth_claims: dict[str, Any]) -> Optional[str]:
        exclude_category = overrides.get("exclude_category") or None
        security_filter = AuthenticationHelper.build_security_filters(overrides, auth_claims)
        filters = []
        if exclude_category:
            filters.append("category ne '{}'".format(exclude_category.replace("'", "''")))
        if security_filter:
            filters.append(security_filter)
        return None if len(filters) == 0 else " and ".join(filters)

    async def merge_generators(generator_list):
        for generator in generator_list:
            async for item in generator:
                if not (item is None):
                    yield item
    
    async def single_item_generator(item: T) -> AsyncGenerator[T, None]:
        yield item