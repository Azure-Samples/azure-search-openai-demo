# Instrukcje dla agentów kodujących

Ten plik zawiera instrukcje dla programistów pracujących nad aplikacją demonstracyjną Azure Search i OpenAI. Obejmuje ogólny układ kodu, sposób dodawania nowych danych, sposób dodawania nowych zmiennych środowiskowych azd, sposób dodawania nowych ustawień deweloperskich oraz sposób dodawania testów dla nowych funkcji.

Zawsze aktualizuj ten plik wraz z wszelkimi zmianami w bazie kodu lub procesie deweloperskim.
W razie potrzeby edytuj ten plik, aby upewnić się, że dokładnie odzwierciedla aktualny stan projektu.

## Ogólny układ kodu

* app: Zawiera główny kod aplikacji, w tym frontend i backend.
  * app/backend: Zawiera kod backendu w Pythonie, napisany przy użyciu frameworka Quart.
    * app/backend/approaches: Zawiera różne podejścia
      * app/backend/approaches/approach.py: Klasa bazowa dla wszystkich podejść
      * app/backend/approaches/retrievethenread.py: Podejście Ask, tylko wyszukuje i odpowiada
      * app/backend/approaches/chatreadretrieveread.py: Podejście Chat, zawiera najpierw krok przepisywania zapytania
      * app/backend/approaches/prompts/ask_answer_question.prompty: Prompt używany przez podejście Ask do odpowiadania na pytanie na podstawie źródeł
      * app/backend/approaches/prompts/chat_query_rewrite.prompty: Prompt używany do przepisywania zapytania na podstawie historii wyszukiwania na lepsze zapytanie wyszukiwania
      * app/backend/approaches/prompts/chat_query_rewrite_tools.json: Narzędzia używane przez prompt przepisywania zapytania
      * app/backend/approaches/prompts/chat_answer_question.prompty: Prompt używany przez podejście Chat do faktycznego odpowiadania na pytanie na podstawie źródeł
    * app/backend/prepdocslib: Zawiera bibliotekę pozyskiwania dokumentów używaną zarówno przez pozyskiwanie lokalne, jak i chmurowe
      * app/backend/prepdocslib/blobmanager.py: Zarządza przesyłaniem do Azure Blob Storage
      * app/backend/prepdocslib/cloudingestionstrategy.py: Buduje indeksator Azure AI Search i zestaw umiejętności dla potoku pozyskiwania chmury
      * app/backend/prepdocslib/csvparser.py: Analizuje pliki CSV
      * app/backend/prepdocslib/embeddings.py: Generuje osadzenia dla tekstu i obrazów przy użyciu Azure OpenAI
      * app/backend/prepdocslib/figureprocessor.py: Generuje opisy figur zarówno dla pozyskiwania lokalnego, jak i umiejętności przetwarzania figur w chmurze
      * app/backend/prepdocslib/fileprocessor.py: Orkiestruje analizę i dzielenie na części poszczególnych plików
      * app/backend/prepdocslib/filestrategy.py: Strategia przesyłania i indeksowania plików (pozyskiwanie lokalne)
      * app/backend/prepdocslib/htmlparser.py: Analizuje pliki HTML
      * app/backend/prepdocslib/integratedvectorizerstrategy.py: Strategia wykorzystująca zintegrowaną wektoryzację Azure AI Search
      * app/backend/prepdocslib/jsonparser.py: Analizuje pliki JSON
      * app/backend/prepdocslib/listfilestrategy.py: Wyświetla pliki z lokalnego systemu plików lub Azure Data Lake
      * app/backend/prepdocslib/mediadescriber.py: Interfejsy do opisywania obrazów (Azure OpenAI GPT-4o, Content Understanding)
      * app/backend/prepdocslib/page.py: Klasy danych dla stron, obrazów i fragmentów
      * app/backend/prepdocslib/parser.py: Interfejs parsera bazowego
      * app/backend/prepdocslib/pdfparser.py: Analizuje pliki PDF przy użyciu Azure Document Intelligence lub parsera lokalnego
      * app/backend/prepdocslib/searchmanager.py: Zarządza tworzeniem i aktualizacją indeksu Azure AI Search
      * app/backend/prepdocslib/servicesetup.py: Współdzielone helpery konfiguracji usługi dla OpenAI, osadzeń, blob storage itp.
      * app/backend/prepdocslib/strategy.py: Interfejs strategii bazowej dla pozyskiwania dokumentów
      * app/backend/prepdocslib/textparser.py: Analizuje zwykły tekst i pliki markdown
      * app/backend/prepdocslib/textprocessor.py: Przetwarza fragmenty tekstu dla pozyskiwania w chmurze (łączy figury, generuje osadzenia)
      * app/backend/prepdocslib/textsplitter.py: Dzieli tekst na fragmenty przy użyciu różnych strategii
    * app/backend/app.py: Główny punkt wejścia dla aplikacji backendowej.
  * app/functions: Funkcje Azure używane do niestandardowych umiejętności pozyskiwania w chmurze (ekstrakcja dokumentów, przetwarzanie figur, przetwarzanie tekstu). Każda funkcja zawiera zsynchronizowaną kopię `prepdocslib`; uruchom `python scripts/copy_prepdocslib.py`, aby odświeżyć lokalne kopie, jeśli zmodyfikujesz bibliotekę.
  * app/frontend: Zawiera kod frontendu React, zbudowany przy użyciu TypeScript, zbudowany przy użyciu vite.
    * app/frontend/src/api: Zawiera kod klienta API do komunikacji z backendem.
    * app/frontend/src/components: Zawiera komponenty React dla frontendu.
    * app/frontend/src/locales: Zawiera pliki tłumaczeń dla internacjonalizacji.
      * app/frontend/src/locales/da/translation.json: Tłumaczenia duńskie
      * app/frontend/src/locales/en/translation.json: Tłumaczenia angielskie
      * app/frontend/src/locales/es/translation.json: Tłumaczenia hiszpańskie
      * app/frontend/src/locales/fr/translation.json: Tłumaczenia francuskie
      * app/frontend/src/locales/it/translation.json: Tłumaczenia włoskie
      * app/frontend/src/locales/ja/translation.json: Tłumaczenia japońskie
      * app/frontend/src/locales/nl/translation.json: Tłumaczenia holenderskie
      * app/frontend/src/locales/ptBR/translation.json: Tłumaczenia portugalskie
      * app/frontend/src/locales/tr/translation.json: Tłumaczenia tureckie
    * app/frontend/src/pages: Zawiera główne strony aplikacji
