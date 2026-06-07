# Azure Deployment Quick Start

Complete deployment setup for Azure Search + OpenAI with production-grade rate limiting.

## 🚀 Quick Links

| Item | Link |
|------|------|
| **Main Branch** | [devcloner/azure-search-openai-demo](https://github.com/devcloner/azure-search-openai-demo) |
| **Deployment Branch** | [deployment-setup](https://github.com/devcloner/azure-search-openai-demo/tree/deployment-setup) |
| **GitHub Actions** | [Workflows](https://github.com/devcloner/azure-search-openai-demo/actions) |
| **Azure Portal** | [portal.azure.com](https://portal.azure.com) |

## ✅ Deployment Status

- [x] Infrastructure as Code (Bicep)
- [x] GitHub Actions CI/CD Workflows
- [x] Docker Multi-Stage Build
- [x] Rate Limiting Engine
- [x] Circuit Breaker Pattern
- [x] Auto-Scaling Configuration
- [x] Application Insights Integration
- [x] Monitoring & Alerting
- [x] Documentation

## 📋 What's Included

### Workflows
```
.github/workflows/
├── deploy-azure-rate-limited.yml  (Smart deployment with monitoring)
├── deploy-azure.yml               (Standard deployment)
└── test.yml                       (Automated testing)
```

### Infrastructure
```
infra/
└── main.bicep                     (Rate-limit aware resources)
```

### Backend Services
```
app/backend/
├── rate_limiter.py               (Token bucket + circuit breaker)
└── azure_clients.py              (Rate-limited Azure clients)
```

### Configuration
```
├── docker-compose.yml            (Local development)
├── Dockerfile.prod               (Production build)
├── .env.example                  (Configuration template)
└── scripts/setup-secrets.sh      (Automated setup)
```

### Documentation
```
├── DEPLOYMENT_GUIDE.md           (How to deploy)
├── RATE_LIMITING.md              (Rate limit details)
├── MONITORING_DASHBOARDS.md      (Monitoring setup)
├── POST_DEPLOYMENT_CHECKLIST.md  (Verification steps)
└── README_DEPLOYMENT.md          (This file)
```

## 🎯 Rate Limits Configured

| Service | Limit | Protection |
|---------|-------|-----------|
| **Azure Search** | 5 QPS | Token bucket throttling |
| **Azure OpenAI** | 90 RPM | Token bucket + exponential backoff |
| **Storage** | 1000 IOPS | Rate limiter + circuit breaker |
| **Concurrent Requests** | 5 search / 2 OpenAI | Request queueing |

## 🔑 3-Step Setup

### Step 1: Configure Secrets (5 minutes)
```bash
# Run automated setup script
bash scripts/setup-secrets.sh

# Or manually add to GitHub:
# Settings → Secrets and variables → Actions
```

**Required Secrets:**
- `AZURE_CREDENTIALS` - Service Principal JSON
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_SEARCH_SERVICE` & `AZURE_SEARCH_KEY`
- `AZURE_OPENAI_ENDPOINT` & `AZURE_OPENAI_KEY`

### Step 2: Create Pull Request (1 minute)
1. Navigate to [Pull Requests](https://github.com/devcloner/azure-search-openai-demo/pulls)
2. Click "New Pull Request"
3. Compare: `deployment-setup` → `main`
4. Review changes
5. Click "Create Pull Request"

### Step 3: Merge & Deploy (45 minutes)
1. Click "Merge Pull Request"
2. Watch GitHub Actions in [Workflows tab](https://github.com/devcloner/azure-search-openai-demo/actions)
3. Deployment auto-triggers
4. Monitor deployment progress

**Total time: ~50 minutes**

## 📊 Deployment Flow

```
1. Push to main
   ↓
2. GitHub Actions Triggered
   ├─ Tests: Python, TypeScript, Security (30 min)
   ├─ Docker: Build & Push (30 min)
   └─ Deploy: Infrastructure + App (45 min)
   ↓
3. Post-Deployment
   ├─ Health Checks (5 min)
   ├─ Rate Limit Monitoring (5 min)
   └─ Alert Configuration (automatic)
   ↓
4. Live ✅
```

## 🔒 Security Features

✅ Managed Identity for Azure services
✅ Secrets stored only in GitHub (never in code)
✅ Non-root Docker user
✅ HTTPS enforced
✅ TLS 1.2 minimum
✅ Audit logging to Application Insights
✅ Service Principal with limited scope

## 📈 Cost Estimate

| Component | Monthly |
|-----------|---------|
| App Service (S1) | $74.88 |
| Azure Search (Standard) | ~$250 |
| Azure OpenAI | ~$100-500 |
| Storage | ~$50 |
| **Total** | **~$475-800** |

*Rate limiting helps keep costs predictable*

## 🛠️ Local Development

### Quick Start
```bash
# Copy env template
cp .env.example .env

# Start services
docker-compose up --build

# Access:
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
```

### Manual Setup
```bash
# Backend
cd app/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend (separate terminal)
cd app/frontend
npm install
npm run dev
```

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[RATE_LIMITING.md](RATE_LIMITING.md)** - Rate limit configuration details
- **[MONITORING_DASHBOARDS.md](MONITORING_DASHBOARDS.md)** - Setting up dashboards
- **[POST_DEPLOYMENT_CHECKLIST.md](POST_DEPLOYMENT_CHECKLIST.md)** - Post-deployment steps

## 🆘 Troubleshooting

### Deployment Failed?
```bash
# Check logs
az deployment group show \
  --resource-group YOUR_RG \
  --name main \
  --query "properties.error"

# Or check GitHub Actions for details
```

### Application Not Starting?
```bash
# View container logs
az container logs \
  --resource-group YOUR_RG \
  --name azure-search-backend
```

### Rate Limiting Triggered?
1. Check `AZURE_SEARCH_QUERY_DELAY_MS` in env
2. Review `MAX_CONCURRENT_SEARCH_REQUESTS`
3. See [RATE_LIMITING.md](RATE_LIMITING.md) for details

## 🎉 Success Criteria

Your deployment is successful when:

✅ **Immediate (30 min)**
- Application deployed without errors
- API responding to requests
- No HTTP errors in logs

✅ **Stable (1 week)**
- No rate limit errors (429)
- No service unavailable errors (503)
- Consistent response times

✅ **Optimal (ongoing)**
- Auto-scaling working smoothly
- Costs within budget
- Team comfortable with operations

## 📞 Support

- **GitHub Issues**: [Report bugs](https://github.com/devcloner/azure-search-openai-demo/issues)
- **Azure Support**: [Azure Portal Support](https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade)
- **Documentation**: See docs folder

## 🔄 Continuous Improvement

### Weekly
- Review error logs
- Check cost trends
- Verify auto-scaling

### Monthly
- Update dependencies
- Review security advisories
- Capacity planning

### Quarterly
- Load testing
- Disaster recovery drill
- Architecture review

---

## Quick Commands Reference

```bash
# View deployment status
az deployment group show -g YOUR_RG --name main

# Check running containers
az container list -g YOUR_RG

# View application logs
az container logs -g YOUR_RG -n azure-search-backend

# Scale up (if needed)
az appservice plan update -g YOUR_RG --name asp-azure-search-prod --sku S1 -n 2

# Monitor costs
az costmanagement query --type Usage --timeframe MonthToDate

# Stop application (dev/testing)
az container stop -g YOUR_RG -n azure-search-backend

# Delete all resources (cleanup)
az group delete -n YOUR_RG
```

---

**Ready to deploy? Start with [Step 1: Configure Secrets](#-3-step-setup)**

🚀 **Your production-ready Azure Search + OpenAI deployment awaits!**
