# Microsoft 365 RAG Agent

This directory contains the Microsoft 365 Agents SDK integration for the RAG chat application. The agent provides AI-powered document search and chat capabilities across Microsoft 365 channels including Teams, Copilot, and web chat.

## Architecture

```
agents/
├── main.py                 # Main entry point
├── agent_app.py           # Core agent application
├── config/
│   └── agent_config.py    # Configuration management
├── services/
│   ├── rag_service.py     # RAG service integration
│   └── auth_service.py    # Authentication service
├── handlers/
│   ├── message_handler.py # General message handler
│   └── teams_handler.py   # Teams-specific handler
├── adapters/
│   └── response_adapter.py # Channel-specific response formatting
└── requirements.txt       # Python dependencies
```

## Features

- **Multi-Channel Support**: Works with Teams, Copilot, and web chat
- **RAG Integration**: Leverages existing RAG capabilities
- **Authentication**: Microsoft 365 authentication and authorization
- **Rich Responses**: Adaptive cards, citations, and interactive elements
- **Conversation State**: Maintains context across conversations
- **Error Handling**: Robust error handling and logging

## Setup

### 1. Install Dependencies

```bash
cd agents
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration values
```

### 3. Required Configuration

- **Bot Framework**: App ID and password from Azure Bot Service
- **Microsoft 365**: Tenant ID, client ID, and client secret
- **Azure OpenAI**: Endpoint, API key, and deployment name
- **Azure AI Search**: Endpoint, key, and index name

### 4. Run the Agent

```bash
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MICROSOFT_APP_ID` | Bot Framework app ID | Yes |
| `MICROSOFT_APP_PASSWORD` | Bot Framework app password | Yes |
| `AZURE_TENANT_ID` | Microsoft 365 tenant ID | Yes |
| `AZURE_CLIENT_ID` | Microsoft 365 client ID | Yes |
| `AZURE_CLIENT_SECRET` | Microsoft 365 client secret | Yes |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Yes |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT` | ChatGPT deployment name | Yes |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | Yes |
| `AZURE_SEARCH_KEY` | Azure AI Search key | Yes |
| `AZURE_SEARCH_INDEX` | Search index name | Yes |

### Agent Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_NAME` | Display name for the agent | "RAG Assistant" |
| `AGENT_DESCRIPTION` | Agent description | "AI-powered document search and chat assistant" |
| `MAX_CONVERSATION_TURNS` | Maximum conversation turns | 20 |
| `ENABLE_TYPING_INDICATOR` | Enable typing indicators | true |
| `ENABLE_TEAMS` | Enable Teams channel | true |
| `ENABLE_COPILOT` | Enable Copilot channel | true |
| `ENABLE_WEB_CHAT` | Enable web chat channel | true |

## API Endpoints

### Health Check
- **GET** `/` - Basic health check
- **GET** `/api/health` - Detailed health check

### Bot Framework
- **POST** `/api/messages` - Main Bot Framework endpoint

### Configuration
- **GET** `/api/config` - Get agent configuration (non-sensitive)

## Development

### Running Locally

1. Set up your environment variables
2. Run the agent: `python main.py`
3. Use Bot Framework Emulator to test locally

### Testing with Teams

1. Deploy to Azure
2. Register with Azure Bot Service
3. Configure Teams channel
4. Test in Teams

## Integration with Main App

The agent integrates with the existing RAG application by:

1. **Shared Services**: Uses the same Azure OpenAI and Search services
2. **Authentication**: Leverages existing authentication system
3. **RAG Logic**: Integrates with existing RAG approaches
4. **Configuration**: Shares configuration with main application

## Next Steps

1. **Phase 2**: Integrate with existing RAG approaches
2. **Phase 3**: Add Teams-specific features
3. **Phase 4**: Implement Copilot integration
4. **Phase 5**: Add advanced features and monitoring

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Check Microsoft 365 app registration
2. **Bot Framework Errors**: Verify app ID and password
3. **Azure Service Errors**: Check service endpoints and keys
4. **Channel Errors**: Verify channel configuration

### Logs

The agent logs to stdout with structured logging. Check logs for:
- Authentication issues
- Service connection problems
- Message processing errors
- Channel-specific issues

## Support

For issues and questions:
1. Check the logs for error details
2. Verify configuration values
3. Test with Bot Framework Emulator
4. Check Azure service status