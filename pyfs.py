from io import BytesIO
from itertools import chain
from pathlib import PurePosixPath
from typing import (
    Any,
    BinaryIO,
    Collection,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
    cast,
)

import parso
from fs.base import FS
from fs.errors import (
    DirectoryExpected,
    FileExpected,
    ResourceNotFound,
    Unsupported,
)
from fs.info import Info
from fs.permissions import Permissions
from fs.subfs import SubFS
from parso.python.tree import Scope

# TODO: Should imports be implemented? Should they be directories in this
# filesystem?

# NOTE: Filename for the code text is simply "<path>/<name>.<type>".

# NOTE: Filename for the directory containing children is simply
# "<path>/<name>.<type>.c" ("c" for children).

# NOTE: Filename for the directory containing definitions in the same scope is
# simply "<path>/<name>.type.c" ("d" for duplicate). The child definitions will
# be uniquely named (perhaps it should be a hash of their contents?), e.g.,
# "0.classdef".

# mypy does not support recursive types yet.
Filesystem = Dict[PurePosixPath, Union["Filesystem", Scope]]  # type: ignore
RawInfo = Mapping[str, Mapping[str, object]]


def map_code_tree(
    tree: Scope, path: PurePosixPath
) -> List[Tuple[PurePosixPath, Scope]]:
    # Recursively construct a list mapping paths (in the code structure) to
    # `Scope`s to `Scope`s.
    scopes = list(chain(tree.iter_funcdefs(), tree.iter_classdefs()))
    # Base case.
    if len(scopes) == 0:
        return []

    path_to_scopes = list(
        map(
            lambda scope: (path / f"{scope.name.value}.{scope.type}", scope),
            scopes,
        )
    )
    # Recursively get children scopes.
    for scope_path, scope in path_to_scopes.copy():
        extension = scope.type
        path_to_scopes += map_code_tree(
            scope, path / f"{scope.name.value}.{extension}.c"
        )  # "c" for children.

    return path_to_scopes


def dedup_paths(
    paths: List[Tuple[PurePosixPath, Scope]]
) -> List[Tuple[PurePosixPath, Scope]]:
    # Group by paths.
    grouped_scopes: Dict[PurePosixPath, List[Scope]] = {}
    for path, scope in paths:
        grouped_scopes.setdefault(path, []).append(scope)

    # De-duplicate paths: Place duplicate definitions made in the same scope
    # into a subdirectory (suffix: ".d" for duplicate). Note, this is still a
    # flat "filesystem".
    fs_dirs: List[Tuple[PurePosixPath, Scope]] = []
    for path, scopes in grouped_scopes.items():
        # Scopes of length 1 can be safely moved out of the list (they are
        # unique).
        if len(scopes) == 1:
            fs_dirs.append((path, scopes[0]))
            continue

        # Collapse multiple scopes into uniquely named files in their '.d'
        # directory.
        for i, scope in enumerate(scopes):
            fs_dirs.append(
                (path.with_suffix(".d") / f"{i}.{scope.type}", scope)
            )
    return fs_dirs


def make_fs(paths: List[Tuple[PurePosixPath, Scope]]) -> Filesystem:
    # Converts list of path-scope pairs to filesystem-like dict.
    filesystem: Filesystem = {}
    # Make fs directory hierarchy.
    for path, scope in paths:
        current_level = filesystem
        for part in path.parts:
            # No subdirs need to be made for root dir.
            if part == "/":
                continue

            posix_part = PurePosixPath(part)
            # Make "file" in specified parent part if this is last part and it
            # is not a directory.
            if part == path.name and not part.endswith((".d", ".c")):
                current_level[posix_part] = scope
                break

            # Make directory if needed.
            if posix_part not in current_level:
                current_level[posix_part] = {}

            # Go into subdirectory.
            current_level = current_level[posix_part]

    return filesystem


