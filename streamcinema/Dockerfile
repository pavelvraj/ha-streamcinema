FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY run.sh /run.sh
RUN chmod a+x /run.sh

COPY app /app/app

CMD ["/run.sh"]
