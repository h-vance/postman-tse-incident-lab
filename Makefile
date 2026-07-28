.PHONY: serve verify

serve:
	python3 lab_api.py

verify:
	bash scripts/verify.sh
