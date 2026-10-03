FROM python:3.14-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY app/ ./app
COPY tools/ /opt/tools/

RUN chmod +x /opt/tools/wt_ext_cli /opt/tools/binBlk

CMD ["python", "app/main.py"]
