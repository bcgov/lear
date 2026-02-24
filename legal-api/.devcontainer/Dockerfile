FROM mcr.microsoft.com/devcontainers/python:3.9-bullseye


RUN \
    rm -f /etc/apt/sources.list.d/yarn.list && \
    apt update && apt install bash-completion postgresql-client -y && \
    pip install --upgrade pip && \
    pip install pre-commit poetry && \
    poetry config virtualenvs.in-project true

RUN \
    pip install ruff

RUN  \
    echo >> /home/vscode/.bashrc && \
    # add completions to bashrc
    # see how ubuntu does it for reference:
    # https://git.launchpad.net/ubuntu/+source/base-files/tree/share/dot.bashrc
    # https://stackoverflow.com/a/68566555
    echo 'if [ -f /etc/bash_completion ] && ! shopt -oq posix; then' >> /home/vscode/.bashrc && \
    echo '    . /etc/bash_completion' >> /home/vscode/.bashrc && \
    echo 'fi' >> /home/vscode/.bashrc && \
    echo >> /home/vscode/.bashrc && \
    echo '. <(poetry completions)' >> /home/vscode/.bashrc
