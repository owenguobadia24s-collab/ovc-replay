"""Research Console vNext maintained unittest surface.

Canonical discovery starts at ``tests`` with ``PYTHONPATH=src``.  The Console
suite also imports the repository-owned ``apps`` package, so entering this test
package must make the repository root visible without changing production
package resolution or weakening the exact maintained test surface.
"""

from pathlib import Path
import sys


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_repository_root_text = str(_REPOSITORY_ROOT)
if _repository_root_text not in sys.path:
    sys.path.insert(0, _repository_root_text)
