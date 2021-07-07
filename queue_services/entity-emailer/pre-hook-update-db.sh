#! /bin/sh

cd /opt/app-root
echo 'ensure database is created'
python pre_hook_create_database.py

echo 'starting upgrade'
python manage.py db upgrade
