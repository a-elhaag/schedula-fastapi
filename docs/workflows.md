# CI/CD Workflows

Current GitHub Actions workflows in `.github/workflows`:

- `ci.yml`
- `deploy.yml`
- `mkdocs-pages.yml`

## `ci.yml` (Continuous Integration)

Triggers:

- push to `main`
- pull requests targeting `main`

Jobs:

- `test`: installs dependencies and runs `pytest`
- `lint`: runs `ruff check .` after tests

Purpose:

- validates backend correctness and code quality for every change

## `deploy.yml` (Azure Container Apps)

Name: `Deploy to Azure Container Apps`

Triggers:

- push to `main` on selected backend paths
- manual dispatch

Flow:

1. run tests
2. build/push container image to ACR
3. update Azure Container App image
4. verify service health endpoint

## `mkdocs-pages.yml` (Docs Deployment)

Name: `Deploy MkDocs to GitHub Pages`

Triggers:

- push to `main` when docs or `mkdocs.yml` changes
- manual dispatch

Flow:

1. checkout and setup Pages context
2. install `mkdocs` + theme
3. build site from `mkdocs.yml`
4. upload `site` artifact
5. deploy artifact to GitHub Pages

## Pages Source Requirement

To ensure MkDocs artifact deployment is used:

- set repository `Settings -> Pages -> Source` to `GitHub Actions`

If source is configured as `Deploy from a branch`, GitHub may run branch-based Pages deployment behavior (which can publish root/docs branch content rather than artifact-based MkDocs output).

## Cleanup Completed

Obsolete docs workflow file was removed and replaced with `mkdocs-pages.yml`.
The Azure deployment workflow was intentionally preserved.
