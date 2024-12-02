import subprocess
import sys

from dls_pmacanalyse import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "dls_pmacanalyse", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
