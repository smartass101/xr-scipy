from __future__ import absolute_import, division, print_function

from textwrap import dedent
import pytest

from xrscipy import docs


def example_func(a, b):
    """
    An example of function.

    This is just an example.

    Parameters
    ----------
    a : int
        An example argument.
    b : float
        Another example argument

    Note
    ----
    This is a note

    See Also
    --------
    see xrscipy.docs
    """
    pass


def test_doc_parser():
    parser = docs.DocParser(example_func.__doc__)
    assert repr(parser) == dedent(example_func.__doc__)

    parser.replace_param('a', 'c : int\n    Replaced parameter.\n')
    print(parser)
    raise ValueError