from abc import ABC
from typing import Any, Optional

from core.authentication import AuthenticationHelper


class Approach(ABC):
    def build_filter(self, overrides: dict[str, Any], auth_claims: dict[str, Any]) -> Optional[str]:
        exclude_category = overrides.get("exclude_category") or None
        security_filter = AuthenticationHelper.build_security_filters(overrides, auth_claims)
        filters = []
        if exclude_category:
            filters.append("category ne '{}'".format(exclude_category.replace("'", "''")))
        if security_filter:
            filters.append(security_filter)
        return None if len(filters) == 0 else " and ".join(filters)
