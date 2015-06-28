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
from rest_framework import serializers
from files.models import * 

class FileRelationshipModelField(serializers.BaseSerializer):
    def to_representation(self, obj):
        arr = []
        for rel in obj.all():
            arr.append({"subject" : rel.subject.md5, 
                        "verb"    : rel.verb, 
                        "object"  : rel.object.md5})
        return arr

class FileMetadataModelField(serializers.BaseSerializer):
    """Metadata objects are serialized as a dictionary"""
    def to_representation(self, obj):
        mdEntries = obj.all()
        d = {}
        for mdEntry in mdEntries:
            d[mdEntry.key] = mdEntry.value
        return d

class FileNameModelField(serializers.BaseSerializer):
    """Filenames are serialized as a simple primitive location"""
    def to_representation(self, obj):
        return obj.location

class FileModelSerializer(serializers.ModelSerializer):
    names = FileNameModelField(many=True)
    metadata = FileMetadataModelField()
    subjectOf = FileRelationshipModelField()
    # Don't include objectOf otherwise relationships will occur twice when reflexive.
    # objectOf = FileRelationshipModelField()

    class Meta:
        model = File
        fields = ('md5', 'sha1', 'crc32', 
                  'analysisDate', 'size', 'names', 'metadata', 'subjectOf')
