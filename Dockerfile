FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir openai pyyaml

EXPOSE 9880

CMD ["python", "-m", "mimo_tts_proxy.app"]
