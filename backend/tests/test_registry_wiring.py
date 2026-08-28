import subprocess
import sys


def test_importing_app_alone_populates_the_registry():
    """Guards against rules only registering because some other test module
    happened to import them first in the same process."""
    code = (
        "from backend.audit.base import registry\n"
        "import backend.app\n"
        "assert registry.get_all(), 'registry is empty after importing backend.app alone'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
