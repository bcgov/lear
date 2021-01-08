FROM python:3.8.5-buster
USER root

# Create working directory
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
RUN mkdir /opt/app-root/data && chmod 777 /opt/app-root/data
WORKDIR /opt/app-root

# Install the requirements
COPY ./requirements.txt .

#RUN pip install --upgrade pip
RUN pip install pip==20.3.3
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER 1001

# Set Python path
ENV PYTHONPATH=/opt/app-root/src

EXPOSE 8080

CMD [ "python", "/opt/app-root/notebookreport.py" ]
