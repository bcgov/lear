FROM postgres:12
COPY tracker_db.sql /docker-entrypoint-initdb.d/
EXPOSE 5432
RUN apt update
RUN apt install sudo
