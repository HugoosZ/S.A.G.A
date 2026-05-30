PORTAL = client/portal-admin
VENV   = $(PORTAL)/.venv
PYTHON = $(VENV)/bin/python
PIP    = $(VENV)/bin/pip

.PHONY: help install run build up down logs clean

help:
	@echo "Portal Admin"
	@echo "  make install   Create virtualenv and install dependencies"
	@echo "  make run       Launch the desktop app"
	@echo "  make build     Package into a standalone executable (dist/SAGA/)"
	@echo ""
	@echo "Infrastructure"
	@echo "  make up        Start BUS + ChromaDB (docker-compose)"
	@echo "  make down      Stop containers"
	@echo "  make logs      Tail container logs"
	@echo ""
	@echo "  make clean     Remove virtualenv and build artifacts"

install:
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r $(PORTAL)/requirements.txt
	@echo "Done. Run 'make run' to start the app."

run:
	@test -f $(PYTHON) || (echo "Virtualenv not found — run 'make install' first." && exit 1)
	cd $(PORTAL) && .venv/bin/python main.py

build:
	@test -f $(PYTHON) || (echo "Virtualenv not found — run 'make install' first." && exit 1)
	cd $(PORTAL) && .venv/bin/python build.py

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	rm -rf $(VENV) $(PORTAL)/dist $(PORTAL)/build $(PORTAL)/SAGA.spec
