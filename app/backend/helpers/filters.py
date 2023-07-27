from helpers.stringhelpers import clean_string

class Filter:
    def __init__(self, productname_field: str, familytype_field: str,
                 state_field: str, lifecycle_field: str):
        self.productname_field = productname_field
        self.familytype_field = familytype_field
        self.state_field = state_field
        self.lifecycle_field = lifecycle_field

    def is_null_or_empty(self, input_string):
        return input_string is None or len(input_string) == 0

    def get_filter_statement(self, field, operator, value):
        if value is not None:
            return f"{field} {operator} '{value}'"
        return ""
    
    def create_filter_string(self, filters, exclude_category):
        filter_list = []
        filter_list.append(self.get_filter_statement("category", "ne", exclude_category) if not exclude_category is None else "")
        filter_list.append(self.get_filter_statement(self.productname_field, "eq", clean_string(filters["product_name"])) if "product_name" in filters and not self.is_null_or_empty(filters["product_name"]) else "")
        filter_list.append(self.get_filter_statement(self.familytype_field, "eq", clean_string(filters["family_type"])) if "family_type" in filters and not self.is_null_or_empty(filters["family_type"]) else "")
        filter_list.append(self.get_filter_statement(self.state_field, "eq", clean_string(filters["state_type"])) if "state_type" in filters and not self.is_null_or_empty(filters["state_type"]) else "")
        filter_list.append(self.get_filter_statement(self.lifecycle_field, "eq", filters["lifecycle"]) if "lifecycle" in filters and not self.is_null_or_empty(filters["lifecycle"]) else "")

        # Remove any empty filter statements
        filter_list = [filter_item for filter_item in filter_list if filter_item]

        filter_string = " and ".join(filter_list)
        return filter_string