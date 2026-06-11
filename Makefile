.PHONY: docs update-logo

update-logo:
	python3 scripts/update_logo.py

docs: update-logo
	# 1. Clean previous build
	rm -rf docs_out

	# 2. Generate HTML
	PYTHONPATH=src pdoc --math -d google -o docs_out aigf \
		--logo "assets/logo.svg" \
		--favicon "assets/logo.svg"

	# 3. Manually copy the assets folder into docs so links work
	cp -r assets docs_out/assets

	@echo "Documentation built successfully!"
