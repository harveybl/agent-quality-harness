.PHONY: check

check:
	PYTHONPATH=src python3 scripts/lint_steps.py
	PYTHONPATH=src python3 -m unittest discover -s evaluator/tests -v
	PYTHONPATH=src python3 -m unittest discover -s frontier/tests -v
	PYTHONPATH=src python3 -m unittest discover -s local/tests -v
	PYTHONPATH=src python3 -m unittest discover -s tests -v
