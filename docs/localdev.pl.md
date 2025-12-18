# Czat RAG: Lokalne rozwijanie aplikacji czatu

Po wdrożeniu aplikacji do Azure możesz chcieć kontynuować rozwój lokalnie. Ten przewodnik wyjaśnia, jak uruchomić aplikację lokalnie, w tym hot reloading i debugowanie.

* [Uruchamianie serwera deweloperskiego z wiersza poleceń](#uruchamianie-serwera-deweloperskiego-z-wiersza-poleceń)
* [Hot reloading plików frontendu i backendu](#hot-reloading-plików-frontendu-i-backendu)
* [Używanie zadania VS Code "Development"](#używanie-zadania-vs-code-development)
* [Używanie trybu debugowania Copilot Chat](#używanie-trybu-debugowania-copilot-chat)
* [Używanie VS Code "Run and Debug"](#używanie-vs-code-run-and-debug)
* [Używanie lokalnego API kompatybilnego z OpenAI](#używanie-lokalnego-api-kompatybilnego-z-openai)
  * [Używanie serwera Ollama](#używanie-serwera-ollama)
  * [Używanie serwera llamafile](#używanie-serwera-llamafile)

## Uruchamianie serwera deweloperskiego z wiersza poleceń

Możesz uruchomić lokalnie **tylko** po pomyślnym uruchomieniu polecenia `azd up`. Jeśli jeszcze tego nie zrobiłeś, postępuj zgodnie z krokami w [Wdrażaniu Azure](../README.pl.md#wdrażanie) powyżej.

1. Uruchom `azd auth login`
2. Uruchom serwer:

  Windows:

  ```shell
  ./app/start.ps1
  ```

  Linux/Mac:

  ```shell
  ./app/start.sh
  ```

  VS Code: Uruchom zadanie "VS Code Task: Start App".

## Hot reloading plików frontendu i backendu

Gdy uruchamiasz `./start.ps1` lub `./start.sh`, pliki backendu będą obserwowane i automatycznie przeładowywane. Jednak pliki frontendu nie będą obserwowane i automatycznie przeładowywane.

Aby włączyć hot reloading plików frontendu, otwórz nowy terminal i przejdź do katalogu frontendu:

```shell
cd app/frontend
```

Następnie uruchom:

```shell
npm run dev
```

Powinieneś zobaczyć:

```shell
> frontend@0.0.0 dev
> vite


  VITE v4.5.1  ready in 957 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

Przejdź do URL wyświetlonego w terminalu (w tym przypadku `http://localhost:5173/`). Ten lokalny serwer będzie obserwował i przeładowywał pliki frontendu. Wszystkie żądania backendu będą kierowane do serwera Python zgodnie z `vite.config.ts`.

Następnie, gdy wprowadzisz zmiany w plikach frontendu, zmiany zostaną automatycznie przeładowane, bez konieczności odświeżania przeglądarki.

Alternatywnie możesz uruchomić oba serwery z hot reloading, używając zadania VS Code "Development". Zobacz [Używanie zadania VS Code "Development"](#używanie-zadania-vs-code-development).

## Używanie zadania VS Code "Development"

Jeśli wolisz zadania VS Code do hot reloading obu serwerów jednocześnie, użyj zadania "Development" zdefiniowanego w `.vscode/tasks.json`.

Jak je uruchomić:

* Uruchom Build Task (Shift+Cmd+B), aby uruchomić domyślne zadanie build, którym jest "Development".
* Lub otwórz paletę poleceń (Shift+Cmd+P) i uruchom: "Tasks: Run Task" -> "Development".

Co robi:

* Uruchamia dwa zadania w tle w dedykowanych panelach:
  * "Frontend: npm run dev" z `app/frontend` (Vite HMR dla natychmiastowych aktualizacji frontendu)
  * "Backend: quart run" z `app/backend` (Quart z `--reload` dla automatycznych ponownych uruchomień backendu)

Wskaźniki gotowości:

* Frontend jest gotowy, gdy Vite wydrukuje Local URL, na przykład: `Local: http://localhost:5173/`.
* Backend jest gotowy, gdy Hypercorn raportuje: `Running on http://127.0.0.1:50505` (port może się różnić).

Wskazówki:

* Aby zatrzymać oba, uruchom: "Tasks: Terminate Task" i wybierz uruchomione zadania.
* Jeśli obserwatory się zatrzymają, zakończ i uruchom "Development" ponownie.
* Zmiany frontendu stosują się przez HMR; zmiany Pythona backendu automatycznie się przeładowują. Nie trzeba ręcznego ponownego uruchamiania.

## Używanie trybu debugowania Copilot Chat

Możesz użyć GitHub Copilot Chat z niestandardowym trybem "debug", aby usprawnić rozwiązywanie problemów w tym repozytorium.

Wymagania wstępne:

* VS Code 1.101+ (niestandardowe tryby czatu są w wersji zapoznawczej)
* Dostęp do GitHub Copilot i Copilot Chat
* Serwer Playwright MCP i serwer GitHub MCP (opcjonalnie)

Aby dowiedzieć się więcej o funkcji trybów czatu, przeczytaj [dokumentację VS Code dla trybów czatu](https://code.visualstudio.com/docs/copilot/chat/chat-modes).

Aby użyć trybu debugowania:

* Otwórz widok czatu.
* Użyj menu rozwijanego trybu czatu u góry widoku czatu, aby wybrać tryb "debug".
* Zacznij czatować w tym trybie; instrukcje i narzędzia z pliku repozytorium zostaną zastosowane automatycznie.
* Tryb użyje zadań z .vscode/tasks.json, aby uruchomić serwer frontendu i backendu, i powinien być w stanie odczytać wszelkie błędy w wyjściu.
* Tryb może również używać narzędzi z serwera Playwright MCP i serwera GitHub MCP, jeśli te serwery są zainstalowane w VS Code.

Co istotne, ten tryb nie będzie faktycznie używał debuggera opartego na punktach przerwania. Czytaj dalej, aby dowiedzieć się, jak używać punktów przerwania podczas debugowania kodu Python.

## Używanie VS Code "Run and Debug"

Ten projekt zawiera konfiguracje zdefiniowane w `.vscode/launch.json`, które pozwalają uruchamiać i debugować aplikację bezpośrednio z VS Code:

* "Backend (Python)": Uruchamia serwer backendu Python, domyślnie na porcie 50505.
* "Frontend": Uruchamia serwer frontendu za pomocą Vite, zazwyczaj na porcie 5173.
* "Frontend & Backend": Konfiguracja złożona, która uruchamia zarówno serwer frontendu, jak i backendu.

Gdy uruchamiasz te konfiguracje, możesz ustawiać punkty przerwania w swoim kodzie i debugować, jak byś to robił w normalnej sesji debugowania VS Code.

## Używanie lokalnego API kompatybilnego z OpenAI

Możesz chcieć zaoszczędzić koszty, rozwijając się przeciwko lokalnemu serwerowi LLM, takiemu jak
[llamafile](https://github.com/Mozilla-Ocho/llamafile/). Należy pamiętać, że lokalny LLM
będzie zazwyczaj wolniejszy i nie tak wyrafinowany.

Gdy lokalny serwer LLM jest uruchomiony i obsługuje punkt końcowy kompatybilny z OpenAI, ustaw te zmienne środowiskowe:

```shell
azd env set USE_VECTORS false
azd env set OPENAI_HOST local
azd env set OPENAI_BASE_URL <twój lokalny punkt końcowy>
azd env set AZURE_OPENAI_CHATGPT_MODEL local-model-name
```

Następnie uruchom ponownie lokalny serwer deweloperski.
Powinieneś teraz być w stanie używać zakładki "Ask".

⚠️ Ograniczenia:

* Zakładka "Chat" będzie działać tylko wtedy, gdy lokalny model językowy obsługuje wywołanie funkcji.
* Twój tryb wyszukiwania musi być tylko tekstowy (bez wektorów), ponieważ indeks wyszukiwania jest wypełniony tylko osadzeniami generowanymi przez OpenAI, a lokalny host OpenAI nie może ich generować.
* Historia rozmów zostanie obcięta za pomocą tokenizerów GPT, które mogą nie być takie same jak tokenizer lokalnego modelu, więc jeśli masz długą rozmowę, możesz skończyć z błędami limitu tokenów.

> [!NOTE]
> Musisz ustawić `OPENAI_HOST` z powrotem na wartość nielocalną ("azure", "azure_custom" lub "openai")
> przed uruchomieniem `azd up` lub `azd provision`, ponieważ wdrożony backend nie może uzyskać dostępu do Twojego lokalnego serwera.

### Używanie serwera Ollama

Na przykład, aby wskazać na lokalny serwer Ollama uruchamiający model `llama3.1:8b`:

```shell
azd env set OPENAI_HOST local
azd env set OPENAI_BASE_URL http://localhost:11434/v1
azd env set AZURE_OPENAI_CHATGPT_MODEL llama3.1:8b
azd env set USE_VECTORS false
```

Jeśli uruchamiasz aplikację wewnątrz VS Code Dev Container, użyj tego lokalnego URL zamiast tego:

```shell
azd env set OPENAI_BASE_URL http://host.docker.internal:11434/v1
```

### Używanie serwera llamafile

Aby wskazać na lokalny serwer llamafile uruchomiony na domyślnym porcie:

```shell
azd env set OPENAI_HOST local
azd env set OPENAI_BASE_URL http://localhost:8080/v1
azd env set USE_VECTORS false
```

Llamafile *nie* wymaga określenia nazwy modelu.

Jeśli uruchamiasz aplikację wewnątrz VS Code Dev Container, użyj tego lokalnego URL zamiast tego:

```shell
azd env set OPENAI_BASE_URL http://host.docker.internal:8080/v1
```
