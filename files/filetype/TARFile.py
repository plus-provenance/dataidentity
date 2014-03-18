import files.filetype
import files.analysis
import tarfile, sys, traceback
from files.filetype.AnalysisFactory import AnalysisFactory

class TARFile(AnalysisFactory):
    def processNestedTarEntry(self, handle, tarInfo, containedBy):
        # NOTE NOTE NOTE
        # DO NOT DO RECURSIVE PROCESSING -- ONE LEVEL ONLY.
        # That means, use the generic analysis factory, not a specialized
        # form that may recursively descend, for security reasons.
        print("Processing nested tar entry %s" % tarInfo.name)
        factory = files.analysis.get_appropriate_factory(tarInfo.name)
        # print("Factory is %s with FILEMAGIC %s" % (factory, self.filemagic))        
        af = factory(filename=None, stream=handle, location=tarInfo.name, redoAnalysis=False)
        af.analyze()        
        af.fileModel.addRelationship("containedBy", containedBy)
        
        return af.fileModel    
    
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)

        # print "Doing TARFile analysis..."
        tf = None
        try:
            tf = tarfile.open(self.filename, "r")
        
            if tf.posix: self.metadata.append(("tarformat", "USTAR_FORMAT"))
            else: self.metadata.append(("tarformat", "GNU_FORMAT"))
    
            handle = None
        
            for tarEntry in tf.getmembers():
                if not tarEntry.isfile(): continue
                handle = tf.extractfile(tarEntry)
                contained = self.processNestedTarEntry(handle, tarEntry, self.fileModel)
                
                files.filetype.qClose(handle)
                
                self.fileModel.addRelationship("contains", contained)
            return True
        except Exception, err:
            template = "{0} Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            print("Failed to process tarfile %s : %s" % (self.filename, message))
            traceback.print_exc(file=sys.stdout)
            return False       
        finally:
            files.filetype.qClose(tf)

for format in [".tgz", ".tar.gz"]:
    files.filetype.register_format(format, TARFile)
    