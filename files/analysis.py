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
from zipfile import ZipFile, is_zipfile

import os
import hashlib
import mimetypes
import subprocess
import magic
from defusedxml import minidom, EntitiesForbidden, DTDForbidden
from files.models import *
import sys, traceback
from ctypes import cast, c_char_p
import struct
import tarfile 
import tempfile

EXTRACTOR_ENABLED = False

try:
    import extractor
    EXTRACTOR_ENABLED = True
except OSError:
    EXTRACTOR_ENABLED = False

if EXTRACTOR_ENABLED: xtractor = extractor.Extractor()
else: xtractor = None

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

class AnalysisFactory:
    """Create an object to analyze a file or input stream.
    @param filename: if provided, the filename to open and analyze.  
    @param stream: if provided, the filename will be ignored and the provided 
    file handle will be analyzed instead.   If you provide this stream, it will be read
    and closed.
    @param location: if provided, the location will be used as the name/location of the file.
    @param redoAnalysis: if true, analysis will take place even if the file has already been 
    analyzed.  If false, if a previous analysis has been performed that will be used."""   
    def __init__(self, filename=None, stream=None, location=None, redoAnalysis=False):        
        self.redoAnalysis = redoAnalysis        
        self.firstAnalysis = True        
        self.filename = filename
        self.fh = stream
        self.filemagic = None
        self.deleteFileOnCleanup = False
        
        """An array of two-item tuples; key/value metadata pairs."""
        self.metadata = []
        
        if location is None: self.location = filename
        else: self.location = location
             
        if location is None and filename is None:
            raise Exception, "If processing a stream, you must provide a location"
                
        if filename is not None and stream is not None:
            raise Exception, "You may only specify one of filename, stream"
        
        if filename is not None:
            self.fh = open(self.filename, "r")        

    def analyze(self):        
        self.getOrCreateFileModel()
        self.getOrCreateFileNameModel()
        self.buildMetadata()        
        self.writeMetadata()
        self.cleanup()
        return True

    def getOrCreateFileNameModel(self):
        if self.fileModel is None: raise "File model hasn't been created"

        objects = FileName.objects.all().filter(
            location=self.location).filter(
            basefile=self.fileModel)
        if len(objects) > 0:
            self.fileNameModel = objects[0]
        else:
            self.fileNameModel = FileName(basefile=self.fileModel, 
                                          location=self.location)
            self.fileNameModel.save()
        return self.fileNameModel

    def getOrCreateFileModel(self):
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        crc32 = None
        
        import zlib
        import binascii
        import struct
    
        firstBlock = True
        
        # In some cases we'll be given a stream.
        # Some analysis tools will only work well on files, 
        # which support seek().  So if we're given a stream,
        # while we're hashing it we'll be writing it to a temp
        # file so that we can use other tools on it subsequently.        
        if self.filename is None:
            (blah, self.filename) = tempfile.mkstemp()#[1]
            os.close(blah)
            self.writehandle = open(self.filename, "wb")
            self.deleteFileOnCleanup = True   
        else: self.writehandle = None
        
        x = 1
        totalRead = 0
        while x > 0:
            buf = self.fh.read(1024 * 64)
            
            if self.writehandle is not None: self.writehandle.write(buf)
            
            # Check the file magic for the first block.
            if firstBlock:                
                self.runExtractorOnBuffer(buf, buf.__len__())
                self.filemagic = magic.from_buffer(buf)
                # print("FILEMAGIC:  %s" % self.filemagic)
                self.metadata.append(("filemagic", self.filemagic))                
                firstBlock = False
            
            md5.update(buf)
            sha1.update(buf)
            
            if crc32 is None: crc32 = zlib.crc32(buf)
            else: crc32 = zlib.crc32(buf, crc32)
            
            x = buf.__len__()
            totalRead = totalRead + x

        qClose(self.fh)        
        if self.writehandle is not None: self.writehandle.close()

        md5sum = md5.hexdigest().lower()
        sha1sum = sha1.hexdigest().lower()
        
        crcbin = struct.pack('!l', crc32)
        crc32sum = binascii.hexlify(crcbin).lower()
    
        if self.filename is not None:
            fullPath = os.path.abspath(self.filename)
            statinfo = os.stat(fullPath)
            size = statinfo.st_size
        else:
            size = totalRead

        try:
            self.fileModel = File.objects.get(md5=md5sum)
            self.firstAnalysis = False
        except File.DoesNotExist:
            self.fileModel = File(md5=md5sum, sha1=sha1sum, 
                                  crc32=crc32sum, size=size)
            self.fileModel.save()
            self.firstAnalysis = True

        return self.fileModel

    def buildMetadata(self):
        print("Building base metadata for %s..." % self.filename)
        pass

    '''Writes FileMetadata for the object 
    @return: True if data was written, False otherwise'''
    def writeMetadata(self):        
        if self.firstAnalysis is False and self.redoAnalysis is False:
            print "Skipping metadata write (%s, %s)" % (self.firstAnalysis, self.redoAnalysis)
            return False
                
        # Delete all previous metadata before writing new.
        # The file hasn't changed (same hash) but metadata extraction may have
        # improved and we don't want the old data around.        
        if self.firstAnalysis is False:
            print("Deleting prior  metadata for file...");
            FileMetadata.objects.all().filter(basefile=self.fileModel).delete()
        
        sequenceNumber = 0
        for idx, tup in enumerate(self.metadata):
            # print "WRITING METADATA TUPLE: %s" % str(tup)
            if tup[0] is None or tup[1] is None:
                print("Error on bad metadata tuple %s => %s: skipping" % (tup[0], tup[1]))
                continue 
            # print("Write MD: %s => %s" % (tuple[0], tuple[1]))
            self.fileModel.addMetadata(tup[0], tup[1], sequenceNumber)
            sequenceNumber = sequenceNumber + 1

        return True
    
    """Performs cleanup actions after an analysis, for example, deleting temp files."""
    def cleanup(self):
        qClose(self.writehandle)
        qClose(self.fh)
                
        if self.deleteFileOnCleanup:
            os.remove(self.filename)
                        
        return True

    """Calls the file utility on the file and returns a brief description"""
    def getFileMagic(self):
        if self.filemagic is not None:
            return self.filemagic
        else:
            if self.filename is None:
                raise Exception, "Filemagic was missing from stream"
                        
            pipe = subprocess.Popen(["/usr/bin/file", "-b", self.filename],
                                  stdout=subprocess.PIPE, stderr=None, stdin=None,
                                  shell=False)
            readhandle = pipe.stdout
            line = readhandle.readline()
            if line is not None: line = line.strip()
            qClose(readhandle)
            pipe.wait()
            return line

    def runExtractorOnBuffer(self, buf, buflen=None):
        if not EXTRACTOR_ENABLED: return self.metadata
        
        if buflen is None: buflen = len(buf)

        def extract_metadata_keyvalues(xt, plugin, type, format, mime, data, datalen, obj=self):
            try:                
                if (format == extractor.EXTRACTOR_METAFORMAT_UTF8):
                    mstr = cast(data, c_char_p)
                    key = xtractor.keywordTypes()[type]
                    val = mstr.value
                    print "Got metadata item from BUF: %s => %s" % (key, val)
                    self.metadata.append((key, val))
            except Exception, errstr:
                print errstr                

        # Run the extraction...
        xtractor.extract(extract_metadata_keyvalues, None, None, buf, buflen)        
        return self.metadata        
        
    """Runs a metadata extraction tool, splits the result by splitDelimiter,
    returns a list of metadata items."""
    def runGenericExtractProgram(self, cmdParts, splitDelimiter=": "):
        items = []
        
        if self.filename is None:
            # print("Skipping generic extract program on %s; filename missing" % self.location)
            return items;
        
        try:
            pipe = subprocess.Popen(cmdParts, stdout=subprocess.PIPE,
                                  stderr=None, stdin=None, 
                                  shell=False)
            
            rh = pipe.stdout
            for line in rh.readlines():
                parts = line.split(splitDelimiter, 2)
                if len(parts) != 2: continue
                items.append((parts[0].strip(), parts[1].strip()))
            qClose(rh)            
            pipe.wait()
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)         
            print("Failed to run generic extract program %s: %s" % (cmdParts, message))

        return items

