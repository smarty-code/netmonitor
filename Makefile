.PHONY: test install uninstall pack check

test:
	python3 -m pytest

check:
	python3 -m pytest

install:
	./scripts/install.sh

uninstall:
	./scripts/uninstall.sh

pack:
	./scripts/pack.sh
