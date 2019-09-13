FROM registry.access.redhat.com/ubi8/nodejs-10

USER root
RUN mkdir /opt/app && chmod 755 /opt/app
WORKDIR /opt/app

COPY package*.json  ./

RUN npm ci

COPY . .

USER 1001
EXPOSE 8080
CMD [ "npm", "run", "serve" ]