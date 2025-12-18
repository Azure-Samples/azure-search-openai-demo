<!--
---
name: Czat RAG z prywatnymi punktami końcowymi
description: Skonfiguruj dostęp do aplikacji czatu tak, aby była dostępna tylko z prywatnych punktów końcowych.
languages:
- python
- typescript
- bicep
- azdeveloper
products:
- azure-openai
- azure-cognitive-search
- azure-app-service
- azure
page_type: sample
urlFragment: azure-search-openai-demo-private-access
---
-->

# Czat RAG: Wdrażanie z dostępem prywatnym

[📺 Oglądaj: (seria RAG Deep Dive) Wdrażanie sieci prywatnej](https://www.youtube.com/watch?v=08wtL1eB15g)

Projekt [azure-search-openai-demo](/) może skonfigurować pełną aplikację czatu RAG na Azure AI Search i OpenAI, dzięki czemu możesz czatować na niestandardowych danych, takich jak wewnętrzne dane przedsiębiorstwa lub zestawy wiedzy specyficzne dla domeny. Po pełne instrukcje dotyczące konfiguracji projektu zapoznaj się z [głównym README](/README.pl.md), a następnie wróć tutaj po szczegółowe instrukcje dotyczące konfigurowania prywatnych punktów końcowych.

Jeśli chcesz wyłączyć dostęp publiczny dla aplikacji, tak aby była dostępna tylko z sieci prywatnej, postępuj zgodnie z tym przewodnikiem.

## Zanim zaczniesz

Wdrażanie z siecią prywatną dodaje dodatkowe koszty do wdrożenia. Zobacz cennik następujących produktów:

* [Azure Container Registry](https://azure.microsoft.com/pricing/details/container-registry/): Warstwa Premium jest używana, gdy dodawana jest sieć wirtualna (wymagana dla prywatnych linków), co generuje dodatkowe koszty.
* [Azure Container Apps](https://azure.microsoft.com/pricing/details/container-apps/): Środowisko profili obciążenia jest używane, gdy dodawana jest sieć wirtualna (wymagana dla prywatnych linków), co generuje dodatkowe koszty. Dodatkowo minimalna liczba replik jest ustawiona na 1, więc będziesz obciążany za co najmniej jedną instancję.
* [VPN Gateway](https://azure.microsoft.com/pricing/details/vpn-gateway/): SKU VpnGw2. Cennik obejmuje podstawowy koszt miesięczny plus koszt godzinowy oparty na liczbie połączeń.
* [Virtual Network](https://azure.microsoft.com/pricing/details/virtual-network/): Warstwa Pay-as-you-go. Koszty oparte na przetworzonych danych.

Cennik następujących funkcji zależy od używanych [opcjonalnych funkcji](./deploy_features.md) *(angielski)*. Większość wdrożeń będzie miała co najmniej 5 prywatnych punktów końcowych (Azure OpenAI, Azure Cognitive Services, Azure AI Search, Azure Blob Storage i Azure App Service lub Azure Container Apps).

* [Azure Private Endpoints](https://azure.microsoft.com/pricing/details/private-link/): Cennik za godzinę za punkt końcowy.
* [Private DNS Zones](https://azure.microsoft.com/pricing/details/dns/): Cennik za miesiąc i strefy.
* [Azure Private DNS Resolver](https://azure.microsoft.com/pricing/details/dns/): Cennik za miesiąc i strefy.

⚠️ Aby uniknąć niepotrzebnych kosztów, pamiętaj o wyłączeniu aplikacji, jeśli nie jest już używana,
usuwając grupę zasobów w portalu lub uruchamiając `azd down`.
Możesz również zdecydować się na usunięcie VPN Gateway, gdy nie jest używana.

## Kroki wdrażania dla dostępu prywatnego

1. Skonfiguruj zmienne środowiskowe azd, aby używać prywatnych punktów końcowych i bramy VPN, z wyłączonym dostępem do sieci publicznej. To pozwoli Ci połączyć się z aplikacją czatu z wewnątrz sieci wirtualnej, ale nie z publicznego Internetu.

    ```shell
    azd env set AZURE_USE_PRIVATE_ENDPOINT true
    azd env set AZURE_USE_VPN_GATEWAY true
    azd env set AZURE_PUBLIC_NETWORK_ACCESS Disabled
    azd up
    ```

2. Aprowizuj wszystkie zasoby Azure:

    ```bash
    azd provision
    ```

3. Po zakończeniu aprowizacji zobaczysz błąd, gdy próbuje uruchomić skrypt pozyskiwania danych, ponieważ nie jesteś jeszcze połączony z VPN. Ta wiadomość powinna zawierać URL do pobrania pliku konfiguracji VPN. Jeśli nie widzisz tego URL, uruchom to polecenie:

    ```bash
    azd env get-value AZURE_VPN_CONFIG_DOWNLOAD_LINK
    ```

    Otwórz ten link w przeglądarce. Wybierz "Download VPN client", aby pobrać plik ZIP zawierający konfigurację VPN.

4. Otwórz `AzureVPN/azurevpnconfig.xml` i zastąp pusty tag `<clientconfig>` następującym:

    ```xml
      <clientconfig>
        <dnsservers>
          <dnsserver>10.0.11.4</dnsserver>
        </dnsservers>
      </clientconfig>
    ```

    > **Uwaga:** Używamy adresu IP `10.0.11.4`, ponieważ jest to pierwszy dostępny adres IP w `dns-resolver-subnet`(10.0.11.0/28) z aprowizowanej sieci wirtualnej, ponieważ Azure rezerwuje pierwsze cztery adresy IP w każdej podsieci. Dodanie tego serwera DNS pozwala klientowi VPN rozwiązywać prywatne nazwy DNS dla usług Azure dostępnych przez prywatne punkty końcowe. Zobacz konfigurację sieci w [network-isolation.bicep](../infra/network-isolation.bicep) po szczegóły.

5. Zainstaluj [Azure VPN Client](https://learn.microsoft.com/azure/vpn-gateway/azure-vpn-client-versions).

6. Otwórz Azure VPN Client i wybierz przycisk "Import". Wybierz plik `azurevpnconfig.xml`, który właśnie pobrałeś i zmodyfikowałeś.

7. Wybierz "Connect" i nowe połączenie VPN. Zostaniesz poproszony o wybranie konta Microsoft i zalogowanie się.

8. Po pomyślnym połączeniu z VPN możesz uruchomić skrypt pozyskiwania danych:

    ```bash
    azd hooks run postprovision
    ```

9. Na koniec możesz wdrożyć aplikację:

    ```bash
    azd deploy
    ```

## Zmienne środowiskowe kontrolujące dostęp prywatny

1. `AZURE_PUBLIC_NETWORK_ACCESS`: Kontroluje wartość dostępu do sieci publicznej w obsługiwanych zasobach Azure. Prawidłowe wartości to 'Enabled' lub 'Disabled'.
    1. Gdy dostęp do sieci publicznej jest 'Enabled', zasoby Azure są otwarte na Internet.
    1. Gdy dostęp do sieci publicznej jest 'Disabled', zasoby Azure są dostępne tylko przez sieć wirtualną.
1. `AZURE_USE_PRIVATE_ENDPOINT`: Kontroluje wdrożenie [prywatnych punktów końcowych](https://learn.microsoft.com/azure/private-link/private-endpoint-overview), które łączą zasoby Azure z siecią wirtualną.
    1. Gdy ustawione na 'true', zapewnia, że prywatne punkty końcowe są wdrażane dla połączenia, nawet gdy `AZURE_PUBLIC_NETWORK_ACCESS` jest 'Disabled'.
    1. Należy pamiętać, że prywatne punkty końcowe nie sprawiają, że aplikacja czatu jest dostępna z Internetu. Połączenia muszą być inicjowane z wewnątrz sieci wirtualnej.
1. `AZURE_USE_VPN_GATEWAY`: Kontroluje wdrożenie bramy VPN dla sieci wirtualnej. Jeśli tego nie użyjesz, a dostęp publiczny jest wyłączony, będziesz potrzebować innego sposobu połączenia z siecią wirtualną.

## Kompatybilność z innymi funkcjami

* **GitHub Actions / Azure DevOps**: Wdrożenie z dostępem prywatnym nie jest kompatybilne z wbudowanymi potokami CI/CD, ponieważ wymaga połączenia VPN do wdrożenia aplikacji. Możesz zmodyfikować potok, aby wykonywał tylko aprowizację i skonfigurować inną strategię wdrażania dla aplikacji.
