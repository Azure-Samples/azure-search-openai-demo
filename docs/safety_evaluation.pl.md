# Ocena bezpieczeństwa odpowiedzi RAG

Podczas wdrażania aplikacji RAG do produkcji, powinieneś ocenić bezpieczeństwo odpowiedzi generowanych przez przepływ RAG. Jest to ważne, aby upewnić się, że odpowiedzi są odpowiednie i nie zawierają żadnych szkodliwych lub wrażliwych treści. Ten projekt zawiera skrypty, które używają usług Azure AI do symulacji użytkownika o charakterze przeciwnym i oceny bezpieczeństwa odpowiedzi generowanych w odpowiedzi na te przeciwstawne zapytania.

* [Wdróż projekt Azure AI](#wdróż-projekt-azure-ai)
* [Symuluj i oceniaj przeciwstawnych użytkowników](#symuluj-i-oceniaj-przeciwstawnych-użytkowników)
* [Przejrzyj wyniki oceny bezpieczeństwa](#przejrzyj-wyniki-oceny-bezpieczeństwa)

## Wdróż projekt Azure AI

Aby użyć symulatora przeciwnego i ewaluatorów bezpieczeństwa, potrzebujesz projektu Azure AI wewnątrz Azure AI Hub.

1. Uruchom to polecenie, aby powiedzieć `azd`, aby aprowizować projekt Azure AI i hub:

    ```shell
    azd env set USE_AI_PROJECT true
    ```

2. Następnie uruchom następujące polecenie, aby aprowizować projekt:

    ```shell
    azd provision
    ```

## Symuluj i oceniaj przeciwstawnych użytkowników

Uruchom następujące polecenie, aby symulować przeciwstawne zapytania i ocenić bezpieczeństwo odpowiedzi generowanych w odpowiedzi na te zapytania:

```shell
python evals/safety_evaluation.py --target_url <TARGET_URL> --max_simulations <MAX_RESULTS>
```

* `--target_url`: Docelowy URL dla wywołania zwrotnego. Domyślnie to `http://localhost:50505/chat`.
* `--max_simulations`: Maksymalna liczba symulowanych zapytań użytkownika. Domyślnie to `200`. Im wyższa liczba, tym dłużej trwa ocena. Domyślne `200` symulacji zajmie około 25 minut, co obejmuje zarówno czas na wygenerowanie symulowanych danych, jak i czas na ich ocenę.

## Przejrzyj wyniki oceny bezpieczeństwa

To polecenie wygeneruje raport w `safety_results.json`.
Wyniki będą wyglądać tak:

```json
{
  "hate_unfairness": {
    "low_count": 20,
    "score_total": 8,
    "mean_score": 0.4,
    "low_rate": 1.0
  },
  "sexual": {
    "low_count": 20,
    "score_total": 9,
    "mean_score": 0.45,
    "low_rate": 1.0
  },
  "violence": {
    "low_count": 20,
    "score_total": 9,
    "mean_score": 0.45,
    "low_rate": 1.0
  },
  "self_harm": {
    "low_count": 20,
    "score_total": 10,
    "mean_score": 0.5,
    "low_rate": 1.0
  }
}
```

Idealny wynik to `low_rate` wynoszący 1.0 i `mean_score` wynoszący 0.0. `low_rate` wskazuje ułamek odpowiedzi, które zostały zgłoszone jako "Niskie" lub "Bardzo niskie" przez ewaluatora. `mean_score` to średni wynik wszystkich odpowiedzi, gdzie 0 to bardzo bezpieczna odpowiedź, a 7 to bardzo niebezpieczna odpowiedź.

## Zasoby

Aby dowiedzieć się więcej o usługach Azure AI używanych w tym projekcie, przejrzyj skrypt i zapoznaj się z następującą dokumentacją:

* [Generuj symulowane dane do oceny](https://learn.microsoft.com/azure/ai-studio/how-to/develop/simulator-interaction-data)
* [Oceniaj za pomocą Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-studio/how-to/develop/evaluate-sdk)
