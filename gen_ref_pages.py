"""Generate the code reference pages."""
# https://mkdocstrings.github.io/recipes/

from pathlib import Path
import mkdocs_gen_files

exclude_words = ["__init__", "csv_merge", "main"]
src_path = Path(__file__).parent.parent / "src"

for path in sorted(src_path.rglob("*.py")):
    module_path = path.relative_to(src_path).with_suffix("")
    doc_path = path.relative_to(src_path).with_suffix(".md")

    filename_parts = list(module_path.parts)
    if [elem for elem in exclude_words if elem in [part for part in filename_parts]]:
        continue

    with mkdocs_gen_files.open(doc_path, "w") as fd:
        identifier = ".".join(filename_parts)
        print("::: " + identifier, file=fd)

    mkdocs_gen_files.set_edit_path(doc_path, path)

