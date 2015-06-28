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

import datetime

from django.core.paginator import Page, Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, render_to_response
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.core.context_processors import csrf
from django.utils import timezone
from django.db.models import Q

from rest_framework.renderers import JSONRenderer

from files.serializer import FileModelSerializer
from files.models import File, FileName, FileMetadata, SubmissionQueue
from files.forms import PostFileForm

import files.processing.process as process
from multiuploader.forms import MultiUploadForm

MAX_RESULTS = 100

"""The amount of time between analyses of a certain file.  If a file
is submitted that we've already analyzed, and less than this amount
of time has passed, then it won't be reanalyzed."""
REANALYZE_EXISTING_FILE_TIMEOUT = datetime.timedelta(seconds=1)

"""Wraps HttpResponse and provides a JSON-specific response"""
class JSONResponse(HttpResponse):
    """An HTTPResponse that renders its content into JSON"""
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data, renderer_context={"indent":2})
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

"""Get the right page out of a paginator object.
@param mgr: a query results manager from a django model
@param maxPerPage: an integer indicating maximum results per page
@param pageNo: a page number submitted by the user.  None is OK, you'll get the first page.  Page indexes out of bounds
will result in the last page.
"""
def getPage(mgr, maxPerPage, pageNo):
    paginator = Paginator(mgr, maxPerPage)
    
    try:
        # Try to get the page the user requested.
        objs = paginator.page(pageNo)
    except PageNotAnInteger:
        # This happens when the page number submitted via the web request is bogus.
        objs = paginator.page(1)
    except EmptyPage:
        # If there are 10 pages, and you ask for page 200, you'll get page 10.
        objs = paginator.page(paginator.num_pages)
    
    return objs

"""Spits out a form useful for uploading multiple files at a time"""
@csrf_exempt
def uploadForm(request):
    context = { 'uploadForm' : MultiUploadForm() }
    context.update(csrf(request))
    return render_to_response("uploadForm.html", context)

def queue(request):
    mgr = SubmissionQueue.objects.all().filter(finished=False).order_by("submitted")
    qObjects = getPage(mgr, 75, request.GET.get('page'))
    
    return render(request, "queue.html", { "submissions" : qObjects })

"""Returns a list of objects with a given metadata key/value"""
def metadataLookup(request, key, value):
    try:     results = int(request.GET['results'])
    except:  results = 20
    if results <= 0 or results > MAX_RESULTS: results = 20

    if key is None or key == '':
        return HttpResponseBadRequest("You must specify a key")
    if value is None or value == '':
        return HttpResponseBadRequest("You must specify a value")

    print "Looking up object by key=%s val=%s" % (key, value)
    mgr = File.objects.all().filter(metadata__key=key, metadata__value=value).order_by("-analysisDate")
    # mdItems = FileMetadata.objects.all().filter(key=key).filter(value=value).order_by("-basefile__analysisDate")[:results]
    # fileObjects = []
    # for mdItem in mdItems:
    #     fileObjects.append(mdItem.basefile)

    fileObjects = getPage(mgr, 20, request.GET.get('page'))
    return appropriate_response(request, fileObjects)

"""Checks the HTTP-Accept header for which content type the client is requesting, 
and returns the right response for that client. Alternatively, check whether there
is a GET parameter called "format" that equals json or html.   Default is HTML if
a determination cannot be made.  
Currently limited to HTML and JSON"""
def appropriate_response(request, data):
    try:
        wantsJSON = False
        wantsJSON = request.META['HTTP_ACCEPT'].find("application/json") != -1
        wantsJSON = wantsJSON or ("json" in request.GET)
                
        if request.GET.has_key("format") and request.GET.get("format")== 'json':
            wantsJSON = True                    
    except Exception, err:
        print("Couldn't determine content type wanted: %s" % err)
        wantsJSON = False

    # print "Objects %s, wantsJSON=%s" % (data, wantsJSON)

    # print "Data class %s %s" % (data, data.__class__)
    if wantsJSON:        
        if data.__class__ == Page:
            arr = []
            for item in data: arr.append(item)
            serializer = FileModelSerializer(arr)
        else: serializer = FileModelSerializer(data)
        return JSONResponse(serializer.data)
    else:
        # Sometimes we'll be given a single item, other times we'll be
        # given an iterable set.  In either case, the template expects
        # a set, so convert single items into a set.
        files = None
        try: 
            if data.__len__() > 0:
                files = data        
            else: files = []
        except AttributeError:
            files = [data]
            
        return render(request, "file.html", { "files" : files })

