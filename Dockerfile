FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

COPY docker-entrypoint.sh /usr/local/bin/arkive-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/arkive-entrypoint \
    && chmod +x /usr/local/bin/arkive-entrypoint

ENTRYPOINT ["arkive-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
