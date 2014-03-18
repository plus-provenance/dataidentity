#   Copyright [2013]
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
import mimetypes

import filetype.AnalysisFactory

"""For a given file or mime type, suggest a class that should be 
used for analyzing that file.
@param fileOrLocation: a full filename (or URL) of the file.
@param mimeType: if known, the MIME type without encoding of the file.
"""  
def get_appropriate_factory(fileOrLocation="", mimeType=None):   
    # Use the base class, which can process any file by default.
    analysisFactoryClass = filetype.AnalysisFactory.AnalysisFactory
    
    if mimeType is None:
        (suggested, encoding) = mimetypes.guess_type(fileOrLocation)
        if suggested is not None: mimeType = suggested
    
    # If we can find a file extension that matches a mapping, use
    # that analyzer instead.
    if fileOrLocation != "":
        for key in filetype.ANALYSIS_MAPPINGS.keys():
            if fileOrLocation.endswith(key):
                analysisFactoryClass = filetype.ANALYSIS_MAPPINGS[key]
                break
    
    if mimeType is not None:
        if filetype.ANALYSIS_MAPPINGS.has_key(mimeType):
            return filetype.ANALYSIS_MAPPINGS[mimeType]
    
    print("Appropriate factory for FILE=%s MIME=%s => %s" % (
            fileOrLocation, mimeType, analysisFactoryClass))
    return analysisFactoryClass

import filetype.ZIPFile, filetype.JARFile, filetype.OfficeFile
import filetype.ID3File, filetype.PDFFile, filetype.ImageFile, filetype.TARFile
import filetype.RubyGEM, filetype.XMLFile 
