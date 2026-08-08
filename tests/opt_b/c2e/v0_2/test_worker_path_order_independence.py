import os
from pathlib import Path
import subprocess
import sys
import unittest

from ovc.opt_b.c2e_v2.serialization import canonical_bytes

ROOT = Path(__file__).resolve().parents[4]


class C2E2WP5WorkerOrderTests(unittest.TestCase):
    def test_dict_and_input_order_is_canonical(self):
        self.assertEqual(canonical_bytes({"b":2,"a":1}), canonical_bytes({"a":1,"b":2}))

    def test_varied_pythonhashseed_has_identical_logical_bytes(self):
        code = "from ovc.opt_b.c2e_v2.serialization import canonical_bytes; print(canonical_bytes({'b':2,'a':1}).hex())"
        values = []
        for seed in ("1","7","999"):
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = seed
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + existing if existing else "")
            values.append(subprocess.check_output([sys.executable,"-c",code],env=env,cwd=str(ROOT),text=True).strip())
        self.assertEqual(len(set(values)), 1)


if __name__ == "__main__":
    unittest.main()
