#!/usr/bin/env python
#   Copyright [2013] [M. David Allen]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# Foo!
"""@author mda"""
from setuptools import setup, find_packages
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

setup(name='dataidentity',
      version='0.1',
      author='Moxious',
      author_email='moxious@oldhat.org',
      url='https://github.com/moxious/dataidentity',
      packages=find_packages(),
      include_package_data=True,
      description="File Identity Tool",
      install_requires=['Django>=1.4', 'python-magic', 
                        'extractor', 'defusedxml', 'PIL',
                        'django-multiuploader',
                        # Upcoming version 0.2.5 fixes a template bug
                        #'django-multiuploader>=0.2.5',
                        'djangorestframework', 'CloudMade'],
     )
