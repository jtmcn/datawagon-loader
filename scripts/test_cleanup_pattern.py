#!/usr/bin/env python3
"""Test the version suffix pattern matching logic."""

import re

# Same pattern from cleanup script
VERSION_SUFFIX_PATTERN = re.compile(r"_v\d+-\d+$")

test_cases = [
    # (folder_name, should_be_deleted, description)
    ("claim_raw", True, "No version suffix - OLD naming"),
    ("ownership_raw", True, "No version suffix - OLD naming"),
    ("claim_raw_v1-1", False, "Has version suffix - NEW naming"),
    ("claim_raw_v1-2", False, "Has version suffix - NEW naming"),
    ("claim_raw_v2-0", False, "Has version suffix - NEW naming"),
    ("asset_ownership_v1-1", False, "Has version suffix - NEW naming"),
    ("report", True, "No version suffix - OLD naming"),
    ("test_v1", True, "Incomplete version pattern - OLD naming"),
    ("test_v1-", True, "Incomplete version pattern - OLD naming"),
    ("test_1-1", True, "Missing 'v' prefix - OLD naming"),
]

print("Testing version suffix pattern matching:\n")
print(f"{'Folder Name':<30} {'Should Delete?':<15} {'Pattern Match':<15} {'Result'}")
print("=" * 80)

all_passed = True

for folder_name, should_delete, description in test_cases:
    has_version_suffix = bool(VERSION_SUFFIX_PATTERN.search(folder_name))
    would_delete = not has_version_suffix

    passed = would_delete == should_delete
    status = "✓ PASS" if passed else "✗ FAIL"

    if not passed:
        all_passed = False

    print(f"{folder_name:<30} {str(should_delete):<15} {str(has_version_suffix):<15} {status}")
    if not passed:
        print(f"  → Expected: delete={should_delete}, Got: delete={would_delete}")

print("=" * 80)
print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")

if all_passed:
    print("\n✓ Pattern matching logic is correct!")
    print("  - Folders WITH version suffix (_vX-Y) will be preserved")
    print("  - Folders WITHOUT version suffix will be deleted")
