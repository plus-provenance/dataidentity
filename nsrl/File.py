#   Copyright [2013] [M. David Allen]
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
import csv
import nsrl.Product
import nsrl.OS

class File:
    sha1 = None
    md5 = None
    crc32 = None
    name = None
    size = None
    prodcode = None
    oscode = None
    specialcode = None    
    
    def __init__(self, sha1, md5, crc32, name, size, prodcode, oscode, specialcode):
        self.sha1 = sha1.lower()
        self.md5 = md5.lower()
        self.crc32 = crc32.lower()
        self.name = name
        self.size = size
        self.prodcode = prodcode
        self.oscode = oscode
        self.specialcode = specialcode
        
    def getProduct(self):
        try: 
            return nsrl.Product.LOOKUP[str(self.prodcode)]
        except KeyError:
            return "Missing"
    
    def getOS(self):
        try: 
            return nsrl.OS.LOOKUP[str(self.oscode)]
        except KeyError:
            return "Missing"
        
    def __str__(self):
        return "File (%s) %s bytes sha1 %s md5 %s crc32 %s prod %s OS %s special %s" % (self.name, self.size, 
                                                                                        self.sha1, self.md5, self.crc32,
                                                                                        self.getProduct(), self.getOS(), 
                                                                                        self.specialcode)
        
class FileIterator:
    csv = None
    header = False
    
    def __init__(self, readhandle):
        self.csv = csv.reader(readhandle, delimiter=',', quotechar='"')    
        self.header = False

    def __iter__(self): return self
        
    def strp(self, val):
        if val.startswith('"'): return val[1:-1]
        return val
        
    def next(self):
        fetch = True
        
        while fetch:
            row = self.csv.next()
            if len(row[1]) != 32:
                print("Skipping line with invalid MD5: %s" % ",".join(row))
            else: fetch = False
        
        return File(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
    
        