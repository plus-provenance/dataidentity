from files.filetype.AnalysisFactory import AnalysisFactory
import files.filetype

"""Performs ID3 tag extraction of files.  Requires id3tool"""
class ID3File(AnalysisFactory):
    def buildMetadata(self):
        AnalysisFactory.buildMetadata(self)        

        if files.filetype.ID3TOOL is not None: print("Doing ID3 analysis...")
        else: print("Skipping ID3 analysis, ID3TOOL not supported.")
        more = self.runGenericExtractProgram([files.filetype.ID3TOOL, self.filename], ": ")
        for item in more: self.metadata.append(item)
        return True

for fmt in [".mp3"]:
    files.filetype.register_format(fmt, ID3File)