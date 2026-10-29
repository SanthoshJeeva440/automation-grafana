from packaging.version import Version, InvalidVersion
def is_upgrade(previous, latest):
    if not previous: return False
    try: return Version(str(latest)) > Version(str(previous))
    except InvalidVersion: return str(latest) != str(previous)
