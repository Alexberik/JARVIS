import tempfile
import unittest
from pathlib import Path

from backend.storage import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "test.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_task_lifecycle(self):
        task = self.store.add_task("Check JARVIS")
        self.assertEqual(len(self.store.list_tasks()), 1)
        toggled = self.store.toggle_task(task["id"])
        self.assertEqual(toggled["done"], 1)
        self.assertTrue(self.store.delete_task(task["id"]))
        self.assertEqual(self.store.list_tasks(), [])

    def test_memory_create_and_search(self):
        item = self.store.add_memory("Obsidian vault is local", "setup")
        self.assertEqual(self.store.list_memories("local")[0]["id"], item["id"])
        self.assertEqual(len(self.store.list_memories("missing")), 0)

    def test_empty_values_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add_task("  ")
        with self.assertRaises(ValueError):
            self.store.add_memory("  ")


if __name__ == "__main__":
    unittest.main()
