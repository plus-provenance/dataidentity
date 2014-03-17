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
from files.models import * 
import glob
import time
import moxious.settings
from zipfile import ZipFile
import sys
import csv
import nsrl.OS
import nsrl.Product
import nsrl.Manufacturer
import nsrl.File
import os

LOOKUP = {}

# Disable debug to prevent query caching...
moxious.settings.DEBUG = False

def check_or_create_metadata(basefile, key, value, checkDBExists=True):
    lookup = "%s:%s:%s" % (basefile.md5, key, value)
    if LOOKUP.has_key(lookup): return None

    if checkDBExists:
        try:
            fm = FileMetadata.objects.get(basefile=basefile, key=key, value=value)
            return None
        except FileMetadata.DoesNotExist:
            pass        
        except Exception, errstr:
            print("Failed to do anything with metadata %s => %s (%s)" % (str(key), str(value), errstr))
            return None
        
    try:
        if len(key) > 255:
            print "WARNING:  Truncating metadata key %s" % key
            key = key[0:255]
        if len(value) > 255:
            print "WARNING: truncating metadata value %s" % value
            value = value[0:255]
            
        fm = FileMetadata(basefile=basefile, key=key, value=value)
        lookup = "%s:%s:%s" % (basefile.md5, key, value)
        LOOKUP[lookup] = True 
        return fm
    except:
        print("Failed to create metadata %s => %s" % (key, value))
        return None

def check_or_create_filename(basefile, name):
    try:
        name = name.decode("UTF-8", "strict")        
        fn = FileName(basefile=basefile, location=name)
        return fn
    except Exception, errstr:
        print("Failed to do anything with filename %s: %s" % (str(name), errstr))
        return None

def MASS_IMPORT(dir):    
    print("Examining %s..." % dir)
    if not os.path.exists(dir):
        print("Usage:  %s dirname (where dirname is a directory where NSRL files reside)" % __file__)
        sys.exit(1)
    
    NSRL_FILES = ["NSRLFile.txt", "NSRLProd.txt", 
                  "NSRLMfg.txt", "NSRLOS.txt", 
                  "hashes.txt"]
        
    nested = open(dir + "/NSRLOS.txt", "r")
    nsrl.OS.importFrom(nested)
    nested.close()
    
    nested = open(dir + "/NSRLProd.txt", "r")
    nsrl.Product.importFrom(nested)
    nested.close()

    nested = open(dir + "/NSRLMfg.txt", "r")
    nsrl.Manufacturer.importFrom(nested)
    nested.close()

    nested = sys.stdin
        
    x = 0
    startTime = time.mktime(time.localtime()) 
    incrTime = time.mktime(time.localtime())
    last_md5 = '' 
    last_file = None
    last_name = None
    
    TOTAL_RECORD_COUNT = 111011933
    
    files = []
    names = []
    metadata = []

    for nsrlfile in nsrl.File.FileIterator(nested):
        x = x + 1

        if nsrlfile.md5 == last_md5:
            diFile = last_file
        else: 
            # This is the first time sequentially in the file we've seen
            # this md5
            try:
                diFile = File.objects.get(md5=nsrlfile.md5)
            except File.DoesNotExist:
                diFile = File(md5=nsrlfile.md5, sha1=nsrlfile.sha1, 
                              crc32=nsrlfile.crc32, size=nsrlfile.size)
                files.append(diFile)
            last_file = diFile
            last_md5 = nsrlfile.md5
        
        if nsrlfile.name != last_name:           
            nm = check_or_create_filename(diFile, nsrlfile.name)
            if nm is not None: names.append(nm)
            last_name = nsrlfile.name

        # Don't check to see if it exists.  This runs the risk of possible
        # dups, but speeds import.
        checkDBExists = False
        
        # But if this is the first time we've seen 

        mditem = check_or_create_metadata(diFile, 'OS', str(nsrlfile.getOS()), checkDBExists)
        if mditem is not None: metadata.append(mditem)
        mditem = check_or_create_metadata(diFile, 'Product', str(nsrlfile.getProduct()), checkDBExists)
        if mditem is not None: metadata.append(mditem)
        
        if x % 12000 == 0:
            # print "Saving files..."
            File.objects.bulk_create(files)
            # print "Saving filenames..."
            FileName.objects.bulk_create(names)
            # print "Saving metadata..."
            FileMetadata.objects.bulk_create(metadata)
            
            elapsed = time.mktime(time.localtime()) - startTime
            incrElapsed = time.mktime(time.localtime()) - incrTime
            progress = ((x+0.0)/(TOTAL_RECORD_COUNT+0.0))*100
            print("%s records processed (%s pct); avg %s/sec this incr %s/sec" % (x, str(progress), str(x/elapsed), str(12000/incrElapsed)))
            incrTime = time.mktime(time.localtime())
            
            files = []
            names = []
            metadata = []
            LOOKUP = {}
        
    # nested.close()

if __name__ == "__main__":
    MASS_IMPORT(sys.argv[1])
