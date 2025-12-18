# Czat RAG: Pozyskiwanie danych

Projekt [azure-search-openai-demo](/) może skonfigurować pełną aplikację czatu RAG na Azure AI Search i OpenAI, dzięki czemu możesz czatować na niestandardowych danych, takich jak wewnętrzne dane przedsiębiorstwa lub zestawy wiedzy specyficzne dla domeny. Po pełne instrukcje dotyczące konfiguracji projektu zapoznaj się z [głównym README](/README.pl.md), a następnie wróć tutaj po szczegółowe instrukcje dotyczące komponentu pozyskiwania danych.

Aplikacja czatu zapewnia dwa sposoby pozyskiwania danych: pozyskiwanie ręczne i pozyskiwanie chmurowe. Oba podejścia używają tego samego kodu do przetwarzania danych, ale pozyskiwanie ręczne działa lokalnie, podczas gdy pozyskiwanie chmurowe działa w Azure Functions jako niestandardowe umiejętności Azure AI Search.

- [Obsługiwane formaty dokumentów](#obsługiwane-formaty-dokumentów)
- [Etapy pozyskiwania](#etapy-pozyskiwania)
  - [Ekstrakcja dokumentów](#ekstrakcja-dokumentów)
  - [Przetwarzanie figur](#przetwarzanie-figur)
  - [Przetwarzanie tekstu](#przetwarzanie-tekstu)
- [Pozyskiwanie lokalne](#pozyskiwanie-lokalne)
  - [Kategoryzowanie danych dla ulepszonego wyszukiwania](#ulepszanie-funkcjonalności-wyszukiwania-poprzez-kategoryzację-danych)
  - [Indeksowanie dodatkowych dokumentów](#indeksowanie-dodatkowych-dokumentów)
  - [Usuwanie dokumentów](#usuwanie-dokumentów)
- [Pozyskiwanie chmurowe](#pozyskiwanie-chmurowe)
  - [Włączanie pozyskiwania chmurowego](#włączanie-pozyskiwania-chmurowego)
  - [Architektura indeksera](#architektura-indeksera)
  - [Indeksowanie dodatkowych dokumentów w chmurze](#indeksowanie-dodatkowych-dokumentów-w-chmurze)
  - [Usuwanie dokumentów z chmury](#usuwanie-dokumentów-z-chmury)
  - [Zaplanowane indeksowanie](#zaplanowane-indeksowanie)
- [Wskazówki dotyczące debugowania](#wskazówki-dotyczące-debugowania)

## Obsługiwane formaty dokumentów

Aby pozyskać format dokumentu, potrzebujemy narzędzia, które może przekształcić go w tekst. Domyślnie indeksowanie ręczne używa Azure Document Intelligence (DI w tabeli poniżej), ale mamy również lokalne parsery dla kilku formatów. Lokalne parsery nie są tak wyrafinowane jak Azure Document Intelligence, ale mogą być używane do zmniejszenia opłat.

| Format | Indeksowanie ręczne                  | Zintegrowana wektoryzacja |
| ------ | ------------------------------------ | ------------------------- |
| PDF    | Tak (DI lub lokalnie z PyPDF)       | Tak                       |
| HTML   | Tak (DI lub lokalnie z BeautifulSoup) | Tak                     |
| DOCX, PPTX, XLSX | Tak (DI)                     | Tak                       |
| Obrazy (JPG, PNG, BPM, TIFF, HEIFF) | Tak (DI) | Tak                       |
| TXT    | Tak (Lokalnie)                       | Tak                       |
| JSON   | Tak (Lokalnie)                       | Tak                       |
| CSV    | Tak (Lokalnie)                       | Tak                       |

## Etapy pozyskiwania

Potok pozyskiwania składa się z trzech głównych etapów, które przekształcają surowe dokumenty w przeszukiwalną zawartość w Azure AI Search. Te etapy mają zastosowanie zarówno do [pozyskiwania lokalnego](#pozyskiwanie-lokalne), jak i [pozyskiwania chmurowego](#pozyskiwanie-chmurowe).

### Ekstrakcja dokumentów

Pierwszy etap wyodrębnia tekst i ustrukturyzowaną zawartość z dokumentów źródłowych za pomocą parserów dostosowanych do każdego formatu pliku. W przypadku plików PDF, HTML, DOCX, PPTX, XLSX i obrazów potok domyślnie używa [Azure Document Intelligence](https://learn.microsoft.com/azure/ai-services/document-intelligence/overview) do wyodrębniania tekstu, tabel i figur z informacjami o układzie. Alternatywnie można użyć lokalnych parserów, takich jak PyPDF i BeautifulSoup, aby zmniejszyć koszty dla prostszych dokumentów. W przypadku plików TXT, JSON i CSV lekkie lokalne parsery wyodrębniają zawartość bezpośrednio.

Podczas ekstrakcji tabele są konwertowane na znaczniki HTML, aby zachować ich strukturę, a figury (gdy włączona jest funkcja multimodalna) są identyfikowane za pomocą ramek ograniczających i zastępników.

Wynikiem tego etapu jest lista stron, z których każda zawiera wyodrębniony tekst z osadzonym HTML tabeli i zastępczymi figurami, takimi jak `<figure id="fig1"></figure>`.

### Przetwarzanie figur

Ten etap jest opcjonalny i ma zastosowanie tylko wtedy, gdy funkcja multimodalna jest włączona *i* sam dokument zawiera figury. Zobacz [dokumentację funkcji multimodalnej](./multimodal.pl.md) po więcej szczegółów.

Gdy obsługa multimodalna jest włączona, figury wyodrębnione w poprzednim etapie są wzbogacane o opisy i osadzenia. Każda figura jest:

1. **Przycięta i zapisana**: Obraz figury jest przycinany z pliku PDF przy użyciu współrzędnych ramki ograniczającej i zapisywany jako plik PNG.
2. **Opisana**: Opis tekstowy jest generowany za pomocą modelu Azure OpenAI GPT-4 Vision lub Azure AI Content Understanding, w zależności od konfiguracji.
3. **Przesłana**: Obraz figury jest przesyłany do Azure Blob Storage i przypisywany mu URL.
4. **Osadzona** (opcjonalnie): Jeśli osadzenia obrazów są włączone, osadzenie wektorowe jest obliczane dla figury za pomocą Azure AI Vision.

Wynikiem tego etapu są wzbogacone metadane figur, w tym tekst opisu, URL magazynu i opcjonalny wektor osadzenia.

### Przetwarzanie tekstu

Ostatni etap łączy wyodrębniony tekst z opisami figur, dzieli zawartość na przeszukiwalne fragmenty i oblicza osadzenia.

### Scalanie figur

Najpierw zastępcze figury w tekście strony są zastępowane pełnymi znacznikami HTML, które zawierają podpis figury i wygenerowany opis, tworząc spójną narrację tekstową, która uwzględnia treść wizualną.

#### Dzielenie na fragmenty

Następnie połączony tekst jest dzielony na fragmenty za pomocą splitter świadomego zdań, który respektuje granice semantyczne. Domyślny rozmiar fragmentu wynosi około 1000 znaków (około 400-500 tokenów dla języka angielskiego), z 10% nakładaniem się między kolejnymi fragmentami, aby zachować kontekst na granicach. Splitter używa podejścia okna przesuwnego, zapewniając, że zdania kończące jeden fragment również rozpoczynają następny, co zmniejsza ryzyko utraty ważnego kontekstu na granicach fragmentów.

**Dlaczego dzielić dokumenty na fragmenty?** Chociaż Azure AI Search może indeksować pełne dokumenty, dzielenie na fragmenty jest niezbędne dla wzorca RAG, ponieważ ogranicza ilość informacji wysyłanych do OpenAI, który ma limity tokenów dla okien kontekstu. Dzieląc zawartość na skoncentrowane fragmenty, system może pobierać i wstrzykiwać tylko najbardziej istotne fragmenty tekstu do promptu LLM, poprawiając zarówno jakość odpowiedzi, jak i efektywność kosztową.

W razie potrzeby możesz zmodyfikować algorytm dzielenia w `app/backend/prepdocslib/textsplitter.py`. Po głębsze, bogate w diagramy wyjaśnienie działania splitter (figury, rekursja, heurystyki scalania, gwarancje i przykłady) zobacz [dokumentację text splitter](./textsplitter.md) *(angielski)*.

#### Osadzanie

Na koniec, jeśli wyszukiwanie wektorowe jest włączone, osadzenia tekstowe są obliczane dla każdego fragmentu za pomocą modeli osadzania Azure OpenAI (text-embedding-ada-002, text-embedding-3-small lub text-embedding-3-large). Te osadzenia są generowane w partiach dla wydajności, z logiką ponawiania, aby obsługiwać limity szybkości.

### Indeksowanie

Ostatnim krokiem jest indeksowanie fragmentów do Azure AI Search. Każdy fragment jest przechowywany jako oddzielny dokument w indeksie wyszukiwania, z metadanymi łączącymi go z powrotem z plikiem źródłowym i numerem strony. Jeśli wyszukiwanie wektorowe jest włączone, obliczone osadzenia są również przechowywane obok tekstu, umożliwiając efektywne wyszukiwanie podobieństwa podczas zapytania.

Oto przykład, jak wygląda ostateczny zaindeksowany dokument fragmentu:

```json
{
    "id": "file-Northwind_Health_Plus_Benefits_Details_pdf-4E6F72746877696E645F4865616C74685F506C75735F42656E65666974735F44657461696C732E706466-page-0",
    "content": "# Zava\n\nNorthwind Health Plus Plan\n...",
    "category": null,
    "sourcepage": "Northwind_Health_Plus_Benefits_Details.pdf#page=1",
    "sourcefile": "Northwind_Health_Plus_Benefits_Details.pdf",
    "storageUrl": "https://std4gfbajn3e3yu.blob.core.windows.net/content/Northwind_Health_Plus_Benefits_Details.pdf",
    "embedding": [0.0123, -0.0456, ...]
}
```

Jeśli multimodalne jest włączone, ten dokument będzie również zawierał pole `"images"` i opisy figur w polu `"content"`.

## Pozyskiwanie lokalne

Skrypt [`prepdocs.py`](../app/backend/prepdocs.py) jest odpowiedzialny zarówno za przesyłanie, jak i indeksowanie dokumentów. Typowe użycie polega na wywołaniu go za pomocą `scripts/prepdocs.sh` (Mac/Linux) lub `scripts/prepdocs.ps1` (Windows), ponieważ te skrypty skonfigurują środowisko wirtualne Python i przekażą wymagane parametry na podstawie bieżącego środowiska `azd`. Możesz przekazać dodatkowe argumenty bezpośrednio do skryptu, na przykład `scripts/prepdocs.ps1 --removeall`. Gdy uruchamiany jest `azd up` lub `azd provision`, skrypt jest automatycznie wywoływany.

![Diagram procesu indeksowania](images/diagram_prepdocs.png)

Skrypt używa następujących kroków do indeksowania dokumentów:

1. Jeśli jeszcze nie istnieje, utwórz nowy indeks w Azure AI Search.
2. Prześlij pliki PDF do Azure Blob Storage.
3. Podziel pliki PDF na fragmenty tekstu.
4. Prześlij fragmenty do Azure AI Search. Jeśli używasz wektorów (domyślnie), oblicz również osadzenia i prześlij je wraz z tekstem.

### Ulepszanie funkcjonalności wyszukiwania poprzez kategoryzację danych

Aby ulepszyć funkcjonalność wyszukiwania, kategoryzuj dane podczas procesu pozyskiwania za pomocą argumentu `--category`, na przykład `scripts/prepdocs.ps1 --category ExampleCategoryName`. Ten argument określa kategorię, do której należą dane, umożliwiając filtrowanie wyników wyszukiwania na podstawie tych kategorii.

Po uruchomieniu skryptu z żądaną kategorią upewnij się, że te kategorie są dodane do listy rozwijanej 'Include Category'. Można to znaleźć w ustawieniach deweloperskich w [`Settings.tsx`](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/frontend/src/components/Settings/Settings.tsx). Domyślna opcja dla tej listy rozwijanej to "All". Uwzględniając określone kategorie, możesz skuteczniej udoskonalać wyniki wyszukiwania.

### Indeksowanie dodatkowych dokumentów

Aby przesłać więcej plików PDF, umieść je w folderze data/ i uruchom `./scripts/prepdocs.sh` lub `./scripts/prepdocs.ps1`.

Skrypt prepdocs zapisuje plik .md5 ze skrótem MD5 każdego pliku, który zostanie przesłany. Gdy skrypt prepdocs jest uruchamiany ponownie, ten skrót jest sprawdzany względem bieżącego skrótu, a plik jest pomijany, jeśli się nie zmienił.

### Usuwanie dokumentów

Możesz chcieć usunąć dokumenty z indeksu. Na przykład, jeśli używasz przykładowych danych, możesz chcieć usunąć dokumenty, które już są w indeksie, przed dodaniem własnych.

Aby usunąć wszystkie dokumenty, użyj `./scripts/prepdocs.sh --removeall` lub `./scripts/prepdocs.ps1 --removeall`.

Możesz również usunąć poszczególne dokumenty, używając flagi `--remove`. Otwórz `scripts/prepdocs.sh` lub `scripts/prepdocs.ps1` i zastąp `/data/*` przez `/data/NAZWA-TWOJEGO-PLIKU-TUTAJ.pdf`. Następnie uruchom `scripts/prepdocs.sh --remove` lub `scripts/prepdocs.ps1 --remove`.

## Pozyskiwanie chmurowe

Ten projekt zawiera opcjonalną funkcję wykonywania pozyskiwania danych w chmurze za pomocą Azure Functions jako niestandardowych umiejętności dla indekserów Azure AI Search. To podejście przenosi obciążenie pozyskiwania z lokalnej maszyny do chmury, umożliwiając bardziej skalowalne i wydajne przetwarzanie dużych zestawów danych.

### Włączanie pozyskiwania chmurowego

1. Jeśli wcześniej wdrażałeś, usuń istniejący indeks wyszukiwania lub utwórz nowy indeks. Ta funkcja nie może być używana z istniejącym indeksem. W nowo utworzonym schemacie indeksu dodawane jest nowe pole 'parent_id'. Jest ono używane wewnętrznie przez indekser do zarządzania cyklem życia fragmentów. Uruchom to polecenie, aby ustawić nową nazwę indeksu:

    ```shell
    azd env set AZURE_SEARCH_INDEX cloudindex
    ```

2. Uruchom to polecenie:

    ```shell
    azd env set USE_CLOUD_INGESTION true
    ```

3. Otwórz `azure.yaml` i odkomentuj sekcje document-extractor, figure-processor i text-processor. To są aplikacje Azure Functions, które zostaną wdrożone i będą służyć jako umiejętności Azure AI Search.

4. (Zalecane) Zwiększ pojemność dla modelu osadzania do maksymalnego przydziału dozwolonego dla Twojego regionu/subskrypcji, aby Azure Functions mogły generować osadzenia bez przekraczania limitów szybkości:

    ```shell
    azd env set AZURE_OPENAI_EMB_DEPLOYMENT_CAPACITY 400
    ```

5. Aprowizuj nowe zasoby Azure Functions, wdróż aplikacje funkcyjne i zaktualizuj indekser wyszukiwania za pomocą:

    ```shell
    azd up
    ```

6. To przesłanie dokumentów z folderu `data/` do kontenera Blob storage, utworzenie indeksera i skillset oraz uruchomienie indeksera w celu pozyskania danych. Możesz monitorować status indeksera z portalu.

7. Gdy masz nowe dokumenty do pozyskania, możesz przesłać dokumenty do kontenera Blob storage i uruchomić indekser z Azure Portal, aby pozyskać nowe dokumenty.

### Architektura indeksera

Potok pozyskiwania chmurowego używa czterech Azure Functions jako niestandardowych umiejętności w indekserze Azure AI Search. Każda funkcja odpowiada etapowi w procesie pozyskiwania. Oto jak to działa:

![Diagram potoku pozyskiwania chmurowego](images/ingestion_pipeline.png)

1. **Użytkownik przesyła dokumenty** do Azure Blob Storage (kontener zawartości)
2. **Indekser Azure AI Search** monitoruje kontener blob i organizuje przetwarzanie
3. **Niestandardowe umiejętności** przetwarzają dokumenty przez trzy etapy:
   - **Document Extractor** (Umiejętność #1): Wyodrębnia tekst i metadane figur z dokumentów źródłowych
   - **Figure Processor** (Umiejętność #2): Wzbogaca figury opisami i osadzeniami
   - **Shaper Skill** (Umiejętność #3): Wbudowana umiejętność Azure AI Search, która konsoliduje wzbogacone dane
   - **Text Processor** (Umiejętność #4): Łączy tekst z wzbogaconymi figurami, dzieli zawartość na fragmenty i generuje osadzenia
4. **Indeks Azure AI Search** otrzymuje ostateczne przetworzone fragmenty z osadzeniami

Funkcje są zdefiniowane w katalogu `app/functions/`, a niestandardowy skillset jest skonfigurowany w skrypcie `app/backend/setup_cloud_ingestion.py`.

#### [Funkcja Document Extractor](app/functions/document_extractor/)

- Implementuje etap [ekstrakcji dokumentów](#ekstrakcja-dokumentów)
- Emituje tekst markdown z zastępczymi `<figure id="...">` i metadanymi figur

#### [Funkcja Figure Processor](app/functions/figure_processor/)

- Implementuje etap [przetwarzania figur](#przetwarzanie-figur)
- Emituje wzbogacone metadane figur z opisami, URL-ami i osadzeniami

#### [Shaper Skill](https://learn.microsoft.com/azure/search/cognitive-search-skill-shaper)

- Konsoliduje wzbogacenia z procesora figur z powrotem do głównego kontekstu dokumentu
- Wymagane, ponieważ drzewo wzbogacania Azure AI Search izoluje dane według kontekstu
- Shaper jawnie łączy:
  - Oryginalną tablicę `pages` z `document_extractor`
  - Wzbogaconą tablicę `figures` z opisami, URL-ami i osadzeniami z `figure_processor`
  - Metadane pliku (file_name, storageUrl)
- Tworzy obiekt `consolidated_document`, który może być konsumowany przez procesor tekstu

#### [Funkcja Text Processor](app/functions/text_processor/)

- Implementuje etap [przetwarzania tekstu](#przetwarzanie-tekstu) (scalanie figur, dzielenie na fragmenty, osadzanie)
- Otrzymuje skonsolidowany dokument z wzbogaconymi figurami z umiejętności Shaper
- Emituje fragmenty gotowe do wyszukiwania z odniesieniami do figur i osadzeniami

### Indeksowanie dodatkowych dokumentów w chmurze

Aby dodać dodatkowe dokumenty do indeksu, najpierw prześlij je do źródła danych (domyślnie Blob storage).
Następnie przejdź do portalu Azure i uruchom indekser. Indekser Azure AI Search zidentyfikuje nowe dokumenty i pozyska je do indeksu.

### Usuwanie dokumentów z chmury

Aby usunąć dokumenty z indeksu, usuń je ze źródła danych (domyślnie Blob storage).
Następnie przejdź do portalu Azure i uruchom indekser. Indekser Azure AI Search zajmie się usunięciem tych dokumentów z indeksu.

### Zaplanowane indeksowanie

Jeśli chcesz, aby indekser uruchamiał się automatycznie, możesz go skonfigurować, aby [uruchamiał się zgodnie z harmonogramem](https://learn.microsoft.com/azure/search/search-howto-schedule-indexers).

## Wskazówki dotyczące debugowania

Jeśli nie jesteś pewien, czy plik został pomyślnie przesłany, możesz odpytać indeks z Azure Portal lub z REST API. Otwórz indeks i wklej zapytania poniżej na pasku wyszukiwania.

Aby zobaczyć wszystkie nazwy plików przesłane do indeksu:

```json
{
  "search": "*",
  "count": true,
  "top": 1,
  "facets": ["sourcefile"]
}
```

Aby wyszukać określone nazwy plików:

```json
{
  "search": "*",
  "count": true,
  "top": 1,
  "filter": "sourcefile eq 'employee_handbook.pdf'",
  "facets": ["sourcefile"]
}
```
