# Ocena jakości odpowiedzi RAG

[📺 Oglądaj: (seria RAG Deep Dive) Ocena jakości odpowiedzi RAG](https://www.youtube.com/watch?v=lyCLu53fb3g)

Postępuj zgodnie z tymi krokami, aby ocenić jakość odpowiedzi generowanych przez przepływ RAG.

* [Wdróż model oceny](#wdróż-model-oceny)
* [Skonfiguruj środowisko oceny](#skonfiguruj-środowisko-oceny)
* [Wygeneruj dane referencyjne](#wygeneruj-dane-referencyjne)
* [Uruchom ocenę zbiorczą](#uruchom-ocenę-zbiorczą)
* [Przejrzyj wyniki oceny](#przejrzyj-wyniki-oceny)
* [Uruchom ocenę zbiorczą na PR](#uruchom-ocenę-zbiorczą-na-pr)

## Wdróż model oceny

1. Uruchom to polecenie, aby powiedzieć `azd`, aby wdrożyć model poziomu GPT-4 do oceny:

    ```shell
    azd env set USE_EVAL true
    ```

2. Ustaw pojemność na najwyższą możliwą wartość, aby upewnić się, że ocena przebiega stosunkowo szybko. Nawet przy wysokiej pojemności może zająć dużo czasu wygenerowanie danych referencyjnych i uruchomienie ocen zbiorczych.

    ```shell
    azd env set AZURE_OPENAI_EVAL_DEPLOYMENT_CAPACITY 100
    ```

    Domyślnie zaaprowizuje to model `gpt-4o`, wersja `2024-08-06`. Aby zmienić te ustawienia, ustaw zmienne środowiskowe azd `AZURE_OPENAI_EVAL_MODEL` i `AZURE_OPENAI_EVAL_MODEL_VERSION` na żądane wartości.

3. Następnie uruchom następujące polecenie, aby aprowizować model:

    ```shell
    azd provision
    ```

## Skonfiguruj środowisko oceny

Utwórz nowe środowisko wirtualne Python i aktywuj je. Jest to obecnie wymagane ze względu na niekompatybilności między zależnościami skryptu oceny a głównym projektem.

```bash
python -m venv .evalenv
```

```bash
source .evalenv/bin/activate
```

Zainstaluj wszystkie zależności dla skryptu oceny, uruchamiając następujące polecenie:

```bash
pip install -r evals/requirements.txt
```

## Wygeneruj dane referencyjne

Wygeneruj dane referencyjne, uruchamiając następujące polecenie:

```bash
python evals/generate_ground_truth.py --numquestions=200 --numsearchdocs=1000
```

Opcje to:

* `numquestions`: Liczba pytań do wygenerowania. Sugerujemy co najmniej 200.
* `numsearchdocs`: Liczba dokumentów (fragmentów) do pobrania z indeksu wyszukiwania. Możesz pominąć opcję, aby pobrać wszystkie dokumenty, ale to znacznie zwiększy czas potrzebny na wygenerowanie danych referencyjnych. Możesz chcieć przynajmniej zacząć od podzbioru.
* `kgfile`: Istniejący plik JSON bazy wiedzy RAGAS, który zazwyczaj nazywa się `ground_truth_kg.json`. Możesz chcieć to określić, jeśli już utworzyłeś bazę wiedzy i chcesz tylko dostosować kroki generowania pytań.
* `groundtruthfile`: Plik do zapisania wygenerowanych odpowiedzi referencyjnych. Domyślnie jest to `evals/ground_truth.jsonl`.

🕰️ To może zająć dużo czasu, możliwie kilka godzin, w zależności od rozmiaru indeksu wyszukiwania.

Przejrzyj wygenerowane dane w `evals/ground_truth.jsonl` po uruchomieniu tego skryptu, usuwając wszelkie pary pytanie/odpowiedź, które nie wydają się realistycznym wejściem użytkownika.

## Uruchom ocenę zbiorczą

Przejrzyj konfigurację w `evals/evaluate_config.json`, aby upewnić się, że wszystko jest poprawnie skonfigurowane. Możesz chcieć dostosować używane metryki. Zobacz [README ai-rag-chat-evaluator](https://github.com/Azure-Samples/ai-rag-chat-evaluator) po więcej informacji o dostępnych metrykach.

Domyślnie skrypt oceny będzie oceniał każde pytanie w danych referencyjnych.
Uruchom skrypt oceny, uruchamiając następujące polecenie:

```bash
python evals/evaluate.py
```

Opcje to:

* `numquestions`: Liczba pytań do oceny. Domyślnie są to wszystkie pytania w danych referencyjnych.
* `resultsdir`: Katalog do zapisania wyników oceny. Domyślnie jest to folder z znacznikiem czasu w `evals/results`. Ta opcja może być również określona w `evaluate_config.json`.
* `targeturl`: URL działającej aplikacji do oceny. Domyślnie jest to `http://localhost:50505`. Ta opcja może być również określona w `evaluate_config.json`.

🕰️ To może zająć dużo czasu, możliwie kilka godzin, w zależności od liczby pytań referencyjnych, pojemności TPM modelu oceny i liczby żądanych metryk opartych na LLM.

## Przejrzyj wyniki oceny

Skrypt oceny wyprowadzi podsumowanie wyników oceny wewnątrz katalogu `evals/results`.

Możesz zobaczyć podsumowanie wyników ze wszystkich przebiegów oceny, uruchamiając następujące polecenie:

```bash
python -m evaltools summary evals/results
```

Porównaj odpowiedzi z danymi referencyjnymi, uruchamiając następujące polecenie:

```bash
python -m evaltools diff evals/results/baseline/
```

Porównaj odpowiedzi w dwóch przebiegach, uruchamiając następujące polecenie:

```bash
python -m evaltools diff evals/results/baseline/ evals/results/SECONDRUNHERE
```

## Uruchom ocenę zbiorczą na PR

To repozytorium zawiera przepływ pracy GitHub Action `evaluate.yaml`, który może być używany do uruchomienia oceny zmian w PR.

Aby przepływ pracy działał pomyślnie, musisz najpierw skonfigurować [ciągłą integrację](./azd.md#github-actions) dla repozytorium.

Aby uruchomić ocenę zmian w PR, członek repozytorium może opublikować komentarz `/evaluate` do PR. To wyzwoli przepływ pracy oceny, aby uruchomić ocenę zmian PR i opublikuje wyniki do PR.

## Oceń odpowiedzi RAG multimodalnego

Repozytorium zawiera również plik `evaluate_config_multimodal.json` specjalnie do oceny odpowiedzi RAG multimodalnego. Ta konfiguracja używa innego pliku referencyjnego, `ground_truth_multimodal.jsonl`, który zawiera pytania oparte na przykładowych danych, które wymagają zarówno źródeł tekstowych, jak i obrazowych do odpowiedzi.

Należy pamiętać, że ewaluator "groundedness" nie jest niezawodny dla RAG multimodalnego, ponieważ obecnie nie uwzględnia źródeł obrazów. Nadal uwzględniamy go w metrykach, ale bardziej niezawodne metryki to "relevance" i "citations matched".
