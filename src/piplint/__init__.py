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


def check_requirements(requirement_files, strict=False):
    """
    Given a list of requirements files, checks them against the installed
    packages in the currentl environment. If any are missing, or do not fit
    within the version bounds, exits with a code of 1 and outputs information
    about the missing dependency.
    """
    version_re = re.compile(r'^([^<>=\s#]+)\s*(>=|>|<|<=|==)?\s*([^<>=\s#]+)?(?:\s*#.*)?$')

    def parse_package_line(line):
        try:
            package, compare, version = version_re.split(line)[1:-1]
        except ValueError:
            raise ValueError("Unknown package line format: %r" % line)
        return (package, compare or None, parse_version(version) if version else None, line)

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

    freeze = Popen(['pip freeze'], stdout=PIPE, shell=True)
    for line in freeze.communicate()[0].splitlines():
        line = line.strip()
        if not line or line.startswith('-'):
            unknown_reqs.add(line)
            continue
        frozen_reqs.append(parse_package_line(line))

    for fname in requirement_files:
        with open(fname) as fp:
            for line in fp:
                line = line.strip()
                if not line or line.startswith('-'):
                    continue

                listed_reqs.append(parse_package_line(line))

    unknown_reqs.update(set(r[0] for r in frozen_reqs).difference(set(r[0] for r in listed_reqs)))

    for r_package, r_compare, r_version, r_line in listed_reqs:
        if not strict:
            package = r_package.lower()
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
    (options, file_list) = parser.parse_args()
    if not file_list:
        print "Usage: piplint <requirements.txt>"
        sys.exit(1)
    sys.exit(check_requirements(file_list, **options.__dict__))

if __name__ == '__main__':
    main()