class ImageFile(AnalysisFactory):        
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)

        from PIL import Image
        from PIL.ExifTags import TAGS

        i = None
        success = True
        
        try:    
            i = Image.open(self.filename)
            
            self.metadata.append(("mode", str(i.mode)))
            self.metadata.append(("format", str(i.format)))
            self.metadata.append(("width", str(i.size[0])))
            self.metadata.append(("height", str(i.size[1])))
            if i.palette is not None:
                self.metadata.append(("palette", str(i.palette)))
                        
            info = i._getexif()
            
            if info is None: self.metadata.append(("EXIF", "None present"))
            else:
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
            
                    if decoded is not None and value is not None:
                        self.metadata.append((str(decoded), str(value)))            
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to extract image metadata from %s: %s" % (self.filename, message))
            success = False
        
        qClose(i)
        
        return success
        
class XMLFile(AnalysisFactory):
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)
        
        print("Doing XMLFile analysis...")
        try:
            if self.filename is not None:
                doc = minidom.parse(self.filename)
            else:
                self.fh.seek(0)
                doc = minidom.parse(self.fh)
            print("Got doc %s" % str(doc))
        except DTDForbidden:
            print("XML file defines DTD")
            self.metadata.append(("defines-dtd", "true"))
            return True
        except EntitiesForbidden:
            print("XML file defines entities")
            self.metadata.append(("defines-entities", "true"))
            return True                
        except Exception, err:
            template = "Failed to seek/open/parse XML: {0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print(message)
            return False 
        
        try:
            self.metadata.append(("root-element", doc.documentElement.tagName))
            for attrName in doc.documentElement.attributes.keys():
                # print("Appending XML metadata for %s" % attrName)
                self.metadata.append((attrName, doc.documentElement.getAttribute(attrName)))
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to extract tags from XML %s: %s" % (self.filename, message))
            return False 
            
        return True        
        
