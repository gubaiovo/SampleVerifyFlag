FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

RUN mkdir -p /app/data/users \
             /app/data/challenge/zips \
             /app/data/challenge/exps

EXPOSE 5000

CMD ["python", "src/app.py"]