#!/usr/bin/env python3

def vprint(message, ident, verbose):
    """Verbose print help function."""
    if verbose:
        print(";; {}: {}".format(ident, message))
