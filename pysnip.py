#!/usr/bin/env python
import argparse
import re
import sys
from contextlib import suppress

import fs

from pyfs import PyCodeFS

# TODO: Match duplicate files when given an identifier to match.

# FIXME: The problem of the code treating local files as the identifier...
# Perhaps just make user do it? This only affects multiple files as args
# anyway.  Checking `identifier` for being a valid python identifer wouldn't
# work since `--regex` changes its meaning...

# TODO: Support setting the separator after each match.


def get_parser():
    parser = argparse.ArgumentParser(
        description="get snippets of Python code in the command line"
    )
    parser.add_argument(
        "-s",
        "--scope",
        default=".",
        # Allow a nicer name in the code.
        dest="path",
        type=get_scopes,
        help="the dotted scopes containing the identifiers to find (default: top-level/module scope)",
    )
    parser.add_argument(
        "-t",
        "--type",
        action="append",
        choices=("classdef", "funcdef"),
        help="the type of statement (e.g., a class definition)",
    )
    parser.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        help="find `identifier` in specified scope and all subscopes",
    )
    parser.add_argument(
        "-r",
        "--regex",
        action="store_true",
        default=False,
        help="find code that match a regular expression, specified by `identifier`",
    )
    # XXX: Perhaps this should be named "--delimiter" ("-d" short option) instead?
    parser.add_argument(
        "-S",
        "--separator",
        # This gets properly escaped later.
        default="\\n",
        help='separate matches with a sequence of characters (default: newline, "\\n")',
    )
    parser.add_argument("identifier", help="the identifier to search for")
    # The files are searched as if they are the root of the scopes.
    # Any imports will be followed (?) (TODO).
    parser.add_argument(
        "files", nargs="+", help="files to search in separately"
    )

    return parser


IDENTIFIER_PATT = re.compile("[A-Za-z_][A-Za-z0-9_]*")


def get_scopes(dotted_name: str) -> str:
    # Special-case top-level scope.
    if dotted_name == ".":
        return "/"

    parts = dotted_name.split(".")
    for part in parts:
        if not IDENTIFIER_PATT.fullmatch(part):
            raise argparse.ArgumentTypeError(
                f"'{part}' is an invalid python identifier"
            )
    return fs.path.join(*parts)


def scope_name_to_path(
    filesystem, scope_path, valid_types=("classdef", "funcdef")
):
    # Try get a valid filesystem path from a scope name (adds ".c" and scope type).
    for scope_type in valid_types:
        possible_path = f"{scope_path}.{scope_type}.c"
        if filesystem.exists(f"{scope_path}.{scope_type}.c"):
            return possible_path
    raise fs.errors.ResourceNotFound(possible_path)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    # The stdlib doesn't have 'necessarily inclusive'-type groups...
    if args.regex and args.identifier is None:
        raise NotImplementedError(
            "TODO: handle invalid option combination (regex but no identifier)"
        )

    if args.regex:
        regex = re.compile(args.identifier)

    # Empty `--type` arg means all types.
    if args.type is None:
        args.type = ["classdef", "funcdef"]

    # Make file patterns for walker.
    if args.regex or args.identifier is None:
        # Regex will be matched later OR all members of specified scope types will
        # be included.
        file_patterns = [f"*.{scope_type}" for scope_type in args.type]
    else:
        # Otherwise match literally
        file_patterns = [
            f"{args.identifier}.{scope_type}" for scope_type in args.type
        ]

    if args.recursive:
        recursion_depth = None
    else:
        recursion_depth = 1

    # Convert escape sequences to real characters (e.g., "\n" to newline char).
    output_separator = bytes(args.separator, encoding="utf-8").decode(
        "unicode-escape"
    )

    for filename in args.files:
        try:
            f = open(filename)
            program = PyCodeFS(f.read())
        except Exception:
            # TODO: Allow exception to be logged.
            print(
                f"Could not open '{filename}' for some reason. Skipping...",
                file=sys.stderr,
            )
            continue
        finally:
            f.close()

        # Skip programs if they don't have the specified scopes.
        with suppress(fs.errors.ResourceNotFound):
            # Root directory is already valid.
            if args.recursive and args.path != "/":
                path = scope_name_to_path(program, args.path)
            else:
                path = args.path

            for code_filename in program.walk.files(
                path, filter=file_patterns, max_depth=recursion_depth
            ):
                # Ignore the '.classdef' or '.funcdef' extension in match.
                filename, _ = fs.path.splitext(fs.path.basename(code_filename))

                # Skip if the basename (minus the extension) does not match regex.
                if args.regex and not regex.match(filename):
                    continue

                print(program.gettext(code_filename), end=output_separator)
