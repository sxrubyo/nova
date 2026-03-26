.PHONY: run test lint seed verify format install dev

run:
	python nova.py start

test:
	pytest tests/ -v --cov=nova

lint:
	ruff check nova/ tests/
	black --check nova/ tests/
	mypy nova/

format:
	black nova/ tests/
	ruff check --fix nova/ tests/

seed:
	python scripts/seed_data.py

verify:
	python nova.py ledger verify

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	python scripts/seed_data.py
	python nova.py start
