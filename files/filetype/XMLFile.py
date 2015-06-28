from files.filetype.AnalysisFactory import AnalysisFactory
from defusedxml import minidom, EntitiesForbidden, DTDForbidden
import files.filetype

class XMLFile(AnalysisFactory):
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)
        
        #print("Doing XMLFile analysis...")
        try:
            if self.filename is not None:
                doc = minidom.parse(self.filename)
            else:
                self.fh.seek(0)
                doc = minidom.parse(self.fh)
            #print("Got doc %s" % str(doc))
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

for fmt in [".xml", ".xslt", ".xsd", "application/xml"]:
    files.filetype.register_format(fmt, XMLFile)
