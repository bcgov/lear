FROM python:3.11-slim

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"

ENV VCS_REF=${VCS_REF}
ENV BUILD_DATE=${BUILD_DATE}
ENV PYTHONUNBUFFERED=1
# ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_21_1


# Configure Jupyter to use user-writable paths

LABEL org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.build-date=${BUILD_DATE}


USER root


ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_4

RUN apt-get update; \
    apt-get install -y libpq-dev zlib1g-dev build-essential shared-mime-info libaio1 libaio-dev unzip wget --no-install-recommends; \
    wget https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-sdk-linux.x64-21.4.0.0.0dbru.zip; \
    wget https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-sqlplus-linux.x64-21.4.0.0.0dbru.zip; \
    wget https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-basic-linux.x64-21.4.0.0.0dbru.zip; \
    mkdir -p /opt/oracle; \
    cp instantclient-* /opt/oracle/ ; \
    cd /opt/oracle/ ; \
    unzip instantclient-basic-linux.x64-21.4.0.0.0dbru.zip ; \
    unzip instantclient-sdk-linux.x64-21.4.0.0.0dbru.zip ; \
    unzip instantclient-sqlplus-linux.x64-21.4.0.0.0dbru.zip ; \
    rm -rf /var/lib/apt/lists/* instantclient-basic-linux.x64-21.4.0.0.0dbru.zip instantclient-sdk-linux.x64-21.4.0.0.0dbru.zip instantclient-sqlplus-linux.x64-21.4.0.0.0dbru.zip ; \
    apt -y clean ; \
    apt -y remove wget unzip ; \
    apt -y autoremove ; \
    rm -rf /var/cache/apt

# Create directories with proper permissions
RUN mkdir -p /opt/app-root && \
    chmod 755 /opt/app-root

WORKDIR /opt/app-root

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

USER 1001

EXPOSE 8080

CMD [ "python", "/opt/app-root/test_connectivity.py" ]
