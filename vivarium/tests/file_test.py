from nose.tools import *
import os.path

from ..humus import Humus
from ..vivarium import File

source = None

def setup():
    global source
    filename = os.path.join(os.path.dirname(__file__), 'files.yaml')
    source = Humus(filename)

def test_defaults():
    fl = File().from_source(source, 'etc.defaults')
    eq_(fl.type, File.IS.regular)
    eq_(fl.location, '/etc/defaults')
    eq_(fl.owner, None)
    eq_(fl.group, None)
    eq_(fl.mode, None)
    eq_(fl._content, '')

def test_simple_file():
    fl = File().from_source(source, 'etc.hosts')
    eq_(fl.type, File.IS.regular)
    eq_(fl.location, '/etc/hosts')
    eq_(fl.owner, 'root')
    eq_(fl.group, 'root')
    eq_(fl.mode, 'u=rw,go=r')
    eq_(fl._template, 'etc.hosts.content')

def test_absent():
    fl = File().from_source(source, 'etc.absent')
    eq_(fl.type, File.IS.absent)
    eq_(fl.location, '/etc/absent')
    eq_(fl.owner, None)
    eq_(fl.group, None)
    eq_(fl.mode, None)

def test_dir():
    fl = File().from_source(source, 'etc.apache.mods.enabled')
    eq_(fl.type, File.IS.dir)
    eq_(fl.location, '/etc/apache2/modules-enabled')
    node = fl._files[0]
    eq_(node.type, File.IS.sym)
    eq_(node.location, '/etc/apache2/modules-enabled/proxy.load')
    eq_(node._target, '../modules-available/proxy.load')

def test_dir_external():
    fl = File().from_source(source, 'etc.apache.mods.available')
    eq_(fl.type, File.IS.dir)
    eq_(fl.location, '/etc/apache2/modules-available')
    node = fl._files[0]
    eq_(node.type, 'regular')
    eq_(node.location, '/etc/apache2/modules-available/proxy.load')
    eq_(node._content, 'apache.proxy.load.content')
    
