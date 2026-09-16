# flybench on the toy connectome: the code, the tests and a full toy run, with no download.
# The real connectomes are built from Codex / neuPrint exports (`flybench build`, `flybench fetch-neuprint`)
# and pinned by fingerprint in flybench/manifests.json; mount a cache at /root/.cache/flybench to use them.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY flybench ./flybench
COPY tasks ./tasks
COPY tests ./tests
COPY docs ./docs
RUN pip install --no-cache-dir . pytest
ENV PYTHONUTF8=1
CMD python -m flybench lint && python -m pytest -q && python -m flybench run -c toy --seeds 2 --controls rewired --jobs 2 --label "toy (docker)"
