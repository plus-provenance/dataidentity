from zipfile import ZipFile
from defusedxml import minidom
import traceback
from files.filetype.ZIPFile import ZIPFile
import sys
import files.filetype

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
            
        zf = None
    
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
                    files.filetype.qClose(f)
            return True
        except Exception, err:
            # Fall back to conservative method
            print("Failed processing office zipfile: %s" % str(err))
            traceback.print_exc(file=sys.stdout)
            return False
        finally:
            if zf is not None: files.filetype.qClose(zf)
            
for format in [".doc", ".docx", ".xls", ".xslx", ".ppt", ".pptx", "application/msword", 
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
               "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
               "application/vnd.ms-excel", 
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
    files.filetype.register_format(format, OfficeFile)
