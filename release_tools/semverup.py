#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#

import datetime
import os
import re

import click
import semver

from release_tools.entry import (CategoryChange,
                                 read_changelog_entries,
                                 determine_changelog_entries_dirpath)
from release_tools.repo import GitHandler

"""
Script to increment the version number of a package.

It will bump up the version following the rules defined
by the semantic versioning specification.
"""

VERSION_FILE_TEMPLATE = (
    "# File auto-generated by semverup on {timestamp}\n"
    "__version__ = \"{version}\"\n"
)


@click.command()
@click.option('--dry-run', is_flag=True,
              help="Do not write a new version number. Print to the standard output instead.")
def semverup(dry_run):
    """Increment version number following semver specification.

    This script will bump up the version number of a package in a
    Git repository using semantic versioning.

    You will need to run this script inside that repository. The
    version number must be stored in any directory, under the name
    of '_version.py'. It must also be tracked in the repository.
    New version will be written in the same file. To increase the number
    properly, the script will get the type of every unreleased change
    stored under 'releases/unreleased' directory.

    WARNING: this script does not increases MAJOR version yet.

    If you don't want to create a new version and see only the final
    result, please active '--dry-run' flag.

    More info about semver specification can be found in the next
    link: https://semver.org/.
    """
    # Get the current version number
    filepath = find_version_file()
    current_version = read_version_number(filepath)

    # Determine the new version and produce the output
    new_version = determine_new_version_number(current_version)

    if not dry_run:
        write_version_number(filepath, new_version)

    click.echo(new_version)


def find_version_file():
    """Find the version file in the repository."""

    filepath = GitHandler().find_file('*_version.py')

    if not filepath:
        raise click.ClickException("version file not found")

    return filepath


def read_version_number(filepath):
    """Read the version number of the given file."""

    try:
        with open(filepath, 'r', encoding='utf-8') as fd:
            m = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                          fd.read(), re.MULTILINE)
            if not m:
                raise click.ClickException("version number not found")
            match = m.group(1)
    except FileNotFoundError:
        msg = "version file {} does not exist".format(filepath)
        raise click.ClickException(msg)

    try:
        version = semver.parse_version_info(match)
    except ValueError:
        msg = "version number '{}' in {} is not a valid semver string"
        msg = msg.format(match, filepath)
        raise click.ClickException(msg)

    return version


def determine_new_version_number(current_version):
    """Guess the next version number."""

    entries = read_unreleased_changelog_entries()

    bump_patch = False
    bump_minor = False

    for entry in entries.values():
        if entry.category != CategoryChange.FIXED:
            bump_minor = True
            break
        else:
            bump_patch = True

    next_version = None

    if bump_patch:
        next_version = current_version.bump_patch()
    if bump_minor:
        next_version = current_version.bump_minor()

    if not next_version:
        msg = "no changes found; version number not updated"
        raise click.ClickException(msg)

    return next_version


def read_unreleased_changelog_entries():
    """Returns entries stored in the unreleased changelog entries dir."""

    dirpath = determine_changelog_entries_dirpath()

    if not os.path.exists(dirpath):
        msg = "changelog entries directory {} does not exist.".format(dirpath)
        raise click.ClickException(msg)

    try:
        entries = read_changelog_entries(dirpath)
    except Exception as exc:
        raise click.ClickException(exc)

    return entries


def write_version_number(filepath, version):
    """Write version number to the given file."""

    values = {
        'timestamp': datetime.datetime.utcnow(),
        'version': version
    }
    stream = VERSION_FILE_TEMPLATE.format(**values)

    with open(filepath, mode='w') as fd:
        fd.write(stream)


if __name__ == '__main__':
    semverup()
