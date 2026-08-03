FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gee_export.py run_loop.sh ./
RUN chmod +x run_loop.sh

CMD ["./run_loop.sh"]
