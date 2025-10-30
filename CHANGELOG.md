# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- chore: remove demo LLM helper `make_greeting` and `api_hello` smoke-test walker from `backend/main.jac` to remove non-production/demo code. (tests: all existing Python tests pass locally)

## Notes

- This cleanup removes a small demo-only endpoint and a byllm Model instantiation that were used for smoke-testing. Production LLM usages (e.g., agent-based summaries) were left intact.
