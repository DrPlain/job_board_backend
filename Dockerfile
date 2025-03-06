FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN useradd -ms /bin/bash celery
RUN chown -R celery:celery /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
