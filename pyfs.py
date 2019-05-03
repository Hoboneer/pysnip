from fs.base import FS
from fs.info import Info
from fs import open_fs
import parso

from itertools import chain
# TODO: Should imports be implemented? Should they be directories in this
# filesystem?


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

    def __init__(self, filename, language_version="3.6"):
        super().__init__()
        with open_fs(filename) as fs:
            self._program = parso.parse()
        # The filesystem representation of the program.
        self._files = {}

    def _build_filesystem(self):
        code_tree = self._program.get_root_node()
        funcdefs = code_tree.iter_funcdefs()
        classdefs = code_tree.iter_classdefs()
        for scopedef in chain(funcdefs, classdefs):
            extension = scopedef.type  # 'funcdef', or 'classdef'.



    # Should the filesystem be prebuilt, such that the code can assume the
    # filesystem is complete? (make it work then make it work fast!)

    def _path_to_scopes(self, path):
        # Converts some filesystem path to list of scopes.
        if path == "/":
            return []
        scopes = path.split("/")
        return scopes

    def _match_scopes(self, scope_ident, scopes):
        # Returns the nearest `Scope` that has the name `scope`.
        for scope in scopes:
            if scope.name.value == scope_ident:
                return scope
        raise NotImplementedError("TODO: error handling for `match_scopes`")

    def _find_ident_in_scope(self, identifier, scopes, type_=None):
        # Returns parso tree of identifier(s) found in correct scope.

        # Visit every node to get to specified scope. Empty `scopes` means the toplevel scope is checked.
        code_path = self._program
        if len(scopes) > 0:
            for scope in scopes:
                funcdefs = code_path.iter_funcdefs()
                classdefs = code_path.iter_classdefs()
                code_path = self._match_scopes(
                    scope, chain(funcdefs, classdefs)
                )

        if type_ == "classdef":
            defs = code_path.iter_classdefs()
        elif type_ == "funcdef":
            defs = code_path.iter_funcdefs()
        else:
            # No type specified.
            classdefs = code_path.iter_classdefs()
            funcdefs = code_path.iter_funcdefs()
            defs = chain(classdefs, funcdefs)

        for ident_def in defs:
            if ident_def.name.value == identifier:
                yield ident_def

    def getinfo(self, path, namespaces=None):
        # TODO: Support namespaces other than 'basic'.
        if namespaces is None:
            namespaces = ["basic"]

        # XXX: Just for now, raise error when unsupported namespace encountered.
        for namespace in namespaces:
            if namespace != "basic":
                raise NotImplementedError(
                    "TODO: What to do about unsupported namespaces?"
                )
        *scopes, ident_and_type = self._path_to_scopes(path)
        identifier, type_ = ident_and_type.split(".")
        # Get the first one found.
        definition = next(
            self._find_ident_in_scope(identifier, scopes, type_), None
        )
        if definition is None:
            raise NotImplementedError(
                "TODO: Implement handling of not-found definition"
            )

        raw_info = {"basic": {"name": identifier, "is_dir": False}}
        return Info(raw_info)

    def listdir(self, path):

        pass
