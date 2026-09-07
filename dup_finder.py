#!/usr/bin/env python3
"""
dup_finder.py

A CLI tool to find duplicate files in a directory by comparing file content
(not just filenames), and optionally delete the extra copies.

Strategy (fast approach):
  1. Group files by size first (files of different sizes can't be identical).
  2. Only compute a SHA-256 hash for files that share a size with at least
     one other file — this avoids hashing every file in large directories.
  3. Files with the same size AND the same hash are true duplicates.

Supports:
  - Recursive directory scanning
  - Reporting duplicate groups and total wasted space
  - Deleting duplicates (keeping one copy per group), with dry-run mode
  - JSON output for scripting/automation

Usage examples:
  # Just report duplicates
  python dup_finder.py ./my_folder

  # Recursive scan
  python dup_finder.py ./my_folder --recursive

  # Preview what would be deleted, without deleting anything
  python dup_finder.py ./my_folder --delete --dry-run

  # Actually delete duplicates, keeping the oldest file in each group
  python dup_finder.py ./my_folder --delete --keep oldest

  # Output as JSON
  python dup_finder.py ./my_folder --json
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

CHUNK_SIZE = 65536  # 64KB chunks for hashing, keeps memory usage low on large files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find (and optionally delete) duplicate files in a directory."
    )
    parser.add_argument(
        "directory", type=str, help="Path to the directory to scan"
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Scan subdirectories as well"
    )
    parser.add_argument(
        "--delete", action="store_true",
        help="Delete duplicate files, keeping one copy per group",
    )
    parser.add_argument(
        "--keep", type=str, choices=["first", "oldest", "newest"], default="first",
        help="Which file to keep in each duplicate group when using --delete (default: first)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview deletions without actually deleting anything (use with --delete)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    parser.add_argument(
        "--min-size", type=int, default=0,
        help="Ignore files smaller than this many bytes (default: 0, no minimum)",
    )
    return parser.parse_args()


def get_files(directory: Path, recursive: bool):
    if recursive:
        return [p for p in directory.rglob("*") if p.is_file()]
    return [p for p in directory.iterdir() if p.is_file()]


def hash_file(path: Path) -> str:
    """Compute the SHA-256 hash of a file's contents, reading in chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def find_duplicates(directory: Path, recursive: bool, min_size: int):
    """
    Returns a list of duplicate groups. Each group is a list of Path objects
    that all have identical content (same size AND same SHA-256 hash).
    """
    files = get_files(directory, recursive)

    # Step 1: group by size (cheap, no hashing needed yet)
    size_groups = defaultdict(list)
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            continue  # skip files we can't read (permissions, broken symlink, etc.)
        if size < min_size:
            continue
        if size == 0:
            continue  # empty files aren't meaningful duplicates
        size_groups[size].append(path)

    # Step 2: only hash files that share a size with at least one other file
    hash_groups = defaultdict(list)
    for size, paths in size_groups.items():
        if len(paths) < 2:
            continue  # unique size, can't be a duplicate, skip hashing entirely
        for path in paths:
            try:
                file_hash = hash_file(path)
            except OSError:
                continue
            hash_groups[(size, file_hash)].append(path)

    # Step 3: keep only groups with 2+ files (true duplicates)
    duplicate_groups = [paths for paths in hash_groups.values() if len(paths) > 1]
    return duplicate_groups


def choose_keeper(group: list, strategy: str) -> Path:
    if strategy == "oldest":
        return min(group, key=lambda p: p.stat().st_mtime)
    if strategy == "newest":
        return max(group, key=lambda p: p.stat().st_mtime)
    return group[0]  # "first"


def print_report(duplicate_groups: list):
    if not duplicate_groups:
        print("No duplicate files found.")
        return

    total_wasted = 0
    print(f"Found {len(duplicate_groups)} group(s) of duplicate files:\n")

    for i, group in enumerate(duplicate_groups, start=1):
        size = group[0].stat().st_size
        wasted = size * (len(group) - 1)
        total_wasted += wasted

        print(f"Group {i} ({len(group)} files, {size:,} bytes each):")
        for path in group:
            print(f"  {path}")
        print()

    print(f"Total wasted space: {total_wasted:,} bytes ({total_wasted / (1024 * 1024):.2f} MB)")


def print_json(duplicate_groups: list):
    output = []
    for group in duplicate_groups:
        size = group[0].stat().st_size
        output.append({
            "size_bytes": size,
            "count": len(group),
            "files": [str(p) for p in group],
        })
    print(json.dumps(output, indent=2))


def delete_duplicates(duplicate_groups: list, keep_strategy: str, dry_run: bool):
    total_deleted = 0
    total_freed = 0

    for i, group in enumerate(duplicate_groups, start=1):
        keeper = choose_keeper(group, keep_strategy)
        to_delete = [p for p in group if p != keeper]
        size = keeper.stat().st_size

        print(f"Group {i}: keeping {keeper}")
        for path in to_delete:
            if dry_run:
                print(f"  [DRY RUN] would delete: {path}")
            else:
                try:
                    path.unlink()
                    print(f"  Deleted: {path}")
                    total_deleted += 1
                    total_freed += size
                except OSError as e:
                    print(f"  Error deleting {path}: {e}")

    if dry_run:
        print("\nDry run only — no files were deleted. Remove --dry-run to apply.")
    else:
        print(f"\nDone. {total_deleted} file(s) deleted, {total_freed:,} bytes freed "
              f"({total_freed / (1024 * 1024):.2f} MB).")


def main():
    args = parse_args()
    directory = Path(args.directory).expanduser().resolve()

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory.")
        sys.exit(1)

    duplicate_groups = find_duplicates(directory, args.recursive, args.min_size)

    if args.json:
        print_json(duplicate_groups)
    else:
        print_report(duplicate_groups)

    if args.delete:
        if not duplicate_groups:
            return
        print()
        delete_duplicates(duplicate_groups, args.keep, args.dry_run)


if __name__ == "__main__":
    main()
