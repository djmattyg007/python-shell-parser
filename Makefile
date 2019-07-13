test:
	pytest --cov --cov-report=html

docs:
	sphinx-build -a -n -b html -d docs/build/doctrees docs docs/build/html

.PHONY: test docs
