"""Conservative source-section context carried alongside PDF passages."""
import json
import re

_CODE = r"[A-Z]{2,8}\s?\d{3,4}[A-Z]?"
_CODE_RE = re.compile(_CODE, re.I)
_CODES = rf"{_CODE}(?:\s*(?:/|&|,|and)\s*{_CODE})*"
_SCOPE_HEADINGS = [
    re.compile(rf"^(?:Assessments?|Assignments?|Coursework|Grading)(?:\s+for)?\s*[:–-]?\s*({_CODES})\s*$", re.I),
    re.compile(rf"^({_CODES})\s*[:–-]\s*(?:Assessments?|Assignments?|Coursework|Grading)\s*$", re.I),
]
_SECTION = re.compile(
    r"(?im)^[ \t]*(?:(?:Part|Section)[ \t]+(?:[IVXLCDM]+|\d+)(?:[ \t]*[:.–-][^\n]*|[ \t]*)"
    r"|(?:Answers?|Solutions?|Answer[ \t]+key)(?:[ \t]+(?:to|for)[^\n]*)?[ \t]*:?[ \t]*)$"
)
_TRUE_FALSE = re.compile(r"\btrue\s*(?:(?:[-–/]\s*)?(?:or\s*[-–]?\s*)?)false\b", re.I)
_TASK = re.compile(r"\b(?:determine|decide|mark|your task|for each|consists of)\b", re.I)
_NUMBERED = re.compile(r"(?m)^[ \t]*\d+[.)][ \t]+")
_PART = re.compile(r"\b(part|section)\s+([IVXLCDM]+|\d+)\b", re.I)
_ITEM = re.compile(r"\b(?:statement|question|item)\s*#?\s*(\d+)\b", re.I)


def _section_key(match):
    value = match.group(2).upper()
    if not value.isdigit():
        digits = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        total = 0
        last = 0
        for char in reversed(value):
            number = digits[char]
            total += -number if number < last else number
            last = max(last, number)
        value = str(total)
    return match.group(1).lower() + ":" + str(int(value))


def query_locator(query):
    """Only an explicit, single item and section is an exact locator."""
    items, parts = list(_ITEM.finditer(query)), list(_PART.finditer(query))
    if len(items) == len(parts) == 1:
        return _section_key(parts[0]), str(int(items[0].group(1)))
    return None


def _page_items(text, active):
    """Index complete numbered propositions; do not invent missing continuations."""
    if not active:
        return {}
    part = _PART.search(active["instruction"])
    if not part:
        return {}
    markers = list(re.finditer(r"(?m)^[ \t]*(\d+)[.)][ \t]+", text))
    items = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = text[marker.end():end].strip()
        # Common standalone page numbers must not become part of the quotation.
        body = re.sub(r"\n\s*\d+\s*$", "", body).strip()
        body = " ".join(body.split())
        if body and len(body) <= 1600 and body[-1] in ".?!":
            items[str(int(marker.group(1)))] = body
    return {"source_section": _section_key(part), "source_items": json.dumps(items)} if items else {}


def course_codes(text):
    return {re.sub(r"\s+", "", code).upper() for code in _CODE_RE.findall(text or "")}


def _exercise_instruction(text):
    head = _NUMBERED.split(text, maxsplit=1)[0][:600]
    if _TRUE_FALSE.search(head) and _TASK.search(head) and re.search(r"\b(?:statements?|questions?)\b", head, re.I):
        return " ".join(head.split())
    return None


def pdf_source_context(text, page_number, previous=None):
    """Return page metadata and the exercise section continuing to the next page.

    Subject scope is deliberately page-local: a following shared policy page
    must not inherit the previous cohort's assessment heading. Explicit Part /
    Section boundaries end an inherited True-or-False exercise.
    """
    metadata = {}
    descriptions = []
    for line in [line.strip() for line in text.splitlines() if line.strip()][:8]:
        for pattern in _SCOPE_HEADINGS:
            match = pattern.fullmatch(line)
            if match:
                metadata["source_scope"] = "|".join(sorted(course_codes(match.group(1))))
                descriptions.append(f"Section heading on page {page_number}: {line}")

    active = previous
    page_exercises = [previous] if previous else []
    sections = list(_SECTION.finditer(text))
    if not sections:
        instruction = _exercise_instruction(text)
        if instruction:
            active = {"instruction": instruction, "page": page_number}
            page_exercises.append(active)
    else:
        # A new section at the top of a page replaces the preceding section.
        if not text[:sections[0].start()].strip():
            page_exercises = []
        for index, marker in enumerate(sections):
            end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
            instruction = _exercise_instruction(text[marker.start():end])
            active = {"instruction": instruction, "page": page_number} if instruction else None
            if active:
                page_exercises.append(active)

    if page_exercises:
        first = page_exercises[0]
        metadata["source_kind"] = "exercise_prompt"
        metadata["context_page"] = first["page"]
        descriptions.append(
            f"Exercise instruction from page {first['page']}: {first['instruction']} "
            "These are propositions to evaluate, not an answer key or verified facts."
        )
        # A mixed-section page is deliberately not given a single item index.
        if not sections or (len(sections) == 1 and active is not None):
            metadata.update(_page_items(text, active))
    if descriptions:
        metadata["source_context"] = "\n".join(descriptions)
    return metadata, active
