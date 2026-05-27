# Build from the repository root so this image can copy data-tool/ and the job wrapper:
#   docker build --platform linux/amd64 -f jobs/colin-extract-delta/Dockerfile -t colin-extract-delta .
FROM --platform=linux/amd64 python:3.11-slim-bullseye

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"
ARG DBSCHEMA_VERSION="9_7_1"
ARG DBSCHEMA_URL="https://dbschema.com/download/dbschema_unix_9_7_1.tar.gz"
ARG CLOUD_SQL_PROXY_VERSION="2.20.0"
ARG ORACLE_IC_VERSION="21_1"
ARG ORACLE_IC_ZIP="instantclient-basiclite-linux.x64-21.1.0.0.0.zip"
ARG ORACLE_IC_URL="https://download.oracle.com/otn_software/linux/instantclient/211000/instantclient-basiclite-linux.x64-21.1.0.0.0.zip"
ARG POSTGRES_JDBC_VERSION="42.7.3"
ARG ORACLE_JDBC_VERSION="23.4.0.24.05"
ARG DBSCHEMA_SHA256=""
ARG ORACLE_IC_SHA256=""
ARG POSTGRES_JDBC_SHA256=""
ARG ORACLE_JDBC_SHA256=""
ARG CLOUD_SQL_PROXY_SHA256=""

ENV VCS_REF=${VCS_REF} \
    BUILD_DATE=${BUILD_DATE} \
    DBSCHEMA_VERSION=${DBSCHEMA_VERSION} \
    APP_HOME=/opt/app-root \
    APP_DATA=/opt/app-root/data \
    HOME=/opt/app-root \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ORACLE_HOME=/opt/oracle/instantclient_21_1 \
    LD_LIBRARY_PATH=/opt/oracle/instantclient_21_1 \
    PATH=/opt/dbschema:/opt/oracle/instantclient_21_1:/opt/app-root/.local/bin:${PATH} \
    DBSCHEMA_DRIVER_DIR=/opt/jdbc \
    PYTHONPATH=/opt/app-root/data-tool/flows:/opt/app-root/data-tool

LABEL org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.build-date=${BUILD_DATE} \
      org.opencontainers.image.title="colin-extract-delta" \
      org.opencontainers.image.description="OCP runtime for COLIN extract delta refresh using data-tool and DbSchemaCLI"

USER root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       curl \
       build-essential \
       git \
       libaio1 \
       libnsl2 \
       libpq-dev \
       openjdk-17-jre-headless \
       postgresql-client \
       unzip \
    && rm -rf /var/lib/apt/lists/*

# Fail closed: external binary/JAR downloads must be checksum-pinned by CI/local builders.
RUN for name in DBSCHEMA_SHA256 ORACLE_IC_SHA256 POSTGRES_JDBC_SHA256 ORACLE_JDBC_SHA256 CLOUD_SQL_PROXY_SHA256; do \
      value="${!name:-}"; \
      if [[ -z "${value}" ]]; then echo "missing required build arg: ${name}" >&2; exit 1; fi; \
    done

# Oracle Instant Client is needed because data-tool enables python-oracledb thick mode.
RUN mkdir -p /opt/oracle \
    && curl -fsSL "${ORACLE_IC_URL}" -o "/tmp/${ORACLE_IC_ZIP}" \
    && echo "${ORACLE_IC_SHA256}  /tmp/${ORACLE_IC_ZIP}" | sha256sum -c - \
    && unzip -q "/tmp/${ORACLE_IC_ZIP}" -d /opt/oracle \
    && rm -f "/tmp/${ORACLE_IC_ZIP}" \
    && test -d "${ORACLE_HOME}"

# DbSchemaCLI is included in the standard DbSchema kit and is used through the free CLI path.
# The OCP job does not require or consume a DbSchema license key.
RUN mkdir -p /opt/dbschema \
    && curl -fsSL "${DBSCHEMA_URL}" -o /tmp/dbschema.tar.gz \
    && echo "${DBSCHEMA_SHA256}  /tmp/dbschema.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/dbschema.tar.gz -C /opt/dbschema --strip-components=1 \
    && rm -f /tmp/dbschema.tar.gz \
    && dbschema_cli="$(find /opt/dbschema -type f -name dbschemacli | head -n 1)" \
    && test -n "${dbschema_cli}" \
    && chmod +x "${dbschema_cli}" \
    && ln -sf "${dbschema_cli}" /usr/local/bin/dbschemacli

# JDBC drivers are copied into ~/.DbSchema/drivers at runtime so DbSchemaCLI can resolve them
# even when it cannot download drivers in-cluster.
RUN mkdir -p /opt/jdbc/PostgreSql /opt/jdbc/Oracle \
    && curl -fsSL "https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar" \
       -o "/opt/jdbc/PostgreSql/postgresql-${POSTGRES_JDBC_VERSION}.jar" \
    && echo "${POSTGRES_JDBC_SHA256}  /opt/jdbc/PostgreSql/postgresql-${POSTGRES_JDBC_VERSION}.jar" | sha256sum -c - \
    && curl -fsSL "https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc11/${ORACLE_JDBC_VERSION}/ojdbc11-${ORACLE_JDBC_VERSION}.jar" \
       -o "/opt/jdbc/Oracle/ojdbc11-${ORACLE_JDBC_VERSION}.jar" \
    && echo "${ORACLE_JDBC_SHA256}  /opt/jdbc/Oracle/ojdbc11-${ORACLE_JDBC_VERSION}.jar" | sha256sum -c -

RUN curl -fsSL "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v${CLOUD_SQL_PROXY_VERSION}/cloud-sql-proxy.linux.amd64" \
      -o /usr/local/bin/cloud-sql-proxy \
    && echo "${CLOUD_SQL_PROXY_SHA256}  /usr/local/bin/cloud-sql-proxy" | sha256sum -c - \
    && chmod +x /usr/local/bin/cloud-sql-proxy

WORKDIR /opt/app-root

COPY data-tool/requirements.txt /tmp/data-tool-requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/data-tool-requirements.txt \
    && rm -f /tmp/data-tool-requirements.txt

# Match data-tool/Makefile install runtime imports: requirements.txt plus legal_api,
# registry_schemas, and sql-versioning. Install local LEAR packages without their
# transitive deps because requirements.txt owns the compatible runtime set.
COPY legal-api/ /opt/app-root/legal-api/
COPY python/common/sql-versioning/ /opt/app-root/python/common/sql-versioning/
RUN python -m pip install --no-cache-dir --no-deps --ignore-requires-python /opt/app-root/legal-api \
    && python -m pip install --no-cache-dir --no-deps /opt/app-root/python/common/sql-versioning \
    && python -m pip install --no-cache-dir --no-deps "git+https://github.com/bcgov/business-schemas.git@2.16.1#egg=registry_schemas"

COPY data-tool/ /opt/app-root/data-tool/
COPY jobs/colin-extract-delta/run.sh /opt/app-root/run.sh
COPY jobs/colin-extract-delta/README.md /opt/app-root/job-README.md

RUN mkdir -p /opt/app-root/data /opt/app-root/.DbSchema/cli \
    && chmod +x /opt/app-root/run.sh \
    && chgrp -R 0 /opt/app-root /opt/dbschema /opt/jdbc /opt/oracle \
    && chmod -R g=u /opt/app-root /opt/dbschema /opt/jdbc /opt/oracle

USER 1001

CMD ["/opt/app-root/run.sh"]
