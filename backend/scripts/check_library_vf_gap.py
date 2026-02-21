"""Check why Library has 1277 but VF only has 1055."""
from pathlib import Path
from collections import Counter

LIBRARY_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")

# 1. Check for duplicates in library
print("=== Library Analysis ===")
all_files = list(LIBRARY_PATH.glob("*.md"))
print(f"Total MD files: {len(all_files)}")

# Check for exact filename duplicates
filenames = [f.name for f in all_files]
filename_counts = Counter(filenames)
duplicates = {k: v for k, v in filename_counts.items() if v > 1}
if duplicates:
    print(f"Duplicate filenames: {len(duplicates)}")
    for name, count in list(duplicates.items())[:5]:
        print(f"  {name}: {count}")
else:
    print("No duplicate filenames")

# 2. Check file sizes (empty or near-empty files?)
empty_files = []
small_files = []
for f in all_files:
    size = f.stat().st_size
    if size == 0:
        empty_files.append(f.name)
    elif size < 500:  # Less than 500 bytes
        small_files.append((f.name, size))

print(f"\nEmpty files (0 bytes): {len(empty_files)}")
print(f"Very small files (<500 bytes): {len(small_files)}")
if small_files[:3]:
    for name, size in small_files[:3]:
        print(f"  {name}: {size} bytes")

# 3. Check year distribution from filenames
print("\n=== Year Distribution (from filenames) ===")
years = {}
no_year = []
for f in all_files:
    # Try to extract year from filename pattern: Author_YYYY_...
    parts = f.stem.split('_')
    found_year = None
    for p in parts:
        if p.isdigit() and len(p) == 4 and 1990 <= int(p) <= 2030:
            found_year = int(p)
            break
    if found_year:
        years[found_year] = years.get(found_year, 0) + 1
    else:
        no_year.append(f.name)

print(f"Files with extractable year: {sum(years.values())}")
print(f"Files without year in filename: {len(no_year)}")
if no_year[:5]:
    print("  Examples without year:")
    for n in no_year[:5]:
        print(f"    {n[:60]}")

print("\nRecent years:")
for y in sorted(years.keys(), reverse=True)[:10]:
    print(f"  {y}: {years[y]} papers")
