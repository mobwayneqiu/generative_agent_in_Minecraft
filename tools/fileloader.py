
def fileLoader(path) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content