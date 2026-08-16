FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY api ./api
COPY route_optimizer ./route_optimizer
COPY frontend ./frontend
RUN pip install --no-cache-dir .
ENV PORT=8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
