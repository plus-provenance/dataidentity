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

from django.conf.urls import patterns, url, include

from files import views

urlpatterns = patterns('', 
    url(r'^processUploads/', include('multiuploader.urls')),
    url(r'uploadFiles/', views.uploadForm, name='upload'),
    url(r'^hash/(?P<hash_id>.+)$', views.getSingleFile, name='singleFile'),
    url(r'^size/(?P<sizeBytes>[0-9]+)$', views.getFilesBySize, name='filesBySize'),
    url(r'^filename/(?P<filename>.+)$', views.filename, name='filename'),
    url(r'^files/(?P<key>[^/]+)/(?P<value>.+)$', 
        views.metadataLookup, name='metadata lookup'),
    url(r'^queue/?$', views.queue, name='queue'), 
    url(r'^analyze$', views.analyze, name='analyze'),
    url(r'^new$', views.latest, name='latest'),
    url(r'^stats$', views.stats, name='stats'),
    url(r'^/?$', views.index, name='index'),
)
