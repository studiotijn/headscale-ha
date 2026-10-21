"""Print one app option for the s6 run scripts: `python3 -m hsha.opt <key>`.

Reads /data/options.json directly (with the app's defaults), so the services do
not depend on the Supervisor API being reachable. Booleans print true/false.
"""

from __future__ import annotations

import sys

from .options import load


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 -m hsha.opt <key>", file=sys.stderr)
        return 2
    value = load().raw.get(argv[1])
    if isinstance(value, bool):
        print("true" if value else "false")
    elif value is None:
        return 1
    else:
        print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
