from utils.version_comparator import is_upgrade
def test_semver_order(): assert is_upgrade("1.9.0","1.10.0")
def test_same_version(): assert not is_upgrade("1.2.0","1.2.0")
def test_baseline(): assert not is_upgrade(None,"1.2.0")
