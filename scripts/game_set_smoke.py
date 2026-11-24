"""Validate game-set payloads for editor + studio tool types."""
from app.services.game_set_service import VALID_TYPES, _payload_from_body

fail = 0


def check(name, cond, detail=""):
    global fail
    print(("PASS" if cond else "FAIL"), name, detail)
    if not cond:
        fail += 1


check("type_count", len(VALID_TYPES) >= 12, str(len(VALID_TYPES)))

cases = [
    ("name-picker", "Lớp 10", "An\nBinh\nChi"),
    ("match-pairs", "Pairs", "a | 1\nb | 2"),
    ("word-search", "WS", "APPLE\nBOOK\nCAT"),
    ("paced-quiz", "Quiz", "Q? | yes | no | maybe"),
    ("tug-of-war", "Tug", '{"raw":"Q? | a | b | c","teamA":"A","teamB":"B"}'),
    ("html-game", "HTML", "<h1>Hi</h1>"),
    ("countdown", "CD", '{"seconds":60,"style":"classic"}'),
    ("sleeping-dragon", "Dragon", '{"threshold":30}'),
    ("text-profiler", "TP", "This is a longer sample English paragraph for saving."),
]

for t, title, content in cases:
    doc, err = _payload_from_body({"type": t, "title": title, "content_text": content})
    check(t, bool(doc) and not err, err or "ok")

doc, err = _payload_from_body({"type": "name-picker", "title": "x", "content_text": "  \n  "})
check("name-picker empty rejected", bool(err), err)

doc, err = _payload_from_body(
    {"type": "wheel", "title": "w", "wheel_items": [{"label": "A"}, {"label": "B"}]}
)
check("wheel still ok", bool(doc), err)

print(f"TOTAL fails={fail}")
raise SystemExit(fail)
