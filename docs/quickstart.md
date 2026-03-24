# Quickstart

## Prerequisites

- Python 3.11+
- MongoDB Atlas (or compatible MongoDB)
- Optional: Docker and Docker Compose

## 1. Create Environment and Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Configure Environment Variables

Create a `.env` file in the repository root.

Minimal required values:

```dotenv
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/<db>?retryWrites=true&w=majority
MONGODB_DB_NAME=schedula
DEBUG=true
```

Optional tuning values are documented in `Configuration`.

## 3. Run the API

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Service URLs:

- `http://localhost:8000/`
- `http://localhost:8000/health`
- `http://localhost:8000/health/ready`
- `http://localhost:8000/docs`

## 4. Run MkDocs Locally

```bash
source .venv/bin/activate
mkdocs serve
```

Docs URL:

- `http://127.0.0.1:8000` (or next available port shown by MkDocs)

## 5. Run Tests

```bash
source .venv/bin/activate
pytest -q
```

## 6. Optional Docker Run

```bash
docker build -t schedula-fastapi .
docker run --rm -p 8000:8000 \
  -e MONGODB_URI="mongodb+srv://..." \
  -e MONGODB_DB_NAME="schedula" \
  schedula-fastapi
```

## Typical Developer Loop

1. Start API with `uvicorn --reload`
2. Update code under `app/`
3. Run `pytest`
4. Update docs in `docs/`
5. Preview docs with `mkdocs serve`
