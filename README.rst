piplint
=======

Piplint validates your current environment with the requirements you've specified as being required. It will
ensure that any requirement listed exists within the environment, and within the bounds of the versions specified.

::

    source env/bin/activate
    piplint requirements/*.txt

You can also pass ``--strict`` if you want to enfoce things like case sensitivity on package names.