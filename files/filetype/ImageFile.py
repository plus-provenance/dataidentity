import files.filetype
from files.filetype.AnalysisFactory import AnalysisFactory

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
        
        files.filetype.qClose(i)
        
        return success


for format in [".gif", ".jpg", ".xpm", ".png", ".bpm", ".tiff", "image/tiff", "image/gif", "image/jpeg", "image/png"]:
    files.filetype.register_format(format, ImageFile)
