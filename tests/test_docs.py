"""The documentation stays in sync with the work: indexes list every record and relative links resolve."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def _numbered(folder):
    return sorted(p for p in (DOCS / folder).glob("[0-9][0-9]*-*.md"))


def test_every_experiment_and_decision_is_in_its_index():
    for folder in ("experiments", "decisions"):
        index = (DOCS / folder / "README.md").read_text()
        missing = [p.name for p in _numbered(folder) if p.name not in index]
        assert not missing, f"{folder}/README.md does not list {missing}"


def test_relative_links_resolve():
    files = [ROOT / "README.md", *DOCS.glob("*.md"), DOCS / "experiments" / "README.md", DOCS / "decisions" / "README.md",
             *_numbered("experiments"), *_numbered("decisions")]
    bad = []
    for f in files:
        for target in re.findall(r"\]\(([^)\s]+)\)", f.read_text()):
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            path = target.split("#")[0]
            if path and not (f.parent / path).resolve().exists():
                bad.append(f"{f.relative_to(ROOT)} -> {target}")
    assert not bad, "broken links: " + "; ".join(bad)
