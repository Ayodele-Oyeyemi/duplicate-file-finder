# Duplicate File Finder

A simple, dependency-free Python CLI tool that finds duplicate files by
comparing their **actual content** (not just filenames), and optionally
deletes the extras.

## Features

- ✅ Finds true duplicates by content, using SHA-256 hashing
- ✅ Fast by design: files are grouped by size first, and only hashed if
  another file shares that size avoids wastefully hashing every file
- ✅ Recursive scanning (include subfolders)
- ✅ Reports duplicate groups and total wasted disk space
- ✅ Optional deletion, keeping one copy per group (`first`, `oldest`, or `newest`)
- ✅ **Dry-run mode** — preview exactly what would be deleted before anything happens
- ✅ JSON output for scripting

## Requirements

- Python 3.7+
- No external dependencies

## Usage

```bash
python dup_finder.py <directory> [options]
```

### Options

| Flag          | Description                                                          |
|---------------|------------------------------------------------------------------------|
| `--recursive` | Scan subdirectories as well                                            |
| `--delete`    | Delete duplicate files, keeping one copy per group                     |
| `--keep`      | Which file to keep when deleting: `first`, `oldest`, `newest` (default: `first`) |
| `--dry-run`   | Preview deletions without deleting anything (use with `--delete`)      |
| `--json`      | Output results as JSON instead of a plain-text report                  |
| `--min-size`  | Ignore files smaller than this many bytes (default: `0`)               |

### Examples

**Just report duplicates:**
```bash
python dup_finder.py ./my_folder
```
```
Found 1 group(s) of duplicate files:

Group 1 (2 files, 13 bytes each):
  ./my_folder/file2.txt
  ./my_folder/file1.txt

Total wasted space: 13 bytes (0.00 MB)
```

**Recursive scan:**
```bash
python dup_finder.py ./my_folder --recursive
```

**Preview a deletion (always do this first!):**
```bash
python dup_finder.py ./my_folder --delete --dry-run
```

**Actually delete duplicates, keeping the oldest file in each group:**
```bash
python dup_finder.py ./my_folder --delete --keep oldest
```

**Ignore small files (e.g. under 1KB):**
```bash
python dup_finder.py ./my_folder --min-size 1024
```

**JSON output:**
```bash
python dup_finder.py ./my_folder --json
```

## How it works (the "fast approach")

Comparing every file against every other file byte-by-byte would be slow on
large directories. Instead:

1. **Group by file size first** — two files can't be identical if they're
   different sizes, so this is a free first filter.
2. **Hash only files that share a size** with at least one other file —
   unique-sized files are skipped entirely, since they can't have a duplicate.
3. **Compare SHA-256 hashes** within each size group, matching hash +
   matching size means the files are content-identical duplicates.

This means directories full of uniquely-sized files (the common case) get
scanned almost instantly, since no hashing is needed at all.

## Safety notes

- **Always run `--delete --dry-run` first** to see exactly what would be
  removed before committing to it.
- Empty files (0 bytes) are ignored — they're not meaningful duplicates and
  there would be too many false positives.
- Deletion is permanent (not moved to trash/recycle bin) — back up anything
  important first.

## Running tests

```bash
python -m unittest discover tests
```