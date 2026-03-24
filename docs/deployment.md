# Deployment

This project has two deployment tracks:

- backend API deployment to Azure Container Apps
- documentation deployment to GitHub Pages via MkDocs workflow

## Backend: Azure Container Apps

Primary workflow file:

- `.github/workflows/deploy.yml`

This workflow:

1. runs tests
2. builds and pushes Docker image to ACR
3. updates the Azure Container App image
4. probes `/health` endpoint after rollout

Required repository secrets:

- `AZURE_CREDENTIALS`
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`

Required env values in workflow:

- `REGISTRY`
- `IMAGE_NAME`
- `RESOURCE_GROUP`
- `CONTAINER_APP`

## Docs: GitHub Pages + MkDocs

Primary workflow file:

- `.github/workflows/mkdocs-pages.yml`

This workflow:

1. installs MkDocs dependencies
2. builds docs from `mkdocs.yml`
3. uploads `site/` artifact
4. deploys artifact using `actions/deploy-pages`

## GitHub Pages Configuration

In repository settings, set:

- Settings -> Pages -> Source -> **GitHub Actions**

If source is set to `Deploy from a branch`, GitHub can run branch-based Pages behavior that may publish root content (for example `README.md`) instead of MkDocs artifact output.

## Manual Deployment Commands (Local)

Build and run container locally:

```bash
docker build -t schedula-fastapi .
docker run --rm -p 8000:8000 \
	-e MONGODB_URI="mongodb+srv://..." \
	-e MONGODB_DB_NAME="schedula" \
	schedula-fastapi
```

## Operational Checks

After deployment, validate:

- `GET /health` returns 200
- `GET /health/ready` returns 200 and `database=connected`
- `POST /schedule/generate` succeeds with real institution data
