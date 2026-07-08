FROM python:3.12-slim

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

ENV DBSCHEMA_HOME=/opt/DbSchema
ENV DBSCHEMA_VERSION=9_7_1

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends default-jre-headless curl;\
    curl --http1.1 -fsSL "https://www.dbschema.com/download/dbschema_unix_9_7_1.tar.gz" -o /tmp/dbschema.tar.gz;\
    tar -xzf /tmp/dbschema.tar.gz -C /opt; \
    rm /tmp/dbschema.tar.gz; \
    mkdir -p "${DBSCHEMA_HOME}/lib"; \
    curl -fsSL "https://repo1.maven.org/maven2/org/testfx/openjfx-monocle/17.0.10/openjfx-monocle-17.0.10.jar" -o "${DBSCHEMA_HOME}/lib/monocle.jar"; \
    ln -sf "${DBSCHEMA_HOME}/DbSchemaCLI" /usr/local/bin/dbschemacli; \
    test -x "${DBSCHEMA_HOME}/DbSchemaCLI"; \
    rm -rf /var/lib/apt/lists/*

ENV HOME=/opt/app-root
RUN mkdir -p /opt/app-root/.DbSchema/cli /opt/app-root/.DbSchema/drivers/PostgreSql && \
    curl -fsSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar" -o /opt/app-root/.DbSchema/drivers/PostgreSql/postgresql.jar

RUN printf '%s\n' 'download driver oracle' > /tmp/download_oracle_driver.sql && \
    mkdir -p /opt/app-root/.DbSchema/drivers/Oracle && \
    dbschemacli /tmp/download_oracle_driver.sql && \
    if [ -f /opt/app-root/.DbSchema/drivers/Oracle/driver.zip ]; then \
        unzip -o /opt/app-root/.DbSchema/drivers/Oracle/driver.zip -d /opt/app-root/.DbSchema/drivers/Oracle && \
        rm -f /opt/app-root/.DbSchema/drivers/Oracle/driver.zip; \
    fi
    
RUN chmod -R g+rwX /opt/app-root/.DbSchema && \
    chmod 755 /opt/app-root

WORKDIR /opt/app-root
COPY requirements.txt .
RUN apt-get update; \
    apt-get install -y --no-install-recommends git;\
    pip install --no-cache-dir -r requirements.txt;\
    rm -rf /var/lib/apt/lists/*

ENV PATH="${DBSCHEMA_HOME}:${PATH}"

COPY src/ ./colin-extract-refresh/src/
RUN mkdir -p /opt/app-root/colin-extract-refresh/src/subset/generated && \
    chmod -R 777 /opt/app-root/colin-extract-refresh/src/subset/generated /opt/app-root/.DbSchema

WORKDIR /opt/app-root/colin-extract-refresh/src

EXPOSE 8080

COPY src .

CMD ["/bin/sh", "-c", "python /opt/app-root/colin-extract-refresh/src/test_connectivity.py && python /opt/app-root/colin-extract-refresh/src/generate_cprd_subset_extract.py --corp-file corp.txt --target-connection my_proxy_test --target-schema colin_extract_temp --mode refresh  && dbschemacli /opt/app-root/colin-extract-refresh/src/subset/generated/subset_refresh.sql"]