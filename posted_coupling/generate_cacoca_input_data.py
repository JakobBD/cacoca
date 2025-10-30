from pathlib import Path

from cacoca_posted_coupling import generate_cacoca_input

code_folder = Path.cwd().parent
target_folder = code_folder / "cacoca" / "data" / "tech" / "posted"
posted_datafolder = code_folder / "posted" / "inst" / "extdata" / "database" / "tedfs" / "Tech"

generate_cacoca_input(target_folder, posted_datafolder=posted_datafolder)