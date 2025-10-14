PYTHON := ".venv/bin/python3"
.ONESHELL:  # run all commands in a single shell, ensuring it runs within a local virtual env

dev:
	pip install --upgrade pip poetry poetry-plugin-export
	poetry config --local virtualenvs.in-project true
	poetry install --no-root

update-deps:
	poetry update
