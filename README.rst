This is the django project for the founderdating.com website.

Instructions for install::

    $ virtualenv fd-env
    $ cd fd-env
    $ source bin/activate
    (fd-env)$ git clone git@github.com:jazkarta/founderdating.git
    (fd-env)$ pip install -r founderdating/requirements.pip
    (fd-env)$ cd founderdating
    (fd-env)$ python manage.py syncdb
    (fd-env)$ python manage.py migrate
    (fd-env)$ python manage.py collectstatic -l
    (fd-env)$ python manage.py runserver