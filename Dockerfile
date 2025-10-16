FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# install system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copy only what's needed for the backend
COPY app/backend/ ./backend/
COPY pyproject.toml ./
COPY requirements-dev.txt ./

WORKDIR /app/backend

# install python deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

EXPOSE 50505

ENV PORT=50505

CMD ["python", "-m", "quart", "--app", "main:app", "run", "--host", "0.0.0.0", "--port", "50505"]
