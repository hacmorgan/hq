SHELL := /usr/bin/env bash


###############
# Tests
###############

test: # Run all tests
	@pytest \
		--verbose \
		--log-level=WARNING \
		--log-cli-level=WARNING \
		applications/tests