* infra: Zawiera szablony Bicep do aprowizacji zasobów Azure.
* tests: Zawiera kod testów, w tym testy e2e, testy integracji aplikacji i testy jednostkowe.

## Dodawanie nowych danych

Nowe pliki należy dodać do folderu `data`, a następnie uruchomić scripts/prepdocs.sh lub scripts/prepdocs.ps1, aby pozyskać dane.

## Dodawanie nowej zmiennej środowiskowej azd

Zmienna środowiskowa azd jest przechowywana przez CLI azd dla każdego środowiska. Jest przekazywana do polecenia "azd up" i może konfigurować zarówno opcje aprowizacji, jak i ustawienia aplikacji.
Podczas dodawania nowych zmiennych środowiskowych azd zaktualizuj:

1. infra/main.parameters.json: Dodaj nowy parametr z nazwą zmiennej przyjazną dla Bicep i zmapuj na nową zmienną środowiskową
1. infra/main.bicep: Dodaj nowy parametr Bicep na górze i dodaj go do obiektu `appEnvVariables`
1. .azdo/pipelines/azure-dev.yml: Dodaj nową zmienną środowiskową w sekcji `env`
1. .github/workflows/azure-dev.yml: Dodaj nową zmienną środowiskową w sekcji `env`

Możesz również potrzebować zaktualizować:

1. app/backend/prepdocs.py: Jeśli zmienna jest używana w skrypcie pozyskiwania, pobierz ją ze zmiennych środowiskowych tutaj. Nie zawsze jest to potrzebne.
1. app/backend/app.py: Jeśli zmienna jest używana w aplikacji backendowej, pobierz ją ze zmiennych środowiskowych w funkcji setup_clients(). Nie zawsze jest to potrzebne.

## Dodawanie nowego ustawienia do "Ustawień deweloperskich" w aplikacji RAG

Podczas dodawania nowego ustawienia deweloperskiego zaktualizuj:

