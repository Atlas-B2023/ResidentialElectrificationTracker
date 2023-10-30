"""Generate the code reference pages."""

from pathlib import Path

import mkdocs_gen_files

for path in sorted(Path("src").rglob("*.py")):
    filename = path.with_suffix("")
    rel_filename = path.relative_to("src").with_suffix("")
    
    filename_parts = filename.parts

    with mkdocs_gen_files.open(rel_filename.with_suffix(".md"), "w") as fd:
        print("::: " + ".".join(filename_parts), file=fd)

    mkdocs_gen_files.set_edit_path(rel_filename.with_suffix(".md"), "gen_ref_pages.py")


# # src_folder = "src"
# # for path in sorted(Path("src_folder").rglob("*.py")):
# #     md_filename = path.relative_to("src_folder").with_suffix(".md")
# #     py_filename = path.relative_to("src_folder")

# #     parts = py_filename.parts
# #     #dont document the __init__ file in modules
# #     if parts[-1] == "__init__":  
# #         parts = parts[:-1]
# #     elif parts[-1] == "__main__":
# #         continue

# #     with mkdocs_gen_files.open(md_filename, "w") as fd:  
# #         # get last part and change to py
# #         print("::: " + src_folder + ".".join(parts), file=fd)  
    
# #     mkdocs_gen_files.set_edit_path(md_filename, "gen_ref_pages.py")
        
# # for total in range(19, 100, 20):
# #     filename = f"sample/{total}-bottles.md"

# #     with mkdocs_gen_files.open(filename, "w") as f:
# #         for i in reversed(range(1, total + 1)):
# #             print(f"{i} bottles of beer on the wall, {i} bottles of beer  ", file=f)
# #             print(f"Take one down and pass it around, **{i-1}** bottles of beer on the wall\n", file=f)

# #     mkdocs_gen_files.set_edit_path(filename, "gen_ref_pages.py")


# with mkdocs_gen_files.open("src/test/RedfinSearcher.md", "w") as fd:  
#     # get last part and change to py
#     print("::: " + "src.test.RedfinSearcher", file=fd)  
#     # print("handler: python")
#     # print("options:")
#     # print("members:")
#     # print("- set_filters_path")
#     # print("- set_filters_path")
#     # options:
#     #   members:
#     #     - set_filters_path
#     #     - generate_filters_path
#     #   show_root_heading: false
#     #   show_source: true
#     #   """)

# mkdocs_gen_files.set_edit_path("src/test/RedfinSearcher.md", "gen_ref_pages.py")