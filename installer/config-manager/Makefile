APP := hyprtk-config-manager

.PHONY: install uninstall dry-run run test

install:
	./install.sh

uninstall:
	./install.sh --uninstall

dry-run:
	./install.sh --dry-run

run:
	qs -p .

test:
	python3 -m unittest discover -s tests
