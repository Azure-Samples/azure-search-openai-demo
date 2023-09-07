FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

RUN python -m pip install --upgrade pip

WORKDIR /demo-code

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY . .
CMD bash -c ". entrypoint.sh"
