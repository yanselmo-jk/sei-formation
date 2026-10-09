"""Valence-aware fragment-recombine (LIBE's 'selective recombination').
Blind composition addition invents species with no valid valence structure.
Real recombination joins fragments at OPEN VALENCE (radical) sites."""
import json, itertools, collections, re
VAL={'H':1,'Li':1,'C':4,'O':2,'F':1,'P':6}   # P:6 makes PF6 saturated (hypervalent)
def EC():
    sp=['C','O','O','C','C','O','H','H','H','H']
    return sp,[(0,1),(0,1),(0,2),(2,3),(3,4),(4,5),(5,0),(3,6),(3,7),(4,8),(4,9)]
def EMC():
    sp=['C','O','C','O','O','C','C']+['H']*8
    return sp,[(0,1),(1,2),(2,3),(2,3),(2,4),(4,5),(5,6),
               (0,7),(0,8),(0,9),(5,10),(5,11),(6,12),(6,13),(6,14)]
def LI():  return ['Li'],[]
def PF6(): return ['P']+['F']*6,[(0,i) for i in range(1,7)]
PRINCIPALS={'EC':EC(),'EMC':EMC(),'Li':LI(),'PF6':PF6()}

def components(sp,bonds,removed):
    keep=[b for i,b in enumerate(bonds) if i not in removed]
    adj=collections.defaultdict(set)
    for a,b in keep: adj[a].add(b); adj[b].add(a)
    seen=set(); out=[]
    for s in range(len(sp)):
        if s in seen: continue
        st=[s]; c=set()
        while st:
            u=st.pop()
            if u in c: continue
            c.add(u); st.extend(w for w in adj[u] if w not in c)
        seen|=c; c=sorted(c); idx={a:i for i,a in enumerate(c)}
        out.append(([sp[a] for a in c],[(idx[a],idx[b]) for a,b in keep if a in idx and b in idx]))
    return out
def openval(sp,bonds):
    deg=collections.Counter()
    for a,b in bonds: deg[a]+=1; deg[b]+=1
    return sum(max(0,VAL[sp[i]]-deg[i]) for i in range(len(sp)))
def formula(sp):
    c=collections.Counter(sp); return ' '.join(f'{e}{c[e]}' for e in sorted(c))
def addf(a,b):
    ca=collections.Counter()
    for f in (a,b):
        for t in f.split():
            m=re.match(r'([A-Z][a-z]?)(\d+)',t); ca[m.group(1)]+=int(m.group(2))
    return ' '.join(f'{e}{ca[e]}' for e in sorted(ca))
def natoms(f): return sum(int(re.match(r'([A-Z][a-z]?)(\d+)',t).group(2)) for t in f.split())
def nLi(f):
    m=re.search(r'Li(\d+)',f); return int(m.group(1)) if m else 0

# --- fragments with open-valence bookkeeping ---
frs={}                       # formula -> max open valence
for name,(sp,bonds) in PRINCIPALS.items():
    for k in (0,1,2):
        for rem in itertools.combinations(range(len(bonds)),k):
            for fsp,fb in components(sp,bonds,set(rem)):
                f=formula(fsp); ov=openval(fsp,fb)
                frs[f]=max(frs.get(f,0),ov)
print(f'[1] unique fragment formulas: {len(frs)}  (open-valence>0: {sum(1 for v in frs.values() if v>0)})')

pool=set(frs)
# --- covalent recombination: BOTH partners need an open valence ---
rad=[f for f,v in frs.items() if v>0]
for a,b in itertools.combinations_with_replacement(rad,2):
    pool.add(addf(a,b))
print(f'[2] + covalent recombination (radical x radical): {len(pool)}')
# --- Li coordination: Li+ may coordinate any O/F-bearing species (dative, no open valence needed) ---
coord={f for f in list(pool) if ('O' in f or 'F' in f)}
for f in coord:
    pool.add(addf('Li1',f))
    pool.add(addf('Li2',f))
print(f'[3] + Li/Li2 coordination: {len(pool)}')

# --- chemical sanity filters (generic, NOT species-specific) ---
def ok(f):
    if natoms(f)>22: return False           # LIBE ceiling
    if nLi(f)>2: return False               # >2 Li = cluster, out of molecular CRN scope
    els=set(re.match(r'([A-Z][a-z]?)',t).group(1) for t in f.split())
    if els<= {'Li'}: return False           # bare Li_n
    if els<={'Li','H'}: return False        # LiH_n clusters: not in scope
    return True
pool={f for f in pool if ok(f)}
print(f'[4] after sanity filters (<=22 atoms, <=2 Li, no bare Li/LiH clusters): {len(pool)}')
Z={'H':1,'Li':3,'C':6,'O':8,'F':9,'P':15}
def nel(f): return sum(Z[re.match(r'([A-Z][a-z]?)(\d+)',t).group(1)]*int(re.match(r'([A-Z][a-z]?)(\d+)',t).group(2)) for t in f.split())
tg=set()
for f in pool:
    for q in (-1,0,1):
        e=nel(f)-q
        if e>0: tg.add((f,q,1 if e%2==0 else 2))
print(f'[5] target (formula,charge,spin): {len(tg)}')
json.dump({'pool':sorted(pool),'targets':sorted(map(list,tg))},open('s2a_pool2.json','w'))
