import subprocess, hashlib, os, magic, tempfile
from files.models import FileName, File, FileMetadata
from ctypes import cast, c_char_p
from files import filetype

class AnalysisFactory:
    """Create an object to analyze a file or input stream.
    @param filename: if provided, the filename to open and analyze.  
    @param stream: if provided, the filename will be ignored and the provided 
    file handle will be analyzed instead.   If you provide this stream, it will be read
    and closed.
    @param location: if provided, the location will be used as the name/location of the file.
    @param redoAnalysis: if true, analysis will take place even if the file has already been 
    analyzed.  If false, if, a previous analysis has been performed that will be used."""   
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
                
                try:                
                    self.filemagic = magic.from_buffer(buf)
                    # print("FILEMAGIC:  %s" % self.filemagic)
                    self.metadata.append(("filemagic", self.filemagic))
                except Exception, err:
                    template = "{0} Arguments:\n{1!r}"
                    message = template.format(type(err).__name__, err.args)         
                    print("Failed to extract file magic: %s" % message)                     
                                
                firstBlock = False
            
            md5.update(buf)
            sha1.update(buf)
            
            if crc32 is None: crc32 = zlib.crc32(buf)
            else: crc32 = zlib.crc32(buf, crc32)
            
            x = buf.__len__()
            totalRead = totalRead + x

        filetype.qClose(self.fh)        
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

    """This method does basically nothing; it's intended for subclassing, where 
    format-specific metadata extraction occurs."""
    def buildMetadata(self):
        print("Building base metadata for %s..." % self.filename)
        pass

    '''Writes FileMetadata for the object 
    @return: True if data was written, False otherwise'''
    def writeMetadata(self):        
        if self.firstAnalysis is False and self.redoAnalysis is False:
            #print "Skipping metadata write (%s, %s)" % (self.firstAnalysis, self.redoAnalysis)
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
        filetype.qClose(self.writehandle)
        filetype.qClose(self.fh)
                
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
                        
            if filetype.FILE_UTIL:
                pipe = subprocess.Popen([filetype.FILE_UTIL, "-b", self.filename],
                                        stdout=subprocess.PIPE, stderr=None, stdin=None,
                                        shell=False)
                readhandle = pipe.stdout
                line = readhandle.readline()
                if line is not None: line = line.strip()
                filetype.qClose(readhandle)
                pipe.wait()
                return line
            else: return "Not supported"

    def runExtractorOnBuffer(self, buf, buflen=None):
        if not filetype.xtractor: return self.metadata
        
        if buflen is None: buflen = len(buf)

        def extract_metadata_keyvalues(xt, plugin, type, format, mime, data, datalen, obj=self):
            try:                
                if (format == filetype.extractor.EXTRACTOR_METAFORMAT_UTF8):
                    mstr = cast(data, c_char_p)
                    key = filetype.xtractor.keywordTypes()[type]
                    val = mstr.value
                    print "Got metadata item from BUF: %s => %s" % (key, val)
                    self.metadata.append((key, val))
            except Exception, errstr:
                print errstr                

        # Run the extraction...
        filetype.xtractor.extract(extract_metadata_keyvalues, None, None, buf, buflen)        
        return self.metadata        
        
    """Runs a metadata extraction tool, splits the result by splitDelimiter,
    returns a list of metadata items."""
    def runGenericExtractProgram(self, cmdParts, splitDelimiter=": "):
        items = []
        
        # cmdparts may contain none if a utility needed for processing was not 
        # found.  For example, ID3File needs id3tool.  If it doesn't exist on the 
        # $PATH, the extractor may call the generic extract with None as the tool, 
        # which of course wouldn't work.
        if self.filename is None or cmdParts is None or cmdParts[0] is None:
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
            filetype.qClose(rh)            
            pipe.wait()
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)         
            print("Failed to run generic extract program %s: %s" % (cmdParts, message))

        return items
