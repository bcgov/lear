# platform=linux/amd64
FROM python:3.12.1-buster

ARG VCS_REF="missing"
ARG BUILD_DATE="missing"

ENV VCS_REF=${VCS_REF}
ENV BUILD_DATE=${BUILD_DATE}

LABEL org.label-schema.vcs-ref=${VCS_REF} \
    org.label-schema.build-date=${BUILD_DATE}

USER root

# Create working directory
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
RUN mkdir /opt/app-root/data && chmod 777 /opt/app-root/data
WORKDIR /opt/app-root

# Install the requirements
COPY ./pyproject.toml .
COPY ./poetry.lock .

#RUN pip install --upgrade pip
RUN poetry install

COPY . .

USER 1001

# Set Python path
ENV PYTHONPATH=/opt/app-root/src

EXPOSE 8080

CMD [ "python", "/opt/app-root/notebookreport.py" ]
