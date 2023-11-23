#!/bin/bash
Run azd env set AZURE_RESOURCE_GROUP {Name of existing resource group}
Run azd env set AZURE_LOCATION {Location of existing resource group}
azd env set OPENAI_HOST openai
azd env set OPENAI_ORGANIZATION {Your OpenAI organization}
azd env set OPENAI_API_KEY {Your OpenAI API key}
