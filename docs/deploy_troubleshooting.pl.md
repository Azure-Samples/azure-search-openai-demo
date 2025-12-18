# Czat RAG: Rozwiązywanie problemów z wdrażaniem

Jeśli napotkasz błąd podczas wdrażania rozwiązania czatu RAG przy użyciu [kroków wdrażania](../README.pl.md#wdrażanie), ten przewodnik pomoże Ci rozwiązać typowe problemy.

1. Próbujesz utworzyć zasoby w regionach, które nie są włączone dla Azure OpenAI (np. East US 2 zamiast East US) lub gdzie model, którego próbujesz użyć, nie jest włączony. Zobacz [tę macierz dostępności modeli](https://aka.ms/oai/models).

1. Przekroczyłeś przydział, najczęściej liczbę zasobów na region. Zobacz [ten artykuł o przydziałach i limitach](https://aka.ms/oai/quotas).

1. Otrzymujesz konflikty "ta sama nazwa zasobu niedozwolona". Prawdopodobnie dzieje się tak, ponieważ uruchomiłeś przykład wiele razy i usuwałeś zasoby, które za każdym razem tworzyłeś, ale zapominasz je wyczyścić. Azure przechowuje zasoby przez 48 godzin, chyba że wyczyscisz je z soft delete. Zobacz [ten artykuł o czyszczeniu zasobów](https://learn.microsoft.com/azure/cognitive-services/manage-resources?tabs=azure-portal#purge-a-deleted-resource).

1. Widzisz `CERTIFICATE_VERIFY_FAILED`, gdy uruchamia się skrypt `prepdocs.py`. Jest to zwykle spowodowane nieprawidłową konfiguracją certyfikatów SSL na Twojej maszynie. Wypróbuj sugestie w tej [odpowiedzi StackOverflow](https://stackoverflow.com/a/43855394).

1. Po uruchomieniu `azd up` i odwiedzeniu strony internetowej widzisz '404 Not Found' w przeglądarce. Poczekaj 10 minut i spróbuj ponownie, ponieważ może nadal się uruchamiać. Następnie spróbuj uruchomić `azd deploy` i ponownie poczekaj. Jeśli nadal napotkasz błędy z wdrożoną aplikacją i wdrażasz do App Service, zapoznaj się z [przewodnikiem po debugowaniu wdrożeń App Service](/docs/appservice.md) *(angielski)*. Proszę zgłoś problem, jeśli logi nie pomogą Ci rozwiązać błędu.
