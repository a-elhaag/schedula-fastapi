# Schedula Solver API — Deployment Guide

**For:** DevOps/Backend Team
**Purpose:** Deploy API to production (Azure Container Apps)
**Last Updated:** 2026-03-23

---

## Deployment Architecture

```
GitHub (schedula-fastapi)
    ↓
CI/CD Pipeline (GitHub Actions)
    ↓
Azure Container Registry
    ↓
Azure Container Apps (Production)
    ↓
MongoDB Atlas (Cloud Database)
```

---

## Prerequisites

- Azure subscription with Container Apps enabled
- GitHub Actions configured for CI/CD
- MongoDB Atlas cluster (already configured)
- Docker installed locally (for testing)

---

## 1. Local Docker Testing

### Build Docker Image

```bash
# From project root
docker build -t schedula-api:latest .

# Verify build
docker images | grep schedula-api
```

### Create Dockerfile (if not exists)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Run Docker Container Locally

```bash
# Create .env file
cat > .env << EOF
MONGODB_URI=mongodb+srv://SchedulaUser1:X2oqdA2P0WLScRI1@cluster1.97zvro6.mongodb.net/?appName=cluster1
MONGODB_DB_NAME=schedula
DEBUG=False
SOLVER_TIME_LIMIT_SECONDS=60
SOLVER_NUM_WORKERS=8
SOFT_WEIGHT_BREAK_WINDOW=100
SOFT_WEIGHT_CONSECUTIVE_SLOTS=80
SOFT_WEIGHT_SESSION_SPREAD=60
SOFT_WEIGHT_CAMPUS_CLUSTERING=40
EOF

# Run container
docker run -d \
  --name schedula-api \
  --env-file .env \
  -p 8000:8000 \
  schedula-api:latest

# Test health
curl http://localhost:8000/health

# View logs
docker logs -f schedula-api

# Stop container
docker stop schedula-api
docker rm schedula-api
```

---

## 2. Azure Container Registry Setup

### Create Registry (one-time)

```bash
# Set variables
RESOURCE_GROUP="schedula-rg"
REGISTRY_NAME="schedularegistry"
LOCATION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME \
  --sku Basic

# Get login credentials
az acr login --name $REGISTRY_NAME
```

### Push Docker Image to Registry

```bash
# Set registry URL
REGISTRY_URL="schedularegistry.azurecr.io"

# Tag image
docker tag schedula-api:latest $REGISTRY_URL/schedula-api:latest
docker tag schedula-api:latest $REGISTRY_URL/schedula-api:v0.1.0

# Push to registry
docker push $REGISTRY_URL/schedula-api:latest
docker push $REGISTRY_URL/schedula-api:v0.1.0

# Verify
az acr repository list --name $REGISTRY_NAME
```

---

## 3. Azure Container Apps Deployment

### Create Container App (one-time)

```bash
# Set variables
RESOURCE_GROUP="schedula-rg"
CONTAINER_APP_NAME="schedula-api"
CONTAINER_APP_ENV="schedula-env"
REGISTRY_NAME="schedularegistry"
LOCATION="eastus"

# Create container app environment
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Create container app
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image schedularegistry.azurecr.io/schedula-api:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server schedularegistry.azurecr.io \
  --registry-username <registry-username> \
  --registry-password <registry-password> \
  --min-replicas 1 \
  --max-replicas 3

# Get URL
az containerapp show \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_APP_NAME \
  --query "properties.configuration.ingress.fqdn" \
  -o tsv
```

### Configure Environment Variables

```bash
# Set environment variables
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    MONGODB_URI="mongodb+srv://SchedulaUser1:X2oqdA2P0WLScRI1@cluster1.97zvro6.mongodb.net/?appName=cluster1" \
    MONGODB_DB_NAME="schedula" \
    DEBUG="False" \
    SOLVER_TIME_LIMIT_SECONDS="60" \
    SOLVER_NUM_WORKERS="8" \
    SOFT_WEIGHT_BREAK_WINDOW="100" \
    SOFT_WEIGHT_CONSECUTIVE_SLOTS="80" \
    SOFT_WEIGHT_SESSION_SPREAD="60" \
    SOFT_WEIGHT_CAMPUS_CLUSTERING="40"
```

### Update Deployment (after code changes)

```bash
# Push new image
docker build -t schedularegistry.azurecr.io/schedula-api:v0.1.1 .
docker push schedularegistry.azurecr.io/schedula-api:v0.1.1

# Update container app
az containerapp update \
  --name schedula-api \
  --resource-group schedula-rg \
  --image schedularegistry.azurecr.io/schedula-api:v0.1.1
```

