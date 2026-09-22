FROM docker.m.daocloud.io/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=0 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=5100

WORKDIR /app/backend

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt gunicorn

COPY backend /app/backend

EXPOSE 5100
CMD ["gunicorn", "-w", "1", "-k", "gthread", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:5100", "run:app"]
