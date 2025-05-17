# Use an ARM-compatible base image (for Raspberry Pi)
FROM python:3.11-slim

WORKDIR /filer

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
