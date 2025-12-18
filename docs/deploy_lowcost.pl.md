# Czat RAG: Wdrażanie z minimalnymi kosztami

Ta aplikacja czatu AI RAG została zaprojektowana w celu łatwego wdrożenia przy użyciu Azure Developer CLI, która aprowizuje infrastrukturę zgodnie z plikami Bicep w folderze `infra`. Te pliki opisują każdy z potrzebnych zasobów Azure i konfigurują ich SKU (warstwę cenową) oraz inne parametry. Wiele usług Azure oferuje warstwę darmową, ale pliki infrastruktury w tym projekcie *nie* domyślnie używają warstwy darmowej, ponieważ często istnieją ograniczenia w tej warstwie.

Jednak jeśli Twoim celem jest minimalizacja kosztów podczas prototypowania aplikacji, postępuj zgodnie z poniższymi krokami *przed* uruchomieniem `azd up`. Po przejściu przez te kroki wróć do [kroków wdrażania](../README.pl.md#wdrażanie).

[📺 Transmisja na żywo: Wdrażanie z darmowego konta](https://www.youtube.com/watch?v=nlIyos0RXHw)

1. Zaloguj się na swoje konto Azure za pomocą Azure Developer CLI:

    ```shell
    azd auth login
    ```

1. Utwórz nowe środowisko azd dla darmowej grupy zasobów:

    ```shell
    azd env new
    ```

    Wprowadź nazwę, która będzie używana dla grupy zasobów.
    To utworzy nowy folder w folderze `.azure` i ustawi go jako aktywne środowisko dla wszelkich przyszłych wywołań `azd`.

1. Przełącz się z Azure Container Apps na darmową warstwę Azure App Service:

    Azure Container Apps ma model cenowy oparty na zużyciu, który jest bardzo niskokosztowy, ale nie jest darmowy, plus Azure Container Registry kosztuje niewielką kwotę każdego miesiąca.

    Aby wdrożyć do App Service zamiast tego:

    * Zakomentuj `host: containerapp` i odkomentuj `host: appservice` w pliku [azure.yaml](../azure.yaml).
    * Ustaw cel wdrożenia na `appservice`:

        ```shell
        azd env set DEPLOYMENT_TARGET appservice
        ```

    * Ustaw SKU App Service na warstwę darmową:

        ```shell
        azd env set AZURE_APP_SERVICE_SKU F1
        ```

    Ograniczenie: Możesz mieć tylko określoną liczbę darmowych instancji App Service na region. Jeśli przekroczyłeś limit w regionie, otrzymasz błąd podczas etapu aprowizacji. Jeśli tak się stanie, możesz uruchomić `azd down`, a następnie `azd env new`, aby utworzyć nowe środowisko z nowym regionem.

1. Użyj darmowej warstwy Azure AI Search:

    ```shell
    azd env set AZURE_SEARCH_SERVICE_SKU free
    ```

    Ograniczenia:
    1. Możesz mieć tylko jedną darmową usługę wyszukiwania we wszystkich regionach.
    Jeśli masz już jedną, albo usuń tę usługę, albo postępuj zgodnie z instrukcjami, aby
    użyć ponownie swojej [istniejącej usługi wyszukiwania](../README.pl.md#existing-azure-ai-search-resource).
    2. Warstwa darmowa nie obsługuje rankera semantycznego, więc interfejs aplikacji nie będzie już wyświetlał
    opcji użycia rankera semantycznego. Należy pamiętać, że zazwyczaj spowoduje to [zmniejszoną trafność wyszukiwania](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/azure-ai-search-outperforming-vector-search-with-hybrid-retrieval-and-ranking-ca/3929167).

1. Użyj darmowej warstwy Azure Document Intelligence (używanej w analizie plików):

    ```shell
    azd env set AZURE_DOCUMENTINTELLIGENCE_SKU F0
    ```

    **Ograniczenie dla plików PDF:**

      Warstwa darmowa zeskanuje tylko pierwsze dwie strony każdego pliku PDF.
      W naszych przykładowych dokumentach te pierwsze dwie strony to tylko strony tytułowe,
      więc nie będziesz mógł otrzymać odpowiedzi z dokumentów.
      Możesz albo użyć własnych dokumentów, które mają tylko 2 strony,
      albo możesz użyć lokalnego pakietu Python do parsowania PDF, ustawiając:

      ```shell
      azd env set USE_LOCAL_PDF_PARSER true
      ```

    **Ograniczenie dla plików HTML:**

      Warstwa darmowa zeskanuje tylko pierwsze dwie strony każdego pliku HTML.
      Więc możesz nie otrzymać bardzo dokładnych odpowiedzi z plików.
      Możesz albo użyć własnych plików, które mają tylko 2 strony,
      albo możesz użyć lokalnego pakietu Python do parsowania HTML, ustawiając:

      ```shell
      azd env set USE_LOCAL_HTML_PARSER true
      ```

1. Użyj darmowej warstwy Azure Cosmos DB:

    ```shell
    azd env set AZURE_COSMOSDB_SKU free
    ```

    Ograniczenie: Możesz mieć tylko jedno darmowe konto Cosmos DB. Aby utrzymać swoje konto wolne od opłat, upewnij się, że nie przekraczasz limitów warstwy darmowej. Po więcej informacji zobacz [warstwa darmowa Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/free-tier).

1. ⚠️ Ten krok jest obecnie możliwy tylko w przypadku wdrażania do App Service ([zobacz problem 2281](https://github.com/Azure-Samples/azure-search-openai-demo/issues/2281)):

    Wyłącz Azure Monitor (Application Insights):

    ```shell
    azd env set AZURE_USE_APPLICATION_INSIGHTS false
    ```

    Application Insights jest już dość niedrogie, więc wyłączenie tego może nie być warte zaoszczędzonych kosztów,
    ale jest to opcja dla tych, którzy chcą zminimalizować koszty.

1. Użyj OpenAI.com zamiast Azure OpenAI: Nie powinno to być konieczne, ponieważ koszty są takie same dla obu usług, ale możesz potrzebować tego kroku, jeśli Twoje konto nie ma dostępu do Azure OpenAI z jakiegoś powodu.

    ```shell
    azd env set OPENAI_HOST openai
    azd env set OPENAI_ORGANIZATION {Twoja organizacja OpenAI}
    azd env set OPENAI_API_KEY {Twój klucz API OpenAI}
    ```

    Zarówno konta Azure OpenAI, jak i openai.com OpenAI będą generować koszty na podstawie używanych tokenów,
    ale koszty są dość niskie dla ilości przykładowych danych (mniej niż $10).

1. Wyłącz wyszukiwanie wektorowe:

    ```shell
    azd env set USE_VECTORS false
    ```

    Domyślnie aplikacja oblicza osadzenia wektorowe dla dokumentów podczas fazy pozyskiwania danych,
    a następnie oblicza osadzenie wektorowe dla pytań użytkowników zadawanych w aplikacji.
    Te obliczenia wymagają modelu osadzania, który generuje koszty za użyte tokeny. Koszty są dość niskie,
    więc korzyści z wyszukiwania wektorowego zazwyczaj przeważają nad kosztami, ale możliwe jest wyłączenie obsługi wektorów.
    Jeśli to zrobisz, aplikacja powróci do wyszukiwania słów kluczowych, które jest mniej dokładne.

1. Po dokonaniu pożądanych dostosowań, postępuj zgodnie z krokami w README [aby uruchomić `azd up`](../README.pl.md#wdrażanie). Zalecamy używanie "eastus" jako regionu ze względów dostępności.

## Zmniejszanie kosztów lokalnie

Aby zaoszczędzić koszty podczas lokalnego rozwoju, możesz użyć modelu kompatybilnego z OpenAI.
Postępuj zgodnie z krokami w [przewodniku lokalnego rozwoju](localdev.md#using-a-local-openai-compatible-api) *(angielski)*.
