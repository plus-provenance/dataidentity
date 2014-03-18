from files.filetype.AnalysisFactory import AnalysisFactory
from files.filetype import PDFINFO
import files.filetype

"""Performs analysis on PDF files.  Requires pdfinfo executable"""
class PDFFile(AnalysisFactory):
    def buildMetadata(self):        
        AnalysisFactory.buildMetadata(self)
        
        if PDFINFO is not None: print("Doing PDF analysis...")
        else: print("PDF analysis unsupported.")
        
        more = self.runGenericExtractProgram([PDFINFO, self.filename], ": ")
        for item in more: self.metadata.append(item)        
        return True

for fmt in [".pdf"]:
    files.filetype.register_format(fmt, PDFFile)