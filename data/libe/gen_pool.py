"""S2-A fragment-recombine pool generation from ADR-001 principal molecules,
then measure c = fraction already present in LIBE at (formula,charge,spin)."""
import json, itertools, collections, re

# ---- principal molecules: (elements, bonds) explicit connectivity ----
def EC():
    sp=['C','O','O','C','C','O','H','H','H','H']   # 0:C_carb 1:O(=O) 2:O_ring 3:C 4:C 5:O_ring
    b=[(0,1),(0,2),(2,3),(3,4),(4,5),(5,0),(3,6),(3,7),(4,8),(4,9)]
    return sp,b
def EMC():
    # CH3-O-C(=O)-O-CH2-CH3
    sp=['C','O','C','O','O','C','C']+['H']*8
    b=[(0,1),(1,2),(2,3),(2,4),(4,5),(5,6),
       (0,7),(0,8),(0,9),(5,10),(5,11),(6,12),(6,13),(6,14)]
    return sp,b
def LI():  return ['Li'],[]
def PF6(): return ['P']+['F']*6,[(0,i) for i in range(1,7)]

PRINCIPALS={'EC':EC(),'EMC':EMC(),'Li':LI(),'PF6':PF6()}

def components(sp,bonds,removed):
    keep=[b for i,b in enumerate(bonds) if i not in removed]
    adj=collections.defaultdict(set)
    for a,b in keep: adj[a].add(b); adj[b].add(a)
    seen=set(); comps=[]
    for s in range(len(sp)):
        if s in seen: continue
        st=[s]; c=set()
        while st:
            u=st.pop()
            if u in c: continue
            c.add(u); st.extend(w for w in adj[u] if w not in c)
        seen|=c; comps.append(sorted(c))
    out=[]
    for c in comps:
        idx={a:i for i,a in enumerate(c)}
        out.append(([sp[a] for a in c],
                    sorted((idx[a],idx[b]) for a,b in keep if a in idx and b in idx)))
    return out

def canon(sp,bonds):
    """crude canonical graph hash: iterative Weisfeiler-Lehman refinement"""
    n=len(sp); adj=collections.defaultdict(list)
    for a,b in bonds: adj[a].append(b); adj[b].append(a)
    lab={i:sp[i] for i in range(n)}
    for _ in range(4):
        lab={i:lab[i]+'|'+','.join(sorted(lab[j] for j in adj[i])) for i in range(n)}
        # compress
        m={v:k for k,v in enumerate(sorted(set(lab.values())))}
        lab={i:str(m[lab[i]]) for i in range(n)}
    return tuple(sorted(lab.values()))

def formula(sp):
    c=collections.Counter(sp)
    return ' '.join(f'{e}{c[e]}' for e in sorted(c))

Z={'H':1,'Li':3,'C':6,'O':8,'F':9,'P':15}

# ---- 1. FRAGMENT: break up to 2 bonds ----
frags={}   # formula -> set of graph hashes
frag_graphs=set()
for name,(sp,bonds) in PRINCIPALS.items():
    nb=len(bonds)
    for k in (0,1,2):
        for rem in itertools.combinations(range(nb),k):
            for fsp,fb in components(sp,bonds,set(rem)):
                f=formula(fsp); h=canon(fsp,fb)
                frags.setdefault(f,set()).add(h); frag_graphs.add((f,h))
print(f'[1] fragments: {len(frag_graphs)} unique (formula,graph); {len(frags)} unique formula')

# ---- 2. RECOMBINE: pairs and Li-coordination triples ----
fl=sorted(frags)
def addf(a,b):
    ca=collections.Counter(); 
    for f in (a,b):
        for tok in f.split():
            m=re.match(r'([A-Z][a-z]?)(\d+)',tok); ca[m.group(1)]+=int(m.group(2))
    return ' '.join(f'{e}{ca[e]}' for e in sorted(ca))

pool=set(fl)
for a,b in itertools.combinations_with_replacement(fl,2):
    pool.add(addf(a,b))
print(f'[2] after pairwise recombination: {len(pool)} unique formula')
# Li+ coordination: Li + (up to 2 solvent-derived fragments) already covered by pairs;
# add Li + pair  (i.e. triples containing Li)
tri=set()
for a,b in itertools.combinations_with_replacement(fl,2):
    tri.add(addf('Li1',addf(a,b)))
pool|=tri
print(f'[3] + Li-coordination triples: {len(pool)} unique formula')

# ---- 3. size filter: LIBE ceiling is 22 atoms ----
def natoms(f):
    return sum(int(re.match(r'([A-Z][a-z]?)(\d+)',t).group(2)) for t in f.split())
pool22={f for f in pool if natoms(f)<=22}
print(f'[4] pool with <=22 atoms (LIBE-comparable): {len(pool22)}')

# ---- 4. charge/spin states ----
def nel(f):
    return sum(Z[re.match(r'([A-Z][a-z]?)(\d+)',t).group(1)]*int(re.match(r'([A-Z][a-z]?)(\d+)',t).group(2)) for t in f.split())
targets=set()
for f in pool22:
    for q in (-1,0,1):
        e=nel(f)-q
        if e<=0: continue
        targets.add((f,q,1 if e%2==0 else 2))
print(f'[5] target (formula,charge,spin) states: {len(targets)}')
json.dump({'pool_formula':sorted(pool22),'targets':sorted(map(list,targets))},
          open('s2a_pool.json','w'))
