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
import files.downloader as downloader
import os
import files.analysis

def process(f): return processFile(f)

def NOTIFY_STATUS(callback, code):
    if callback is None or not hasattr(callback, '__call__'): return
    try:
        callback(code)
    except Exception, err:
        template = "{0} Arguments:\n{1!r}"
        message = template.format(type(err).__name__, err.args)         
        print("Failed to use callback: %s" % message)        

def processURL(url, statusCallback=None):
    dl = downloader.Downloader(allowRedirects=False)
    
    NOTIFY_STATUS(statusCallback, SubmissionQueue.FETCHING)
    tmpfile, metadata, contentType = dl.download(url)
    
    try:
        NOTIFY_STATUS(statusCallback, SubmissionQueue.ANALYZING)
        result = processFile(tmpfile, url, contentType)
        
        NOTIFY_STATUS(statusCallback, SubmissionQueue.FINALIZE)
    
        for index, tup in enumerate(metadata):        
            # print("Adding HTTP metadata %s => %s" % (tuple[0], tuple[1]))
            result.fileModel.addMetadata(tup[0], tup[1])
        return result
    finally:
        # Make sure to always remove the tempfile.  Leaving them littering
        # the /tmp directory is not a good thing.
        try: os.remove(tmpfile)
        except Exception, e:
            print("Failed to remove tmpfile %s: %s" % (tmpfile, e))
    

"""Process a file found at full path f.  If a location is specified,
that location will be used for the name instead of the local filename."""
def processFile(f, location=None, mimeType=None, statusCallback=None):
    if not os.path.exists(f):
        print("File %s doesn't exist." % f)
        return None

    if os.path.islink(f):
        print("Skipping %s because it is a link." % f)
        return None

    if not os.path.isfile(f):
        print("Skipping %s because it isn't a file." % f)
        return None

    path = os.path.abspath(f)

    # Get the right class to use to analyze this.
    if location is not None:
        analysisFactoryClass = files.analysis.get_appropriate_factory(location, mimeType)
    else: 
        analysisFactoryClass = files.analysis.get_appropriate_factory(path, mimeType)

    # Create the analysis factory, run the analysis.
    
    print "Analyzing %s with %s" % (f, analysisFactoryClass)
    af = analysisFactoryClass(f, None, location, True)    
    af.analyze()
    
    if af:
        print("FILE %s size %d MD5 = %s" % (path, af.fileModel.size, 
                                            af.fileModel.md5))
    return af
