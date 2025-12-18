# Czat RAG: Udostępnianie środowisk wdrożeniowych

Jeśli wdrożyłeś już rozwiązanie czatu RAG, postępując zgodnie z krokami w [przewodniku wdrażania](../README.pl.md#wdrażanie), możesz chcieć udostępnić środowisko współpracownikowi.
Ty lub oni możecie wykonać następujące kroki:

1. Zainstaluj [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
1. Uruchom `azd init -t azure-search-openai-demo` lub sklonuj to repozytorium.
1. Uruchom `azd env refresh -e {nazwa środowiska}`
   Będą potrzebować nazwy środowiska azd, identyfikatora subskrypcji i lokalizacji, aby uruchomić to polecenie. Możesz znaleźć te wartości w swoim pliku `.azure/{nazwa env}/.env`. To wypełni plik `.env` ich środowiska azd wszystkimi ustawieniami potrzebnymi do uruchomienia aplikacji lokalnie.
1. Ustaw zmienną środowiskową `AZURE_PRINCIPAL_ID` albo w tym pliku `.env`, albo w aktywnej powłoce na ich identyfikator Azure, który mogą uzyskać za pomocą `az ad signed-in-user show`.
1. Uruchom `./scripts/roles.ps1` lub `./scripts/roles.sh`, aby przypisać wszystkie niezbędne role użytkownikowi. Jeśli nie mają niezbędnych uprawnień do tworzenia ról w subskrypcji, możesz potrzebować uruchomić ten skrypt za nich. Po uruchomieniu skryptu powinni być w stanie uruchomić aplikację lokalnie.
