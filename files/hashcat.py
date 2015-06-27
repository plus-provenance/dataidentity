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
import sys
import os
import time
from files.processing import process
import django

if __name__ == "__main__":
    print "My PID is %s" % os.getpid()
    django.setup()
    #time.sleep(5)
    
    if len(sys.argv) > 1:
        for file in sys.argv[1:]:
            if os.path.isdir(file):
                for root, dirs, files in os.walk(file):
                    for name in files:
                        process.processFile(os.path.join(root, name))
            else: process.processFile(file)
    else:
        print "Reading file list from STDIN..."
        for line in sys.stdin:
            line = line.strip()
            process.processFile(line)
