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
from files.models import SubmissionQueue
from django.db.models import Q
import time
import datetime
from django.utils import timezone
import files.processing.process as process

"""The amount of time between analyses of a certain file.  If a file
is submitted that we've already analyzed, and less than this amount
of time has passed, then it won't be reanalyzed."""
REANALYZE_EXISTING_FILE_TIMEOUT = datetime.timedelta(seconds=1)

def flagStarted(item):
    item.status = SubmissionQueue.STARTED
    item.save()

def flagFinished(item):
    item.status = SubmissionQueue.FINISHED
    item.finished = True
    item.save()

def flagFailed(item):
    item.status = SubmissionQueue.FAILED
    item.finished = True
    item.save()

"""Consumes and processes one item from the submission queue."""
def consumeItem(item):
    try:        
        if item.finished or item.status != SubmissionQueue.NOT_STARTED:
            raise "Will not process started or finished item."
        
        flagStarted(item)
        print("Consuming %s" % item)
        
        # reanalyzeTimeout = timezone.localtime(timezone.now()) - REANALYZE_EXISTING_FILE_TIMEOUT

        def callback(statusCode):
            item.status = statusCode
            item.save()

        analysisFactory = process.processURL(item.location, callback)
        
        if analysisFactory is not None and analysisFactory.fileModel is not None:
            flagFinished(item)
        else:
            flagFailed(item)
        
    except Exception, err:
        flagFailed(item)
        template = "{0} Arguments:\n{1!r}"
        message = template.format(type(err).__name__, err.args)         
        print("Failed to consume %s: %s" % (item, message))

"""Check and see if the queue contains items suitable for processing.  If so, 
return a manager containing those items.  Otherwise return false."""
def itemsAvailable():    
    mgr = SubmissionQueue.objects.all().filter(finished=False).filter(status=SubmissionQueue.NOT_STARTED).order_by("submitted")    
    if mgr.exists(): return mgr
    return False

if __name__ == '__main__':
    while True:
        mgr = itemsAvailable()
        if mgr == False:
            print "Empty queue.  Sleep."
            time.sleep(5)
            continue
        else:
            # Here's where we would deal with multiple threads, but we're not doing that now.
            consumeItem(mgr[0])