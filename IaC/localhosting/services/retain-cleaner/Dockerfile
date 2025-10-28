FROM python:3.11-slim
RUN groupadd -r myuser && useradd -r -g myuser myuser && pip install --no-cache-dir paho-mqtt==1.6.1
WORKDIR /app
COPY app.py /app/app.py
USER myuser
CMD ["python", "-u", "app.py"]
