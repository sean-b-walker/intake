import json
import sys
from pathlib import Path

from hold import cited, settle
from letter import read_eml


def load_result(path):
    raw = path.read_text()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def problems_for(facts, expected, settled):
    card = settled["card"]
    problems = []

    if card["outcome"] != expected["outcome"]:
        problems.append(
            f"outcome: expected {expected['outcome']}, got {card['outcome']}"
        )
    if expected.get("ask") and card["ask"] != expected["ask"]:
        problems.append(f"ask: expected {expected['ask']}, got {card['ask']}")
    for flag in expected.get("flags", []):
        if flag not in settled["flags"]:
            problems.append(f"missing flag {flag}")
    if card["citation"] and not cited(facts, card):
        problems.append("citation was not in the email")
    if expected["outcome"] == "draft" and not card["citation"]:
        problems.append("draft slip has no citation")

    return problems


def main():
    live = "--live" in sys.argv
    root = Path(__file__).parent
    labels = json.loads((root / "labels.json").read_text())
    samples = sorted((root / "samples").glob("*.eml"))

    if live:
        from desk import ask, load_env

        load_env()
        print("live run")
    else:
        print("fixture run")

    passed = 0
    warned = 0
    failed = 0

    broken_facts = read_eml(root / "samples" / "absence.eml")
    for name in ("broken.json", "short.json"):
        result = load_result(root / "fixtures" / name)
        settled = settle(name, broken_facts, result)
        if settled["card"]["outcome"] == "person" and settled["errors"]:
            passed += 1
            print(f"PASS {name}: held")
        else:
            failed += 1
            print(f"FAIL {name}")
            print(json.dumps(settled["card"], indent=2))

    for path in samples:
        expected = labels.get(path.name)
        if expected is None:
            sys.exit(f"missing label for {path.name}")

        facts = read_eml(path)
        if live:
            result = ask(facts)
        else:
            result = load_result(root / "fixtures" / f"{path.stem}.json")

        settled = settle(path.name, facts, result)
        card = settled["card"]
        problems = problems_for(facts, expected, settled)

        if problems:
            failed += 1
            print(f"FAIL {path.name}")
            for problem in problems:
                print(f"- {problem}")
            print(json.dumps(card, indent=2))
        else:
            passed += 1
            print(f"PASS {path.name}: {card['outcome']}")

        model = settled["model"]
        if isinstance(model, dict) and model.get("outcome") != card["outcome"]:
            warned += 1
            print(f"WARN {path.name}: model said {model.get('outcome')}, held")

    total = len(samples) + 2
    print(f"\n{passed}/{total} slips matched; {warned} holds")
    if failed or passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
