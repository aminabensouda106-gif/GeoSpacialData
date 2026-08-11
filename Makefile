.PHONY: bootstrap up down logs reset seed test

# Each target wraps a POSIX shell script in scripts/, so the same logic runs
# whether invoked via `make` (Linux/CI/WSL) or `bash scripts/<name>.sh`
# directly (e.g. Windows/Git Bash hosts without GNU make installed).

bootstrap:
	bash scripts/bootstrap.sh

up:
	bash scripts/up.sh

down:
	bash scripts/down.sh

logs:
	bash scripts/logs.sh

reset:
	bash scripts/reset.sh

seed:
	bash scripts/seed.sh

test:
	bash scripts/test.sh
