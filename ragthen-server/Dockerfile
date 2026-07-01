FROM python:3.13-slim

WORKDIR /app

COPY ragthen-core/ /app/ragthen-core
RUN pip install -e /app/ragthen-core

COPY ragthen-server/ /app/ragthen-server
RUN pip install -e /app/ragthen-server

EXPOSE 8000

CMD ["uvicorn", "ragthen_server.api:app", "--host", "0.0.0.0", "--port", "8000"]
