"""A collection of small things to be shared

Note, that some doctests are added as smoketests to ensure that all
dependencies are imported and not forgotten.
"""

import os
import decorators
from collections import Counter


# -- Morph transforms -------------------
# All transforms should accept two arguments, first being an object to which
# a transform is applied. It could be ignored if not used by the code.

def to_int(_, x):
    """Attempts to convert a user-input string to int

    First argument is ignored since the function does not need self reference.
    Intended use:
    >>> _ = object()
    >>> to_int(_, "10")
    10
    >>> to_int(_, "0x0a")
    10

    Non-strings cause exceptions:
    >>> to_int(_, 10)  # doctest:+ELLIPSIS +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: ...
    """
    if isinstance(x, str):
        if x.startswith("0x"):
            return int(x, 16)
        return int(x)
    raise ValueError("Requires a string-like object")


# TODO: does this belong here?
def substitute_pc(other, x):
    """Replaces "pc" with an address pointed to by PC"""
    if isinstance(x, str):
        if x.lower() == "pc":
            return str(other.c.r.pc)
        return x
    # This should never happen because this is a strictly internal function.
    raise ValueError("Requires a string-like object")

# -- End morph transforms. -------------


@decorators.strict_precond("type(val) == int", ValueError, "argument must be an int")
@decorators.strict_precond("val >= 0", ValueError, "argument must be >= 0")
@decorators.strict_precond("val < 2**(4*width)", ValueError, "{val} does not fit in {width} chars")
def _printable_repr(val, width):
    """Internal helper to generate unsigned integers zero-padded representations

    Property: ∀ x, w ∈ N: len(_printable_repr(x, w)) == w
    >>> _printable_repr(10, 2)
    '0a'
    >>> _printable_repr(-10, 2)  # doctest:+ELLIPSIS +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: ...
    >>> _printable_repr(1000, 2)  # doctest:+ELLIPSIS +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: ...
    """
    return hex(val)[2:].zfill(width)


def byte(val):
    """Returns hex representation of val zero-padded to two characters

    >>> byte(10)
    '0a'
    >>> byte(1000)  # doctest:+ELLIPSIS +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: ...
    """
    return _printable_repr(val, 2)


def word(val):
    """Returns hex representation of val zero-padded to two characters

    >>> word(10)
    '000a'
    >>> word(1000)
    '03e8'
    >>> word(0x10000)  # doctest:+ELLIPSIS +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: ...
    """
    return _printable_repr(val, 4)


def byte_to_repr(val, asascii=False):
    """Converter which can return ASCII of a byte upon request

    Intended to be used for dumping memory areas with possible human readable
    strings in them.
    >>> byte_to_repr(10)
    '0a'
    >>> byte_to_repr(97)
    '61'
    >>> byte_to_repr(97, asascii=True)
    ' a'
    >>> byte_to_repr(10, asascii=True)
    '\\\\n'
    >>> len(byte_to_repr(10, asascii=True))
    2
    >>> byte_to_repr(8, asascii=True)
    '08'
    """
    if asascii and (32 < val < 127):
        return chr(val).rjust(2, " ")
    elif asascii and val in (9, 10, 13):
        # These are \t, \n and \r chars, everything else is better represented
        # as just bytes. Furthermore len(chr(10)) == 1, but it is printed out
        # as \n. In order not to confuse the dumper symbol representation
        # must be taken apart and '\' and 'n' returned as two individual
        # symbols.
        return repr(chr(val))[1:-1]
    return byte(val)


# TODO: does this belong here?
def mem_element(mem, addr, asascii=False):
    try:
        return byte_to_repr(mem.read(addr), asascii)
    except IndexError:
        return "NA"


def file_accessible(fname):
    """Checks if a file could be read

    >>> file_accessible(__file__)  # smoke test
    True
    """
    return os.path.exists(fname) and os.path.isfile(fname) and os.access(fname, os.R_OK)


hxs = set(("1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "a", "b", "c", "d", "e", "f"))
def is_hex(x):
    return all(y.lower() in hxs for y in x)


def is_return(char):
    return char == "\n"
