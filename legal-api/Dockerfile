FROM python:3.7
USER root


# Create working directory
RUN mkdir /opt/app && chmod 755 /opt/app
WORKDIR /opt/app


# Install the requirements
COPY ./requirements/prod.txt .
COPY ./requirements/dev.txt .
COPY ./requirements/repo-libraries.txt .

RUN pip install --no-cache-dir -r prod.txt
RUN pip install --no-cache-dir -r dev.txt
RUN pip install --no-cache-dir -r repo-libraries.txt

COPY . .
RUN pip install .

USER 1001

# Run the server
EXPOSE 5000

CMD ["flask", "run","--host", "0.0.0.0"]