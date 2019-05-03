SRC_FILES=pysnip.py

BLACK_FLAGS=--line-length=79 --py36
CTAGS_FLAGS=--languages=Python

.PHONY: format tags compile-deps sync-deps

# This is very ugly. Please make it conform better to Makefile conventions.
refresh-deps: 
	@make compile-deps
	@make sync-deps

# Pin versions of packages specified in `requirements.in`.
compile-deps:
	@pip-compile --generate-hashes

# Sync site packages with versions in `requirements.txt`.
sync-deps:
	@pip-sync

requirements.txt: requirements.in
	@pip-compile --generate-hashes

tags:
	@ctags $(CTAGS_FLAGS) $(SRC_FILES)

format:
	@black $(BLACK_FLAGS) $(SRC_FILES)
	@# Make sure that tags are refreshed.
	@make tags
