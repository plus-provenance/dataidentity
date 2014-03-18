# from files.analysis import get_appropriate_factory, AnalysisFactory, qClose
import sys, traceback
from zipfile import ZipFile, is_zipfile
from files.filetype.AnalysisFactory import AnalysisFactory
import files.filetype
import files.analysis

class ZIPFile(AnalysisFactory):
    def processNestedZipEntry(self, handle, zipInfo, containedBy):
        # NOTE NOTE NOTE
        # DO NOT DO RECURSIVE PROCESSING -- ONE LEVEL ONLY.
        # That means, use the generic analysis factory, not a specialized
        # form that may recursively descend, for security reasons.
        print("Processing nested zip entry %s" % zipInfo.filename)
                
        factory = files.analysis.get_appropriate_factory(zipInfo.filename)
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

        # print "Doing ZIPFile analysis..."
                
        zf = None
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
                    files.filetype.qClose(handle)
                        
            return True
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to process zipfile %s : %s" % (self.filename, message))
            traceback.print_exc(file=sys.stdout)
            return False
        finally:
            files.filetype.qClose(zf)
            
for format in [".zip", "application/zip"]:
    files.filetype.register_format(format, ZIPFile)
            
