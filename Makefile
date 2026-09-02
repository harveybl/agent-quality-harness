.PHONY: check

check:
	python3 scripts/lint_steps.py
	python3 -m unittest discover -s evaluator/tests -v
	python3 -m unittest discover -s frontier/tests -v
	python3 -m unittest discover -s local/tests -v
	python3 -m unittest discover -s tests -v
