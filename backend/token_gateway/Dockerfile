FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

COPY backend/token_gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY CHANGELOG.md /app/CHANGELOG.md

RUN chmod +x /app/backend/token_gateway/start.sh

EXPOSE 9099

CMD ["/app/backend/token_gateway/start.sh"]

