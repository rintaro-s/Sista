FROM python:3.11-slim
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
# copy wait script and ensure it's executable
COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh || true
# copy python-based wait script too and make executable
COPY wait-for-db.py /wait-for-db.py
RUN chmod +x /wait-for-db.py || true

COPY start.sh /start.sh
RUN chmod +x /start.sh || true

# Use python wait script as entrypoint so the backend waits for the DB to become ready
ENTRYPOINT ["sh", "-c", "python /wait-for-db.py && echo 'wait-for-db succeeded, starting uvicorn' && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
