# Czat RAG: Alternatywne przykłady czatu RAG

Istnieje coraz większa liczba sposobów budowania aplikacji czatu RAG.

* [Najbardziej podobne do tego repozytorium](#najbardziej-podobne-do-tego-repozytorium)
* [azurechat](#azurechat)
* [sample-app-aoai-chatGPT](#sample-app-aoai-chatgpt)

## Najbardziej podobne do tego repozytorium

Zainspirowane tym repozytorium, istnieją podobne aplikacje czatu RAG dla innych języków:

* [**JavaScript**](https://aka.ms/azai/js/code)
* [**.NET**](https://aka.ms/azai/net/code)
* [**Java**](https://aka.ms/azai/java/code)

Nie wszystkie obsługują te same funkcje co to repozytorium, ale stanowią dobry punkt wyjścia do budowania aplikacji czatu RAG w preferowanym języku.

## azurechat

Innym popularnym przykładem jest Azure Chat Solution Accelerator:
[https://github.com/microsoft/azurechat](https://github.com/microsoft/azurechat)

AzureChat wdraża prywatną aplikację czatu z interfejsem podobnym do ChatGPT na Azure, z wbudowanymi możliwościami czatowania nad wewnętrznymi danymi i plikami oraz opcjonalnymi rozszerzeniami.

Kluczowe różnice w porównaniu z tym repozytorium:

* **Stos technologiczny**: AzureChat używa pełnego stosu JavaScript/TypeScript z backendem Node.js; to repozytorium używa Pythona (Quart) do usług backendowych.
* **Nacisk na przypadek użycia**: AzureChat oferuje więcej funkcji związanych z personalizacją użytkownika, podczas gdy to repozytorium oferuje więcej funkcji potrzebnych w scenariuszach korporacyjnych, takich jak ACL danych i ocena.

Porównanie funkcji:

| Funkcja | azure-search-openai-demo | azurechat |
| --- | --- | --- |
| Obsługa wektorów | ✅ Tak | ✅ Tak |
| Pozyskiwanie danych | ✅ Tak ([Wiele formatów](data_ingestion.md#supported-document-formats)) | ✅ Tak |
| Trwała historia czatu | ✅ Tak | ✅ Tak |
| Multimodalne | ✅ Tak | ✅ Tak |
| Wejście/wyjście głosowe | ✅ Tak | ✅ Tak |
| Przesyłanie plików | ✅ Tak | ✅ Tak |
| Uwierzytelnianie + ACL | ✅ Tak (Zorientowane na przedsiębiorstwa) | ✅ Tak (Zorientowane na osoby) |
| Kontrola dostępu | ✅ Tak (Na poziomie dokumentu) | ❌ Ograniczone |

Porównanie technologii:

| Technologia | azure-search-openai-demo | azurechat |
| --- | --- | --- |
| Frontend | React (TypeScript) | React (TypeScript) |
| Backend | Python (Quart) | Node.js (TypeScript) |
| Baza danych | Azure AI Search | Azure AI Search |
| Wdrożenie | Azure Developer CLI (azd) | Azure Developer CLI (azd) |

## sample-app-aoai-chatGPT

Innym popularnym repozytorium dla tego przypadku użycia jest:
[https://github.com/Microsoft/sample-app-aoai-chatGPT/](https://github.com/Microsoft/sample-app-aoai-chatGPT/)

To repozytorium jest przeznaczone dla klientów korzystających z Azure OpenAI studio i Azure Portal do konfiguracji. Zawiera również obsługę `azd` dla osób, które chcą wdrożyć je całkowicie od podstaw.

Główne różnice:

* To repozytorium zawiera wiele podejść RAG (retrieval-augmented generation), które łączą wyniki wielu wywołań API (do Azure OpenAI i ACS) na różne sposoby. Drugie repozytorium używa tylko wbudowanej opcji źródeł danych dla API ChatCompletions, która używa podejścia RAG w określonym indeksie ACS. To powinno działać w większości przypadków, ale jeśli potrzebujesz większej elastyczności, ten przykład może być lepszą opcją.
* To repozytorium jest również nieco bardziej eksperymentalne w innych aspektach, ponieważ nie jest powiązane z Azure OpenAI Studio jak drugie repozytorium.

Porównanie funkcji:

| Funkcja | azure-search-openai-demo | sample-app-aoai-chatGPT |
| --- | --- | --- |
| Obsługa wektorów | ✅ Tak | ✅ Tak |
| Pozyskiwanie danych | ✅ Tak ([Wiele formatów](data_ingestion.md#supported-document-formats)) | ✅ Tak ([Wiele formatów](https://learn.microsoft.com/azure/ai-services/openai/concepts/use-your-data?tabs=ai-search#data-formats-and-file-types)) |
| Trwała historia czatu | ✅ Tak | ✅ Tak |
| Opinie użytkowników | ❌ Nie | ✅ Tak |
| GPT-4-vision |  ✅ Tak | ❌ Nie |
| Uwierzytelnianie + ACL |  ✅ Tak | ✅ Tak |
| Przesyłanie przez użytkownika |  ✅ Tak | ❌ Nie |
| Wejście/wyjście mowy | ✅ Tak | ❌ Nie |

Porównanie technologii:

| Technologia | azure-search-openai-demo | sample-app-aoai-chatGPT |
| --- | --- | --- |
| Frontend | React | React |
| Backend | Python (Quart) | Python (Quart) |
| Baza danych wektorów | Azure AI Search | Azure AI Search, CosmosDB Mongo vCore, ElasticSearch, Pinecone, AzureML |
| Wdrożenie | Azure Developer CLI (azd) | Azure Portal, az, azd |
