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
import urllib2
import urlparse
import os
import tempfile

class HeadRequest(urllib2.Request):
    def get_method(self):  
        return "HEAD"

class RedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)
        result.status = code
        raise Exception("Permanent Redirect: %s" % 301)

    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        result.status = code
        raise Exception("Temporary Redirect:  %s" % 302)

"""Gets the MIME type of a URL via a HEAD request before downloading."""
def getMimeType(url):
    response = urllib2.urlopen(HeadRequest(url))
    return response.info().getheader("Content-Type")

"""Given a download, saves the file locally and returns an absolute path 
to the file"""
class Downloader:
    def __init__(self, allowRedirects=False, maxSize=500*1024*1024):
        self.allowRedirects = allowRedirects
        self.maxSize = maxSize
        pass
 
    def validateURL(self, url):
        parseResult = urlparse.urlparse(url, scheme='http')
        if parseResult is None:  
            raise Exception, "Unrecognized URL %s" % url
        if (not parseResult.scheme 
            == 'http') and (not parseResult.scheme == 'https'):
            raise Exception, "Only HTTP/HTTPS urls are accepted."
        if parseResult.query != '':
            raise Exception, "URLs with query fragments are not accepted."
        
        if parseResult.password is not None:
            raise Exception, "URLs containing passwords are not accepted."

        return True

    """Downloads a specified URL.  Returns a file that contains the contents
    of the URL, and an array of 2-member metadata tuples that came from the
    HTTP transaction"""
    def download(self, url):
        # This method will throw an exception on an invalid URL.
        self.validateURL(url)

        parseResult = urlparse.urlparse(url)
        tmpFile = tempfile.mkstemp()[1]

        if not self.allowRedirects:
            opener = urllib2.build_opener(RedirectHandler)
            urllib2.install_opener(opener)

        response = urllib2.urlopen(HeadRequest(url))

        try:
            length = int(response.info().getheader("Content-Length"))
        except Exception:
            # Some servers don't provide this header, so you're just SOL
            print("Can't determine length of %s" % url)
            length = 1

        if length > self.maxSize:
            raise Exception, "URL is of size %d, which exceeds maximum %d" % (
                int(length), int(self.maxSize))

        metadata = []
        headers = ["Content-Type", "Content-MD5", "Date", "Last-Modified", "ETag"]

        for header in headers:
            try:
                val = response.info().getheader(header)
                if val is not None:                
                    metadata.append(("HTTP:"+str(header), str(val)))
            except: pass

        contentType = response.info().getheader("Content-Type")
        print("Response MIME type is %s" % contentType)
        u = urllib2.urlopen(url)
        f = open(tmpFile, "wb")
    
        # Read data and write to file.
        totalRead = 0
        block_sz = 8 * 1024
        while True:
            buffer = u.read(block_sz)
            totalRead = totalRead + block_sz
            if not buffer: break
            f.write(buffer)
            if totalRead > self.maxSize:
                f.close()
                os.remove(tmpFile)
                raise Exception, "Read past max size %d. File too large." % self.maxSize

        f.close()
        return tmpFile, metadata, contentType
