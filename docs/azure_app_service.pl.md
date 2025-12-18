# Czat RAG: Wdrażanie na Azure App Service

Ze względu na [ograniczenie](https://github.com/Azure/azure-dev/issues/2736) Azure Developer CLI (`azd`), może istnieć tylko jedna opcja hosta w pliku [azure.yaml](../azure.yaml).
Domyślnie używany jest `host: containerapp`, a `host: appservice` jest zakomentowany.

Aby wdrożyć do Azure App Service, wykonaj następujące kroki:

1. Zakomentuj `host: containerapp` i odkomentuj `host: appservice` w pliku [azure.yaml](../azure.yaml).

2. Zaloguj się na swoje konto Azure:

    ```bash
    azd auth login
    ```

3. Utwórz nowe środowisko `azd` do przechowywania parametrów wdrożenia:

    ```bash
    azd env new
    ```

    Wprowadź nazwę, która będzie używana dla grupy zasobów.
    To utworzy nowy folder w folderze `.azure` i ustawi go jako aktywne środowisko dla wszelkich przyszłych wywołań `azd`.

4. Ustaw cel wdrożenia na `appservice`:

    ```bash
    azd env set DEPLOYMENT_TARGET appservice
    ```

5. (Opcjonalnie) To jest moment, w którym możesz dostosować wdrożenie, ustawiając inne zmienne środowiskowe `azd`, aby [użyć istniejących zasobów](deploy_existing.md) *(angielski)*, [włączyć opcjonalne funkcje (takie jak uwierzytelnianie lub wizja)](deploy_features.md) *(angielski)* lub [wdrożyć do darmowych warstw](deploy_lowcost.md) *(angielski)*.
6. Aprowizuj zasoby i wdróż kod:

    ```bash
    azd up
    ```

    To zaaprowizuje zasoby Azure i wdroży ten przykład do tych zasobów, w tym zbuduje indeks wyszukiwania na podstawie plików znajdujących się w folderze `./data`.

    **Ważne**: Należy pamiętać, że zasoby utworzone przez to polecenie będą generować natychmiastowe koszty, głównie z zasobu AI Search. Te zasoby mogą generować koszty, nawet jeśli przerwiecie polecenie, zanim zostanie w pełni wykonane. Możesz uruchomić `azd down` lub usunąć zasoby ręcznie, aby uniknąć niepotrzebnych wydatków.