"""Performs analysis on PDF files.  Requires pdfinfo executable"""
class PDFFile(AnalysisFactory):
    def buildMetadata(self):        
        AnalysisFactory.buildMetadata(self)
        
        print("Doing PDF analysis...")
        more = self.runGenericExtractProgram(["/usr/bin/pdfinfo", 
                                              self.filename],
                                             ": ")
        for item in more: self.metadata.append(item)        
        return True
        
"""Performs ID3 tag extraction of files.  Requires id3tool"""
class ID3File(AnalysisFactory):
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)

        print "Doing ID3 analysis..."
        more = self.runGenericExtractProgram(["/usr/bin/id3tool", 
                                              self.filename], ": ")
        for item in more: self.metadata.append(item)
        return True

class ZIPFile(AnalysisFactory):
    def processNestedZipEntry(self, handle, zipInfo, containedBy):
        # NOTE NOTE NOTE
        # DO NOT DO RECURSIVE PROCESSING -- ONE LEVEL ONLY.
        # That means, use the generic analysis factory, not a specialized
        # form that may recursively descend, for security reasons.
        print("Processing nested zip entry %s" % zipInfo.filename)
                
        factory = get_appropriate_factory(zipInfo.filename)
        af = factory(filename=None, stream=handle, 
                             location=zipInfo.filename, redoAnalysis=False)
        af.analyze()
        af.fileModel.addRelationship("containedBy", containedBy)        
        
        # Add some metadata specific to the zipinfo
        if zipInfo.comment is not None and len(zipInfo.comment) > 0:
            af.fileModel.addMetadata("comment", zipInfo.comment)
                        
        af.fileModel.addMetadata("CRC", "%s" % zipInfo.CRC)
        
        return af.fileModel

    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)

        if not is_zipfile(self.filename):
            self.metadata.append(("Data format warning", "File cannot be processed as a ZIP file"))
            return True

        print "Doing ZIPFile analysis..."
                
        try:
            
            
            zf = ZipFile(self.filename, "r")
            for zipInfo in zf.infolist():
                handle = None
                
                try:                    
                    if zipInfo.filename.endswith('/'):
                        # Don't process directories
                        continue
                    
                    handle = zf.open(zipInfo, "r")
                    contained = self.processNestedZipEntry(handle, zipInfo,  
                                                           self.fileModel)
                    # Add some zip-specific metadata.
                    self.fileModel.addRelationship("contains", contained)
                except Exception, err:
                    template = "{0} Arguments:\n{1!r}"
                    message = template.format(type(err).__name__, err.args)
                    print("Failed to process zipfile item %s (%s): %s" % (zipInfo.orig_filename, self.filename, message))
                    traceback.print_exc(file=sys.stdout)
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))                                        
                finally:            
                    qClose(handle)
                        
            return True
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to process zipfile %s : %s" % (self.filename, message))
            traceback.print_exc(file=sys.stdout)
            return False
        finally:
            qClose(zf)

class JARFile(ZIPFile):   # NOTE!!!! Do not confuse ZIPFile with ZipFile    
    def buildMetadata(self):        
        ZIPFile.buildMetadata(self)
                
        if not is_zipfile(self.filename):
            self.metadata.append(("Data format warning", "File cannot be processed as a JAR file"))
            return True
                
        print "Doing JAR analysis..."

        try:
            zf = ZipFile(self.filename, "r")
            manifest = zf.open("META-INF/MANIFEST.MF", "r")
            
            try:
                for line in manifest.readlines():
                    # print "MANIFEST LINE %s" % line
                    parts = line.split(": ", 2)
                    if len(parts) == 2: 
                        #print "Appending JAR Metadata %s=%s" % (parts[0], parts[1])
                        self.metadata.append((parts[0].strip(), parts[1].strip()))
            finally:
                qClose(manifest)
                        
            return True
        except KeyError, err: 
            print("JARFile %s contained no manifest: %s" % (self.filename, err))
            return False
        except Exception, err:            
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to process jarfile %s : %s" % (self.filename, message))
            traceback.print_exc(file=sys.stdout)
            return False
        finally:
            qClose(zf)

