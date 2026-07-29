FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir flask akshare openai pandas werkzeug
COPY . .
EXPOSE 51888
CMD ["python","server.py"]
