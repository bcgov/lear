# quay.io is where jupyter docker-stacks publishes now (Docker Hub's jupyter/* froze in 2023 at python 3.9);
# legal_api requires >=3.13,<3.14 so pin the python-3.13 tag rather than latest
FROM quay.io/jupyter/scipy-notebook:python-3.13

ENV DEBIAN_FRONTEND=noninteractive

ARG NB_USER="jovyan"
ARG NB_UID="1000"
ARG NB_GID="100"

USER root

ENV DEBIAN_FRONTEND=dialog
USER ${NB_UID}
WORKDIR "${HOME}"
