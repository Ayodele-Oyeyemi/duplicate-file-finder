"""
Tests for dup_finder.py.

Run with:
    python -m unittest discover tests
or:
    python tests/test_dup_finder.py
"""

import sys
import tempfile
import shutil
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dup_finder import find_duplicates, hash_file, choose_keeper


class TestDupFinder(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def write(self, name: str, content: str) -> Path:
        path = self.tmp_dir / name
        path.write_text(content)
        return path

    def test_identical_content_detected_as_duplicate(self):
        self.write("a.txt", "hello world")
        self.write("b.txt", "hello world")
        self.write("c.txt", "something else")

        groups = find_duplicates(self.tmp_dir, recursive=False, min_size=0)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_different_content_not_duplicate(self):
        self.write("a.txt", "hello")
        self.write("b.txt", "world")

        groups = find_duplicates(self.tmp_dir, recursive=False, min_size=0)
        self.assertEqual(len(groups), 0)

    def test_same_size_different_content_not_duplicate(self):
        # Same length but different bytes -> different hash, not a duplicate.
        self.write("a.txt", "aaaaa")
        self.write("b.txt", "bbbbb")

        groups = find_duplicates(self.tmp_dir, recursive=False, min_size=0)
        self.assertEqual(len(groups), 0)

    def test_empty_files_ignored(self):
        self.write("a.txt", "")
        self.write("b.txt", "")

        groups = find_duplicates(self.tmp_dir, recursive=False, min_size=0)
        self.assertEqual(len(groups), 0)

    def test_recursive_scan(self):
        self.write("a.txt", "duplicate content")
        sub = self.tmp_dir / "subfolder"
        sub.mkdir()
        (sub / "b.txt").write_text("duplicate content")

        groups_non_recursive = find_duplicates(self.tmp_dir, recursive=False, min_size=0)
        self.assertEqual(len(groups_non_recursive), 0)

        groups_recursive = find_duplicates(self.tmp_dir, recursive=True, min_size=0)
        self.assertEqual(len(groups_recursive), 1)
        self.assertEqual(len(groups_recursive[0]), 2)

    def test_min_size_filter(self):
        self.write("a.txt", "hi")
        self.write("b.txt", "hi")

        groups = find_duplicates(self.tmp_dir, recursive=False, min_size=100)
        self.assertEqual(len(groups), 0)

    def test_hash_file_consistency(self):
        path = self.write("a.txt", "consistent content")
        hash1 = hash_file(path)
        hash2 = hash_file(path)
        self.assertEqual(hash1, hash2)

    def test_hash_file_differs_for_different_content(self):
        path1 = self.write("a.txt", "content one")
        path2 = self.write("b.txt", "content two")
        self.assertNotEqual(hash_file(path1), hash_file(path2))


class TestChooseKeeper(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_first_strategy(self):
        a = self.tmp_dir / "a.txt"
        b = self.tmp_dir / "b.txt"
        a.write_text("x")
        b.write_text("x")

        keeper = choose_keeper([a, b], "first")
        self.assertEqual(keeper, a)

    def test_oldest_strategy(self):
        a = self.tmp_dir / "a.txt"
        a.write_text("x")
        time.sleep(0.01)
        b = self.tmp_dir / "b.txt"
        b.write_text("x")

        keeper = choose_keeper([a, b], "oldest")
        self.assertEqual(keeper, a)

    def test_newest_strategy(self):
        a = self.tmp_dir / "a.txt"
        a.write_text("x")
        time.sleep(0.01)
        b = self.tmp_dir / "b.txt"
        b.write_text("x")

        keeper = choose_keeper([a, b], "newest")
        self.assertEqual(keeper, b)


if __name__ == "__main__":
    unittest.main()
