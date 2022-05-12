FROM jupyter/scipy-notebook:latest

ENV DEBIAN_FRONTEND=noninteractive

ARG NB_USER="jovyan"
ARG NB_UID="1000"
ARG NB_GID="100"

USER root

ENV DEBIAN_FRONTEND=dialog
USER ${NB_UID}
WORKDIR "${HOME}"
