.PHONY: build up down logs restart clean

build:
	docker compose build

up:
	docker compose up --build -d
	@echo ""
	@echo "╔════════════════════════════════════════════════╗"
	@echo "║  🏦 NovaPay Bank API is running!               ║"
	@echo "║                                                ║"
	@echo "║  API:        http://localhost:8080              ║"
	@echo "║  Swagger UI: http://localhost:8080/docs         ║"
	@echo "║  ReDoc:      http://localhost:8080/redoc        ║"
	@echo "║  OpenAPI:    http://localhost:8080/openapi.json  ║"
	@echo "╚════════════════════════════════════════════════╝"

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down && docker compose up --build -d

clean:
	docker compose down -v
	rm -f bank.db
