FROM python:3.14-slim

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY src/ ./src
COPY tools/ /opt/tools/

RUN chmod +x /opt/tools/wt_ext_cli /opt/tools/binBlk

CMD ["python", "src/main.py"]
