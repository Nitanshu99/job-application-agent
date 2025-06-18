# Phi-3 Mini Model Service
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY model_server.py .

EXPOSE 8001

CMD ["python", "model_server.py"]
