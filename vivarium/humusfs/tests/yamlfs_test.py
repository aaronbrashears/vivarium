import errno
import os.path

from ..yamlfs import YamlFS

def fullname(filename):
    return os.path.join(os.path.dirname(__file__), filename)

def test_init():
    yfs = YamlFS(fullname('simple.yaml'))
    assert True

def test_create_without_file():
    yfs = YamlFS(fullname('no_such_file.yaml'))
    assert True

def test_can_open_and_read_file():
    yfs = YamlFS(fullname('simple.yaml'))
    fl = yfs.open('/first/more/file')
    content = fl.read()
    assert 'contents' == content

def test_can_open_and_write_file():
    def write(yaml_file, file_inside, contents):
        yfs = YamlFS(fullname(yaml_file))
        fl = yfs.open(file_inside, 'w')
        fl.write(contents)
        fl.close()
    def read(yaml_file, file_inside):
        yfs = YamlFS(fullname(yaml_file))
        fl = yfs.open(file_inside)
        return fl.read()
    yaml_file = 'temp.yaml'
    file_inside = '/something/something'
    contents = 'contents'
    write(yaml_file, file_inside, contents)
    assert read(yaml_file, file_inside) == contents
    os.remove(fullname(yaml_file))

def test_with_closes_file():
    yaml_file = 'temp.yaml'
    file_inside = '/something/something'
    contents = 'contents'
    yfs = YamlFS(fullname(yaml_file))
    with yfs.open(file_inside, 'w') as fl:
        fl.write(contents)
    with yfs.open(file_inside) as fl:
        assert fl.read() == contents
    os.remove(fullname(yaml_file))

def test_list_root():
    yfs = YamlFS(fullname('simple.yaml'))
    files = yfs.list('/')
    assert 2 == len(files)
    assert 'first' in files
    assert 'second' in files

def test_list_subdir():
    yfs = YamlFS(fullname('simple.yaml'))
    files = yfs.list('/first')
    assert 2 == len(files)
    assert 'more' in files
    assert 'less' in files

def test_list_subdir_with_trailing_slash():
    yfs = YamlFS(fullname('simple.yaml'))
    files = yfs.list('/first/')
    assert 2 == len(files)
    assert 'more' in files
    assert 'less' in files

def test_list_subdir_with_files_and_dir():
    yfs = YamlFS(fullname('simple.yaml'))
    files = yfs.list('/first/more')
    assert 2 == len(files)
    assert 'file' in files
    assert 'dir' in files

def test_is_file():
    yfs = YamlFS(fullname('simple.yaml'))
    assert True == yfs.isfile('/first/more/file')

def test_is_not_file():
    yfs = YamlFS(fullname('simple.yaml'))
    assert False == yfs.isfile('/first/more')

def test_is_dir():
    yfs = YamlFS(fullname('simple.yaml'))
    assert True == yfs.isdir('/first/more')

def test_is_not_dir():
    yfs = YamlFS(fullname('simple.yaml'))
    assert False == yfs.isdir('/first/more/file')

def test_is_file_no_file_is_io_error():
    yfs = YamlFS(fullname('simple.yaml'))
    try:
        is_file = yfs.isfile('/first/more/no_such_file')
    except IOError, ee:
        if ee[0] != errno.ENOENT:
            raise
    assert True

def test_mkdirs():
    yaml_file = 'temp.yaml'
    yfs = YamlFS(fullname(yaml_file))
    dirs = '/foo/bar'
    yfs.mkdirs(dirs)
    file_inside = dirs + '/baz'
    contents = 'contents'
    with yfs.open(file_inside, 'w') as fl:
        fl.write(contents)
    with yfs.open(file_inside) as fl:
        assert fl.read() == contents
    os.remove(fullname(yaml_file))
