# Czat RAG: Wdrażanie z Azure Developer CLI

Ten przewodnik zawiera zaawansowane tematy, które nie są konieczne do podstawowego wdrożenia. Jeśli jesteś nowy w projekcie, zapoznaj się z głównym [README](../README.pl.md#wdrażanie) po instrukcje dotyczące wdrażania projektu.

[📺 Oglądaj: Wdrażanie aplikacji czatu](https://www.youtube.com/watch?v=mDFZdmn7nhk)

* [Jak działa `azd up`?](#jak-działa-azd-up)
* [Konfigurowanie ciągłego wdrażania](#konfigurowanie-ciągłego-wdrażania)
  * [GitHub actions](#github-actions)
  * [Azure DevOps](#azure-devops)

## Jak działa `azd up`?

Polecenie `azd up` pochodzi z [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview) i zajmuje się zarówno aprowizowaniem zasobów Azure, jak i wdrażaniem kodu do wybranych hostów Azure.

Polecenie `azd up` używa pliku `azure.yaml` w połączeniu z plikami infrastruktury jako kodu `.bicep` w folderze `infra/`. Plik `azure.yaml` dla tego projektu deklaruje kilka "hooków" dla kroku prepackage i kroków postprovision. Polecenie `up` najpierw uruchamia hook `prepackage`, który instaluje zależności Node i buduje pliki JavaScript oparte na React.JS. Następnie pakuje cały kod (zarówno frontend, jak i backend) do pliku zip, który zostanie wdrożony później.

Następnie aprowizuje zasoby na podstawie `main.bicep` i `main.parameters.json`. W tym momencie, ponieważ nie ma domyślnej wartości dla lokalizacji zasobu OpenAI, poprosi Cię o wybranie lokalizacji z krótkiej listy dostępnych regionów. Następnie wyśle żądania do Azure, aby aprowizować wszystkie wymagane zasoby. Po aprowizowaniu wszystkiego uruchamia hook `postprovision`, aby przetworzyć lokalne dane i dodać je do indeksu Azure AI Search.

Na koniec sprawdza `azure.yaml`, aby określić hosta Azure i przesyła plik zip do Azure App Service. Polecenie `azd up` jest teraz zakończone, ale może zająć kolejne 5-10 minut, zanim aplikacja App Service będzie w pełni dostępna i działająca, szczególnie w przypadku początkowego wdrożenia.

Powiązane polecenia to `azd provision` tylko do aprowizacji (jeśli pliki infra się zmieniają) i `azd deploy` tylko do wdrażania zaktualizowanego kodu aplikacji.

## Konfigurowanie ciągłego wdrażania

To repozytorium zawiera zarówno przepływ pracy GitHub Actions, jak i potok Azure DevOps do ciągłego wdrażania z każdym push do `main`. Przepływ pracy GitHub Actions jest domyślny, ale możesz przełączyć się na Azure DevOps, jeśli wolisz.

Więcej szczegółów dostępnych jest w [Learn.com: Konfigurowanie potoku i push aktualizacji](https://learn.microsoft.com/azure/developer/azure-developer-cli/configure-devops-pipeline?tabs=GitHub)

### GitHub actions

Po wdrożeniu aplikacji raz za pomocą `azd up`, możesz włączyć ciągłe wdrażanie z GitHub Actions.

Uruchom to polecenie, aby skonfigurować konto Service Principal do wdrażania CI i przechowywać zmienne środowiskowe `azd` w sekretach GitHub Actions:

```shell
azd pipeline config
```

Możesz wyzwolić przepływ pracy "Deploy" ręcznie z GitHub actions lub poczekać na następny push do main.

Jeśli zmienisz swoje zmienne środowiskowe `azd` w dowolnym momencie (przez `azd env set` lub w wyniku aprowizacji), uruchom ponownie to polecenie, aby zaktualizować sekrety GitHub Actions.

### Azure DevOps

Po wdrożeniu aplikacji raz za pomocą `azd up`, możesz włączyć ciągłe wdrażanie z Azure DevOps.

Uruchom to polecenie, aby skonfigurować konto Service Principal do wdrażania CI i przechowywać zmienne środowiskowe `azd` w sekretach GitHub Actions:

```shell
azd pipeline config --provider azdo
```

Jeśli zmienisz swoje zmienne środowiskowe `azd` w dowolnym momencie (przez `azd env set` lub w wyniku aprowizacji), uruchom ponownie to polecenie, aby zaktualizować sekrety GitHub Actions.
