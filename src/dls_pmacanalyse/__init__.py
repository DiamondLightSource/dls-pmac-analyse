"""Top level API.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""
from ._version import __version__
from .errors import ConfigError
from .globalconfig import GlobalConfig
from .pmac import Pmac
from .webpage import WebPage

__all__ = ["__version__"]
