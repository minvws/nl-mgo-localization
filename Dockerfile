# syntax=docker/dockerfile:1
# syntax directive is used to enable Docker BuildKit

ARG PYTHON_VERSION=3.11

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS base

ARG PROJECT_DIR="/src" \
    APP_USER="app" \
    APP_GROUP="app" \
    NEW_UID=1000 \
    NEW_GID=1000 \
    VENV_PATH=/opt/venv

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=${VENV_PATH}

# Create a non-privileged user that the app will run under.
RUN groupadd --system ${APP_GROUP} --gid=${NEW_GID} && \
    adduser \
        --disabled-password \
        --gecos "" \
        --uid ${NEW_UID} \
        --gid ${NEW_GID} \
        ${APP_USER}

RUN apt-get update && \
    apt-get install -y \
        git \
        gnupg2 \
        make \
        vim \
        postgresql-client \
        postgresql-client-common \
        procps \
        && rm -rf /var/lib/apt/lists/*

WORKDIR ${PROJECT_DIR}

FROM base AS builder

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM base

ARG PROJECT_DIR
ARG APP_USER
ARG VENV_PATH

COPY --from=builder --chown=${APP_USER}:${APP_GROUP}  ${VENV_PATH} ${VENV_PATH}

USER ${APP_USER}

EXPOSE 8006:8006
WORKDIR ${PROJECT_DIR}

ENV PYTHONPATH=${PROJECT_DIR} \
    PATH="${VENV_PATH}/bin:$PATH"

ENTRYPOINT ["/src/docker-entrypoint.sh"]
CMD ["python", "app/main.py"]