---

## 4. GitHub Actions CI/CD Pipeline

### Create `.github/workflows/deploy.yml`

```yaml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [main]
    paths:
      - 'app/**'
      - 'requirements.txt'
      - 'Dockerfile'
      - '.github/workflows/deploy.yml'

env:
  REGISTRY: schedularegistry.azurecr.io
  IMAGE_NAME: schedula-api
  RESOURCE_GROUP: schedula-rg
  CONTAINER_APP: schedula-api

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Log in to Azure Container Registry
        uses: azure/docker-login@v1
        with:
          login-server: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

      - name: Deploy to Azure Container Apps
        run: |
          az containerapp update \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --set-env-vars DEPLOYMENT_SHA="${{ github.sha }}"

      - name: Verify deployment
        run: |
          az containerapp show \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query "properties.runningStatus" -o tsv
```

### GitHub Secrets Configuration

```bash
# In GitHub: Settings → Secrets and variables → Actions

# Azure credentials (from `az account show`)
AZURE_CREDENTIALS=
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "..."
}

# Registry credentials
REGISTRY_USERNAME=<acr-username>
REGISTRY_PASSWORD=<acr-password>
```

---

## 5. Production Checklist

### Pre-Deployment
- [ ] All tests passing: `pytest tests/`
- [ ] Code reviewed and merged to `main`
- [ ] `.env` configured for production (MongoDB Atlas URI)
- [ ] Docker image builds successfully
- [ ] Docker container runs locally without errors

### Deployment
- [ ] Push to GitHub `main` branch
- [ ] GitHub Actions pipeline starts automatically
- [ ] Docker image built and pushed to registry
- [ ] Container App updated with new image

### Post-Deployment
- [ ] Check Container App status: `az containerapp show --name schedula-api ...`
- [ ] Verify health endpoint: `curl https://<app-url>/health`
- [ ] Test schedule generation: `curl -X POST https://<app-url>/schedule/generate ...`
- [ ] Monitor logs: `az containerapp logs show --name schedula-api ...`

---

## 6. Scaling Configuration

### Auto-Scaling Rules

```bash
# Update min/max replicas (for load handling)
az containerapp update \
  --name schedula-api \
  --resource-group schedula-rg \
  --min-replicas 2 \
  --max-replicas 5

# CPU/Memory settings
az containerapp create-config \
  --cpu 0.5 \
  --memory 1.0Gi
```

### Performance Tuning

| Setting | Value | Notes |
|---------|-------|-------|
| **Min Replicas** | 2 | Always have 2 instances running |
| **Max Replicas** | 5 | Scale to 5 during high load |
| **CPU** | 0.5 | Half CPU core per instance |
| **Memory** | 1.0 Gi | 1 GB RAM per instance |
| **Timeout** | 65s | HTTP request timeout |

---

## 7. Monitoring & Logging

### Azure Monitor Setup

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
  --resource-group schedula-rg \
  --workspace-name schedula-logs

# Connect to Container App
az containerapp env update \
  --name schedula-env \
  --resource-group schedula-rg \
  --logs-workspace-id <workspace-id> \
  --logs-workspace-key <workspace-key>
```

### View Logs

```bash
# Recent logs
az containerapp logs show \
  --name schedula-api \
  --resource-group schedula-rg \
  --follow

# Query logs
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query 'ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1h) | summarize count() by Level'
```

### Alerts

```bash
# Create alert for high CPU
az monitor metrics alert create \
  --name schedula-api-cpu-alert \
  --resource-group schedula-rg \
  --scopes /subscriptions/<sub-id>/resourceGroups/schedula-rg/providers/Microsoft.App/containerApps/schedula-api \
  --condition "avg Percentage CPU > 80" \
  --description "Alert when CPU > 80%"

# Create alert for errors
az monitor metrics alert create \
  --name schedula-api-errors \
  --resource-group schedula-rg \
  --scopes /subscriptions/<sub-id>/resourceGroups/schedula-rg/providers/Microsoft.App/containerApps/schedula-api \
  --condition "total Exceptions > 10" \
  --description "Alert when errors spike"
```

---

## 8. Rollback Procedure

### If Deployment Fails

```bash
# View recent image versions
az acr repository show-tags \
  --name schedularegistry \
  --repository schedula-api

