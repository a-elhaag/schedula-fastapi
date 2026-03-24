# Quickstart

Prerequisites

- Python 3.11+
- A virtual environment (recommended)

Install dependencies and run locally:

1. Create and activate a virtualenv (example):

   python -m venv .venv
   source .venv/bin/activate

2. Install requirements:

   pip install -r requirements.txt

3. Serve the docs locally:

   mkdocs serve

4. Run the API (in another shell):

   source .venv/bin/activate
   uvicorn app.main:app --reload
