# platform=linux/amd64
FROM python:3.13-slim

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"

ENV VCS_REF=${VCS_REF}ß
ENV BUILD_DATE=${BUILD_DATE}

LABEL org.label-schema.vcs-ref=${VCS_REF} \
    org.label-schema.build-date=${BUILD_DATE}ß

USER root

# Create working directoryå
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
RUN mkdir /opt/app-root/data && chmod 777 /opt/app-root/data
WORKDIR /opt/app-root

# Install the requirements
COPY ./requirements.txt .

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

#RUN pip install --upgrade pip
RUN pip install pip==25.1.1
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER 1001

# Set Python path
ENV PYTHONPATH=/opt/app-root/src

EXPOSE 8080

CMD [ "python", "/opt/app-root/sftpnuans.py" ]
