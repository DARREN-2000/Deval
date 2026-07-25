# Multi-stage build: the wheel is built in a throwaway stage so that build
# tooling (hatchling, setuptools) never reaches the published image.
FROM python:3.14-slim AS build

WORKDIR /build

# Pinned so an upstream release cannot silently change how the wheel is built.
RUN pip install --no-cache-dir hatchling==1.25.0

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m hatchling build -t wheel && ls -1 dist


FROM python:3.14-slim AS runtime

LABEL org.opencontainers.image.title="deval" \
      org.opencontainers.image.description="The open-source Engineering Standards Platform - one deterministic health score for any repository." \
      org.opencontainers.image.source="https://github.com/DARREN-2000/deval" \
      org.opencontainers.image.documentation="https://darren-2000.github.io/deval/" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Deval has no runtime dependencies, so this installs exactly one package.
COPY --from=build /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Scanning untrusted repositories as root is a poor default.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin deval
USER deval

# Mount the repository under test here, ideally read-only:
#   docker run --rm -v "$PWD:/repo:ro" ghcr.io/darren-2000/deval:latest
WORKDIR /repo

ENTRYPOINT ["deval"]
CMD ["scan", "."]
