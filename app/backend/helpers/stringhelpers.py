import re

def clean_string(input_string):
    # Convert the string to lowercase
    input_string = input_string.lower()

    # Use a regular expression to remove special characters except '_' and spaces
    cleaned_string = re.sub(r'[^a-z0-9_ -]', '', input_string)

    return cleaned_string