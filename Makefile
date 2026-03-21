run:
	mkdir -p ./downloads
	uv run ./bin/bandcamptui -c cookies.txt -d downloads

test:
	uv run python -m pytest -v

lint:
	uvx ruff check

format:
	uvx ruff format

build:
	uv build
