# Public site release gates

Graduate Pathfinder separates five acceptance gates. Passing one gate never implies that a later gate passed.

## 1. Local automated gate

Run the repository checks from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
python3 scripts/check_skill_structure.py .
python3 /Users/zzz/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
npm --prefix web ci
npx --prefix web playwright install chromium
npm --prefix web run typecheck
npm --prefix web run test:site
npm --prefix web run build:site
node scripts/check-site-assets.mjs
python3 scripts/check_workflows.py .
git diff --check
```

A local pass covers the checked source tree and locally built static artifact only. It does not prove GitHub Actions, deployment, live routing, image approval, or release publication.

## 2. Hosted Actions gate

After integration into `main`, confirm that the ordinary CI workflow and the guarded Pages workflow pass on GitHub. GitHub is the authoritative parser and executor of workflow YAML. A local workflow-contract pass is not a hosted Actions result.

## 3. Generated-image human-review gate

A human reviewer must inspect the three original concept artworks and the three captured site screenshots at native resolution. Confirm there is no accidental readable text, logo, person, recognizable institution, private data, clipping, missing imagery, or misleading real-evidence presentation. Automated asset checks and agent inspection do not satisfy this human gate.

## 4. Live Pages acceptance gate

Only after the Pages workflow succeeds, verify the live Home, Explore, and Docs routes under `https://z-lab-boop.github.io/graduate-pathfinder/`. Confirm CSS, JavaScript, JSON, and local images load under the project subpath; repeat the key English/Chinese, keyboard, mobile, synthetic-label, privacy, and no-probability checks against the hosted site. Until that happens, repository URLs are intended routes, not proof of a live site.

## 5. Release and download gate

No tagged binary release with downloadable assets is currently verified or claimed. Install the complete source repository as the Skill directory. Website artwork and screenshots are documentation assets, not release binaries. Publishing a tag or download requires a separate reviewed release process and must not be inferred from local, hosted CI, human-image, or live Pages acceptance.
