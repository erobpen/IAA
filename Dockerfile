FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EXPOSE 5000 (Not strictly needed for a script, but keeping just in case we add web server back)
EXPOSE 5000

CMD ["python", "analyzer.py"]
