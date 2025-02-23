gunicorn --log-level=debug --access-logfile=- --error-logfile=- -w 4 -b :8000 app:app --chdir /home/site/wwwroot

