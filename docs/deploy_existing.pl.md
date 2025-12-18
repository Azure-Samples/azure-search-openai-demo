
# Czat RAG: Wdrażanie z istniejącymi zasobami Azure

Jeśli masz już istniejące zasoby Azure lub chcesz określić dokładną nazwę nowego zasobu Azure, możesz to zrobić, ustawiając wartości środowiskowe `azd`.
Powinieneś ustawić te wartości przed uruchomieniem `azd up`. Po ich ustawieniu wróć do [kroków wdrażania](../README.pl.md#wdrażanie).

* [Grupa zasobów](#grupa-zasobów)
* [Zasób OpenAI](#zasób-openai)
* [Zasób Azure AI Search](#zasób-azure-ai-search)
* [Zasoby Azure App Service Plan i App Service](#zasoby-azure-app-service-plan-i-app-service)
* [Zasoby Azure AI Vision](#zasoby-azure-ai-vision)
* [Zasób Azure Document Intelligence](#zasób-azure-document-intelligence)
* [Zasób Azure Speech](#zasób-azure-speech)
* [Inne zasoby Azure](#inne-zasoby-azure)

## Grupa zasobów

1. Uruchom `azd env set AZURE_RESOURCE_GROUP {Nazwa istniejącej grupy zasobów}`
1. Uruchom `azd env set AZURE_LOCATION {Lokalizacja istniejącej grupy zasobów}`

## Zasób OpenAI

### Azure OpenAI

1. Uruchom `azd env set AZURE_OPENAI_SERVICE {Nazwa istniejącej usługi OpenAI}`
1. Uruchom `azd env set AZURE_OPENAI_RESOURCE_GROUP {Nazwa istniejącej grupy zasobów, do której aprowizowana jest usługa OpenAI}`
1. Uruchom `azd env set AZURE_OPENAI_LOCATION {Lokalizacja istniejącej usługi OpenAI}`
1. Uruchom `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT {Nazwa istniejącego wdrożenia czatu}`. Potrzebne tylko, jeśli nazwa wdrożenia czatu nie jest domyślną 'gpt-4.1-mini'.
1. Uruchom `azd env set AZURE_OPENAI_CHATGPT_MODEL {Nazwa modelu istniejącego wdrożenia czatu}`. Potrzebne tylko, jeśli model czatu nie jest domyślnym 'gpt-4.1-mini'.
1. Uruchom `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_VERSION {Ciąg wersji dla istniejącego wdrożenia czatu}`. Potrzebne tylko, jeśli wersja modelu wdrożenia czatu nie jest domyślną '2024-07-18'. Zdecydowanie musisz to zmienić, jeśli zmieniłeś model.
1. Uruchom `azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_SKU {Nazwa SKU dla istniejącego wdrożenia czatu}`. Potrzebne tylko, jeśli SKU wdrożenia czatu nie jest domyślnym 'Standard', na przykład jeśli jest 'GlobalStandard'.
1. Uruchom `azd env set AZURE_OPENAI_EMB_DEPLOYMENT {Nazwa istniejącego wdrożenia osadzania}`. Potrzebne tylko, jeśli wdrożenie osadzania nie jest domyślnym 'embedding'.
1. Uruchom `azd env set AZURE_OPENAI_EMB_MODEL_NAME {Nazwa modelu istniejącego wdrożenia osadzania}`. Potrzebne tylko, jeśli model osadzania nie jest domyślnym 'text-embedding-3-large'.
1. Uruchom `azd env set AZURE_OPENAI_EMB_DIMENSIONS {Wymiary dla istniejącego wdrożenia osadzania}`. Potrzebne tylko, jeśli model osadzania nie jest domyślnym 'text-embedding-3-large'.
1. Uruchom `azd env set AZURE_OPENAI_EMB_DEPLOYMENT_VERSION {Ciąg wersji dla istniejącego wdrożenia osadzania}`. Jeśli wdrożenie osadzania to jeden z modeli 'text-embedding-3', ustaw to na liczbę 1.
1. Ten projekt *nie* używa kluczy podczas uwierzytelniania do Azure OpenAI. Jednak jeśli Twoja usługa Azure OpenAI musi mieć włączony dostęp za pomocą klucza z jakiegoś powodu (np. do użytku przez inne projekty), uruchom `azd env set AZURE_OPENAI_DISABLE_KEYS false`. Wartość domyślna to `true`, więc powinieneś uruchomić polecenie tylko wtedy, gdy potrzebujesz dostępu za pomocą klucza.

Gdy uruchomisz `azd up` później i zostaniesz poproszony o wybranie wartości dla `openAiResourceGroupLocation`, upewnij się, że wybierzesz tę samą lokalizację co istniejąca grupa zasobów OpenAI.

### Openai.com OpenAI

1. Uruchom `azd env set OPENAI_HOST openai`
2. Uruchom `azd env set OPENAI_ORGANIZATION {Twoja organizacja OpenAI}`
3. Uruchom `azd env set OPENAI_API_KEY {Twój klucz API OpenAI}`
4. Uruchom `azd up`

Możesz pobrać swój klucz OpenAI, sprawdzając [swoją stronę użytkownika](https://platform.openai.com/account/api-keys) i swoją organizację, przechodząc do [strony organizacji](https://platform.openai.com/account/org-settings).
Dowiedz się więcej o tworzeniu bezpłatnej wersji próbnej OpenAI pod [tym linkiem](https://openai.com/pricing).
*Nie* sprawdzaj swojego klucza w kontroli źródła.

Gdy uruchomisz `azd up` później i zostaniesz poproszony o wybranie wartości dla `openAiResourceGroupLocation`, możesz wybrać dowolną lokalizację, ponieważ nie będzie używana.

## Zasób Azure AI Search

1. Uruchom `azd env set AZURE_SEARCH_SERVICE {Nazwa istniejącej usługi Azure AI Search}`
1. Uruchom `azd env set AZURE_SEARCH_SERVICE_RESOURCE_GROUP {Nazwa istniejącej grupy zasobów z usługą ACS}`
1. Jeśli ta grupa zasobów znajduje się w innej lokalizacji niż ta, którą wybierzesz dla kroku `azd up`,
  uruchom `azd env set AZURE_SEARCH_SERVICE_LOCATION {Lokalizacja istniejącej usługi}`
1. Jeśli SKU usługi wyszukiwania nie jest standardowe, uruchom `azd env set AZURE_SEARCH_SERVICE_SKU {Nazwa SKU}`. Jeśli określisz warstwę darmową, Twoja aplikacja nie będzie już mogła używać rankera semantycznego. Należy pamiętać, że [SKU wyszukiwania nie można zmienić](https://learn.microsoft.com/azure/search/search-sku-tier#tier-upgrade-or-downgrade). ([Zobacz inne możliwe wartości SKU](https://learn.microsoft.com/azure/templates/microsoft.search/searchservices?pivots=deployment-language-bicep#sku))
1. Jeśli masz istniejący indeks skonfigurowany ze wszystkimi oczekiwanymi polami, uruchom `azd env set AZURE_SEARCH_INDEX {Nazwa istniejącego indeksu}`. W przeciwnym razie polecenie `azd up` utworzy nowy indeks.

Możesz również dostosować usługę wyszukiwania (nową lub istniejącą) do wyszukiwań w języku innym niż angielski:

1. Aby skonfigurować język zapytania wyszukiwania na wartość inną niż "en-US", uruchom `azd env set AZURE_SEARCH_QUERY_LANGUAGE {Nazwa języka zapytania}`. ([Zobacz inne możliwe wartości](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage))
1. Aby wyłączyć sprawdzanie pisowni, uruchom `azd env set AZURE_SEARCH_QUERY_SPELLER none`. Zapoznaj się z [tą tabelą](https://learn.microsoft.com/rest/api/searchservice/preview-api/search-documents#queryLanguage), aby ustalić, czy sprawdzanie pisowni jest obsługiwane dla Twojego języka zapytania.
1. Aby skonfigurować nazwę analizatora do użycia dla przeszukiwanego pola tekstowego na wartość inną niż "en.microsoft", uruchom `azd env set AZURE_SEARCH_ANALYZER_NAME {Nazwa analizatora}`. ([Zobacz inne możliwe wartości](https://learn.microsoft.com/dotnet/api/microsoft.azure.search.models.field.analyzer?view=azure-dotnet-legacy&viewFallbackFrom=azure-dotnet))

## Zasoby Azure App Service Plan i App Service

1. Uruchom `azd env set AZURE_APP_SERVICE_PLAN {Nazwa istniejącego Azure App Service Plan}`
1. Uruchom `azd env set AZURE_APP_SERVICE {Nazwa istniejącego Azure App Service}`.
1. Uruchom `azd env set AZURE_APP_SERVICE_SKU {SKU Azure App Service, domyślnie B1}`.

## Zasoby Azure AI Vision

1. Uruchom `azd env set AZURE_VISION_SERVICE {Nazwa istniejącej usługi Azure AI Vision}`
1. Uruchom `azd env set AZURE_VISION_RESOURCE_GROUP {Nazwa istniejącej grupy zasobów Azure AI Vision}`
1. Uruchom `azd env set AZURE_VISION_LOCATION {Nazwa istniejącej lokalizacji Azure AI Vision}`
1. Uruchom `azd env set AZURE_VISION_SKU {SKU usługi Azure AI Vision, domyślnie F0}`

## Zasób Azure Document Intelligence

Aby obsługiwać analizę wielu formatów dokumentów, to repozytorium używa wersji podglądowej Azure Document Intelligence (dawniej Form Recognizer), która jest dostępna tylko w [ograniczonych regionach](https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-layout).
Jeśli Twój istniejący zasób znajduje się w jednym z tych regionów, możesz go ponownie użyć, ustawiając następujące zmienne środowiskowe:

1. Uruchom `azd env set AZURE_DOCUMENTINTELLIGENCE_SERVICE {Nazwa istniejącej usługi Azure AI Document Intelligence}`
1. Uruchom `azd env set AZURE_DOCUMENTINTELLIGENCE_LOCATION {Lokalizacja istniejącej usługi}`
1. Uruchom `azd env set AZURE_DOCUMENTINTELLIGENCE_RESOURCE_GROUP {Nazwa grupy zasobów z istniejącą usługą, domyślnie główna grupa zasobów}`
1. Uruchom `azd env set AZURE_DOCUMENTINTELLIGENCE_SKU {SKU istniejącej usługi, domyślnie S0}`

## Zasób Azure Speech

1. Uruchom `azd env set AZURE_SPEECH_SERVICE {Nazwa istniejącej usługi Azure Speech}`
1. Uruchom `azd env set AZURE_SPEECH_SERVICE_RESOURCE_GROUP {Nazwa istniejącej grupy zasobów z usługą mowy}`
1. Jeśli ta grupa zasobów znajduje się w innej lokalizacji niż ta, którą wybierzesz dla kroku `azd up`,
  uruchom `azd env set AZURE_SPEECH_SERVICE_LOCATION {Lokalizacja istniejącej usługi}`
1. Jeśli SKU usługi mowy nie jest "S0", uruchom `azd env set AZURE_SPEECH_SERVICE_SKU {Nazwa SKU}`.

## Inne zasoby Azure

Możesz również używać istniejących kont Azure AI Storage. Zobacz `./infra/main.parameters.json` po listę zmiennych środowiskowych do przekazania do `azd env set`, aby skonfigurować te istniejące zasoby.
