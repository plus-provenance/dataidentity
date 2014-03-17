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
from django.db import models
from django import template
import os

register = template.Library()
INTERNAL_PREFIX="moxious:"

"""This class represents an item submitted by a user for processing.
Because processing can take a while, we store them in a queue for 
serial processing."""
class SubmissionQueue(models.Model):
    STARTED = "start"
    NOT_STARTED = "ns"
    FETCHING = "fetch"
    ANALYZING = "analyze"
    FINALIZE = "finalize"
    FINISHED = "finish"
    FAILED = "fail"
    
    STATUS_CHOICES = (
        (STARTED, "Started"),
        (NOT_STARTED, "Not yet started"),
        (FETCHING, "Fetching resource"),
        (ANALYZING, "Analyzing resource"),
        (FINISHED, "Finished"),
        (FINALIZE, "Finalizing"),
        (FAILED, "Failed")
    ) 
    
    class Meta:
        ordering = ["submitted"]
        verbose_name = "Submission Queue Item"
        verbose_name_plural = "Submission Queue Items"
    
    location = models.CharField(max_length=255, db_index=True)
    submitted = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, db_index=True, choices=STATUS_CHOICES, default=NOT_STARTED)
    finished = models.BooleanField(default=False)
    
    def __str__(self):
        return "Submission Item (%s) %s %s %s" % (self.location, self.status, str(self.finished), str(self.submitted))

class FileName(models.Model):
    class Meta:
        ordering = ['location']
        verbose_name = "file name/location"
        verbose_name_plural = "file names/locations"

    basefile = models.ForeignKey('File', related_name='names')
    location = models.CharField(max_length=255, db_index=True)
    analysisDate = models.DateTimeField(auto_now_add=True)

    def is_url(self):
        return self.location.lower().startswith("http")

    def filename(self):
        name = self.location.split("/")[-1]

        if name is None or name == '':
            if len(self.location) < 50:
                return self.location
            else:
                return self.location[0:47] + "(...)"

        return name

    def extension(self):
        return os.path.splitext(self.location)[1]

class FileRelationship(models.Model):
    subject = models.ForeignKey('File', related_name='subjectOf')
    verb = models.CharField(max_length=64, db_index=True)
    object = models.ForeignKey('File', related_name='objectOf')
    
    class Meta:
        verbose_name = "file relationship"
        verbose_name_plural = "file relationships"

class FileMetadata(models.Model):
    basefile = models.ForeignKey('File', related_name='metadata')
    key = models.CharField(max_length=255, db_index=True)
    value = models.CharField(max_length=255, db_index=True)
    seq = models.IntegerField(default=0)

    class Meta:
        verbose_name = "file metadata item"
        verbose_name_plural = "file metadata items"
        ordering = ['seq']

    """Sometimes files are linked to one another via a metadata field value,
    which is an md5 hash.  This function returns that related file object.  
    This is *not* the file object the metadata item is attached to, but the
    file object the metadata *value* points to."""
    @property
    def valueRelatedFile(self):
        try: return File.objects.get(md5=self.value)
        except Exception, err:
            print err
            return None
        
class File(models.Model):
    class Meta:
        ordering = ['-analysisDate']
        verbose_name = "file profile"
        verbose_name_plural = "file profiles"

    md5 = models.CharField(max_length=32, db_index=True, primary_key=True)
    sha1 = models.CharField(max_length=42, db_index=True)
    crc32 = models.CharField(max_length=8, db_index=True)
    analysisDate = models.DateTimeField(auto_now_add=True)
    size = models.BigIntegerField(default=0)

    @property
    def describeSize(self):
        s = self.size
        
        kb = 1024
        mb = 1024 * kb
        gb = 1024 * mb
        tb = 1024 * gb
        
        if s > tb: return str(round(float(s)/float(tb), 2) + " TB")
        if s > gb: return str(round(float(s)/float(gb), 2) + " GB")
        if s > mb: return str(round(float(s)/float(mb), 2) + " MB")
        if s > kb: return str(round(float(s)/float(kb), 2) + " KB")        
        return "%s bytes" % str(s)
        
    @property
    def basicMetadata(self):
        return self.metadata.all().exclude(key__startswith=INTERNAL_PREFIX)

    @property
    def containments(self):
        return self.subjectOf.all().filter(verb="contains")

    @property    
    def containers(self):
        return self.subjectOf.all().filter(verb="containedBy")

    """Add a relationship from this file to another; this file will be the subject.
    @param verb: a string describing the relationship (e.g. "contains")
    @param object: the File object involved in the relationship"""  
    def addRelationship(self, verb, object):
        if type(verb) != str: raise Exception("Verb must be a string")
        if type(object) != File: raise Exception("Other must be a file")
        fr = FileRelationship(subject=self, verb=verb, object=object)
        fr.save()
        return fr

    def addMetadata(self, key, value, seq=0):
        fm = FileMetadata(basefile=self, key=key, value=value, seq=seq)
        fm.save()
        return fm

    def extension(self):
        try: 
            fname = self.names.all()[0]
            return fname.extension()
        except:  return ""
