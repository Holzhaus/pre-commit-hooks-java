#!/usr/bin/env python3
# Copyright (c) 2022 Jan Holthuis <jan.holthuis@ruhr-uni-bochum.de>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import argparse
import logging
import pathlib
import re
import typing

PACKAGE_STATEMENT_PATTERN = re.compile(r"package\s+(?P<name>\w+\.[\w\.]*\w+)\s*;")


class JavaPackageStatement(typing.NamedTuple):
    match: re.Match
    lineno: int

    @property
    def name(self) -> str:
        return self.match.group("name")

    @property
    def components(self) -> typing.Iterable[str]:
        return self.name.split(".")


def find_java_package_statement(
    path: pathlib.Path,
) -> typing.Optional[JavaPackageStatement]:
    logger = logging.getLogger(__name__)
    inside_comment = False
    with path.open(mode="r", encoding="utf8") as fp:
        for lineno, line in enumerate(fp):
            if "/*" in line:
                inside_comment = True

            if "*/" in line:
                inside_comment = False

            if inside_comment:
                continue

            if match := PACKAGE_STATEMENT_PATTERN.match(line):
                package_statement = JavaPackageStatement(match, lineno)
                logger.debug(
                    "%s:%d: Found package_statement '%s'",
                    str(path),
                    lineno,
                    package_statement.name,
                )
                return package_statement

    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check package statements in Java files."
    )
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
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.loglevel, format="%(message)s")

    result = 0
    for path in args.file:
        package_statement = find_java_package_statement(path)
        if package_statement is None:
            print(f"{path!s}: File does not have a package statement")
            result = 1
            continue

        package_components = tuple(package_statement.components)
        path_components = path.parent.parts
        if len(path_components) > len(package_components):
            path_components = path_components[-len(package_components) :]

        if package_components != path_components:
            print(
                f"{path!s}:{package_statement.lineno}: Package should be "
                f"{'.'.join(path_components)!r} but is {package_statement.name!r}"
            )
            result = 1

    return result
