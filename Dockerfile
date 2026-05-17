FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py channel.py seed.py seed.sql ./

EXPOSE 8080

CMD ["python", "app.py"]
