import json
import os

from google import genai
from google.genai import types

from recon.models import Discrepancy

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL","gemini-3.6-flash")

SYSTEM_PROMPT = """You are answering questions about a reconciliation exceptions list \
for ONE org. You will be given the complete list of that org's exceptions as JSON, \
under EXCEPTIONS. Answer ONLY using that data.

Rules, no exceptions:
- Every number, count, or claim in your answer must be traceable to specific \
exception ids in the data you were given.
- If the question cannot be answered from the given data -- because it asks about \
something not present, or is ambiguous, or requires information you were not given \
-- you MUST refuse. Do not guess, estimate, or answer from general knowledge.
- Never invent an exception id. Only cite ids that literally appear in EXCEPTIONS.

Respond with ONLY a JSON object, no other text, in this exact shape:
{"answer": "<your answer or refusal, in plain English>",
 "citations": [<int ids you actually used, empty list if none>],
 "refused": <true or false>}
"""


def _client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def answer_question(question: str, org_id: str) -> dict:
    """Returns {"answer": str, "citations": [int...], "refused": bool}."""
    question = (question or "").strip()
    if not question:
        return {"answer": "Ask a question about the exceptions for your org.", "citations": [], "refused": True}

    # Step 1: query the database ourselves. This is the entire grounding
    # guarantee -- the model only ever sees what this queryset returns.
    rows = list(
        Discrepancy.objects.filter(org_id=org_id)
        .values("id", "reason_code", "summary", "record_id", "entry_id", "location_id", "detail")
    )

    if not rows:
        return {"answer": "There are no exceptions recorded for your org.", "citations": [], "refused": False}

    client = _client()
    if client is None:
        # Fail closed, not open: missing key -> refuse, don't guess or crash.
        return {
            "answer": "The question-answering service is not configured (missing API key).",
            "citations": [],
            "refused": True,
        }

    user_content = (
        f"EXCEPTIONS (JSON, {len(rows)} total for this org):\n"
        f"{json.dumps(rows, default=str)}\n\n"
        f"QUESTION: {question}"
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        parsed = json.loads(response.text)
    except Exception as exc:  # any failure here must refuse, not 500 the request
        print("Angeerasa: exception in openAI", exc)
        return {
            "answer": f"Could not get a grounded answer right now ({exc.__class__.__name__}).",
            "citations": [],
            "refused": True,
        }

    # Step 2: never trust the model's own citations blindly -- verify
    # every id it claims actually exists in the rows we gave it.
    real_ids = {r["id"] for r in rows}
    claimed_ids = parsed.get("citations", []) or []
    if not set(claimed_ids).issubset(real_ids):
        return {
            "answer": "Could not verify the grounding of that answer, so refusing rather than risk a wrong citation.",
            "citations": [],
            "refused": True,
        }

    return {
        "answer": parsed.get("answer", ""),
        "citations": claimed_ids,
        "refused": bool(parsed.get("refused", False)),
    }