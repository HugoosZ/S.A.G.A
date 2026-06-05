PORTAL  = clients/portal-admin
VENV    = $(PORTAL)/.venv
PYTHON  = $(VENV)/bin/python
PIP     = $(VENV)/bin/pip

# Intérprete usado para crear el venv. Sobrescribir cuando el python3 por
# defecto no tiene Tk (pyenv suele compilarse sin _tkinter):
#   make install PYTHON3=/opt/homebrew/bin/python3.11
PYTHON3 ?= python3

.PHONY: help install run build up down logs clean

help:
	@echo "Portal Admin"
	@echo "  make install                       Create virtualenv and install dependencies"
	@echo "  make install PYTHON3=/path/python  Use a specific interpreter (needs Tk)"
	@echo "  make run                           Launch the desktop app"
	@echo "  make build                         Package into a standalone executable (dist/SAGA/)"
	@echo ""
	@echo "Infrastructure"
	@echo "  make up        Start BUS + ChromaDB (docker-compose)"
	@echo "  make down      Stop containers"
	@echo "  make logs      Tail container logs"
	@echo ""
	@echo "  make clean     Remove virtualenv and build artifacts"

install:
	@$(PYTHON3) -c "import tkinter" 2>/dev/null || (echo "El intérprete '$(PYTHON3)' no tiene Tk. Reinstala Python con soporte Tcl/Tk o sobrescribe PYTHON3, por ejemplo: make install PYTHON3=/opt/homebrew/bin/python3.11" && exit 1)
	$(PYTHON3) -m venv $(VENV)
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
