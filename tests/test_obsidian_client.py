import tempfile
import unittest
from pathlib import Path

from backend.obsidian_client import ObsidianClient


class ObsidianClientTests(unittest.TestCase):
    def test_rest_status_reports_missing_key_without_network_call(self):
        client = ObsidianClient({"mode": "rest", "rest": {"api_key": ""}})
        status = client.status()
        self.assertFalse(status["ok"])
        self.assertFalse(status["configured"])

    def test_filesystem_paths_stay_inside_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / "vault"
            vault.mkdir()
            client = ObsidianClient({
                "mode": "filesystem",
                "filesystem": {"vault_path": str(vault)},
            })
            client.write_note("JARVIS/Test.md", "hello")
            self.assertEqual(client.read_note("JARVIS/Test.md"), "hello")
            with self.assertRaises((ValueError, PermissionError)):
                client.read_note("../outside.md")


if __name__ == "__main__":
    unittest.main()
