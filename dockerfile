FROM python:3.14-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app
COPY tools/ /opt/tools/

RUN chmod +x /opt/tools/wt_ext_cli /opt/tools/binBlk

CMD ["python", "main.py"]
