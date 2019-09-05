FROM registry.access.redhat.com/ubi8/python-36
USER root


# Create working directory
RUN mkdir /opt/app && chmod 755 /opt/app
WORKDIR /opt/app

USER 1001
# Install the requirements
COPY ./requirements/prod.txt .
COPY ./requirements/dev.txt .
COPY ./requirements/repo-libraries.txt .

RUN pip install --no-cache-dir -r prod.txt
RUN pip install --no-cache-dir -r dev.txt
RUN pip install --no-cache-dir -r repo-libraries.txt

COPY . .

# Run the server
EXPOSE 5000
CMD [ "flask", "run","--host", "0.0.0.0"]