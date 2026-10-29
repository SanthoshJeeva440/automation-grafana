def format_upgrade(x):
    return f'{x["name"]} ({x["category"]}): {x["previous_version"]} -> {x["latest_version"]}\\n{x["release_url"]}'
