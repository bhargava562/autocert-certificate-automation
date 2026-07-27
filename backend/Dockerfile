FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies will be installed once the backend package scaffold exists.
COPY . /app

CMD ["bash", "-lc", "python -V && sleep infinity"]