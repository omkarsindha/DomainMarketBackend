import os

print(os.getcwd())
#
# output_file = "all_code.txt"
#
# with open(output_file, "w", encoding="utf-8") as out:
#     for root, dirs, files in os.walk("."):
#         # prevent descending into .venv and tests
#         if ".venv" in dirs:
#             dirs.remove(".venv")
#         if "tests" in dirs:
#             dirs.remove("tests")
#
#         # sort for consistent output
#         dirs.sort()
#         files.sort()
#
#         for file in files:
#             if file.endswith(".py"):
#                 filepath = os.path.join(root, file)
#                 relpath = os.path.relpath(filepath, ".")  # relative path
#                 out.write(f"===== {relpath} =====\n")
#                 with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
#                     out.write(f.read())
#                     out.write("\n\n")