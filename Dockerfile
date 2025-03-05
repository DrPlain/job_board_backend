FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN useradd -m -r appuser && chown appuser:appuser /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