class PyCodeFS(FS):
    _meta = {
        "case_insensitive": False,
        "invalid_path_chars": ",",  # Reserved for future.
        "max_path_length": None,
        "network": False,
        # At least until `parso` supports modifications and a design
        # is worked out for this.
        "read_only": True,
        "supports_rename": False,
    }

    def __init__(self, code_text: str, language_version: Optional[str] = None):
        super().__init__()
        self._program = parso.parse(code_text, version=language_version)
        paths_to_scopes = self._build_filesystem()
        # For quick (direct) access of files (O(1) vs O(n)).
        self._files: Dict[PurePosixPath, Scope] = dict(paths_to_scopes)
        # For walking the filesystem.
        self._filesystem: Filesystem = make_fs(paths_to_scopes)

    def _build_filesystem(self) -> List[Tuple[PurePosixPath, Scope]]:
        code_tree = self._program.get_root_node()
        # Start at root directory (top-level/module scope)
        paths_to_scopes = map_code_tree(code_tree, PurePosixPath("/"))
        return dedup_paths(paths_to_scopes)

    def _get_file_at_path(self, path: str) -> Tuple[PurePosixPath, Filesystem]:
        path_obj = PurePosixPath(path)
        try:
            resource = self._files[path_obj]
        except KeyError:
            # Attempting to access a directory.
            # Walk through `path` in filesystem.
            current_level = self._filesystem
            try:
                for part in path_obj.parts:
                    # Root directory does not exist in internal representation
                    # of filesystem.
                    if part == "/":
                        continue
                    current_level = current_level[PurePosixPath(part)]
            except KeyError:
                raise ResourceNotFound(path)

            # At this point, a valid "file" should be stored in `current_level`.
            resource = current_level

        return (path_obj, resource)

    def getinfo(
        self, path: str, namespaces: Optional[Collection[str]] = None
    ) -> Info:
        path = self.validatepath(path)
        # TODO: Support namespaces other than 'basic'.
        if namespaces is None:
            namespaces = ["basic"]

        # XXX: Just for now, raise error when unsupported namespace
        # encountered.
        for namespace in namespaces:
            if namespace != "basic":
                raise NotImplementedError(
                    "TODO: What to do about unsupported namespaces?"
                )

        path_obj, resource = self._get_file_at_path(path)

        raw_info = {
            "basic": {
                # Special-case root-dir.
                "name": "/" if path == "/" else path_obj.name,
                "is_dir": path == "/"
                # Resource is a directory if it suffixes include '.d' or '.c'.
                or len(set((".d", ".c")) & set(path_obj.suffixes)) > 0,
            }
        }
        return Info(raw_info)

    def listdir(self, path: str) -> List[str]:
        path = self.validatepath(path)
        info = self.getinfo(path)
        if not info.is_dir:
            raise DirectoryExpected(path)
        path_obj, resource = self._get_file_at_path(path)
        local_files = [str(filename) for filename in resource.keys()]
        return local_files

    def makedir(
        self,
        path: str,
        permissions: Optional[Permissions] = None,
        recreate: bool = False,
    ) -> SubFS[FS]:
        raise Unsupported(msg="cannot modify pyfs")

    def openbin(
        self, path: str, mode: str = "r", buffering: int = -1, **options: Any
    ) -> BinaryIO:
        path = self.validatepath(path)
        info = self.getinfo(path)
        if not info.is_file:
            raise FileExpected(path)
        if "w" in mode:
            raise Unsupported(msg="cannot modify pyfs")
        if "x" in mode:
            raise Unsupported(msg="cannot get exclusive control of resource")
        _, resource = self._get_file_at_path(path)
        return BytesIO(
            bytes(
                cast(Scope, resource).get_code(include_prefix=False),
                encoding="utf-8",
            )
        )

    def remove(self, path: str) -> None:
        raise Unsupported(msg="cannot modify pyfs")

    def removedir(self, path: str) -> None:
        raise Unsupported(msg="cannot modify pyfs")

    def setinfo(self, path: str, info: RawInfo) -> None:
        raise Unsupported(msg="cannot modify pyfs")
