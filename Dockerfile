# //FROM python:3.9-slim

#//WORKDIR /app

#//COPY requirements.txt .
#//RUN pip install --no-cache-dir -r requirements.txt

#//COPY . .

#//# If you have a service account key file, uncomment the next line
#//# COPY ee-key.json .

##CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app