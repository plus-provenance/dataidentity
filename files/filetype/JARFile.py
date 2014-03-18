import sys, traceback
from zipfile import ZipFile, is_zipfile
import files.filetype
from files.filetype.ZIPFile import ZIPFile

class JARFile(ZIPFile):   # NOTE!!!! Do not confuse ZIPFile with ZipFile    
    def buildMetadata(self):        
        ZIPFile.buildMetadata(self)
                
        if not is_zipfile(self.filename):
            self.metadata.append(("Data format warning", "File cannot be processed as a JAR file"))
            return True
                
        # print "Doing JAR analysis..."

        zf = None
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
                files.filetype.qClose(manifest)
                        
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
            files.filetype.qClose(zf)

for format in [".jar", "application/java-archive", ".war", ".ear"]:
    files.filetype.register_format(format, JARFile)                      
