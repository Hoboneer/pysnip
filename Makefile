SRC_FILES=pysnip.py pyfs.py

# Max line length of 79 chars makes working in a vertically-split terminal
# window easier.
BLACK_FLAGS=--line-length=79 --py36
CTAGS_FLAGS=--languages=Python
ISORT_FLAGS=--atomic --multi-line=3 --trailing-comma

.PHONY: refresh-deps
# This is very ugly. Please make it conform better to Makefile conventions.
refresh-deps: 
	@make compile-deps
	@make sync-deps

.PHONY: compile-deps
# Pin versions of packages specified in `requirements.in`.
compile-deps:
	@pip-compile --generate-hashes

.PHONY: compile-deps-dev
# Pin versions of packages specified in `requirements-dev.in`.
compile-deps-dev:
	@pip-compile --generate-hashes requirements-dev.in

.PHONY: sync-deps
# Sync site packages with versions in `requirements.txt`.
sync-deps:
	@pip-sync

.PHONY: tags
tags:
	@ctags $(CTAGS_FLAGS) $(SRC_FILES)

.PHONY: sort-imports
sort-imports:
	@isort $(ISORT_FLAGS) $(SRC_FILES)

.PHONY: format
format: sort-imports
	@black $(BLACK_FLAGS) $(SRC_FILES)
	@# Make sure that tags are refreshed.
	@make tags

.PHONY: lint
lint:
	@flake8 $(SRC_FILES)

.PHONY: typecheck
typecheck:
	@mypy $(SRC_FILES)
