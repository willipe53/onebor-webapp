#!/usr/bin/env python3

from pathlib import Path
import collections
import statistics
import locale
import argparse

locale.setlocale(locale.LC_ALL, '')
report = {}
ranks = {}
pcts = {}
longest_name = 0
grand_total = 0
smallest_pct = 4

parser = argparse.ArgumentParser(
    description='Analyze React component and file sizes')
parser.add_argument('--all', action='store_true',
                    help='Process all of the data (show files with <4% of total)')
parser.add_argument('--components', action='store_true',
                    help='Focus on React components only (.tsx files)')
parser.add_argument('--services', action='store_true',
                    help='Focus on service files (.ts files)')
args = parser.parse_args()

if args.all:
    smallest_pct = 0

# Define the source directory (relative to scripts directory)
src_dir = Path("../src")

# Define file patterns based on arguments
file_patterns = []
if args.components:
    file_patterns = ["*.tsx"]
elif args.services:
    file_patterns = ["*.ts"]
else:
    # Default: analyze both .tsx and .ts files
    file_patterns = ["*.tsx", "*.ts"]

# Collect files
files_to_analyze = []
for pattern in file_patterns:
    files_to_analyze.extend(src_dir.rglob(pattern))

# Process files
for path in files_to_analyze:
    name = path.name
    folder = path.parent
    fullname = folder.joinpath(name)
    lines = 0

    try:
        with path.open(encoding='utf-8') as f:
            content = f.read()
            lines = len(content.splitlines())
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}")
        continue

    # Skip test files, generated files, and other non-essential files
    if any(skip in name.lower() for skip in ['.test.', '.spec.', '.stories.', '.generated.', '.d.ts']):
        continue

    # Create folder key (relative to src)
    folder_key = str(folder.relative_to(src_dir))
    if folder_key == ".":
        folder_key = "src"

    if folder_key not in report:
        report[folder_key] = {}

    report[folder_key][name] = lines
    ranks[name] = lines
    grand_total += lines

    if len(name) > longest_name:
        longest_name = len(name)

if grand_total == 0:
    print("No files found to analyze.")
    exit(1)

me = statistics.mean(ranks.values())

# Calculate ranks and percentages
rank = 0
sorted_ranks = sorted(ranks.items(), reverse=True, key=lambda item: item[1])
for k, v in sorted_ranks:
    rank += 1
    pcts[k] = round((v / grand_total) * 100)
    ranks[k] = rank

# Print report
for dir_name, file_list in report.items():
    print(f"\n{dir_name:<{longest_name+3}} Lines  Rank  Pct   Times the {round(me)} line average")
    total = 0

    for file_name, lines in collections.OrderedDict(sorted(file_list.items(), reverse=True, key=lambda item: item[1])).items():
        mean_mult = lines / me
        warning = f"{mean_mult:.1f}"

        if pcts[file_name] >= smallest_pct:
            print(
                f"  {file_name:<{longest_name}} {lines:>5d} {ranks[file_name]:>5d}  {pcts[file_name]:>3d}%      {warning}")
        total += lines

    dir_pct = round((total / grand_total) * 100)
    print(
        f"Total {dir_name:<{longest_name-4}} {total:>,d}        {dir_pct:>3d}%")

print(f"\n{'Grand Total':<{longest_name+2}} {grand_total:>,d}")

# Additional analysis
print(f"\nAnalysis Summary:")
print(f"Average file size: {round(me)} lines")
print(
    f"Largest file: {max(ranks.keys(), key=lambda k: ranks[k])} ({max(ranks.values())} lines)")
print(
    f"Files over 2x average: {len([f for f, lines in ranks.items() if lines > me * 2])}")
print(
    f"Files over 5x average: {len([f for f, lines in ranks.items() if lines > me * 5])}")

# Show largest files
print(f"\nTop 10 largest files:")
# Get original line counts, not ranks
line_counts = {}
for path in files_to_analyze:
    name = path.name
    if any(skip in name.lower() for skip in ['.test.', '.spec.', '.stories.', '.generated.', '.d.ts']):
        continue
    try:
        with path.open(encoding='utf-8') as f:
            content = f.read()
            lines = len(content.splitlines())
        line_counts[name] = lines
    except:
        continue

top_files = sorted(line_counts.items(), reverse=True,
                   key=lambda item: item[1])[:10]
for i, (filename, lines) in enumerate(top_files, 1):
    print(
        f"{i:2d}. {filename:<{longest_name}} {lines:>5d} lines ({pcts[filename]:>2d}% of total)")
