FROM abiosoft/caddy

WORKDIR /etc/

COPY ./CaddyFile .

EXPOSE 2015

WORKDIR /srv

ENTRYPOINT ["/bin/parent", "caddy"]
CMD ["--conf", "/etc/CaddyFile", "--log", "stdout", "--agree=$ACME_AGREE"]
