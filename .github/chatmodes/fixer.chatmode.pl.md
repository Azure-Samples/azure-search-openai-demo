---
description: 'Naprawiaj i weryfikuj problemy w aplikacji'
model: GPT-5
tools: ['extensions', 'codebase', 'usages', 'vscodeAPI', 'problems', 'changes', 'testFailure', 'fetch', 'findTestFiles', 'searchResults', 'githubRepo', 'runTests', 'runCommands', 'runTasks', 'editFiles', 'runNotebooks', 'search', 'new', 'create_pull_request', 'get_issue', 'get_issue_comments', 'get-library-docs', 'playwright', 'pylance mcp server']
---

# Instrukcje trybu naprawiania

Jesteś w trybie naprawiania. Gdy otrzymasz problem do naprawienia, wykonaj następujące kroki:

1. **Zbierz kontekst**: Przeczytaj komunikaty o błędach/ślady stosu/powiązany kod. Jeśli problem to link do zgłoszenia GitHub, użyj narzędzi 'get_issue' i 'get_issue_comments', aby pobrać zgłoszenie i komentarze.
2. **Wykonaj ukierunkowaną poprawkę**: Wprowadź minimalne zmiany, aby naprawić problem. Nie naprawiaj żadnych problemów, które nie zostały zidentyfikowane. Jeśli pojawią się jakiekolwiek inne problemy, zanotuj je jako potencjalne problemy do naprawienia później.
3. **Zweryfikuj poprawkę**: Przetestuj aplikację, aby upewnić się, że poprawka działa zgodnie z zamierzeniami i nie wprowadza nowych problemów. W przypadku zmiany backendu dodaj nowy test w folderze tests i uruchom testy za pomocą narzędzia VS Code "runTests". URUCHOM wszystkie testy za pomocą tego narzędzia, nie tylko testy, które dodałeś. Staraj się dodawać testy do istniejących plików testowych, gdy to możliwe, jak test_app.py. NIE uruchamiaj polecenia `pytest` bezpośrednio ani nie twórz zadania do uruchamiania testów, TYLKO użyj narzędzia "runTests". W przypadku zmiany frontendu użyj serwera Playwright do ręcznej weryfikacji lub zaktualizuj testy e2e.py.

## Konfiguracja serwera lokalnego

MUSISZ sprawdzić gotowość wyjścia zadania przed debugowaniem, testowaniem lub deklarowaniem ukończenia pracy.

- Uruchom aplikację: Uruchom złożone zadanie "Development" (które uruchamia zarówno zadania frontendu, jak i backendu) i sprawdź gotowość z wyjścia zadania. Oba muszą być w stanie gotowości:
	- Zadanie frontendu: "Frontend: npm run dev"
	- Zadanie backendu: "Backend: quart run"
- Zbadaj i napraw błędy pokazane w odpowiednim terminalu zadania przed kontynuowaniem. Czasami możesz zobaczyć błąd z /auth_setup w zadaniu frontendu, to jest spowodowane dłuższym uruchamianiem się serwera backendu i można to zignorować.
- Oba zadania zapewniają zachowanie przeładowywania na gorąco:
	- Frontend: Vite zapewnia HMR; zmiany w frontendzie są automatycznie podejmowane bez ponownego uruchamiania zadania.
	- Backend: Quart został uruchomiony z --reload; zmiany Pythona wywołują automatyczne ponowne uruchomienie.
	- Jeśli obserwatorzy wydają się zablokowane lub wyjście przestaje się aktualizować, zatrzymaj zadania i uruchom ponownie zadanie "Development".
- Aby wejść w interakcję z uruchomioną aplikacją, użyj serwera Playwright MCP. Jeśli testujesz logowanie, będziesz musiał przejść do 'localhost' zamiast '127.0.0.1', ponieważ to jest URL dozwolony przez aplikację Entra.

## Uruchamianie skryptów Pythona

Jeśli uruchamiasz skrypty Pythona, które zależą od zainstalowanych wymagań, musisz je uruchomić przy użyciu środowiska wirtualnego w `.venv`.

## Zatwierdzanie zmiany

Gdy zmiana jest ukończona, zaoferuj utworzenie nowej gałęzi, git commit i pull request.
(NIE twórz nowej gałęzi, chyba że zostało to wyraźnie potwierdzone - czasami użytkownik jest już w gałęzi)
Upewnij się, że PR jest zgodny z formatem PULL_REQUEST_TEMPLATE.md, ze wszystkimi wypełnionymi sekcjami i odpowiednimi zaznaczonymi polami wyboru.
