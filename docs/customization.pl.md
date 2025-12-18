# Czat RAG: Dostosowywanie aplikacji czatu

[📺 Oglądaj: (seria RAG Deep Dive) Dostosowywanie aplikacji](https://www.youtube.com/watch?v=D3slfMqydHc)

> **Wskazówka:** Zalecamy używanie trybu GitHub Copilot Agent podczas dodawania nowych funkcji lub wprowadzania zmian w kodzie. Ten projekt zawiera plik [AGENTS.md](../AGENTS.pl.md), który prowadzi Copilot do generowania kodu zgodnie z konwencjami projektu.

Ten przewodnik zawiera więcej szczegółów dotyczących dostosowywania aplikacji czatu RAG.

- [Używanie własnych danych](#używanie-własnych-danych)
- [Dostosowywanie interfejsu użytkownika](#dostosowywanie-interfejsu-użytkownika)
- [Dostosowywanie backendu](#dostosowywanie-backendu)
  - [Podejścia Chat/Ask](#podejścia-chatask)
    - [Podejście Chat](#podejście-chat)
    - [Podejście Ask](#podejście-ask)
- [Poprawa jakości odpowiedzi](#poprawa-jakości-odpowiedzi)
  - [Zidentyfikuj punkt problemu](#zidentyfikuj-punkt-problemu)
  - [Poprawa wyników OpenAI ChatCompletion](#poprawa-wyników-openai-chatcompletion)
  - [Poprawa wyników Azure AI Search](#poprawa-wyników-azure-ai-search)
  - [Ocena jakości odpowiedzi](#ocena-jakości-odpowiedzi)

## Używanie własnych danych

Aplikacja czatu została zaprojektowana do pracy z dowolnymi dokumentami PDF. Przykładowe dane są dostarczone, aby pomóc Ci szybko rozpocząć, ale możesz łatwo zastąpić je własnymi danymi. Najpierw będziesz chciał usunąć wszystkie istniejące dane, a następnie dodać własne. Zobacz [przewodnik po pozyskiwaniu danych](data_ingestion.md) *(angielski)* po więcej szczegółów.

## Dostosowywanie interfejsu użytkownika

Frontend jest zbudowany przy użyciu [React](https://reactjs.org/) i [komponentów Fluent UI](https://react.fluentui.dev/). Komponenty frontendu są przechowywane w folderze `app/frontend/src`. Aby zmodyfikować tytuł strony, tekst nagłówka, przykładowe pytania i inne elementy interfejsu użytkownika, możesz dostosować plik `app/frontend/src/locales/{en/es/fr/jp/it}/translation.json` dla różnych języków (angielski jest domyślny). Podstawowe ciągi znaków i etykiety używane w całej aplikacji są zdefiniowane w tych plikach.

## Dostosowywanie backendu

Backend jest zbudowany przy użyciu [Quart](https://quart.palletsprojects.com/), frameworka Python dla asynchronicznych aplikacji internetowych. Kod backendu jest przechowywany w folderze `app/backend`. Frontend i backend komunikują się przez HTTP za pomocą odpowiedzi JSON lub strumieniowanych NDJSON. Dowiedz się więcej w [przewodniku po protokole HTTP](http_protocol.md) *(angielski)*.

### Podejścia Chat/Ask

Zazwyczaj główny kod backendu, który będziesz chciał dostosować, znajduje się w folderze `app/backend/approaches`, który zawiera klasy zasilające zakładki Chat i Ask. Każda klasa używa innego podejścia RAG (Retrieval Augmented Generation), które obejmują komunikaty systemowe, które powinny zostać zmienione, aby pasowały do Twoich danych

#### Podejście Chat

Zakładka czatu używa podejścia zaprogramowanego w [chatreadretrieveread.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/chatreadretrieveread.py).

1. **Przepisywanie zapytania**: Wywołuje API OpenAI ChatCompletion, aby przekształcić pytanie użytkownika w dobre zapytanie wyszukiwania, używając promptu i narzędzi z [chat_query_rewrite.prompty](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/prompts/chat_query_rewrite.prompty).
2. **Wyszukiwanie**: Odpytuje Azure AI Search o wyniki wyszukiwania dla tego zapytania (opcjonalnie używając osadzeń wektorowych dla tego zapytania).
3. **Odpowiadanie**: Następnie wywołuje API OpenAI ChatCompletion, aby odpowiedzieć na pytanie na podstawie źródeł, używając promptu z [chat_answer_question.prompty](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/prompts/chat_answer_question.prompty). To wywołanie obejmuje również historię poprzednich wiadomości (lub tyle wiadomości, ile mieści się w limicie tokenów modelu).

Prompty są obecnie dostosowane do przykładowych danych, ponieważ zaczynają się od "Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook." Zmodyfikuj prompty [chat_query_rewrite.prompty](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/prompts/chat_query_rewrite.prompty) i [chat_answer_question.prompty](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/prompts/chat_answer_question.prompty), aby pasowały do Twoich danych.

##### Chat z funkcją multimodalną

Jeśli postępowałeś zgodnie z instrukcjami w [przewodniku multimodalnym](multimodal.pl.md), aby włączyć multimodalne RAG,
istnieje kilka różnic w podejściu czatu:

1. **Przepisywanie zapytania**: Bez zmian.
2. **Wyszukiwanie**: W tym kroku oblicza osadzenie wektorowe dla pytania użytkownika za pomocą [API wektoryzacji tekstu Azure AI Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/how-to/image-retrieval#call-the-vectorize-text-api) i przekazuje to do Azure AI Search, aby porównać z polami osadzania obrazów w zaindeksowanych dokumentach. Dla każdego pasującego dokumentu pobiera każdy powiązany obraz z Azure Blob Storage i konwertuje go na kodowanie base64.
3. **Odpowiadanie**: Gdy łączy wyniki wyszukiwania i pytanie użytkownika, zawiera obrazy zakodowane w base64 i wysyła zarówno tekst, jak i obrazy do multimodalnego LLM. Model generuje odpowiedź, która zawiera cytowania do obrazów, a interfejs użytkownika renderuje obrazy, gdy cytowanie jest kliknięte.

Ustawienia można dostosować, aby wyłączyć obliczanie osadzeń wektorowych obrazów lub wyłączyć wysyłanie wejść obrazowych do LLM, jeśli jest to pożądane.

#### Podejście Ask

Zakładka ask używa podejścia zaprogramowanego w [retrievethenread.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/retrievethenread.py).

1. **Wyszukiwanie**: Odpytuje Azure AI Search o wyniki wyszukiwania dla pytania użytkownika (opcjonalnie używając osadzeń wektorowych dla tego pytania).
2. **Odpowiadanie**: Następnie łączy wyniki wyszukiwania i pytanie użytkownika i wywołuje API OpenAI ChatCompletion, aby odpowiedzieć na pytanie na podstawie źródeł, używając promptu z [ask_answer_question.prompty](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/prompts/ask_answer_question.prompty).

Prompt dla kroku 2 jest obecnie dostosowany do przykładowych danych, ponieważ zaczyna się od "Assistant helps the company employees with their questions about internal documents." Zmodyfikuj [ask_answer_question.prompty](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/prompts/ask_answer_question.prompty), aby pasował do Twoich danych.

#### Ask z funkcją multimodalną

Jeśli postępowałeś zgodnie z instrukcjami w [przewodniku multimodalnym](multimodal.pl.md), aby włączyć multimodalne RAG,
istnieje kilka różnic w podejściu ask:

1. **Wyszukiwanie**: W tym kroku również oblicza osadzenie wektorowe dla pytania użytkownika za pomocą [API wektoryzacji tekstu Azure AI Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/how-to/image-retrieval#call-the-vectorize-text-api) i przekazuje to do Azure AI Search, aby porównać z polami osadzania obrazów w zaindeksowanych dokumentach. Dla każdego pasującego dokumentu pobiera każdy powiązany obraz z Azure Blob Storage i konwertuje go na kodowanie base64.
2. **Odpowiadanie**: Gdy łączy wyniki wyszukiwania i pytanie użytkownika, zawiera obrazy zakodowane w base64 i wysyła zarówno tekst, jak i obrazy do multimodalnego LLM. Model generuje odpowiedź, która zawiera cytowania do obrazów, a interfejs użytkownika renderuje obrazy, gdy cytowanie jest kliknięte.

Ustawienia można dostosować, aby wyłączyć obliczanie osadzeń wektorowych obrazów lub wyłączyć wysyłanie wejść obrazowych do LLM, jeśli jest to pożądane.

#### Utrwalanie nadpisań ustawień

Interfejs użytkownika zapewnia menu "Developer Settings" do dostosowywania podejść, takich jak wyłączanie rankera semantycznego lub używanie wyszukiwania wektorowego.
Te ustawienia są przekazywane w polu "context" żądania do backendu i nie są zapisywane na stałe.
Jednak jeśli znajdziesz ustawienie, które chcesz uczynić stałym, istnieją dwa podejścia:

1. Zmień wartości domyślne w frontendzie. Znajdziesz wartości domyślne w `Chat.tsx` i `Ask.tsx`. Na przykład ta linia kodu ustawia domyślny tryb wyszukiwania na Hybrid:

    ```typescript
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    ```

    Możesz zmienić wartość domyślną na Text, zmieniając kod na:

    ```typescript
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Text);
    ```

2. Zmień nadpisania w backendzie. Każde z podejść ma metodę `run`, która przyjmuje parametr `context`, a pierwsza linia kodu wyodrębnia nadpisania z tego `context`. Tam możesz nadpisać dowolne ustawienia. Na przykład, aby zmienić tryb wyszukiwania na tekst:

    ```python
    overrides = context.get("overrides", {})
    overrides["retrieval_mode"] = "text"
    ```

    Zmieniając ustawienie w backendzie, możesz bezpiecznie usunąć interfejs Developer Settings z frontendu, jeśli nie chcesz go udostępniać swoim użytkownikom.

## Poprawa jakości odpowiedzi

Gdy już uruchamiasz aplikację czatu na własnych danych i z własnym dostosowanym promptem systemowym,
następnym krokiem jest przetestowanie aplikacji za pomocą pytań i odnotowanie jakości odpowiedzi.
Jeśli zauważysz jakiekolwiek odpowiedzi, które nie są tak dobre, jak byś chciał, oto proces ich poprawy.

### Zidentyfikuj punkt problemu

Pierwszym krokiem jest zidentyfikowanie, gdzie występuje problem. Na przykład, jeśli używasz zakładki Chat, problem może być:

1. API OpenAI ChatCompletion nie generuje dobrego zapytania wyszukiwania na podstawie pytania użytkownika
2. Azure AI Search nie zwraca dobrych wyników wyszukiwania dla zapytania
3. API OpenAI ChatCompletion nie generuje dobrej odpowiedzi na podstawie wyników wyszukiwania i pytania użytkownika

Możesz spojrzeć na zakładkę "Thought process" w aplikacji czatu, aby zobaczyć każdy z tych kroków
i określić, który jest problemem.

### Poprawa wyników OpenAI ChatCompletion

Jeśli problem dotyczy wywołań API ChatCompletion (kroki 1 lub 3 powyżej), możesz spróbować zmienić odpowiedni prompt.

Po zmianie promptu upewnij się, że zadajesz to samo pytanie wiele razy, aby sprawdzić, czy ogólna jakość się poprawiła, i [uruchom ocenę](#ocena-jakości-odpowiedzi), gdy będziesz zadowolony ze zmian. API ChatCompletion może dawać różne wyniki za każdym razem, nawet dla temperatury 0.0, ale szczególnie dla wyższej temperatury niż ta (jak nasza domyślna 0.7 dla kroku 3).

Możesz również spróbować zmienić parametry ChatCompletion, takie jak temperatura, aby sprawdzić, czy to poprawia wyniki dla Twojej domeny.

### Poprawa wyników Azure AI Search

Jeśli problem dotyczy Azure AI Search (krok 2 powyżej), pierwszym krokiem jest sprawdzenie, jakie parametry wyszukiwania używasz. Ogólnie rzecz biorąc, najlepsze wyniki znajdują się przy wyszukiwaniu hybrydowym (tekst + wektory) plus dodatkowy krok semantycznego ponownego rankingu, i to właśnie włączyliśmy domyślnie. Może być jednak kilka domen, w których ta kombinacja nie jest optymalna. Sprawdź ten post na blogu, który [ocenia strategie wyszukiwania AI](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/azure-ai-search-outperforming-vector-search-with-hybrid-retrieval-and-ranking-ca/3929167), aby lepiej zrozumieć różnice, lub obejrzyj ten [film RAG Deep Dive o AI Search](https://www.youtube.com/watch?v=ugJy9QkgLYg).

#### Konfigurowanie parametrów w aplikacji

Możesz zmienić wiele parametrów wyszukiwania w "Developer settings" w frontendzie i sprawdzić, czy wyniki poprawiają się dla Twoich zapytań. Najbardziej istotne opcje:

![Zrzut ekranu opcji wyszukiwania w ustawieniach deweloperskich](images/screenshot_searchoptions.png)

#### Konfigurowanie parametrów w Azure Portal

Możesz uznać za łatwiejsze eksperymentowanie z opcjami wyszukiwania za pomocą eksploratora indeksu w Azure Portal.
Otwórz zasób Azure AI Search, wybierz zakładkę Indexes i wybierz tam indeks.

Następnie użyj widoku JSON eksploratora wyszukiwania i upewnij się, że określasz te same opcje, których używasz w aplikacji. Na przykład to zapytanie reprezentuje wyszukiwanie z skonfigurowanym rankerem semantycznym:

```json
{
  "search": "eye exams",
  "queryType": "semantic",
  "semanticConfiguration": "default",
  "queryLanguage": "en-us",
  "speller": "lexicon",
  "top": 3
}
```

Możesz również użyć parametru `highlight`, aby zobaczyć, jaki tekst jest dopasowywany w polu `content` w wynikach wyszukiwania.

```json
{
    "search": "eye exams",
    "highlight": "content"
    ...
}
```

![Zrzut ekranu eksploratora wyszukiwania z podświetlonymi wynikami](images/screenshot_searchindex.png)

Eksplorator wyszukiwania działa dobrze do testowania tekstu, ale trudniej jest go używać z wektorami, ponieważ musiałbyś również obliczyć osadzenie wektorowe i wysłać je. Prawdopodobnie łatwiej jest używać frontendu aplikacji do testowania wektorów/wyszukiwania hybrydowego.

#### Inne podejścia do poprawy wyników wyszukiwania

Oto dodatkowe sposoby poprawy wyników wyszukiwania:

- Dodanie dodatkowych metadanych do pola "content", takich jak tytuł dokumentu, aby można je było dopasować w wynikach wyszukiwania. Zmodyfikuj [searchmanager.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/prepdocslib/searchmanager.py), aby uwzględnić więcej tekstu w polu `content`.
- Uczynienie dodatkowych pól przeszukiwalnymi przez krok wyszukiwania pełnotekstowego. Na przykład pole "sourcepage" nie jest obecnie przeszukiwalne, ale możesz uczynić je `SearchableField` z `searchable=True` w [searchmanager.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/prepdocslib/searchmanager.py). Taka zmiana wymaga [przebudowania indeksu](https://learn.microsoft.com/azure/search/search-howto-reindex#change-an-index-schema).
- Użycie wywołania funkcji do wyszukiwania według określonych pól, takich jak wyszukiwanie według nazwy pliku. Zobacz ten post na blogu o [wywołaniu funkcji dla strukturalnego wyszukiwania](https://blog.pamelafox.org/2024/03/rag-techniques-using-function-calling.html).
- Użycie innej strategii podziału dla dokumentów lub modyfikacja istniejących, aby poprawić fragmenty, które są indeksowane. Możesz znaleźć obecnie dostępne splitter w [textsplitter.py](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/prepdocslib/textsplitter.py).

### Ocena jakości odpowiedzi

Po wprowadzeniu zmian do promptów lub ustawień będziesz chciał rygorystycznie ocenić wyniki, aby sprawdzić, czy się poprawiły. Postępuj zgodnie z [przewodnikiem po ocenie](./evaluation.pl.md), aby dowiedzieć się, jak uruchamiać oceny, przeglądać wyniki i porównywać odpowiedzi w różnych przebiegach.
