"""Utility method for closing handles.  We have handles from a bunch of different 
sources and APIs (regular files, TAR libraries, ZIP libraries, JARs, etc).  They all
have a close() method, but you can't necessarily assume that their close semantics are
the same.  This is meant as a catch-all force close method."""
def qClose(handle):
    if handle is not None:
        try: 
            handle.close();
            # print "Closed handle %s" % handle
        except Exception, e:
            # print "failed to close %s: %s" % (handle, e)
            pass
    return True

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except:
    print("Unable to support PIL and EXIF tag extensions: please install for better image file support.")

try:
    from zipfile import ZipFile, is_zipfile
except:
    print("Unable to support ZIP extensions: please install a python that supports zipfile")

try:
    import tarfile
except: 
    print("Unable to import tarfile: please install it for better TAR file support.")

try:
    from defusedxml import minidom, EntitiesForbidden, DTDForbidden
except:
    print("Unable to import defusedxml: please install it for better XML support.")

############### Find command-line utilities.... ###############################

from distutils.spawn import find_executable

FILE_UTIL = find_executable("file")
if FILE_UTIL == None:
    print("Can not find 'file' installed: basic metadata scanning disabled")

ID3TOOL = find_executable("id3tool")

if ID3TOOL == None:
    print("Can not find id3tool installed: ID3 tag scanning disabled.")

PDFINFO = find_executable("pdfinfo")

if PDFINFO == None:
    print("Can not find pdfinfo installed: PDF metadata scanning disabled.")

try:
    import extractor
    print "Got extractor"
    xtractor = extractor.Extractor()
    print "Created extractor"
except:
    print("Can not find python module 'extractor': some metadata extraction disabled.")
    xtractor = None

print("Extractor is %s" % str(xtractor))

"""A dictionary mapping file extensions to the AnalysisFactory class you 
should use for analyzing a given file."""
ANALYSIS_MAPPINGS = {}

def register_format(extension, constructor):
    ANALYSIS_MAPPINGS[extension] = constructor
    return ANALYSIS_MAPPINGS

