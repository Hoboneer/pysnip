from itertools import chain
from typing import List, Tuple, Dict, Union
from pathlib import PurePosixPath

import parso
from parso.python.tree import Scope
import fs


# Does mypy support recursive types yet?
Filesystem = Dict[PurePosixPath, Union['Filesystem', Scope]]


# NOTE: Filename for the code text is simply "<path>/<name>.<type>".

# NOTE: Filename for the directory containing children is simply
# "<path>/<name>.<type>.c" ("c" for children).

# NOTE: Filename for the directory containing definitions in the same scope is
# simply "<path>/<name>.type.c" ("d" for duplicate). The child definitions will
# be uniquely named (perhaps it should be a hash of their contents?), e.g., "0.classdef".

def recurse_filter(tree: Scope, path: PurePosixPath) -> List[Tuple[PurePosixPath, Scope]]:
    # Recursively construct a list mapping paths (in the code structure) to `Scope`s to `Scope`s.
    scopes = list(chain(tree.iter_funcdefs(), tree.iter_classdefs()))
    # Base case.
    if len(scopes) == 0:
        return []

    path_to_scopes = list(
        map(lambda scope: (path / f"{scope.name.value}.{scope.type}", scope), scopes)
    )
    # Recursively get children scopes.
    for scope_path, scope in path_to_scopes.copy():
        extension = scope.type
        path_to_scopes += recurse_filter(
            scope, path / f"{scope.name.value}.{extension}.c"
        )  # "c" for children.

    return path_to_scopes

def paths_to_fs(path_to_scopes: List[Tuple[PurePosixPath, Scope]]) -> Filesystem:
    # Converts result of `recurse_filter` to filesystem-like dict.

    # Group by paths.
    grouped_scopes: Dict[PurePosixPath, List[Scope]] = {}
    for path, scope in sorted(path_to_scopes.copy(), key=lambda item: item[0]):
        grouped_scopes.setdefault(path, []).append(scope)

    # De-duplicate paths: Place duplicate definitions made in the same scope
    # into a subdirectory (suffix: ".d" for duplicate).
    fs_dirs: List[Tuple[PurePosixPath, Scope]] = []
    for path, scopes in grouped_scopes.items():
        # Scopes of length 1 can be safely moved out of the list (they are
        # unique).
        if len(scopes) == 1:
            fs_dirs.append((path, scopes[0]))
            continue

        # Collapse multiple scopes into uniquely named files in their '.d' directory.
        for i, scope in enumerate(scopes):
            fs_dirs.append((path.with_suffix('.d') / f"{i}.{scope.type}", scope))

    filesystem = {}
    # Make fs directory hierarchy.
    for path, scope in fs_dirs:
        current_level = filesystem
        for i, part in enumerate(path.parts):
            # No subdirs need to be made for root dir.
            # TODO: What to do about "weird" paths? (e.g., '/' parts in the middle).
            if i == 0 and part == '/':
                continue

            # Make "file" in specified parent part if this is last part it is not a directory.
            if part == path.name and not part.endswith(('.d', '.c')):
                current_level[part] = scope
                break

            # Make directory if needed.
            if part not in current_level:
                current_level[part] = {}

            # Go into subdirectory.
            current_level = current_level[part]

    return filesystem


with fs.open_fs(".") as cwd:
    program = parso.parse(cwd.gettext("test.py"))
    tree = program
    paths_to_scopes = recurse_filter(tree, PurePosixPath("/"))
    filesystem = paths_to_fs(paths_to_scopes)
