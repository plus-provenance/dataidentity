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
import nsrl.Manufacturer

LOOKUP = {}

class OS:
    code = None
    name = None
    version = None
    mfgcode = None
    
    def __init__(self, code, name, version, mfgcode):
            self.code = code
            self.name = name
            self.version = version
            self.mfgcode = mfgcode        
    
    def __str__(self):
        return "%s version %s manufacturer %s" % (self.name, self.version, self.getManufacturer())

    def getManufacturer(self):
        try:
            return nsrl.Manufacturer.LOOKUP[self.mfgcode].name
        except KeyError:
            return "Unknown"

def importFrom(readhandle):
    records = csv.reader(readhandle, delimiter=',', quotechar='"')
    for row in records:
        o = OS(row[0], row[1], row[2], row[3])
        LOOKUP[str(o.code)] = o
        # print o
        
        