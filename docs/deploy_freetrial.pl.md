# Czat RAG: Wdrażanie z konta bezpłatnej wersji próbnej

Jeśli właśnie utworzyłeś konto bezpłatnej wersji próbnej Azure i korzystasz z kredytów bezpłatnej wersji próbnej,
musisz wprowadzić kilka modyfikacji ze względu na ograniczenia konta bezpłatnej wersji próbnej.

Postępuj zgodnie z tymi instrukcjami *przed* uruchomieniem `azd up`.

## Dostosowanie do niskich przydziałów OpenAI

Konta bezpłatnej wersji próbnej obecnie otrzymują maksymalnie 1K TPM (tokenów na minutę), podczas gdy nasze szablony Bicep próbują przydzielić 30K TPM.

Aby zmniejszyć przydział TPM, uruchom te polecenia:

```shell
azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT_CAPACITY 1
azd env set AZURE_OPENAI_EMB_DEPLOYMENT_CAPACITY 1
```

Alternatywnie, jeśli masz konto OpenAI.com, możesz użyć go zamiast tego:

```shell
azd env set OPENAI_HOST openai
azd env set OPENAI_ORGANIZATION {Twoja organizacja OpenAI}
azd env set OPENAI_API_KEY {Twój klucz API OpenAI}
```

## Dostosowanie do ograniczeń Azure Container Apps

Domyślnie ten projekt wdraża do Azure Container Apps, używając procesu zdalnej kompilacji, który buduje obraz Docker w chmurze.
Niestety, konta bezpłatnej wersji próbnej nie mogą używać tego procesu zdalnej kompilacji.

Masz dwie opcje:

1. Zakomentuj lub usuń `remoteBuild: true` w `azure.yaml` i upewnij się, że masz Docker zainstalowany w swoim środowisku.

2. Wdróż używając App Service zamiast tego:

    * Zakomentuj `host: containerapp` i odkomentuj `host: appservice` w pliku [azure.yaml](../azure.yaml).
    * Ustaw cel wdrożenia na `appservice`:

        ```shell
        azd env set DEPLOYMENT_TARGET appservice
        ```
