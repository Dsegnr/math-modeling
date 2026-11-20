"""Verify the published frozen payload against SHA256SUMS without modifying it."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent


def main():
    failures = []
    count = 0
    for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            failures.append(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(name)
        count += 1
    if failures:
        print('FAILED:', *failures, sep='\n')
        return 1
    print(f'OK: {count} frozen files verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
