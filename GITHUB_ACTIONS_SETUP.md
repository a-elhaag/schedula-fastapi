# GitHub Actions Setup Summary

## ✅ Completed

### 1. GitHub Secrets Created
All required secrets have been added to your GitHub repository using `gh secret set`:

- **AZURE_CREDENTIALS** ✅ - Service principal with Contributor role
  - clientId: b8f675ce-fbcc-4a7e-9561-88af51882a90
  - tenantId: 84c31ca0-ac3b-4eae-ad11-519d80233e6f
  - subscriptionId: d9b2d83f-6e51-4182-9b58-97d075a19770

- **REGISTRY_USERNAME** ✅ - schedularegistry

- **REGISTRY_PASSWORD** ✅ - ACR admin password

### 2. GitHub Actions Workflow
The deployment workflow `.github/workflows/deploy.yml` has been:
- ✅ Created with proper trigger conditions
- ✅ Updated with correct resource group name (schedula)
- ✅ Committed to git
- ✅ Pushed to main branch (commit: d7626c8)

### 3. Workflow Triggers
The workflow automatically runs on:
- ✅ Push to `main` branch with changes to:
  - `app/**`
  - `requirements.txt`
  - `Dockerfile`
  - `tests/**`
  - `.github/workflows/deploy.yml`
- ✅ Manual trigger via `workflow_dispatch`

## Workflow Jobs

### Job 1: Test (ubuntu-latest)
- Sets up Python 3.12
- Installs dependencies
- Runs pytest on `tests/` directory

### Job 2: Build and Deploy (ubuntu-latest, runs after test passes)
- Logs into Azure with service principal
- Logs into Azure Container Registry
- Builds Docker image with metadata
- Pushes to ACR with tags:
  - Branch name
  - Semantic versioning (if tagged)
  - Commit SHA
- Deploys to Container App
- Verifies deployment with health check

## Repository Links
- **GitHub Repo**: https://github.com/a-elhaag/schedula-fastapi
- **Actions Page**: https://github.com/a-elhaag/schedula-fastapi/actions
- **Workflow File**: https://github.com/a-elhaag/schedula-fastapi/blob/main/.github/workflows/deploy.yml

## Next Steps

### Check Workflow Status
1. Go to: https://github.com/a-elhaag/schedula-fastapi/actions
2. Click on latest "Deploy to Azure Container Apps" workflow
3. View logs for each job

### Monitor Production
- **API URL**: https://schedula-api.happysand-30861dbc.uaenorth.azurecontainerapps.io
- **Health Endpoint**: https://schedula-api.happysand-30861dbc.uaenorth.azurecontainerapps.io/health
- **Docs**: https://schedula-api.happysand-30861dbc.uaenorth.azurecontainerapps.io/docs

### Trigger Manual Deployment
Run from command line:
```bash
gh workflow run deploy.yml --ref main
```

Or via GitHub UI:
1. Go to Actions → Deploy to Azure Container Apps
2. Click "Run workflow"

## Environment Variables (Configured in Container App)
- MONGODB_URI
- MONGODB_DB_NAME
- DEBUG
- SOLVER_TIME_LIMIT_SECONDS
- SOLVER_NUM_WORKERS
- SOFT_WEIGHT_BREAK_WINDOW
- SOFT_WEIGHT_CONSECUTIVE_SLOTS
- SOFT_WEIGHT_SESSION_SPREAD
- SOFT_WEIGHT_CAMPUS_CLUSTERING

## Security Notes
⚠️ Service principal credentials are stored as GitHub Secrets (encrypted)
⚠️ ACR password is stored as GitHub Secret (encrypted)
⚠️ Never commit credentials to the repository

All workflow runs are logged and auditable in GitHub Actions UI.
