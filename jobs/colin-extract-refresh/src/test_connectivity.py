import sys

from checks.check_business import run_check as run_business_check
from checks.check_colin import run_check as run_colin_check

def main() -> int:
    print("== running test_connectivity.py ==")
    run_business_check()
    run_colin_check()
    print("== done test_connectivity.py ==")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[test-connectivity] failed: {exc}", file=sys.stderr)