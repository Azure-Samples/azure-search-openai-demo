# Czat RAG: Architektura aplikacji

Ten dokument zawiera szczegółowy przegląd architektury tej aplikacji, aplikacji Retrieval Augmented Generation (RAG), która tworzy doświadczenie podobne do ChatGPT nad własnymi dokumentami. Łączy Azure OpenAI Service dla możliwości AI z Azure AI Search do indeksowania i wyszukiwania dokumentów.

Aby rozpocząć pracę z aplikacją, zobacz główny [README](../README.pl.md).

## Diagram architektury

Poniższy diagram ilustruje kompletną architekturę, w tym przepływ interakcji użytkownika, komponenty aplikacji i usługi Azure:

```mermaid
graph TB
    subgraph "User Interface"
        User[👤 User]
        Browser[🌐 Web Browser]
    end

    subgraph "Application Layer"
        subgraph "Frontend"
            React[⚛️ React/TypeScript App<br/>Chat Interface<br/>Settings Panel<br/>Citation Display]
        end
        
        subgraph "Backend"
            API[🐍 Python API<br/>Flask/Quart<br/>Chat Endpoints<br/>Document Upload<br/>Authentication]
            
            subgraph "Approaches"
                CRR[ChatReadRetrieveRead<br/>Approach]
                RTR[RetrieveThenRead<br/>Approach]
            end
        end
    end

    subgraph "Azure Services"
        subgraph "AI Services"
            OpenAI[🤖 Azure OpenAI<br/>GPT-4 Mini<br/>Text Embeddings<br/>GPT-4 Vision]
            Search[🔍 Azure AI Search<br/>Vector Search<br/>Semantic Ranking<br/>Full-text Search]
            DocIntel[📄 Azure Document<br/>Intelligence<br/>Text Extraction<br/>Layout Analysis]
            Vision2[👁️ Azure AI Vision<br/>optional]
            Speech[🎤 Azure Speech<br/>Services optional]
        end
        
        subgraph "Storage & Data"
            Blob[💾 Azure Blob Storage<br/>Document Storage<br/>User Uploads]
            Cosmos[🗃️ Azure Cosmos DB<br/>Chat History<br/>optional]
        end
        
        subgraph "Platform Services"
            ContainerApps[📦 Azure Container Apps<br/>or App Service<br/>Application Hosting]
            AppInsights[📊 Application Insights<br/>Monitoring<br/>Telemetry]
            KeyVault[🔐 Azure Key Vault<br/>Secrets Management]
        end
    end

    subgraph "Data Processing"
        PrepDocs[⚙️ Document Preparation<br/>Pipeline<br/>Text Extraction<br/>Chunking<br/>Embedding Generation<br/>Indexing]
    end

    %% User Interaction Flow
    User -.-> Browser
    Browser <--> React
    React <--> API

    %% Backend Processing
    API --> CRR
    API --> RTR
    
    %% Azure Service Connections
    API <--> OpenAI
    API <--> Search
    API <--> Blob
    API <--> Cosmos
    API <--> Speech
    
    %% Document Processing Flow
    Blob --> PrepDocs
    PrepDocs --> DocIntel
    PrepDocs --> OpenAI
    PrepDocs --> Search
    
    %% Platform Integration
    ContainerApps --> API
    API --> AppInsights
    API --> KeyVault
    
    %% Styling
    classDef userLayer fill:#e1f5fe
    classDef appLayer fill:#f3e5f5
    classDef azureAI fill:#e8f5e8
    classDef azureStorage fill:#fff3e0
    classDef azurePlatform fill:#fce4ec
    classDef processing fill:#f1f8e9
    
    class User,Browser userLayer
    class React,API,CRR,RTR appLayer
    class OpenAI,Search,DocIntel,Vision2,Speech azureAI
    class Blob,Cosmos azureStorage
    class ContainerApps,AppInsights,KeyVault azurePlatform
    class PrepDocs processing
```

