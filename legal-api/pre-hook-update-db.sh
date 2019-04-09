#! /bin/sh
export LIBRARY_PATH=/opt/rh/httpd24/root/usr/lib64
export X_SCLS=rh-python35 httpd24
export LD_LIBRARY_PATH=/opt/rh/rh-python35/root/usr/lib64:/opt/rh/httpd24/root/usr/lib64
export PATH=/opt/app-root/bin:/opt/rh/rh-python35/root/usr/bin:/opt/rh/httpd24/root/usr/bin:/opt/rh/httpd24/root/usr/sbin:/opt/app-root/src/.local/bin/:/opt/app-root/src/bin:/opt/app-root/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'my_db'" | grep -q 1 || psql -U postgres -c "CREATE DATABASE my_db"

cd /opt/app-root/src
echo 'ensure database is created'
/opt/app-root/bin/python pre_hook_create_database.py

echo 'starting upgrade'
/opt/app-root/bin/python manage.py db upgrade
