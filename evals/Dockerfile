ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt /tmp/eval-requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r /tmp/eval-requirements.txt

COPY . /app/evals/
