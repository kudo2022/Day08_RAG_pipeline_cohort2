FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LEGAL_AGENT_DOMAIN=procurement

WORKDIR /app

COPY requirements.render.txt ./
RUN pip install --upgrade pip && pip install -r requirements.render.txt

COPY . .

RUN chmod +x /app/start.sh && python scripts/prepare_render_runtime.py

EXPOSE 10000

CMD ["/app/start.sh"]
