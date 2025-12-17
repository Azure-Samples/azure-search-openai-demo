# Współtworzenie

Ten projekt przyjmuje wkłady i sugestie. Większość wkładów wymaga zgody na
Umowę licencyjną współtwórcy (CLA) deklarującą, że masz prawo i faktycznie przyznasz nam
prawa do korzystania z Twojego wkładu. Szczegóły znajdziesz na <https://cla.opensource.microsoft.com>.

Gdy przesyłasz pull request, bot CLA automatycznie określi, czy musisz dostarczyć
CLA i odpowiednio oznaczy PR (np. sprawdzenie statusu, komentarz). Po prostu postępuj zgodnie z instrukcjami
dostarczonymi przez bota. Będziesz musiał to zrobić tylko raz we wszystkich repozytoriach korzystających z naszego CLA.

Ten projekt przyjął [Kodeks postępowania Microsoft Open Source](https://opensource.microsoft.com/codeofconduct/).
Aby uzyskać więcej informacji, zobacz [FAQ Kodeksu postępowania](https://opensource.microsoft.com/codeofconduct/faq/) lub
skontaktuj się z [opencode@microsoft.com](mailto:opencode@microsoft.com), jeśli masz dodatkowe pytania lub komentarze.

- [Przesyłanie Pull Requestu (PR)](#przesyłanie-pull-requestu-pr)
- [Konfigurowanie środowiska deweloperskiego](#konfigurowanie-środowiska-deweloperskiego)
- [Uruchamianie testów jednostkowych](#uruchamianie-testów-jednostkowych)
- [Uruchamianie testów E2E](#uruchamianie-testów-e2e)
- [Styl kodu](#styl-kodu)
- [Dodawanie nowych funkcji](#dodawanie-nowych-funkcji)
  - [Dodawanie nowych zmiennych środowiskowych azd](#dodawanie-nowych-zmiennych-środowiskowych-azd)
  - [Dodawanie nowych ciągów znaków UI](#dodawanie-nowych-ciągów-znaków-ui)

## Przesyłanie Pull Requestu (PR)

Przed przesłaniem Pull Requestu (PR) rozważ następujące wytyczne:

- Przeszukaj repozytorium (<https://github.com/[organization-name>]/[repository-name]/pulls) w poszukiwaniu otwartego lub zamkniętego PR
  związanego z Twoim zgłoszeniem. Nie chcesz powielać wysiłków.
- Wprowadź swoje zmiany w nowym forku git
- Postępuj zgodnie z [konwencjami stylu kodu](#styl-kodu)
- [Uruchom testy](#uruchamianie-testów-jednostkowych) (i napisz nowe, jeśli to konieczne)
- Zatwierdź swoje zmiany, używając opisowego komunikatu zatwierdzenia
- Wypchnij swój fork do GitHub
- W GitHub utwórz pull request do gałęzi `main` repozytorium
- Poproś opiekuna o sprawdzenie Twojego PR i rozwiąż wszelkie komentarze, które mogą mieć

## Konfigurowanie środowiska deweloperskiego

Zainstaluj zależności deweloperskie:

```shell
python -m pip install -r requirements-dev.txt
```

Zainstaluj hooki pre-commit:

```shell
pre-commit install
```

Skompiluj JavaScript:

```shell
( cd ./app/frontend ; npm install ; npm run build )
```

## Uruchamianie testów jednostkowych

Uruchom testy:

```shell
python -m pytest
```

Jeśli snapshoty testów wymagają aktualizacji (a zmiany są oczekiwane), możesz je zaktualizować, uruchamiając:

```shell
python -m pytest --snapshot-update
```

Po pomyślnym przejściu testów wygeneruj raport pokrycia, aby upewnić się, że Twoje zmiany są objęte:

```shell
pytest --cov --cov-report=xml && \
diff-cover coverage.xml --html-report coverage_report.html && \
open coverage_report.html
```

## Uruchamianie testów E2E

Zainstaluj zależności przeglądarki Playwright:

```shell
playwright install --with-deps
```

Uruchom testy:

```shell
python -m pytest tests/e2e.py --tracing=retain-on-failure
```

Gdy wystąpi błąd, plik zip śladu zostanie zapisany w folderze test-results.
Możesz go wyświetlić, używając interfejsu wiersza poleceń Playwright:

```shell
playwright show-trace test-results/<trace-zip>
```

Możesz również użyć przeglądarki śladu online na <https://trace.playwright.dev/>

## Styl kodu

Ta baza kodu zawiera kilka języków: TypeScript, Python, Bicep, Powershell i Bash.
Kod powinien być zgodny ze standardowymi konwencjami każdego języka.

W przypadku Pythona możesz wymusić konwencje za pomocą `ruff` i `black`.

Zainstaluj zależności deweloperskie:

```shell
python -m pip install -r requirements-dev.txt
```

Uruchom `ruff`, aby sprawdzić plik:

```shell
python -m ruff <ścieżka-do-pliku>
```

Uruchom `black`, aby sformatować plik:

```shell
python -m black <ścieżka-do-pliku>
```

Jeśli wykonałeś powyższe kroki, aby zainstalować hooki pre-commit, możesz po prostu poczekać, aż te hooki uruchomią `ruff` i `black` za Ciebie.

## Dodawanie nowych funkcji

Zalecamy używanie trybu agenta GitHub Copilot podczas dodawania nowych funkcji,
ponieważ ten projekt zawiera plik [AGENTS.md](AGENTS.md),
który instruuje Copilot (i innych agentów kodujących) jak generować kod dla typowych zmian w kodzie.

Jeśli nie używasz trybu agenta Copilot, zapoznaj się zarówno z tym plikiem, jak i poniższymi sugestiami.

### Dodawanie nowych zmiennych środowiskowych azd

Podczas dodawania nowych zmiennych środowiskowych azd pamiętaj o aktualizacji:

1. [main.parameters.json](./infra/main.parameters.json)
1. [appEnvVariables w main.bicep](./infra/main.bicep)
1. [Pipeline ADO](.azdo/pipelines/azure-dev.yml).
1. [Przepływy pracy Github](.github/workflows/azure-dev.yml)

### Dodawanie nowych ciągów znaków UI

Podczas dodawania nowych ciągów znaków UI pamiętaj o aktualizacji wszystkich tłumaczeń.
W przypadku wszelkich tłumaczeń wygenerowanych za pomocą narzędzia AI,
proszę wskazać w opisie PR, które ciągi znaków języka zostały wygenerowane przez AI.

Oto współtwórcy społeczności, którzy mogą przejrzeć tłumaczenia:

| Język     | Współtwórca          |
|-----------|---------------------|
| Duński    | @EMjetrot           |
| Francuski | @manekinekko        |
| Japoński  | @bnodir             |
| Norweski  | @@jeannotdamoiseaux |
| Portugalski| @glaucia86         |
| Hiszpański | @miguelmsft        |
| Turecki   | @mertcakdogan       |
| Włoski    | @ivanvaccarics      |
| Holenderski|                    |
| Polski    | @michuhu            |
