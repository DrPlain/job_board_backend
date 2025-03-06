FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Create a new user
RUN useradd -m celery_user

# Switch to the new user
USER celery_user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