* frontend:
  * app/frontend/src/api/models.ts: Dodaj do ChatAppRequestOverrides
  * app/frontend/src/components/Settings.tsx: Dodaj element UI dla ustawienia
  * app/frontend/src/locales/*/translations.json: Dodaj tłumaczenie dla etykiety/podpowiedzi ustawienia dla wszystkich języków
  * app/frontend/src/pages/chat/Chat.tsx: Dodaj ustawienie do komponentu, przekaż je do Settings
  * app/frontend/src/pages/ask/Ask.tsx: Dodaj ustawienie do komponentu, przekaż je do Settings

* backend:
  * app/backend/approaches/chatreadretrieveread.py: Pobierz z parametru overrides
  * app/backend/approaches/retrievethenread.py: Pobierz z parametru overrides
  * app/backend/app.py: Niektóre ustawienia mogą wymagać wysłania w trasie /config.

## Podczas dodawania testów dla nowej funkcji

Wszystkie testy znajdują się w folderze `tests` i używają frameworka pytest.
Istnieją trzy style testów:

* testy e2e: Używają playwright do uruchomienia aplikacji w przeglądarce i testowania UI end-to-end. Znajdują się w e2e.py i mockują backend przy użyciu snapshotów z testów aplikacji.
* testy integracji aplikacji: Głównie w test_app.py, te testy testują punkty końcowe API aplikacji i używają mocków dla usług takich jak Azure OpenAI i Azure Search.
* testy jednostkowe: Pozostałe testy to testy jednostkowe, które testują poszczególne funkcje i metody. Znajdują się w plikach test_*.py.

Podczas dodawania nowej funkcji dodaj testy dla niej w odpowiednim pliku.
Jeśli funkcja jest elementem UI, dodaj test e2e dla niej.
Jeśli jest to punkt końcowy API, dodaj test integracji aplikacji dla niej.
Jeśli jest to funkcja lub metoda, dodaj test jednostkowy dla niej.
Używaj mocków z tests/conftest.py do mockowania zewnętrznych usług. Preferuj mockowanie na poziomie HTTP/requests, gdy to możliwe.

Podczas uruchamiania testów upewnij się, że najpierw aktywujesz środowisko wirtualne .venv:

```shell
source .venv/bin/activate
```

Aby sprawdzić pokrycie, uruchom następujące polecenie:

```shell
pytest --cov --cov-report=annotate:cov_annotate
```

Otwórz katalog cov_annotate, aby wyświetlić adnotowany kod źródłowy. Będzie jeden plik na plik źródłowy. Jeśli plik ma 100% pokrycia źródła, oznacza to, że wszystkie linie są objęte testami, więc nie musisz otwierać pliku.

Dla każdego pliku, który ma mniej niż 100% pokrycia testów, znajdź odpowiedni plik w cov_annotate i przejrzyj plik.

Jeśli linia zaczyna się od ! (wykrzyknik), oznacza to, że linia nie jest objęta testami. Dodaj testy, aby pokryć brakujące linie.

## Wysyłanie pull requestów

Podczas wysyłania pull requestów upewnij się, że przestrzegasz formatu PULL_REQUEST_TEMPLATE.md.

## Aktualizowanie zależności

Aby zaktualizować określony pakiet w backendzie, użyj następującego polecenia, zastępując `<package-name>` nazwą pakietu, który chcesz zaktualizować:

```shell
cd app/backend && uv pip compile requirements.in -o requirements.txt --python-version 3.10 --upgrade-package package-name
```

## Sprawdzanie podpowiedzi typu Python

Aby sprawdzić podpowiedzi typu Python, użyj następującego polecenia:

```shell
cd app/backend && mypy . --config-file=../../pyproject.toml
```

```shell
cd scripts && mypy . --config-file=../pyproject.toml
```

Zauważ, że obecnie nie wymuszamy podpowiedzi typu w folderze testów, ponieważ wymagałoby to dodania wielu komentarzy `# type: ignore` do istniejących testów.
Wymuszamy podpowiedzi typu tylko w głównym kodzie aplikacji i skryptach.

## Styl kodu Python

Nie używaj pojedynczych podkreśleń przed "prywatnymi" metodami lub zmiennymi w kodzie Pythona. Nie przestrzegamy tej konwencji w tej bazie kodu, ponieważ jest to aplikacja, a nie biblioteka.

## Wdrażanie aplikacji

Aby wdrożyć aplikację, użyj narzędzia CLI `azd`. Upewnij się, że masz zainstalowaną najnowszą wersję CLI `azd`. Następnie uruchom następujące polecenie z katalogu głównego repozytorium:

```shell
azd up
```

To polecenie ZARÓWNO aprowizuje zasoby Azure, JAK I wdroży kod aplikacji.

Jeśli zmieniłeś tylko szablony Bicep i chcesz ponownie aprowizować zasoby Azure, uruchom:

```shell
azd provision
```

Jeśli zmieniłeś tylko kod aplikacji i chcesz ponownie wdrożyć kod, uruchom:

```shell
azd deploy
```

Jeśli używasz pozyskiwania w chmurze i chcesz wdrożyć tylko poszczególne funkcje, uruchom niezbędne polecenia wdrożenia, na przykład:

```shell
azd deploy document-extractor
azd deploy figure-processor
azd deploy text-processor
```
