FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY repoman/ repoman/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["repoman", "serve"]
