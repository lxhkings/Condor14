"""Build-time enforcement of spec §7.2: the word "hypothetical" must not
appear in user-facing HTML except inside an explicit allowlist of
risk-warning sentences.

For MVP the allowlist is empty — there should be NO "hypothetical" anywhere.
"""

import re
from pathlib import Path

# Edit this set when adding SEC-style risk-warning sentences that legitimately
# need the word "hypothetical". Each entry must be the EXACT sentence as it
# appears in the rendered HTML (with terminal punctuation).
HYPOTHETICAL_ALLOWLIST: set[str] = set()

_PATTERN = re.compile(r"\bhypothetical\b", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def check_hypothetical_allowlist(public_dir: Path) -> list[tuple[Path, int, str]]:
    """Walk public_dir for *.html files; return (path, line_number, snippet)
    for each occurrence of "hypothetical" outside the allowlist."""
    violations: list[tuple[Path, int, str]] = []
    for html_path in public_dir.rglob("*.html"):
        for line_no, line in enumerate(html_path.read_text().splitlines(), start=1):
            if not _PATTERN.search(line):
                continue
            # Strip HTML tags for sentence-level check
            stripped = re.sub(r"<[^>]+>", "", line).strip()
            sentences = _SENTENCE_SPLIT.split(stripped)
            for s in sentences:
                if _PATTERN.search(s) and s.strip() not in HYPOTHETICAL_ALLOWLIST:
                    violations.append((html_path, line_no, s.strip()[:160]))
                    break
    return violations
