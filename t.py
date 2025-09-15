import os

for root, dirs, files in os.walk("."):
    # prevent descending into .venv
    if ".venv" in dirs:
        dirs.remove(".venv")
    if "tests" in dirs:
        dirs.remove("tests")

    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            print(f"===== {filepath} =====")
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                print(f.read())