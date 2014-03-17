#!/bin/bash

python manage.py reset files
python files/hashcat.py test
