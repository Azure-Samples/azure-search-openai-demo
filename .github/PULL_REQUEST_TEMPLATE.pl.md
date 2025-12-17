## Cel

<!-- Opisz zamiar proponowanych zmian. Jaki problem rozwiązuje lub jaką funkcjonalność dodaje? -->


## Czy to wprowadza zmianę powodującą niezgodność wsteczną?

Gdy programiści wykonają merge z main i uruchomią serwer, azd up lub azd deploy, czy to spowoduje błąd?
Jeśli nie jesteś pewien, wypróbuj to w starym środowisku.

```
[ ] Tak
[ ] Nie
```

## Czy to wymaga zmian w dokumentacji learn.microsoft.com?

To repozytorium jest cytowane w [tym samouczku](https://learn.microsoft.com/azure/developer/python/get-started-app-chat-template),
który zawiera instrukcje wdrażania, ustawień i użytkowania. Jeśli tekst lub zrzut ekranu musi się zmienić w samouczku,
zaznacz poniższe pole i powiadom autora samouczka. Pracownik Microsoft może to zrobić za Ciebie, jeśli jesteś zewnętrznym współtwórcą.

```
[ ] Tak
[ ] Nie
```

## Typ zmiany

```
[ ] Poprawka błędu
[ ] Funkcja
[ ] Aktualizacja stylu kodu (formatowanie, zmienne lokalne)
[ ] Refaktoryzacja (brak zmian funkcjonalnych, brak zmian api)
[ ] Zmiany treści dokumentacji
[ ] Inne... Proszę opisz:
```

## Lista kontrolna jakości kodu

Zobacz [CONTRIBUTING.md](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/CONTRIBUTING.md#submit-pr) po więcej szczegółów.

- [ ] Wszystkie bieżące testy przechodzą (`python -m pytest`).
- [ ] Dodałem testy, które dowodzą, że moja poprawka jest skuteczna lub że moja funkcja działa
- [ ] Uruchomiłem `python -m pytest --cov`, aby zweryfikować 100% pokrycia dodanych linii
- [ ] Uruchomiłem `python -m mypy`, aby sprawdzić błędy typów
- [ ] Użyłem hooków pre-commit lub uruchomiłem `ruff` i `black` ręcznie na moim kodzie.
