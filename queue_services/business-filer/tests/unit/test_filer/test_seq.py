import pytest 

@pytest.fixture(scope='session')
def sequence_generator():
    def _generator(start=1000000):
        current = start
        while True:
            yield current
            current += 1
    return _generator

# def test_get_next_identifier(sequence_generator):
#     gen = sequence_generator()
#     assert next(gen) == 1000000
#     assert next(gen) == 1000001
#     assert next(gen) == 1000002

# def test_get_nexti_2_identifier(sequence_generator):
#     gen = sequence_generator()
#     assert next(gen) == 1000003
#     assert next(gen) == 1000004
#     assert next(gen) == 1000005



@pytest.fixture(scope="session")
def sequence():
    count = {"value": 1000000}
    def _next():
        val = count["value"]
        count["value"] += 1
        return val
    return _next

def test_seq1_identifier(sequence):
    assert sequence() == 1000000
    assert sequence() == 1000001

def test_seq2_identifier(sequence):
    assert sequence() == 1000002
    assert sequence() == 1000003

def test_seq3_identifier(sequence):
    assert sequence() == 1000004
    assert sequence() == 1000005

def test_seq4_identifier(sequence):
    assert sequence() == 1000006
    assert sequence() == 1000007