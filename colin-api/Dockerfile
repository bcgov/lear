FROM python:3.8.6-buster
USER root


# Installing Oracle instant client
WORKDIR    /opt/oracle
RUN        apt-get update && apt-get install -y libaio1 wget unzip \
    && wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip \
    && wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-sqlplus-linuxx64.zip \
    && unzip instantclient-basiclite-linuxx64.zip \
    && rm -f instantclient-basiclite-linuxx64.zip \
    && unzip instantclient-sqlplus-linuxx64.zip \
    && rm -f instantclient-sqlplus-linuxx64.zip \
    && cd /opt/oracle/instantclient* \
    && rm -f *jdbc* *occi* *mysql* *README *jar uidrvci genezi adrci \
    && echo /opt/oracle/instantclient* > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

# Create working directory
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
WORKDIR /opt/app-root

# Install the requirements
COPY ./requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./src

RUN pip install ./src

USER 1001

# Run the server
ENV PYTHONPATH=/opt/app-root/src

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080",  "--config", "/opt/app-root/src/gunicorn_config.py", "wsgi:application"]
