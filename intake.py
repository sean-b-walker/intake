import json
import sys

from desk import ask, load_env
from hold import settle
from letter import read_eml


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 intake.py samples/absence.eml")

    load_env()

    path = sys.argv[1]
    facts = read_eml(path)
    result = ask(facts)
    settled = settle(path, facts, result)

    print(path)
    print(settled["card"]["outcome"])
    print(json.dumps(settled, indent=2))


if __name__ == "__main__":
    main()