class TARFile(AnalysisFactory):
    def processNestedTarEntry(self, handle, tarInfo, containedBy):
        # NOTE NOTE NOTE
        # DO NOT DO RECURSIVE PROCESSING -- ONE LEVEL ONLY.
        # That means, use the generic analysis factory, not a specialized
        # form that may recursively descend, for security reasons.
        print("Processing nested tar entry %s" % tarInfo.name)
        factory = get_appropriate_factory(tarInfo.name)        
        af = factory(filename=None, stream=handle, 
                     location=tarInfo.name, redoAnalysis=False)
        af.analyze()        
        af.fileModel.addRelationship("containedBy", containedBy)
        
        return af.fileModel    
    
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)

        print "Doing TARFile analysis..."
        try:
            tf = tarfile.open(self.filename, "r")
        
            if tf.posix: self.metadata.append(("tarformat", "USTAR_FORMAT"))
            else: self.metadata.append(("tarformat", "GNU_FORMAT"))

            handle = None
        
            for tarEntry in tf.getmembers():
                if not tarEntry.isfile(): continue
                handle = tf.extractfile(tarEntry)
                contained = self.processNestedTarEntry(handle, tarEntry, self.fileModel)
                
                qClose(handle)
                
                self.fileModel.addRelationship("contains", contained)
            return True
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to process tarfile %s : %s" % (self.filename, message))
            traceback.print_exc(file=sys.stdout)
            return False       
        finally:
            qClose(tf)

"""Helper function for YAML parser"""
def construct_ruby_object(loader, suffix, node):
    return loader.construct_yaml_map(node)

"""Helper function for YAML parser"""
def construct_ruby_sym(loader, node):
    return loader.construct_yaml_str(node)

class RubyGEM(TARFile):
    """Extracts special items from a gemspec as metadata"""
    def makeMetadataFromGemspec(self, spec):
        harvestFields = ['author', 'authors', 'name', 'platform', 'require_paths', 'rubygems_version', 'summary', 'version', 'license', 'licenses']
                
        def is_sequence(arg):
            return (not hasattr(arg, "strip") and
                    hasattr(arg, "__getitem__") or
                    hasattr(arg, "__iter__"))

        def qFlatten(seq):
            r = ""
            for i in seq:
                if isinstance(i, str): 
                    r = r + " " + i
            return r

        for field in harvestFields:
            if spec.has_key(field):
                val = spec[field]
                
                if not is_sequence(val):
                    self.metadata.append(("gem:%s" % field, str(val)))
                else:
                    self.metadata.append(("gem:%s" % field, qFlatten(val)))            

    def buildMetadata(self):
        TARFile.buildMetadata(self)

        try: 
            import yaml            
        except:
            print("Skipping GEM analysis of %s because YAML is not supported by this python" % self.filename)
            return
        
        try:
            import gzip
        except:
            print("Skipping GEM analysis of %s because GZip is not supported by this python" % self.filename)
            return        

        print "Doing GEM analysis..."
        try:
            tf = tarfile.open(self.filename, "r")
            
            for tarEntry in tf.getmembers():
                if not tarEntry.isfile(): continue
                if not tarEntry.name == 'metadata.gz': continue
                
                handle = tf.extractfile(tarEntry)
                gzipHandle = gzip.GzipFile(fileobj=handle)

                yaml.add_multi_constructor(u"!ruby/object:", construct_ruby_object)
                yaml.add_constructor(u"!ruby/sym", construct_ruby_sym)

                gemSpec = yaml.load(gzipHandle)
                print "FOUND GEMSPEC %s" % str(gemSpec)
                
                self.makeMetadataFromGemspec(gemSpec)
                
                qClose(gzipHandle)
                qClose(handle)
        finally:
            qClose(tf)

