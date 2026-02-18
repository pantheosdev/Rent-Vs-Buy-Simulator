.PHONY: run qa preflight preflight-fast build-release vr-smoke vr-update vr-compare

run:
	streamlit run app.py

qa:
	python run_all_qa.py

preflight:
	python scripts/preflight.py --run-vr-smoke

preflight-fast:
	python scripts/preflight.py

build-release:
	python scripts/build_release_zip.py --name rent-vs-buy-simulator

vr-smoke:
	python tools/visual_regression/vr_playwright.py --smoke

vr-update:
	python tools/visual_regression/vr_playwright.py --update-baseline

vr-compare:
	python tools/visual_regression/vr_playwright.py