"""Return a list of the top N files that match a given filename 
"""
def filename(request, filename):
    encoded = filename

    # Find files that contain that snippet of filename
    # print("FINDING FILENAMES: '%s'" % encoded)    
    mgr = File.objects.all().filter(names__location__contains=encoded).order_by('-analysisDate')
    
    fileObjects = getPage(mgr, 20, request.GET.get('page'))
    return appropriate_response(request, fileObjects)

def getFilesBySize(request, sizeBytes):
    size_int = -1
    try: size_int = int(sizeBytes)
    except: return HttpResponseBadRequest("Size must be an integer")
    
    if size_int <= 0: return HttpResponseBadRequest("Size must be positive");
    
    mgr = File.objects.all().filter(size=size_int).order_by("-analysisDate")

    fileObjects = getPage(mgr, 20, request.GET.get('page'))
    return appropriate_response(request, fileObjects)

"""Get a single file by its hash code; can be md5, sha1, or crc32"""
def getSingleFile(request, hash_id):
    if hash_id.__len__() == 32:
        f = get_object_or_404(File, md5=hash_id.lower())
    elif hash_id.__len__() == 40:
        f = get_object_or_404(File, sha1=hash_id.lower())
    elif hash_id.__len__() == 8:
        f = get_object_or_404(File, crc32=hash_id.lower())
    else:
        raise Http404

    return appropriate_response(request, f)

"""Basic index HTML"""
def index(request):
    try:    results = int(request.GET['results'])
    except: results = 10
    if results <= 0 or results > MAX_RESULTS: results = 20
    
    latest = File.objects.all().order_by("-analysisDate")[:results]
    
    fileObjs = getPage(latest, results, request.GET.get('page'))
    return appropriate_response(request, fileObjs)

"""Get the latest objects.  Can be passed a "results" GET parameter to specify
how many"""
def latest(request):
    try:     results = int(request.GET['results'])
    except:  results = 20        
    if results <= 0 or results > MAX_RESULTS: results = 20
    
    latest = File.objects.all().order_by("-analysisDate")[:results]
    serializer = FileModelSerializer(latest)
    return JSONResponse(serializer.data)

"""Takes a URL and performs analysis on it; returns JSON consisting of the 
analysis results. 
@param url: the URL to analyze
"""
@csrf_exempt
def analyze(request):
    try: url = request.POST['url']
    except: 
        try: url = request.GET['url']
        except: return HttpResponseBadRequest("You must specify a url")

    try: URLValidator()(url)
    except ValidationError, e:
        print e
        return HttpResponseBadRequest("Invalid url %s (%s)" % (
                str(url), str(e)))

    reanalyzeTimeout = timezone.localtime(timezone.now()) - REANALYZE_EXISTING_FILE_TIMEOUT

    # See if there are any filenames with the same URL, that have been
    # analyzed more recently than the timeout.  If there are, then just
    # return the first one and don't do analysis.
    names = FileName.objects.all().filter(location=url).filter(basefile__analysisDate__gt=reanalyzeTimeout).order_by('-basefile__analysisDate')

    if len(names) > 0:
        print "Found previously analyzed object."
        f = names[0].basefile
        serializer = FileModelSerializer(f)
        return JSONResponse(serializer.data)

    # See if the item is already in the queue awaiting processing.  If it is, 
    # then just forward to the queue page, and don't do anything since it's already
    # on our list to get to.
    #
    # @TODO: this doesn't yet support re-analysis of old URLs that haven't been 
    # analyzed in a long time.    
    qItems = SubmissionQueue.objects.all().filter(location=url).filter(finished=False)
    if qItems.exists():
        return JSONResponse({"message" : "Already in processing queue"})
    else:
        sqi = SubmissionQueue(location=url)
        sqi.save()
        return JSONResponse({"message" : "Added to queue"})

    # Dead code for now. old stuff.
    try:
        analysisFactory = process.processURL(url)
        serializer = FileModelSerializer(analysisFactory.fileModel)
        return JSONResponse(serializer.data)
    except Exception, e:
        return JSONResponse({"error" : str(e) })
      
def stats(request):
    dict = {}
    
    dict['files'] = File.objects.count()
    dict['names'] = FileName.objects.count()
    dict['metadata'] = FileMetadata.objects.count()
    
    return JSONResponse(dict)

