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

LOOKUP = {}

class Product:
    code = None
    name = None
    version = None
    opsystemcode = None
    mfgcode = None
    language = None
    apptype = None
    
    def __init__(self, code, name, version, opsystemcode, mfgcode, language, apptype):
            self.code = code
            self.name = name
            self.version = version
            self.opsystemcode = opsystemcode
            self.language = language
            self.mfgcode = mfgcode        
            self.apptype = apptype
    
    def __str__(self):
        return "%s version %s language %s type %s" % (self.name, self.version, self.language, self.apptype)

def importFrom(readhandle):
    records = csv.reader(readhandle, delimiter=',', quotechar='"')    
    for row in records:
        o = Product(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
        LOOKUP[str(o.code)] = o
        
        # print o
        
        