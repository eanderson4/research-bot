"""Adversarial verification gate: worker notes must survive a fact-check
against their own cited sources before entering a deliverable.

The verifier agent gets the notes AND the (cached) source page text, checks
every claim, and emits CLAIM/VERDICT/EVIDENCE lines plus a final
`OVERALL: PASS|FAIL supported=n distorted=n unsupported=n`.

Notes files may hold sections for several sources (`summarize -o FILE`
appends one `### <url>` section per page); each section is verified against
its own source only, so a claim is never audited against the wrong page.

`research verify NOTES.md` writes NOTES.verdict.md next to the notes and
exits nonzero on FAIL, so an orchestrator can gate on it:
    research summarize $URL -o notes/ && research verify notes/<file>.md
Exit codes: 1 = claims failed verification, 2 = only source-fetch failures
(claims unverifiable, none proven wrong). Source pages are read from the
page cache, so verification costs LLM tokens only — no re-fetching fees.
"""
import re
import sys
from pathlib import Path

from . import agents, fetch

OVERALL_RE = re.compile(
    r"OVERALL:\s*(PASS|FAIL)\s*supported=(\d+)\s*distorted=(\d+)\s*unsupported=(\d+)", re.I)
URL_RE = re.compile(r"^#+\s*(?:notes:\s*)?(?:Source:\s*)?(https?://\S+)", re.M | re.I)


def parse_overall(text: str):
    """Return {passed, supported, distorted, unsupported} or None if absent."""
    m = OVERALL_RE.search(text or "")
    if not m:
        return None
    return {"passed": m.group(1).upper() == "PASS",
            "supported": int(m.group(2)), "distorted": int(m.group(3)),
            "unsupported": int(m.group(4))}


def _clean_url(u: str) -> str:
    return u.rstrip(").,")


def source_urls(notes_text: str):
    seen, urls = set(), []
    for u in URL_RE.findall(notes_text):
        u = _clean_url(u)
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def split_sections(notes_text: str):
    """Map each cited URL to only the notes text under its own heading(s),
    in order of first appearance. Single-source files map to the full text."""
    matches = list(URL_RE.finditer(notes_text))
    urls = source_urls(notes_text)
    if len(urls) <= 1:
        return {u: notes_text for u in urls}
    sections = {}
    for i, m in enumerate(matches):
        url = _clean_url(m.group(1))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(notes_text)
        sections[url] = sections.get(url, "") + notes_text[m.start():end]
    return sections


def verify_text(notes_text: str, source_text: str, url: str, model=None):
    """One verifier call. Returns llm.call dict + 'overall' (parsed verdict)."""
    res = agents.run("verifier", (
        f"SOURCE URL: {url}\n\n"
        f"=== NOTES TO AUDIT ===\n{notes_text}\n\n"
        f"=== SOURCE TEXT ===\n{source_text}"
    ), model=model)
    res["overall"] = parse_overall(res["text"])
    return res


def verify_file(notes_path: Path, model=None, max_chars=120000):
    """Verify a notes file, section by section, against each cited source.
    Returns (passed, verdict_path, verdicts)."""
    notes_text = notes_path.read_text()
    sections = split_sections(notes_text)
    if not sections:
        raise ValueError(f"no source URLs found in headings of {notes_path}")
    verdicts, passed = [], True
    for url, section_text in sections.items():
        try:
            source_text = fetch.fetch_text(url, max_chars=max_chars)
        except Exception as e:
            verdicts.append((url, None, f"SOURCE FETCH FAILED: {e}"))
            passed = False
            continue
        res = verify_text(section_text, source_text, url, model=model)
        overall = res["overall"]
        if overall is None or not overall["passed"]:
            passed = False
        verdicts.append((url, overall, res["text"]))

    vpath = notes_path.with_suffix(".verdict.md")
    out = [f"# verdict: {notes_path.name}", ""]
    for url, overall, text in verdicts:
        out += [f"## {url}", "", text, ""]
    tag = "PASS" if passed else "FAIL"
    out += [f"# RESULT: {tag}"]
    vpath.write_text("\n".join(out) + "\n")
    return passed, vpath, verdicts


def run(args):
    try:
        passed, vpath, verdicts = verify_file(
            Path(args.notes).expanduser(), model=args.model, max_chars=args.max_chars)
    except (ValueError, OSError) as e:
        sys.exit(f"error: {e}")
    claims_failed = False
    for url, overall, text in verdicts:
        if overall:
            tag = "PASS" if overall["passed"] else "FAIL"
            if not overall["passed"]:
                claims_failed = True
            print(f"{tag}  {url}  (supported={overall['supported']} "
                  f"distorted={overall['distorted']} unsupported={overall['unsupported']})")
        elif text.startswith("SOURCE FETCH FAILED"):
            print(f"UNVERIFIABLE  {url}  ({text})")
        else:
            claims_failed = True
            print(f"FAIL  {url}  (no parseable verdict)")
    print(f"VERDICT -> {vpath}")
    if not passed:
        # 1 = claims failed; 2 = nothing failed but some sources couldn't be fetched
        sys.exit(1 if claims_failed else 2)
