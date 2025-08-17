FROM python:3.9-slim  # Local dev; use nvcr.io/nvidia/pytorch:25.07-py3 for EC2
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY data/ ./data/
EXPOSE 5000
CMD ["python", "-m", "app.app"]