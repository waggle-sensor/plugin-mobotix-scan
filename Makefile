all:

.PHONY: test
test:
	docker build -t plugin-mobotix-sampler .
	docker run --rm --entrypoint=python3 plugin-mobotix-sampler app/test.py
