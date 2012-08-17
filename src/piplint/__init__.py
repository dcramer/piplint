"""
piplint
~~~~~~~

:copyright: 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import re
import sys
from pkg_resources import parse_version
from subprocess import Popen, PIPE


def check_requirements(requirement_files, strict=False, venv=None):
    """
    Given a list of requirements files, checks them against the installed
    packages in the currentl environment. If any are missing, or do not fit
    within the version bounds, exits with a code of 1 and outputs information
    about the missing dependency.
    """
    version_re = re.compile(r'^([^<>=\s#]+)\s*(>=|>|<|<=|==)?\s*([^<>=\s#]+)?(?:\s*#.*)?$')
    checkout_re = re.compile(r'[#@]')

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
            (url, rev, eggname) = checkout_re.split(line)
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

    for fname in requirement_files:
        with open(fname) as fp:
            for line in fp:
                line = line.strip()
                if not is_requirements_line(line):
                    continue

                listed_reqs.append(parse_package_line(line))

    unknown_reqs.update(set(r[0] for r in frozen_reqs).difference(set(r[0] for r in listed_reqs)))

    for r_package, r_compare, r_version, r_line in listed_reqs:
        if not strict:
            r_package = r_package.lower()
        found = False

        for package, _, version, line in frozen_reqs:
            if not strict:
                package = package.lower()
            if found:
                continue
            if package == r_package:
                if not valid_version(version, r_compare, r_version):
                    print "Requirement %r was found in virtualenv, but is not a valid version" % r_package
                    print "Found %r, but expected %r" % (line, r_line)
                    return 1

                found = True

        if not found:
            print "Requirement %r not found in virtualenv." % r_package
            print "You must correct your environment before committing (and running tests)."
            if unknown_reqs:
                print ""
                print "For debugging purposes, the following unrecognized requirements were found:"
                print ""
                print "\n".join(sorted(unknown_reqs))
            return 1

    return 0


def main():
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("--strict", dest="strict", action='store_true', default=False)
    parser.add_option("-E", "--environment", dest="venv", metavar="DIR",
                      default=None, help="virtualenv environment to check against")
    (options, file_list) = parser.parse_args()
    if not file_list:
        print "Usage: piplint <requirements.txt>"
        sys.exit(1)
    sys.exit(check_requirements(file_list, **options.__dict__))

if __name__ == '__main__':
    main()
