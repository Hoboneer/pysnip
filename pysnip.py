#!/usr/bin/env python
import argparse
from itertools import chain

import fs
import parso


def get_parser():
    parser = argparse.ArgumentParser(
        description="get snippets of Python code in the command line"
    )
    parser.add_argument(
        "-s",
        "--scope",
        default=".",
        help="the dotted scopes containing the identifiers to find",
    )
    parser.add_argument(
        "-t",
        "--type",
        default=None,
        help="the type of statement (e.g., classdef)",
    )
    parser.add_argument("identifier", help="the identifier to search for")
    # The files are searched as if they are the root of the scopes.
    # Any imports will be followed (?).
    parser.add_argument(
        "files", nargs="+", help="files to search in separately"
    )

    return parser


def get_scopes(dotted_name):
    if dotted_name == ".":
        return []
    return dotted_name.split(".")


def match_scopes(scope_ident, scopes):
    # Returns the nearest `Scope` that has the name `scope`.
    for scope in scopes:
        if scope.name.value == scope_ident:
            return scope
    raise NotImplementedError("TODO: error handling for `match_scopes`")


def find_ident_in_scope(program, identifier, scopes, type_):
    # Returns code of identifier(s) found in correct scope.

    # Visit every node to get to specified scope.
    code_path = program
    if len(scopes) > 0:
        for scope in scopes:
            funcdefs = code_path.iter_funcdefs()
            classdefs = code_path.iter_classdefs()
            code_path = match_scopes(scope, chain(funcdefs, classdefs))

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
            yield ident_def.get_code(include_prefix=False)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    scopes = get_scopes(args.scope)
    programs = []
    with fs.open_fs(".") as disk:
        for file in args.files:
            programs.append(parso.parse(disk.gettext(file)))

    for program in programs:
        code_texts = find_ident_in_scope(
            program, args.identifier, scopes, args.type
        )
        for code in code_texts:
            print(code)
