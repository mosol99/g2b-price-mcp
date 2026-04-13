FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

ENV G2B_SERVICE_KEY=""
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server:mcp._mcp_server.sse.app", "--host", "0.0.0.0", "--port", "8000"]
