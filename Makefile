.PHONY: check test test-cov cov-report cov-html cov

check:
	uv run mypy .

test:
	uv run pytest tests

lint:
	uv run ruff check .
	uv run --with mypy mypy pythemes

testcov:
	uv run coverage run -m pytest tests

cov-report:
	uv run coverage report

cov-html:
	uv run coverage html

cov: test-cov cov-report cov-html
