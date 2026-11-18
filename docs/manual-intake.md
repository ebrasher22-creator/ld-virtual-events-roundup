# Exact manual intake demonstration (synthetic, never publish)

From a clean checkout of `feature/github-event-pipeline`, use Python 3.11+ and no installed dependencies. All mutations below are inside ignored `work/manual-intake-demo`; real repository intake/data remain unchanged. Start with a fresh directory (the initialization refuses to overwrite an earlier demonstration).

```sh
python3 - <<'PY'
from pathlib import Path
import json
import shutil
root = Path('work/manual-intake-demo')
root.mkdir(parents=True, exist_ok=False)
shutil.copytree('config', root/'config')
(root/'data').mkdir()
(root/'data/canonical-events.json').write_text('[]\n')
(root/'data/reviews.json').write_text('{}\n')
for agent in ['chatgpt', 'gemini']:
    folder = root/'intake'/agent
    folder.mkdir(parents=True)
    shutil.copy(f'tests/fixtures/{agent}.json', folder/'2026-11-24-synthetic.json')
PY
python3 scripts/validate.py --root work/manual-intake-demo
python3 scripts/ingest.py --root work/manual-intake-demo
python3 scripts/assign_weeks.py --root work/manual-intake-demo --as-of 2026-11-24
python3 scripts/generate_post.py --root work/manual-intake-demo --as-of 2026-11-24
python3 - <<'PY'
from pathlib import Path
import hashlib
import json
import subprocess
import sys
root = Path('work/manual-intake-demo')
canonical = root/'data/canonical-events.json'
before = hashlib.sha256(canonical.read_bytes()).hexdigest()
subprocess.run([sys.executable, 'scripts/ingest.py', '--root', str(root)], check=True)
subprocess.run([sys.executable, 'scripts/assign_weeks.py', '--root', str(root), '--as-of', '2026-11-24'], check=True)
assert before == hashlib.sha256(canonical.read_bytes()).hexdigest()
events = json.loads(canonical.read_text())
future = json.loads((root/'data/future-events.json').read_text())
review = json.loads((root/'weeks/2026/RW49_2026-11-29_to_2026-12-05/review.json').read_text())
assert len(events) == 2 and len(future) == 1
assert sorted(len(e['submissions']) for e in events) == [1, 3]
assert any('start_datetime' in e['conflict_flags'] for e in events)
assert review['selected_ids'] == []
assert review['below_target'] is True
print('PASS: 4 submissions → 2 canonical events; overlap retained both agents; conflicting time quarantined; 1 future event; 0 selected; rerun unchanged.')
PY
```

The full sample objects are in `tests/fixtures/chatgpt.json` and `tests/fixtures/gemini.json`. They contain 1 and 3 submissions, respectively. All use example.org and fictional event information. The overlapping event is assigned `2026/RW49_2026-11-29_to_2026-12-05`; the future event is January 5, 2027. Empty eligible output is the correct safe result because neither has an independent human review, and the overlap also has conflicting times.

To demonstrate nonempty draft rendering **with a simulated human review in an isolated test**:

```sh
python3 scripts/smoke.py
```

This adds a third synthetic event, assigns a synthetic review only to it, and writes a one-event draft under `tests/smoke-output/`. `unverified-review.json` proves zero selection before review, `review.json` proves one selection afterwards, and the canonical/future/review snapshots preserve the synthetic evidence. Do not copy this simulated approval into production.

## Real intake

Save unwrapped JSON arrays to `intake/chatgpt/YYYY-MM-DD-name.json` or `intake/gemini/YYYY-MM-DD-name.json`, validate with `python3 scripts/validate.py`, then submit the changes on a new intake branch targeting the current default branch. Human approval must precede merging. Run ingestion and assignment, inspect canonical changes, resolve conflicts against primary pages, then add independently supported reviews and regenerate. Use `--as-of 2026-11-24` for the first pilot. In Actions dispatch **Prepare reviewed roundup artifacts**, select the feature branch and set `as_of` to `2026-11-24`.

Raw intake files are append-only. Markdown fences, an enclosing `events` object, missing required fields, uppercase agent labels, `CST` as a timezone, timestamps without seconds/offsets, `online` instead of `virtual`, string numeric costs, extra fields, null required URLs/dates, and evidence in the wrong shape will be rejected. Inaccessible pages remain pending; no agent-supplied verification claim can bypass human review.
