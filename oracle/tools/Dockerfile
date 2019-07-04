FROM store/oracle/database-enterprise:12.2.0.1
USER root

RUN useradd -l -u 1003919999 -g 0 -G 0,54321,54322 learDev && \
    mkdir /import && \
    chmod -R 775 /import

COPY bin/uid_entrypoint /home/uid_entrypoint
COPY bin/dockerInit2.sh /home/oracle/setup/dockerInit2.sh
COPY bin/startupDB2.sh /home/oracle/setup/startupDB2.sh
COPY bin/shutDB2.sh /home/oracle/setup/shutDB2.sh
COPY bin/setupDB2.sh /home/oracle/setup/setupDB2.sh
COPY bin/configDB2.sh /home/oracle/setup/configDB2.sh
COPY bin/configDBora2.sh /home/oracle/setup/configDBora2.sh
COPY bin/untarDB2.sh /home/oracle/setup/untarDB2.sh
RUN \
   chown -R 1003919999 /ORCL && \
   chown -R 1003919999 /u01 && \
   chown -R 1003919999 /u02 && \
   chown -R 1003919999 /u03 && \
   chown -R 1003919999 /u04 && \
   chown -R 1003919999 /home && \
   chmod 775 /home/oracle/setup/dockerInit2.sh && \
   chmod 775 /home/oracle/setup/startupDB2.sh && \
   chmod 775 /home/oracle/setup/shutDB2.sh && \
   chmod 775 /home/oracle/setup/configDB2.sh && \
   chmod 775 /home/oracle/setup/configDBora2.sh && \
   chmod 775 /home/oracle/setup/untarDB2.sh && \
   chgrp -R 0 /ORCL && \
   chmod -R g=u /ORCL && \
   chgrp -R 0 /u01 && \
   chmod -R g=u /u01 && \
   chgrp -R 0 /u02 && \
   chmod -R g=u /u02 && \
   chgrp -R 0 /u03 && \
   chmod -R g=u /u03 && \
   chgrp -R 0 /u04 && \
   chmod -R g=u /u04 && \
   chgrp -R 0 /home && \
   chmod -R g=u /home && \
   chmod g=u /etc/passwd

USER 1003919999
ENTRYPOINT [ "/home/uid_entrypoint" ]
EXPOSE 1521:5500
ENTRYPOINT ["/home/oracle/setup/dockerInit2.sh"]
