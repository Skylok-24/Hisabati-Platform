# Python image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# تثبيت dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# نسخ المشروع
COPY . .

EXPOSE 8000

# تشغيل migrations ثم gunicorn
CMD sh -c "python manage.py migrate && gunicorn trusthandle.wsgi:application --bind 0.0.0.0:8000 --workers 3"