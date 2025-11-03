FROM python:3.13-bookworm

WORKDIR /app

COPY ./ /app

RUN python -m pip install -r requirements.txt

RUN python -m pip install gunicorn

CMD ["python3", "-m", "gunicorn", "-b", "0.0.0.0:8000", "main:app"]
