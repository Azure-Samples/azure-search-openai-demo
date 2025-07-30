# RAG Chat: Application Architecture

This document provides a detailed architectural overview of this application, a Retrieval Augmented Generation (RAG) application that creates a ChatGPT-like experience over your own documents. It combines Azure OpenAI Service for AI capabilities with Azure AI Search for document indexing and retrieval.

For getting started with the application, see the main [README](../README.md).

## Architecture Diagram

The following diagram illustrates the complete architecture including user interaction flow, application components, and Azure services:

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

## Chat Query Flow

The following sequence diagram shows how a user query is processed:

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

## Document Ingestion Flow

The following diagram shows how documents are processed and indexed:

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

## Key Components

### Frontend (React/TypeScript)

- **Chat Interface**: Main conversational UI
- **Settings Panel**: Configuration options for AI behavior
- **Citation Display**: Shows sources and references
- **Authentication**: Optional user login integration

### Backend (Python)

- **API Layer**: RESTful endpoints for chat, search, and configuration. See [HTTP Protocol](http_protocol.md) for detailed API documentation.
- **Approach Patterns**: Different strategies for processing queries
  - `ChatReadRetrieveRead`: Multi-turn conversation with retrieval
  - `RetrieveThenRead`: Single-turn Q&A with retrieval
- **Authentication**: Optional integration with Azure Active Directory

### Azure Services Integration

- **Azure OpenAI**: Powers the conversational AI capabilities
- **Azure AI Search**: Provides semantic and vector search over documents
- **Azure Blob Storage**: Stores original documents and processed content
- **Application Insights**: Provides monitoring and telemetry

## Optional Features

The architecture supports several optional features that can be enabled. For detailed configuration instructions, see the [optional features guide](deploy_features.md):

- **GPT-4 with Vision**: Process image-heavy documents
- **Speech Services**: Voice input/output capabilities
- **Chat History**: Persistent conversation storage in Cosmos DB
- **Authentication**: User login and access control
- **Private Endpoints**: Network isolation for enhanced security

## Deployment Options

The application can be deployed using:

- **Azure Container Apps** (default): Serverless container hosting
- **Azure App Service**: Traditional PaaS hosting option. See the [App Service hosting guide](appservice.md) for detailed instructions.

Both options support the same feature set and can be configured through the Azure Developer CLI (azd).
