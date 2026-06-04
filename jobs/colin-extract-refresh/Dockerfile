FROM python:3.11-slim

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"

ENV VCS_REF=${VCS_REF}
ENV BUILD_DATE=${BUILD_DATE}
ENV PYTHONUNBUFFERED=1





LABEL org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.build-date=${BUILD_DATE}


USER root

ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_21_4
ENV LD_LIBRARY_PATH=${ORACLE_CLIENT_LIB_DIR}


WORKDIR /opt/oracle/
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends unzip wget ca-certificates;\
    apt-get install -y --no-install-recommends libaio1 || apt-get install -y --no-install-recommends libaio1t64; \
    ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1 || true; \
    ln -sf /lib/x86_64-linux-gnu/libaio.so.1t64 /lib/x86_64-linux-gnu/libaio.so.1 || true; \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-basic-linux.x64-21.4.0.0.0dbru.zip; \
    unzip instantclient-basic-linux.x64-21.4.0.0.0dbru.zip; \
    rm instantclient-basic-linux.x64-21.4.0.0.0dbru.zip; \
    cd "${ORACLE_CLIENT_LIB_DIR}"; \
    rm -f *jdbc* *occi* *mysql* *README *jar uidrvci genezi adrci; \
    test -e libclntsh.so || ln -sf libclntsh.so.* libclntsh.so; \
    test -f libclntsh.so; \
    echo "${ORACLE_CLIENT_LIB_DIR}" > /etc/ld.so.conf.d/oracle-instantclient.conf; \
    ldconfig; \
    chmod 755 "${ORACLE_CLIENT_LIB_DIR}"; \
    rm -rf /var/lib/apt/lists/*

# Create directories with proper permissions
RUN mkdir -p /opt/app-root && \
    chmod 755 /opt/app-root

WORKDIR /opt/app-root

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER 1001

EXPOSE 8080

COPY . .

CMD [ "python", "/opt/app-root/test_connectivity.py" ]