"""Extracts metadata from MS Office files.  
Requires OleFileIO-PL and oletools"""
class OfficeFile(ZIPFile):
    def buildMetadata(self):
        ZIPFile.buildMetadata(self)
        
        print "Doing Office Analysis..."
        extractList = { "docProps/core.xml" : [
                           'dc:title', 'dc:subject', 'dc:creator', 'cp:keywords', 
                           'dc:description', 'cp:lastModifiedBy', 'cp:revision',
                           'cp:lastPrinted', 'dcterms:created', 'dcterms:modified'                           
                        ],
                        "docProps/app.xml" : [
                           'Template', 'TotalTime', 'Words', 'Application',
                           'PresentationFormat', 'Paragraphs', 'Slides', 'Notes',
                           'HiddenSlides', 'MMClips', 'Company', 'AppVersion'
                        ]
                       }
                
        try:
            zf = ZipFile(self.filename)

            # For each of several XML files in the archive,
            # open them, extract a few fields, and add to the 
            # metadata list.            
            for extractFile in extractList.keys():
                f = zf.open(extractFile, "r")
                try:
                    xmldoc = minidom.parse(f)
                
                    extractFields = extractList[extractFile]
                    for extractField in extractFields:
                        itemlist = xmldoc.getElementsByTagName(extractField)
                        if len(itemlist) > 0:
                            try:  txt = itemlist[0].firstChild.nodeValue
                            except:  # node was empty
                                txt = ""
                        
                            self.metadata.append((extractField, txt))
                finally:            
                    qClose(f)
            return True
        except Exception, err:
            # Fall back to conservative method
            print("Failed processing office zipfile: %s" % str(err))
            traceback.print_exc(file=sys.stdout)
            return False
        finally:
            qClose(zf)

"""A dictionary mapping file extensions to the AnalysisFactory class you 
should use for analyzing a given file."""
ANALYSIS_MAPPINGS = {    
   # Office files
   ".doc" : OfficeFile, ".docx" : OfficeFile,
   ".xls" : OfficeFile, ".xlsx" : OfficeFile, 
   ".ppt" : OfficeFile, ".pptx" : OfficeFile,                   
   "application/msword": OfficeFile, 
   "application/vnd.openxmlformats-officedocument.wordprocessingml.document" : OfficeFile,
   "application/vnd.ms-powerpoint" : OfficeFile,
   "application/vnd.openxmlformats-officedocument.presentationml.presentation":OfficeFile,
   "application/vnd.ms-excel" : OfficeFile, 
   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": OfficeFile,
                      
   # Ruby stuff
   ".gem" : RubyGEM,
                      
   # JAR files
   ".jar" : JARFile,
   "application/java-archive" : JARFile,
   
   # Other java formats.
   ".war" : JARFile,
   ".ear" : JARFile,
                      
   # ZIP files
   ".zip"  : ZIPFile,
   "application/zip" : ZIPFile,
                      
   # PDF files
   ".pdf" : PDFFile,
   "application/pdf" : PDFFile,
                      
   # TAR files    
   ".tgz" : TARFile,  
   ".tar.gz" : TARFile,
   "application/x-tar" : TARFile,
   ".tar.bz2" : TARFile,
                      
   # Images
   ".gif" : ImageFile, ".jpg" : ImageFile,
   ".png" : ImageFile, ".xpm" : ImageFile,
   ".bpm" : ImageFile, 
   ".tiff" : ImageFile, 
   "image/tiff" : ImageFile,
   "image/gif" : ImageFile,
   "image/jpeg" : ImageFile,
   "image/png" : ImageFile,
   "image/x-xpixmap" :ImageFile,   
                      
   # XML
   ".xml" : XMLFile,  ".xslt" : XMLFile,
   ".xsd" : XMLFile,
   "application/xml" : XMLFile   
} # End ANALYSIS_MAPPINGS

"""For a given file or mime type, suggest a class that should be 
used for analyzing that file.
@param fileOrLocation: a full filename (or URL) of the file.
@param mimeType: if known, the MIME type without encoding of the file.
"""  
def get_appropriate_factory(fileOrLocation="", mimeType=None):   
    # Use the base class, which can process any file by default.
    analysisFactoryClass = AnalysisFactory
    
    if mimeType is None:
        (suggested, encoding) = mimetypes.guess_type(fileOrLocation)
        if suggested is not None: mimeType = suggested
    
    # If we can find a file extension that matches a mapping, use
    # that analyzer instead.
    if fileOrLocation != "":
        for key in ANALYSIS_MAPPINGS.keys():
            if fileOrLocation.endswith(key):
                analysisFactoryClass = ANALYSIS_MAPPINGS[key]
                break
    
    if mimeType is not None:
        if ANALYSIS_MAPPINGS.has_key(mimeType):
            return ANALYSIS_MAPPINGS[mimeType]
    
    print("Appropriate factory for FILE=%s MIME=%s => %s" % (
            fileOrLocation, mimeType, analysisFactoryClass))
    return analysisFactoryClass