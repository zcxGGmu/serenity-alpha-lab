FROM node:20-bookworm-slim AS web-builder

WORKDIR /build/apps/serenity-web
COPY apps/serenity-web/package.json apps/serenity-web/package-lock.json ./
RUN npm ci
COPY apps/serenity-web/ ./
RUN npm run build


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system serenity \
    && useradd --system --gid serenity --home-dir /app --shell /usr/sbin/nologin serenity

COPY pyproject.toml ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir .

COPY --from=web-builder /build/apps/serenity-web/dist /app/web
RUN mkdir -p /app/output/ui \
    && chown -R serenity:serenity /app

USER serenity

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import json, urllib.request; payload=json.load(urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=3)); assert payload.get('status') == 'ok' and payload.get('research_only') is True"]

CMD ["serenity-alpha-lab", "serve-app", "--host", "0.0.0.0", "--port", "8010"]
