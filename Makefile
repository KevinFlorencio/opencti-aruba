SHELL := /bin/bash
COMPOSE := docker compose

.PHONY: help up down ps logs collect build refresh seed backup deploy-site

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Start OpenCTI, connectors and the site
	$(COMPOSE) up -d
	$(COMPOSE) ps

down: ## Stop the stack (volumes preserved)
	$(COMPOSE) down

ps: ## Container status
	$(COMPOSE) ps

logs: ## Follow OpenCTI logs
	$(COMPOSE) logs -f --tail=100 opencti

collect: ## Build one snapshot from OpenCTI + MISP
	set -a; . ./.env; set +a; \
	OPENCTI_TOKEN=$$OPENCTI_ADMIN_TOKEN MISP_KEY=$$MISP_API_KEY \
	python3 scripts/collect_radar.py --pretty

build: ## Build the static site
	cd site && npm run build

refresh: ## Collect + rebuild (same entrypoint as the timer)
	./scripts/refresh.sh

seed: ## Push the curated Aruba STIX bundle into OpenCTI
	set -a; . ./.env; set +a; \
	OPENCTI_TOKEN=$$OPENCTI_ADMIN_TOKEN python3 scripts/seed_aruba.py

backup: ## Backup config, MISP DB and OpenCTI volumes (needs root for /mnt/hdd)
	sudo ./scripts/backup.sh

deploy-site: ## Copy a locally built site to the VM
	tar czf - site/dist | ssh $${DEPLOY_HOST:?set DEPLOY_HOST} 'rm -rf ~/aruba-ti/site/dist && tar xzf - -C ~/aruba-ti'
