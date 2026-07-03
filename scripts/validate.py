"""
Quran JSON Validator
Validates all translation files in data/ against the JSON schema,
checks verse counts, detects empty texts, and generates checksums.md5.
"""
import json
import sys
import hashlib
import argparse
from pathlib import Path

# Ensure UTF-8 output on all platforms (Windows cp1256 workaround)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema")
    sys.exit(1)

ROOT      = Path(__file__).parent.parent
DATA_DIR  = ROOT / "data"
SCHEMA    = ROOT / "schemas" / "translation-schema.json"
CHECKSUMS = ROOT / "checksums.md5"

AYAH_COUNTS = [
    7,286,200,176,120,165,206,75,129,109,
    123,111,43,52,99,128,111,110,98,135,
    112,78,118,64,77,227,93,88,69,60,
    34,30,73,54,45,83,182,88,75,85,
    54,53,89,59,37,35,38,29,18,45,
    60,49,62,55,78,96,29,22,24,13,
    14,11,11,18,12,12,30,52,52,44,
    28,28,20,56,40,31,50,40,46,42,
    29,19,36,25,22,17,19,26,30,20,
    15,21,11,8,8,19,5,8,8,11,
    11,8,3,9,5,4,7,3,6,3,5,4,5,6,
]
assert sum(AYAH_COUNTS) == 6236
TOTAL_VERSES = 6236
TOTAL_SURAHS = 114


def load_schema() -> dict:
    if not SCHEMA.exists():
        print(f"FATAL: Schema not found at {SCHEMA}")
        sys.exit(1)
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def md5(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def validate_file(path: Path, schema: dict) -> list[str]:
    """Validate a single translation file. Returns list of error strings."""
    errors = []
    lang = path.parent.name

    # 1. Load JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"[{lang}] Invalid JSON: {e}"]

    # 2. Schema validation
    validator = jsonschema.Draft7Validator(schema)
    schema_errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    for err in schema_errors[:10]:
        errors.append(f"[{lang}] Schema error at {list(err.path)}: {err.message}")
    if schema_errors:
        return errors  # No point continuing if schema fails

    # 3. Total verse count
    if len(data) != TOTAL_VERSES:
        errors.append(f"[{lang}] Expected {TOTAL_VERSES} verses, got {len(data)}")

    # 4. Sequential IDs
    for i, verse in enumerate(data, 1):
        if verse["id"] != i:
            errors.append(f"[{lang}] Non-sequential ID at position {i}: got id={verse['id']}")
            break

    # 5. All 114 surahs present
    surahs_present = set(v["surah"] for v in data)
    missing_surahs = set(range(1, 115)) - surahs_present
    if missing_surahs:
        errors.append(f"[{lang}] Missing surahs: {sorted(missing_surahs)}")

    # 6. Per-surah ayah counts
    by_surah: dict[int, int] = {}
    for v in data:
        by_surah[v["surah"]] = by_surah.get(v["surah"], 0) + 1
    wrong_counts = [
        (s, by_surah.get(s, 0), AYAH_COUNTS[s - 1])
        for s in range(1, 115)
        if by_surah.get(s, 0) != AYAH_COUNTS[s - 1]
    ]
    for surah, got, expected in wrong_counts[:10]:
        errors.append(f"[{lang}] Surah {surah}: expected {expected} ayahs, got {got}")

    # 7. No empty or whitespace-only text
    empty = [(v["surah"], v["ayah"]) for v in data if not v.get("text", "").strip()]
    if empty:
        errors.append(f"[{lang}] Empty/whitespace text in {len(empty)} verse(s): {empty[:5]}")

    # 8. No duplicate (surah, ayah) pairs
    seen: set[tuple] = set()
    duplicates = []
    for v in data:
        key = (v["surah"], v["ayah"])
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    if duplicates:
        errors.append(f"[{lang}] Duplicate verse(s): {duplicates[:5]}")

    return errors


def run(strict: bool = True) -> bool:
    schema = load_schema()

    json_files = sorted(DATA_DIR.glob("*/quran_*.json"))
    if not json_files:
        print(f"ERROR: No translation files found in {DATA_DIR}")
        sys.exit(1)

    print(f"Validating {len(json_files)} translation file(s)...\n")

    all_passed = True
    checksums: list[str] = []

    for path in json_files:
        lang = path.parent.name
        errors = validate_file(path, schema)

        if errors:
            all_passed = False
            print(f"❌  {path.name}")
            for err in errors:
                print(f"    {err}")
        else:
            digest = md5(path)
            checksums.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
            print(f"✅  {path.name}  ({path.stat().st_size // 1024} KB)  md5:{digest[:12]}…")

    print()

    # Write checksums only for files that passed
    if checksums:
        CHECKSUMS.write_text("\n".join(checksums) + "\n", encoding="utf-8")
        print(f"✓ checksums.md5 updated ({len(checksums)} file(s))")

    if all_passed:
        print("\n✅  All files passed validation.")
        return True
    else:
        print("\n❌  Validation failed. See errors above.")
        if strict:
            sys.exit(1)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Quran translation JSON files")
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Return exit code 0 even on failure (for local testing)",
    )
    args = parser.parse_args()
    run(strict=not args.no_strict)
