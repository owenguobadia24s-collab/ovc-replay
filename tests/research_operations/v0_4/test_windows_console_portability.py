from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from ovc.research_operations.v0_4.platform_metrics import memory_total_bytes, peak_rss_bytes

ROOT = Path(__file__).resolve().parents[3]


class WindowsResearchConsolePortabilityTests(unittest.TestCase):
    def test_rc_g5_import_chain_does_not_require_resource_module(self) -> None:
        code = """
import sys
sys.modules['resource'] = None
import apps.research_console.ro4_active_projection_source
import ovc.research_operations.v0_4
print('RC_WINDOWS_IMPORT_OK')
"""
        env = dict(os.environ)
        python_path = [str(ROOT), str(ROOT / "src")]
        if env.get("PYTHONPATH"):
            python_path.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(python_path)
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("RC_WINDOWS_IMPORT_OK", completed.stdout)

    def test_host_metrics_are_positive(self) -> None:
        self.assertGreater(memory_total_bytes(), 0)
        self.assertGreater(peak_rss_bytes(), 0)

    @unittest.skipUnless(sys.platform == "win32", "Windows-specific host metric probe")
    def test_native_windows_metric_probe_is_available(self) -> None:
        self.assertGreater(memory_total_bytes(), 0)
        self.assertGreater(peak_rss_bytes(), 0)


if __name__ == "__main__":
    unittest.main()
