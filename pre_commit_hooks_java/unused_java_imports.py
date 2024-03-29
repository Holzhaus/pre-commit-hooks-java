#!/usr/bin/env python3
# Copyright (c) 2022 Jan Holthuis <jan.holthuis@ruhr-uni-bochum.de>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import argparse
import enum
import itertools
import logging
import pathlib
import re
import typing

IMPORT_PATTERN = re.compile(
    r"import\s+(?P<static>(?:static\s+)?)(?P<name>\w+\.[\w\.]*\w+)\s*;"
)


class RemovalReason(enum.Enum):
    DUPLICATE = 1
    UNUSED = 2


class JavaImport(typing.NamedTuple):
    match: re.Match
    lineno: int
    removal_reason: RemovalReason

    @property
    def name(self) -> str:
        return self.match.group("name")

    @property
    def is_static(self) -> bool:
        return bool(self.match.group("static"))

    @property
    def identifier(self) -> str:
        return self.name.rpartition(".")[2]


def find_unnecessary_imports(path: pathlib.Path) -> typing.Iterable[JavaImport]:
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
                java_import = JavaImport(match, lineno, RemovalReason.UNUSED)
                if (
                    first_import := unused_imports.get(java_import.identifier)
                ) is not None:
                    java_import = JavaImport(match, lineno, RemovalReason.DUPLICATE)
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


def lines_with_unnecessary_imports_removed(
    path: pathlib.Path, unnecessary_imports: typing.Iterable[JavaImport]
) -> typing.Iterable[str]:
    imports_by_lines = {
        k: list(v)
        for k, v in itertools.groupby(
            sorted(unnecessary_imports, key=lambda x: x.lineno),
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
        unnecessary_imports = list(find_unnecessary_imports(path))
        for unnecessary_import in unnecessary_imports:
            import_type = "static import" if unnecessary_import.is_static else "import"
            removal_reason = (
                "Unused"
                if unnecessary_import.removal_reason == RemovalReason.UNUSED
                else "Duplicate"
            )
            print(
                "%s:%d: %s %s '%s'"
                % (
                    str(path),
                    unnecessary_import.lineno,
                    removal_reason,
                    import_type,
                    unnecessary_import.name,
                )
            )

        if unnecessary_imports and args.fix:
            new_lines = list(
                lines_with_unnecessary_imports_removed(path, unnecessary_imports)
            )
            with path.open(mode="w+", encoding="utf8") as fp:
                fp.writelines(new_lines)
            logger.info(
                "%s: Wrote file with %d unnecessary imports removed",
                str(path),
                len(unnecessary_imports),
            )

    return 0