## Przepływ zapytania czatu

Poniższy diagram sekwencji pokazuje, jak przetwarzane jest zapytanie użytkownika:

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend API
    participant S as Azure AI Search
    participant O as Azure OpenAI
    participant Bl as Blob Storage

    U->>F: Enter question
    F->>B: POST /chat with query
    B->>S: Search for relevant documents
    S-->>B: Return search results with citations
    B->>O: Send query + context to GPT model
    O-->>B: Return AI response
    B->>Bl: Log interaction (optional)
    B-->>F: Return response with citations
    F-->>U: Display answer with sources
```

## Przepływ pozyskiwania dokumentów

Poniższy diagram pokazuje, jak dokumenty są przetwarzane i indeksowane:

```mermaid
sequenceDiagram
    participant D as Documents
    participant Bl as Blob Storage
    participant P as PrepDocs Script
    participant DI as Document Intelligence
    participant O as Azure OpenAI
    participant S as Azure AI Search

    D->>Bl: Upload documents
    P->>Bl: Read documents
    P->>DI: Extract text and layout
    DI-->>P: Return extracted content
    P->>P: Split into chunks
    P->>O: Generate embeddings
    O-->>P: Return vector embeddings
    P->>S: Index documents with embeddings
    S-->>P: Confirm indexing complete
```

## Kluczowe komponenty

### Frontend (React/TypeScript)

- **Interfejs czatu**: Główny interfejs konwersacyjny
- **Panel ustawień**: Opcje konfiguracji dla zachowania AI
- **Wyświetlanie cytatów**: Pokazuje źródła i referencje
- **Uwierzytelnianie**: Opcjonalna integracja logowania użytkownika

### Backend (Python)

- **Warstwa API**: Endpointy RESTful dla czatu, wyszukiwania i konfiguracji. Zobacz [Protokół HTTP](http_protocol.md) *(angielski)* po szczegółową dokumentację API.
- **Wzorce podejść**: Różne strategie przetwarzania zapytań
  - `ChatReadRetrieveRead`: Konwersacja wieloetapowa z wyszukiwaniem
  - `RetrieveThenRead`: Jednoetapowe Q&A z wyszukiwaniem
- **Uwierzytelnianie**: Opcjonalna integracja z Azure Active Directory

### Integracja usług Azure

- **Azure OpenAI**: Zasila możliwości konwersacyjne AI
- **Azure AI Search**: Zapewnia wyszukiwanie semantyczne i wektorowe nad dokumentami
- **Azure Blob Storage**: Przechowuje oryginalne dokumenty i przetworzoną zawartość
- **Application Insights**: Zapewnia monitorowanie i telemetrię

## Opcjonalne funkcje

Architektura obsługuje kilka opcjonalnych funkcji, które można włączyć. Po szczegółowe instrukcje konfiguracji zobacz [przewodnik opcjonalnych funkcji](deploy_features.md) *(angielski)*:

- **GPT-4 z Vision**: Przetwarzaj dokumenty zawierające dużo obrazów
- **Usługi mowy**: Możliwości wejścia/wyjścia głosowego
- **Historia czatu**: Trwałe przechowywanie rozmów w Cosmos DB
- **Uwierzytelnianie**: Logowanie użytkownika i kontrola dostępu
- **Prywatne punkty końcowe**: Izolacja sieciowa dla zwiększonego bezpieczeństwa

## Opcje wdrożenia

Aplikację można wdrożyć przy użyciu:

- **Azure Container Apps** (domyślnie): Hosting kontenerów bez serwera
- **Azure App Service**: Tradycyjna opcja hostingu PaaS. Zobacz [przewodnik hostingu App Service](appservice.md) *(angielski)* po szczegółowe instrukcje.

Obie opcje obsługują ten sam zestaw funkcji i można je skonfigurować za pomocą Azure Developer CLI (azd).
