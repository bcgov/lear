.PHONY: help build build-nc smoke-local validate shellcheck yaml-parse template-required-params contract-validate

MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_ABS_DIR := $(patsubst %/,%,$(dir $(MKFILE_PATH)))
REPO_ROOT := $(abspath $(CURRENT_ABS_DIR)/../..)
PROJECT_NAME := colin-extract-delta
DOCKER_NAME := colin-extract-delta
TAG_NAME ?= dev
CHECKSUM_BUILD_ARGS = \
	--build-arg DBSCHEMA_SHA256="$(DBSCHEMA_SHA256)" \
	--build-arg ORACLE_IC_SHA256="$(ORACLE_IC_SHA256)" \
	--build-arg POSTGRES_JDBC_SHA256="$(POSTGRES_JDBC_SHA256)" \
	--build-arg ORACLE_JDBC_SHA256="$(ORACLE_JDBC_SHA256)" \
	--build-arg CLOUD_SQL_PROXY_SHA256="$(CLOUD_SQL_PROXY_SHA256)"

build: ## Build the runtime image from the repo root context; requires checksum build args
	docker build --platform linux/amd64 -f $(CURRENT_ABS_DIR)/Dockerfile -t $(DOCKER_NAME):$(TAG_NAME) $(REPO_ROOT) \
		--build-arg VCS_REF=$$(git -C $(REPO_ROOT) rev-parse --short HEAD 2>/dev/null || echo missing) \
		--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
		$(CHECKSUM_BUILD_ARGS)

build-nc: ## Build the runtime image without cache; requires checksum build args
	docker build --no-cache --platform linux/amd64 -f $(CURRENT_ABS_DIR)/Dockerfile -t $(DOCKER_NAME):$(TAG_NAME) $(REPO_ROOT) \
		$(CHECKSUM_BUILD_ARGS)

smoke-local: ## Run wrapper smoke mode in an already-built image; requires DB/Cloud SQL env vars
	docker run --rm --env-file .env \
		-e SMOKE_ONLY=true \
		-e APP_DATA=/opt/app-root/data \
		$(DOCKER_NAME):$(TAG_NAME)

shellcheck: ## Shell lint if shellcheck is installed
	@if command -v shellcheck >/dev/null 2>&1; then shellcheck $(CURRENT_ABS_DIR)/run.sh; else echo "shellcheck not installed; skipping"; fi

yaml-parse: ## Parse OpenShift templates after replacing template placeholders with simple values
	python -c 'from pathlib import Path; import importlib.util, re, sys; \
spec=importlib.util.find_spec("yaml"); \
(spec is not None) or (print("PyYAML is not installed; skipping yaml parse") or sys.exit(0)); \
import yaml; base=Path("$(CURRENT_ABS_DIR)")/"openshift"/"templates"; \
paths=[base/"bc.yaml", base/"cronjob.yaml"]; \
[print(f"parsed {p}") for p in paths for _ in [yaml.safe_load(re.sub(r"\$$\{[A-Z0-9_]+\}", "placeholder", re.sub(r"\$$\{\{[A-Z0-9_]+\}\}", "1", p.read_text())))] ]'

template-required-params: ## Ensure rollout-specific CronJob params are required and have no concrete defaults
	python -c 'from pathlib import Path; import re, sys; \
text=Path("$(CURRENT_ABS_DIR)/openshift/templates/cronjob.yaml").read_text(); \
required={"TAG","IMAGE_NAMESPACE","IMAGE_TAG","DBSCHEMA_SOURCE_CONNECTION","DBSCHEMA_TARGET_CONNECTION","DBSCHEMA_TARGET_SCHEMA","GCP_SA_SECRET_NAME","GCP_SA_SECRET_KEY"}; \
params={m.group("name"):m.group("body") for m in re.finditer(r"(?ms)^  - name: (?P<name>[A-Z0-9_]+)\n(?P<body>.*?)(?=^  - name: |\Z)", text)}; \
errors=[]; \
[errors.append(f"missing parameter {name}") for name in sorted(required) if name not in params]; \
[errors.append(f"{name} must be required") for name in sorted(required) if name in params and not re.search(r"^    required: true$$", params[name], re.M)]; \
[errors.append(f"{name} must not define a concrete value/default") for name in sorted(required) if name in params and re.search(r"^    value:\s*", params[name], re.M)]; \
print("cronjob required rollout params are explicit") if not errors else (print("\n".join(errors), file=sys.stderr), sys.exit(1))'

contract-validate: ## Validate OCP wrapper/data-tool flow and generator contracts without requiring pytest
	python $(CURRENT_ABS_DIR)/validate_contract.py

validate: shellcheck yaml-parse template-required-params contract-validate ## Run lightweight local validation
	bash -n $(CURRENT_ABS_DIR)/run.sh
	python -m py_compile $(REPO_ROOT)/data-tool/flows/refresh_extract_subset_flow.py

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
