FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn job_board_backend.wsgi:application --bind 0.0.0.0:8000"]
