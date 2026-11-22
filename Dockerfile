ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl git \
    && rm -rf /var/lib/apt/lists/*

COPY versions.env .
RUN . ./versions.env \
    && curl -sSfLo /usr/local/bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v"$TAILWIND_VERSION"/tailwindcss-linux-x64 \
    && chmod +x /usr/local/bin/tailwindcss

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
