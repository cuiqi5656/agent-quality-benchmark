.PHONY: dev api test check docker-up docker-down

dev:
	pnpm dev

api:
	pnpm api

test:
	pnpm test:python
	pnpm test

check:
	pnpm check

docker-up:
	docker compose up --build

docker-down:
	docker compose down
