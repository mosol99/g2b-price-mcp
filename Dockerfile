FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# 환경변수: G2B_SERVICE_KEY를 배포 시 설정
ENV G2B_SERVICE_KEY=""

EXPOSE 8000

CMD ["python", "server.py"]
