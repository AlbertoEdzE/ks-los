.PHONY: up down logs test db-reset check-infra

up:
	docker-compose -f infrastructure/docker-compose.yml up -d

down:
	docker-compose -f infrastructure/docker-compose.yml down

logs:
	docker-compose -f infrastructure/docker-compose.yml logs -f

test:
	pytest src/tests

db-reset:
	docker-compose -f infrastructure/docker-compose.yml down -v
	docker-compose -f infrastructure/docker-compose.yml up -d

check-infra:
	curl -f http://localhost:11434/api/tags || echo "Ollama not healthy"