# Rollback to previous version
az containerapp update \
  --name schedula-api \
  --resource-group schedula-rg \
  --image schedularegistry.azurecr.io/schedula-api:v0.1.0

# Verify
az containerapp show \
  --name schedula-api \
  --resource-group schedula-rg \
  --query "properties.template.containers[0].image" -o tsv
```

---

## 9. Database Backup & Recovery

### MongoDB Atlas Backups (Automated)

MongoDB Atlas automatically backs up your cluster:
- **Continuous backups:** Every 30 minutes
- **Retention:** 35 days
- **Location:** AWS/Azure region matching your cluster

### Manual Backup

```bash
# Export MongoDB data
mongodump --uri "mongodb+srv://SchedulaUser1:X2oqdA2P0WLScRI1@cluster1.97zvro6.mongodb.net/schedula"

# Or use MongoDB Atlas UI:
# 1. Go to Data → Backup
# 2. Click "Snapshot"
# 3. Wait for snapshot to complete
```

### Recovery

```bash
# If needed, restore from MongoDB Atlas UI:
# 1. Go to Data → Backup
# 2. Select snapshot
# 3. Click "Restore"
```

---

## 10. SSL/TLS Certificate

### HTTPS Configuration

Azure Container Apps automatically provides HTTPS with managed certificates. Your API is accessible at:

```
https://schedula-api.<unique-id>.eastus.azurecontainerapps.io
```

### Custom Domain (Optional)

```bash
# Add custom domain
az containerapp hostname add \
  --name schedula-api \
  --resource-group schedula-rg \
  --hostname solver.schedula.dev \
  --certificate-id <cert-id>
```

---

## 11. Environment-Specific Configuration

### Development `.env`
```bash
DEBUG=True
SOLVER_TIME_LIMIT_SECONDS=60
SOLVER_NUM_WORKERS=1
MONGODB_URI=mongodb://user:password@localhost:27017
```

### Staging `.env`
```bash
DEBUG=False
SOLVER_TIME_LIMIT_SECONDS=60
SOLVER_NUM_WORKERS=4
MONGODB_URI=mongodb+srv://user:pass@staging-cluster.mongodb.net
```

### Production `.env`
```bash
DEBUG=False
SOLVER_TIME_LIMIT_SECONDS=60
SOLVER_NUM_WORKERS=8
MONGODB_URI=mongodb+srv://SchedulaUser1:X2oqdA2P0WLScRI1@cluster1.97zvro6.mongodb.net/?appName=cluster1
CORS_ORIGINS=https://schedula.dev,https://app.schedula.dev
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
az containerapp logs show --name schedula-api --resource-group schedula-rg

# Common issues:
# - Environment variables missing (check MongoDB URI)
# - Port binding failed (ensure port 8000 is used)
# - Import errors (check Python dependencies in requirements.txt)
```

### High Latency/Timeouts

```bash
# Check if replicas are at max
az containerapp show --name schedula-api --resource-group schedula-rg \
  --query "properties.template.scale"

# Increase max replicas
az containerapp update --name schedula-api --resource-group schedula-rg \
  --max-replicas 10
```

### MongoDB Connection Issues

```bash
# Verify connection string in Container App
az containerapp show --name schedula-api --resource-group schedula-rg \
  --query "properties.configuration.env[?name=='MONGODB_URI']"

# Test connection locally
python -c "
import asyncio
from pymongo.asynchronous.mongo_client import AsyncMongoClient
uri = 'your-uri-here'
client = AsyncMongoClient(uri)
asyncio.run(client.admin.command('ping'))
print('Connected!')
"
```

---

## Cost Optimization

| Item | Estimate | Notes |
|------|----------|-------|
| **Container Apps** | $40–100/month | 2 instances, 0.5 CPU, 1 GB RAM |
| **MongoDB Atlas** | $60–200/month | Cluster size depends on data |
| **Azure Monitor** | $0–50/month | Log retention |
| **Total** | ~$100–350/month | Varies by usage |

### Cost Reduction Tips
1. Lower min replicas to 1 (trade availability for cost)
2. Use smaller container resources if load is low
3. Adjust MongoDB cluster size based on actual usage
4. Use reserved capacity in Azure (for 1+ year commitment)

---

## Support

**Issues?**
- Check Azure Container Apps logs: `az containerapp logs show ...`
- Verify MongoDB Atlas connection
- Review application logs in Azure Monitor
- Check GitHub Actions workflow history

---

**Deployment Version:** 0.1.0
**Last Updated:** 2026-03-23
**Status:** ✅ Ready for Production Deployment
