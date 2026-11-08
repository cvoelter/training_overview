"""Download the experiment reports listed in experiments.json and assemble the site.

Output goes to ./public:
  public/index.html          overview page with the experiment menu
  public/reports/<id>.html   one report per experiment

Set GH_TOKEN to a token with read access to the private source repositories
(public repositories work without it, but a token avoids API rate limits).
Encryption is done afterwards by StatiCrypt in the GitHub Actions workflow.
"""

import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public"
API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN", "").strip()


def github_get(url, accept):
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "training-overview"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300) as resp:
        return resp.read()


def fetch_report(exp):
    path = urllib.parse.quote(exp["path"])
    ref = urllib.parse.quote(exp.get("branch", "main"))
    return github_get(f"{API}/repos/{exp['repo']}/contents/{path}?ref={ref}", "application/vnd.github.raw+json")


def fetch_last_commit(exp):
    query = urllib.parse.urlencode({"path": exp["path"], "sha": exp.get("branch", "main"), "per_page": 1})
    commits = json.loads(github_get(f"{API}/repos/{exp['repo']}/commits?{query}", "application/vnd.github+json"))
    if not commits:
        return None
    return commits[0]["commit"]["committer"]["date"]


def error_page(exp, message):
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{escape(exp['name'])}</title></head>
<body style="font-family: system-ui, sans-serif; padding: 2rem; color: #333">
<h2>Report could not be loaded</h2>
<p><b>{escape(exp['name'])}</b> &mdash; {escape(exp['repo'])}/{escape(exp['path'])}</p>
<pre style="background:#f4f4f4;padding:1rem;white-space:pre-wrap">{escape(message)}</pre>
<p>Check the repository/path in <code>experiments.json</code> and that the token has access to the repository.</p>
</body></html>""".encode("utf-8")


def main():
    experiments = json.loads((ROOT / "experiments.json").read_text(encoding="utf-8"))
    ids = [e["id"] for e in experiments]
    if len(ids) != len(set(ids)):
        sys.exit("Duplicate experiment ids in experiments.json")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "reports").mkdir(parents=True)

    menu = []
    failures = 0
    for exp in experiments:
        entry = {
            "id": exp["id"],
            "name": exp["name"],
            "description": exp.get("description", ""),
            "repo": exp["repo"],
            "updated": None,
            "ok": True,
        }
        try:
            content = fetch_report(exp)
            try:
                entry["updated"] = fetch_last_commit(exp)
            except urllib.error.URLError as err:
                print(f"  warning: could not get commit date for {exp['id']}: {err}")
            print(f"OK    {exp['id']}: {len(content) / 1e6:.1f} MB")
        except urllib.error.HTTPError as err:
            hint = " (private repo without access, or wrong path?)" if err.code == 404 else ""
            content = error_page(exp, f"HTTP {err.code} {err.reason}{hint}")
            entry["ok"] = False
            failures += 1
            print(f"FAIL  {exp['id']}: HTTP {err.code}{hint}")
        except urllib.error.URLError as err:
            content = error_page(exp, str(err))
            entry["ok"] = False
            failures += 1
            print(f"FAIL  {exp['id']}: {err}")
        (OUT / "reports" / f"{exp['id']}.html").write_bytes(content)
        menu.append(entry)

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    template = (ROOT / "site_template" / "index.html").read_text(encoding="utf-8")
    # Escape "</" so experiment names can never close the <script> tag.
    data = json.dumps({"experiments": menu, "built": built}).replace("</", "<\\/")
    (OUT / "index.html").write_text(template.replace("/*__SITE_DATA__*/null", data), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")

    print(f"\nBuilt {len(menu)} experiment(s), {failures} failed.")


if __name__ == "__main__":
    main()
