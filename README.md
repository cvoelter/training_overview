# Training Overview

A password-protected GitHub Pages site that collects the training-progress reports
(HTML files) of several behavioral experiments from their own repositories, public or private,
and shows them behind a single menu.

## How it works

1. `experiments.json` lists the experiments and where each report lives.
2. The GitHub Actions workflow (`.github/workflows/deploy.yml`) runs on every push, every
   6 hours, and on demand. It
   - downloads each report through the GitHub API (`scripts/build_site.py`), using a token so
     private repositories work,
   - builds `index.html` with the experiment menu (`site_template/index.html`),
   - encrypts every page with [StatiCrypt](https://github.com/robinmoisson/staticrypt) (AES-256),
   - publishes the encrypted files to GitHub Pages.

The unencrypted reports are never committed to this repository. Only encrypted pages are
published.

## One-time setup

1. **Create a token** that can read the source repositories:
   - If all source repos belong to you or to one organization, use a *fine-grained* token
     (Settings → Developer settings → Fine-grained tokens) with *Contents: Read-only* on those repos.
   - If repos belong to other users and you are a collaborator,
     use a *classic* token with the `repo` scope. Fine-grained tokens can't access another user's
     personal repos. Note that a classic token can read **all** private repos you have access to,
     so keep it only as a secret.
2. In this repo, open **Settings → Secrets and variables → Actions** and add:
   - `SOURCE_REPOS_TOKEN`: the token from step 1
   - `SITE_PASSWORD`: the password for the website (use a long one)
3. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Push to `main` or run the workflow from the **Actions** tab. The site will be at
   `https://cvoelter.github.io/training_overview/`.

## Adding an experiment

Add an entry to `experiments.json` and push:

```json
{
  "id": "my_study",
  "name": "My Study",
  "description": "optional short text",
  "repo": "owner/repository",
  "branch": "main",
  "path": "folder/report.html"
}
```

`id` must be unique (it is used in the URL, e.g. `.../#my_study`). If the repo is private, the token
must have access to it. A report that can't be downloaded shows up in the menu as
"could not be loaded" with the reason. The other experiments are still published.

## Refreshing immediately after a report changes (optional)

By default, the site refreshes every 6 hours. To refresh right away when a source repo pushes a new
report, add this workflow to the source repo (it needs a secret `OVERVIEW_TOKEN`, a token that
can trigger workflows in this repo):

```yaml
name: Notify training overview
on:
  push:
    paths: ["4_ANALYSES/planko_report.html"]
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -X POST -H "Authorization: Bearer ${{ secrets.OVERVIEW_TOKEN }}" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/cvoelter/training_overview/dispatches \
            -d '{"event_type":"report-updated"}'
```

## Notes

- **Password protection is client-side.** Without the password, the pages are encrypted noise.
  How secure this is depends on the password's strength, so use a long one. Changing
  `SITE_PASSWORD` and re-running the workflow changes the password.
- Tick **"Remember me"** at login. This lets the reports inside the menu page unlock automatically
  (stored for 30 days). Otherwise each report asks for the password again.
- **This repo can stay public.** It contains only the configuration (repository names and paths),
  not the reports. GitHub Pages on a private repo requires a paid plan.
- Limits: GitHub Pages allows files up to 100 MB and sites up to 1 GB. Encryption roughly doubles
  file size, so a 22 MB report becomes about 45 MB.
- Local test of the download step: `GH_TOKEN=<token> python scripts/build_site.py`, then open
  `public/index.html` (unencrypted, so don't share it).
