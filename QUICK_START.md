# 🚀 Quick Reference - Foundry + Azure OpenAI Setup

## One-Line Deploy
```bash
./scripts/setup-foundry-azure.sh prod
```

## Essential Commands

### Verify Setup
```bash
azd show                          # Check deployment status
azd monitor --follow             # View logs in real-time
```

### Load Data
```bash
./scripts/prepdocs.sh            # Ingest sample documents
```

### Start Development
```bash
./app/start.sh                   # Start frontend + backend
# OR manually:
cd app/frontend && npm run dev   # Terminal 1
cd app/backend && python -m quart run --reload -p 50505  # Terminal 2
```

### Access Application
```
http://localhost:5000            # Development
https://<container-app-url>      # Production
```

## Environment Setup
```bash
# Copy template
cp .env.template .env

# Edit with your Azure details
nano .env
# Fill in:
# - AZURE_SUBSCRIPTION_ID
# - AZURE_TENANT_ID
# - AZURE_RESOURCE_GROUP
# - AZURE_LOCATION
```

## Model Information

### Chat Model
- **Name**: gpt-4o (latest multimodal)
- **Capabilities**: Reasoning, vision, text, code
- **Use for**: Main chat interface, complex queries
- **Fallback**: gpt-4-mini (faster, cheaper)

### Embedding Model
- **Name**: text-embedding-3-large
- **Dimensions**: 1536 (superior quality)
- **Use for**: Document search, semantic similarity
- **Fallback**: text-embedding-3-small (faster)

## Services Deployed

| Service | Status | Endpoint |
|---------|--------|----------|
| **Chat API** | Running | `/api/chat` |
| **Search** | Ready | Azure Search |
| **Embeddings** | Ready | Azure OpenAI |
| **Storage** | Ready | Blob Storage |
| **Monitoring** | Active | Application Insights |
| **Foundry Agents** | Available | Via CLI/API |

## Key Features
- ✅ Advanced multimodal reasoning (gpt-4o)
- ✅ Hybrid vector + semantic search
- ✅ Real-time streaming responses
- ✅ Query rewriting for better results
- ✅ Complete audit trail & monitoring
- ✅ Enterprise security

## File Locations
| File | Purpose |
|------|---------|
| `FOUNDRY_AZURE_SETUP.md` | Complete setup guide |
| `FOUNDRY_VERIFICATION.md` | Verification & troubleshooting |
| `DEPLOYMENT_SUMMARY.md` | Overview & deployment info |
| `.env.template` | Environment variables template |
| `scripts/setup-foundry-azure.sh` | Deploy everything |
| `app/backend/foundry_integration.py` | Foundry integration code |

## Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Model not found | Check deployment names in Portal |
| Vector search fails | Verify embedding dimensions (1536) |
| Auth error | Run `az login` again |
| Slow responses | Check OpenAI quota |
| High costs | Use gpt-4-mini, reduce search results |

## Support
- 📖 Full guide: `FOUNDRY_AZURE_SETUP.md`
- ✓ Verify setup: `FOUNDRY_VERIFICATION.md`
- 🔧 Troubleshoot: Same file
- 📊 Status: `azd show`

## Next: Deploy Now
```bash
./scripts/setup-foundry-azure.sh prod
```

---
**Ready to build intelligent RAG applications with Azure OpenAI + Foundry!** 🎉
