from itertools import chain
from typing import List, Tuple

import parso
from parso.tree import Scope
import fs


# NOTE: Filename for the code text is simply "<path>/<name>.<type>".

# NOTE: Filename for the directory containing children is simply
# "<path>/<name>.<type>.c" ("c" for children).

# TODO: What to do about duplicates?
#       - Perhaps make a new directory with similar naming scheme? This forces
#         users to choose which code text they want.
#       - Naming scheme? "<path>/<name>.<type>.d" ("d" for duplicates).
#         Perhaps filename should just be a (maybe, randomly chosen) number in
#         order to differentiate.

def recurse_filter(tree: Scope, path: str) -> List[Tuple[str, Scope]] :
    # Tree is a parso tree.
    # Path is a POSIX path.
    scopes = list(chain(tree.iter_funcdefs(), tree.iter_classdefs()))
    # Base case.
    if len(scopes) == 0:
        return []

    path_to_scopes = list(map(lambda scope: (path, scope), scopes))
    # Recursively get children scopes.
    for path, scope in path_to_scopes.copy():
        extension = scope.type
        path_to_scopes += recurse_filter(scope, f"{path}{scope.name.value}.{extension}.d/")

    return path_to_scopes

# with fs.open_fs('.') as cwd:
#     program = parso.parse(cwd.gettext('test.py'))
#     funcdefs = program.iter_funcdefs()
#     classdefs = program.iter_classdefs()
#     for scopedef in chain(funcdefs, classdefs):
#         extension = scopedef.type
#         name = scopedef.name.value
#         print(f"{name}.{extension}")
#         print(scopedef.get_code(include_prefix=False))

with fs.open_fs('.') as cwd:
    program = parso.parse(cwd.gettext('test.py'))
    tree = program
    paths_to_scopes = recurse_filter(tree, "/")
    for path, scope in paths_to_scopes:
        print(path)
        print(scope.get_code(include_prefix=False))
    print(paths_to_scopes)
