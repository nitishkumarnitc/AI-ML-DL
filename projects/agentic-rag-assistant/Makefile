.PHONY: help setup ingest run serve eval test lint format clean docker-build docker-run compose-up

# Override the interpreter if needed, e.g. `make PY=python3.11 test`.
PY ?= python
# Pass a question to `make run`, e.g. `make run Q="How long is the warranty?"`.
Q ?=

help:
	@echo "Targets:"
	@echo "  setup        - create .venv and install the package with dev extras"
	@echo "  ingest       - build the local Chroma index from data/knowledge"
	@echo "  run          - run the CLI agent (make run Q=\"your question\")"
	@echo "  serve        - run the FastAPI server locally (uvicorn; needs the .[api] extra)"
	@echo "  eval         - run the eval harness + CI-style eval gate (needs a key)"
	@echo "  test         - run unit tests (offline, no key required)"
	@echo "  lint         - run ruff"
	@echo "  format       - auto-format with ruff"
	@echo "  clean        - remove caches and the local index"
	@echo "  docker-build - build the Docker image (agentic-rag-assistant)"
	@echo "  docker-run   - run the image, mapping port 8000 (needs .env)"
	@echo "  compose-up   - docker compose up --build"

setup:
	$(PY) -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"
	@echo "Next: cp .env.example .env  and set ANTHROPIC_API_KEY"

ingest:
	$(PY) -m src.agent.retrieval

run:
	$(PY) -m src.app $(Q)

serve:
	$(PY) -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

eval:
	$(PY) -m evals.run_evals

test:
	$(PY) -m pytest

lint:
	ruff check .

format:
	ruff format .

clean:
	rm -rf .chroma .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

docker-build:
	docker build -t agentic-rag-assistant .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env agentic-rag-assistant

compose-up:
	docker compose up --build
