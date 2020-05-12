# Base image
FROM python:3.7
USER root


# Create working directory
RUN mkdir /opt/app && chmod 755 /opt/app
WORKDIR /opt/app

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Add rest of files
COPY . .

USER 1001

# Run server
EXPOSE 5000

CMD ["flask", "run","--host", "0.0.0.0"]
