.PHONY: test run version qa

test:
	PYTHONPATH=backend python3 -m unittest discover -s tests -v

run:
	QT_QPA_PLATFORMTHEME=$${QT_QPA_PLATFORMTHEME:-gtk3} qs -p .

version:
	PYTHONPATH=backend python3 -m hyprtk_file_manager.cli version

qa:
	./scripts/qa.sh
