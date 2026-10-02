"""Deploy/recall step-order check on the saved circuit (circuit model of verify_hyperion73.py).
Every hangar transit must go HOME -> ... -> N+1 -> junction (deploy) and back without
any step in the wrong direction, for several docking-lock times."""
import runpy, json, sys
g = runpy.run_path(str(__import__('pathlib').Path(__file__).with_name('verify_hyperion73.py')), run_name='seq')
Sim = g['Sim']
res = {}
for lock in (0.2, 0.35, 0.6, 1.0):
    s = Sim(lock); s.tick(180)
    seq = {r['name']: [r['physical']] for r in s.rails}
    def rec():
        for r in s.rails:
            if seq[r['name']][-1] != r['physical']: seq[r['name']].append(r['physical'])
    s.click()
    for _ in range(int(60 * 60)):
        s.tick(1); rec()
        if s.active(): break
    s.tick(120); rec()
    dep = {k: list(v) for k, v in seq.items()}
    for r in s.rails: seq[r['name']] = [r['physical']]
    s.click()
    for _ in range(int(120 * 60)):
        s.tick(1); rec()
        if s.stowed(): break
    ok = True
    for r in s.rails:
        n, H, HOME = r['rail_end'], r['junction'], r['home']
        want_dep = list(range(HOME, n, -1)) + [H]
        want_rec = [H] + list(range(n + 1, HOME + 1))
        ok &= dep[r['name']] == want_dep and seq[r['name']] == want_rec
    res[lock] = ok
    print(f'lock {lock}s: deploy {"ok" if ok else dep} recall {"ok" if ok else seq}')
sys.exit(0 if all(res.values()) else 1)
