FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /var/lib/relaydesk && chown 65532:65532 /var/lib/relaydesk
USER 65532:65532
CMD ["python", "-m", "app.relay_api"]
