FROM python:3.11-slim

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"

ENV VCS_REF=${VCS_REF}
ENV BUILD_DATE=${BUILD_DATE}
ENV PYTHONUNBUFFERED=1
ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_21_1


# Configure Jupyter to use user-writable paths

LABEL org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.build-date=${BUILD_DATE}


USER root

WORKDIR /opt/oracle

RUN apt-get update; \
    apt-get install -y --no-install-recommends libaiol wget unzip ca-certificates; \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/211000/instantclient-basiclite-linux.x64-21.1.0.0.0.zip; \
    unzip instantclient-basiclite-linux.x64-21.1.0.0.0.zip; \
    rm -f instantclient-basiclite-linux.x64-21.1.0.0.0.zip; \
    cd "${ORACLE_CLIENT_LIB_DIR}"; \
    rm -f *jdbc* *occi* *mysql* *README *jar uidvrci genezi adrci; \
    echo "${ORACLE_CLIENT_LIB_DIR}" > /etc/ld.so.conf.d/oracle-instantclient.conf; \
    ldconfig; \
    rm -rf /var/lib/apt/lists/*

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
