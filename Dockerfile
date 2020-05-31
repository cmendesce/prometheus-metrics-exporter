FROM python:3.7-slim
WORKDIR /app
ADD ./requirements.txt .
RUN pip install --upgrade pip && \ 
    pip install -r requirements.txt
ADD ./app.py .
EXPOSE 80
CMD gunicorn app:app --timeout 100 --bind 0.0.0.0:80