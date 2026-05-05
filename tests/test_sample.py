from target_code.sample_code import add

def test_add():
    assert add(2, 3) == 5

def test_fail():
    assert add(2, 2) == 5