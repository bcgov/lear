# Base image
FROM python:3.7

# Update installation utilites and packages
RUN apt-get update

# Set working directory
RUN mkdir /opt/server
WORKDIR /opt/server

# Add and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add rest of files
COPY . .

# Run server
EXPOSE 5000
CMD python manage.py run -h 0.0.0.0