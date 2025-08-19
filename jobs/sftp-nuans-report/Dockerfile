# Use the official Python 3.13 slim image with explicit SHA256 verification
FROM python:3.13-slim

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"

ENV VCS_REF=${VCS_REF}
ENV BUILD_DATE=${BUILD_DATE}
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/opt/app-root/src

# Configure Jupyter to use user-writable paths
ENV JUPYTER_CONFIG_DIR=/opt/app-root/.jupyter
ENV JUPYTER_DATA_DIR=/opt/app-root/.local/share/jupyter
ENV JUPYTER_RUNTIME_DIR=/opt/app-root/.local/share/jupyter/runtime

LABEL org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.build-date=${BUILD_DATE}

# Create directories with proper permissions
RUN mkdir -p /opt/app-root && \
    chmod 755 /opt/app-root && \
    mkdir -p /opt/app-root/data && \
    chmod 777 /opt/app-root/data && \
    mkdir -p ${JUPYTER_DATA_DIR} && \
    chmod -R 777 /opt/app-root/.local

WORKDIR /opt/app-root

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip==25.1.1 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

USER 1001

EXPOSE 8080

CMD ["python", "/opt/app-root/sftpnuans.py"]