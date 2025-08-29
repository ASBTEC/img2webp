# Dockerfile
FROM python:3.12-slim

# Native libs Pillow uses at runtime (no build toolchain needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libopenjp2-7 libtiff6 libwebp7 libwebpdemux2 libwebpmux3 zlib1g \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src .

# Default to showing help; compose overrides the command
ENTRYPOINT ["python", "/app/main.py"]
CMD ["--help"]