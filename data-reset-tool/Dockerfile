# Base image
FROM python:3.7

# Update installation utilites and packages
RUN apt-get update

# Set working directory
RUN mkdir /opt/server
WORKDIR /opt/server

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Add rest of files
COPY . .

# Run server
EXPOSE 5000

CMD ["flask", "run","--host", "0.0.0.0"]
