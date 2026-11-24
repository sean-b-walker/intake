import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


root = Path(__file__).parent

dob_re = re.compile(
    r"\b(?:date of birth|dob)\b[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
    re.I,
)
student_re = re.compile(
    r"\bstudent (?:number|id|no\.?)\b[:\s#]*\d{4,}",
    re.I,
)
phone_re = re.compile(r"\b04\d{2}[\s-]?\d{3}[\s-]?\d{3}\b")
space_re = re.compile(r"\s+")

payment_bits = ("gift card", "bsb", "new account", "pay the", "bank detail")
credential_bits = ("password", "reset it", "one-time code", "login")
record_bits = ("other child", "another student", "class list")
welfare_bits = (
    "does not feel safe",
    "doesn't feel safe",
    "does not want to be here",
    "self-harm",
)
complaint_bits = ("complaint about", "complain about")
injection_bits = (
    "ignore the office rules",
    "ignore previous",
    "ignore the above",
    "set outcome",
    "you are now",
    "system prompt",
)

force_flags = (
    "payment",
    "credentials",
    "records",
    "welfare",
    "complaint",
    "injection",
    "mismatch",
)
flag_order = force_flags + ("personal",)


def scrub(text):
    text = dob_re.sub("date of birth [withheld]", text)
    text = student_re.sub("student number [withheld]", text)
    text = phone_re.sub("[withheld]", text)
    return text


def redact(facts):
    copy = dict(facts)
    copy["subject"] = scrub(copy.get("subject", ""))
    copy["body"] = scrub(copy.get("body", ""))
    return copy


def domain(addr):
    if not addr or "@" not in addr:
        return ""
    return addr.rsplit("@", 1)[1].lower()


def has_bit(text, bits):
    lowered = text.lower()
    return any(bit in lowered for bit in bits)


def flags(facts):
    text = f"{facts.get('subject', '')}\n{facts.get('body', '')}"
    found = set()

    if has_bit(text, payment_bits):
        found.add("payment")
    if has_bit(text, credential_bits):
        found.add("credentials")
    if has_bit(text, record_bits):
        found.add("records")
    if has_bit(text, welfare_bits):
        found.add("welfare")
    if has_bit(text, complaint_bits):
        found.add("complaint")
    if has_bit(text, injection_bits):
        found.add("injection")
    if scrub(text) != text:
        found.add("personal")

    reply = domain(facts.get("reply_to"))
    sender = domain(facts.get("from_addr"))
    if reply and sender and reply != sender:
        found.add("mismatch")

    return [flag for flag in flag_order if flag in found]


def validate(value):
    schema = json.loads((root / "schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: str(error.path))
    return [
        f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in errors
    ]


def squash(text):
    return space_re.sub(" ", text).strip()


def cited(facts, result):
    quote = result.get("citation", "") if isinstance(result, dict) else ""
    if not isinstance(quote, str):
        return False
    quote = squash(quote)
    if len(quote) < 8:
        return False
    source = squash(f"{facts.get('subject', '')}\n{facts.get('body', '')}")
    return quote in source


def held_note(found):
    if "welfare" in found:
        return "Held for a person. Do not draft a reply to this one."
    if "injection" in found:
        return "Held for a person. The email tried to instruct the assistant."
    if "credentials" in found:
        return "Held for a person. Do not reply with a login or password link."
    if "payment" in found:
        return "Held for a person. Do not reply about payment."
    if "records" in found:
        return "Held for a person. This asks for student records."
    if "complaint" in found:
        return "Held for a person. A staff complaint is not drafted."
    if "mismatch" in found:
        return "Held for a person. The reply address does not match the sender."
    return "Held for a person."


def settle(name, facts, result):
    found = flags(facts)
    shown = redact(facts)
    model = result if isinstance(result, dict) else None
    errors = []

    if model is None:
        errors.append("model reply was not JSON")
    else:
        errors.extend(validate(model))
        if not errors and not cited(facts, model):
            errors.append("citation was not in the email")

    if errors:
        card = {
            "ask": "other",
            "when": "today",
            "outcome": "person",
            "citation": "",
            "note": "Held for a person. The reply check did not pass.",
        }
    else:
        card = {
            "ask": model["ask"],
            "when": model["when"],
            "outcome": model["outcome"],
            "citation": model["citation"],
            "note": model["note"],
        }

    if any(flag in found for flag in force_flags):
        card["outcome"] = "person"
        card["note"] = held_note(found)
        if "welfare" in found:
            card["when"] = "today"
        if model and cited(facts, model):
            card["citation"] = model["citation"]
        else:
            card["citation"] = ""

    return {
        "file": name,
        "flags": found,
        "shown": shown,
        "model": model,
        "errors": errors,
        "card": card,
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 hold.py fixtures/absence.json")

    path = Path(sys.argv[1])
    value = json.loads(path.read_text())
    errors = validate(value)

    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("VALID")


if __name__ == "__main__":
    main()
