"""
piplint
~~~~~~~

:copyright: 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import argparse
import os
import re
from pkg_resources import parse_version
from subprocess import Popen, PIPE


class TextColours:
    def __init__(self, enabled=False):
        if enabled:
            self.enable()
        else:
            self.disable()

    def enable(self):
        self.OKGREEN = '\033[92m'
        self.WARNING = '\033[93m'
        self.FAIL = '\033[91m'
        self.ENDC = '\033[0m'

    def disable(self):
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


def check_requirements(requirement_files, strict=False, verbose=False,
        venv=None, do_colour=False):
    """
    Given a list of requirements files, checks them against the installed
    packages in the currentl environment. If any are missing, or do not fit
    within the version bounds, exits with a code of 1 and outputs information
    about the missing dependency.
    """
    colour = TextColours(do_colour)

    version_re = re.compile(r'^([^<>=\s#]+)\s*(>=|>|<|<=|==)?\s*([^<>=\s#]+)?(?:\s*#.*)?$')

    def parse_package_line(line):
        try:
            if line.startswith('-e'):
                return parse_checkout_line(line)
            package, compare, version = version_re.split(line)[1:-1]
        except ValueError:
            raise ValueError("Unknown package line format: %r" % line)
        return (package, compare or None, parse_version(version) if version else None, line)

    def parse_checkout_line(whole_line):
        """
        parse a line that starts with '-e'

        e.g.,
        -e git://github.com/jcrocholl/pep8.git@bb20999aefc394fb826371764146bf61d8e572e2#egg=pep8-dev
        """
        # Snip off the '-e' and any leading whitespace
        line = whole_line[2:].lstrip()

        # Check if there is a revision specified
        if '@' in line:
            url, last_bit = line.rsplit('@', 1)
            rev, eggname = last_bit.split('#', 1)
            return (url, '==', rev, line)
        else:
            (url, eggname) = line.split('#')
            return (url, None, None, line)

    def is_requirements_line(line):
        """
        line is a valid requirement in requirements file or pip freeze output
        """
        if not line:
            return False
        if line.startswith('#'):
            return False
        if line.startswith('-e'):
            return True
        if line.startswith('-'):
            return False
        if line.startswith('http://') or line.startswith('https://'):
            return False
        return True


    def valid_version(version, compare, r_version):
        if not all([compare, version]):
            return True
        if compare == '==':
            return version == r_version
        elif compare == '<=':
            return version <= r_version
        elif compare == '>=':
            return version >= r_version
        elif compare == '<':
            return version < r_version
        elif compare == '>':
            return version > r_version
        raise ValueError("Unknown comparison operator: %r" % compare)

    frozen_reqs = []
    unknown_reqs = set()
    listed_reqs = []
    args = 'pip freeze'
    if venv is not None:
        args = venv + "/bin/" + args
    freeze = Popen([args], stdout=PIPE, shell=True)
    for line in freeze.communicate()[0].splitlines():
        line = line.strip()
        if not is_requirements_line(line):
            unknown_reqs.add(line)
            continue
        frozen_reqs.append(parse_package_line(line))

    # Requirements files may include other requirements files;
    # if so, add to list.
    included_files = []
    for file in requirement_files:
        path = os.path.dirname(file)
        args = "grep '^\-r' %s" % file
        grep = Popen([args], stdout=PIPE, shell=True)
        for line in grep.communicate()[0].splitlines():
            included_files.append(os.path.join(path, line[2:].lstrip()))
    requirement_files.extend(included_files)

    for fname in requirement_files:
        with open(fname) as fp:
            for line in fp:
                line = line.strip()
                if not is_requirements_line(line):
                    continue

                listed_reqs.append(parse_package_line(line))

    unknown_reqs.update(set(r[0] for r in frozen_reqs).difference(set(r[0] for r in listed_reqs)))

    errors = []

    for r_package, r_compare, r_version, r_line in listed_reqs:
        r_package_lower = r_package.lower()
        found = False

        for package, _, version, line in frozen_reqs:
            if package.lower() == r_package_lower:
                found = True
                if strict and package != r_package:
                    unknown_reqs.remove(package)
                    errors.append(
                        "%sUnexpected capitalization found: %r is required but %r is installed.%s"
                        % (colour.WARNING, r_package, package, colour.ENDC)
                    )
                elif valid_version(version, r_compare, r_version):
                    unknown_reqs.discard(package)
                    if verbose:
                        print ("%sRequirement is installed correctly: %s%s"
                               % (colour.OKGREEN, r_line, colour.ENDC))
                else:
                    errors.append(
                        "%sUnexpected version of %r found: %r is required but %r is installed.%s"
                        % (colour.WARNING, r_package, r_line, line, colour.ENDC)
                    )
                break

        if not found:
            errors.append("%sRequirement %r not installed in virtualenv.%s"
                          % (colour.FAIL, r_package, colour.ENDC))

    if unknown_reqs:
        print "\nFor debugging purposes, the following packages are installed but not in the requirements file(s):"
        unknown_reqs_with_versions = []
        for unknown_req in unknown_reqs:
            for req in frozen_reqs:
                if unknown_req == req[0]:
                    unknown_reqs_with_versions.append(req[3])
                    break
        print "%s%s%s\n" % (colour.WARNING,
                            "\n".join(sorted(unknown_reqs_with_versions)),
                            colour.ENDC)

    if errors:
        print "Errors found:"
        print '\n'.join(errors)
        print "You must correct your environment before committing (and running tests).\n"
        return 1

    if not errors and not unknown_req:
        print ("%sNo errors found; all packages accounted for!%s"
               % (colour.OKGREEN, colour.ENDC))

    return 0


def main():

    cli_parser = argparse.ArgumentParser()
    cli_parser.add_argument('-c', '--colour', '--color', action='store_true',
                            help='coloured output')
    cli_parser.add_argument('-E', '--environment', dest='venv', metavar='DIR',
                            default=None,
                            help='virtualenv to check against')
    cli_parser.add_argument('-s', '--strict', action='store_true',
                            default=False,
                            help='strict matching of package names')
    cli_parser.add_argument('-v', '--verbose', action='store_true',
                            default=False, help='show status of all packages')
    cli_parser.add_argument('file', nargs='+',
                            help='requirements file(s), use `-` for stdin')
    cli_args = cli_parser.parse_args()

    # call the main function to kick off the real work
    check_requirements(cli_args.file, strict=cli_args.strict,
                       verbose=cli_args.verbose, venv=cli_args.venv,
                       do_colour=cli_args.colour,)


if __name__ == '__main__':
    main()
