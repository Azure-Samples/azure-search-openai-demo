# Czat RAG: Wdrażanie na Azure Container Apps

Ze względu na [ograniczenie](https://github.com/Azure/azure-dev/issues/2736) Azure Developer CLI (`azd`), może istnieć tylko jedna opcja hosta w pliku [azure.yaml](../azure.yaml).
Domyślnie używany jest `host: containerapp`, a `host: appservice` jest zakomentowany.

Jednak jeśli masz starszą wersję repozytorium, możesz potrzebować wykonać te kroki, aby wdrożyć do Container Apps, lub możesz pozostać przy Azure App Service.

Aby wdrożyć do Azure Container Apps, wykonaj następujące kroki:

1. Zakomentuj `host: appservice` i odkomentuj `host: containerapp` w pliku [azure.yaml](../azure.yaml).

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

4. Ustaw cel wdrożenia na `containerapps`:

    ```bash
    azd env set DEPLOYMENT_TARGET containerapps
    ```

5. (Opcjonalnie) To jest moment, w którym możesz dostosować wdrożenie, ustawiając inne zmienne środowiskowe `azd`, aby [użyć istniejących zasobów](docs/deploy_existing.md) *(angielski)*, [włączyć opcjonalne funkcje (takie jak uwierzytelnianie lub wizja)](docs/deploy_features.md) *(angielski)* lub [wdrożyć do darmowych warstw](docs/deploy_lowcost.md) *(angielski)*.
6. Aprowizuj zasoby i wdróż kod:

    ```bash
    azd up
    ```

    To zaaprowizuje zasoby Azure i wdroży ten przykład do tych zasobów, w tym zbuduje indeks wyszukiwania na podstawie plików znajdujących się w folderze `./data`.

    **Ważne**: Należy pamiętać, że zasoby utworzone przez to polecenie będą generować natychmiastowe koszty, głównie z zasobu AI Search. Te zasoby mogą generować koszty, nawet jeśli przerwiecie polecenie, zanim zostanie w pełni wykonane. Możesz uruchomić `azd down` lub usunąć zasoby ręcznie, aby uniknąć niepotrzebnych wydatków.

## Dostosowywanie profilu obciążenia

Domyślny profil obciążenia to Consumption. Jeśli chcesz użyć dedykowanego profilu obciążenia, takiego jak D4, uruchom:

```bash
azd env set AZURE_CONTAINER_APPS_WORKLOAD_PROFILE D4
```

Pełna lista profili obciążenia znajduje się w [dokumentacji profili obciążenia](https://learn.microsoft.com/azure/container-apps/workload-profiles-overview#profile-types).
Należy pamiętać, że dedykowane profile obciążenia mają inny model rozliczeniowy niż plan Consumption. Sprawdź [dokumentację rozliczeń](https://learn.microsoft.com/azure/container-apps/billing) po szczegóły.

## Prywatne punkty końcowe

Prywatne punkty końcowe są nadal w prywatnej wersji zapoznawczej dla Azure Container Apps i nie są obecnie obsługiwane.
