FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install -r /app/requirements.txt

CMD ["python", "main.py"]