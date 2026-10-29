import re

PATTERN = r"(?<!\\d)(\\d+\\.\\d+(?:\\.\\d+)?(?:[-+][0-9A-Za-z.-]+)?)"

def test_common_release_tags():
    for tag, expected in [("v1.64.1", "1.64.1"), ("1.2.3", "1.2.3"), ("v2.0", "2.0")]:
        match = re.search(PATTERN, tag.lstrip("vV"))
        assert match
        assert match.group(1) == expected
