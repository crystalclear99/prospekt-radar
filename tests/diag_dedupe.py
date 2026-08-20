import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sources import billa, marktguru
from core.models import _slug_name

b = billa.fetch()
m = marktguru.fetch()
print(f"BILLA roh: {len(b)}  marktguru roh: {len(m)}")

# exakte key-Kollisionen innerhalb BILLA
def stats(offers, label):
    keys = collections.Counter(o.key for o in offers)
    dups = {k:c for k,c in keys.items() if c>1}
    print(f"\n{label}: {len(offers)} offers, {len(keys)} unique keys, {len(dups)} keys mit >1")
    empties = sum(1 for o in offers if _slug_name(o.product)=="")
    print(f"  leere slug_name: {empties}")
    # groesste Kollisionsgruppen
    for k,c in sorted(dups.items(), key=lambda x:-x[1])[:5]:
        names = [o.product for o in offers if o.key==k][:4]
        print(f"    key={k!r} x{c}: {names}")

stats(b, "BILLA")
stats(m, "marktguru")

# fuzzy-Gruppen
def fuzzy(o):
    bv,bu = o.amount.base()
    return (o.store.strip().lower(), round(bv,3), bu, frozenset(_slug_name(o.product).split()))
allo = b+m
fz = collections.Counter(fuzzy(o) for o in allo)
big = sorted(((k,c) for k,c in fz.items() if c>1), key=lambda x:-x[1])[:8]
print("\nGroesste FUZZY-Gruppen (store, base, tokens):")
for k,c in big:
    ex = [o.product for o in allo if fuzzy(o)==k][:4]
    print(f"  x{c} tokens={set(k[3])} base={k[1]}{k[2]}: {ex}")
