"""Top level API.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from ._version import __version__

# handy in ipython maybe ?
# from .errors import ConfigError
from .globalconfig import GlobalConfig  # type: ignore # noqa: F401

# from .pmac import Pmac
# from .webpage import WebPage

__all__ = ["__version__"]
