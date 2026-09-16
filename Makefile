# POSIX twin of reproduce.ps1 (ROADMAP item 39). `make reproduce` regenerates LEADERBOARD.md and the
# explorer snapshot from the committed results; `make reproduce-full` also reruns the two headline
# result files on the pinned connectomes (~40 min with JOBS=6). `make docker` builds the image and
# runs the toy suite inside it.
JOBS ?= 6
export PYTHONUTF8 = 1

.PHONY: reproduce reproduce-full test lint docker

lint:
	python -m flybench lint

test:
	python -m pytest -q

reproduce: lint test
	python -m flybench compare results -o LEADERBOARD.md
	@if [ -f ../fly-explorer/scripts/leaderboard-snapshot.py ]; then cd ../fly-explorer && python scripts/leaderboard-snapshot.py ../flybench && npm test; fi
	git status --short LEADERBOARD.md results
	@echo "reproduce: done. A non-empty status above means a committed number changed."

reproduce-full: lint test
	python -m flybench run -c flywire783 --gain 0.45 --seeds 3 --controls rewired --jobs $(JOBS) --label "LIF gain 0.45 (3 seeds)" -o results/flywire783_gain0.45.json
	python -m flybench run -c malecns --gain 0.65 --seeds 3 --controls rewired --jobs $(JOBS) --label "MaleCNS gain 0.65 (Minecraft demo)" -o results/malecns-gain-0.65.json
	$(MAKE) reproduce

docker:
	docker build -t flybench .
	docker run --rm flybench
