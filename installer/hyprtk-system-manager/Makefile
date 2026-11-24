.PHONY: test run install version qa doctor panels

test:
	PYTHONPATH=backend python3 -m unittest discover -s tests -v

run:
	./bin/hyprtk-settings open

install:
	./install.sh

version:
	PYTHONPATH=backend python3 -m system_manager.cli version

panels:
	PYTHONPATH=backend python3 -m system_manager.cli panels

doctor:
	PYTHONPATH=backend python3 -m system_manager.cli doctor

qa:
	./scripts/qa.sh
