#!/usr/bin/env python3
# Copyright (c) 2022 Jan Holthuis <jan.holthuis@ruhr-uni-bochum.de>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import argparse
import itertools
import logging
import pathlib
import re
import typing

IMPORT_PATTERN = re.compile(
    r"import\s+(?P<static>(?:static\s+)?)(?P<name>\w+\.[\w\.]*\w+)\s*;"
)


class JavaImport(typing.NamedTuple):
    match: re.Match
    lineno: int

    @property
    def name(self) -> str:
        return self.match.group("name")

    @property
    def is_static(self) -> bool:
        return bool(self.match.group("static"))

    @property
    def identifier(self) -> str:
        return self.name.rpartition(".")[2]


def find_unused_imports(path: pathlib.Path) -> typing.Iterable[JavaImport]:
    logger = logging.getLogger(__name__)
    unused_imports: dict[str, JavaImport] = {}
    inside_comment = False
    with path.open(mode="r", encoding="utf8") as fp:
        for lineno, line in enumerate(fp):
            if "/*" in line:
                inside_comment = True

            if "*/" in line:
                inside_comment = False

            if inside_comment:
                continue

            if match := IMPORT_PATTERN.match(line):
                java_import = JavaImport(match, lineno)
                if (
                    first_import := unused_imports.get(java_import.identifier)
                ) is not None:
                    logger.debug(
                        "%s:%d: Found duplicate import '%s' "
                        "(already imported in line %d)",
                        str(path),
                        lineno,
                        java_import.name,
                        first_import.lineno,
                    )
                    yield java_import
                    continue

                unused_imports[java_import.identifier] = java_import
                if java_import.is_static:
                    logger.debug(
                        "%s:%d: Found static import '%s'",
                        str(path),
                        lineno,
                        java_import.name,
                    )
                else:
                    logger.debug(
                        "%s:%d: Found import '%s'", str(path), lineno, java_import.name
                    )
                continue

            for identifier, java_import in unused_imports.copy().items():
                if re.search(rf"\b{re.escape(identifier)}\b", line):
                    logger.debug(
                        "%s:%d: Import '%s' used here",
                        str(path),
                        lineno,
                        java_import.name,
                    )
                    del unused_imports[identifier]

        yield from unused_imports.values()


def lines_with_unused_imports_removed(
    path: pathlib.Path, unused_imports: typing.Iterable[JavaImport]
) -> typing.Iterable[str]:
    imports_by_lines = {
        k: list(v)
        for k, v in itertools.groupby(
            sorted(unused_imports, key=lambda x: x.lineno),
            key=lambda x: x.lineno,
        )
    }

    with path.open(mode="r", encoding="utf8") as fp:
        for lineno, line in enumerate(fp):
            imports_in_current_line = imports_by_lines.get(lineno, [])
            for java_import in imports_in_current_line:
                line = line.replace(java_import.match.group(0), "")
            if not imports_in_current_line or line.strip():
                yield line


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check Java imports.")
    parser.add_argument("file", nargs="+", type=pathlib.Path, help="file path(s)")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
        help="Be verbose",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Write file with unused imports removed"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.loglevel, format="%(message)s")

    logger = logging.getLogger(__name__)
    for path in args.file:
        unused_imports = list(find_unused_imports(path))
        for unused_import in unused_imports:
            import_type = "static import" if unused_import.is_static else "import"
            print(
                "%s:%d: Unused %s '%s'"
                % (str(path), unused_import.lineno, import_type, unused_import.name)
            )

        if unused_imports and args.fix:
            new_lines = list(lines_with_unused_imports_removed(path, unused_imports))
            with path.open(mode="w+", encoding="utf8") as fp:
                fp.writelines(new_lines)
            logger.info(
                "%s: Wrote file with %d unused imports removed",
                str(path),
                len(unused_imports),
            )

    return 0
