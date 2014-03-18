import tarfile
import files.filetype
from files.filetype.TARFile import TARFile

"""Helper function for YAML parser"""
def construct_ruby_object(loader, suffix, node):
    return loader.construct_yaml_map(node)

"""Helper function for YAML parser"""
def construct_ruby_sym(loader, node):
    return loader.construct_yaml_str(node)

class RubyGEM(TARFile):
    """Extracts special items from a gemspec as metadata"""
    def makeMetadataFromGemspec(self, spec):
        harvestFields = ['author', 'authors', 'name', 'platform', 'require_paths', 'rubygems_version', 'summary', 'version/version', 'license', 'licenses',
                         "signing_key", "homepage", "executables", "email"]
            
        """A method that allows xpath-like access through a nested dictionary.  Separate nodes by slashes, i.e.
        with dictionary { "x": "Foo", "y" : { "bar" : "baz" } } the path expression "y/bar" evaluates to "baz"."""    
        def xpath_get(mydict, path):
            elem = mydict
            try:
                for x in path.strip("/").split("/"):
                    elem = elem.get(x)
            except: pass

            return elem                
                
        """Returns true if an object is a sequence (but not a string), false otherwise (via duck-typing)"""
        def is_sequence(arg):
            return (not hasattr(arg, "strip") and
                    hasattr(arg, "__getitem__") or
                    hasattr(arg, "__iter__"))

        """Quickly flatten all string members of a sequence into a single string, comma separated."""
        def qFlatten(seq):
            r = []
            for i in seq:
                if isinstance(i, str): 
                    r.append(i)
            return ", ".join(r)

        for field in harvestFields:
            val = xpath_get(spec, field)
            if val is None: continue
            if not is_sequence(val):
                self.metadata.append(("gem:%s" % field, str(val)))
            else:
                self.metadata.append(("gem:%s" % field, qFlatten(val)))
        
        # Harvest dependencies, if present.
        try: 
            deps = spec['dependencies']
            if deps is not None:
                for dep in deps:
                    if dep is not None:
                        try: 
                            depName = dep['name']
                            if isinstance(depName, basestring):
                                self.metadata.append(("gem:dependency", depName))
                        except KeyError: pass
        except KeyError: pass
        return

    def buildMetadata(self):
        TARFile.buildMetadata(self)

        try: 
            import yaml            
        except:
            print("Skipping GEM analysis of %s because YAML is not supported by this python" % self.filename)
            return
        
        try:
            import gzip
        except:
            print("Skipping GEM analysis of %s because GZip is not supported by this python" % self.filename)
            return        

        print "Doing GEM analysis..."
        try:
            tf = tarfile.open(self.filename, "r")
            
            for tarEntry in tf.getmembers():
                if not tarEntry.isfile(): continue
                if not tarEntry.name == 'metadata.gz': continue
                
                handle = tf.extractfile(tarEntry)
                gzipHandle = gzip.GzipFile(fileobj=handle)

                yaml.add_multi_constructor(u"!ruby/object:", construct_ruby_object)
                yaml.add_constructor(u"!ruby/sym", construct_ruby_sym)

                gemSpec = yaml.load(gzipHandle)
                # print "FOUND GEMSPEC %s" % str(gemSpec)
                
                # For debugging....
                # import pprint
                # pp = pprint.PrettyPrinter(indent=4)
                # pp.pprint(gemSpec)
                
                self.makeMetadataFromGemspec(gemSpec)
                
                files.filetype.qClose(gzipHandle)
                files.filetype.qClose(handle)
        finally:
            files.filetype.qClose(tf)
            
for format in [".gem"]:
    files.filetype.register_format(format, RubyGEM)
