from ..vivarium import _merge_dicts as merge

def test_merge_does_not_modify():
    lesser = dict(a=1,b=2)
    greater = dict(a=2,c=3)
    merged = merge(lesser, greater)
    assert len(lesser) == 2
    assert lesser['a'] == 1
    assert lesser['b'] == 2
    assert len(greater) == 2
    assert greater['a'] == 2
    assert greater['c'] == 3
    assert len(merged) == 3
    assert merged['a'] == 2
    assert merged['b'] == 2
    assert merged['c'] == 3

def test_merge():
    lesser = dict(a=1,b=2,c=dict(ca=31, cc=33, cd=dict(cca=1)), d=4, f=6, g=7)
    greater = dict(b='u2',c=dict(cb='u32', cd=dict(cda=dict(cdaa='u3411', cdab='u3412'))), e='u5', h=dict(i='u4321'))
    merged = merge(lesser, greater)
    assert merged['a'] == 1 and merged['d'] == 4 and merged['f'] == 6
    assert merged['b'] == 'u2' and merged['e'] == 'u5'
    assert merged['c']['ca'] == 31
    assert merged['c']['cb'] == 'u32'
    assert merged['c']['cd']['cda']['cdaa'] == 'u3411'
    assert merged['c']['cd']['cda']['cdab'] == 'u3412'
    assert merged['g'] == 7
    assert merged['h']['i'] == 'u4321'
