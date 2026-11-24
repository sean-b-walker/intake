# intake

A slip for the school office. One parent email in, a short card out: what they are asking, how soon, a quote from the email, and whether the office can draft a reply or a person has to take it.

It does not send mail. It does not reply to the parent. If the check fails, the slip is held.

The samples are made up. Do not put real parent or student mail in here.

## Run

```
pip install -r requirements.txt
python3 score.py
python3 show.py
```

`score.py` reads the saved replies in `fixtures/`. No API key. Some of those replies are wrong on purpose, so a hold can be shown without calling a model. `show.py` opens http://127.0.0.1:8765. Start with Absence, then Refund account, Camp form, and the one with a student number.

`python3 intake.py samples/absence.eml` calls a model. That needs a `.env`:

```
INTAKE_API_KEY=
INTAKE_BASE_URL=
INTAKE_MODEL=
```

`python3 score.py --live` does the same across the samples.

Payment, a password link, another child's records, a staff complaint, a safety worry, an instruction aimed at the assistant, or a reply address on a different domain is held even if the model says draft. A student number, date of birth, or phone is taken out of the text before a model sees it.
