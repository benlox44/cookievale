ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY versions.env .

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev postgresql-client make curl \
    && rm -rf /var/lib/apt/lists/*

RUN . ./versions.env \
    && curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v"$TAILWIND_VERSION"/tailwindcss-linux-x64 \
    && mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss \
    && chmod +x /usr/local/bin/tailwindcss

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
