from ..vivarium import _topological_sort as topo_sort
from ..vivarium import CircularDependencyError

def test_dependencies():
    deps = {
        'des_system_lib':   set('std synopsys std_cell_lib des_system_lib dw02 dw01 ramlib ieee'.split()),
        'dw01':             set('ieee dw01 dware gtech'.split()),
        'dw02':             set('ieee dw02 dware'.split()),
        'dw03':             set('std synopsys dware dw03 dw02 dw01 ieee gtech'.split()),
        'dw04':             set('dw04 ieee dw01 dware gtech'.split()),
        'dw05':             set('dw05 ieee dware'.split()),
        'dw06':             set('dw06 ieee dware'.split()),
        'dw07':             set('ieee dware'.split()),
        'dware':            set('ieee dware'.split()),
        'gtech':            set('ieee gtech'.split()),
        'ramlib':           set('std ieee'.split()),
        'std_cell_lib':     set('ieee std_cell_lib'.split()),
        'synopsys':         set(),
        }
    expected = [
        'ieee std synopsys'.split(),
        'dware gtech ramlib std_cell_lib'.split(),
        'dw01 dw02 dw05 dw06 dw07'.split(),
        'des_system_lib dw03 dw04'.split()]
    for layer in topo_sort(deps):
        print(layer)
        assert layer == expected.pop(0)

def test_circular():
    deps = {
        'foo': set(['bar', 'wallo']),
        'bar': set(['baz']),
        'baz': set(['foo']),
        }
    try:
        for layer in topo_sort(deps):
            print(layer)
    except CircularDependencyError:
        return
    assert False
