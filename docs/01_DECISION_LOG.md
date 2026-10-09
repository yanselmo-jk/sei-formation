# Decision Log (ADR)

organizer만 이 파일에 기록한다. 결정은 되돌릴 수 있으나, **지운 기록은 남긴다**
(Status를 `Superseded by ADR-NNN`으로 바꾸고 원문은 보존).

## 🔴 READ THIS FIRST — live values, superseded values (2026-08-19, rules through 35)

> Written after both teammates applied the same fix to their own documents, and after this file's
> own recent ADRs corrected each other three times. **If anything later in this file conflicts with
> this block, THE BLOCK WINS** until a replacement block is issued.
> 🔒 *A structure outside the loop beats care inside it.*

### LIVE
```
κ_thread      1.207  [MEASURED]        equal thread counts (P6_t16 214 s vs ref 177.3 s)
κ_physical    ~2.4   [ESTIMATE]        ⟵ THE OPERATIVE PLANNING VALUE. Budgets are in a
                                          PHYSICAL-CORE convention (03_COMPUTE_PLAN:5581)
S             1.551  [MEASURED]        16→64. packing gain 4/S = 2.58 ⟹ PACK, don't widen
r_composite   1.14 – 1.30 (n=2)        ADR-032 planned 1.25 and WAS RIGHT
r_high        1.5284 only (n=1)        gate 2-3 OPEN
u_cheap       🔴 60 core-h INVALIDATED — §R18.5 and everything downstream rest on it
B0 gate       ~5,000 – 15,000 ref-core-h   ← the only thing requested
B0 GUARD      🔴 15,000 REFERENCE is the AUTHORITY; the guard counts KNL ⟹ 36,000 KNL, DERIVED.
              **36,000 is NOT a raise** — RT-1's 21,000 KNL = 8,750 ref, i.e. STRICTER.
              `B0_APPROVED_REFERENCE_CORE_HOURS = 15000.0` is the only place a figure is typed.
Li–X cutoff   2.75 Å [MEASURED, MLIP RDF first minimum, user 2026-08-19]  ⟵ was 2.4 PLACEHOLDER
              🔴 Layer-I verdicts computed under 2.4 must be RECOMPUTED, not grandfathered.
              ⚠ NOT element-resolved — the user gave Li–X generically.
U-55 primary  🔒 PRE-REGISTERED 2026-08-19 before any data: **κ₂ vs opt_cycles.** The other 17
              correlations are exploratory pointers, NEVER decision-making (n=23, 18 tests).
              🔴 Do NOT justify k=2 with the 6,000× ladder figure — SYNTHETIC fixture.
V-2a          17,000 reserved [ESTIMATE derived from an ESTIMATE]
schedule      weeks = 4.0κ(100/N) + 9.5 + 3.0·n_recomp ⟹ κ=2.4, N=200: 14.3/17.3/20.3 wk
```

### 🔴 SUPERSEDED — DO NOT QUOTE THESE
| dead value | where it appears | correction |
|---|---|---|
| `r_composite 1.04–1.14` | ADR-064 as first written | **ADR-065** — range narrowed by omission |
| `r_composite 1.0365–1.30` | ADR-064's own first correction | **ADR-065** — still contained a VOID point |
| `r_high = 0.3816` | ADR-064 | **ADR-065** — numerator did not converge; VOID |
| "P1 failed chemically; QST2 found a shallow saddle" | ADR-064 | **ADR-066** — artefact. `n_frames = 1` per direction |
| "P1 is evidence against QST2" | implied by ADR-064/066 | **ADR-066** — QST2's preconditions were never met |
| U-55 "the design leans on the class that did not converge" | **ADR-065, lead's wording** | **ADR-067** — WITHDRAWN to UNDECIDED |
| "floppy Li⁺ manifold" as a finding | ADR-065 | **ADR-067** — over-symmetric input explains it entirely |
| `V-2a 4,000–60,000` / `600–8,000` / `700–5,000` / `11,700` | ADR-070/072 | **17,000** (ADR-072 + lead ruling) |
| "§R16.8 is a real cost anchor" | ADR-072 as relayed | **ADR-072/073** — it is `[ESTIMATE]`, and NO VASP HAS EVER BEEN MEASURED HERE |
| DFT MD requested, 130–700 | ADR-070 | withdrawn in favour of the MLIP; **reserved-not-deleted** |
| `40–100 atoms/frame` | engineer5's pricing | **ADR-072** — it was the atom count of a REJECTED option |
| "unmeasured VASP ⟹ LiF:Li2CO3 ⟹ ADR-003 axis (b)" | **ADR-073, relayed by the lead** | **ADR-074** — middle link false; class A uses EXPERIMENTAL anchors. The correct target is ADR-014 transferability, and it is BIGGER |

### 🔒 Rules that earned themselves this round
```
17  separate "the event I observed" from "what I inferred it breached"
18  decide a gate's FAILURE DIRECTION before writing it. A gate that falls toward PASS is worse
    than no gate.
19  print a discovery set and read it — and state what it EXCLUDES, not only what it includes
20  when a check passes, state the PROPERTY it establishes, not the NAME of what it ran on.
    🔴 Applies to any inference from a proxy — including a proxy that worked for a DIFFERENT CODE.
21  a confirmation is independent only if the value did not originate with us
22  an expected value derived from our own code tests only that the code has not changed
23  an experiment that does not reproduce the hypothesis proves nothing in either direction
24  a revert result has a shelf life; re-run it after the test file changes
25  a snapshot taken mid-experiment carries the experiment
🔴 26 (this round, four instances): BEFORE ATTRIBUTING A COMPUTATIONAL FAILURE TO THE CHEMISTRY,
    CHECK THE INPUT. P1's "chemical failure", r_composite ≈ 1.04, the floppy-manifold hypothesis,
    and the 90.3° Li–O=C angle had ONE cause, and every time the disqualifying fact was written in
    the artefact and unread — a header line, a `converged: false`, a bond count, `n_frames: 1`.
    **The chemistry hypothesis is the expensive one, and it was the second thing to check every time.**
🔴 27 (three instances in one round): WHEN AN ENTRY IS AMENDED, THE AMENDMENT GOES IN THE AMENDED
    ENTRY'S TITLE — not only in the amending one's.
    🔒 The backward link is the one that gets followed; the forward link is the one that gets written.
    A 75-entry log is read by SCANNING TITLES, so a correction living in another entry's body is
    invisible to the reader who most needs it.
    Instances: qc_levels.json's unanswered "[confirmation requested]" · §39.16(g) headed
    "Final number" and revised two rounds later · ADR-073's title naming an observable its own
    body no longer claims.
🔴 28  GREP HEADINGS FOR FINALITY WORDS — final · confirmed · settled · closed · 확정 · 최종 —
    AND CHECK EACH ONE STILL IS. That word class suppresses further reading, which is exactly why
    stale claims survive longest there.
    Found by this pass, in the lead's own STATE: "vasp_std 6.4.3 present" sat inside a block headed
    "settled [MEASURED] — do not re-run these", hours after we established PRESENT ≠ CAN COMPUTE.
    🔴 A LATER PASS (2026-08-19) found TWO MORE, both the lead's: an entry headed "guard 22,000
    기각 — 확정" whose numbers are KNL and which reads as a violation next to B0's 36,000; and a
    ledger headed "CURRENT" whose B0-D range still priced arm 2 at 23 species after ADR-078 cut it
    to 3. **That heading had already been demoted from "FINAL" once. It went stale a third time.**
🔴 29  WHEN A CORRECTION FACTOR IS INHERITED, RE-CHECK WHICH ENGINE IT WAS DERIVED FOR BEFORE
    RE-CHECKING ITS ARITHMETIC. ADR-047's `T_eff ≈ T/2` was arithmetically flawless and applied to
    the wrong protocol — derived for DRC (mechanism-following, NVE), applied to a ladder owned by
    reactive MD (sampling). **No amount of verifying the algebra would have found that.**
    🔒 Same family as rule 20, but for a NUMBER rather than a CHECK — which is why it evaded a team
    that had already learned rule 20. (ADR-079)
🔴 30  A QUALITATIVE WORD WHERE A NUMBER WAS AVAILABLE IS A MEASUREMENT NOT TAKEN.
    **Asymmetric application across comparable objects is the tell** — the file that got the word
    looks fine next to the file that got the number. Instance: §39.4(g) called an angle "linear"
    while §39.14(g) quantified the analogous one at 90.3° and called it "wrong against
    measurement". Both were comparably wrong (+42° and −48°). (ADR-080)
🔴 31  A REMEDY IS NOT FREE UNTIL THE OPTION IS CONFIRMED TO **EXIST IN THE ENGINE.**
    "Specify X, cost zero" prices the DECISION and silently assumes the CAPABILITY. Instance:
    "use a Nosé–Hoover or Langevin thermostat, cost 0" — **xtb 6.7.1 has exactly one thermostat and
    it is Berendsen.** The gap was invisible from every document; only the binary had it.
    🟢 `strings <binary>` is a ZERO-COST CAPABILITY CHECK. Run it before pricing a spec at zero. (ADR-081)
🔴 32  A RULE WRITTEN ABOUT ONE OBJECT DOES NOT TRANSFER TO THE NEXT OBJECT OF THE SAME KIND
    WITHOUT SOMEONE CHECKING — **and the AUTHOR is the least likely person to notice, because they
    know they already wrote it.** Instance: proposer5's §39.4(c) *"do NOT hard-code a threshold this
    round; that is how −100 got there"*, then `SOFT_MODE_CM1 = 50` two sections later.
    🔒 Fourth instance this session of a defence that existed and was not applied one step
    sideways (rule 20's CP2K→VASP · the PFL trigger variable · the thermostat tree's omitted bias
    variable · this). (ADR-082)
🔴 33  A SUPPLIED ARTEFACT MUST BE VERIFIED AGAINST SOMETHING IT COULD NOT HAVE BEEN FITTED TO,
    BEFORE IT IS USED TO VALIDATE ANYTHING. Instance: the user's G16 eigenvalue block — electron
    count from the molecular formula (49) and multiplicity from a separate report field (2), both
    derivable WITHOUT trusting the block, both agreeing. **Without that step, "the parser matched
    the sample" only shows the sample matched the parser.**
    🔒 Companion to 21: **21 is about who produced a NUMBER; 33 is about what independently
    constrains an ARTEFACT.** (ADR-084)
🔴 34  A FIX THAT SPLITS ONE CONCEPT INTO TWO MUST BE CHECKED AGAINST THE INPUTS WHERE THE **SECOND
    CONCEPT DOES NOT EXIST.** Instance: splitting HOMO from SOMO introduced `n_alpha > n_beta`,
    which fires on a RESTRICTED log (no Beta block ⟹ n_beta = 0) and reports a SOMO for a
    doubly-occupied orbital — **all 19 closed-shell singlets, silently.**
    🔴 The fix for one conflation created another, IN THE SAME EDIT, and the alpha/beta framing
    that makes the split natural is exactly what hides the case. (ADR-085)
🔴 35  A VERIFIED FREEZE POINT IS ONLY VALID WHILE NOTHING IS RUNNING — and **a list of "what
    remains" is STALE BY CONSTRUCTION whenever the other party is still working.**
    Instances, both within twenty minutes on 2026-08-19: the lead verified a tree
    (`7226a82f95f862e0`, 1115 tests), reported *"ready to restart"*, and the digest moved to
    `4a484eb71ef2b36d` / 1122 while the report was being written — **and the handoff file was
    renamed, leaving THREE dead paths in the lead's own STATE.** Separately the lead's open-items
    list went stale **in both directions**: four items listed open were already done, two listed
    open landed in flight.
    🔒 **Verify only after confirming the other party has STOPPED, and stamp the verification with
    what it is conditional on.** ⟹ **Trust the code over the handoff, and the handoff over any
    lead list.** `grep` for the symbol before implementing anything from a checklist.
```

## 형식

```
## ADR-NNN: <한 줄 제목>
- **Status**: Proposed | Accepted | Superseded by ADR-NNN | Rejected
- **Date**: YYYY-MM-DD
- **Stage**: S1 | S2 | S3 | S4 | Infra
- **Resolves**: U-NN (05_STATE.md의 미확정 항목)
- **Context**: 무엇을 정해야 했는가
- **Proposer 입장**: (정확도 관점 요약 + 근거)
- **Engineer 입장**: (비용/시간 관점 요약 + 견적)
- **Decision**: 무엇으로 정했는가
- **Rationale**: 왜. trade-off에서 무엇을 포기했는가
- **Consequences**: 이 결정이 강제하는 후속 작업 / 닫아버린 선택지
- **Revisit trigger**: 어떤 조건이 관측되면 이 결정을 재검토하는가
```

---

<!-- 첫 ADR부터 아래에 append -->

## ADR-001: 대상 electrolyte를 EC:EMC 3:7 + 1M LiPF6로 고정하되 조성 확장성을 구조적 요구사항으로 둔다

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra (S1~S4 전체 구속)
- **Resolves**: U-01
- **Context**: 대상 조성이 정해지지 않으면 S1의 species 목록, S2의 network 초기 노드,
  S3의 TS 개수, S4의 관측량이 전부 미정이다. 다른 모든 U-NN의 상위 의존성.
- **Proposer 입장**: N/A — 사용자 지정 사항. (방법론 판단이 아니라 연구 대상 정의)
- **Engineer 입장**: N/A — 사용자 지정 사항.
- **Decision**:
  - 1차 대상: **EC:EMC 3:7 (v/v) + 1M LiPF6**. 첨가제 없음.
  - 명시적으로 다룰 1차 species: EC, EMC, Li+, PF6-, 그리고 이들의 solvation complex.
  - **확장성이 기능 요구사항이다.** 새 species(FEC, VC, DMC, LiFSI, …) 도입 시 추가 개발
    기간 **~1개월**로 흡수 가능해야 한다. 즉 species-specific 하드코딩 금지.
- **Rationale**: 상용 LIB 표준 baseline이라 문헌·실험 비교점이 가장 많고, EC 환원은 SEI
  형성의 정준 출발점이라 S1 게이트 검증이 가능하다. species 수가 적어 S2 network 폭발
  위험도 가장 낮다. 첨가제(FEC 등)는 F계 부반응 경로를 크게 늘리므로 1차 범위에서 제외한다.
- **Consequences**:
  - S2 탐색 엔진(U-04)은 **조성 불가지론적(composition-agnostic)** 이어야 한다.
    EC 전용 반응 규칙을 손으로 나열하는 접근은 1개월 확장 요구를 만족하지 못하므로
    사실상 배제된다. proposer/engineer는 이 제약 하에서 후보를 재단할 것.
  - species 목록·반응 규칙·thermo 파라미터는 코드가 아니라 **데이터(설정 파일/DB)** 로
    분리되어야 한다. coder 단계의 구속 조건.
  - PF6- 분해(→ PF5, POF3, LiF)를 1차 network에 포함한다. LiF는 U-10 검증 대상이다.
- **Revisit trigger**: 1차 파이프라인이 XPS 조성비를 재현하지 못하고, 그 원인이 첨가제
  부재가 아니라 조성 정의 자체에 있다고 판명될 때.

---

## ADR-002: anode 표면을 명시적으로 다루지 않는다 — bulk/cluster 환원만

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S1
- **Resolves**: U-02
- **Context**: 표면을 명시하면 S1이 slab DFT/AIMD + 전위 제어(grand-canonical 등)로
  가고, 비용이 1~2 order 오른다. 표면을 빼면 값싸지만 표면 촉매 효과와 전극전위
  의존성을 잃는다.
- **Proposer 입장**: N/A — 사용자 지정 사항.
- **Engineer 입장**: N/A — 사용자 지정 사항. (비용 상한이 크게 완화됨)
- **Decision**: **표면 없음.** 전자 이동은 bulk electrolyte 내 species / solvation
  complex에 대한 환원으로 다룬다. slab, 전극, 계면 이중층은 1차 범위에서 제외한다.
- **Rationale**: 3~5개월 안에 S1→S4 전 구간을 관통하려면 S1에서 예산을 다 태울 수 없다.
  또한 검증 대상(U-10)인 가스 발생종과 SEI 조성비는 대체로 **용액상 환원 후 후속
  화학**이 지배하므로, 표면 없이도 지배 경로 식별은 가능하다는 판단.
- **Consequences**:
  - **전자의 화학퍼텐셜(전극전위)을 외부 파라미터로 명시해야 한다.** 표면이 없으므로
    "몇 V vs Li/Li+에서의 환원인가"가 계산에 자동으로 들어오지 않는다. S1 방법론 제안은
    반드시 (a) 절대 전위 기준(reference) 설정 방법과 (b) 계산된 환원전위를 실험
    dQ/dV peak과 대조하는 절차를 포함해야 한다. **이것 없는 S1 제안은 미완성으로 간주한다.**
  - solvation 환경 정의가 S1 정확도의 지배 인자가 된다. implicit-only는 Li+ 배위가
    환원전위를 크게 바꾸므로 정당화 없이 채택 불가.
  - 표면 촉매 효과, 전자 터널링 거리 의존성, SEI 성장에 따른 전자 전달 차단은
    모델링되지 않는다. → S4에서 두께 성장의 self-limiting 메커니즘은 **가정으로 들어가며,
    그 가정을 명시해야 한다.**
- **Revisit trigger**: S1 게이트에서 계산 환원전위가 실험값과 정성적으로도 어긋나고
  그 원인이 표면 부재로 지목될 때. 또는 S4가 self-limiting 성장을 전혀 재현하지 못할 때.

---

## ADR-003: 검증 관측량은 가스 발생종과 XPS 조성비 두 축으로 하고, 개발 기간은 3~5개월로 둔다

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra (S2·S4 구속)
- **Resolves**: U-10, 일정 상한
- **Context**: 무엇과 비교할지가 정해져야 S2의 network 완결성 기준과 S4의 출력 형식이
  정해진다. 일정 상한이 정해져야 engineer가 예산 봉투를 그릴 수 있다.
- **Proposer 입장**: N/A — 사용자 지정 사항.
- **Engineer 입장**: N/A — 사용자 지정 사항.
- **Decision**:
  - 검증 축 1: **가스 발생종 상대 수율** — C2H4, CO, CO2 (DEMS 관측량과 대조)
  - 검증 축 2: **XPS 기반 SEI 조성비** — LiF, Li2CO3, LEDC, ROCO2Li 등의 상대 비율
  - 일정: 1차 조성 파이프라인 **3~5개월**. 신규 species 추가 시 **+~1개월**.
- **Rationale**: 두 관측량은 서로 독립적인 network 영역을 검증한다. 가스종은 EC
  환원의 ring-opening 이후 분기(1e- vs 2e-, C2H4 방출 vs CO 방출)를 직접 구속하고,
  XPS 조성비는 응축상 생성물 분기를 구속한다. 둘을 함께 맞추는 것이 어느 하나만
  맞추는 것보다 훨씬 강한 제약이며, 지배 경로 오식별을 막는다.
- **Consequences**:
  - **pruning(U-05)은 이 두 관측량으로 가는 경로를 잘라내면 안 된다.** 순수 에너지
    cutoff만으로 자르면 소수 생성물인 가스종 경로가 먼저 죽는다. flux 기반 기준과
    "관측량 도달 경로 보호" 규칙이 함께 필요하다. proposer는 이를 반영해 U-05를 설계할 것.
  - S2→S3 게이트 통과 조건에 **C2H4, CO, CO2, LiF, Li2CO3, LEDC가 network 안에
    실제로 노드로 존재할 것**이 포함된다.
  - S4 출력은 두께뿐 아니라 **species별 몰 수율(가스/응축상 분리)** 을 반드시 낸다.
  - SEI 두께·성장 kinetics는 1차 검증 대상이 아니다 → S4에서 공간 차원(1D 성장 모델)은
    필수가 아니며, 이는 U-08의 비용을 크게 낮춘다.
- **Revisit trigger**: 두 관측량을 동시에 맞추는 파라미터 집합이 존재하지 않는 것으로
  판명될 때(모델 구조 결함 신호). 또는 사용자가 두께 성장을 1차 목표로 승격할 때.

---

## ADR-004: 계산 자원 실사양 확정 — 전용 기준선, 그러나 HPC 직접 접근은 불가

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra
- **Resolves**: engineer의 A2·A4 가정, 인력 규모. **A1/A3/A8은 여전히 `[UNRESOLVED]`**
- **Context**: engineer가 `03_COMPUTE_PLAN.md` §0에서 하드웨어 가정 A1~A8을 세우고
  "A4(점유율)와 A2(wall-time)가 문서 전체 숫자를 지배한다"고 지목, lead 경유 확인을 요청.
  실행 환경 관측 결과 현재 세션은 16 vCPU WSL 박스이며 GPU·스케줄러가 없어
  **engineer는 실자원을 한 번도 관측하지 못한 채 견적을 냈다.**
- **Proposer 입장**: N/A (이 라운드 미참여)
- **Engineer 입장**: 공유(1.35 M core-h)를 계획 기준선으로 삼아야 하며 전용을 전제한
  계획은 공유로 떨어지는 순간 5.7배 초과로 즉사한다. 단 **전용을 받아도 실효 이득은
  달력 기준 1.5~2배**인데, 실질 상한이 core-hour가 아니라 (i) S3의 인간 실패 triage
  시간, (ii) AIMD 궤적의 직렬성, (iii) MLIP AL 재학습의 직렬성이기 때문.
- **Decision**:
  1. **A4 = 전용에 가까움.** 기준선 봉투를 **7.74 M core-h / 12,000 GPU-h**로 개정한다.
  2. **A2 = wall-time 상한 24 h.** engineer 가정이 정확했다. 체크포인팅 설계 유지.
  3. **인력 = 2~3명.** ⇒ S3 명시적 DFT TS **계획 300건 / 하드 실링 500건** 유지.
     (1명이었다면 250건으로 내려야 했다.)
  4. 🔴 **HPC 직접 접근 불가. 사용자가 수동 제출한다.**
- **Rationale**: 전용 자원이 확인됐으므로 봉투를 올리는 것이 맞다. 그러나 engineer의
  "전용이어도 1.5~2배"라는 경고는 **철회하지 않는다.** 병목이 core-hour가 아니라
  wall-clock과 인간 시간이라는 진단이 자원 확대로 무효화되지 않기 때문이다.
  자원이 늘었다고 stage를 새로 추가하는 것은 금지하며, 여유는 S3 건수·S1 샘플·예비분에만 쓴다.
- **Consequences**:
  - 🔴 **파일럿 P1~P3를 우리가 실행할 수 없다.** engineer가 "W1-3 최우선 과업"으로
    지목한, 단가 스프레드 8배→3배 축소 작업이 **사용자 왕복에 의존**하게 됐다.
    ⇒ 모든 단가는 사용자 회신 전까지 **`[ESTIMATE]`로 남는다.** 8배 스프레드를 안고 간다.
  - ⇒ 파일럿은 **인도 패키지**로 재정의된다: 스케줄러 비의존 실행 진입점 + A1/A3/A8을
    자동 측정하는 프로브 잡 + 구조화 출력(JSON/YAML) + 스크립트 내장 성공/실패 판정.
    **우리가 못 보는 것을 스크립트가 보게 만든다.** coder의 1순위 산출물이 된다.
  - ⇒ 일정에 **인간 왕복 지연**(패키지 인도 → 사용자 실행 → 결과 회신)이 신규 임계
    경로 항목으로 추가된다. engineer §10 인간 시간 예산에 없던 항목이다.
  - ⇒ U-09 재검토 필요: **워크플로 매니저를 우리가 운영할 수 없고 사용자가 운영한다.**
    원격 운영 부담과 셋업 난이도의 가중치가 올라가므로 Parsl+jobflow ↔ AiiDA 판단이
    바뀔 수 있다. engineer에게 재판정 지시함.
  - 코드는 **우리 환경에서 실행 검증이 불가능하다.** critic의 역할이 통상보다 무거워진다
    (실행으로 못 잡는 오류를 정적 검토로 잡아야 함).
- **Revisit trigger**: 사용자가 SSH 접근을 열어줄 때(즉시 파일럿 직접 실행으로 전환).
  또는 파일럿 회신 결과가 `[ESTIMATE]` 대비 2배 이상 벗어날 때(봉투 전면 재계산).

---

## ADR-005: S1 방법 = cluster+implicit 전수(tier-1) + AIMD 진단 4계(tier-2). GC-DFT는 방법론적으로 배제

- **Status**: Accepted (tier-2 내부 분기는 P2 파일럿에 종속)
- **Date**: 2026-08-17
- **Stage**: S1
- **Resolves**: **U-03**
- **Context**: ADR-002가 표면을 제거해 전자의 화학퍼텐셜이 계산에 자동으로 들어오지 않는
  상태에서, 환원 barrier를 어떤 방법으로 낼 것인가.
- **Proposer 입장**: 단일 방법으로는 불가. `S1-A`(MD-표집 cluster–continuum, 열역학 사이클
  + Nelsen 4-point λ)는 E_red 절대값 ±0.2~0.3 V이나 **동일 족 내 상대 간격은 ±0.05~0.1 V**로
  훨씬 좋다. 그러나 cluster+SMD는 **outer-sphere λ를 계통적으로 과소평가**하며, 그 편향이
  유효 반경 a와 전하변화 유형에 따라 **차등적으로** 걸려 상쇄되지 않는다.
  `S1-B`(explicit AIMD 수직 에너지갭, linear-response Marcus)는 절대값 생산이 아니라
  (i) S1-A의 λ 편향 크기 측정, (ii) **mechanism_flag(stepwise vs concerted) 판정**이 목적.
- **Engineer 입장**: S1 상한 200 k core-h. (a) cluster+implicit 74 k(0.37×) 통과 — 권장
  baseline. (c) Marcus AIMD GGA 150 k(0.75×) 조건부 통과. **hybrid AIMD 2.2~5.5 M = 봉투의
  1.6~4배, 즉사** → PBE 궤적 + hybrid SP 재가중(48 k, 2% 비용)으로 대체 제안.
  **(d) grand-canonical DFT 720 k = S1 상한의 3.6배, 예산 내 불가.**
- **Decision**:
  1. **2-tier 채택.** tier-1 = S1-A를 전 species 전수(opt+freq **250건**, 상한 600의 42%).
     tier-2 = S1-B를 **4계에만** 적용.
  2. **tier-2 4계 확정**: ① Li⁺(EC)₄ (SSIP) ② 자유 EC ③ Li⁺(EC)₃(PF6⁻) (CIP)
     ④ 개환 EC 라디칼의 2차 환원. ①②는 **쌍으로만 의미**가 있다(차등 λ 측정).
  3. **AIMD 설계**: Stage A(탐색, 4계 × 환원상태 × 7 ps = 28 ps, **비구속** PBE) →
     Stage B(생산, ≤240 ps 등가). **합계 ≤268 ps < 상한 300 ps.**
  4. **hybrid AIMD 0 ps.** 대신 PBE 궤적 위 hybrid single-point.
  5. 🔴 **[통과 조건 G-AIMD]** 환원상태 궤적의 표적 분자 위 스핀밀도 `s(t)`를 기록한다.
     `⟨s⟩>0.8` → 비구속 4계 유지 + hybrid SP. `⟨s⟩<0.5` → **PBE 궤적 무효**,
     **cDFT로 diabat 강제**(비용 1.5~2.5배 ⟹ 계 수 4→2, ①②만 남김). 회색(0.5~0.8) → lead 판정.
     **분기는 P2 파일럿의 1 ps 실측으로 조기 결정한다.**
  6. **전위 기준**: §1.1 **R2(동일-프로토콜 내부 Li⁺/Li 기준)를 1차**로 한다. R1(Trasatti)은
     비교 보고용. **R3(실험 앵커 선형 교정)는 선택 항목으로 강등**(아래 7).
  7. **R3 앵커 세트(60 job, ~12 k core-h)를 포기하고 tier-2의 4번째 계를 산다.**
  8. 🔴 **grand-canonical DFT 배제 — 비용이 아니라 방법론 사유로.**
  9. **S1 게이트는 절대값이 아니라 순서·간격·창으로 잡는다** (§1.2 C1/C2/C3).
- **Rationale**:
  - **왜 2-tier인가**: proposer가 `∂ΔG‡/∂λ = ¼[1−(ΔG/λ)²]`를 실제로 계산했고, 우리 조건
    (U≈0.8 V, E_red≈0.5~0.8 V ⟹ |ΔG|/λ≈0.15)에서 배율이 **정확히 ¼**임을 보였다.
    ⟹ **λ 오차 0.4 eV = ΔG‡ 오차 0.1 eV = rate 50배.** λ를 방치할 수 없다.
  - **왜 하필 그 4계인가**: ADR-003 관측량이 *비(ratio)* 라서 오차가 상쇄될 것 같지만,
    λ_out ∝ (1/2a − 1/R)(1/ε_op − 1/ε_s)이므로 **유효 반경과 전하변화 유형이 다르면
    차등 오차가 되어 상쇄되지 않는다.** 자유 EC(0→−1, a≈2.8 Å) ↔ Li⁺(EC)₄(+1→0, a≈4.5 Å)의
    λ 차이가 0.2~0.4 eV ⟹ ΔG‡ 0.05~0.1 eV ⟹ **rate 비 7~50배** ⟹ 어느 종이 먼저
    환원되는지가 뒤집힐 수 있다. 반면 **EC vs EMC는 전하변화 유형·반경이 같아 상쇄되므로
    tier-1으로 충분하다.** ④는 1e⁻/2e⁻ 분기 = **C2H4 방출 vs CO 방출** 분기를 통제하는데,
    λ 오차가 ET 쪽에만 걸리는 비대칭 오차라 상쇄되지 않는다 — **ADR-003 축(a)의 본체.**
  - **왜 R3를 버리고 4계를 샀는가**: proposer 스스로 R3의 carbonate계 가역 앵커 확보가
    불확실하고 화학종족이 달라 전이 가능성이 의심스럽다고 평가했다.
    **불확실한 교정층보다 확실한 검증축을 산다.**
  - **왜 GC-DFT가 "불필요"가 아니라 "해로운"가**: GC-DFT는 분자 용질에 **분수 전자수** 상태를
    강제한다. 정확한 범함수의 E(N)은 정수점 사이에서 구간선형이어야 하나 근사 범함수는
    볼록이고, 그 편차(비편재화/SIE 오차)는 **정확히 분수 점유에서 최대**가 된다.
    ⟹ 우리가 §7.2에서 가장 걱정하는 그 오차를 능동적으로 증폭시킨다. 게다가 전극이 없으면
    분수 전자를 담을 물리적 저장소가 없어 물리적 대응물이 없는 수학적 산물이 된다.
    대안(`ΔG(e⁻) = −eU + const`, R2)은 **정수 전자 이동만 다뤄 분수 점유 문제가 원천적으로
    없다.** ⟹ 열등한 우회로가 아니라 정공법이다. engineer의 비용 논거보다 이쪽이 강하다.
  - **왜 hybrid SP를 "재가중"이라 부르지 않는가**: 형식적으로는 중요도 재가중이 가능하나,
    ΔΔE 요동이 계 크기에 따라 증가해 150원자 주기계에서는 `β·σ(ΔΔE) ≫ 1`이 되어 실효
    표본수가 붕괴한다. ⟹ 실제로 하는 일은 **"GGA 앙상블 위의 hybrid 갭 평가"** 이며,
    타당성은 전적으로 GGA 앙상블이 옳으냐(= ⟨s⟩)에 달려 있다. **주장을 실제보다 강하게
    쓰지 않는 것**이 이 결정의 핵심이다.
- **Consequences**:
  - S1이 낼 수 있는 것은 **상대 속도**뿐이다. 전극이 없어 `H_ab`가 정의되지 않으므로
    Marcus prefactor를 계산할 수 없다. ⟹ `k_ET,i = A·exp(−ΔG‡_ET,i/k_BT)`, **공통 A 가정.**
    ADR-003 관측량이 둘 다 비(ratio)라 A는 1차적으로 소거되나, **ET와 화학 단계가 경쟁하는
    분기점(정확히 C2H4/CO 분기)에서는 A가 답을 바꾼다.** ⟹ **S4에서 A 민감도 스캔 필수**(U-08).
  - `mechanism_flag`가 S1의 최우선 출력이다. concerted이면 λ와 ΔG‡_chem을 분리해 쓰는 것
    자체가 틀리며 오차가 eV 급이다. **판정 없이 S1을 닫으면 S3/S4가 잘못된 elementary step
    목록 위에 세워진다.** Stage A를 **비구속**으로 도는 이유가 이것이다(구속하면 개환을 못 본다).
  - **필수 벤치마크 B1/B2/B4 실행**(B3는 tier-2에 흡수). B1은 "오차 상쇄가 성립한다"는
    주장의 유일한 근거이므로 관례로 정당화 금지.
  - E_red를 평균 단일값이 아니라 **분포(중앙값 + 5/95 백분위)로 보고**하고 S4에 분포를
    전달한다. 용매화 착물 15개 절단으로 분포 꼬리를 버리는 손실(총 속도 factor 2~3 과소평가)을
    계산을 늘리지 않고 드러내는 방법이다.
  - S1 예산: tier-1 50 k + tier-2 143 k ≈ **193 k / 200 k = 97%. 여유 3%.**
- **Revisit trigger**: P2 파일럿의 ⟨s⟩가 회색대(0.5~0.8)로 나올 때. B1에서 오차 상쇄가
  성립하지 않는 것으로 측정될 때. C2 게이트에서 EC-EMC 간격이 0.1 V 이내로 나올 때
  (= 방법이 두 종을 구분하지 못함 ⟹ 방법 교체).

---

## ADR-006: S2 엔진 = 열거-후-여과 CRN(S2-A, HiPRGen/LIBE 계열) backbone. **LIBE 재사용 검증에 조건부**

- **Status**: ✅ **Accepted** (2026-08-17, P0 실측으로 조건 충족 — 하단 「P0 검증 결과」 참조).
  단 **실행 방식**(LIBE 재사용 vs 자체 계산)은 ADR-010에서 별도 판정
- **Date**: 2026-08-17
- **Stage**: S2
- **Resolves**: **U-04 (조건부)**
- **Context**: ADR-001의 조성 확장성(새 species ~1개월)과 ADR-003의 노드 커버리지
  (C2H4/CO/CO2/LiF/Li2CO3/LEDC/ROCO2Li가 실제 노드로 존재)를 **동시에** 만족하는 엔진 선택.
- **Proposer 입장**: **S2-A backbone.** principal molecule을 fragment 분해 → 재조합으로
  species pool 생성 → pool 위 화학양론 균형 반응 전수 열거 → 필터 → 열역학 rate 기반 kMC로
  경로 추출. 문헌 규모 >5,000 species / >80M reaction이며 **LEDC·LEMC·기체 부산물 경로가
  이미 실제로 식별된 유일한 후보.** S2-B(YARP/Chemoton)는 O(10²) species 커버리지로
  K1·K2 동시 만족 불가. S2-C(MLIP 발견기)는 자진 스코프 제외.
- **Engineer 입장**: **S2-A를 견적하지 않았다** — proposer 후보안을 보기 전에 작성했고,
  `05_STATE.md`의 원래 3후보만 다뤘다. 그가 견적한 YARP류는 재단 후 60 k core-h로 통과.
  ⟹ **그의 "RMG rule library 3~8 인간-주" 비판은 S2-A에 적용되지 않는다**(S2-A는 template-free).
- **Decision**:
  1. **S2-A를 backbone으로 잠정 채택.** S2-B의 기술(GSM→DFT TS→IRC)은 **S3의 정제 도구**로
     사용한다 — 엔진이 아니라 도구로 위치.
  2. **S2-C(MLIP 발견기) 1차 스코프 제외** (proposer 자진, engineer의 GPU 예산 5,000/6,000
     소진 + AL 직렬성 20~65일 논거 수용).
  3. 🔴 **조건**: LIBE 재사용 불가 시 ~150 k / 상한 160 k로 **예비분이 0이 된다.**
     P0 결과가 부정이면 **이 ADR을 재개봉한다.** 조용히 진행하지 않는다.
- **Rationale**: 선택 근거는 **비용이 아니라 ADR 요구**다. K1(확장성)을 구조적으로 만족하는
  유일한 후보이며(새 solvent/salt = principal list에 추가 → 자동 fragment, 사람 손 ≈ 수일),
  ADR-003 목표종이 문헌에서 이미 발견된 유일한 후보다. 또한 S2-B를 고르면 rolling S3가
  성립하지 않아(ADR-007 SG-1) 임계 경로 3~4주를 잃고 engineer의 비관 시나리오(26주+,
  5개월 초과)에 한 발 들어간다.
- **Consequences**:
  - **S2-A는 barrier를 계산하지 않는다.** 반응 가부를 ΔG로 판정하므로 열역학적으로
    내리막이나 운동학적으로 금지된 반응이 들어온다. ⟹ **S3가 필수인 이유이자, S2-A 단독으로는
    가스 분기비를 신뢰할 수 없다는 뜻.**
  - **pool에 없는 분자로 가는 반응은 원리적으로 못 찾는다.** LEDC까지는 되지만 SEI 폴리머는
    안 된다. 다분자(3체 이상) 협동 단계 없음.
  - S2-C 제외로 **완결성 감사 수단을 잃었다.** 남는 검증은 "알려진 성분이 재발견되는가"
    뿐이며 이는 **필요조건이지 충분조건이 아니다** — 미지의 지배 경로가 있어도 발견 못 한다.
    부분 대체(비용 ≈0): **flux는 높은데 문헌에 없는 종 상위 20개를 명시 보고**한다.
  - 예상 규모: species O(10³~10⁴), reaction O(10⁷~10⁸) → S3 정제 대상 O(10²~10³)로 축소.
- **Revisit trigger**: ~~P0에서 LIBE 재사용 불가 판명 시 즉시.~~ (발동하지 않음)
  S2→S3 게이트에서 목표종 7개 중 하나라도 노드로 나타나지 않을 때.

### P0 검증 결과 [MEASURED, 2026-08-17] — 조건 충족, 확정

proposer가 LIBE를 **실제로 내려받아 검증**했다(`data/libe/libe.json`, 285 MB,
MD5 figshare 공표값과 일치). 추정이 아니다.

| 항목 | 결과 |
|---|---|
| 접근·라이선스 | ✅ 다운로드 완료, **CC BY 4.0** (출처 표기만 하면 자유 재사용) |
| 🔴 **level of theory** | ✅ **ωB97X-V/def2-TZVPPD/SMD** — figshare 공식 description |
| 규모 | 17,190 엔트리 / 고유 (formula,charge,spin) 3,758 ⟹ conformer 배수 4.57 |
| thermo | `quasi_rrho_eV` **17,190/17,190 (100%)** — Grimme quasi-RRHO. 진동수 99.9% |
| 라디칼·이온 | charge −1:6,250 / 0:5,868 / +1:5,072, spin 1/2/3 = 7,146/7,612/2,432 |

🔴 **ADR-003 게이트 노드 6종 + ROCO2Li가 전부 실재한다** (conformer 수):
C2H4 7 / CO 4 / CO2 4 / LiF 4 / Li2CO3 18 / **LEDC 68** / ROCO2Li계 111 / LEMC 25·9 /
PF6⁻·PF5·POF3 3·2·3. EMC 계열 라디칼·생성물 13종도 **전부 존재(0/13 결손)**.

> ⟹ **ADR-007의 안전장치 SG-1(wave-1 목표종 역추적)이 성립한다는 직접 증거다.**
> 목표종이 generation-0 pool에 이미 전부 들어 있으므로 network 수렴을 기다리지 않고
> k-shortest path를 물을 수 있다. **추론이 아니라 확인된 사실.**
> 동시에 "S2-B는 rolling과 양립 불가"(ADR-007 SG-1)의 근거도 강화된다 — S2-B에는
> 이 사전 존재성이 없다.

**결손 (정직하게 — S1은 이득이 전혀 없다)**
- **원자수 상한 22, ≥30원자 엔트리 0개** ⟹ S1 클러스터(30~80원자)는 전부 LIBE 밖.
  **S1 비용 감면 0.**
- **Li(EC)₃ / Li(EC)₄ 부재** (Li(EC)₁ 111 conf, Li(EC)₂ 28 conf, Li(EC)₃/₄ **0**)
  ⟹ ADR-005 tier-2 주력종 Li⁺(EC)₄를 직접 계산해야 한다 (tier-1 250 job 안에 포함).
- C5+ 올리고머 희박, BF4⁻ 부재.

**보너스 — ADR-001 확장성이 부분 선불되어 있다**: FEC 34 conf / VC 51 / DMC 8 / PC 25 /
DEC 3 / FSI⁻ 3 / TFSI⁻ 1, N·S 화학 총 717 엔트리. BF4⁻만 0.
⟹ "새 species ~1개월 흡수" 요구가 첨가제·이미드염에 대해 **실증적으로 뒷받침된다.**

**부수 성과 — `mechanism_flag`(U-03-c)를 비용 0으로 조기 진단**
LIBE의 EC / EC⁻ 최적화 구조·자유에너지로 판정: 중성 EC는 닫힌고리가 전역 최저(sanity
check 통과), **닫힌고리 EC⁻가 실재하는 극소점**(libe-120806, 진동수 보유).
⟹ **diabatic 환원 상태가 존재 ⟹ λ가 정의된다 ⟹ ADR-005 S1-B의 실패모드 중
"개환으로 diabat이 사라진다"는 쪽이 크게 완화.** 문헌 barrier ≈0.48 eV 기준 수명 ≈20 μs로
AIMD 창(30 ps)보다 6자리 길다.
⟹ 🔴 **Stage A(7 ps 비구속)가 이분법적 정량 시험이 된다**: 7 ps 내 개환 없음 ⟹
ΔG‡ > 0.16 eV ⟹ stepwise 확정, λ 측정 유효 / 개환 발생 ⟹ concerted ⟹ λ와 ΔG‡_chem 분리 금지.
※ proposer는 "열린 이성질체가 EC⁻의 직접 개환 산물과 동일하다고 확인된 것은 아니므로
1.543 eV를 반응열로 쓰지 말고 상한으로만 쓴다"고 스스로 제한했다. 그 절제를 지지한다.

**후속 `[UNRESOLVED]`**: ① LIBE의 error-correction scheme 내용 (우리 자체 계산분에도
동일 보정을 적용해야 정합) ② LIBE thermo의 기준 상태(1 atm vs 1 M) — 전하별로 다르면 유해.

---

## ADR-007: engineer 상한 2건 정정, rolling S3 채택(wave-1 기준 변경), U-05 안전장치 SG-1~5 명문화

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S2 / S3 / Infra
- **Resolves**: U-05 (부분 — 정식 설계는 proposer 후속), engineer-proposer 미합의 4건
- **Context**: engineer의 예산 상한 중 2건에 proposer가 정식 이의를 제기했고, rolling S3의
  wave-1 선택 기준에서 둘이 갈렸다.
- **Decision — 정정 1: "S2 탐색 중 DFT 호출 = 0건" → "S2 탐색 루프 안의 *TS 탐색* DFT = 0건"**
  - **proposer 인용.** engineer의 `10⁴ 시도 × 800 core-h = 8 M core-h` 산식은 **TS 탐색 단가**에서
    나왔고 그 판정 자체는 옳다(proposer도 전적 동의). 그러나 그 문장은 **species 단위 thermo
    DFT(단분자 opt+freq, 5~25원자, ~30 core-h)까지 금지**하는 것으로 읽힌다. **단가 25배,
    건수 완전 별개인 두 가지를 한 문장이 묶었다.**
  - species thermo DFT를 금지하면 CRN의 모든 ΔG가 xTB 수준(반응 ΔG 오차 **0.5~1 eV**)이 되어
    **flux 기반 pruning이 무효화**되고, 그러면 ADR-003 목표종 경로가 무작위로 잘린다.
    ⟹ **정확도 손실이 아니라 방법 무효화.** species thermo DFT는 S2 예산 내 별도 허용.
- **Decision — 정정 2: "generation depth ≤ 3"은 S2-B 채택 시에만 적용**
  - engineer의 depth 상한은 iterative expansion에서 유도됐고 **그 문맥에서는 정당하다**
    (depth 4 = ×10~100). 그러나 S2-A는 pool을 한 번에 만들고 반응은 pool 위 조합이므로
    **경로 깊이가 비용에 들어가지 않는다.**
  - 🔴 결정적 근거: **LEDC는 최소 3~4 세대 깊이다**(EC + e⁻ → EC⁻ → 개환 라디칼 → 이량화 →
    +2 Li⁺). depth ≤3을 전 엔진에 강제하면 **ADR-003 게이트 종을 예산 상한이 죽인다.**
    상한이 검증 대상을 죽이는 구조는 허용하지 않는다.
- **Decision — rolling S3 채택. 단 wave-1은 flux가 아니라 목표종 역추적으로 채운다**
  - engineer 원안: gen-1/gen-2가 나오는 즉시 **flux 상위 ~30 반응**을 S3로 흘림 (S3 착수
    W10→W6~7, 임계 경로 3~4주 단축).
  - proposer 반론: 초기 network의 flux 편향은 **무작위가 아니라 "깊이"에 대해 구조적으로**
    걸린다(중간체를 소비하는 반응이 아직 없어 얕은 단계 flux 과대, 깊은 단계는 flux 0).
    ⟹ 깊은 LEDC 경로가 구조적으로 하위 배치되고, **선소진된 DFT 예산은 되돌릴 수 없다.**
    (소수 가스 경로는 gen-2의 국소 경쟁이라 부분 network에서도 보이므로 위험이 낮다 —
    lead가 우려했던 "소수 경로가 죽는다"는 rolling이 아니라 ΔG cutoff의 위험이었다.)
  - **채택**: wave-1(W6~7, ~60건)은 **ADR-003 목표종 역추적 경로 전용**. 목표종 7개는
    사전에 알려져 있어 network 수렴을 기다릴 필요가 없다. wave-2(W8~10, ~120건) P0 잔여 +
    flux 상위. wave-3(W10~14, ~120건) flux 잔여 + 민감도 지목.
    ⟹ **engineer의 일정 이득을 100% 보존하면서 ADR-003을 깨지 않는다. 상충이 없다.**
  - 부수 이득(proposer가 추가로 지적, 채택): rolling은 `TS 계산 → rate 갱신 → 재랭킹`의
    **폐루프**라 큐에 **정보가치(value-of-information) 항**을 넣을 수 있다. batch로는 원리적으로
    불가능하다. ⟹ **같은 300건으로 더 많은 결정 불확실성을 제거한다. rolling은 일정 타협이
    아니라 과학적으로 우월한 설계다.**
- **Decision — U-05 안전장치 SG-1~SG-5를 스펙에 명문화 (타협 불가)**
  - **SG-1** wave-1 = 목표종 역추적 (위). **S2-A에서만 성립**하며 S2-B에서는 목표종이 해당
    depth 전까지 존재하지 않아 성립하지 않는다 ⟹ **"S2-B + rolling"은 양립 불가 조합.**
  - **SG-2** network freeze(W10) 이전에 S3 예산의 **60%(180/300) 초과 집행 금지.** 나머지
    ≥120건은 수렴된 network의 flux 순위에 배정.
  - **SG-3** 🔴 **순위 안정성 게이트.** wave-N 집행 직전 flux 순위를 재계산해 wave-(N−1) 순위와
    **상위 100의 Spearman ρ**를 측정. **ρ≥0.7이면 집행, ρ<0.7이면 중단하고 network를 더 펼친다.**
    "부분 network의 flux를 써도 되는가"에 대한 **측정 가능한 falsifier**다. 비용 = 정렬 한 번.
    **이것이 없는 rolling은 근거 없는 도박이므로 필수 조건으로 건다.**
  - **SG-4** 사후 감사 원장. 집행된 TS마다 선택 당시 network 상태 해시를 기록하고, W15에
    **"최종 flux 상위 300 중 실제로 explicit TS를 받은 비율"** 을 보고. **70% 미만이면 rolling이
    실증적으로 오배분했다는 뜻이며 한계로 명시 보고한다.** 숨기지 않는 것이 목적.
  - **SG-5** 🔴 **큐 우선순위는 가중합이 아니라 사전식(lexicographic).**
    `Tier A 목표종 k-shortest path(k=10) 위 반응 → Tier B flux 상위 → Tier C 정보가치 상위.`
    **가중합(`w_T·1[target] + w_F·log flux`)을 쓰면 큰 flux 값 하나가 목표종 보호를 사들일 수
    있다.** ADR-003 Consequences는 "보호"를 요구했지 "가산점"을 요구하지 않았다.
  - **금지**: ΔG cutoff 단독 pruning, depth cutoff 단독 pruning.
- **Decision — S3 300건의 배분을 proposer 안대로 고정**
  - **P0(선점) 100~120건**: ADR-003 목표종 7종의 k-shortest path(k=10) 위 고유 반응.
    **flux와 무관하게 선점.** / **P1 130~180건**: flux 상위 / **P2 나머지**: 민감도 지목.
  - 250건으로 깎일 경우 **P0는 절대 건드리지 않고 P1을 180→130으로 줄인다.**
    잃는 것: flux 130~180위가 rate-rule/analogy 처리 ⟹ 총 flux의 10~25% ⟹ XPS 조성비가
    그 규모로 흔들림. **완화**: `barrier_source: rule` 플래그를 달고 S4 민감도에서 그 반응군을
    **일괄 ±0.2 eV 스캔**해 결론이 뒤집히는지 본다. 뒤집히면 예비 20%에서 추가 TS를 산다.
  - **100건 미만이면 가스 분기비 검증 불가**(P0만으로 100~120 필요). 250 안전 / 150 아슬아슬 /
    **100 미만 불가.**
- **Consequences**: U-04와 U-05는 **묶어서 판정해야 하며 분리 불가**하다(SG-1이 엔진에 종속).
  ADR-006이 재개봉되면 이 ADR의 rolling 부분도 함께 재검토된다.
- **Revisit trigger**: SG-3의 ρ가 wave-2에서도 0.7에 도달하지 못할 때(rolling 포기, batch 회귀).
  SG-4의 사후 비율이 70% 미만일 때(다음 조성에서 rolling 재설계).

---

## ADR-008: 기간 5개월 확정, air-gapped 확정, U-09 = Snakemake + 파일큐 + job array (Case B)

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra
- **Resolves**: **U-09**, 기간 상한, engineer Q2/Q4
- **Context**: ADR-004로 HPC 직접 접근이 불가해지자 engineer가 Round 2에서
  **"운영 주체가 우리가 아니라 사용자이고, 사용자는 참여자가 아니라 제출 대행자"** 임을
  근거로 Round 1의 U-09 권고(Parsl + jobflow/atomate2, 대안 AiiDA)를 **스스로 뒤집었다.**
  판정 기준이 "기능이 얼마나 좋은가"에서 **"사용자에게 얼마나 적은 운영 부담을 지우는가"** 로 바뀜.
- **Proposer 입장**: N/A (인프라 사안)
- **Engineer 입장**: AiiDA는 PostgreSQL+RabbitMQ+daemon을 사용자가 유지보수해야 하므로
  **탈락**. Parsl은 로그인 노드 상주 프로세스가 흔히 kill되므로 **단독 탈락**(내부 pilot
  계층으로만 재활용). FireWorks는 Q2=yes면 최선(LaunchPad를 우리가 호스팅, 사용자는
  `rlaunch rapidfire`만). Snakemake+파일큐는 Q2=no면 최선(상주 서비스 0개).
- **Decision**:
  1. **기간 = 5개월(21.5주) 확정.** 4개월은 완화수단이 **전부** 성공해야만 성립(여유 1주)하며,
     하나만 빠져도 초과한다.
  2. **air-gapped 확정** (사용자 답변). ⟹ **Case B 확정.**
  3. **U-09 = Snakemake(거친 DAG ~50 stage) + 파일 기반 작업큐(원자적 rename으로 claim)
     + SLURM job array(세밀 태스크) + SQLite 단일 파일 provenance.**
     AiiDA / Parsl / FireWorks 전부 탈락.
  4. **계층 분리 필수**: Snakemake는 ~50개 거친 stage만 관리한다. 10⁵개 세밀 태스크를
     Snakemake에 넣으면 DAG 계산에서 죽는다. stage 내부의 10³~10⁵개 xTB 태스크는
     job array 워커가 파일큐에서 뽑아 쓴다 = **pilot-job의 데몬 없는 구현.**
  5. **공통 유지 4개항**: ① 작업 키 = **구조 해시(InChIKey/graph hash) + 파라미터 해시**
     (species 이름 기반 키 금지 — 새 species 추가 시 전부 깨진다) ② **멱등 재실행**
     ③ provenance DB는 **단일 파일 아티팩트(SQLite)** — 원격 조회가 불가하므로 왕복 짐에
     실려 오가야 한다 ④ **반송 tarball만으로 DAG 상태를 완전 복원**할 수 있어야 한다
     (결과뿐 아니라 작업큐 상태 완료/실패/미착수를 함께 반송).
- **Rationale**: ①②는 ADR-001의 "새 species ~1개월 흡수" 요구를 구조적으로 충족한다 —
  신규 species 추가 = 기존 결과 100% 재사용 + 신규분만 계산. Case B 설계는 Case A에서도
  동작하지만 역은 성립하지 않으므로, 불확실했던 시점에도 Case B가 안전한 기본값이었다.
- **Consequences**:
  - 🔴 **수동 제출이 임계 경로에 ~4주를 얹는다** (8회 왕복 × 3.5일). Round 1 계획의 여유
    2주가 **-2주**가 되므로 4개월 계획은 성립하지 않는다. 이것이 5개월 확정의 1차 근거.
  - **임계 경로가 바뀌었다**: Round 1 `S2→S3 핸드오프` →
    Round 2 **`[RT-1 파일럿 결과 대기] → S1 방법 확정 → S2→S3 핸드오프`.**
    파일럿 결과 전에는 S1 생산을 시작할 수 없고 봉투도 확정할 수 없다.
    ⟹ **파일럿 인도 패키지가 현재 최우선 산출물.** coder에게 배정함.
  - **완화수단은 선택이 아니라 필수**: 왕복 pipelining(가장 큰 레버, 비용 0), fat batch,
    투기적 중복 실행, **자기 연쇄 제출**(24 h wall × AIMD 15궤적 × 5회 = 75회 재제출을
    사용자가 손으로 하면 프로젝트가 끝나지 않는다 ⟹ 사용자 개입은 정확히 `sbatch` 1회).
  - **설계 원칙: 계산은 싸고 왕복은 비싸다.** 잉여 계산 자원을 **새 stage가 아니라
    사람 시간·왕복 횟수를 줄이는 데** 쓴다(TS 탐색 ×3 중복으로 실패율 40%→15%, 투기적
    선계산, S1 조밀 샘플링). **S3 건수 증설(500→1,500)은 금지** — 사람이 없다.
  - 봉투 개정: 전용·수동 기준 **5.80 M core-h**(duty cycle 45%). core-h는 4.3배 늘었으나
    **산출되는 과학의 양은 1.7배**만 는다.
- **Revisit trigger**: 사용자가 SSH/GPU 접근을 열어줄 때(Case A 재검토 + 임계경로 -2~3주).
  P0 프로브의 `outbound_network`가 예상과 다르게 나올 때.

---

## ADR-009: ~~인간 시간이 진짜 제약이며 현 스코프는 인간 예산을 초과한다~~ → **정정: 초과하지 않는다. 파탄은 달력이다**

- **Status**: **Superseded in part** — 아래 「🔴 정정」 참조. 진단의 방향은 유지되나
  **"인간예산 1.4~1.8배 초과"라는 수치 주장은 철회한다.**
- **Date**: 2026-08-17
- **Stage**: Infra (전 stage 구속)
- **Resolves**: 없음. **미해결 상태를 명시적으로 기록하기 위한 ADR이다.**
- **Context**: engineer가 §R2-3에서 "S3 상한을 정하는 것은 core-hour가 아니라 사람"임을
  곡선으로 보이고, 팀 용량을 `2.5명 × 20 h/주 = 50 인간-h/주`로 가정해 **S3 = 500건**을 도출했다.
  이후 사용자 확인 결과 실제는 **1인당 주 10시간 미만, 그것도 산발적**이다.
- **Engineer 입장 (Round 2)**: TS 1건당 인간 비용 0.31 h = 실패 분류 3.5분(자동 triage 후)
  + **과학적 타당성 검토 15분**. *"15분/건은 깎을 수 없다. 이걸 0으로 두면 검증되지 않은
  barrier가 S4로 흘러들어가고 ADR-003의 두 검증축이 무의미해진다."* 총 인간시간 소요
  **488~762 h** (수동 제출 체제가 +170 h ≈ +40%를 얹음).
- **Proposer 입장**: S3 배분에서 **P0(ADR-003 목표종 선점)만으로 100~120건이 필요**하며
  **100건 미만이면 가스 분기비 검증 불가**. 250 안전 / 150 아슬아슬 / 100 미만 불가.
- **문제 (lead 계산)**:
  ```
  5개월 21.5주 × 25 h/주(팀 2.5명 × 10 h) = 537 인간-h   (20 h/주면 430 h)
  §R2-9 소요                              = 488 ~ 762 인간-h
  ⟹ 소요/용량 = 91% ~ 177%
  ```
  **낙관값조차 용량과 겨우 맞고, 비관값은 1.4~1.8배 초과다.**
  engineer의 "compute 2,000건 vs 사람 500건, 격차 4배"는 이제 **격차 8~10배**이며,
  S3만의 문제가 아니라 **프로젝트 총 인간예산 초과**다.
- **Decision**: **없음 — 결정 불가.** 아래가 확정되어야 결정 가능하다.
  1. engineer의 인간시간 재계산 (20 / 25 h/주 두 시나리오, S3 상한 곡선 재작도)
  2. 인간시간 절감 수단별 절감량(인간-h)과 대가 — *"코드 X시간 투자 → 인간시간 Y시간 구매"* 형태
  3. proposer의 S3 하한 해상도 (150 / 100 / 80건에서 각각 무엇이 무너지는가)
  4. proposer의 "explicit TS가 꼭 필요한 반응 vs rule로 충분한 반응"을 가르는 과학적 기준
  5. 위가 모두 나온 뒤 **스코프 축소안 3개 + 기간 연장안**을 사용자에게 올린다
- **Rationale (왜 지금 닫지 않는가)**: 지금 임의로 S3 건수를 정하면 ADR-003 검증축 (a)가
  조용히 무너진다. 반대로 낙관적으로 "5개월에 된다"고 쓰면 **05_STATE.md가 낙관 문서가
  된다.** 둘 다 하지 않고 미해결로 남긴다.
- **Consequences**:
  - **모든 인력·자동화 판단의 우선순위가 바뀐다.** 계산 자원은 봉투의 75%가 남아도는데
    사람이 없다 ⟹ **자동화에 계산과 코드를 쏟아붓는 것이 유일하게 옳은 투자다.**
  - coder 스코프를 좁게 유지해야 한다 — **코드가 늘면 검토할 사람이 늘어난다.**
  - S3 상한이 100건 밑으로 내려가면 그건 일정 문제가 아니라 **프로젝트 목표 미달**이다.
- **Revisit trigger**: 위 5개 입력이 모이는 즉시. 또는 사용자가 인력/투입시간을 늘릴 때.

### 🔴 정정 (2026-08-17, engineer §R3.1) — 내 수치 주장이 틀렸다

engineer가 **자기 숫자의 범주 오류를 스스로 찾아 정정했고, 그 위에 세운 내 진단도 함께 무너진다.**

> **§R2-9의 488~762 h는 "총 작업량"이지 "인간이 해야 하는 작업량"이 아니었다.**
> 이 팀의 proposer·engineer·coder·critic은 **전부 AI teammate**이고, AI 작업은 인간-시간
> 통화로 거의 무료다. engineer가 §R2-9에서 둘을 한 칸에 합산했고, **lead는 그 숫자를
> 검산 없이 받아 "소요/용량 91~177%"를 도출했다.** 산술은 맞았고 입력이 틀렸다.

**재분해 후 (engineer §R3.1)**

| | 소요 | 용량 344 h (주20h) | 용량 430 h (주25h) |
|---|---|---|---|
| 자동화 전 | 232~369 h | 67~107% 🟡 비관값만 7% 초과 | 54~86% 🟢 |
| 자동화 후 | 127~195 h | 37~57% 🟢 | 30~45% 🟢 |

※ 용량에는 **산발적 근무의 재오리엔테이션 세금 15~20%**(매 세션 "어디까지 했더라"를
다시 읽는 시간)가 이미 반영돼 있다. 명목 시간을 그대로 쓰면 안 된다는 지적도 채택.

**⟹ 총 인간시간은 파탄이 아니다.** 다만 여유가 얇으므로 자동화 투자는 여전히 정당하다.

### 🔴 그러나 진짜 파탄이 다른 곳에서 확인됐다 — **달력(왕복 지연)**

engineer §R3.3: Q3(산발적 인력)는 인간시간보다 **왕복 속도**를 훨씬 심하게 때린다.
```
달력 총계 = 12주 + (직렬 왕복 사망시간)
```
| 조합 | 총계 | 21.5주 대비 |
|---|---|---|
| 8왕복 · 주1회 | 20.0주 | +1.5주 🟡 |
| **8왕복 · 주1회 + 계통 재계산 1회** | **24.0주** | **−2.5주** 🔴 |

engineer는 Round 1부터 **"계통적 재계산 1회는 거의 확실히 발생한다"** 고 썼고 그 판단을
철회하지 않았다. ⟹ **5개월 완주 확률 [ESTIMATE] 50~60%.**
engineer 원문: *"'5개월 안에 끝난다'고 쓰지 않겠다."*

> 🟢 **완화 — 사용자 답변 Q7 = "주 2회 이상, 짧게"**: engineer가 지목한 최선의 시나리오다.
> 왕복 1회 3.5일, 직렬 8회 = **4.0주**(주1회의 8.0주 대비 절반). 최악 조합을 피했다.
> ⟹ 완주 확률 재산정을 engineer에게 지시함.
>
> engineer 원문(사용자에게 전달 완료): *"주당 몇 시간보다 **주당 몇 번 접속하는가**가
> 달력을 지배한다. 같은 10시간이라도 주 1회 몰아 쓰면 주 2회 나눠 쓰는 것보다 달력이
> 4주 길어진다. 이것은 사용자가 비용 없이 바꿀 수 있는 유일한 변수다."*

### S3 건수 — 위협받지 않는다 (좋은 소식)

engineer §R3.2: 자동화 없이도 **165~348건**. proposer의 방어선 100~120건은 **모든
시나리오에서 지켜진다.** ⟹ **ADR-003 검증축 (a)는 Q3에 의해 무너지지 않는다.**
유일한 위협은 복합 비관(주20h + 자동화 없음 + 타업무 60% + 계통 재계산 1회) ⟹ ~83건.

### 🔴 lead의 교훈 (기록 목적)

**teammate가 준 숫자를 그대로 상위 결론에 넣기 전에 그 숫자의 *정의*를 검산해야 한다.**
ADR-011의 `c` 정의 불일치(내가 잡음)와 이번 인간시간 범주 오류(engineer가 잡음)는
**같은 종류의 실패**다 — 같은 단어가 다른 양을 가리키는데 숫자가 커서 통과되는 것.
두 번 발생했으므로 우연이 아니다. 앞으로 **수치를 인용할 때 그 수치의 분모·모집단을
명시적으로 확인한다.**

---

## ADR-010: ADR-005의 S1 절단을 철회한다 — 폐기된 예산선에 맞춘 판정이었다

- **Status**: Accepted (**ADR-005의 Decision 7 및 AIMD 상한을 수정**)
- **Date**: 2026-08-17
- **Stage**: S1
- **Amends**: ADR-005
- **Context**: engineer가 `03_COMPUTE_PLAN.md` §11.3(a)에서 **lead의 판정 오류를 지적했다.**
  proposer는 S1 계획을 **S1 ≤ 200 k core-h**에 맞춰 깎았고(193 k = 97%, 여유 3%),
  그 여유 부족을 근거로 **R3 실험 앵커 포기 ↔ AIMD 4번째 계**의 거래를 제안했으며
  **lead가 이를 승인했다(ADR-005 Decision 7).**
  🔴 **그런데 그 200 k는 Round 1 *공유* 시나리오의 S1 선이고, ADR-004(전용 확정)에서
  이미 폐기됐다.** Round 2 전용 봉투의 S1 선은 **1.16 M**이며 proposer의 193 k는 **17%**다.
  **여유는 3%가 아니라 83%였다.**
- **Engineer 입장**: *"lead의 승인은 잘못된 전제 위에 있었다. 철회를 권고한다."*
  더불어 §11.3(c)에서 **AIMD 상한의 성격 자체가 바뀌었음**을 실측으로 보였다.
- **Decision**:
  1. 🔴 **ADR-005 Decision 7(R3 앵커 포기)을 철회한다.** R3 실험 앵커를 **예산 사유로는
     포기하지 않는다**(+12 k = S1 선의 1%). 단 proposer가 §1.1에서 지적한 "carbonate계
     가역 앵커 확보 불확실 + 화학종족 상이"는 유효하므로, **앵커의 실제 존재 여부로만
     판단한다.** 없으면 폐기해도 좋다 — 이유가 "예산"이면 안 된다.
  2. **conformer 5 → 10 복원** (+75 k). proposer가 스스로 기록한 손실(최저 자유에너지
     conformer 누락 ⟹ ΔG 상향 편향 0.03~0.08 eV)을 되산다.
  3. 🔴 **cDFT 분기에서도 tier-2 4계를 유지한다** (+85 k). ADR-005 Decision 5의
     "⟨s⟩<0.5 ⟹ 계 수 4→2로 축소"를 **철회한다.**
     근거(engineer 실측): **궤적끼리 완전 병렬이므로 계를 4→2로 줄여도 달력이 1일도
     줄지 않는다.** ⟹ 축소는 아무것도 사지 못하면서 **1e⁻/2e⁻ 분기(C2H4:CO,
     ADR-003 축(a)의 본체)만 잃는다.**
  4. **level 상향(ωB97X-V/def2-TZVPPD) 판단에서 예산 항목을 제거한다.** 단가비가 5배여도
     tier-1은 S1 선의 22%다. proposer의 "단가비 4배 초과 시 후퇴" 후퇴선을 **무효화**한다.
     ⟹ **순수하게 과학(LIBE thermo 정합성)으로만 결정하라.**
     ※ 단가비가 실제로 민감한 곳은 **S1이 아니라 S2-A의 2,000 species thermo**다.
       P1b는 S1이 아니라 **S2의 예산 리스크를 측정하는 파일럿**으로 위치를 바꾼다.
  5. **AIMD 상한 개정** (ADR-005 Decision 3의 "≤268 ps" 표현을 대체):
     - 계 수 ~~≤ 6~~ → **≤ 12** (병렬이라 달력 비용 0, core-h만 선형)
     - 총량 ~~≤ 300 ps~~ → **≤ 400 k core-h** (등가 환산으로 통일)
     - 🔴 **신규 진짜 상한: 단일 궤적 길이 ≤ 30 ps (GGA) / ≤ 20 ps (cDFT).**
       근거: cDFT 30 ps = 궤적 하나에 **14일 + 재제출 14회**. S1 창(5주)에 재시도 여지가 사라진다.
     - **hybrid AIMD = 0 ps** (불변)
     - 🔴 **재제출 14회 = self-chaining 없으면 사용자 수동 개입 14회 = 프로젝트 사망.**
       ADR-008의 self-chaining이 **AIMD에서는 선택이 아니라 존폐 조건**이다.
- **Rationale**: **"비싼 것은 계 수가 아니라 궤적 길이다"** 는 재진단이 핵심이다.
  Round 1의 "계를 줄여라"는 core-h가 binding일 때만 옳았고, 전용 봉투에서는 binding이
  아니다. proposer의 Stage A(4계 × 7 ps) + Stage B 설계는 **형태가 이미 옳았다 —
  계는 넓게, 궤적은 짧게.** 축소를 강요한 것은 폐기된 숫자였다.
- **Consequences**:
  - S1 소비 전망 193 k → **~490 k / S1 선 1.16 M = 42%.** 앵커·conformer·level·4계를
    전부 복원해도 절반 이하다.
  - **ADR-005 Decision 5의 cDFT 분기는 "계 수 축소" 없이 "궤적 길이 ≤20 ps" 제약만 받는다.**
  - 🔴 **교훈(기록 목적)**: 상위 ADR이 예산선을 바꾸면 **그 예산선에 맞춰 내려진 하위
     판정을 자동으로 재검토해야 한다.** ADR-004(전용 확정) 시점에 ADR-005의 절단을
     되돌렸어야 했다. 이 누락을 engineer가 잡았다. **앞으로 봉투가 바뀌면 lead는
     그 봉투를 참조한 모든 미확정 절단을 즉시 재점검한다.**
- **Revisit trigger**: ADR-009(인간예산)의 해소안이 S1 범위를 다시 줄이도록 요구할 때.
  ※ **계산 여유가 돌아온 것과 사람이 없는 것은 별개다. ADR-009는 이 ADR로 해소되지 않는다.**

---

## ADR-011: S2-A 실행 방식(LIBE 재사용 vs 자체 계산)은 손익분기 c*=75%로 판정. **c 미측정**

- **Status**: 🔒 **Superseded by ADR-026 (판정) + ADR-028 (계층화 폐기)**.
  `c` = 29~41%로 실측됐고(ADR-026), **결정 근거가 비용에서 "레벨 이음매"로 교체**됐다.
  본 ADR의 **N_DFT 계층화(2,000/2,500)는 폐기**됐다(ADR-028: 실측 pool 2,142로 전 pool
  계산이 계층화보다 싸다). `c*` 규칙 자체는 **"등가성이 성립하는가?"를 묻게 하는 트리거**로만 존치.
  ~~Proposed — `c` 실측 대기~~
- **Date**: 2026-08-17
- **Stage**: S2
- **Resolves**: 없음 (판정 규칙만 확정)
- **Context**: LIBE를 재사용하면 **신규분도 LIBE level(ωB97X-V/def2-TZVPPD, 비쌈)로
  계산해야 정합**하고, 자체 계산으로 가면 전 pool을 값싼 자체 level로 **일관되게** 계산할 수
  있다. 두 선택지는 **양립 불가**다(같은 kMC에 다른 level의 ΔG 두 벌을 넣을 수 없다).
- **Engineer 입장**: proposer의 pool 단가 견적(20~40 core-h)에 **내부 비일관성**이 있다 —
  level 상향을 요구하면서 단가는 저level 값을 썼다. def2-TZVPPD는 수소까지 diffuse
  ⟹ 기저 1.4~1.6배 ⟹ 비용 ~2.6배, ωB97X-V의 VV10 +10~30%, SCF 수렴 악화까지
  ⟹ **species 1건당 기준 240 core-h**(conformer ×3 포함). 실제 견적은 proposer 대비 **6배.**
  ```
  (i) LIBE 재사용: N_pool × (1−c) × 240      (ii) 자체 계산: N_pool × 60
  손익분기 c* = 75%
  ```
- **Decision (판정 규칙만)**:
  - **c ≥ 75% → LIBE 재사용.** **c < 75% → 재사용을 포기하고 전 pool 자체 계산이 더 싸다.**
    (자체 계산은 문헌 비교 가능성을 잃는다. 그 손익은 proposer의 과학 판단 영역이다.)
  - 🔴 **계층화 필수 — 5,000 species 전수 DFT 금지.**
    Tier-A 전 pool xTB thermo(≈무료) → Tier-B 1차 flux로 DFT 대상 선별 **+ ADR-003 목표종
    경로 위 species는 flux 무관 무조건 포함** → Tier-C 선별분만 DFT thermo →
    Tier-D DFT thermo로 flux 재계산.
    **N_DFT 계획 2,000 / 실링 2,500** (480 k / 600 k core-h).
    ⟹ **xTB는 "누구를 자를까"가 아니라 "누구에게 DFT를 줄까"를 정하는 데만 쓰고, 자르는
    판단은 DFT thermo로 한 Tier-D에서만 한다.** 이러면 xTB 오차(반응 ΔG 0.5~1 eV)가
    최종 pruning에 들어가지 않는다 — proposer의 반론(ADR-007 정정 1)을 정면 해소.
  - **[상한, S2-A] N_pool ≤ 6,000 species** (반응 ~10⁸, DB 50~500 GB. 이 위로는 메모리·I/O가
    먼저 죽는다). **N_DFT ≤ 2,500. 경로 깊이 제한 없음.**
- **🔴 미해결 — `c`가 아직 측정되지 않았다 (lead가 발견한 정의 불일치)**:
  proposer의 P0가 낸 **95.8%는 "LIBE 엔트리 중 원소계가 (C,H,O,Li,P,F) 부분집합인 비율"**,
  즉 **LIBE의 성질**이다. engineer의 `c`는 **"우리 pool 중 LIBE에 있는 비율"** 이다.
  **두 양은 다르다.** proposer의 "신규 fragment 수백 건"은 c≈90~94%를 함의하나 **추정이다.**
  ⟹ proposer에게 **실제 pool을 생성해 (formula, charge, spin) 수준에서 세라**고 지시함.
  계산 자원 불필요.
- **Consequences**: **S2가 이제 유일한 예산 리스크다**(S1 42%, S3는 인간 상한, S4 무료).
  최악 조합(c 미지 + 단가비 5× + N_DFT 2,500) = 1.07 M = S2 배정의 153%이나
  **예비 2.26 M으로 흡수 가능 — 봉투는 안 깨진다.**
  🔴 **유일한 실패 모드는 계층화를 어기고 5,000 전수 DFT를 강행하는 것**(1.2~2.1 M, 171~300%).
- **Revisit trigger**: `c` 실측치 도착 즉시. P1b의 단가비가 5배를 넘을 때.

---

## ADR-012: 🔴 AIMD를 생산 도구에서 **검증 도구로 강등**한다 — λ를 분해해 각 조각에 맞는 도구를 재배정

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S1
- **Resolves**: **U-11**. **ADR-005 Decision 2·3·5, ADR-010 Decision 3·5를 대체**
- **Context**: 사용자 지시 — *"AIMD를 최소화 할 수 있는 방안을 모색해야 해.
  AIMD는 너무 비싸서 현실적이지 않아."*
  🔴 **"비싼 것"의 정체를 먼저 특정했다: core-h가 아니다** (4계 143 k = S1 선 1.16 M의 12%).
  **달력과 왕복이다** — 단일 궤적 6.9일(GGA)/13.9일(cDFT), **재제출 56~112회**,
  air-gapped 수동 제출에서 **self-chaining이 존폐 조건**인 단일 실패점, 직렬이라 임계 경로에 직접 얹힘.
  ⟹ 이 프로젝트의 실제 통화(ADR-009 정정: 파탄은 달력) 기준으로 **사용자 판단이 옳다.**
- **Proposer 입장**: 🔴 **자기 핵심 논거를 철회했다.**
  *"AIMD는 λ에 대해 대체 가능하고, 대체안이 오히려 더 정확할 개연성이 높다."*
  1. **λ는 λ_in + λ_out으로 분리된다.** λ_in(용질 기하 완화) ← **cluster DFT Nelsen 4-point,
     이미 S1-A에 있다.** λ_out(용매 배향 재배열) ← **정전 선형응답이므로 고전 MD가 맞는 도구.**
  2. **오차 분석**: 비분극 고정전하 FF는 `1/ε_op` 항 때문에 λ_out을 **2.0배 과대평가**
     (EC:EMC 3:7, n≈1.40 ⟹ ε_op≈1.95: 올바른 인자 0.477 vs FF 0.964).
     **MDEC 전하 스케일링(×1/√ε_op = 0.716) 후 잔차 3.5%** ⟹ λ_out 0.5 eV 기준 **0.02 eV.**
     **GGA-AIMD에 부여했던 ±0.15~0.3 eV보다 한 자리 작다.**
  3. **표집이 이긴다**: AIMD 30 ps vs 고전 MD 10+ ns = **300배.** λ_out은 느리게 수렴하는
     집단 정전량이라 **표집 300배가 전자구조 등급을 이긴다.** (proposer 자신이 §1.4에서
     "20 ps는 carbonate 배향 완화에 짧을 수 있다"고 썼던 것이 여기서 부메랑이 됐다.)
  4. **λ 차등(ADR-005의 핵심 논거)은 보존된다** — 고전 MD는 각 화학종의 λ_out을 실제 용매와
     함께 명시적으로 계산하므로 반경·전하부류 의존성을 직접 담는다.
     **고전 경로 λ 차등 오차 ±0.03~0.08 eV < GGA-AIMD ±0.15~0.3 eV.**
     ⟹ **ADR-005가 방어하려던 바로 그 양이 AIMD 없이 더 잘 지켜진다.**
     선형응답 falsifier(가우시안성, `λ=σ²/2k_BT`)도 **더 좋은 통계로** 유지된다.
  5. **`mechanism_flag`는 AIMD가 아니라 TS 계산이 답한다.**
     *"내 Stage A 설계를 폐기한다. 더 나쁜 도구였다."* — Stage A(7 ps)는 개환 여부
     **이분법**만 주고 판별 임계가 ΔG‡≈0.16 eV 부근에서만 작동하는데, **클러스터 TS는
     ΔG‡ 값 자체를 전 구간에서 준다.** 6건 = **8 k core-h, 1 배치, 재제출 0회.**
     덤으로 §8.6의 `[FULLTEXT-UNVERIFIED]` 문헌 barrier 의존이 하나 사라진다.
- **Engineer 입장**: 달력 견적 진행 중이나 판정 근거가 이미 압도적이어서 lead가 선판정.
  (§11.3(c)에서 "cDFT 30 ps = 궤적당 14일 + 재제출 14회"를 최악으로 지목했던 당사자.)
- **Decision — proposer의 (b)안 채택**:
  1. **대체 골격**: `λ_in ← cluster DFT Nelsen` + `λ_out ← 고전 MD 선형응답(MDEC 전하 스케일링)`
     + `mechanism_flag ← 클러스터 TS 6건` + **교차검증**(클러스터 크기 외삽 λ ↔ 고전 MD λ_out).
  2. **AIMD 잔존 규모 = 2계 × 환원상태만 × 3 ps ≈ 2 k core-h.**
     **목적은 λ 생산이 아니라 환원종 고전 FF 검증** (Li–O RDF·배위수를 AIMD와 대조).
     단일 job wall **16.7 h < 24 h 상한 ⟹ 재제출 0회, 왕복 1회, self-chaining 불필요.**
  3. **완전 제거(a)를 택하지 않는다.** proposer 논거: *"(a)의 지배 오차원은 ε_op가 아니라
     환원종 FF의 구조적 타당성(0.1~0.2 eV)이고, 그 FF는 이제 λ 차등 논거 전체를 떠받치는
     **하중 부재**가 된다. 하중 부재를 검증하는 데 배치 2건은 싼 보험이다."*
     ⟹ **사용자 지시를 과잉 이행하지 않는다.** 더 싼 안이 있어도 검증을 버리지 않는다.
  4. **소멸하는 것**: ADR-005 Decision 5의 **G-AIMD 스핀밀도 분기**, ADR-010 Decision 3의
     **cDFT 분기**, Stage A/B 설계, "AIMD 4계 양보 불가"(쟁점 8).
     ⟹ 감시 장치들은 **GGA AIMD가 스스로 만든 실패모드(SIE)를 감시하던 것**이므로
     AIMD가 사라지면 감시 대상도 사라진다. **부수효과가 아니라 이 결정의 주된 이득.**
     ※ P2 파일럿의 `s(t)` 측정은 **그대로 유지**한다 — 2 k AIMD의 건전성 확인에 여전히 쓰인다.
- **Rationale**: 이것은 **비용 압력에 방법을 깎은 것이 아니라, 압력이 더 나은 방법을
  찾게 만든 사례다.** λ를 분해 가능한 양으로 보지 않았던 것이 proposer의 원래 오류였고
  (본인 표현: *"당시 나는 λ를 분리 가능한 양으로 보지 않았다. 그것이 내 오류였다"*),
  분해하고 나니 각 조각에 더 맞는 도구가 있었다. **결과적으로 비용 1.4%, 재제출 0%,
  정확도는 향상.** 세 축이 동시에 좋아지는 경우 trade-off는 실재하지 않았던 것이다.
- **Consequences**:
  - 🔴 **신규 필수 작업 — 환원종 고전 力場 파라미터화** (EC⁻, Li⁺(EC)₃(EC⁻), CIP⁻).
    RESP 전하는 **LIBE에서 비용 0으로 조달**, 결합 파라미터는 S1-A가 이미 계산하는 환원종
    Hessian에서 유도 ⟹ **증분 계산비용 ≈ 0. 그러나 인간시간 1~2주 [ESTIMATE].**
    ⚠ **인간시간이 희소 통화이므로(ADR-009) 이 항목이 작지 않다.** engineer에게
    "인간 필수분 vs AI 작업"으로 분해하라고 지시함.
  - 이 FF가 **λ 차등 논거 전체를 떠받치는 하중 부재**가 된다. 2 k AIMD가 그 검증이다.
  - **신규 `[UNRESOLVED]` U-03-d**: 전하 스케일링(잔차 3.5%, 구현 자명) vs 분극 力場
    (APPLE&P 계열, 잔차 더 작으나 조달·구현 부담). **(b)의 3 ps 검증이 판정 근거를 준다
    ⟹ 파일럿 이후로 미룬다. 지금 정하지 않는다.**
  - **신규 `[UNRESOLVED]` U-03-e**: λ_in + λ_out **가법성** 검증. 클러스터 크기 외삽으로 얻은
    총 λ가 `λ_in(cluster) + λ_out(고전MD)`와 일치하는가. **불일치 크기가 가법성 가정의 오차다.**
    비용은 S1-A에 흡수.
  - 🔴 **발견 기능이 세 번째로 잘렸다** — R-16 참조. 응축상 sub-ps 예기치 못한 화학을
    발견할 수단을 잃는다. **사용자 판단 사항으로 승격했다.**
- **Revisit trigger**: 2 k AIMD 검증에서 고전 FF의 Li–O RDF·배위수가 AIMD와 유의하게
  어긋날 때(FF 재파라미터화 → 그래도 안 맞으면 AIMD 확대 재검토).
  U-03-e에서 가법성이 깨지는 것으로 측정될 때.

---

## ADR-013: 진행 전략 = ①자동화 선투자(5개월). ②연장 전환은 **G-W6 게이트에서 측정치로 판정**

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra
- **Resolves**: 진행 전략 선택 (engineer §R3.5 / §R4.6 선택지 ①~④)
- **Context**: engineer가 Round 3에서 **5개월 완주 확률 50~60%** 로 정직하게 보고하고
  선택지 4개를 냈다. 그 뒤 두 가지가 개선됐다: **Q7(주 2회 접속 확보)** 과
  **ADR-012(AIMD 최소화)**.
- **Engineer 입장 (§R4)**: 완주 확률 **50~60% → 70~80%(Q7) → 85~90%(AIMD 최소화)
  → 90%+(L4·L5·L6 자동화)**.
  §R3.3의 최악 조합(8왕복·주1회·재계산1회 = 24.0주, **−2.5주**)이 주 2회에서는
  **18.6주(+2.9주)** 가 된다. ⟹ *"사용자가 '주 2회 짧게'를 택한 것이 이 프로젝트에서
  가장 값싸고 효과 큰 결정이었다."*
  ⟹ **③④(스코프 축소)를 사용자에게 올릴 필요가 없어졌다. 선택지가 4개 → 2개.**
- **Decision**:
  1. **① 자동화 선투자로 진행.** 기간 5개월 유지(ADR-008), 스코프 전부 유지, S3 300건,
     ADR-003 두 검증축 모두 정량 유지.
  2. **W1~4에 L1~L7 자동화 선투자.** 우선순위: **L3(세션 상태 자동요약) 최우선**
     — coder 3일 투자로 35~50 인간-h, ROI 최고이며 **산발적 근무의 재오리엔테이션
     세금(15~20%)을 정확히 겨냥**한다. 이어 **L4·L5·L6(달력 레버)** — 왕복 8회 → 5회.
  3. 🔴 **[게이트 G-W6] W6에 측정치로 ② 전환 여부를 판정한다.**
     - 측정 대상: (i) L1·L3·L4가 실제로 동작하는가 (ii) **실제 왕복 1~2회의 사망시간이
       며칠이었는가**
     - **왕복 사망시간 ≤ 5일 AND L1·L3 동작 → ① 유지(5개월)**
     - **그 외 → 즉시 ②(6.5개월) 전환 선언.** W6이면 아직 늦지 않다.
  4. **③(S3 150건 축소)·④(파이프라인 우선)는 채택하지 않는다.** 다만 **폐기하지 않고
     G-W6 이후의 비상 선택지로 보존**한다.
- **Rationale**: engineer 원칙 — *"지금 ①/② 중 하나를 고르지 마라. **측정 가능한 시점에
  결정하라.**"* 이 게이트가 **"낙관적으로 밀어붙이다 4개월째에 실패를 발견"하는 최악을
  막는다.** 지금 ②를 고르면 필요 없을지도 모르는 6주를 미리 지불하는 것이고, ①을 고르고
  게이트를 안 두면 늦게 발견한다. **게이트가 두 실패를 동시에 막는다.**
  ※ 5개월은 사용자가 ADR-008에서 확정한 값이므로 ①이 그 결정과 정합한다.
     **②로의 전환은 기간 변경이므로 반드시 사용자 승인을 받는다** — G-W6에서 lead가 발의한다.
- **Consequences**:
  - **coder의 다음 과업이 정해졌다**: 본 파이프라인이 아니라 **L3 → L4·L5·L6 자동화**.
    (S1 설계가 ADR-012로 바뀌었으므로 지금 S1을 짜면 버리는 코드가 된다.)
  - 🔴 **① 고유 리스크(engineer가 정직하게 명시, 감수한다)**: **자동 과학검토가 인간
    전문가 검토를 부분 대체한다.** 25% 표본 인간 검토 + 10% 무작위 감사 + ADR-003 두
    축이 백스톱이지만, **계통적으로 잘못된 TS 집합은 표본검사를 통과할 수 있다.**
    이 위험은 제거되지 않는다. R-12 참조.
  - **자동화를 우리 환경에서 검증할 수 없다**(ADR-004) ⟹ 자동 triage 자체의 버그가
    왕복 1~2회를 더 먹을 수 있다. engineer 견적의 "추가 왕복 +1.5"가 그것이다.
  - S1 착수가 **1~2주 지연**된다. 절감(3.1~7.0주)이 이를 확실히 상회하므로 선투자가 옳다.
- **Revisit trigger**: **G-W6 게이트 (W6).** 그 외 — 파일럿 회신 단가가 비관값으로
  실현될 때(R-04), 계통적 재계산이 2회 발생할 때(a안에서도 19.5주로 여유 +2.0주까지 잠식).
- ⚠ **[2026-08-17 즉시 재개봉] ADR-014의 재스코핑으로 배분·일정 전제가 바뀌었다.**
  ①/②/G-W6 구조 자체는 유지되나 **숫자는 engineer 재산정 대기.**

---

## ADR-014: 🔴 **프로젝트 재스코핑 — 반응 전수 탐색이 본체가 되고, 미지 계로의 이전가능성이 최종 요구사항이 된다**

- **Status**: Accepted (지시 확정). **하위 설계는 proposer/engineer 재산출 대기**
- **Date**: 2026-08-17
- **Stage**: 전 stage (S2 중심)
- **Resolves**: **R-16** (발견 기능 청구서). **재개봉**: ADR-006, ADR-007, ADR-011,
  ADR-012(추가 축소 방향), ADR-013(배분·일정)
- **Context**: 사용자 지시 —
  > *"진행을 전면적으로 점검해야겠는데, **가능한 모든 reaction을 찾는것부터가 우선**이야.
  > 추후에 **잘 알려지지 않은 계**에 대해서도 시뮬레이션을 진행해야 해. 이 **가능한 반응
  > 모두 탐색 부분에서 대부분의 시간이 소요**될 거야. **AIMD는 개발 과정에서 최대한 배제**하고,
  > **경험적 방법론을 동원해서라도** 이 방법을 찾아."*
- **Decision**:
  1. 🔴 **R-16을 "지불한다"로 확정.** **S2-C(MLIP/reactive MD 발견기)를 스코프에 복원한다.**
     proposer의 §6.6 자진 철회를 취소한다. **발견 기능이 이 프로젝트의 본체다.**
  2. 🔴 **미지 계로의 이전가능성이 최종 요구사항이 된다.**
  3. **예산·시간의 무게중심을 S3 → S2로 옮긴다.** (기존 배분 S3 25% / S2 12% ⟹ 역전)
  4. **AIMD를 개발 과정에서 0에 수렴시킨다.** ADR-012(잔존 2 k core-h)보다 더 민다.
  5. **경험적 방법론 전면 허용** — ReaxFF, GFN2-xTB, MLIP/foundation model,
     group additivity, BEP/Evans–Polanyi, rule 학습. **커버리지가 정확도에 우선한다**
     (정확도는 이후 tier에서 회복).
- **Rationale**: 사용자의 판단이며 lead는 이를 수행한다. 덧붙여 **이 재조정은 우리 자원
  프로필과 오히려 정합한다** — engineer 진단상 **계산 자원은 봉투의 58%(3.4 M core-h)가
  미소비 전망이고 희소한 것은 인간시간**인데, **S3(TS 검토)는 인간 집약(0.31 h/건, 500건에서
  사람이 상한)이고 S2(탐색)는 계산 집약·인간 경량**이다. ⟹ **비싼 통화를 덜 쓰고 남는
  통화를 쓰는 방향**이며, engineer가 §R2-4에서 세운 "계산을 사람 시간으로 환전하라"의 연장이다.
- **Consequences — 무엇이 무너지는가 (정직하게)**:
  - 🔴 **알려진 답에 기대는 장치들이 전부 이전 불가다.** 이것이 이번 변경의 가장 깊은 결과다.
    - **ADR-007 SG-5 Tier A(목표종 7종 k-shortest path 보호)** — 미지 계에는 **보호할
      목표종이 없다.** 원리적으로 이전 불가. **계 비의존적 선별 원리로 대체해야 한다.**
    - **ADR-003 검증축(가스 수율·XPS 조성비)** — 미지 계에는 대조할 실험값이 없다.
      1차 계 검증으로는 유효하나 **일반 파이프라인의 검증 원리가 될 수 없다.**
    - **ADR-011의 LIBE 재사용** — 엔진(fragment-recombine)은 template-free라 이전되지만
      **데이터 재사용은 carbonate 화학 한정.** 미지 계는 **c ≈ 0 ⟹ engineer의 c*=75%
      규칙상 "자체 계산"이 일반 케이스**가 된다. LIBE는 1차 계 가속기로 재정의.
    - **proposer의 DRC/DSC 선별** — 관측량을 알아야 정의되는데 미지 계에서는 그 관측량이
      무엇인지도 모른다. **재정식화 필요.**
  - ⟹ **핵심 미해결 질문: 알려진 답 없이 "탐색이 충분했다"를 어떻게 판정하는가.**
    proposer에게 완결성 기준(수렴 지표)과 **blind test 설계**(1차 계에서 목표종 보호를
    일부러 끄고 돌려 알려진 생성물이 스스로 나오는지 확인)를 요구함.
  - **일정**: 탐색 전수화 + 이전가능성 실증은 **일이 늘어난 것이다.** ADR-013의 5개월(①)이
    유지되는지 engineer 재산정 중. **G-W6 게이트가 사실상 발동 예정일 가능성이 높다.**
  - **왕복 구조 위험**: 탐색이 세대별 반복이면 왕복이 늘어난다(engineer §11.1(e):
    평평한 배치 2회 vs 반복 루프 4~6회). **달력을 지배할 수 있다.**
  - 🟢 **파일럿 P3(gen-1 candidate fanout 실측)의 가치가 크게 올랐다** — 이제 그것이
    **프로젝트 본체의 조합 폭발 계수**를 재는 항목이다.
  - **proposer의 세 차례 청구서(R-09 → R-15 → R-16)가 옳았음이 확인됐다.** 발견 기능을
    잘라온 결정들이 상위 요구와 어긋나 있었다. 재작업의 원인은 상위 요구 변경이지
    proposer의 판단 오류가 아니다.
- **Revisit trigger**: proposer의 완결성 기준·계 비의존 선별 원리, engineer의 재배분·일정이
  도착하는 즉시 하위 ADR(006/007/011/012/013)을 순차 개정한다.

---

## ADR-015: 재스코핑의 방법론 골격 — 완결성은 **통계적으로 추정**하고, 선별은 **물성으로 정의**하며, **병목은 barrier surrogate로 이동한다**

- **Status**: Accepted (골격). **U-12(surrogate 설계)는 미해결 — 다음 라운드 1순위**
- **Date**: 2026-08-17
- **Stage**: S2 중심 (S1/S3/S4 파급)
- **Resolves**: **R-17**(계 비의존 완결성·선별 원리). **ADR-012 철회**,
  **ADR-007 SG-5 Tier A 대체**, **ADR-003 재진술**
- **Context**: ADR-014로 "전수 탐색 + 미지 계 이전가능성"이 요구가 되면서, 알려진 답에
  기대던 장치가 전부 무너졌다(R-17). proposer가 §14에서 대체 골격을 냈다.
- **Decision**:

  **1. 🔴 탐색 경계 = 세대·에너지 cutoff가 아니라 "발견률의 수렴"**
  - 외연적 경계("N세대까지")는 무엇이 있는지 알아야 정할 수 있어 **부적합**.
    **자기참조적 경계**(탐색이 새 구조를 더 못 낼 때까지)만 답 비의존이다.
  - 허용 transformation을 **조성 불가지론적**으로 정의: `break m / form n (m+n ≤ 4)`
    + 전하/스핀 변화 ∈ {−1,0,+1} + 회합/해리. **원소 목록에 의존하지 않으므로 이전된다.**

  **2. 🔴 완결성 판정 = Good–Turing 커버리지 + Chao1 (생태학의 종 풍부도 추정)**
  - `Ĉ = 1 − f₁/N` (f₁ = 한 번만 발견된 종). **정지 기준 Ĉ ≥ 0.95** [잠정]
  - `Ŝ = S_obs + f₁²/(2f₂)`. **정지 기준 (Ŝ−S_obs)/S_obs < 0.05** [잠정]
  - 우리 문제는 *"숲에 종이 몇 개인가"* 와 **수학적으로 동일**하다. 답 비의존이라 이전된다.
  - 🔴 **정직한 한계(proposer가 스스로 명시, 숨기지 않는다)**: *"Ĉ와 Chao1은 **표본추출기가
    표본추출하는 분포**의 커버리지를 잰다. 화학적 진실의 커버리지가 아니다. 엔진이 어떤
    부류에 **구조적으로 눈이 멀어 있으면** 그 부류는 f₁에도 f₂에도 나타나지 않으므로
    **Ĉ는 높게 읽히면서 현실은 놓친다.**"*

  **3. 🔴 ⟹ 다중 엔진 포획–재포획이 "선택"이 아니라 "필수"가 된다**
  - `N̂ = |S_A|·|S_B| / |S_A∩S_B|` (Lincoln–Petersen). **엔진이 하나면 완결성은
    원리적으로 추정 불가다.** 다중 엔진의 진짜 이유는 커버리지 확대가 아니라
    **완결성을 추정 가능하게 만드는 것.**
  - 🔴 **⟹ 엔진 선택 기준이 바뀐다: 개별 성능이 아니라 *실패 모드가 서로 독립적인가*.**
  - 독립성·균등포획 가정이 깨지면 N̂은 **과소추정(낙관)** 되므로 **Chao 이질성 보정형을
    쓰고 결과는 "누락량의 하한"으로만 보고**한다. 엔진 3개면 독립성 가정 자체를 검정 가능.

  **4. 🔴 선별 원리를 이름 기반 → 물성 기반으로 (SG-5 Tier A 대체)**
  - **P-1 관측 가능 부류를 ΔG_solv로 정의**: 기체(DEMS) = ΔG_solv 임계 이상 → 휘발 /
    응축상(XPS) = 임계 이하 → 석출. **ΔG_solv는 SMD로 이미 계산하는 산출물이지
    사전 지식이 아니다.** ⟹ **ADR-003은 폐기가 아니라 재진술로 살아남는다.**
  - **P-2** 체류시간 `τ = 1/Σk_out` (= 생성물의 정의 그 자체, 이름 불요)
  - **P-3** 관절 엣지 — 제거 시 큰 하류 부분망이 도달 불가해지는 엣지
  - **P-4** 고flux × 고분기엔트로피 (**DSC의 계 비의존적 일반화**)
  - **P-5** VoI (기존, 이미 계 비의존)
  - **새 SG-5 (사전식)**: `Tier A = P-1 ∪ P-3` > `Tier B = P-4` > `Tier C = P-5` > `Tier D = 잔여 flux`

  **5. 🔴 병목이 "발견"에서 "barrier"로 이동한다 — 이번 라운드 최대 발견**
  > *"10⁵~10⁶ 반응을 발견하면 그래프는 생기지만 **순위를 매길 수 없다.** DFT TS는 수백
  > 건이 상한이다(인간시간). ⟹ **진짜 산출물은 network가 아니라, 우리 DFT TS 집합으로
  > 학습되고 불확실도를 내는 barrier 대리모형(surrogate)이다.** 여기서 '경험적 방법론'은
  > 타협이 아니라 **핵심 기술**이다. 이것이 없으면 전수 탐색은 순위 없는 목록만 남긴다."*
  - ⟹ 사용자의 *"경험적 방법론을 동원해서라도"* 는 **타협 허용이 아니라 핵심 기술 지정**이었다.
  - **3층 구조 확정**:
    `발견층(계산집약·인간경량) → barrier층 surrogate(🆕 새 병목) → 검증층 DFT TS 수백 건(인간집약)`

  **6. 엔진 조합 = 3-source capture–recapture 성립 조건**
  `S2-A 열거(결정론적·전수)` ⟂ `S2-C/D 반응성 MD(확률적·응축상)` ⟂ `S2-B TS탐색(그래프편집)`
  - **S2-C 복원 + ReaxFF 재평가 상향** — proposer 자기 판단 2건 철회:
    *"발견 엔진에게 요구되는 것은 정확도가 아니라 **가설 생성**이다. ReaxFF의 오차는
    **위양성(버리면 됨)** 이지 위음성이 아니다. **위양성이 싼 계층에서 정확도를 요구한
    것이 내 오류였다.**"*

  **7. 개발기 AIMD = 0. ADR-012 철회**
  대체: D1(DFT 최적화 구조 대조, 비용 0) / D2(1D 퍼텐셜 스캔 ~40 SP) / D3(두 FF
  파라미터화의 스프레드를 오차막대로) / D4(응축상 앙상블 검증은 개발 후로 연기).
  **잃는 것(정량)**: 다체 패킹 앙상블 미검증 ⟹ λ_out 잔차 **±0.05 → ±0.10 eV.**
  새 목적함수(존재 여부가 문제이지 순위가 문제인 국면이 아님)에서 무해하다고 판정.

  **8. 이전가능성 검증 E1 < E2 < E3 (강도 순)**
  - **E1 Blind rediscovery** (최소 조건, smoke test): 목표종 보호·문헌 seeding을 전부 끄고
    돌려 **알려진 7종이 P-1~P-5 우선순위에서 몇 위인가.** 합격 = 전부 상위 10%.
    통과해도 이전가능성이 증명되지는 않는다(같은 계).
  - **E2 Leave-one-chemistry-out** (개발기 반복 게이트, **권장**): 한 화학 부류를 뺀 채
    조율하고 **뺀 부류에서 시험**(carbonate만으로 조율 → P–F 화학을 발견하는가).
    **미지 계를 실제로 모사하는 유일한 개발기 시험.**
    🟢 **LIBE의 FEC/VC/FSI/TFSI가 무료 hold-out 화학을 제공한다.**
  - **E3 사전등록 예측** (최종 인수, 가장 강함): 파이프라인 **동결 후** 미본 전해질계에
    적용, **예측을 먼저 기록하고** 문헌과 대조. **동결이 규율의 핵심** — 결과를 본 뒤
    조정하면 시험이 아니다.
- **Rationale**: **Q-B의 답이 Q-E의 시험으로 검증되는 닫힌 구조**다 — 선별 원리를
  제안하면서 그 원리의 반증 절차를 함께 냈다. 원리가 옳다면 이름을 모른 채로도
  LiF·Li₂CO₃·LEDC·C2H4·CO·CO2를 상위로 끌어올려야 한다.
- **Consequences**:
  - 🔴 **U-12(barrier surrogate) 신설 — 현재 최우선 미해결.** 아키텍처·특징(미지 계
    이전성이 설계 제약)·불확실도 추정(VoI와 능동학습을 구동)·학습 데이터 예산·
    **falsifier**. **이것이 없으면 전수 탐색은 순위 없는 목록이다.**
  - **U-13**: Ĉ ≥ 0.95 / Chao1 < 5% 임계는 **잠정**. 파일럿 종 축적 곡선으로 교체.
  - **U-14**: P-1의 ΔG_solv 임계(휘발/석출 판정). 🔴 **R-07(응축상 격자에너지 미해결)이
    여기서 재등장한다.** SMD의 절대 ΔG_solv 정확도가 판정을 좌우.
  - **blind test 정답지는 critic이 독립적으로 만든다** — 방법 설계자가 만들면 자기가
    찾을 수 있는 것만 정답에 들어간다. 독립성이 E1/E2의 성립 조건.
  - engineer 배분 재계산의 대상이 3층으로 늘었고, **"가장 싼 엔진 하나" 선택지는 사라졌다**
    (최소 3개 동시 운용이 완결성 추정의 전제).
- **Revisit trigger**: U-12 설계가 실패하거나 surrogate 불확실도가 선별을 구동하기에
  부족한 것으로 판명될 때 — 그 경우 전수 탐색의 규모 자체를 재검토해야 한다.
  E1에서 알려진 7종이 상위 10%에 들지 못할 때(P-1~P-5 선별 원리 결함).

---

## ADR-016: **미량 H2O를 principal species에 추가한다** — ADR-001 개정

- **Status**: Accepted (사용자 승인)
- **Date**: 2026-08-17
- **Stage**: S2 (ADR-001 조성 정의 개정)
- **Resolves**: critic 발견 D-3
- **Context**: 🔴 **critic이 blind test 정답지를 만들다가 아무도 보지 못한 구멍을 찾았다.**
  S2-A의 fragment-recombine 엔진은 **principal molecule 목록에서 분해한 원자 조각의
  조합만** 만들 수 있다. ADR-001의 조성 정의(EC:EMC 3:7 + 1M LiPF6, **첨가제 없음**)에
  H2O가 없으므로 **H·OH 조각이 pool에 들어오지 않고, LiPF6 가수분해·HF 매개 화학 전체가
  원리적으로 생성 불가**하다.
  > critic: *"하필 확인 수준이 가장 높은(`[RECALL-강]`) 항목들이 이 갈래에 몰려 있다
  > (LiPF6 + H2O → LiF + POF3 + 2HF, HF + Li2CO3(s) → LiF(s) + H2O + CO2).
  > **엔진의 결함이 아니라 입력 정의의 문제이지만 결과는 같다** — 문헌에서 가장 확실하다고
  > 알려진 반응 갈래 하나가 통째로 사각지대가 될 위험이 있다."*
- **Decision**: **미량 H2O를 principal species에 추가한다.** HF를 별도 초기 species로 둘지는
  proposer 판정(H2O에서 생성되게 두는 것과 비교).
- **Rationale**: 상용 전해질은 실제로 잔류 수분 10~20 ppm을 가지며, LiPF6 가수분해는 SEI
  문헌에서 가장 확립된 반응 중 하나다. **무수 계를 가정하면 XPS 조성비에서 LiF 비율을
  계통적으로 과소평가**한다 — ADR-003 축(b)에 직접 걸린다. 추가 비용은 작다.
- **Consequences**:
  - **N_pool과 반응 수가 증가**한다. engineer의 §R6.1 수확체감 곡선과 N_pool 상한(≤6,000,
    ADR-011)에 이 증분이 앉을 자리가 있는지 확인 필요.
  - **미량 species의 농도 취급이 새 문제다** — H2O는 미량인데 **촉매적으로 순환**한다
    (HF 생성 → 소모 → 재생). 정상상태 농도 설정 방법을 proposer가 정해야 한다.
  - 🔴 **이 발견의 일반 교훈**: `fragment-recombine 엔진은 입력 목록에 없는 화학을
    "못 찾는" 게 아니라 "물을 수 없다."` **principal species 목록 자체가 탐색 공간의
    하드 경계**이며, ADR-014의 "미지 계" 요구 하에서는 **이 목록을 어떻게 정하는가가
    방법의 일부**가 된다. 미지 계에서는 무엇을 principal에 넣어야 할지도 모른다.
    ⟹ **U-15 신설**: 미지 계에서 principal species 목록을 정하는 원리.
- **Revisit trigger**: H2O 갈래가 network를 감당 못 할 만큼 키울 때(그 경우 미량 species를
  별도 tier로 분리). E1 blind test에서 LiF 경로가 여전히 상위에 안 오를 때.

---

## ADR-017: 이전가능성 데모 = **1계로 시작**, 데모 계 수를 일정 조절 노브로 삼는다

- **Status**: Accepted (사용자 승인). **ADR-013 보완**
- **Date**: 2026-08-17
- **Stage**: Infra
- **Resolves**: engineer Q9
- **Engineer 입장 (§R6.5)**: ADR-014의 재스코핑으로 **완주 확률이 Round 5의 88~92%에서
  75~80%(데모 3계)로 내려갔다.** 선택은 둘 — **(가) 5개월 + 데모 1계 = 85%** /
  **(나) 6.5개월 + 데모 3계 = 93%+.** 권고는 (가)로 시작해 G-W6에서 (나) 전환 판정.
  > *"데모 계는 1차 계 파이프라인이 완성된 뒤에 붙는 **순수 증분 작업**이라 나중에
  > 추가하기 쉽고 잘라내기도 쉽다. **일정 위험을 흡수하는 완충재로 쓰기에 최적이다.**
  > ⇒ **데모 계 수를 일정 조절 노브로 삼아라. 다른 것을 자르지 마라.**"*
- **Decision**:
  1. **이전가능성 데모 = 1계로 시작.** 5개월 유지, 완주 확률 **85%**.
  2. 🔴 **절단 우선순위를 고정한다**: 일정이 밀리면 **① 데모 계 수 → ② (G-W6에서) 기간 연장**
     순으로 건드린다. **S3 건수·ADR-003 검증축·발견 엔진 수는 마지막까지 자르지 않는다.**
  3. **G-W6에서 (나) 전환 여부를 재판정**한다 (ADR-013의 게이트에 이 항목을 합친다).
- **Rationale**: engineer 논거 — **이전성은 "시연"이지 "통계"가 아니므로** 1계로도 ADR-001의
  확장성 요구는 만족한다. 그리고 데모 계는 증분 작업이라 **일정 완충재로서 가장 싸게
  붙였다 뗐다 할 수 있는 항목**이다. 다른 것(검증축·엔진 수)을 자르면 되돌릴 수 없다.
- **Consequences**:
  - E2(leave-one-chemistry-out)는 **1차 계 내부에서** 수행한다(carbonate로 조율 → P–F 화학
    시험 등). 🟢 **LIBE의 FEC/VC/FSI/TFSI가 무료 hold-out 화학을 제공**하므로 데모 계를
    늘리지 않고도 E2를 여러 번 돌릴 수 있다.
  - E3(사전등록 예측)는 데모 1계로 수행 — **동결 규율은 그대로.**
- **Revisit trigger**: **G-W6.** 또는 E2가 1차 계 내부 hold-out만으로 이전성을 보이기에
  불충분한 것으로 판명될 때.

---

## ADR-018: U-12 barrier surrogate 설계 채택 — 판정 기준은 **"정확한가"가 아니라 "결론이 오차에 견디는가"**

- **Status**: Accepted (설계 골격). 하위 `[UNRESOLVED]` U-12-a/b/c 존치
- **Date**: 2026-08-17
- **Stage**: S2/S3 횡단 (ADR-015가 지목한 신규 병목)
- **Resolves**: **U-12**
- **Context**: ADR-015에서 **병목이 "발견"에서 "barrier"로 이동**했다. 10⁵~10⁶ 반응을
  발견해도 DFT TS는 수백 건이 상한이므로, **진짜 산출물은 network가 아니라 barrier 대리모형**이다.
- **Decision (proposer §15 채택)**:
  1. **Marcus 고유장벽 분해**를 모델 골격으로 (§15.1). **계층 베이즈(부분 풀링)** 아키텍처 —
     계열별 데이터가 얇아도 전역 정보를 빌려 쓴다.
  2. 🔴 **무장벽·확산율속 반응(라디칼 재결합, 이온 회합)은 surrogate 밖에 둔다.**
     *"섞으면 계열 추정이 오염된다."* 별도 병렬 처리 부류.
  3. **특징 설계에서 이전성을 배제 규칙으로 강제한다** (§15.3) — 특정 원소·작용기에
     특화된 특징을 **먼저 금지 목록으로 명시**하고 설계한다. ADR-014의 미지 계 요구가
     설계 제약으로 코드화되는 지점.
  4. **다중충실도 Δ-learning**을 학습 데이터 최대 레버로 (§15.4) — 저수준(xTB) 대량 +
     DFT 소량의 차분 학습.
  5. **불확실도는 세 원천(모델·데이터·계열)을 분리하고 conformal로 보정** (§15.5).
     이 불확실도가 §13.4 VoI와 능동학습(다음 DFT TS를 어디에 쓸지)을 구동한다.
  6. 🔴 **falsifier = precision@k** (surrogate 상위 k 중 DFT 진짜 상위 k에 속하는 비율) +
     **결론 강건성 시험**.
- **🔴 Rationale — 이 프로젝트 전반의 판정 원칙으로 승격한다**:
  > proposer §15.6: *"surrogate 예측을 **자기가 주장하는 불확실도만큼 섭동**시켜 앙상블을
  > 돌린다. 안 뒤집히면 **이 결정에 대해서는 surrogate가 충분하다. 일반적으로 부정확해도
  > 상관없다.** ⟹ **'surrogate가 정확한가'가 아니라 '우리가 내리려는 결론이 surrogate
  > 오차에 견디는가'가 우리가 답해야 할 질문이다.**"*

  이 기준을 **surrogate에 한정하지 않고 프로젝트 전반의 판정 원칙으로 채택한다.**
  우리는 계산 자원·인간시간·달력 모두에서 제약되어 있고, **"모든 것을 정확하게"는
  달성 불가**다. 대신 **각 결론이 어떤 오차까지 견디는지를 측정**하고, 견디지 못하는
  지점에만 정밀도를 투입한다. ADR-007의 `barrier_source: rule` ±0.2 eV 일괄 스캔,
  ADR-015의 앙상블 DRC, ADR-012의 λ 오차 허용 판정이 전부 같은 원리의 사례였다 —
  **이제 그것을 명시적 원칙으로 올린다.**
- **Consequences**:
  - **U-12-a** Marcus 고유장벽 형태가 우리 반응 부류 전반에 성립하는가 (원자·기 전달에는
    부적합할 수 있음). `[UNRESOLVED]`
  - **U-12-b** 공개 반응 barrier 데이터셋의 존재·적합성 **미확인. 있다고 가정하지 않는다.**
  - **U-12-c** 반응 계열 수 15~25는 추정(≥3건 & σ<0.1 eV 기준에서 유도). 실측 필요.
  - 🔴 **R-20 잔존**: surrogate가 실패하면 전수 탐색 전체가 순위 없는 목록이 된다.
    falsifier(precision@k + 결론 강건성)가 그 실패를 **조기에 드러내는** 장치다.
- **Revisit trigger**: precision@k가 실용 수준에 못 미칠 때. 결론 강건성 시험에서
  주요 결론이 surrogate 자체 불확실도만으로 뒤집힐 때(그 경우 DFT TS 배분을 재설계).

---

## ADR-019: 재스코핑 확정본 — 5개월 성립(82%), 독립 3-source = E1⟂E2⟂E3a(ReaxFF), 왕복 7회

- **Status**: Accepted. **단 독립성 판정 기준은 proposer 과학적 승인 대기**
- **Date**: 2026-08-17
- **Stage**: Infra 전반
- **Resolves**: **R-22**(조건부), engineer Q-1~Q-5 확정. **ADR-013/017 숫자 확정**
- **Engineer 입장 (§R7~§R8 확정본)**:

  **1. 🟢 R-22(엔진 독립성) 해결 — 4번째 축이 필요 없다**
  lead 지적(S2-B와 xTB 반응성 MD가 GFN2-xTB 공유)은 정당하나, **상관은 두 축
  (에너지 모형 / 탐색 방식)에서 따로 발생하고 각 쌍이 최소 한 축에서 독립이면 된다.**

  | 엔진 | 에너지 모형 | 탐색 방식 |
  |---|---|---|
  | **E1** 그래프 열거 | thermo DFT | 결정론적 조합 |
  | **E2** xTB TS 탐색 | GFN2-xTB | 그래프편집 + 최적화 |
  | **E3a** ReaxFF MD | ReaxFF | 확률적 MD |
  | E3b xTB 반응성 MD | GFN2-xTB | 확률적 MD |

  E1⟂E2, E1⟂E3a, **E2⟂E3a 모두 두 축에서 독립.** E2⟂E3b(에너지 동일)와
  E3a⟂E3b(탐색 동일)만 상관.
  ⟹ **독립 3-source = E1 ⟂ E2 ⟂ E3a(ReaxFF). E3b는 보조 실행으로 강등**(계속 돌리되
  독립 포획원으로 세지 않는다). **바뀌는 것은 통계 처리이지 계산량이 아니다.**
  🟢 *"통계적 독립성에 필수인 엔진(ReaxFF)이 하필 가장 싼 엔진이다 — 25 k core-h,
  인간 4~8 h, 재적합 불필요. 운이 좋다."*
  ※ engineer는 **자기 Round 1의 ReaxFF 비판을 철회**했다: proposer의 *"발견 엔진에
  요구되는 것은 정확도가 아니라 가설 생성"* 논거를 수용해 **재적합 없이 기존 파라미터를
  그대로 쓰기로** 했고, 계상했던 **인간 1~3주가 0이 됐다.**
  ※ 4번째 축이 필요해지면 **DFTB/PM7이 계당 +30~60 k, 왕복 +0회**로 값싸다.

  **2. 🟢 H2O 증분은 상한을 위협하지 않는다 — 그리고 수확체감의 예외다**
  pool ×1.3~1.8(기준 ×1.5) ⟹ N_pool 7,500 (**상한 20,000의 38%**), 계당 618 k → **798 k (+29%)**.
  🔴 **"수확체감 구간에 들어가는가"는 잘못된 질문이다**:
  > *"수확체감은 **같은 화학 안에서 더 높은 에너지의 조각을 추가**할 때 나타난다.
  > H2O는 그것이 아니다. fragment-recombine은 pool에 없는 원자 조성을 만들 수 없으므로
  > H2O 부재는 커버리지 부족이 아니라 **구조적 접근 불가**였다.
  > ⟹ **H2O 증분은 깊이 축이 아니라 폭 축이다. 수확체감이 적용되지 않는다.**"*
  ⟹ 이 프로젝트에서 **비용 대비 가치가 가장 좋은 +29%**로 평가.

  **3. 배분 확정 (5.80 M core-h, 데모 1계)** — S1 110 k / S2 1차계 798 k / S2 데모 798 k /
  S3 579 k(1차 175건 + 데모 30건) / S4 <5 k / **예비 3.13 M(54%)**.
  🔴 **"미소비 61%"는 오해다 — 예비의 96%가 이미 조건부 용처 지정**:
  데모 +2계 1,596 k / N_DFT 5,000→10,000 600 k / 계통 재계산 1회 800 k.
  > *"실제 자유 여유는 134 k(2%)뿐이다. **'남아돈다'는 표현을 여기서는 쓰지 않겠다.**"*

  **4. 일정 확정 — 5개월 성립.** `3(개발) + 7×0.5(왕복) + (S1 0.8 + S2 2.5 + S3 2.0) + 3(S4·검증)`
  | | 기간 | 여유 |
  |---|---|---|
  | 기본 | 14.8주 | **+6.7주** |
  | 계통 재계산 1회 | 17.8주 | +3.7주 |
  | **계통 재계산 2회** | **20.8주** | **+0.7주 (양수)** |

  **완주 확률 82%.** 왕복 **7회** 확정, 그중 **RT-7(데모 1계)만이 유일한 안전 노브**
  (ADR-017의 절단 우선순위와 정합).

  **5. 🔴 자동화 L1~L7은 "권고"가 아니라 "전제"가 됐다 (§R7.6)**
  surrogate 층 인간 필수분(+21~32 h)이 얹히면서 **인간 필수분 267~437 h vs 용량 344 h(주20h)
  = 78~127%.** **자동화 없이 H20이면 27% 초과.**
  ⟹ **G-W6 게이트의 (i)항(L1·L3·L4 동작 여부)이 일정 판정이 아니라 성립 판정이 된다.**
- **Decision**: 위 1~5를 전부 채택한다. **단 1번(독립성 판정 기준)은 방법론 주장이므로
  proposer의 과학적 승인을 조건으로 한다** — engineer 자신도 *"비용 문제가 아니라
  완결성 수치의 신뢰도 문제이므로 proposer/critic에게 넘긴다"* 고 명시했다.
- **Consequences**:
  - 🔴 **[신규 U-08 구속] H2O가 S4를 kMC → microkinetics(강성 ODE)로 민다.**
    미량 H2O(10~50 ppm ≈ 몰분율 0.1%)인데 HF 화학은 **자기촉매적**이라 중요도는 낮지 않다.
    **kMC는 사건을 속도에 비례해 뽑으므로 3자릿수 농도 차 + 시간척도 분리가 겹치면
    지배 화학에만 스텝을 소모하고 가수분해 갈래를 사실상 못 본다**(필요 스텝 10⁹~10¹²).
    ADR-003이 공간 차원을 뺐으므로 **0-D 강성 ODE가 이미 가능**하고, 그 경로면 농도
    3자릿수 차이를 **적분기가 자동 처리**한다. 비용은 여전히 무료.
    ⚠ engineer: *"지금 정하지 않으면 S4 구현 단계(W15 이후)에 발견되어 그때는 고칠
    시간이 없다."* **U-08 설계에 반드시 반영.**
  - **RT-3(S2 전체 자율 DAG)의 내부 구조가 핵심** — 3엔진 발견 병렬 → 열거·여과 →
    thermo DFT → xTB TS 앵커 2×10⁵ → surrogate v0 → 랭킹, **총 7.5일 / 사용자 개입
    `sbatch` 1회.** 이를 왕복 4~5회로 쪼개면 **달력 1.5~2.0주 손실.**
    **coder 스펙의 최우선 구조 요구다.** (ADR-008 U-09 선택이 여기서 배당을 냈다.)
- **Revisit trigger**: proposer가 독립성 판정 기준("각 쌍이 최소 한 축에서 독립이면 된다")을
  기각할 때 → 4번째 축(DFTB/PM7) 추가. **G-W6**에서 자동화 미동작 시 → 성립 자체 재검토.

---

## ADR-020: R-22 해결 — 독립 3축 = S2-A ⟂ (S2-B+S2-C 병합) ⟂ ReaxFF. **종속성은 배제 대상이 아니라 추정 대상**

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S2
- **Resolves**: **R-22**. ADR-019 Decision 1을 **수정 확정**
- **Context**: lead가 "S2-B와 S2-C가 GFN2-xTB를 공유하면 함께 눈이 멀어 완결성이 낙관적으로
  읽힌다"고 제기. engineer가 축 기반 논거로 해법을 냈고, proposer가 **포획 확률을 분해해**
  더 정확한 판정을 냈다. 두 답은 결론이 같고 근거가 다르며, **proposer 쪽이 옳다.**
- **Proposer 판정 (§16.1)**:

  **1. 🔴 "xTB barrier 오차"는 두 엔진에 상관되게 작용하지 않는다 — 포획 구동 요인이 다르다**
  ```
  S2-B: P(포획) = P(그래프 편집이 열거됨) × P(xTB TS 탐색이 수렴)   ← 열거가 구동. 에너지 아님
  S2-C: P(포획) = P(궤적에서 반응이 실제로 일어남) = f(xTB barrier, T, 표집시간)
  ```
  xTB가 barrier를 엉뚱하게 높게 주면 — **S2-C는 궤적에서 그 반응이 안 일어나 놓치지만,
  S2-B는 편집이 이미 열거됐으므로 TS를 여전히 찾는다**(에너지만 틀리게 붙는다). **포획된다.**

  **2. 🔴 [coder 구속 — 독립성의 성립 조건] S2-B는 탐색 단계에서 barrier cutoff를 적용하면 안 된다.**
  > *"수렴한 것은 전부 기록하고 필터는 나중에 건다. **cutoff를 탐색 단계에 두는 순간
  > S2-B의 포획이 xTB 에너지에 종속되어 S2-C와 실패 모드가 상관된다. 이 한 줄이 독립성의
  > 성립 조건이다.**"*

  **3. 진짜 상관 실패 모드는 "틀린 barrier"가 아니라 "틀린 구조/위상"**
  xTB가 Li 배위 하전종의 비물리적 해리, P–F 배위수를 틀리는 경우(proposer가 §1.5에서
  *"GFN2-xTB 신뢰도가 급락하는 영역이고 우리 계가 정확히 그 영역"* 이라 쓴 바로 그것)에는
  두 엔진이 같은 방향으로 눈이 먼다. **⟹ 이것이 검사 대상이다.**

  **4. 정직한 축 구성 — "3개인 척하지 말고 2개는 병합한다"**
  ```
  축 1: S2-A 그래프 열거   (DFT/LIBE 열화학. 실패 모드 = pool 정책·문법 한계 = critic D-2~D-5)
  축 2: S2-B + S2-C 병합    (xTB 해밀토니안. 실패 모드 = 구조/위상 오차)
  축 3: ReaxFF 반응성 MD    (결합차수 力場. 실패 모드 = 파라미터 부재/부정확)
  ```
  **S2-A는 진짜로 독립이다** — 실패 모드의 *종류*가 다르다(문법 vs 해밀토니안).
  ⟹ **A ⟂ (B,C) 성립. B ⟂ C는 부분적으로만 성립** ⟹ B와 C를 하나로 병합해 선언한다.

  **5. 🔴 ReaxFF를 넣는 원칙적 이유 = "커버리지를 더"가 아니라 "독립성 공급원"**
  결합차수 기반 경험 力場으로 긴박구속(tight-binding)인 xTB와 **함수 형태·파라미터화 절차가
  완전히 다르다** ⟹ 실패 모드가 상관될 이유가 없다.
  ※ GFN1/GFN-FF는 같은 계열이라 독립성이 약하다 — **차선이지 대체재가 아니다.**

  **6. 🔴 독립성을 가정하지 않고 *측정*한다 — 로그선형 포획–재포획 모형**
  3개 소스면 각 반응의 포획 이력이 **2³ = 8칸 분할표**를 이룬다. 여기에 로그선형 모형
  (생태학·역학 표준)을 적합: `M0`(완전 독립) / `M_BC`(B–C 상호작용항) / `M_AB, M_AC, M_ABC`.
  - **적합된 상호작용항의 크기가 곧 종속성의 정량치**다. AIC로 모형 선택.
  - 종속성이 유의하면 **그 항을 포함한 모형으로 N̂을 추정**한다.
    ⟹ **종속성은 배제 대상이 아니라 추정 대상이 된다.**
  - 🔴 **소스가 2개면 분할표가 2²=4칸이고 상호작용항이 식별 불가하다. ⟹ 제3축의 진짜 값어치.**
- **Decision**: proposer의 4·5·6을 채택한다. **ADR-019 Decision 1의 "E3b를 보조로 강등"은
  유지하되, 근거를 "축이 다르므로 독립"에서 "포획 구동 요인이 다르므로 barrier 오차는
  비상관, 단 구조/위상 오차는 상관 → B와 C를 병합 선언"으로 교체한다.**
  ReaxFF는 **비용이 아니라 독립성 공급 목적**으로 필수 채택.
- **🔴 Consequences — 남는 한계를 반드시 명시한다**:
  > proposer: *"포획–재포획은 **모든 소스가 공유하는 맹점은 원리적으로 탐지하지 못한다.**
  > 우리 세 축은 전부 **분자 수준**이므로, critic D-2(응축상 격자가 반응물)는 세 축 모두에서
  > 보이지 않고 **Ĉ는 높게, N̂은 작게 읽힌다.**"*

  ⟹ **capture–recapture(정량)와 critic의 D-목록(구조적 열거)은 상호보완이며 둘 다 필요하다.
  어느 하나로 다른 하나를 대체할 수 없다.** ⟹ **critic의 맹점 목록 작성은 일회성 과업이
  아니라 상시 유지 항목으로 승격한다.**
  - **coder 구속 신설**: S2-B 탐색 단계 barrier cutoff 금지 (위 2번).
  - engineer의 축 기반 논거와 결론이 같으므로 **예산·일정(ADR-019)은 변경 없다.**
    4번째 축(DFTB/PM7)은 불필요 — 단 필요해지면 계당 +30~60 k, 왕복 +0회로 값싸다.
- **Revisit trigger**: 로그선형 모형에서 B–C 상호작용항이 너무 커서 N̂ 추정이 불안정할 때
  → 제4축 추가. critic D-목록이 세 축 공유 맹점을 새로 드러낼 때.

### 🔴 개정 (2026-08-17, proposer §17 + lead 중재) — 축 3을 ReaxFF → **PM7**로, ReaxFF는 1회성 교정축으로

**엇갈림의 정체 (lead 중재)**: engineer는 R7.3에서 ReaxFF 비판을 철회하며 *"재적합 없이
기존 파라미터를 쓴다, 인간 1~3주 → 0"* 이라 했고, proposer는 §17.4에서 *"engineer의
ReaxFF 반론을 수용한다 — 상시 축으로 쓰면 이전성 요구를 깬다"* 고 했다. **충돌이 아니다:**
- **engineer가 옳은 것**: **1차 계**(Li/C/H/O/F/P)에 대해 기존 파라미터로 충분하다 → 비용 0.
- **proposer가 옳은 것**: **미지 계**에 새 원소(S/N/B — LiFSI/LiTFSI/LiBF4)가 들어오면
  파라미터가 없거나 **분기가 달라 섞어 쓸 수 없다.** 계당 1~3주가 되살아난다.
  ⟹ **상시 축으로는 ADR-014/015의 이전성 요구를 깬다.**

**확정 구성**
```
축 1: S2-A 그래프 열거     (DFT 열화학 / 실패모드 = 문법 한계)  — 상시, 이전성 최상
축 2: S2-B + S2-C 병합     (GFN2-xTB / 공유 맹점)               — 상시
축 3: PM7 (MOPAC)          (NDDO 계열 — GFN2와 형식이 완전히 다름) — 상시, 계당 셋업 0
(교정) ReaxFF              (결합차수 力場 / 최상 독립)           — 🔴 1차 계에서 1회만
(진단) X2                  xTB↔DFT 위상 불일치 종 목록          — 반응 없이 공유맹점 상한 측정
```
~~🔴 **ReaxFF 재배치의 논리**: 1차 계에 한 번만 세워 B–C 종속성의 크기를 실측하고,
그 값을 미지 계로 "이월된 가정"임을 명시한 채 넘긴다.~~
🔴 **[사용자 지시로 취소] — 아래 "ReaxFF 전면 배제" 참조.**

**추가 판정 — engineer의 MLIP 탈락 근거는 범위가 과했다**: 그의 반론은 *"AL 루프가 계마다
6주"* 인데 **zero-shot 사용에는 AL 루프가 없다.** 다만 zero-shot foundation MLIP은 대개
중성·폐각 DFT로 학습되어 **하전·개각종 입력을 못 받는 약점**이 있어(우리 화학의 본체),
PM7이 1순위를 유지한다. **U-19 확인 시 MLIP이 2순위로 살아난다.**

### 🟢 proposer가 추가로 세운 두 장치 (§17.2·17.3) — 채택

**1. 2-source로 후퇴하면 결론이 한쪽으로만 유효해진다 ⟹ 제3축은 필수다**
> *"편향의 **방향**을 알므로 2-source 결과는 단측 결론으로 유효하다: `실제 누락 ≥ N̂ − S_obs`.
> `N̂ − S_obs`가 크면 **'탐색 부족'이 결정적으로 입증**되지만, 작으면 **아무 결론도 못 낸다**
> (진짜 수렴인지 상관 때문인지 구분 불가). ⟹ **2-source는 '덜 탐색했다'는 증명할 수 있어도
> '충분히 탐색했다'는 증명할 수 없다. 우리에게 필요한 것은 후자다.**"*

**2. 🔴 CR 내부 검정에만 의존하지 않는다 — 우리에겐 "정답을 아는 검증 표본"이 있다**
- 로그선형 CR의 한계: 3-source면 관측 칸 7개 vs 모수 8개 ⟹ **3원 상호작용을 0으로 가정해야
  식별된다(가정이지 검정 결과가 아니다).** 더 심각하게 **포획 이질성**(반응마다 찾기 쉬움이
  다름)이 **완전 독립인 소스에도 양의 상관을 만든다**(Chao M_h) ⟹ B–C 항이 유의해도
  공유 해밀토니안 때문인지 단순 난이도 이질성 때문인지 **구분되지 않는다.**
- **완화 1**: 난이도 공변량(ΔG_rxn, 변하는 결합 수, 분자도, 종 크기 — **전부 이미 갖고 있다**)을
  넣은 조건부 모형(M_th). **공변량 조건화 후에도 남는 B–C 항이 공유 해밀토니안 신호다.**
  ⟹ **coder 구속: 로그선형 모형에 난이도 공변량을 반드시 포함할 것.**
- **완화 2 (더 강함)**: **S3의 DFT TS 집합(수백 건)이 "개체군을 아는 검증 표본"** 이다
  — *"대부분의 CR 응용에는 없는 사치다."* ① `P(found_C|found_B)` vs `P(found_C)` 직접 검정
  ② 초과분이 xTB 오차·종 불안정성과 상관되는지로 **원인 귀속** ③ 종 단위 진단.
- 🔴 **[신규 필수 진단 X2]** pool 전 종의 `xTB 최적화 위상 ≠ DFT 최적화 위상` 비율
  = **E3~E5 공유 맹점의 직접적 상한.** *"공유 맹점을 추정하지 않고 **열거**한다. 반응을
  하나도 안 돌리고 공유 맹점의 크기를 미리 잴 수 있다."* 증분 비용 ≈ 0.

### 🔴 재개정 (2026-08-17, 사용자 지시) — **ReaxFF 전면 배제**

> 사용자: **"ReaxFF도 배제해."**

**최종 확정 구성**
```
축 1: S2-A 그래프 열거   (DFT 열화학 / 실패모드 = 문법 한계)   — 상시
축 2: S2-B + S2-C 병합    (GFN2-xTB, 긴박구속 / 공유 맹점)      — 상시
축 3: PM7 (MOPAC)        (NDDO)                                — 상시, 계당 셋업 0
(진단) X2                 위상 불일치 종 목록 — 유지·확장 검토
~~(교정) ReaxFF~~         🔴 삭제
```

**🔴 이 배제가 만드는 위험 (lead 판단 — 기록하고 넘어간다)**
ReaxFF는 **결합차수 力場이라 QM과 형식이 근본적으로 달랐다.** 배제하면 **남은 축 2·3이
둘 다 반경험 QM**이다(tight-binding vs NDDO). 형식은 다르나 **둘 다 최소기저 + 파라미터화
QM**이고, 반경험법이 공통으로 약한 영역이 **하필 proposer가 §1.5에서 "우리 계가 정확히
그 영역"이라 쓴 Li 배위 하전종·P–F 결합**이다.
⟹ **축 2와 축 3이 함께 눈이 멀 가능성이 ReaxFF가 있을 때보다 커졌다.**

**lead가 제안한 완화 (proposer 판정 대기)**: **X2를 확장한다.**
```
|xTB실패 ∩ PM7실패| / |xTB실패 ∪ PM7실패|   ← 반경험 QM 공유 맹점의 직접 측정치
```
X2는 지금 `xTB 위상 ≠ DFT 위상`인 종을 센다. 여기에 `PM7 위상 ≠ DFT 위상`을 함께 재고
**두 집합의 교집합을 측정**하면, **ReaxFF 1회성 교정이 주려던 "축 간 종속성 크기"를
반응을 하나도 안 돌리고 더 싸게 얻는다.** 비용은 PM7 종 최적화 추가뿐(무료 수준).
proposer에게 이 방향의 타당성과 **놓치는 것**을 판정하도록 지시함.

**🔴 U-18이 단일 실패점이 됐다**: ReaxFF라는 대비책이 사라졌으므로 **PM7/MOPAC을
air-gapped 클러스터에 반입할 수 없으면 축 3이 통째로 없어지고 2-source로 후퇴한다.**
그리고 §17.2에 따라 **2-source는 "덜 탐색했다"는 증명해도 "충분히 탐색했다"는 증명하지
못한다** ⟹ **ADR-014의 "전수 탐색" 주장 자체가 무너진다.**
⟹ **U-18은 예산 항목이 아니라 성립 조건이다.** engineer에게 우선 처리 지시:
① MOPAC 라이선스가 **네트워크 인증을 요구하는지**(요구하면 air-gapped 불가)
② 🔴 **RT-2에 PM7 가용성 프로브를 얹어 축 3의 존폐를 W4에 확정**(왕복을 늘리지 않는 순수 이득)
③ 불가 시 차선책 가격표(DFTB3 / zero-shot MLIP)

**신규 `[UNRESOLVED]`**: **U-18** PM7/MOPAC 가용성·라이선스·**air-gapped 반입 가능성**
(🔴 **단일 실패점**) / **U-19** zero-shot foundation MLIP의 하전·개각종 처리 가능 여부
(축 3 차선책 후보라 우선순위 상승).

---

## ADR-021: 🔴 **R-07 · U-14 · U-08이 하나의 장치로 동시에 닫힌다** — 석출을 가역 반응쌍으로, 임계는 계산된 K_sp로

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S4 (+ S2 phase 태그)
- **Resolves**: **R-07**(응축상 석출 자유에너지 — ADR-003 이래 최장기 미해결),
  **U-14**(ΔG_solv 임계), **U-08**(S4 방법 선택)
- **Context**: R-07은 ADR-003 시점부터 *"검증축 (b)의 최대 위험"* 으로 열려 있었다 —
  분자 CRN이 LiF·Li₂CO₃를 분자 단위체로만 표현해 **격자 에너지를 통째로 빠뜨리고
  eV급 오차**를 낸다. engineer가 §R8.3에서 H2O 도입의 하류 구속(kMC 강성)을 발견했고,
  lead가 R-07·U-14·U-08을 **묶어서 설계하라**고 지시했다.
- **Proposer 판정 (§18.7)**:

  **1. 🔴 kMC 배제 — engineer의 결론을 지지하되 근거를 교체한다**
  > *"engineer의 논거(스텝 10⁹~10¹²)는 옳다. **그러나 kMC 진영에는 표준 대응책
  > (τ-leaping, 빠른/느린 반응 하이브리드 분할)이 있으므로 '스텝 수가 많다'만으로는
  > 배제 논거로 약하다.**"*

  **더 강한 근거 (비용이 아니라 물리)**: kMC를 써야 하는 이유는 **딱 두 가지 —
  (i) 공간 상관, (ii) 작은 개체수(copy number)에서의 요동.**
  **ADR-003이 (i)을 이미 제외했다.** 그리고 (ii)도 성립하지 않는다 — **최소 농도 species인
  H2O조차 1.3 mM이고 어떤 현실적 제어 부피에서도 개체수 ≫ 1이다.**
  ⟹ **결정론적 극한이 유효하다. 확률성이 사올 물리가 없다.**
  ⟹ **강성 ODE(음함수 적분기)는 타협이 아니라 정확히 맞는 도구다.**

  **2. 🔴 석출을 "큰 속도상수를 갖는 가역 반응쌍"으로 둔다 — DAE를 피한다**
  석출은 **용해도 구속**을 만든다(고체 존재 시 용존 농도가 포화값에 고정) ⟹ 원리적으로는
  **상보성 조건을 갖는 DAE**이지 평범한 ODE가 아니다.
  **실용 처방**: 석출/용해를 큰 속도상수의 가역 쌍으로 두어 완화시키면 **강성 적분기가
  알아서 준평형으로 몰아주고 평범한 강성 ODE로 유지된다. DAE 솔버 불필요.**

  **3. 🔴 그리고 이것이 U-14를 닫는다 — 임계가 임의값이 아니라 계산량이 된다**
  ```
  K_sp = exp(−ΔG_precip / RT)
  ΔG_precip = ΔG_lattice(주기 DFT) + n·ΔG_solv(SMD)
  ```
  ⟹ **ADR-015 P-1의 "석출 판정 임계"가 자의적 컷오프가 아니라 계산된 용해도곱이 된다.**
  그리고 `ΔG_lattice`를 주기 DFT로 넣는 것이 곧 **R-07이 요구하던 격자 에너지의 도입**이다.
  ⟹ **R-07 · U-14 · U-08이 하나의 장치로 동시에 닫힌다.**
- **Decision**: 위 1·2·3을 채택한다. **S4 = 0-D 강성 ODE(음함수 적분기).** 석출·용해는
  가역 반응쌍. 석출 임계는 계산된 `K_sp`. `ΔG_lattice`는 주기 DFT로 조달.
- **🔴 Consequences — 함께 확정되는 가정과 구속**:
  - **[명시 가정] 가스 이탈**: 이탈은 1차 제거항(Henry 상수 × 물질전달계수)이고, **물질전달
    계수는 셀 기하에 의존하는 자유 파라미터**다. ⟹ **가정: ΔG_solv가 임계 이상인 모든 종에
    대해 이탈이 화학보다 빠르다.** 그러면 **상대 가스 수율 = 상대 생성 속도**가 되어 계수가
    소거된다. 🔴 **ADR-003 축(a)가 이 가정에 의존함을 명시 보고한다.**
  - **[coder 구속] 미량 species의 수치 함정**: 농도가 3자릿수 낮으면 상대 허용오차만으로는
    H2O 갈래가 **수치 잡음에 묻힌다.** ⟹ **species별 절대 허용오차(atol)를 농도 규모에 맞춰
    개별 지정**(H2O·HF는 `atol ≈ 1e-12 M` 급).
  - **[감사 지표] `H2O turnover number` 필수 보고.** **TON ≈ 1이면 재생 단계 누락 신호**
    (H2O는 촉매적으로 순환해야 한다). `[H2O]₀ = 5 / 20 / 100 ppm` 민감도 스캔 필수.
  - **H2O 취급 확정**: `[H2O]₀ ≈ 1.3 mM`(20 ppm), **고정 저수조 금지**,
    **HF는 초기종으로 넣지 않는다**(H2O에서 생성되게 둔다).
- **Revisit trigger**: 개체수 가정이 깨지는 국소 영역이 발견될 때(그 경우 하이브리드).
  가스 이탈 가정이 실험 비교에서 기각될 때 → 축(a)의 해석을 상대 수율에서 후퇴시켜야 한다.

---

## ADR-022: PM7 4번째 축의 정당화는 "더 많이 찾기"가 아니라 **"층 II의 완결성을 증명 가능하게 만들기"**

- **Status**: Accepted (U-18 확인 선행 조건)
- **Date**: 2026-08-17
- **Stage**: S2
- **Resolves**: lead 질의(2개 독립이면 되는가 / 3개 전부 필요한가)의 최종 판정
- **Proposer 판정 (§18.6)**: 추정을 **두 층**으로 나눈다.
  - **층 I (headline 수치)** — E1의 균질성으로 **3-source면 충분. PM7 불필요.**
  - 🔴 **층 II — 필요하다.** 층 II는 소스가 2개뿐이라 **종속성이 식별 불가**하고,
    §17.2에 따라 **"덜 탐색했다"만 증명 가능하고 "충분히 탐색했다"는 증명 불가**다.
    **그런데 층 II가 바로 critic D-4/D-5 영역(우리 문법 밖 화학)이고, "잘 알려지지 않은
    계"에서 가장 위험한 영역이다** — 미지 계일수록 문법 밖 화학의 비중이 크기 때문.
  > *"PM7을 4번째 축으로 추가한다. 근거는 **'더 많이 찾기 위해'가 아니라 '층 II에
  > 3-source를 만들어 완결성을 **증명 가능**하게 만들기 위해'** 다."*
- **Decision**: PM7 추가. **단 목적이 명시적이므로 폐기 조건도 명시적이다.**
  🔴 **재검토 조건: 층 II에서 PM7 단독 포획이 유의미한가.** 유의미하지 않으면 유지할 이유가 없다.
- **Consequences**: ADR-020 개정으로 ReaxFF가 배제되어 **PM7이 축 3이자 사실상 유일한
  비-xTB 반경험 축**이 됐다. ⟹ **U-18(air-gapped 반입)이 단일 실패점.**
  불가 시 층 II가 2-source로 후퇴 = **"충분히 탐색했다"를 증명할 수 없게 된다.**
- **Revisit trigger**: ~~U-18 불가 판정 시~~ (🟢 **U-18 해결 — ADR-023 참조**).
  1년 후 층 II PM7 단독 포획 유의성 재평가.

---

## ADR-023: ReaxFF 배제의 대가 정량화 — **lead의 우려는 옳았으나 전제가 틀렸다.** U-18 해결

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S2
- **Resolves**: **U-18**(🟢 해결). ReaxFF 배제의 손실 확정. X2 확장 채택
- **Context**: 사용자가 ReaxFF 배제를 지시했고, lead가 *"남은 축 2·3이 둘 다 반경험 QM이라
  Li 배위 하전종·P–F에서 함께 눈이 멀 위험이 커졌다"* 고 우려하며 X2 확장을 제안했다.

### 🟢 U-18 해결 (engineer)
**MOPAC v22+ 는 오픈소스이고 conda-forge로 배포된다.** air-gapped 반입 가능.
⟹ **단일 실패점 소멸.** coder 구속: **`MOPAC ≥ 22.0` 명시.**
- **비용**: 계당 798 k − 25 k(ReaxFF 제거) + 33 k(PM7) + 0.75 k(X2) = **807 k (+1.1%)**.
  **왕복 +0회**(PM7·X2 전부 RT-3 자율 DAG 내 병렬), **wall 상한 미접촉**(최장 13.9 h < 24 h).
  ⟹ **ADR-019의 배분·일정을 흔들지 않는다.**
- 🔴 **[상한] PM7 궤적 길이 ≤ 5 ps. replica로 보상하라.** (100 ps로 짜면 wall 166.7 h로 폭발)
- **engineer가 proposer의 PM7 선택을 독립적으로 확증**: *"DFTB+가 속도로는 낫지만
  **GFN2-xTB 자체가 DFTB 계열(tight-binding)이라 DFTB와 xTB는 PM7(NDDO 계보)보다 서로
  훨씬 가깝다.** ⟹ 속도로는 DFTB가 낫지만 **독립성으로는 PM7이 옳다.**"*

### 🔴 proposer 판정 — lead의 우려는 옳았으나 **전제가 틀렸다**

**1. 상관 우려 자체는 맞다 (§19.1)** — PM7(NDDO)과 GFN2(tight-binding)의 독립성은
**영역별로 갈린다**: **Li⁺ 배위 화학은 독립성 양호**(정전기 모형과 원소쌍 파라미터가 다름).
🔴 **음이온·라디칼 안정성, 초원자가 P–F는 강하게 상관** — *"그리고 이 영역이 우리가 가장
아쉬운 영역이다. lead의 우려가 맞다."*

**2. 🔴 그러나 ReaxFF가 그 영역을 구해주지도 못했다 (§19.2)**
> *"**ReaxFF에는 전자가 없다.** 전하 상태를 EEM/QEq 전하 균등화로만 다루고,
> **라디칼 성격·스핀·음이온 안정성을 표현할 형식적 수단이 없다.**
> ⟹ 음이온·라디칼·P–F 영역에서 **ReaxFF의 포획 확률은 p ≈ 0 이었을 것이다.**
> 그리고 **p ≈ 0 인 소스는 그 부분모집단의 CR에 아무것도 기여하지 못한다.**"*
>
> **⟹ ReaxFF 배제로 잃는 것은 "음이온/P–F 영역의 독립성"이 아니다. 그건 애초에 못 샀다.**

**⟹ lead의 완화 요구는 정당했으나, 내가 상정한 구제 수단(ReaxFF)은 그 역할을 할 수
없었다. 우려는 유지하되 귀속을 정정한다.**

**3. 실제로 잃는 것 — 두 가지, 두 번째가 크다 (§19.3)**
- **손실 A (작음)**: **비-QM 형식 축의 소멸.** 남은 세 축 중 둘이 전자구조 계산이고 축 1도
  DFT 열화학에 의존 ⟹ **"전자구조 방법이 그 종을 표현하지 못하면 아무도 못 본다"** 는
  공통 취약점이 남는다.
- 🔴 **손실 B (큼)**: **독립적인 장시간 표집 축의 소멸. X2로도, 무엇으로도 대체 불가.**

### X2 확장 — 채택. 단 **두 개 중 하나만** 대체한다
| ReaxFF 1회성 교정이 사려던 것 | X2 확장이 대체하는가 |
|---|---|
| (a) 제3의 에너지 모형으로 축2–축3 종속성 크기 측정 | ✅ **대체한다. 그리고 더 낫다** — 추론이 아니라 직접 측정이고 **반응을 하나도 안 돌린다** |
| (b) 독립적인 장시간 표집 축 | ❌ **대체 못 한다. 무엇도 대체 못 한다** (손실 B) |

**proposer의 X2 강화 3건 (스칼라를 목록으로 바꾼다)**
1. **비율만 세지 말고 *어느 종이* 실패하는지 열거하라.** 실패 종이 화학적으로 응집된
   부류를 이루면 그 종이 걸린 반응을 전부 열거해 **"위험에 처한 network의 비율"을
   정확히 보고**할 수 있다. **추정하지 않고 열거한다.**
2. **3중 검사로 확장**: (i) 최적화 수렴 (ii) 해리 여부 (iii) 전하·스핀 국재화.
   🟢 (iii)의 DFT 기준값은 **LIBE `partial_spins.mulliken`으로 비용 0에 조달**된다.
3. **X2(종 수준)와 오즈비 진단(반응 수준)을 교차 확인.** 일치하면 강한 확증, 어긋나면
   **동역학적 접근성 고유의 상관**이 따로 있다는 신호.
   ⚠ **ReaxFF 배제로 `OR(E3a)`의 준거가 사라져 이제 PM7 기반으로 계산해야 하며,
   그만큼 준거의 독립성이 약해진다. 이것도 기록할 손실이다.**

### U-18 실패 시 차선 서열 (재평가됨 — 보존)
U-18은 해결됐으나 서열은 보존한다: **① zero-shot foundation MLIP**(U-19 전제) →
**② 저비용 복합 DFT(B97-3c / PBEh-3c / HF-3c)** — *"진짜 기저 + 진짜 DFT. 반경험 공유
근사를 전부 벗어난다 — 독립성이 가장 확실"* → ③ DFTB3(**DFTB 계열이라 GFN2와 가깝다.
이전 3순위에서 하향**) → ④ GFN1/GFN-FF는 **독립 축으로 세지 마라**. 여기까지 오면
**2-source임을 선언하고 단측 결론만 보고한다.**
- **Decision**: 위를 전부 채택. **손실 B(독립 장시간 표집 축)는 완화 수단이 없으므로
  감수하고 최종 보고서에 명시한다.**
- **신규 `[UNRESOLVED]` Q15 (engineer → proposer)**: 🔴 **PM7 5 ps 궤적으로 반응 사건을
  볼 수 있는가** (고온/bias 필요한가). engineer의 wall 상한이 강제한 **형태의 과학적 대가**다.
- **Revisit trigger**: X2에서 실패 종 비율이 커서 network의 유의미한 부분이 "위험"으로
  분류될 때 → 차선 서열의 ②(저비용 복합 DFT)를 부분 도입.

### 🔴 정정 2건 (2026-08-17, engineer §R9.2·§R9.4)

**정정 1 — 독립성은 에너지 모형만이 아니라 *후보 생성기*에도 걸린다. 축 3 설계가 바뀐다.**
> engineer: *"축 2(S2-B 그래프편집 TS 탐색)와 축 3(PM7 TS 탐색)이 **같은 그래프편집 후보
> 생성기**를 쓰면 둘은 **같은 후보 집합을 보고 '어느 것이 수렴하느냐'에서만 갈린다.**
> 그러면 `S_A ∩ S_B ≈ min(|S_A|,|S_B|)` 이 되어 **N̂ ≈ max(|S_A|,|S_B|)** —
> 즉 **'우리는 전부 찾았다'는 거짓 확신을 출력한다.**"*
>
> ### **⟹ 축 3은 반드시 *확률적 후보 생성기*(반응성 MD)를 가져야 한다.
> PM7을 TS 탐색 전용으로 쓰는 구성은 비용은 싸지만 통계적으로 무가치하다.**

proposer의 §14.1(b) 경고(구조적으로 눈먼 부류는 통계에 안 나타난다)를 **후보 생성기 축으로
확장한 것**이며 옳다. **lead도 놓쳤다.**
🔴 **⟹ Q15가 부수 질문에서 축 3의 존폐 질문으로 승격한다.** PM7 반응성 MD가 필수가 됐으므로
**"5 ps 궤적으로 반응 사건을 볼 수 있는가"** 에 축 3 전체가 걸린다. 못 보면 2-source 후퇴.
※ **MOPAC은 범용 열욕 MD 엔진이 아니다** — ASE/pysisyphus 구동 + 스텝당 프로세스 오버헤드로
**xTB 대비 10~50배** 느리다. 5 ps 상한의 출처가 이것이다.

**정정 2 — X2는 "공유 맹점의 상한"이 아니다. 낙관 편향이 있다.**
본 ADR 본문에서 X2를 *"직접적 상한"* 으로 적었으나 **틀렸다. 정정한다.**
> engineer: *"비교는 **DFT를 돌린 5,000종에서만** 가능하고 그 5,000종은 **flux 상위로 선별된
> 집합**이다. ⇒ X2가 재는 것은 '공유 맹점의 상한'이 아니라 **'우리가 이미 들여다본 영역에서의
> 불일치율'** 이다. **xTB가 구조적으로 눈먼 영역은 애초에 flux 상위에 오르지 못했을 수
> 있으므로 X2는 낙관 방향으로 편향된다.**"*

**proposer의 §14.1(b) 자기경고와 정확히 같은 종류의 편향**이다 — 표본추출기가 못 보는 것은
표본에도 안 나타난다. 🔴 **보고 시 "상한"이라는 표현을 쓰지 않는다.** 편향 완화안
(불일치 종을 DFT 표집 기준에 의도적으로 포함 / 저비용 무작위 표본으로 편향 크기 측정)을
proposer에게 물었고, 어느 쪽도 안 되면 **"낙관 편향된 하한"으로만 보고**한다.
※ 증분 비용은 proposer 견적대로 ≈0 (750 core-h = 봉투의 0.013%). 비용은 쟁점이 아니다.

---

## ADR-024: Q15 판정 — PM7 궤적 **10 ps** 승인. 축 3 실행 규약 (A)(B)(C)는 **필수 조건**

- **Status**: Accepted (wall 산술은 engineer 검산 대기)
- **Date**: 2026-08-17
- **Stage**: S2 (축 3)
- **Resolves**: **Q15**
- **Context**: engineer가 wall 상한으로 PM7 궤적을 5 ps로 제한했고(*"형태의 과학적 대가"*),
  §R9.2에서 **축 3은 반드시 확률적 후보 생성기(반응성 MD)를 가져야 한다**고 판정하면서
  Q15가 **축 3의 존폐 질문으로 승격**했다.
- **Decision — PM7 궤적 상한을 5 ps → 10 ps로 올린다**
  proposer 근거(§20.4)는 **barrier 도달범위가 아니라 왕복**이다:
  > *"고전 力場 스냅샷을 PM7으로 넘기면 力場 불일치로 초기 과도구간이 생겨 **처음 1~2 ps는
  > 재평형에 소모**된다. `5 ps → 실효 창 3~4 ps` / `10 ps → 실효 창 8~9 ps`.
  > **실효 창 3~4 ps에서는 2단계 연쇄를 한 궤적 안에서 볼 수 없다** ⟹ 반복 시딩 회차가
  > 많아진다. ⟹ **10 ps는 계산 +1.1%를 지불하고 왕복을 산다. 우리의 희소 통화는 왕복이다.**"*

  **engineer 자신의 숫자로 검산됨**: `100 ps → wall 166.7 h` ⟹ `1 ps ≈ 1.67 h` ⟹
  **10 ps = wall 16.7 h < 24 h 상한. 여유 7 h.** ⟹ **상한 위반 없음, ADR-019 불변 전망.**
  ※ 후퇴안(proposer 제시): 5 ps 고수 시 **반복 시딩 3 → 5회차**로 보상하되 **왕복이 는다.**
    *"이 교환을 engineer가 선택하면 된다 — 어느 쪽이든 과학은 성립한다."*
- **🔴 축 3 실행 규약 — 셋 다 필수. 하나라도 빠지면 축 3의 포획 확률이 급락해
  3-source CR이 사실상 2-source로 퇴화한다**
  - **(A)** replica 초기조건을 **장시간 고전 MD의 탈상관 스냅샷**에서 추출.
    🟢 **λ_out용 ns급 고전 궤적이 이미 있다 — 비용 0.** 사전조직화는 고전 MD가 공급하고
    PM7은 빠른 반응만 담당한다. (proposer의 C2 "느린 사전조직화" 구제책)
  - **(B)** 반복 시딩 **≥3 회차** (C1 구제)
  - **(C)** 🔴 **온도 사다리 600 / 1000 / 1500 K 를 replica에 배분하고 합집합을 취한다.**
- **🔴 (C)의 근거 — 고온의 대가는 속도가 아니라 *메커니즘 왜곡*이다**
  `ΔG‡ = ΔH‡ − TΔS‡` ⟹ **해리성(생성물 분자 수가 느는) 단계가 고온에서 구조적으로 유리**해진다.
  | T | ΔS‡ = +50 J/mol/K 해리 단계의 유효 안정화 |
  |---|---|
  | 300 K | 0.16 eV |
  | 1000 K | **0.52 eV** |
  | 1500 K | **0.78 eV** |
  > **1500 K에서 해리 경로는 회합 경로 대비 0.78 eV의 가짜 우위를 얻는다 — 경로 순서를
  > 통째로 뒤집을 수 있는 크기다.** ⟹ **단일 고온은 해리·파편화 쪽으로 체계 편향되고
  > 회합 경로를 놓친다.** 단순 "속도 재가중"이 아니다.

  ※ **분기비 자체는 왜곡되지 않는다** — 새 아키텍처에서 PM7의 역할은 **발견 전용**이고
    분기비는 surrogate(ADR-018) + microkinetics(ADR-021)가 낸다. **고온은 "무엇을 찾는가"를
    편향시키지 "계산된 분기비"를 편향시키지 않는다. 다만 못 찾은 반응은 분기비에 못 들어간다.**
  ※ **추가 권고**: 가능하면 온도보다 **밀도/압축(nanoreactor식)** 선호 — 압축은 **이분자 충돌
    빈도**만 올리고 barrier를 지수적으로 재가중하지 않아 **분기 왜곡이 훨씬 작다.**
    단분자 반응엔 무효 ⟹ **조합: 중간 온도 + 밀도 부스트.** engineer 견적 요청함.
- **Consequences**:
  - **손실 B(독립 장시간 표집 축)의 성격이 정밀해졌다.** proposer §20.3: 짧은 궤적 다수가
    못 보는 세 부류 중 **C1(희귀 사건)·C2(느린 사전조직화)는 구제 가능**(반복 시딩 / 고전 MD
    스냅샷 시딩)하나, 🔴 **C3(느린 집단 과정)는 손실 B와 *같은 것*이다. 새 손실이 아니라
    손실 B의 연속성 성분을 심화시킨다.**
    ⟹ **최종 보고서 한계 문장에 추가**: *"응집·핵생성·다단 사슬성장은 탐색되지 않았다."*
  - **CR 이질성 공변량에 `발견 온도` 추가** (기존: ΔG_rxn, 변하는 결합 수, 분자도, 종 크기).
    *"1500 K에서만 나왔다 = 엔트로피 구동 의심"* 진단이 따라온다. **coder 구속.**
  - **U-21 신설**: 고전 MD → PM7 핸드오프의 **재평형 시간 실측**(1~2 ps는 `[ESTIMATE]`).
    **파일럿 궤적 1개의 온도·에너지 추이로 즉시 측정 가능** ⟹ RT-2 탑재 검토 중.
    **이 값이 실효 반응 창을 정하므로 궤적 길이 결정의 근거가 된다.**
- **Revisit trigger**: U-21 실측 재평형 시간이 2 ps를 크게 넘을 때(실효 창이 더 줄어든다).

### 🔴 개정 (2026-08-17, proposer §21.2·§21.3) — **10 ps 승인을 철회한다. 진짜 레버는 상자 크기였다**

**proposer가 자기 요청을 철회했다.** 발견 도달범위는 `N·t`의 함수이고, **PM7 SCF 비용은
원자수에 초선형(≈N^2.5~N^3)** 이므로 **상자를 줄이고 replica를 늘리는 것이 같은 비용으로
훨씬 많은 `N·t`를 산다.**
```
300 원자 → 100 원자 : 비용 15~27배 감소 ⟹ 같은 예산에 replica ×20
replica ×20 이 사는 barrier 도달범위 = k_BT·ln(20) = +0.26 eV  (1000 K)
비교: 5 ps → 10 ps 가 사는 것            = +0.06 eV
                                        ⟹ 상자 축소가 4배 이상 효율적
```
> *"**발견 목적에는 벌크 수렴 용매화가 필요 없다. 필요한 것은 반응성 조우다.**
> 반응물 2~4분자 + 1차 용매껍질 ≈ **60~120 원자**면 화학이 보인다."*

**개정 확정 구성**
1. **궤적 길이 = 5 ps 유지** (10 ps 철회)
2. 🔴 **PM7 반응성 MD 상자 ~100 원자로 축소, 남는 예산 전부를 replica로**
3. 🔴 **PM7 사전 이완(pre-relax)을 필수 단계로** — 각 고전 MD 스냅샷을 PM7으로 짧게 이완시킨
   뒤 동역학 시작 ⟹ **τ_eq ~1.5 → ~0.3 ps, 실효 효율 η 0.70 → 0.94.**
   **재평형 낭비를 계산이 아니라 절차로 없앤다.** 10 ps가 사려던 것의 대부분을 비용 0에 얻는다.
4. **U-21이 게이트 측정으로 승격** — `t ≥ 3τ_eq` 를 만족해야 5 ps가 정당화된다. 파일럿 1궤적.

**잃는 것 (proposer 명시)**: 100원자 상자는 **장거리 용매화·이온 대기를 못 담아** 하전종의
상대 안정성이 왜곡될 수 있다. **그러나 축 3의 역할은 발견이지 에너지가 아니고, 발견된 후보의
에너지는 하류 DFT/surrogate가 매긴다 ⟹ 허용 가능.**
🔴 **단 맹점 목록에 "이온 대기가 필요한 반응(다중 이온 협동)은 축 3이 구조적으로 못 본다" 추가.**

### 🔴 X2 명명 정정 — "상한"을 폐기한다 (proposer §21.4·§21.6)
proposer 판정: engineer의 X2 편향 진단은 **"결론이 맞고 메커니즘이 틀렸다."**
- **명명 확정**: ADR-023의 ~~"직접적 상한"~~ → **"pool 내 불편 추정치 / 전역 하한"**
- **X2 표집을 층화 표집으로 재설계** — lead의 두 제안(불일치 종 의도적 포함 / 무작위 표본)을
  통합. 🔴 **층 B(균등 무작위 300~500종)를 불편성 앵커로 필수 포함.**
- **X2 금지 규칙 [coder 구속]**: **DFT 대상 선정에 xTB를 쓰지 말 것** (B2 편향 차단).
- **X2 상시 규칙**: pool 밖에서 새로 발견된 종을 전부 비교집합에 추가 (B1 편향 완화).

---

## ADR-025: U-18 **종결**. "AIMD 배제"의 범위 = **(b) 길고 직렬적인 생산 AIMD**. RT-2 프로브를 처리량으로 재정의

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: S2 / Infra
- **Resolves**: **U-18(종결)**, 사용자 지시 "AIMD 최대 배제"의 범위
- **1. 🟢 U-18 종결 — 성립 조건이 아니었다 [MEASURED, engineer 웹 확인]**
  lead가 "핵심"으로 지목했던 조건(*"라이선스 키가 네트워크 인증을 요구하는가"*)에 대한 답:
  **요구하지 않는다.**
  | 항목 | 결과 |
  |---|---|
  | 라이선스 키 | **불필요** (MOPAC2016 → OpenMOPAC 재배포 시 키 폐지) |
  | 비밀번호 활성화 | **불필요** |
  | 온라인 인증 | **없음** |
  | 라이선스 | v22.x LGPL → **v23+ Apache 2.0** |
  | 오프라인 설치 | tarball → 로컬 설치, **키 없이 동작** |
  ⟹ **단일 실패점 아님. air-gapped 반입에 장애 없음.** coder 구속 `MOPAC ≥ 22.0` 유지.

- **2. ✅ 사용자 확정 — "AIMD 배제"는 (b)를 의미한다**
  engineer가 §R10.5에서 **자의적 해석을 거부하고 범위를 물었다**:
  > *"**나는 이것을 '지시 위반'으로 미리 배제하지 않겠다. 동시에 몰래 집어넣지도 않겠다.**
  > lead가 사용자에게 물어야 할 질문: AIMD 배제는 (a) DFT 동역학 자체를 쓰지 말라는 뜻인가,
  > (b) 길고 직렬적이며 재제출이 많은 생산 AIMD를 쓰지 말라는 뜻인가?"*

  **사용자 답변: (b).**

  **근거의 정합성**: 지시의 명시된 사유는 *"너무 비싸서 현실적이지 않아"* 였고, **그 비용의
  정체를 규명한 것이 engineer의 §R4.2였다**(궤적당 6.9일, 재제출 56~112회, self-chaining
  단일실패점). 같은 분석이 **짧은 궤적 대량 병렬 앙상블에는 그 근거가 적용되지 않음**을 보인다:
  | | 지시가 겨냥한 대상 (구 생산 AIMD) | 차선책 (DFT 확률적 MD) |
  |---|---|---|
  | 궤적 길이 | 30 ps | **3 ps** |
  | 궤적당 wall | **166 h (6.9일)** | **16.6 h** |
  | 재제출 | **7~14회 (총 56~112)** | **0회** |
  | self-chaining SPOF | 🔴 존폐 조건 | **없음** |
  | 왕복 | +2 | **0** |
  ⟹ **물리 엔진은 같지만 비용 프로파일이 정반대다.**
  ⟹ **축 3 차선책에 `DFT 확률적 MD (3 ps × 30 궤적, 32 k core-h, 왕복 +0)` 가 복귀한다.**
  zero-shot MLIP의 GPU 왕복 의존과 U-19 위험을 지지 않아도 된다.
  ⚠ **단 차선책 설계에 지금 투자하지 않는다.** 발동 조건은 RT-2 프로브 결과뿐이다.

- **3. 🔴 RT-2 프로브를 "가용성"에서 "처리량"으로 재정의 (engineer §R10.2)**
  > *"**진짜 미지수는 'MOPAC이 있는가'가 아니라 '몇 초/step인가'다. 그게 축 3의 과학적
  > 유효성을 정한다.**"*

  MOPAC은 반입만 하면 되므로 존재 여부는 미지수가 아니다. **s/step이 replica 수 → barrier
  도달범위 → 포획 확률을 정한다.**
  🔴 **U-21(τ_eq)도 같은 프로브에 얹는다** — `t ≥ 3τ_eq` 게이트(ADR-024 개정)와 s/step이
  **같은 파일럿 궤적 1개에서 함께 나온다.**

- **4. 🟢 X2 확장이 ReaxFF 1회성 교정을 167배 싸게 대체 (25,000 → 150 core-h)**
  비용이 쟁점이 아닌 수준이므로 **층화 표집(층 B = 균등 무작위 300~500종, 불편성 앵커)을
  전부 포함**한다.

- **Consequences**: **§R8/ADR-019 확정본 유지** (계당 806 k, −1.0%). 일정 불변.
  🔴 **방법론 세부의 추가 정밀화는 여기서 멈춘다** — `s/step`·`τ_eq`가 `[ESTIMATE]`인 상태에서
  더 다듬는 것은 수확체감이다. **proposer는 U-05 정식 설계로, engineer는 RT-2 프로브 사양으로
  전환한다.** U-05가 RT-3(S2 전체 자율 DAG)의 스펙이므로 임계 경로에 있다.
- **Revisit trigger**: RT-2에서 PM7 처리량이 목표 미달일 때 → 차선 서열 발동
  (사용자 (b) 답변으로 **DFT 확률적 MD가 유효 후보**).

---

## ADR-026: 🔴 **LIBE 재사용을 포기한다.** `c = 29~41%` 실측 — 그러나 결정적 이유는 비용이 아니라 **레벨 이음매**

- **Status**: Accepted. **ADR-011을 Proposed → 종결(기각된 (i)안)로 대체**
- **Date**: 2026-08-17
- **Stage**: S2 (S1 파급)
- **Resolves**: **ADR-011의 `c` 미측정**, **쟁점 5(S1 level 상향)**
- ⚠ **처리 지연 기록**: proposer가 §10에서 `c`를 실측해 뒀으나 **lead가 며칠 분량의 라운드
  동안 이를 처리하지 않았다.** coder의 L3(세션 다이제스트)를 처음 실행했을 때
  *"ADR-011 — c가 아직 측정되지 않았다"* 가 **미해결로 표시되어 발견됐다.**
  **자동화가 배정 첫날 lead의 누락을 잡아낸 사례로 남긴다.**

### 1. 🔴 실측: `c = 29~41%` — c* = 75%를 크게 밑돈다
proposer가 S2-A fragment-recombine 레시피를 ADR-001 principal molecule에 **실제로 구현해**
pool을 생성하고 LIBE에 `(formula, charge, spin)` 수준으로 존재하는 비율을 셌다
(`data/libe/gen_pool.py`, 산출 `coverage*.json`).
- **생성 정책 3종 모두에서 c가 낮다** ⟹ 결손은 생성기 artifact가 아니다.
  (naive → valence-aware 전환에도 39.8 → 40.5%로 **거의 안 움직였다.**)
- **결손 구조**: **P 화학이 지배적**(전체 결손의 40.8%. P를 빼도 c = 52.4%로 여전히 미달).
  **원자수 의존이 가파르다** — ≤2원자 100% → 10원자 51% → 22원자 14%.
  **큰 재조합 생성물이 결손의 본체.** charge 의존은 없다(이온·라디칼 편향 문제가 아님).

### 2. 🔴 가장 중요한 발견 — **pool은 자연의 성질이 아니라 정책의 함수다**
역방향 진단: **우리 pool이 LIBE를 재현하는 비율 = 26.8%.**
> *"**두 집합은 서로를 포함하지 않는다.** 내 pool이 LIBE의 상위집합이었다면 'LIBE가
> 불완전하다'고, 부분집합이었다면 '내 레시피가 과하다'고 말할 수 있다. **둘 다 아니다.**
> ⟹ **S2-A의 species pool은 자연의 성질이 아니라 재조합 정책의 함수다.
> 따라서 `c`도 물리량이 아니라 정책 의존량이다.**"*

LIBE의 "selective recombination" 선택 규칙은 **논문 본문 유료화로 확인 불가**(`[UNRESOLVED]`).
> *"그 규칙을 모르는 한 `c`를 올리는 것은 우리 정책을 LIBE에 맞춰 역설계하는 일이 되고,
> 그것은 **과학이 아니라 데이터셋 맞추기다. 나는 반대한다.**"*

### 3. 🔴 engineer 결정규칙에 대한 방법론적 이의 — **결정적 이유는 비용이 아니다**
> *"engineer의 규칙은 (i)과 (ii)가 **과학적으로 등가일 때만** 성립한다. 등가가 아니다.
> (i)은 고수준 열화학을, (ii)는 값싼 레벨을 준다. **비용만 비교해 c\*를 뽑는 것은 서로 다른
> 물건의 가격을 비교하는 것이다.**"*

🔴 **그리고 (i)에는 계상되지 않은 과학적 비용이 있다 — 레벨 이음매(seam):**
c 비율을 LIBE에서, 나머지를 자체 계산에서 가져오면 **두 레벨에 걸친 반응이 레벨 간 계통
차이를 가짜 ΔG로 물려받는다.** 이분자 반응 4종이 모두 같은 출처일 확률은 `c⁴+(1−c)⁴`:
> **c = 0.40 ⟹ 0.156 ⟹ 반응의 약 84%가 레벨 이음매를 가로지른다.**

레벨 간 계통 차이가 종당 0.1 eV여도 반응 ΔG에 **0.1~0.2 eV의 무작위 부호 오차**가 들어가고,
이는 **flux 순위와 DRC 선별(ADR-015 P-1~P-5)을 직접 파괴한다.**
⟹ **비용 문제가 아니라 파이프라인 무효화 위험이다.**

### 4. Decision — **(iii) 채택**
| 안 | 내용 | core-h | 판정 |
|---|---|---|---|
| (i) | LIBE 재사용 + 신규분을 LIBE 레벨로 | 306 k | 🔴 이음매 84% |
| (ii) | 전 pool을 단일 값싼 레벨로 자체 계산 | 129 k | ✅ 이음매 0 |
| **(iii)** | **(ii) + LIBE 겹침을 교차레벨 교정·외부검증에 사용** | **129 k + α** | ✅ **채택** |

**전 pool을 하나의 레벨로 일관되게 자체 계산하고, LIBE와 겹치는 867 상태(SEI pool 포함 시
1,345)를 "무료 고수준 참조값"으로 쓴다. ⟹ LIBE를 생산값의 출처가 아니라 외부 벤치마크로
강등한다.**
> *"(iii)이 (i)보다 나은 이유는 **비용이 아니라 과학이다.** ① 이음매 0 ⟹ flux/DRC 순위가
> 신뢰 가능해진다. ② **867종을 두 레벨로 갖게 된다** — §1.7 B1(오차 상쇄 검증)을 5종이
> 아니라 **867종으로** 할 수 있다. 이런 규모의 교차레벨 벤치마크는 흔치 않다. ③ 값이 싸다."*

### 5. ⟹ **쟁점 5(S1 level 상향) 철회** (proposer 자진)
> *"나는 'LIBE 호환성 때문에 S1이 ωB97X-V/def2-TZVPPD여야 한다'고 주장했다. **LIBE를
> 생산값으로 쓰지 않기로 한 이상 그 논거는 소멸한다.** 남는 제약은 **S1과 S2가 서로 같은
> 레벨이어야 한다**는 것뿐이며(같은 kMC에 들어가므로), 그 레벨은 **순수하게 과학으로**
> 정하면 된다. **내가 만든 논거였으므로 내가 거둔다.**"*
- ⟹ **ADR-010 Decision 4의 전제(LIBE 정합성)가 사라졌다.** level 선택은 이제
  **S1↔S2 내부 일관성**만 요구하며, 절대 수준은 과학적 판단 사항.

### 6. [실험 X1] 이 결정을 확정하는 측정 — 거의 공짜
> **LIBE와 겹치는 867 상태를 값싼 레벨로 계산해 LIBE 고수준 값과 대조, 반응 ΔG 잔차 σ 측정**
> (종별 offset 회귀 후 잔차).
> - **σ < 0.1 eV** → 값싼 레벨로 충분. (iii) 확정.
> - **σ > 0.2 eV** → 값싼 레벨이 flux 순위를 파괴한다 ⟹ 전 pool 고수준으로.
> - 비용 `867 × 60 ≈ 52 k` 이나 **이 867종은 (ii)에서 어차피 계산할 pool의 일부** ⟹ 증분 ≈ 0.
- **Consequences**: engineer의 §11.1(c) 손익분기 규칙은 **비용 비교로는 유효하나 과학적
  등가성 가정이 깨져 단독 판정 근거가 될 수 없다.** engineer에게 (ii)/(iii) 재견적 지시.
  **X2 진단(ADR-023)과 X1이 같은 배치에서 돈다.**
- **Revisit trigger**: X1에서 σ > 0.2 eV일 때. LIBE의 재조합 선택 규칙이 공개되어
  정책 비교가 가능해질 때.

---

## ADR-027: **U-05 확정** — 발견 원장과 작업 network를 분리한다. 안 하면 완결성 추정과 가지치기가 서로를 파괴한다

- **Status**: Accepted. **RT-3(S2 자율 DAG)의 스펙**
- **Date**: 2026-08-17
- **Stage**: S2/S3
- **Resolves**: **U-05**(정식 설계), **U-05-a/b/d**, **U-13**(정지 기준), critic **D-2/D-4/D-5** 처분
- **Context**: ADR-015(P-1~P-5) · ADR-018(surrogate) · ADR-021(K_sp) 확정 이후 남은
  **마지막 큰 설계 공백.** 임계 경로(RT-3 스펙).

### 1. 🔴 뼈대 — **발견 원장(Discovery Ledger) ↔ 작업 network 분리**
```
발견 원장   append-only. 절대 가지치기하지 않는다.
            기록: (species|reaction, 발견 엔진, 회차, 발견 온도, 시각, 초기조건 해시)
            ⟹ Ĉ / Chao1 / capture–recapture 는 오직 이 원장에서만 계산된다
     │ 스냅샷(해시 고정)
     ▼
작업 network  L0~L3로 공격적으로 가지친다. microkinetics·DRC·S3 선별은 여기서만.
```
> 🔴 *"가지친 뒤에 Ĉ를 계산하면 **f₁·f₂가 오염되어 완결성 수치가 통째로 무의미해진다.**
> **이 분리 없이 완결성 추정과 가지치기를 같은 자료구조 위에서 돌리면 두 기능이 서로를
> 파괴한다.**"* 원장은 메타데이터라 저장 비용이 사실상 없다.

**두 시계(two-clock) 설계** — 시계 A(발견, Ĉ 수렴까지, 원장에만) / 시계 B(S3 wave, 스냅샷
위에서). 🟢 **결합은 SG-3이 자동으로 한다**: 발견이 아직 고flux 반응을 추가 중이면 순위가
흔들려 ρ가 떨어지고 **S3 집행이 스스로 멈춘다. 두 시계를 손으로 동기화할 필요가 없다.**

### 2. 정지 기준(U-13) — 🔴 **층별로 따로 계산한다**
`Ĉ ≥ 0.95 AND (Chao1 − S_obs)/S_obs < 0.05` **[잠정 — 파일럿 축적곡선으로 교체]**
> 🔴 *"**층을 합쳐서 계산하면 안 된다.** 층 I(E1 문법 안)은 전수 열거라 빨리 수렴하고,
> 합산하면 **층 I의 수렴이 층 II의 미탐색을 가린다.**
> 층 II가 기준에 못 미치면 정지하지 말고, 시간이 다하면 **'under-explored'로 보고한다 —
> 수치를 만들어내지 않는다.**"*

### 3. 가지치기 사다리 (작업 network 전용)
**L0** 보존칙·변하는 결합 ≤4·금지 원자가(거의 무손실) → **L1** 단일 단계 `ΔG > +1.5 eV` 제거
(**이보다 조이지 않는다**) → **L2** flux 하위 절단 → **L3** **P-1~P-3 보호 대상은 flux 무관
무조건 보존, L2에 우선.**
🔴 **금지**: ΔG cutoff 단독, depth 단독. 🔴 **L1은 가지치기이지 선별이 아니다 — S3 선별은
DRC가 한다. 섞지 마라.**

### 4. U-05-a — 균일 ±0.3 eV 폐기, **출처별 이질 섭동폭**
| `barrier_source` | σ_r |
|---|---|
| `dft_ts` | ±0.05 eV |
| `bep_family`(A1~A3 충족) | **해당 계열의 BEP 실측 잔차 그대로** |
| `analogy_weak`(앵커 <3) | ±0.3 eV |
| `default`(계열 없음) | ±0.5 eV |
🟢 *"이질 폭이 **잘 모르는 반응 쪽으로 예산을 자동으로 몰아준다** = VoI의 자연스러운 구현."*

### 5. U-05-b — 계열 정의를 **논쟁이 아니라 측정으로** 고른다
키 후보 `F0 → F1 → **F2+q** → F3`. **선택 규준: "구성원 ≥3건 AND BEP 잔차 σ < 0.1 eV"를
만족하는 계열이 덮는 반응 수를 최대화하는 수준.** 즉 **§9.2의 A2가 곧 계열 정의의 합격 기준.**
기본 **F2+q**로 시작, 앵커가 마르면 F1로 내린다.
🔴 **U-12-c 경보 유지: 계열 수 >100이면 계층모형이 전역 평균으로 붕괴한다.
첫 DFT TS 배치에서 계열 분포 실측 즉시 확인.**

### 6. U-05-d — **L2 flux 임계는 지금 정하지 않는다**
**작업 network 엣지 수가 500~700이 되도록 역산**(S3 상한 300 + rate-rule 처리분).
*"network 크기가 실측되기 전에는 정할 수 없다."* — ADR-025의 정밀화 중단 원칙과 정합.

### 7. 🔴 critic 맹점 최종 처분
| # | 처분 | 내용 |
|---|---|---|
| **D-2** 응축상/격자 반응물 | 🔴 **문법 확장 — 감수 불가** | **상 태그 `X(soln)\|X(s)\|X(g)` + 석출 반응 `n·X(soln) ⇌ X(s)`.** 격자에너지 대상은 **LiF·Li2CO3·Li2O·LiOH·LEDC 5~6종으로 유계.** ADR-021대로 큰 속도상수 가역쌍으로 완화. 🟢 **HF+Li2CO3(s) 촉매 순환이 이걸로 표현 가능해진다 — ADR-003 축(b)가 여기 걸려 있어 감수 불가** |
| **D-4** 사슬성장/중합 | **별도 처리 — 집중(lumped) 채널** | 성장 첫 2~3 단계 barrier로 전파 속도상수를 정하고 **모멘트법**으로 저차 모멘트만 추적. **정직한 손실: 사슬 길이를 분해하지 못하고 "중합체 sink로 가는 질량 flux"만 추적.** XPS에서 "유기 중합체" 한 덩어리로 보고 |
| **D-5** 3체 이상 concerted | **부분 완화 + 잔여 감수** | **다성분 착물(`Li⁺(EC)₃(PF6⁻)` 등)을 pool species로 넉넉히 포함**시키면 그 "안"의 3체 협동이 **착물의 단분자 반응**으로 표현된다(열거 문법 안). 남는 진짜 삼분자 충돌은 농도 3승 억제라 **감수 + 최종 한계 목록 기재** |
| **D-1**(대조군) | — | LEDC·ROCO2Li계·PF6⁻ 단계분해는 **E1 문법 안 ⟹ E1의 필수 통과 하한선. 못 찾으면 엔진 고장이다** |
- **Consequences**:
  - **coder 구속 신설**: 원장/작업 network **분리 자료구조**, 원장 append-only 강제,
    스냅샷 해시 고정, 층별 Ĉ 계산, 출처별 σ_r 테이블, 상 태그 3종.
  - **U-05-d(flux 임계)와 U-13(정지 임계)은 실측 후 확정** — 지금 숫자를 만들지 않는다.
  - D-2 처분으로 **격자에너지 계산 5~6종이 신규 작업**으로 들어온다(유계, 주기 DFT).
    engineer 견적 필요.
- **Revisit trigger**: 계열 수가 100을 넘을 때(계층모형 붕괴 → F1로 하향).
  층 II가 정지 기준에 끝내 도달하지 못할 때(→ "under-explored" 보고, 수치 조작 금지).

---

## ADR-028: (iii) 재견적 — **계층화 폐기. 예산 봉투의 30%.** 레벨 선택이 더 이상 예산 문제가 아니다

- **Status**: Accepted. **ADR-011의 N_DFT 계층화를 폐기**, **ADR-023의 X2 비용 기술 정정**
- **Date**: 2026-08-17
- **Stage**: S2 (S1 파급)
- **Resolves**: ADR-026 이후 재견적. **ADR-011 종결**
- **Engineer 판정 (§R13~§R14)**:

  **1. 🟢 c* 규칙에 대한 proposer의 이의 전면 수용 — 자기 유도의 숨은 가정을 인정**
  > *"**맞다. 내 유도는 두 선택지가 같은 물건을 낸다고 암묵 가정했고, 그 가정을 명시하지
  > 않았다. 명시했다면 proposer가 더 일찍 반박할 수 있었다.**
  > 가격표를 붙이는 것이 내 일이지만, **무엇의 가격인지를 흐리면 그 가격표는 해롭다.**"*

  **2. 🔴 이음매 산술 검증 — 그리고 c가 최악 구간 바로 옆이다**
  | c | 동일출처 확률 `c⁴+(1−c)⁴` | 이음매 가로지름 |
  |---|---|---|
  | 0.29 | 0.261 | 73.9% |
  | **0.40 (실측)** | 0.155 | **84.5%** |
  | 0.50 | 0.125 | **87.5% (최대)** |
  > **이음매 비율은 c=0.5에서 최대다.** c가 매우 높거나(≈1) 낮으면(≈0) 이음매가 적은데
  > **중간값이 가장 나쁘다.** 실측 c=29~41%는 **최악 구간 바로 옆.**
  > ⟹ **"c가 낮아서 (i)이 비싸다"보다 "c가 중간이라 (i)이 과학적으로 최악이다"가 더 강한
  > 논거다.** 결론이 비용·과학 양쪽에서 **과잉결정(over-determined)** 됐다.

  🔴 **일반 원리 (재사용 가능 — 기록해 둔다)**:
  > **부분 재사용(partial reuse)은 항상 이음매를 만든다. 외부 데이터셋 재사용을 검토할
  > 때마다 `1 − cⁿ − (1−c)ⁿ` 을 먼저 계산하라** (n = 반응 참여 종 수).
  > `c*` 규칙은 폐기하지 않되 **단독 판정 근거가 아니라 "등가성이 성립하는가?"를 먼저
  > 묻게 하는 트리거**로 격하한다.

  **3. 🔴 계층화 폐기 — 실측 pool이 추정의 43%였다**
  실측 `N_pool = 2,142` vs engineer 추정 5,000. ⟹ **전 pool을 값싼 레벨로 계산하는 것이
  ADR-011의 계층화(N_DFT 2,000/2,500)보다 싸고(0.40×) 과학적으로도 깨끗하다.**
  ⟹ **ADR-011의 Tier-A~D 계층화를 폐기한다.** (xTB로 DFT 대상을 고르는 단계 자체가 사라지므로
  **ADR-026의 "X2 DFT 대상 선정에 xTB 금지" 구속도 자동 충족**된다.)

  **4. X2 비용 — 두 번 정정된 끝에 0이 된다**
  | 시점 | 값 | 사유 |
  |---|---|---|
  | ADR-023 기록 | 150 core-h | 🔴 **engineer 자기 오류** — 층 B는 flux 집합 밖 종을 다수 포함해 DFT가 전부 신규 |
  | §R12.4 정정 | 24 k core-h | 400종 × 60 |
  | **§R14.4 최종** | **≈ 0** | **전 pool을 계산하므로 "flux 집합 밖"이라는 개념 자체가 사라진다** |
  ⟹ **ADR-023의 "167배 싸게 대체"라는 서술을 폐기한다.** 정확한 서술은
  **"거의 같은 값에 더 나은 통계적 성질을 산다"**(§R13.0) → 최종적으로는 **전 pool 계산에 흡수.**

  **5. 🟢 예산 — 계당 867 k → 526 k (−39%). 총 2.43 M → 1.75 M = 봉투의 30%**
  🔴 **⟹ 레벨 선택이 더 이상 예산 문제가 아니다. 고수준 전 pool도 봉투의 50%로 들어온다.**
- **Decision**: 1~5 전부 채택. **ADR-011 종결**(계층화 폐기, `c*` 규칙은 트리거로 격하).
  ADR-023의 X2 비용 서술 정정.
- **🔴 Consequences — proposer에게 열린 결정 하나**:
  ADR-026에서 *"남는 제약은 S1과 S2가 서로 같은 레벨이어야 한다는 것뿐이며, 그 레벨은
  순수하게 과학으로 정하면 된다"* 고 했는데, **이제 예산이 그 판단을 전혀 구속하지 않는다.**
  ⟹ **S1·S2 공통 레벨 선택을 과학적 근거만으로 확정하라** (신규 `U-22`).
  선택지는 값싼 레벨(예: ωB97X-D/def2-TZVP)부터 고수준(ωB97X-V/def2-TZVPPD)까지 전부 열려 있다.
  **X1(867종 교차레벨 잔차 σ)이 그 판단의 실측 입력이다.**
- **Revisit trigger**: RT-1 파일럿 단가가 도착해 `[ESTIMATE]`가 `[MEASURED]`로 바뀔 때
  (engineer의 명시적 재개 조건 1). 또는 pool 실측값이 다시 크게 바뀔 때(재개 조건 2).

---

## ADR-029: **U-22 확정** — S1·S2 공통 레벨은 고수준 기본값. X1에 **영대조군**을 넣어 "레벨 손실"과 "프로토콜 결함"을 분리한다

- **Status**: Accepted (기본값 확정 + X1 분기 규칙). **ADR-010 Decision 4를 종속 처리**
- **Date**: 2026-08-17
- **Stage**: S1 / S2
- **Resolves**: **U-22**, **ADR-010 Decision 4**
- **Context**: ADR-028로 예산이 레벨 선택을 전혀 구속하지 않게 됐다(고수준 전 pool도 봉투의
  50%). lead가 *"비용을 근거로 쓰지 마라. 이번에는 정말로 무관하다"* 고 지시.
- **Decision — 기본값 `ωB97X-V/def2-TZVPPD/SMD`, S1·S2 공통**
  proposer 근거는 **셋 다 물리적이며 비용이 아니다**:
  1. **우리 화학이 음이온·라디칼 음이온이다** — **diffuse가 물리적으로 필요하다.**
  2. **S1의 본체가 전자 부착**이다 — **전자친화도에 diffuse는 선택이 아니다.**
  3. 🔴 **U-05-b의 계열 합격 기준이 σ < 0.1 eV**인데, **레벨 잡음이 그 예산의 상당 부분을
     먹으면 계열 정의 자체가 불안정해진다.**
     > *"**정확도 예산은 계열 정의에 써야지 레벨 절감에 쓸 게 아니다.**"*
  - **내려갈 유일한 조건은 SCF 강건성**이며, 그 경우에도 **`def2-TZVPD`까지만. `def2-TZVP`로는
    가지 않는다.** 프레이밍: **"구멍 대신 잡음을 선택한다."**

- **🔴 X1 재설계 — 영대조군(null control) 도입이 핵심이다**
  `σ_eff = σ(L) ⊖ σ(L_A)` — **영대조군을 뺀 순 손실**로 판정한다.
  (L_A = 우리 프로토콜로 **LIBE와 같은 레벨**을 재현한 대조군.)
  ⟹ **"값싼 레벨이 나쁘다"와 "우리 프로토콜이 애초에 LIBE를 재현하지 못한다"를 분리한다.**
  이 분리가 없으면 프로토콜 결함을 레벨 탓으로 오진한다.

  | 조건 | 결정 |
  |---|---|
  | `σ_eff < 0.05 eV` AND `ρ > 0.95` | 값싼 레벨 채택 (S1·S2 공통) |
  | `0.05 ≤ σ_eff < 0.1` AND `ρ > 0.90` | 채택하되 **ADR-027의 `default`/`analogy_weak` σ_r를 그만큼 상향** — **손실을 불확실도로 흡수하고 명시** |
  | `σ_eff ≥ 0.1` OR `ρ ≤ 0.90` | **고수준 유지** |
  | 🔴 **L_A 자체의 σ > 0.1 eV** | **경보.** 우리 프로토콜이 LIBE와 재현되지 않는다는 뜻 — **레벨 문제가 아니라 프로토콜 문제.** 레벨 결정 전에 프로토콜부터 고친다 |
  | 🔴 **고수준 SCF 실패율 > 5%** | **레벨과 무관하게 발동.** `def2-TZVPD`로 하향 |

- **⟹ ADR-010 Decision 4 종속 처리**: S1과 S2는 **같은 kMC/ODE에 들어가므로 반드시 동일
  레벨**이어야 한다. ADR-026에서 "LIBE 호환성" 논거는 철회됐으나 **"S1↔S2 상호 일관성"
  제약은 그때도 남겨뒀고 지금도 유효하다.**
  ⟹ **ADR-010 Decision 4는 U-22의 결과를 그대로 따른다. 독립 결정이 아니다.**
- **Consequences**:
  - **U-22-a**: X1의 **L_A(영대조군) 결과가 레벨 결정의 선행 조건**이다. L_A σ가 크면
    레벨이 아니라 프로토콜을 먼저 고친다. `[UNRESOLVED — X1 대기]`
  - **U-22-b**: **고수준 SCF 실패율**(engineer P1b가 측정). >5%면 하향 분기 발동.
    `[UNRESOLVED — P1b 대기]`
  - **기본값이 고수준이므로 파일럿 결과를 기다리는 동안 설계·코드는 고수준을 전제로 진행한다**
    (내려가는 것은 위험이 낮고, 올라가는 것은 재작업이다).
- **Revisit trigger**: X1 / P1b 결과 도착 시 분기 규칙 적용.

---

## ADR-030: 🔴 **가정 A10 — RTX 4070 SUPER ≈ H100 / 2.** 개발 박스 GPU 실측을 H100으로 환산하는 규칙

- **Status**: Accepted (**가정이다. 실측이 아니다**)
- **Date**: 2026-08-17
- **Stage**: Infra
- **Context**: 사용자 지시로 개발 박스(WSL)에서 GPU 파일럿을 실행했다. 그 과정에서
  **이 환경에 GPU가 있음이 밝혀졌다** — engineer의 Round 1 관측("GPU 없음")은 `nvidia-smi`가
  PATH가 아니라 `/usr/lib/wsl/lib/`에 있어서 생긴 오진이었다.
  ```
  [MEASURED] NVIDIA GeForce RTX 4070 SUPER · 12.88 GB (가용 11.59) · CUDA 13.1 · WSL 패스스루
  [MEASURED] pyscf 2.14.0 / gpu4pyscf-cuda12x 1.8.1 / cupy 14.1.1 설치·임포트 성공
  ```
  🔴 **그러나 이 GPU는 프로젝트 대상인 H100(80 GB)이 아니다.** 여기서 나오는 수치를 그대로
  쓸 수 없고, 환산 규칙이 없으면 **측정을 해놓고도 쓰지 못한다.**

### 🔴 가정 A10 (사용자 지시)
> **H100 ≈ 2 × RTX 4070 SUPER** (우리 DFT 작업부하 기준)

**이것은 사용자가 지정한 가정이며 실측이 아니다.** 벤치마크로 검증되지 않았다.
**A10에서 유도된 모든 숫자는 `[DERIVED-A10]`으로 표기한다.**

### 환산 규칙 (A10 + engineer §R2-7의 기존 가정 결합)
engineer의 기존 `[ESTIMATE]`: **H100 1장 ≈ 64-core 노드의 8배**(중형 분자 DFT, 보수적).
A10과 결합하면:
```
[DERIVED-A10]  RTX 4070 SUPER 1장 ≈ 64-core 노드의 4배
[DERIVED-A10]  H100 wall-clock      = (4070 SUPER 실측 wall) / 2
[DERIVED-A10]  1 H100-h             ≈ 8 node-h ≈ 512 core-h   (A1 = 64 core/node 가정 하)
[DERIVED-A10]  1 4070S-h            ≈ 4 node-h ≈ 256 core-h
```
⚠ **A1(64 core/node)도 미확인 가정이다.** RT-1의 `cluster.cores_per_node`가 128이면
위 core-h 환산이 **전부 2배**가 된다(engineer RUNBOOK §R15 1단계가 A1을 최우선으로
재계산하라고 한 이유). ⟹ **A10과 A1이 곱해지므로 오차가 누적된다.**

### 자원 총량 환산 `[DERIVED-A10]`
| | H100 기준 (engineer §R2-7) | **4070 SUPER 환산** |
|---|---|---|
| 6장 × 2,016 h (전용) | 12,000 GPU-h | — |
| CPU 등가 | **6.1 M core-h** | **3.07 M core-h** (절반) |
| 개발 박스 **1장** | — | **2,016 h × 256 = 0.52 M core-h 등가** |

> 🟢 **개발 박스 GPU 1장이 CPU 봉투(5.80 M)의 약 9% 등가다** `[DERIVED-A10]`.
> 작지 않다. 다만 **현행 계획에서 GPU를 쓰는 생산 작업이 없다** — MLIP이 ADR-014→§R6.3에서
> 탈락하고 축 3이 PM7(CPU)로 확정됐기 때문이다. ⟹ **GPU의 현재 용도는 P4 프로브뿐이고,
> 잠재 용도는 ADR-028이 만든 최대 비용 항목(전 pool thermo 2,142종)의 GPU-DFT 오프로드다.**

### 잠재 이득 — 전 pool thermo의 GPU 오프로드 `[DERIVED-A10]`
ADR-028에서 **전 pool thermo가 계당 최대 비용 항목**이 됐다(N_pool 2,142, 계당 총 526 k core-h).
opt+freq가 GPU-DFT로 가능하다면:
```
H100 6장 전용 12,000 GPU-h → 6.1 M core-h 등가  ⟹ 전 pool thermo를 통째로 흡수하고 남는다
4070 SUPER 1장 (개발 박스)  → 0.52 M core-h 등가 ⟹ 계당 526 k의 약 100% 등가
```
> 🔴 **단 이것은 "GPU-DFT가 opt+freq 워크플로를 지원한다"는 미검증 전제 위에 있다.**
> engineer가 §R2-7에서 이미 경고했다: *"GPU-DFT는 SCF/gradient/Hessian은 성숙하나
> **TS 최적화·IRC 워크플로는 CPU 코드만큼 성숙하지 않고 functional/basis 지원도 제한적**이다."*
> **P4가 재려는 것이 정확히 이 전제다.** 그리고 우리는 방금 그 미성숙의 실례를 봤다 —
> `wb97x-d3`가 지원되지 않아 CPU·GPU 양쪽이 실패했다(범함수명 오류).

### 이 환산으로 **할 수 있는 것 / 할 수 없는 것**
| | 판정 |
|---|---|
| 개발 박스 P4 실행을 **스모크 검증**으로 쓰는 것 | 🟢 유효 — 패키지가 도는가, 판정 로직이 맞는가 |
| 개발 박스 wall을 **H100 wall로 환산**하는 것 | 🟡 A10 하에서만. **`[DERIVED-A10]` 표기 필수** |
| **메모리 상한 원자 수**를 환산하는 것 | 🔴 **불가.** 12.88 GB vs 80 GB는 **속도가 아니라 용량**이고 A10이 다루지 않는다. **실제 GPU 머신에서만 측정 가능** |
| 개발 박스 숫자를 **P4의 확정 측정값으로 보고**하는 것 | 🔴 **금지.** 스모크 결과이지 P4가 아니다 |
- **Decision**: A10을 공식 가정으로 채택하고, 이로부터 유도된 모든 수치에 **`[DERIVED-A10]`**
  태그를 단다. 개발 박스 P4 결과는 **`[SMOKE — RTX 4070 SUPER, not H100]`** 로 표기하고
  **P4의 실제 측정값 자리를 비워 둔다**(engineer RUNBOOK §R15 0단계의 "skipped는 조용히
  추정값으로 채우지 마라" 규칙과 같은 취급).
- **Consequences**:
  - **A10은 검증 대상이다.** 실제 GPU 머신에서 P4를 돌리면 **같은 계·같은 레벨**로 비교해
    A10의 배수(2×)를 **실측으로 교체**할 수 있다. 그때까지 `[DERIVED-A10]`을 떼지 않는다.
  - 🔴 **A10 × A1 오차 누적**: 두 가정이 곱해지므로 core-h 등가는 **최대 4배까지 흔들릴 수
    있다**(A10이 2배 틀리고 A1이 2배 틀리는 경우). **자원 배분 결정의 근거로 쓰지 마라.**
    용도는 "GPU 오프로드를 검토할 가치가 있는가"의 **자릿수 판단**까지다.
  - **engineer 재spawn 시 A10을 §0 가정표에 A1~A9와 나란히 등재**하라(RUNBOOK 반영 대상).
- **Revisit trigger**: 실제 H100 머신에서 P4 실행 시 즉시(배수 실측 교체).
  RT-1의 `cluster.cores_per_node`가 64가 아닐 때(core-h 환산 전면 재계산).

### 📊 개발 박스 P4 실행 결과 `[SMOKE — RTX 4070 SUPER, not H100]` (2026-08-17)

**⚠ 이것은 P4의 확정 측정값이 아니다.** 스모크 검증이며, **P4의 실제 측정값 자리는 비워 둔다.**
범함수를 `wb97x-d3` → **`wb97x-v`**(ADR-029 생산 레벨)로 고친 사본으로 실행.
계: `li_ec_radical_reactant.xyz` **11원자**, `def2-tzvp`, UKS doublet.

| 항목 | 값 |
|---|---|
| CPU wall | **186.94 s** (16 스레드, AMD Ryzen 7 7800X3D 8-core) |
| GPU wall | **62.05 s** (RTX 4070 SUPER) |
| **속도비 (동일 머신)** | **3.01×** |
| E(CPU) | −349.907522400861 Ha |
| E(GPU) | −349.9075223489916 Ha |
| **에너지 차** | **5.2 × 10⁻⁸ Ha** ⟹ 판정 기준 `< 1e-5 Ha`를 **약 200배 여유로 통과** 🟢 |
| `max_atoms_ok` | **66** (12.9 GB에서 OOM 없음) |
| `oom_at_atoms` | null |

🟢 **`cpu_reference_machine: "gpu_host"` 가 기록됐다** — 내가 요구한 "속도비 분모가 어느
머신의 CPU인지" 명시가 반영됐다.
🔴 **`gpu_model: null` 은 여전히 버그다.** 어느 GPU에서 잰 값인지 JSON에 안 남는다. coder에 지시함.

#### 환산과 그 한계
```
[MEASURED]     4070S ≈ 3.01 × (16스레드 Ryzen 7800X3D)
[DERIVED-A10]  H100  ≈ 6.02 × (16스레드 Ryzen 7800X3D)
```
🔴 **이것을 engineer의 §R2-7 "H100 ≈ 64-core 노드의 8배"와 직접 비교할 수 없다.**
분모가 다르다 — **16스레드 데스크톱 CPU ≠ 64-core HPC 노드.**
⟹ **두 숫자를 잇는 것은 RT-1의 `probe_node`(A1 + CPU 사양)이며, 그 전에는 환산 불가다.**
**engineer의 8배 추정은 여전히 미검증 상태로 남는다.**

#### 🟢 그래도 얻은 것 — 메모리 상한이 우리 계를 덮는다
`max_atoms_ok = 66` @ 12.9 GB, `def2-tzvp`.
- **S2 pool species는 5~25원자**(ADR-026 실측, LIBE 상한 22) ⟹ **여유롭게 들어온다**
- **S1 클러스터는 30~80원자** ⟹ **66원자까지는 커버, 상단은 경계선**
- ⟹ **12.9 GB 급 GPU로도 전 pool thermo(ADR-028의 최대 비용 항목)는 메모리상 가능하다.**
🔴 **단 80 GB H100의 상한은 여기서 외삽하지 않는다** — ADR-030 본문대로 **메모리는 A10의
적용 대상이 아니다**(속도가 아니라 용량). 실제 GPU 머신에서 측정한다.

#### ✅ 출하본 재실행 (패치 없이, `dist` 빌드 그대로) — 요구사항 전부 반영 확인
| 항목 | 값 |
|---|---|
| `gpu_model` | **"NVIDIA GeForce RTX 4070 SUPER"** 🟢 (이전 `null` 버그 해소) |
| `gpu_memory_total` / `gpu_count` | 12282 MiB / 1 |
| `name_preflight` | **`xc_valid: true`, `basis_valid: true`**, 원소 C/H/O/Li 확인 🟢 |
| `level.xc` / `level.basis` | `wb97x-v` / `def2-tzvp` |
| `level.xc_matches_production` | **true**, `production_xc_source: "ADR-029"` 🟢 |
| `level.production_basis` | `def2-TZVPPD` + **환산 주의 문구가 JSON에 내장됨** |
| `n_basis_functions` | 224 |
| CPU wall / GPU wall | **177.32 s / 62.08 s** ⟹ **속도비 2.86×** |
| 에너지 차 | **5.19 × 10⁻⁸ Ha** (기준 1e-5 Ha) |
| `cpu_reference_machine` / `cpu_model` | `gpu_host` / AMD Ryzen 7 7800X3D |
| `max_atoms_ok` / `oom_at_atoms` | 66 / null |

🟢 **`name_preflight` 블록이 신설됐다** — 내가 요구한 "본 계산 전 범함수·기저 이름 검증"이
구현됐고, `wb97x-d3` 같은 결함이 **SCF 시작 전에 잡힌다.**
🟢 **`level` 블록에 "P4는 def2-TZVP로 쟀고 생산은 def2-TZVPPD다. 속도비 환산 시 기저 함수
수 차이를 반영하라"는 경고가 JSON에 내장됐다** — 사람이 기억할 필요가 없다.
📌 두 실행의 속도비 **3.01× / 2.86×** — CPU 변동 범위 안. **일관적이다.**

#### (아래 ADR-031이 이 절의 환경 가정을 실측으로 교체한다)

#### 이 실행이 실제로 산 것
1. 🔴 **`wb97x-d3` 결함을 왕복 없이 잡았다** — 사용자 GPU 머신에서 터졌으면 **3.5일 손실**.
2. **GPU-DFT 정확도가 검증됐다** — 5.2e-8 Ha는 기준의 200배 여유. **GPU 오프로드의
   정확도 측면 우려는 해소**(속도·메모리는 별개).
3. **gpu4pyscf 설치 경로가 확인됐다** — `nvidia-*-cu12` 라이브러리 추가 + `LD_LIBRARY_PATH`
   설정이 필요하다는 것. **실제 GPU 머신 셋업 시 같은 절차가 필요할 수 있다.**
   ⟹ **README_USER.gpu.md에 이 절차를 넣어야 한다.** coder 전달 대상.

---

## ADR-031: 🔴 실제 클러스터 환경 실측 확정 — 그리고 **ADR-029(레벨)를 가용성이 뒤집었다**

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra + S1/S2
- **Resolves**: **A1/A2 실측**, 스케줄러·소프트웨어 인벤토리, **ADR-029 개정**
- **Context**: 사용자가 실제 클러스터에서 `--dry-run`을 실행하고 출력을 회신했다.
  **RT-1의 일부가 이미 도착한 셈이다.** 이어서 노드 사양·큐 이름을 직접 정정해 줬다.

### 1. 실측 환경 `[MEASURED]`
| 항목 | 값 | 비고 |
|---|---|---|
| **계산 노드** | **68 core 시스템, 64 코어 사용** | 🟢 **engineer의 A1=64 가정이 맞았다** |
| 로그인 노드 | **24 core** | 🔴 **계산 노드와 다르다.** 아래 3번 |
| **스케줄러 / 큐** | **PBS / `normal`** | SLURM 아님 |
| wall 상한 | **24 h** | 🟢 engineer A2 가정 적중 |
| **CP2K** | **있음** | 🟢 P2/P2ext/p2_scaling 정상. **VASP AIMD 폴백 불필요** |
| **xtb** | 없음 → **동봉으로 해결** | 아래 4번 |
| **QC 코드** | 🔴 **ORCA/Q-Chem/psi4 전부 없음. Gaussian16 + VASP** | 아래 2번 |
| GPU | CPU 클러스터엔 없음 | GPU는 별도 머신. **패키지 분리가 옳았다** |
| 🟢 **self-chaining** | `P2ext` 가 `LINKS 2` 로 체인됨 | **critic B-1에서 고친 로직이 실제 클러스터에서 작동** |

**여전히 미측정**: A8(스크래치)·I/O·Q2(네트워크)·**A9(duty cycle 0.45)**·큐 대기.
`probe_*`가 실제로 실행되어야 나온다(dry-run만 왔다). 🔴 **A9는 왕복 모델과 일정의 근거다.
실측된 것처럼 쓰지 마라.**

### 2. 🔴 **ADR-029 개정 — `ωB97X-V`가 Gaussian16에 없다**
ADR-029는 `ωB97X-V/def2-TZVPPD/SMD`를 **순수하게 과학적 근거**로 확정했고, 그때 조건은
*"예산이 구속하지 않는다"* 였다. **이제 가용성이 구속한다.**
**proposer 확인 결과**: `ωB97X-V` · `ωB97M-V`(VV10 계열) · `wB97XD3` **모두 G16에 없다.**

> **⟹ 개정 결정: `ωB97X-D / def2-TZVPPD (gen) / SMD` 를 S1·S2 공통 레벨로 한다.**

| | 레벨 | 판정 |
|---|---|---|
| **G-1** | `wB97XD` / **def2-TZVPPD (gen)** / SMD | ✅ **채택.** range-separated라 장거리 교환 점근이 옳고 음이온 자기상호작용에 강함. **LIBE(ωB97X-V)와 교환 골격(ωB97X)이 같고 상관/분산만 다르다 — 가용한 것 중 최근접** |
| G-2 | `wB97XD` / def2-TZVPD (gen) / SMD | **SCF 강건성 대비책** |
| ~~G-3~~ | `M06-2X` | 🔴 기각 — **range-separated가 아니어서** 전하이동·음이온에 열등 |
| ~~참고~~ | `wB97XD` / **def2-TZVP(내장)** | 🔴 기각 — **diffuse 없음.** ADR-029의 핵심 논거 위반 |

🔴 **구현 제약**: `def2TZVPPD`는 **G16 내장 키워드가 아니다.** `gen`으로 외부 기저를 입력해야
하며, **패키지가 Gaussian 형식 기저를 동봉**해야 한다(C·H·O·Li·P·F 전부).
⟹ **`name_preflight`의 성격이 바뀐다**: "키워드가 유효한가"가 아니라
**"동봉한 기저가 등장 원소를 전부 덮는가"**.

### 3. 🔴 **X1의 영대조군을 잃었고, 더 나은 것으로 대체했다**
ADR-029의 `L_A`(= LIBE와 **동일 레벨**로 재계산하는 영대조군)는 **G16으로 ωB97X-V를 재현할
수 없으므로 불가능**하다. 그런데 ADR-029의 논지는 *"L_A의 σ를 모르면 나머지 σ를 해석할 수 없다"* 였다.

> **⟹ `L_A′` (신규): 같은 종을 G-1 레벨로 *두 번* 계산한다 — conformer 시드와 시작 구조를
> 독립적으로 바꿔서. 그 산포가 `σ_protocol`이다.**
> proposer: *"레벨 차이가 아니라 **프로토콜 잡음만** 분리해낸다 — 원래 L_A가 재려던 것보다
> **더 정확히 겨냥한다**(원래는 프로토콜 잡음 + 코드 구현 차이가 섞여 있었다).
> **σ_protocol이 곧 우리가 살 수 있는 정확도의 바닥**이고, U-05-b의 σ<0.1 eV 예산에서
> **먼저 빼야 할 항목**이다."*

**⟹ X1의 성격도 바뀐다**: "더 싸게 갈 수 있는가"(레벨 선택)에서 **"LIBE를 외부 벤치마크로
쓸 때의 계통 offset이 얼마이고, 그것이 flux *순위*를 보존하는가"(벤치마크 교정)** 로.
proposer 평: **"격하이고 단순화다. 좋은 소식이다."**
⟹ **coder 구속**: P5에 **"같은 종을 독립 시드로 2회" 모드** 필요(대표 종 3~4개).

### 4. 🟢 **xtb 동봉 — lead가 직접 검증**
```
출처 github.com/grimme-lab/xtb/releases v6.7.1 · 27 MB(xz) · LGPL-3.0-or-later(재배포 가능)
검증: 압축 해제 → bin/xtb 실행 → 물 GFN2 단일점 "TOTAL ENERGY -5.070383095219 Eh" 정상 종료
```
⟹ **P3가 살아난다.** ADR-014 이후 P3가 재는 **조합 폭발 계수**는 프로젝트 본체의 규모를
정하는 숫자다. ⚠ 정적 링크가 아닐 수 있으므로 **클러스터 glibc가 낮으면 실패할 수 있다** —
그 경우 **사유를 기록하고 다음 탐지 수단으로 넘어가게** 한다(조용히 죽지 않는다).

### 5. 🔴 이번 데이터가 드러낸 **패키지 결함 — 이기종 노드**
**dry-run의 planner가 *로그인 노드*(24 core)로 모든 잡을 sizing했다.** `plan.py:size_job`이
그 값으로 wall·links·core-h를 계산하므로 **계산 노드(64)와 2.7배 어긋난다.**
⟹ 잡이 wall에 잘리거나 자원이 안 맞고, **dry-run은 그걸 정상으로 보고한다.**
**고침 지시**: 로그인/계산 사양을 **분리된 필드**로, PBS `pbsnodes -a`/`qstat -Qf normal`로
큐 `normal`의 노드 사양 조회, 실패 시 `--cores-per-node` 지정, **둘 다 없으면 경고.**
🔴 **engineer RUNBOOK §R15 1단계에 경고 추가 지시**: *"`cores_per_node`가 로그인 값인지
계산 노드 값인지 반드시 확인하라. 이 프로젝트에서 실제로 2.7배 차이가 났다."*

### 6. ⚠ lead 자기 정정
로그인 노드 값(24)을 계산 노드 값으로 오인해 **"봉투가 5.80 M → 2.18 M(38%)로 준다"** 고
engineer에게 지시했다. **틀렸다. 철회했다.** A1=64가 실측으로 확인됐으므로
**ADR-019(5개월·완주 82%)와 ADR-028 배분은 흔들리지 않는다.**
**교훈**: 실측값을 받았을 때 **그 값이 어느 대상에서 측정된 것인지**를 먼저 확인해야 한다.
ADR-011의 `c` 정의 불일치, ADR-009의 인간시간 범주 오류와 **같은 계열**이다 — 세 번째다.
- **Revisit trigger**: `probe_*`가 실제 실행되어 A8·I/O·Q2·A9·큐대기가 도착할 때.
  G16에서 `gen` 기저가 예상보다 느릴 때(단가 재산정).

---

## ADR-032: 🔴 **composite 레벨 채택** — 그리고 그 주된 이득은 비용이 아니라 **구멍을 잡음으로 강등하는 것**

- **Status**: Accepted (조건 3건 동반 필수)
- **Date**: 2026-08-17
- **Stage**: S1 / S2 / S3
- **Resolves**: **U-30**. **ADR-029/031의 "고수준 전 pool"을 대체**
- **Context**: ADR-031이 레벨을 `ωB97X-D/def2-TZVPPD(gen)/SMD`로 확정했으나, engineer가
  Round 15에서 **자기 오류(정정 A)** 를 찾아냈다 — **§R14.5가 레벨 상향 비용을 `전 pool
  thermo`에만 곱하고 S1·S3를 레벨 불변으로 놓았다. 73% 과소평가.**
  ⟹ 고수준 총액이 A1=64에서도 **봉투의 122%(r=6, 데모1)** 로 **들어오지 않는다.**
  ⟹ ADR-029의 전제(*"예산이 레벨을 전혀 구속하지 않는다"*)가 사망했다.

### 채택 — `composite`
```
기하·진동수 @ ωB97X-D / def2-SVPD (gen) / SMD
   //  에너지 SP @ ωB97X-D / def2-TZVPPD (gen) / SMD
r_composite = 1.25   (고수준의 1/4.8, 값싼 레벨의 +25%)
```
| 구성 | 총액 | 봉투(5.81 M, A1=64·duty .45) 대비 |
|---|---|---|
| 고수준 r=6, 데모1 | 7.10 M | 🔴 **122%** |
| 고수준 r=6, 데모0 | 5.08 M | 🟡 87% (ADR-017 위반) |
| **composite, 데모1** | **2.17 M** | 🟢 **37%** |

🟢 **⟹ composite 채택으로 스코프 절단이 전혀 필요 없다.** 데모 1계(ADR-017)도 5개월(ADR-008)도
duty 개선도 불필요하다. **engineer가 올린 U-31(⑦ 5개월+데모0 vs ⑧ 6.5개월+데모1)은 소멸한다.**

### 🔴 Rationale — 채택 근거의 **주축은 비용이 아니다**
proposer §26(f):
> engineer가 *부수 효과*라 부른 것 — *"diffuse가 SP 1회에만 걸리므로 SCF 실패가 궤도
> 최적화 전체를 죽이지 않는다"* — **이것이 사실은 주된 이득이다.**
> §24.1에서 나는 **"구멍은 잡음보다 나쁘다 — 종 하나가 빠지면 그 종이 걸린 반응이 전부
> 사라지고, 이는 *구조적 0*이라 CR로도 탐지되지 않는다"** 고 썼다.
> **composite는 diffuse SCF 실패를 "network의 구멍"에서 "재시도 가능한 SP 1건"으로 강등한다.**
> ⟹ **비용 절감보다 이 강건성 이득이 크다. 이것만으로도 composite를 선호할 근거가 된다.**

**ADR-018의 판정 원칙("정확한가"가 아니라 "결론이 오차에 견디는가")의 연장이다** —
composite는 정확도를 조금 내주고 **탐지 불가능한 실패 모드(구조적 0)를 탐지 가능한
실패 모드(SP 재시도)로 바꾼다.** 그 교환이 우리 목적함수에 유리하다.
※ **ADR-029의 diffuse 논거(§24.3)는 예산과 무관한 물리이므로 유지되며, composite가 그것을
보존한다** — diffuse는 SP에 살아 있다.

### 🔴 채택 조건 3건 — **셋 중 하나라도 빠지면 판정 근거가 성립하지 않는다**
1. **(c) 시험 집합 R1~R4** — composite vs 고수준의 반응 ΔG 차이를 실측하는 집합.
   **사전 확약 판정 규칙**(engineer §R16.10): `|ΔG| < 0.05 채택 / 0.05~0.1 채택 + σ_r 상향
   / ≥ 0.1 불가`. **300 core-h로 살 수 있다.**
2. **(d) 선택지 C** — **회합·해리 반응만 진동수를 고수준으로.** *"불가 판정 전 필수 검토."*
   (진동 엔트로피가 분자 수 변화에 민감한 부류만 선택적으로 올린다.)
3. **(e) conformer 재정렬 규율** — SVPD에서 최저 1개만 고르지 말고, **SVPD 에너지 창
   ±0.1 eV 안의 conformer 전부에 TZVPPD SP를 돌린 뒤 TZVPPD 에너지로 재정렬.**
   *"SP는 싸다. 이 한 줄이 세 번째 위험을 제거한다. 그리고 이건 composite 특유의 문제가
   아니라 **어떤 //표기 계산에도 필요한 규율**이다."*

### Consequences
- **S3도 composite로** (proposer §27.4 동의): TS opt·IRC를 값싼 기저에서, 고수준은 최종 SP에만.
  🔴 **coder 구속**: **허수진동수 판정(ADR-027 M1~M3)이 값싼 기저의 Hessian으로 이뤄진다.**
  존재·개수는 기저에 둔감하나 **크기(cm⁻¹)는 민감하다** ⟹ **M2(허수진동수 크기 범위) 임계를
  값싼 기저 기준으로 재보정해야 한다.**
- **`r`이 여전히 최대 미지수다** — 총액을 1.3~10.2 M(7.8배)로 벌린다. **RT-1b(300 core-h)가
  이를 ±25%로 좁힌다.** ⟹ **파일럿 인도 게이트에 포함.**
- **ADR-031의 레벨 결정은 폐기가 아니라 "SP 레벨"로 격하**된다. G-1(`ωB97X-D/def2-TZVPPD`)이
  **여전히 최종 에너지 레벨**이고, 기하·진동수만 `def2-SVPD`로 내려간다.

### 함께 접수한 정정
- 🟢 **Q13 정정 (proposer §27.2)**: **H2O 도입에 따른 pool 증가는 ×1.5가 아니라 실측 ×1.04.**
  ADR-016/028이 ×1.5로 견적했던 것이 **과대**였다. **데모 계 생사 문제가 아니다.**
- **축 3 차선 서열 개정 (§27.3c)**: GPU 부재로 **zero-shot MLIP 탈락**, **CP2K DFT MD가 1순위**로.
- **CREST 대체 = RDKit ETKDG+MMFF** (CP2K 재작성 회피).
- **VASP 격자에너지**: LEDC 포논이 비관값의 대부분. **안전판(Γ점 전용 + 음향 근사 + δ 앵커
  흡수)을 비관값 발생 시 발동으로 합의.**
- **Revisit trigger**: **RT-1b의 `r_composite` 실측.** 시험집합 R1~R4에서 `|ΔG| ≥ 0.1 eV`가
  나오면 composite 불가 → 선택지 C 검토 → 그래도 불가면 U-31(⑦/⑧)이 부활한다.

---

## ADR-033: P2 처분 — 2개 삭제, 1개는 **소비자가 바뀌어 `P2f`(CP2K FIST 스모크)로 교체**

- **Status**: Accepted (사용자 지시 + proposer §28 확인)
- **Date**: 2026-08-17
- **Stage**: 파일럿
- **Context**: 사용자 *"P2가 필요 없으면 단순히 제거해."* lead가 P2 계열의 명시 근거가
  **폐기된 ADR-005 G-AIMD 분기**를 가리키고 있음을 발견하고 proposer에 확인 요청.
- **Decision**:
  | 항목 | 처분 | 근거 |
  |---|---|---|
  | **P2ext** | 🔴 **삭제** (1,152 core-h) | 소비자 없음. ADR-015 §14.5로 G-AIMD 감시 장치 전체가 소멸 |
  | **p2_scaling** | 🔴 **삭제** (60) | 소비자 없음. 직렬 궤적의 달력 문제가 생산 AIMD와 함께 사라짐 |
  | **P2** | 🟡 **`P2f`(CP2K FIST 스모크)로 교체** (400 → <50) | 소비자가 **바뀌었다**. 아래 |
  **회수 ≈ 1,562 core-h** (기존 CPU 파일럿 예약 1,882의 83%)
- **🟢 lead의 우려가 해소됐다 — λ_out 고전 MD 경로는 막히지 않는다** (proposer §28.2):
  > **CP2K의 `FIST` 모듈이 고전 MD 엔진이다.** 표준 力場·Ewald/SPME·NVT/NPT 지원.
  > 그리고 **수직 에너지갭 계산에는 코드 기능이 필요 없다** — 궤적 + 두 벌의 RESP 전하만
  > 있으면 **Coulomb 합으로 후처리**된다. *"MD 코드가 두 상태의 갭을 지원할 필요가 없다.
  > **스크립트 문제다.**"* (§11.1의 분해 — λ_out은 양자역학이 아니라 정전기학이 지배 — 에서 직접 따라 나온다.)
  ⟹ **CP2K는 여전히 필요하다. 단 AIMD가 아니라 FIST용이다.** 파일럿도 그에 맞춰 교체.
  ⚠ **진짜 비용은 코드가 아니라 환원종 FF 파라미터화(1~2 인간-주)이고, 이건 불변이다.**
- **P2의 조건부 부활 경로**: **MOPAC 부재 시 축 3 = CP2K DFT 확률적 MD**(§27.3c)가 되며,
  그때 `s/step`이 다시 필요해진다. ⚠ **이는 사용자가 금지한 "길고 직렬적인 생산 AIMD"가
  아니다** — 3 ps × 수십 궤적, 체인 0회, 완전 병렬. **ADR-025의 배제 범위 (b) 밖이다.**
- **Consequences**: **CP2K 계정(`-A`)이 여전히 필요하다**(`P2f`가 씀). 사용자 확인 대기,
  그때까지 `etc` + "미확인" 표시. **MOPAC 유무 확인이 최우선 미해결**(축 3의 존폐).
- **Revisit trigger**: MOPAC 확인 결과. 있으면 `P2f`만 남고, 없으면 P2(AIMD s/step)가 부활한다.

---

## ADR-034: ADR-028의 전제 정정 — **"레벨 선택이 예산 문제가 아니다"는 거짓이었다.** 그러나 ADR-032의 결론은 강화된다

- **Status**: Accepted. **ADR-028 Consequences 정정 · ADR-029/031 전제 정정 · ADR-032 보강**
- **Date**: 2026-08-17
- **Stage**: Infra / S1·S2·S3
- **Context**: engineer가 A1=64 복원 후 Round 15 정정판(§R18)을 냈다. **봉투·일정·상한은
  전부 복원되어 ADR-019/028이 흔들리지 않는다**(소요 2.05 M = 봉투의 35%, 예비 65%).
  🔴 **그러나 딱 한 항목이 복원되지 않았다 — 생산 레벨.**

### 1. 🔴 정정 — ADR-028의 *"레벨 선택이 더 이상 예산 문제가 아니다. 고수준 전 pool도
   봉투의 50%로 들어온다"* 는 **거짓이었다**
그 판정은 engineer의 §R14.5 위에 있었고, **그 계산은 레벨 상향 비용을 `전 pool thermo`에만
곱하고 S1·S3를 레벨 불변으로 놓았다**(engineer 자기 진단: 73% 과소평가).
**A1과 무관한 순수 산술 오류**이므로 봉투 복원 후에도 그대로 남는다.
```
총액 = 855 + 959·r (데모1)   [k core-h],  봉투 5.81 M
r=1.25 composite 데모1 → 2.05 M = 35%   🟢
r=4    고수준 낙관     → 4.69 M = 81%   🟡 재계산 1회면 118%
r=6    고수준 기준     → 6.61 M = 114%  🔴
```
⟹ **ADR-029가 "순수하게 과학으로만 결정하라"고 한 전제가 성립하지 않았다.
고수준은 처음부터 감당 불가였다.** 실제 증분은 §R14.6이 말한 +1.15 M이 아니라 **+4.8 M
(봉투의 83%)** 이다.

### 2. 🔴 그리고 배제 근거가 **셋으로 늘었고 서로 독립이다**
| # | 근거 | 내용 |
|---|---|---|
| 1 | **예산** | r=6 데모1 = 114% |
| 2 | 🔴 **일정 — 예산보다 먼저 죽는다** | 고수준 r=6 데모1 = **24.2주** (S2 ×2.6, S3 ×5.7). **재계산 0회에서도 5개월(21.5주) 초과** |
| 3 | **실행 가능성** | 고수준 TS 1건 = 172 h = **8 체인 링크**(job 상한 1,536 core-h). 205건 × 8링크, 링크 손실 5%면 재시도 배수 1.7 → 2.6. **반영하면 데모0도 100% 초과** |
**⟹ 하나가 틀려도 나머지 둘이 남는다. 고수준 전 pool은 배제 확정이다.**

### 3. 🟢 그러나 ADR-032(composite 채택)는 **약화되지 않고 강화된다**
engineer §R18: *"권고는 그대로 composite. **다만 성격이 바뀌었다** — '살기 위한 절박한
선택'에서 **'여유 65%를 갖고 고르는 최선'** 으로. proposer에게 **예산 압박 없이** U-30을
판정하라고 정정해 보냈다. **진짜 선택지는 `composite` vs `값싼 레벨`이지
`composite` vs `고수준 전량`이 아니다.**"*

🔴 **이것이 ADR-032를 검증한다.** 내가 ADR-032에서 채택 근거의 주축을 **비용이 아니라
강건성**(*"구멍을 잡음으로 강등한다"*)에 둔 것이 옳았다 — **예산 압박이 사라져도 결론이
그대로**이기 때문이다. **비용으로 정당화했다면 지금 재검토 대상이 됐을 것이다.**
⟹ **ADR-032 유지. 조건 3건(시험집합 R1~R4 / 선택지 C / conformer 재정렬)도 그대로.**

### 4. 🟢 복원된 것 (ADR-019/028 불변 확인)
`봉투 5.81 M · 소요 2.05 M(35%) · 예비 3.76 M(65%) · 일정 13.5~14.8주 · 완주 82%`
**§R16의 살인적 상한은 전부 철회**됐다: `N_pool ≤ 16,600 · S3 ≤ 500(사람 상한) ·
앵커 6×10⁵/계 · PM7 replica 60 k · 데모 3계 가능.` 예비 기지정 69%, **자유 여유 1.18 M(31%)**
— ADR-028 시점의 2%보다 오히려 낫다.
※ **§R15 관통 원리("희소 통화는 core-hour가 아니라 인간시간과 왕복")도 복원**됐다.

### 5. 남은 봉투 미지수 — **`n_nodes = 100`**
🔴 **`[ASSUMPTION]`이고 봉투가 여기 정비례한다. 남은 유일한 봉투 미지수다.**
큐가 `normal`로 확정됐으므로 `pbsnodes -a` + `qstat -Qf normal`로 교차검증 가능.
※ **A9(duty 0.45)의 성격이 바뀌었다** — 봉투의 65%가 미소비 전망이므로 **예산 레버가 아니라
달력 레버**다. 절단 순서의 `⓪ duty 개선` 권고는 유지하되 근거를 예산 → 달력으로 교체.
※ **κ(코어 성능)는 최상위 미지수에서 내려갔다** — 68코어 시스템은 2020년 이후 세대라
`κ = 0.8~1.2` [ESTIMATE].

### 6. 🔴 engineer의 자기 실패 기록 — **팀 규칙으로 승격한다**
> §R17.9 신규 9: *"§R16.1에서 나는 **'이 `24`가 `login_cpu`에서 온 것인지 `compute_nodes`에서
> 온 것인지 확인돼야 한다'고 정확히 적어놓고, 답을 기다리지 않고 그 값 위에 라운드 전체를
> 세웠다.** 봉투를 62% 깎고, 확정본을 불성립으로 판정하고, proposer에게 5배 틀린 상한을 보내고,
> lead에게 요구사항 포기를 요구했다.*
> ***`[MEASURED]`는 "측정됐다"이지 "무엇을 측정했는지 안다"가 아니다.***
> ***의심을 문서에 적는 것은 방어가 아니다.** 봉투를 곱하는 값은 출처 필드가 확인되기 전에는
> **그 값을 쓰는 작업 자체를 차단**해야 한다. 한 라운드를 폐기하는 것보다 한 왕복을 기다리는
> 것이 항상 싸다."*

**⟹ 팀 규칙으로 채택한다.** 그리고 lead도 같은 실패를 했다(로그인 노드 값을 검증 없이
engineer에게 전달). **ADR-009(인간시간 범주 오류) · ADR-011(`c` 정의 불일치) · ADR-031 §6에
이어 네 번째다. 전부 "숫자가 무엇에 대한 것인지 확인하지 않은 것"이다.**

🟢 **그리고 engineer가 건진 규칙 하나를 함께 채택한다:**
> *"견적을 낼 때 **'이 결론이 어느 가정에 의존하는가'를 표시하라.** 그 표시가 있으면 가정
> 하나가 무너져도 라운드 전체를 버리지 않는다."*
> — §R16에 "생존 항목 표"를 붙인 실천으로 **실제로 §R16의 절반이 살아남았다.**
- **Revisit trigger**: `n_nodes` 실측. RT-1b의 `r` 실측(고수준 배제 근거 1의 강도 변화).

### 🔴 ADR-034 정정 (engineer §R18.8) — 수요 모형을 통일한다

**lead가 쓴 `880 + 1,036·r`은 §R16의 낡은 모형이다**(S3 재시도 2.2, 5링크 전제).
A1=64에서 **링크가 2개**이므로 재시도 배수가 `1.7/0.95² = 1.9`가 되고 S3가 749 k → 642 k다.
```
✅ 확정 수요 모형:  총액 = 855 + 959·r (데모1) / 498 + 695·r (데모0)   [k core-h]
```
| 구성 | ~~lead 값~~ | **확정값(§R18)** | 판정 |
|---|---|---|---|
| composite(r=1.25) 데모1 | ~~2.17 M (37%)~~ | **2.05 M (35%)** | 동일 — 여유 |
| 고수준 r=6 데모1 | ~~7.10 M (122%)~~ | **6.61 M (114%)** | 동일 — 불가 |
| 고수준 r=6 데모0 | ~~5.08 M (87%)~~ | **4.67 M (80%)** | 동일 — 조건부 |
**판정은 어느 모형에서도 바뀌지 않는다.** job 실링 1,536 core-h, S3 2링크는 일치.

### 🔴 배제 근거를 예산만으로 적지 말 것 (engineer 지적)
> *"네 표에서 **'87%/80%, 예산은 겨우 되네'로 보이는 구성들이 달력에서 먼저 죽는다.**
> 그리고 고수준 TS 1건 = 8 체인 링크 · 링크 손실 5%면 재시도 1.7 → 2.6인데
> **양쪽 표 어디에도 미반영이고, 반영하면 r=6·데모0(80%)도 100%를 넘는다.**"*

⟹ **`r`이 실측에서 4로 나와 예산이 통과하더라도 일정(24.2주)과 링크 수는 여전히 막는다.**
본 ADR §2의 3중 근거를 **표와 함께** 읽어야 한다. 예산 수치만 인용하지 마라.

### 🟢 추가 — **U-30이 부결돼도 스코프는 잘리지 않는다**
```
값싼 레벨 단독 (r=1, 데모1) = 1.81 M = 봉투의 31%  → 들어온다
```
⟹ **composite 부결 시 잃는 것은 열역학 품질이지 범위가 아니다.** 데모 1계·5개월·검증축·
발견 엔진은 어느 경우에도 유지된다. **ADR-032의 판정을 예산 때문에 서두를 이유가 없다.**

### 🟢 κ(코어 성능)는 레벨 판정을 뒤집지 못한다
κ = 1.5로 밝혀져도 **composite 35%는 버티고 고수준은 114% → 171%가 된다.**
⟹ **κ는 배제 근거를 강화만 한다. U-30 판정을 κ 때문에 미룰 필요 없다.**
※ engineer 자백: *"내 `κ=0.8~1.2`도 코어 수에서 세대를 역산한 것이고, **그게 방금 우리를
태운 방식이다.**"* ⟹ **계산 노드 `model_name`을 사용자에게 묻는 것(비용 0)이 RT-1c(30 core-h)보다 먼저다.**

### 🔴 `⓪ duty 개선`의 근거 교체 (ADR-017 반영 시)
engineer가 §R16.1에서 *"duty가 최대 예산 레버"* 라 한 것은 **2.18 M 봉투에서만 참이었다.**
5.81 M에서는 봉투의 65%가 미소비이므로 **duty는 예산을 사지 않고 달력만 산다.**
**순서 규칙("대가 0인 레버를 다 쓰기 전에 과학을 자르지 마라")은 그대로 옳다 — 근거만 교체.**

### 🟢 engineer의 상설 규약 승격 (§R17 5.5단계, 매 라운드 체크리스트)
1. **"결론을 비용으로만 정당화하지 마라. 비용은 봉투가 바뀌면 뒤집힌다."**
   — engineer 자평: *"나는 §R14.5/§R14.6에서 고수준 채택을 **비용 근거로 열어줬고,
   그 숫자가 틀리자 근거 전체가 사라졌다.** proposer가 composite를 강건성으로 정당화한 것이 옳았다."*
2. **"배제 판정에는 독립 근거를 복수로 세워라. 하나가 틀려도 나머지가 남는다."**
3. **`[MEASURED]` 출처 확인** (ADR-034 §6)
4. **생존 항목 표 상설화**
🔴 **네 번째 반복(ADR-009·011·031·034)이라는 지적을 받아들여, 규칙을 문서에 적는 데 그치지
않고 RUNBOOK의 실행 단계 안에 넣었다** — engineer.

### 책임 소재 (기록)
lead가 *"내가 먼저 틀린 값을 줬다"* 고 했으나 engineer는 **절반만 수용**했다:
> *"네가 준 것은 프로브 요약이었고, **그 값의 출처를 확인하는 것은 견적을 내는 내 일이다.**
> 나는 §R16.1에 확인이 필요하다고 정확히 적어놓고 답을 기다리지 않았다.
> **방어선을 설계해놓고 통과시킨 것은 나다.**"*

---

## ADR-035: M2(허수진동수 크기) 임계 — **재보정 불요를 잠정 승인.** 그러나 결정의 가치는 숫자가 아니라 **미검증 전제를 적어둔 것**에 있다

**일자**: 2026-08-17 | **상태**: 잠정 승인 (critic 검증 대기 / P1b 사후 검증 예정)
**관련**: ADR-032(composite 채택), proposer §27.4, critic 재리뷰 체크리스트 8번

### 맥락 — critic이 리뷰 전에 예측한 결함
ADR-032로 composite를 채택하면서 **TS 판정에 쓰이는 Hessian의 기저가 바뀌었다**:
전량 고수준(def2-TZVPPD) → 값싼 레벨(def2-SVPD). proposer는 이때 명시적으로 구속을 걸었다:
> *"허수진동수의 **존재·개수는 기저에 둔감하지만 크기(cm⁻¹)는 민감하다** ⟹
> **M2(허수진동수 크기 범위) 임계를 값싼 기저 기준으로 재보정해야 한다.** coder 구속."*

critic은 **재리뷰를 시작하기도 전에** 이 지점을 지목했다:
> *"`IMAG_WINDOW_CM1 = (-2000, -100)`이 값싼 기저 기준으로 재산정됐는지, 예전 고수준 기준
> 숫자가 그대로 남아 있는지가 핵심 — **이게 '같은 사실이 두 곳에 있고 한쪽만 갱신됨'의
> 여섯 번째 반복일 가능성이 가장 높은 지점이다.**"*

**lead 확인 결과 예측이 적중했다**: `criteria/p1.py` mtime 15:07(ADR-032 이전),
`grep "svpd|SVPD|hessian_level|basis"` → **0건**. 창만 있고 출처가 없었다.

### 결정
**1. 숫자는 유지한다** — `IMAG_WINDOW_CM1 = (-2000.0, -100.0)`.
coder 논거: *"창 폭 1,900 cm⁻¹는 기저 변경에 따른 변동(통상 수십 cm⁻¹)을 충분히 덮는다."*

**2. 🔴 그러나 이 ADR의 실제 산출물은 숫자가 아니라 `IMAG_WINDOW_PROVENANCE`다.**
판정 결과에 **어느 기저의 Hessian이었는지**를 항상 함께 싣는다
(`p1.py:265`, `_basis_from_route(freq_text)` — 하드코딩이 아니라 **로그 route에서 파싱**).
**하드코딩하지 않은 것이 핵심이다** — 그랬다면 이 ADR이 고치려는 바로 그 중복을 새로 만든다.

**3. coder가 스스로 미검증 전제를 적었다.** 이것이 이 결정을 승인 가능하게 만든 이유다:
> *"'수십 cm⁻¹'는 **문헌 통념이며 우리 계에서 실측하지 않았다.** P1b가 같은 계를 두 기저로
> 돌리므로, 그 결과로 이 전제를 사후 검증할 수 있다."*

**4. 과학적 재보정 권한은 proposer에게 있다.** coder는 숫자를 바꾸지 않았고, 바꿔야 한다고
판단되면 lead에게 보고하도록 구속했다. **구현자가 임계를 정하는 것은 스펙 발명이다.**

### 🔴 lead가 승인하면서도 남긴 의심 (critic에게 검증 요청함)
- **(a) 전제의 적용 범위**: "수십 cm⁻¹"는 통념이지만, **diffuse 함수 유무는 음이온·라디칼
  음이온에서 특히 민감하다. 우리 계는 환원 생성물 — 정확히 라디칼 음이온이다.**
  통념이 우리 계에 적용되는지가 확인되지 않았다.
- **(b) 🔴 논거의 논리적 빈틈**: *"창 폭이 넓다"* 는 **폭이 아니라 경계까지의 거리가 문제**라는
  점을 비껴간다. 상한 −2000은 넉넉하나 **하한 −100 근처의 얕은 TS는 기저 변경으로 창 밖으로
  나갈 수 있다.** 위험은 폭에 균등하게 분포하지 않는다.
- **(c)** provenance를 싣는 판정 경로가 **하나도 빠짐없이** 덮였는지.

⟹ **틀렸을 때의 결과: 가짜 TS를 통과시키거나 진짜 TS를 버린다.** 둘 다 S3 게이트를 오염시킨다.

### 결과 — 여섯 번째 반복은 어떻게 끝났나
| 회차 | 사례 | 발견 시점 |
|---|---|---|
| 1~5 | `SEI_KEY`, Mulliken stride, `wb97x-d3`, `guard_source`, sysprobe GPU | **사후** |
| **6** | **M2 임계** | 🟢 **사전 — critic이 리뷰 전에 예측** |

**패턴을 다섯 번 보고 여섯 번째를 예측했다. 이것이 리뷰가 도달할 수 있는 최선의 형태다.**
같은 라운드에서 coder도 P1b 대상 종을 manifest에서 **유도**하며 주석을 남겼다:
> *"여기에 id를 박으면 종을 바꿀 때 두 곳을 고쳐야 하고, **그러면 한쪽만 갱신된다.**"*
⟹ **팀이 이 패턴을 사후 수정이 아니라 사전 차단으로 다루기 시작했다.**

### 재개 조건 (이 ADR을 다시 열어야 하는 때)
1. **P1b 결과가 도착하면** — 같은 계를 두 기저로 돌리므로 (a)의 전제가 실측된다. **필수.**
2. TS 중 허수진동수가 **−100 ~ −250 cm⁻¹ 구간에 몰리면** — (b)의 위험이 현실화된 것.
3. critic이 (a)~(c) 중 하나라도 반증하면 → **proposer 재소환.**

---

## ADR-036: 폴백 코어 수는 **회신 JSON에서 `null`이다** — 하드 실패보다 정확히 겨냥한 방어

**일자**: 2026-08-17 | **상태**: 확정 (critic 재리뷰 중, 부작용 검증 요청함)
**관련**: ADR-034(로그인 24 vs 계산 64 사고), critic 재리뷰 MAJOR, engineer §R17 5.5

### 맥락
critic이 MAJOR로 올렸다: engineer의 요구 문구는 **"실패시켜라"**(하드 실패)였는데
coder는 **"시끄러운 폴백 + 계속 진행"** 을 구현했다. critic은 판정을 lead에게 넘겼다:
> *"coder가 독자 판단으로 요구사항을 약화했다는 사실 자체는 lead가 알고 재승인해야 한다 —
> **내가 대신 판정할 사안이 아니다.**"*

### 결정
🔴 **하드 exit은 요구하지 않는다. 대신 폴백 값이 `[MEASURED]`로 소비되는 것을 금지한다.**

**1. 하드 exit을 기각한 이유** — 이건 **프로브 패키지**다. `cores_per_node` 하나를 못 정했다고
전체를 죽이면 **I/O·큐대기·처리량·P1·P3의 측정값까지 같이 잃는다.** 대가가 이득보다 크다.
coder의 15초 중단 기회 + 제출 경로 노출은 critic 확인대로 **원래 사고의 핵심 조건
(경고가 안 보임)을 실제로 제거했다.**

**2. 🔴 그러나 진짜 해악은 실행이 계속되는 것이 아니다 — 잘못된 값이 측정값으로 소비되는 것이다.**
**우리는 이걸로 이미 한 번 크게 당했다(ADR-034):** lead가 로그인 노드 24코어를 계산 노드
값으로 engineer에게 넘겼고, engineer는 §R16 한 라운드 전체를 그 위에 썼다.
> engineer 자평: *"**`[MEASURED]`는 '측정됐다'이지 '무엇을 측정했는지 안다'가 아니다.**"*

**3. 요구사항 — 회신 JSON에서 그 자리는 `null`이다.**
| 키 | 값 |
|---|---|
| `cluster.cores_per_node` | **`null`** (계산 노드에서 온 값만 앉힌다) |
| `cluster.cores_per_node_login_fallback` | 원값 **보존**(버리지 않는다) |
| `cluster.cores_per_node_note` | *"이 값으로 봉투를 계산하지 마라"* |
| `unresolved_for_lead[]` | `cluster.cores_per_node` 항목 생성 |

### 🔴 핵심 논거 — 왜 경고가 아니라 `null`인가
> **경고 문자열은 사람만 읽는다. `null`은 코드도 읽는다.**

ADR-034의 사고는 사람이 경고를 못 봐서가 아니라 **소비자(engineer)가 그 숫자를 그대로
집어 들었기 때문**에 일어났다. 방어는 **소비 지점**에 있어야 한다.
**하드 실패는 생산 지점을 막는 것이고, `null`은 소비 지점을 막는 것이다. 해악이 있는 쪽은 후자다.**

### 🔴 이 판정이 만든 새 위험 (lead가 스스로 올린 것, critic 검증 요청함)
`env["cores_per_node"]`는 **여전히 폴백 값을 갖고 jobs sizing에 쓰인다**(`cli.py:122,154`).
⟹ **회신은 `null`인데 실제 잡은 24코어 가정으로 사이징된다.**
lead는 *"wall을 길게 잡는 쪽이라 보수적"* 이라 판단했으나 **확인하지 않았다.**
🔴 **PBS `select=`/`ncpus=`에 24가 박혀 나가면 64코어 노드에서 자원을 잘못 요청하거나
큐가 거부할 수 있다.** ⟹ **내 판정이 만든 위험이므로 critic에게 명시적으로 검증을 넘겼다.**

### 부수 기록 — critic이 인도를 막았다
lead는 같은 라운드에 인도 게이트 3건을 **"통과"로 선언**했고, 직후 critic이 **BLOCKER 2건**을
찾았다(B-3: P1 판정이 Gaussian 로그를 파싱 못 해 **모든 결과가 `fail`**; B-4: `SEI_CP2K` vs
`SEI_CP2K_BIN`). **1,000 core-h가 무의미해질 뻔했다.**

🔴 **lead 검증 방식의 구조적 결함**:
| | 방법 | 결과 |
|---|---|---|
| lead | 필드가 **존재하는지** (`grep`) | 통과 선언 |
| critic | 함수를 **실행** (`p1.parse_frequencies(sample)` → `([], 'none')`) | BLOCKER 2건 |

**존재와 작동은 다른 사실이다. `build_stamp check ✅`도 "소스≡타르볼"이지 "코드가 맞다"가 아니다.**
⟹ **상설 규약 추가: 인도 게이트 검증은 `grep`이 아니라 경로 실행으로 한다.**
(engineer §R17 5.5의 4개 규칙에 이어 **5번째**.)

또한 critic 진단: **520 테스트 전부 통과 상태에서 BLOCKER 2건이 살아 있었다** —
*"두 모듈이 각각 단위 테스트는 통과하지만 **통합 경로 자체가 한 번도 실행된 적이 없다.**"*
⟹ **테스트를 늘리지 말고 경로를 실행하라.** `tests/test_integration_paths.py` 19건 신설
(양성 대조군 포함). **단 "테스트가 있다"는 또 존재 확인이므로, 수정 전 코드에서 실제로
실패하는지를 critic이 확인한다.**

---

## ADR-037: **GPU 패키지 드롭** — 측정이 정확해도 그 값을 넣을 자리가 없다

**일자**: 2026-08-17 | **상태**: 확정 | **근거**: engineer §R19, lead 확인
**관련**: ADR-030(A10 환산 규칙), ADR-015, ADR-014, ADR-034(배제엔 독립 근거 복수)

### 맥락 — 사용자 신제약
> *"모든 DFT/반경험적 방법론은 **VASP, Gaussian, xTB**로 완료되었으면 좋겠어."*
환경은 **air-gapped**(⟹ `pip install` 불가). P4는 **pyscf + gpu4pyscf**를 쓴다.

### 결정
**GPU tarball을 인도하지 않는다. 파일은 남긴다(삭제 아님, 미인도).**

### 🔴 결정적 근거 — 소비자 소멸 (비용이 아니다)
engineer 조사: P4의 **유일한 소비자**는 ADR-030이 적어둔 **전 pool thermo(2,142종)의
GPU-DFT 오프로드**였고, **신제약이 그것을 금지한다.**
> *"측정이 정확해도 **그 값을 넣을 계획 항목이 없다.**"*

| 잠재 소비자 | 판정 |
|---|---|
| MLIP active learning | 탈락 (ADR-014) |
| surrogate 학습·추론 | GPU 불필요 (§2025/§2192) |
| 축 3 반응성 MD | GPU 불필요 (§1831) |
| zero-shot MLIP | 조건부 잔존(U-19 미확인). 🔴 **발동해도 P4는 답을 주지 않는다** — P4는 GPU-DFT 프로브이지 MLIP 프로브가 아니다 |
| **전 pool thermo GPU 오프로드** | 🔴 **신제약으로 소멸 — 이것이 P4의 존재 이유였다** |

🔴 **이 판정은 ADR-034 규약 1("결론을 비용으로만 정당화하지 마라")을 지킨다.**
드롭의 근거는 설치가 어렵다는 것이 아니라 **소비자가 없다는 것**이다. 봉투가 바뀌어도 뒤집히지 않는다.

### 선택지 (3)(VASP-GPU / G16-GPU 대체)을 기각한 이유 — **독립 근거 복수** (ADR-034 규약 2)
**G16 GPU** `[VERIFIED-WEB 2026-08-17, gaussian.com/gpu]`:
1. 지원 카드 = K40/K80/P100/V100/**A100까지. 🔴 H100 없음, GeForce 없음** ⟹ 우리 H100 6장도 개발박스 4070S도 목록 밖
2. 원문 *"not effective for **small jobs**"* — 우리 pool은 **5~25원자**(ADR-026 실측)로 정확히 그 케이스
⟹ **두 근거가 독립.** 하나가 틀려도 나머지가 남는다.

**VASP GPU** `[VERIFIED-WEB, vasp.at]`:
1. OpenACC 포트는 **NVHPC SDK ≥21.2로 재컴파일 필요**(CUDA-C 포트는 6.3.0에서 삭제) ⟹ **"설치 0"이 거짓**
2. **평면파/주기계라 고립분자 벤치마크로 부적합** — 진공상자 결과는 생산 레벨(GTO ωB97X-V/def2-TZVPPD/SMD) 단가에 대해 아무것도 말하지 않는다

### 부활 비용 (되살릴 수 있다)
```
부활 단가 = coder 재빌드 0.5~1일 + 왕복 1회 3.5일 = 4.0~4.5일
P(부활) = 0.05~0.15 [ESTIMATE]  ⟹ 기대 부활비 0.2~0.6일
vs (2) 유지의 기대 손실 2.1~3.2일
```
(2)의 손실은 추측이 아니라 **우리 저장소 유물** `[MEASURED-artifact]`: `run.sh:65`의
`env -u LD_LIBRARY_PATH` 회피 주석, `README_USER.gpu.md:40`의 *"pip install만으로는 부족할 수
있습니다"* + nvidia-nvjitlink/cusolver/cublas 안내. **인터넷 있는 개발박스에서도 CUDA 런타임
충돌을 겪었다.** air-gapped 첫 시도 성공률 **10~40%** `[ESTIMATE]`.
🔴 **P4는 어느 임계 경로 위에도 없다** ⟹ 비관 시나리오가 프로젝트를 죽이지 않는다.
반면 (2)의 실패는 임계 경로 위의 왕복·사용자 주의와 경쟁한다.

### 🟢 부수 이득 — 사용자의 "설치 항목" 질문에 대한 답이 **0건**이 된다
lead 확인: `README_USER.cpu.md:62` *"`python3`(3.6+) 하나뿐. `pip install`도 인터넷도 필요
없습니다"*, `:68` *"**설치하지 마세요.** 없는 소프트웨어는 '없음'이 그 자체로 답입니다."*
+ G16·VASP 보유 + **xtb 동봉 완료**. **CP2K 부재 시 P2f는 `skipped`로 정상 처리**됨을
lead가 `collect.py:314`로 확인. ⟹ **CPU 패키지는 설치 요구가 진짜로 0이다.**

### ADR-030 부분 무효화
**A10 환산 규칙(4070S ≈ H100/2)은 유효하다.** 그러나 ADR-030의 **"잠재 용도 = 전 pool
thermo GPU-DFT 오프로드"** 항은 **신제약으로 무효**다. P4 실측값 자리를 비워 둔다는
ADR-030의 규율은 유지되며, **드롭은 그 빈칸을 채우지 않고 닫는 것**이다.
4070S의 `2.86× / max_atoms_ok=66 / ΔE=5.19e-8`은 전부 **`[SMOKE — not H100]`** 라벨로 보존.

### 부활 트리거 (§R19.6, 그 전에는 재론하지 않는다)
1. 사용자 제약 완화(pyscf 계열 허용) 2. U-19 + RT-2 실패 → **단 그때 필요한 것은 신규 MLIP 프로브이지 P4가 아니다**
3. G16이 H100을 지원하고 **동시에** 소비자가 소분자가 아니게 될 때

### 인도 영향
**없음.** 두 tarball은 물리적으로 분리돼 있고 드롭에 필요한 coder 작업은 **0**
(재빌드 0, 재스탬프 0, critic 재리뷰 0). **인도 목록에서 파일 하나를 빼면 끝이다.**

---

## ADR-038: λ_out을 **MD 없이** 얻는다 — ADR-012의 고전 MD 경로 철회, **CP2K 요구 소멸**

> 🔴🔴 **[2026-08-17 부분 보류 — ADR-039 참조]**
> 본 ADR의 **"(B) 연속체 단독 채택"** 부분은 **확정이 아니다.** 같은 질문에 대해
> **두 번째 독립 proposer 분석(§33)이 정반대 결론((A) GFN-FF MD 주경로)** 을 냈고,
> **§30의 핵심 논거인 "차등에서 오차가 상쇄된다"를 문헌 사례로 직접 반박**했다.
> **아래에서 살아 있는 것은 ① CP2K 요구 소멸(양쪽 일치) ② ADR-012 고전 MD 경로의 재검토뿐이다.**
> λ_out 엔진 선택은 **P2g(V1/V2) + U-27 실측으로 가른다.**

**일자**: 2026-08-17 | **상태**: 🔴 **부분 보류** (CP2K 소멸=확정 / 엔진 선택=미확정)
**근거**: proposer §30, lead 확인
**관련**: **ADR-012 철회(부분)**, ADR-015(AIMD=0), ADR-037, §11(고전 MD 선형응답), §28.2

### 맥락 — 사용자 신제약
> *"모든 DFT/반경험적 방법론은 **VASP, Gaussian, xTB**로 완료되었으면 좋겠어."*
파일럿에 남은 유일한 위반이 **CP2K(P2f)** 였고, 그 존재 이유는 ADR-012의 **λ_out을
고전 MD 선형응답으로 얻는다** 는 경로였다.

### 결정 — (B) 해석/연속체 경로 채택
🔴 **G16의 비평형 PCM이 λ_out을 직접 준다.** `SCRF=(...,NonEq=write)` → `NonEq=read` 2단계.
전부 **단일점**이며 새 코드·새 MD가 없다.
```
① 중성 N 평형 SMD 최적화 (NonEq=write)  → 느린 분극 저장
② 같은 기하, 환원종 R, NonEq=read       → G_R^vert   (느린 분극 동결)
③ 같은 기하, 환원종 R, 평형 SMD         → G_R^eq
λ_out = G_R^vert − G_R^eq     (기하 고정 ⟹ 순수 outer-sphere)
λ_in  = 기존 Nelsen 4-point
```
🟢 **부수 이점**: SMD의 비정전기(CDS) 항은 **기하에만 의존하고 유전율에 의존하지 않으므로
같은 기하에서의 비평형−평형 차이에서 정확히 상쇄된다.** ⟹ CDS 파라미터화 불확실성이
λ_out에 들어오지 않는다.

### 정확도 — 판정이 바뀐 이유는 물리가 아니라 **목적함수**다
| | λ_out 오차(차등) | ΔG‡_ET 오차 (×0.25) |
|---|---|---|
| 고전 MD + 전하 스케일링 | ±0.03~0.08 eV | 0.008~0.02 eV |
| **연속체 (비평형 PCM)** | **0.05~0.1 eV** `[ESTIMATE]` | **0.013~0.025 eV** |

🔴 **proposer는 §11.2의 "고전 MD가 더 정확하다"는 판정을 철회하지 않았다.**
> *"그 판정은 여전히 옳다. 문제는 **그 추가 정확도가 지금 필요한가**이다."*

**차등 오차가 절대 오차보다 훨씬 작은 이유**: 두 화학종에 **같은 공동 알고리즘·같은 유전율**이
적용돼 오차가 상관되고 차이에서 상쇄된다. **§7.1(b)의 우려는 cluster+SMD가 λ_out을 *암묵적으로*
다루는 것이었는데, 비평형 PCM은 그것을 *명시적으로* 계산한다 — 같은 물건이 아니다.**
ΔG‡ 오차 0.025 eV = **rate 2.7배**로, 우리 예산(0.1 eV = 50배) 안에 여유롭게 든다.

### 🔴 λ가 실제로 중요한 곳은 한 군데 — 거기만 따로 지킨다
λ는 E_red(단열 열역학량)에 들어가지 않고, 절대 ET 속도도 H_ab 부재로 계산 불가다.
⟹ λ가 사는 곳은 **상대 ET 속도**뿐이며 실질 소비처는 둘:
1. 종 간 상대 ET 속도 — **연속체로 충분**
2. 🔴 **1e⁻ vs 2e⁻ 분기 (= C2H4 vs CO, ADR-003 축(a)의 본체)** — **(2차 ET) vs (화학반응)** 이
   경쟁하고 **λ 오차가 ET 쪽에만 비대칭으로 걸린다**

⟹ **처방: 연속체 λ_out 전량 채택 + 2차 환원 분기에만 검증을 건다.**
**[검증 X3] 클러스터 크기 외삽** — 명시 용매껍질 0→1→2로 λ를 계산해 외삽, **연속체가 얼마나
놓치는지 직접 측정.** MD 불요, 새 코드 불요, **DFT 단일점만.**
§11.8의 `U-03-e`(가법성 검증)가 **보조 검증에서 주 검증으로 승격**된다.
외삽이 연속체와 **0.1 eV 이상** 어긋나면 그때 MD를 재논의한다.

### MD를 버리며 잃는 것 — 하나 있고, 숨기지 않는다
§1.3의 고전 MD는 λ_out만이 아니라 **Li⁺ 1차 배위 통계**에도 쓰였고, §1.6은 용매화 환경
정의를 **오차원 2위(E_red에 0.3~0.5 eV)** 로 꼽았다. **대체(둘 다 MD 불요)**:
1. **문헌 배위 통계** (CN≈4, EC-rich, CIP 분율의 농도 의존 — MD·분광 양쪽에서 보고됨)
2. **열거 + Boltzmann 가중** (CN=3,4,5 × EC/EMC/PF6⁻). 🔴 **한계 명시**: 고립 클러스터의
   상대 안정성이지 벌크 내 개체수가 아니다 ⟹ **1과 2가 어긋나면 1을 채택.**

### 연쇄 정리
- **ADR-012의 "고전 MD 선형응답" 부분 철회** — proposer 자평: *"내가 §11에서 세운 경로다.
  **AIMD를 대체하려고 만든 것이었는데 AIMD가 이미 사라졌으므로 그 대체물도 함께 재검토되는
  것이 옳다.** 순서상 §11 시점에는 볼 수 없었다."*
- **§11.8의 "환원종 고전 力場 파라미터화 1~2 인간-주" 불필요** 🟢 인간시간 회수
- **§28.2의 CP2K FIST 요구 소멸** ⟹ **P2f 제거**(아래)
- **U-03-d(전하 스케일링 vs 분극 力場) 소멸** — 고전 力場을 안 쓰므로 질문 자체가 없다

### P2f 제거 — 독립 근거 둘 (ADR-034 규약 2)
1. **소비자 소멸** (위)
2. **잔여 가치(가용성)가 이미 중복** — lead 확인: `sysprobe.py:17-26`의 `SOFTWARE_TARGETS`에
   `cp2k`/`cp2k.psmp`/`cp2k.popt`가 있고 `--version`까지 부른다(`:320` 모듈 스캔도 포함).
   ⟹ **`probe_node`가 이미 CP2K 유무를 회신에 싣는다.**

🟢 **결과: 파일럿의 계산 코드가 Gaussian16 + xtb 둘뿐 — 사용자 요구 그대로. 설치 요구 0건.**
⚠ **CP2K를 영구 배제하는 것은 아니다.** §27.3c 축 3 DFT MD 폴백에 남아 있으며 MOPAC 확인에
종속된다. 가용성은 `probe_node`가 계속 보고한다.

### 신규 `[UNRESOLVED]`
- 🔴 **U-27**: G16에서 **`NonEq`가 SMD와 결합해 동작하는지 미확인**(SMD는 IEFPCM 기반이라
  정전 부분은 되어야 하나 확인 안 됨). ⟹ **P1b에 스모크 1건을 얹어 이번 회신에서 답을 받는다**
  (lead 지시). 안 되면 **IEFPCM로 λ_out만 계산하고 나머지는 SMD 유지 — 분리 가능하므로 치명적 아님.**
- **U-28**: X3 외삽이 연속체와 0.1 eV 이상 어긋날 때의 대응. 그때 MD 재논의.

### lead 부기 — 왕복을 사는 거래
U-27 스모크 추가는 **범위를 엄격히 고정**(1종, 기존 입력 재사용, 실패해도 P1b 생존, IEFPCM
자동 폴백)한 대가로 **왕복 1회 = 달력 3.5일**을 산다. 사용자가 아직 실행 전이므로 **달력 비용 0.**

---

## ADR-039: λ_out 재결 — **부류 1/부류 2 분리**, X3 최우선 게이트, **사전등록 판정규칙**

**일자**: 2026-08-17 | **상태**: 확정 | **근거**: proposer §35(재결), §30, §34, engineer §R20
**관련**: **ADR-038 부분 보류 해제**, ADR-003 축(a), ADR-001(조성 확장성), ADR-018

### 사건 — 우연한 blind replication
🔴 **lead의 주소 지정 실수**로 같은 질문에 **두 proposer 세션이 서로를 모른 채 병렬로 답했다.**
§30 = **(B) 연속체 단독**, §34 = **(A) GFN-FF 주경로**. **결론이 반대.**
재결(§35)에서 §34 저자가 **§30이 대체로 옳다고 인정하고 자기 권고를 개정**했다.

### 🔴 이 사고의 실제 산출물 — 둘 다 틀린 것이 하나 있었다
| # | 쟁점 | §30 | §34 | 판정 |
|---|---|---|---|---|
| 1 | 연속체 오차 **부호** | 과소(**인용 없음**) | 과대(Ambrosio 확인) | **미해결 → U-39** |
| 2 | **차등이냐 절대냐** | 전부 차등 | 전부 차등 | 🔴 **둘 다 틀렸다** |
| 3 | falsifier 존재 | X3 있음 | "0"이라 씀 | **§30이 옳다** |

🔴 **2번이 핵심이고 어느 쪽도 보지 못했다.**
**1e⁻ vs 2e⁻ 분기에서는 (ET 갈래: λ 있음) vs (화학 갈래: λ 없음)이 경쟁한다
⟹ 상쇄할 상대가 존재하지 않는다 ⟹ 들어오는 것은 차등 오차가 아니라 절대 오차다.**
**§30은 차등 오차 예산(0.05~0.1 eV)을 절대 오차 소비처에 적용했다 — 범주 오류.**
그리고 이 반증의 도구는 **§30.3 자신의 문장**(*"λ 오차가 ET 쪽에만 비대칭으로 걸린다"*)이었다.

| λ_out **절대**오차 | ΔG‡(ET 갈래) | C2H4:CO 오차 |
|---|---|---|
| 0.20 eV | 0.049 eV | **7×** |
| 0.50 eV | 0.123 eV | **115×** |

### 결정 1 — 부류를 나눈다 (ADR-038의 보류 해제)
```
부류 1 (종 간 상대 ET 속도)      ← (B) G16 비평형 PCM. §30 채택. 새 MD 불요.
부류 2 (1e⁻ vs 2e⁻ = 축(a) 본체) ← 🔴 (B) 단독 불가. X3 브래킷이 (A) 발동을 정한다.
(A) GFN-FF                       ← "주경로" 기각 → **X3 조건부, 스코프 4종 → 1~2종**
CP2K                             ← 불필요 (양측 일치, engineer §R20도 기각)
```
🔴 **부류 1의 결론은 §30과 같지만 정당화가 다르다.** *"차등에서 상쇄된다"* 를 근거로 삼지 않고
**X3로 측정한 값** 위에 세운다. **상쇄를 가정하면 X3를 안 돌려도 되지만, 측정을 근거로 하면
X3가 필수가 된다.** 그리고 우리는 **오차의 부호조차 모른다(U-39)** — common-mode 상쇄 논거는
부호를 알 때만 성립한다.

### 결정 2 — X3를 최우선 게이트로 승격, **P2g보다 먼저** 돌린다
X3는 점 추정이 아니라 **브래킷**을 준다:
```
연속체 : 모든 것이 응답 가능 → 과대 편향 (Ambrosio 확인)
X3     : 배치 무질서 없음    → 과소 편향 (구조적)
⟹ 참값을 양쪽에서 감싼다 = 정당한 오차막대
```
**산출물은 "맞다/틀리다"가 아니라 브래킷 폭 W다.** 순서를 바꾸면 두 번 계산한다.

### 결정 3 — 🟢 **사전등록 판정규칙 확정** (결과를 보기 전에 고정)
`W = λ_hi(연속체) − λ_lo(X3)`, **부류 2 종 기준**:
| W | ΔG‡ 불확실도 | 분기비 | 판정 |
|---|---|---|---|
| **≤ 0.15 eV** | ≤0.037 | ≤4.2× | 🟢 **(B) 단독. (A) 불발동** |
| **0.15~0.35** | 0.037~0.086 | 4.2~28× | 🟡 **(A)를 부류 2에만** (궤적 10~20) |
| **> 0.35 eV** | >0.086 | >28× | 🔴 **(A) 전량** (궤적 40) |

부류 1 별도: (B)와 X3의 **λ 차등** 차이 ≤0.2 eV면 (B). 초과 시 **두 값 모두에서** C1 순서·C2
간격을 검사하고 **결론이 같으면 진행**(ADR-018 원칙), 갈릴 때만 (A) 확장.

🔴 **이 표는 결과를 보기 전에 확정됐다. 사후에 고치지 마라.**
proposer가 자기 예상(W가 중간 구간)을 함께 적었고 그 이유가 옳다:
> *"**예상을 적어두는 이유는 사후 합리화를 막기 위해서다.**"*
> *"§30도 §34도 미리 이기지 않는다. W가 정한다."*

### 결정 4 — `P2g` 유지, **정당화 교체 승인**
❌ λ_out → 🟢 **Li⁺ 배위 통계(§1.6 오차원 2위, E_red에 0.3~0.5 V) + ADR-001 이전성**
🔴 **결정적 논거**: §30.4의 대체안(문헌 CN)은 **ADR-001을 위반한다.**
> *"**미지 조성에는 문헌 배위 통계가 존재하지 않는다.** '문헌에서 가져온다'는 우리가 팔기로 한
> 물건과 양립하지 않는다."*

ADR-001(조성 확장성)·ADR-015(이전성)가 이 프로젝트의 인수 조건이다. 두 번째 대체안(열거+
Boltzmann)도 §30 자신이 *"벌크 팩킹·엔트로피 누락"* 이라 적었는데 **CIP/SSIP 분율이 정확히
그 둘이 정하는 양**이다. ⟹ **P2g는 X3 결과에 비종속. V2가 본체.**
V2 실패 시 문헌 CN을 **가정으로** 쓰고 보고서에 명시 — **그때 ADR-001 확장성이 실제로 얼마나
지켜지는지는 미해결로 남는다.**

🔴 **자기지적 기록**: *"우리는 λ_out(0.05~0.12 eV급)을 두고 두 세션이 병렬로 싸웠고,
그보다 3~10배 큰 오차원(배위 통계)의 조달은 §30이 문헌에 넘겼다."*
**논쟁의 크기가 오차의 크기에 비례하지 않았다.**

### 인도 영향 — **없음**
X3·P2g·(A)는 전부 **S1 파이프라인 항목**이고 **RT-1 파일럿에 들어가지 않는다.**
engineer §R20.3(*"패키지를 건드리지 마라"*) 유효. **패키지 최종 변경은 CP2K 제거 + U-27 스모크뿐.**

### 신규 `[UNRESOLVED]`
- **U-39**: 연속체 λ_out 오차의 **부호**. §30 "과소"(무인용) vs Ambrosio "과대"(확인). **모른다가 답.**
- **U-41**: 🔴 **문헌 Li⁺ 배위 통계가 실재하는가.** §30.4 주장에 **인용이 없고 proposer도 미확인.**
  **V2 실패 시 유일한 조달원이므로, 공백이면 ADR-001 확장성이 실제로 깨진다.** 문헌 라운드 필요.
- **U-37 재정의**: "SMD 이음매"(철회) → **"공동 반경 규약 민감도"**. 처방 = α 스캔(비용 0).

### 🟢 팀 운영 — 의도적 병렬 답변을 도구로 채택 (제한적)
proposer 권고를 **좁게** 수용한다:
> *"주소 실수를 재발방지 대상으로만 처리하지 말고, **쟁점이 큰 판정에서 의도적 병렬 답변을
> 도구로** 검토하라. 비용은 토큰이고, 얻는 것은 **단일 관점에서 안 보이는 오차의 상관구조**다."*

🔴 **적용 조건(남용 금지)**: ①틀렸을 때 되돌리기 비싸고 ②이미 내려진 ADR을 뒤집으며
③달력에 영향이 큰 판정. **일상 질의에는 쓰지 않는다** — 두 배의 토큰과 재결 라운드가 든다.
**근거**: 이번에 얻은 것(부류 1/2 구분)은 **어느 한쪽도 단독으로는 찾지 못했을 것**이다.

### 부수 — proposer↔engineer 직접 왕복 **최초 성사**
proposer가 lead를 거치지 않고 engineer에게 직접 견적을 물었다(1왕복, 스코프 2개 동시).
**설계한 지 오래됐으나 `SendMessage` 부재로 한 번도 일어나지 않던 것이 이번에 처음 작동했다.**

---

## ADR-040: V1 통과 승인 — 단 **판정은 임계값이 아니라 전파량 위에 세운다**

**일자**: 2026-08-17 | **상태**: 확정 | **근거**: proposer §36, coder V1 실측
**관련**: ADR-039(사전등록 규칙), U-42/U-43 신규

### 🔴 쟁점 — proposer가 **결과를 본 뒤 자기 합격기준을 바꿨다**
§34.8 원래 기준 `≤1e-6 상대` ⟹ 실측 `1.080e−06` = **아슬아슬한 불합격**.
개정 기준 `≤0.1 k_BT` ⟹ `0.044 k_BT` = **2.3배 여유 합격.** **기준 변경이 판정을 뒤집는다.**

**이것은 교과서적인 사후 합리화 위험이다.** 그러나 다음 세 가지로 승인한다:
1. 🟢 **proposer가 먼저 자진 신고했다** — *"내 V1 합격기준이 틀렸다. **골대를 조용히 옮기지 않겠다.**"*
2. **폐기 사유가 결과와 독립적이고 물리적으로 옳다**:
   ① GFN-FF 총에너지는 원자 기준에너지를 포함한 **임의 원점** ⟹ 분모가 무의미
   ② 🔴 **총에너지는 N에 비례 ⟹ 상자를 키우면 저절로 합격한다 — 도착된 유인**
   ⟹ **옛 기준은 "우리에게 유리하게 조작 가능"했다. 그것이 폐기의 진짜 이유다.**
3. 새 기준을 **빠듯하게** 잡을 수도 있었으나(0.05) 그러지 않았고, 실측이 2.3배 여유로 든다.

### 🔴 그러나 lead는 판정을 **임계값 위에 세우지 않는다**
임계값 논쟁은 원리적으로 결론이 안 난다. **판정의 근거는 전파량이다** — 이것은 기준 선택과
무관하게 계산되고, 우리 예산과 직접 비교된다:
```
1차 섭동 상계:  |δ⟨ΔE⟩| ≤ σ(ΔE)·σ(ε)/k_BT = (249 × 1.140)/25.85 = 11.0 meV
  ⟹ δλ_out ≤ 0.011 eV → δΔG‡ ≤ 0.0027 eV → **rate 배수 오차 ≤ 1.11×**
비교:  실격선 50× (0.1 eV)      ⟹ 여유 45배
       §35.4 녹색 구간 W≤0.15 eV ⟹ 그 1/14
```
그리고 이 상계는 **세 겹으로 보수적**이다(완전상관 가정 / σ(ε)에 반셀 최댓값 / 앙상블 간 상쇄 무시).
🔴 **⟹ 옛 기준(1e−6)으로 불합격시켜도 전파량은 1.11×다. 즉 기준 논쟁이 결론을 바꾸지 않는다.**
**이것이 승인의 실제 근거이며, 임계값 개정은 부차적이다.**

**추가 근거 — GFN-FF 에너지는 추정량에 등장하지 않는다**: 설계상 λ_out은 **우리 RESP 전하로
후처리한 갭**에서 나오고 GFN-FF는 **배치만 공급**한다. 잡음이 들어오는 유일한 경로가
볼츠만 가중 왜곡이고, 위 상계가 그것을 닫는다.

**부수 진단(숫자가 스스로 말한 것)**: 편차가 **비단조**(0.10→2.2e−5, 0.25→3.2e−6, 0.50→4.2e−5)
⟹ 계통 버그면 단조·누적이어야 한다. **비단조+소진폭 = 수치잡음이지 모형 결함이 아니다.**
0.50 이동에도 **결합수 324 불변**(=27×12) ⟹ 최소상 규약이 옳게 작동.

### 결정 1 — V1 통과. **단 (A)의 필요성은 전혀 늘지 않았다**
> *"**V1은 가용성 게이트이지 정확도 게이트가 아니다.** 실패했다면 (A)가 W와 무관하게 제거됐다.
> 통과했으므로 (A)가 **선택지에 남는다. 그뿐이다.**"*
🔴 **ADR-039 §35.4 사전등록 규칙 그대로 유지. V1이 잘 나왔다고 (A)를 밀면 그게 사후 합리화다.**

### 결정 2 — **V1b가 진짜 게이트다** (V1은 MD를 보증하지 못한다)
coder의 선긋기(*"우리가 잰 것은 단일점 불변성이지 MD 중 drift가 아니다"*)를 채택한다.
**drift의 압도적 다수 원인은 에너지가 아니라 힘이다.** `F ≠ −∇E`이면 에너지가 완벽히
불변이어도 MD는 반드시 drift하고, **V1은 이 경로에 원리적으로 눈이 멀었다.**

🔴 **V1b 판정②가 결정적이다**: NVE 5 ps를 **Δt = 1.0 / 0.5 fs 두 벌**로 돌려
**drift가 Δt²로 줄어드는가**를 본다.
> **안 줄면 그것은 적분오차가 아니라 힘–에너지 불일치이며 어떤 시간 스텝으로도 못 고친다.**
> **이 한 시험이 "튜닝 가능"과 "구조적 결함"을 가른다.** ⟹ **U-42.**
실패 시 **(A)의 PBC 경로가 소멸하고 droplet도 함께 죽는다**(같은 문제를 공유 — proposer가
droplet을 승격하면서도 이 점을 정직하게 명시했다).

### 결정 3 — `X3-min`은 **일방향 시험**임을 못박는다
> **"경보는 조기에 울릴 수 있어도 무죄는 선고 못 한다."**
X3-min = {자유 EC, Li⁺(EC)₄}는 연속체의 **쉬운** 사례(잘 정의된 공동·1가·단단한 고리),
부류 2는 **최악** 사례(2가 음이온·유연한 개환 사슬·유전 포화). ⟹ **W(X3-min)은 하한이다.**
| 결과 | 결론 |
|---|---|
| W > 0.35 eV | 🔴 **(A) 전량 발동 확정 — X3-full 안 기다린다** |
| W ≤ 0.15 eV | 🟢 부류 1만 (B) 확정. 🔴 **부류 2를 면제하지 않는다. X3-full은 반드시 돈다** |
*"'쉬운 사례가 통과했으니 다 통과'가 가장 흔한 검증 오류다."*

### 결정 4 — 🔴 **순서를 lead가 바꾼다: V1b를 X3-min보다 먼저**
proposer 권고는 `X3-min → V1b/c/d → V2`였다. **기각한다. 근거는 과학이 아니라 자원이다:**
- **X3-min은 Gaussian16을 쓴다 ⟹ 클러스터 ⟹ 사용자 제출 ⟹ 왕복 1회 = 달력 3.5일.**
- **V1b/V1c/V1d는 동봉 xtb만 쓴다 ⟹ 개발박스 ⟹ 달력 0.**
⟹ **V1b를 지금 돌린다.** V2 규모를 두 번 정하는 문제는 발생하지 않는다(V1b는 V2 규모와 무관).
🔴 **그리고 V1b가 U-42에서 실패하면 X3-min의 왕복 하나를 통째로 아낀다.**

### 결정 5 — V2 규모 혼선 해소 (**lead가 만든 혼선이다**)
lead가 coder에게 engineer의 **1,000~3,000원자**를 그대로 전달했으나 **그것은 λ_out 생산용**이다.
| | 수렴을 지배하는 길이 | 필요 크기 |
|---|---|---|
| λ_out 생산 | 정전 먼 장 `1/R` 15~20 Å | 1,300~2,300 원자 |
| **V2 (구조 검증)** | **Li–O 1차 껍질 ~2 Å** (2차 ~6 Å) | 🟢 **300~500 원자** |
⟹ **V2는 `Li⁺(EC)₄ + 용매 ~30분자 ≈ 300원자`, droplet 8 Å로 즉시 실행 가능.**

### 🟢 신규 팀 규약 — `[ISSUE-UNREPRODUCED]`
coder가 **같은 증상(591 eV)을 캐시 함정만으로 만들어냈다** ⟹ Issue #1118의 보고 증상이
사용자 측 함정으로 생성될 수 있음이 **실증**됐다.
⟹ **#1118의 지위를 "(A)의 알려진 실패 모드" → "미확인 위험 지표"로 격하.**
**"xtb의 결함"으로 인용 금지. "재현 조건 미상" 병기 필수.**
⚠ **반대 방향으로도 단정하지 않는다** — 우리는 #1118의 재현 조건을 모른다. **#1118은 여전히
V1b를 정당화하되, (A)에 불리한 증거로는 쓰지 않는다.**
> 🔴 **"재현하지 않은 버그 리포트는 증거가 아니다." `[FULLTEXT-UNVERIFIED]`와 같은 등급.**
> **이번엔 `[MEASURED]`가 `[문헌 보고]`를 이겼다.**

### 신규 `[UNRESOLVED]`
- **U-42** 🔴 GFN-FF의 `F = −∇E` 일치. **V1b 판정②가 유일한 판정 수단.** 실패 시 PBC·droplet 동시 소멸.
- **U-43** MD 중 토폴로지 동결 여부·크기. **버그가 아닐 수 있다**(우리 용도엔 오히려 유리). V1c에서 측정만.

### 확정 순서
`1. V1b → (실패 시 정지) → 2. V1c/V1d → 3. X3-min(왕복) → 4. V2(300~500원자)`

---

## ADR-041: **경계에서 테스트하지 마라 — 진입점에서 테스트하라.** 같은 실패가 세 번 반복됐다

**일자**: 2026-08-17 | **상태**: 확정 (상설 규약) | **근거**: critic 3개 라운드 누적
**관련**: ADR-036(grep 아닌 경로 실행), engineer §R17 5.5 규약 목록

### 사실 — 세 번 다 "테스트는 있었고 통과했다"
| # | 결함 | 컴포넌트 | 실제 경로 | 테스트가 놓친 이유 |
|---|---|---|---|---|
| 1 | **B-3** Gaussian freq 미파싱 → **모든 P1이 `fail`** | `g16.parse_frequencies` **정상**(단위테스트 철저) | `collect_p1 → evaluate_p1`이 **ORCA 파서를 부름** | `test_criteria.py`가 **ORCA 픽스처만** 씀. Gaussian 입력 **0건** |
| 2 | **거부 메시지 절단** → 원인이 잘려 **왕복 낭비** | `format_feasibility`/`_wrap` **정상**(coder가 고침) | `to_dict()`에 **`message[:400]` 하드컷**이 앞단에 남음 | `TestRejectionMessageIsNotTruncated` 3건이 **`to_dict()`를 안 거침** |
| 3 | **`--emit-script` ≠ 제출본** → **디버깅이 거짓말이 됨** | `build_spec()` **동일** | `cmd_emit_script`의 env에 **`SEI_QC_LEVEL` 누락** | `emit_script` 테스트 **0건** |

🔴 **세 번 모두 "부품은 맞는데 조립선에 한 단계가 더 있었다."**
그리고 세 번 모두 **전체 테스트가 통과하는 상태**였다(520 / 542 / 561건).
> critic: *"두 모듈이 각각 단위 테스트는 통과하지만 **통합 경로 자체가 한 번도 실행된 적이 없다.**"*

### 🔴 왜 이게 특별히 비싼가
셋 다 **조용히 틀린다**: 크래시가 없고, 회신 JSON은 정상 형태로 도착하며, **틀렸다는 사실이
사용자 클러스터에서 며칠 뒤에야 드러난다.** 1번은 **1,000 core-h**를, 2·3번은 **왕복
1회 = 달력 3.5일**을 태울 뻔했다(2번은 실제로 한 번 태웠다 — `...encountere`로 잘린 그 회신).

### 결정 — 상설 규약 (engineer §R17 5.5 목록에 **6번째**로 추가)
🔴 **결함의 회귀 테스트는 "사용자가 실제로 치는 명령"에서 시작한다. 내부 함수에서 시작하지 않는다.**

**구체 규칙**
1. **진입점 고정**: 사용자 경로가 `./run.sh --dry-run`이면 테스트도 거기서 시작한다.
   내부 함수 단위 테스트는 **추가로** 둘 수는 있으나 **그것으로 대체할 수 없다.**
2. **"부품이 맞다"는 증거로 쓰지 마라.** `g16.parse_frequencies`가 옳다는 것은
   `evaluate_p1`이 옳다는 근거가 **전혀** 아니다.
3. **두 경로가 같아야 한다면 그 동일성 자체를 테스트하라.**
   (`제출본 ≡ --emit-script 출력`처럼. **"같은 함수를 쓴다"는 설계 의도이지 검증이 아니다.**)
4. 🔴 **값을 변형하는 지점을 전수 조사하라** — 절단(`[:400]`, `[:66]`), 반올림, 기본값 주입,
   직렬화. **조립선의 어느 단계든 값을 바꿀 수 있고, 부품 테스트는 그 단계를 못 본다.**

### 🔒 규약 13 — **"판단을 유발하는 값"에만 진입점 검증을 건다** (coder2 제안, lead 채택)
lead 가 *"새 필드를 만들 때 진입점 테스트를 함께 만든다"* 를 제안했고 **coder2 가 반대했다. 옳다:**
> ① **대부분의 필드는 진단용 통과값이다**(`modules_raw`, `queues_raw`, `route`…).
>    거기까지 요구하면 **의식(ritual)이 되고, 의식은 지켜지지 않거나 지켜져도 아무것도 안 잡는다.**
> ② **넓은 규칙은 "없는 규칙을 테스트로 굳히는" 실수를 제도화한다**(규약 12).
> ③ 🔴 **이번 결함의 원인은 "새 필드"가 아니다** — `longest_stage()` 는 **단위 테스트가 4건이나
>    있었다. 있어서 오히려 덮였다고 착각했다.**

🔒 **채택하는 좁은 규칙:**
> **어떤 값이 *누군가 그것을 보고 행동하기를 기대*하며 만들어졌다면, 그 값은
> ① **최종 산출물까지 도달하는지** ② **사람이 읽는 채널(`warnings[]`)에도 뜨는지**
> 둘 다 검증해야 한다. 하나만 있으면 절반짜리 안전장치다.**

**적용(판단 유발값)**: 트립와이어 · 게이트 판정 · `degraded` · `[INVALID]` · `blocked_by_gate` ·
`queue_wall_surprise` — **"이걸 보면 무언가 해야 한다"는 값**
**제외(진단 통과값)**: 원문 로그 · 모듈 목록 · 경로 · provenance

🔴 **구분 기준 한 줄**: *"이 값이 `true` 인데 아무도 안 봤다면 무엇이 잘못되는가?"*
**답이 있으면 판단 유발값, "나중에 참고할 때 아쉽다"면 진단값.**

🟢 **기계적 강제 가능**(다음 판): `test_producer_consumer.py` 에 **판단 유발값 레지스트리**를 두고
회신 JSON 도달 + `warnings[]` 연결을 검사. 기존 `TestKnownLostFieldsStayConsumed` 를
**"이미 샌 값" → "판단 유발값"** 목록으로 승격하는 형태.

⚠ **coder2 가 스스로 적은 한계**: *"'판단 유발값이냐'는 사람이 판정한다. 그 판정이 틀리면
규칙이 안 걸린다."* 🔴 **그래도 넓은 규칙보다 낫다: 넓은 규칙은 전부 통과하면서 아무것도 안
잡지만, 좁은 규칙은 '이 값이 판단 유발값인가'라는 질문을 강제한다. 그 질문이 이번에 안 한 것이다.**

### 검증 규율 (lead 자신에게)
ADR-036에서 이미 세웠던 것을 재확인한다: **인도 게이트 검증은 `grep`이 아니라 경로 실행.**
lead는 이번에도 `561 tests OK` + `stamp ✅`로 "정상"을 보고했고 **critic이 두 치명을 찾았다.**
> **"전체 테스트 통과"는 결함 부재의 증거가 아니다. 세 라운드 연속으로 반증됐다.**

### 🔴 남겨두는 반례 — 이 규약이 만능이 아니다
**우리 박스에는 PBS도 Gaussian도 없다.** 진입점 테스트로도 **`qsub`이 실제로 수용하는지는
검증 불가능**하다. ⟹ 그 영역은 규약이 아니라 **`[UNVERIFIED — 사용자 클러스터에서만 확인
가능]` 라벨 + 진단 가능성 설계**로 다룬다. **"틀렸을 때 우리가 알 수 있는가"가 그 영역의
유일한 판정 기준이다.** (이번 라운드에서 그 판정 기준 자체가 #2·#3으로 깨졌다는 것이
문제의 심각성이다.)

### 부수 관찰 — 도구를 우회하는 경로를 항상 하나 남겨라
진단 도구가 두 라운드 연속 실패하자, **가장 빠른 답은 우리 코드를 거치지 않는 경로**였다:
사용자가 `qsub`을 직접 쳐서 **PBS 원문 메시지를 받는 것.**
⟹ **자체 진단 계층은 실패할 수 있다. 원천 도구를 직접 두드리는 절차를 항상 문서에 남겨라.**

---

## ADR-042: **회귀 테스트는 "수정 전 코드에서 깨지는 것"을 보기 전까지 존재하지 않는 것으로 간주한다**

**일자**: 2026-08-18 | **상태**: 확정 (상설 규약) | **근거**: 전임 coder 인수인계 §0.4, 세션 누적
**관련**: ADR-041(진입점 테스트), ADR-036(grep 아닌 경로 실행)

### 승격 사유
전임 coder 가 교체 전 남긴 인수인계에 이 한 문장이 있었다:
> **"회귀 테스트는 수정 전 코드에서 깨지는 것을 확인하기 전까지 존재하지 않는 것으로 간주한다."**

**HANDOFF 파일은 유실·미독 가능성이 있고, 이 규칙은 이 세션에서 가장 비싸게 배운 것이다.**
⟹ ADR 로 승격한다.

### 이 절차가 실제로 잡은 것 (전부 "통과"로 보이던 상태)
| 결함 | 겉보기 |
|---|---|
| **새 테스트가 한 번도 실행되지 않음** (같은 이름 클래스가 앞 정의를 덮음) | 33건 전부 통과 |
| **동일성 테스트가 항등식** (같은 인자를 두 번 넣어 비교) | 통과 |
| **`to_dict()` 의 400자 컷**이 실제 경로에 남음 | 컴포넌트 테스트 통과 |

🔴 **세 건 모두 전체 테스트 스위트가 초록이었다.** ADR-041 이 "어디서 테스트하나"를 정했다면,
**이 ADR 은 "그 테스트가 진짜인지 어떻게 아나"를 정한다.**

### 🔴 절차를 무효화하는 함정 2종 (규칙과 함께 반드시 기억한다)
전임 coder 가 **둘 다 밟았고**, 그래서 규칙만으로는 부족하다는 것이 증명됐다.

**(a) 되돌린 파일이 *깨져서* 난 오류를 "결함 탐지"로 착각한다.**
슬라이스 편집이 구문을 깨뜨려 `FAIL` 이 아니라 **import ERROR** 가 났다.
그대로 넘겼으면 *"3건이 깨진다"* 대신 *"1건 에러"* 를 근거로 삼았을 것이다 —
**되돌린 것이 아니라 부순 것이었다.**
⟹ **되돌린 파일의 구문을 먼저 확인**(`ast.parse`)하고, 🔴 **`FAIL` 과 `ERROR` 를 구분해서 읽어라.**
**`ERROR` 는 대개 실험이 잘못된 것이다.**

**(b) 복원했는데 안 고쳐진 것처럼 보인다 — `__pycache__`.**
복원 후에도 2건이 계속 실패했다. 코드는 맞았고 **테스트가 되돌린 코드의 `.pyc` 를 보고 있었다.**
⟹ **되돌리기 실험 뒤에는 `find . -name __pycache__ -exec rm -rf {} +` 하고 다시 확인한다.**

**(c) 🔴 되돌리기가 *실제로 적용되지 않았는데* 적용된 줄 안다** (coder2, 2026-08-18)
7개 필드를 정규식으로 한꺼번에 지웠는데 **`"seed"` 줄만 안 지워졌고**, 그 상태의 "FAIL 3건"을
결과로 넘길 뻔했다. **되돌리기가 부분만 적용된 채 통과한 것이다.**
> coder2: *"확인해서 `"seed"` 만 정확히 지워 재실험하니 그 2건이 정확히 깨졌습니다."*
⟹ 🔒 **되돌린 뒤, 그 변경이 파일에 실제로 반영됐는지를 먼저 단언하라.**
**정규식·일괄 편집은 조용히 일부만 걸린다.**

🔴 **세 형태가 모두 "실험이 거짓이 되는" 방식이고, 서로 다른 지점에서 발생한다:**
| | 무엇이 거짓이 되나 |
|---|---|
| (a) 파일이 깨짐 | **되돌린 게 아니라 부순 것** — `ERROR` 를 결함 탐지로 오독 |
| (b) `__pycache__` | **고쳤는데 안 고쳐진 것처럼** 보임 |
| (c) 부분 적용 | **안 되돌렸는데 되돌린 줄** 알고 통과 |
**⟹ 되돌리기 실험의 검증은 세 지점 전부에서 필요하다.**


🔴 **lead 도 이 세션 초반에 같은 `.pyc` 함정에 걸려 "패키지 결함"이라고 보고했다.**
**lead 와 coder 가 각각 한 번씩 당했다 — 사람이 기억할 종류가 아니므로 규약에 박는다.**

### 🔴 보강 — **없는 규칙을 테스트로 굳히지 마라** (coder2 자진 신고, 2026-08-18)
coder2 가 P3 제거로 깨진 테스트를 고치다가 *"생략 가능한 모든 항목은 `fallback_hint` 를 가진다"*
로 일반화해 새 테스트를 썼다. **그 불변식은 한 번도 참인 적이 없었다** — 보유 항목은 P3 하나뿐이었고
P3 제거 후에는 0 개다.
> coder2: **"없는 규칙을 테스트로 굳히는 것은 결함을 못 잡는 것보다 나쁩니다 —
> **다음 사람이 그걸 근거로 삼습니다.**"*

🔴 **본 ADR 의 주 규칙("되돌려서 깨지는지 보라")으로는 이 병이 안 걸린다 —
없는 규칙도 되돌리면 깨진다.** 필요한 검사는 다른 축이다:
> 🔒 **새 불변식을 테스트로 굳히기 전에, 그것이 *현재 코드베이스에서 실제로 성립하는 사례*를
> 열거하라. 사례가 0~1 개면 불변식이 아니라 우연이다.**

**두 검사는 직교한다: "되돌리면 깨지는가"(테스트가 살아 있는가) ⟂ "지금까지 참이었는가"
(규칙이 실재하는가). 둘 다 필요하다.**

### 부수 규칙 — 픽스처는 **진짜 생성기**로 만든다
`args` 는 `cli.build_parser().parse_args()`, `env` 는 `cli.build_env()` 로.
> **"손으로 채우면 *내가 상상한 CLI* 를 검증하게 된다."**
실제 사고: 손으로 만든 `env` 에 `vendored: {}` 를 넣어 P3 가 빠졌고, **lead 와 숫자가 안 맞았다.**

### 🔴 프로토콜 정정 — **동결 동일성은 `tarball sha256` 이 아니라 `source_digest` 다**
coder2 발견(2026-08-18):
> **"tarball `sha256` 은 재빌드할 때마다 바뀐다 — **gzip 에 mtime 이 들어간다.** 소스가 같아도.
> ⟹ 동일성 비교는 `build_stamp` 의 `source_digest` 로 하라."**

```
source_digest   e2ade998db3fc8ec   ← 소스가 실제로 바뀌어야 변한다
tarball sha256  ec2bb8ef321f / 436b7574b88a   ← 재빌드마다 변한다 (같은 소스에서도)
```

🔴 **lead 는 동결 지시를 매번 tarball `sha256` 으로 냈고, 세 번 어긋났다.**
전임 coder 가 §0.7 에 *"트리 해시가 한 판 뒤처진 채로 지시가 온다"* 고 예고한 그 사고인데,
**원인의 절반이 "내가 낡은 값을 인용한 것"이 아니라 "그 값이 애초에 동일성 지표가 아니었던 것"이다.**

🔒 **규약: 동결·리뷰 대상·인도본의 동일성은 `source_digest` 로 지정한다.**
**`tarball sha256` 은 배포 무결성(전송 중 손상) 확인용으로만 쓴다.** 두 용도를 섞지 않는다.
⚠ **`build_stamp check` 는 원래부터 내용 해시 기반이라 옳게 동작하고 있었다** — 틀린 것은
**사람이 인용하던 숫자**였다.

### 관련 상설 규약 (누적)
1. 결론을 비용으로만 정당화하지 마라 (engineer §R17)
2. 배제 판정에는 독립 근거를 복수로 (engineer §R17)
3. `[MEASURED]` 출처 확인 — *"측정됐다"이지 "무엇을 측정했는지 안다"가 아니다* (ADR-034)
4. 생존 항목 표 상설화 (engineer §R17)
5. 인도 게이트는 `grep` 이 아니라 **경로 실행**으로 (ADR-036)
6. 경계가 아니라 **진입점**에서 테스트하라 (ADR-041)
7. 🔴 **회귀 테스트는 되돌려서 깨지는 것을 보기 전까지 존재하지 않는다** (본 ADR)
8. **양성 대조 출력에는 `[양성 대조 — 주입]` 라벨** (lead 가 발견 목록으로 오독한 전례)

---

## ADR-043: **부재(negative)를 보고하기 전에 "그것을 찾아보기는 했는가"를 확인한다**

**일자**: 2026-08-18 | **상태**: 확정 (상설 규약) | **근거**: engineer3 자체 정정, lead 독립 확인
**관련**: **ADR-034**(`[MEASURED]` 출처 확인), ADR-036(폴백값 `null`), ADR-042

### 사건
engineer 가 **"MOPAC 부재 확정 `[MEASURED]` (PATH·module 목록 모두 없음)"** 을 두 채널로 보고했고,
그에 근거해 **"독립 3축 중 축 3(PM7)이 불가"** 라고 판정했다. **lead 는 그것을 사용자에게 전달했다.**
engineer 가 스스로 원본을 다시 파고 **철회**했다. **lead 가 독립 확인했다:**
```
cluster.software 키 = 정확히 19개
[apptainer, cp2k, cp2k.popt, cp2k.psmp, crest, docker, g09, g16, module, mpirun,
 nvidia-smi, orca, psi4, python3, qchem, singularity, srun, vasp_std, xtb]
🔴 'mopac' 없음 — 부재로 나온 게 아니라 **애초에 찾아본 적이 없다.**

modules = 32개뿐. orca/lammps/gromacs/QE 매치 0건.
🔴 Nurion 급 기계에 그것들이 없을 리 없다 ⟹ **키워드 필터 + `head -400` 절단된 부분 목록.**
   부재 증거로 쓸 수 없다.
```
⟹ **MOPAC = `[NOT MEASURED]`. 축 3 은 "불가"가 아니라 "미확인"이다.**

🟢 **대조군**: `crest` 는 **19개 프로브 키에 있었고 결과가 `''`**, module 키워드에도 있었고 매치 0건.
⟹ **"찾아봤고 없었다"** = 유효한 부재. **CREST 부재 판정은 유지된다.**
**같은 회신 안에서 한 부재는 유효하고 다른 부재는 무효다. 그 차이가 이 ADR 의 전부다.**

### 결정 — 상설 규약 (9번째)
> 🔴 **부재를 보고하기 전에, 그 항목이 *프로브 대상 목록에 있었는지* 먼저 확인한다.
> 프로브하지 않은 것의 부재는 측정이 아니다. 회신 스키마의 키 집합을 직접 열거해 확인한다.**

**왜 이것이 별도 규약이어야 하는가 — 기존 규약이 못 막는다:**
- **긍정 결과는 출처가 자명하다**(값이 있으면 뭔가가 그것을 만들었다).
  **부정 결과는 그렇지 않다** — "없음"은 *찾아보고 없음* 과 *안 찾아봄* 을 구분하지 않는다.
- **ADR-036 은 폴백값을 `null` 로 만들어 *긍정* 쪽을 막았다. *부정* 쪽은 열려 있었다.**
  **이번이 그 구멍이다.**

### 🔴 개정 — 세 번째 사례로 규칙을 좁힌다 (engineer §R24 제안, lead 승인)
| # | 사례 | 누가 | 형태 |
|---|---|---|---|
| ① | 인도 게이트 통과 선언 | lead | `grep` 으로 필드 존재만 확인 (ADR-036/041) |
| ② | **"MOPAC 부재 확정"** | engineer | 프로브 목록에 없는 것을 부재로 |
| ③ | **"`%chk` 0건"** | coder2 | **대소문자 변형을 놓침** |

**셋 다 "없음"을 `grep` 류로 단정했고 셋 다 틀렸다.**
🔒 **개정 규약:**
> **부재는 `grep` 으로 확정하지 않는다. 다음을 모두 만족해야 `[MEASURED — 부재]` 다:**
> **(i) 그것이 *검사 대상 목록에 있었는가* (ii) *대소문자·별칭·변형*을 포함했는가
> (iii) 가능하면 *경로 실행*으로 확인했는가.**
> **하나라도 못 하면 `[NOT MEASURED]` 다.**

### 구현 구속 (coder)
1. 🔴 **`parse_module_avail` 의 키워드 필터와 `head -400` 절단을 제거하고 `module avail` 전문을 회신에 담아라.** 이번 오류의 근본 원인이다.
2. **프로브 대상 목록을 회신에 함께 실어라.** 그래야 받는 쪽이 "없음"과 "안 찾음"을 구분한다.
3. `mopac`/`mopac2016`/`MOPAC2016.exe` 를 프로브 목록에 추가.

### 오류 계보 (engineer 자평)
① coder 128 core → ② 로그인 24 core(ADR-034, **출처 미확인**) → ③ κ=0.8~1.2(§R18.1)
→ ④ **"MOPAC 부재 확정" — ②와 정확히 같은 유형.**
> engineer: *"같은 라운드에 ADR-034 를 인용하면서 ADR-034 를 위반했다."*

### 🟢 발견 경위 — 직접 왕복이 잡았다
> engineer: *"**proposer 가 'CP2K 빌드가 실제로 뭘 실행할 수 있느냐'고 캐물어서 원본을 다시 팠다.
> 질문이 없었으면 틀린 채로 넘어갔다.**"*

**teammate 간 직접 대화가 처음으로 오류를 잡았다.** lead 중계 체제에서는 일어나지 않았을 것이다
(lead 는 그 요약을 이미 통과시켜 사용자에게 전달한 상태였다).
⟹ **사용자의 "팀 간 직접 소통이 가능해야 한다"는 지시가 즉시 값을 냈다.**

### 파생 — 축 3 판정의 구조가 바뀐다
core-h 로는 세 선택지 모두 봉투의 1~2% 다. **차이는 왕복에 있다:**
| 선택지 | core-h | 🔴 왕복 |
|---|---|---|
| MOPAC-PM7 | ~1% | **확인 1줄, 다음 패키지에 편승 = 0회** 🟡 **아직 죽지 않았다** |
| xtb GFN1/2 | ~1% | 🟢 ~0 (P3 로 검증됨). 단 **독립성 낮음**(proposer §2396) |
| CP2K 축 신설 | ~1~2% | 🔴 **1~2회 = 3.5~7일** (총 7회 중 RT-1 소진) |

🔴 **engineer 정정**: *"'비용은 어느 쪽이든 문제가 아니다'는 core-h 에 한해 참이고
**왕복에 대해서는 참이 아니다.**"* ⟹ **proposer 판정은 MOPAC 확인 1줄이 회신될 때까지 보류.**

---

## ADR-044: 축 3 = **PM7 유지**. 2-source 선언도 CP2K 신설도 아니다 — **MOPAC·CREST 동봉**

**일자**: 2026-08-18 | **상태**: 확정 | **근거**: proposer §37, engineer §R21.10
**관련**: **ADR-020(독립 3축)**, ADR-023, **ADR-025(MOPAC 반입 가능성)**, ADR-043, ADR-041

### 결정
| | 판정 |
|---|---|
| 축 3 | 🟢 **PM7 유지.** 새 축을 만들지 않는다 |
| MOPAC | **동봉**(xtb 와 같은 경로) |
| CREST | **동봉.** RDKit 대체안 **철회** |
| CP2K | **폐기 아님 — 조건부 대기** |
| xtb GFN2 를 축 3 으로 | 🔴 **기각** |

### 🔴 lead 오류 정정 2건 (내가 물은 방식 자체가 틀렸다)
**1. 사전등록 폴백의 발동 조건을 내가 오독했다.**
나는 *"MOPAC 이 없으니 §2700 폴백(2-source 선언) 발동 조건인가"* 라고 물었다.
proposer: **그 폴백은 표의 4행이고 조건은 "차선 ①zero-shot MLIP ②저비용 복합DFT/DFT MD
③DFTB3 이 *전부* 불가"다. ②가 `cp2k/5.1.0·6.1.0` `[MEASURED]` 로 살아 있으므로 4행에 도달하지
않았다.** ⟹ **"MOPAC 이 없다"는 그 폴백의 트리거가 아니다.**

**2. 더 근본적으로 — RT-1 은 U-18/ADR-025 를 반증하지 않았다.**
> 🔴 **"U-18 은 '설치돼 있는가'가 아니라 '반입 가능한가'였다. 이번 회신이 잰 것은 `PATH`/`module`
> 뿐이다. **'사이트가 안 깔아뒀다'와 '우리가 못 쓴다'는 다른 명제다.**"*

**이 둘을 같게 놓으면 *측정하지 않은 것*을 근거로 축을 버리는 것이 된다.** ADR-043 과 같은 계열의
오류이며, **이번엔 부재 여부가 아니라 부재의 *함의*를 과장한 형태**다.

**반입 경로는 이미 실증됐다**(전부 이번 회신 안): https 아웃바운드 true(계산·로그인 양쪽) /
miniconda3 존재 / 🔴 **동봉 xtb 가 KNL 에서 실제로 돌았다(P3 pass, crash 0)** —
**"사이트에 없는 바이너리를 동봉해 KNL 에서 돌리기"가 이미 1회 성공했다** / 실패 시 소스 빌드.

### 축 3 이 죽는 실제 경로 — **사전등록 게이트 3개**
| | 내용 |
|---|---|
| **G1** | 바이너리가 **KNL(AVX-512 BW/DQ/VL 부재)** 에서 도는가 |
| **G2** | `s/step` (engineer §R10.2 가 지목한 진짜 미지수) |
| **G3** | 하전·개각종의 SCF 수렴·파라미터 |
🔴 **전부 계산 노드에서, 1노드 수 분~궤적 1개.**
> **"로그인 노드 `--version` 은 게이트가 아니다(ADR-041). RT-1 의 P1/P1b/P5 가 죽은 것이
> 정확히 그 계열의 실패다."**

### xtb GFN2 를 축 3 으로 쓰는 안 — 기각 근거가 강하다
> *"GFN1/GFN-FF 보다 **더 나쁘다** — 같은 계열이 아니라 **축 2 가 이미 쓰는 바로 그 해밀토니안**
> 이라 `S₂∩S₃≈min ⟹ N̂≈max`. **2-source 보다 나쁘다: 2-source 는 정직하게 모르는 것이고,
> GFN2 3축은 3-source 인 척하며 낙관 편향을 만든다.**"*

### 2-source 로 갔을 때의 손실 (정량화 — 참고 보존)
관측칸 3 · 모수 3 ⟹ **df=0, λ_AB 를 넣을 자유도가 없다.**
⟹ 잃는 것은 정확도가 아니라 **ADR-020 의 표제("종속성은 추정 대상") 자체의 성립**이다.
`[예시계산]` 참 N=2,000, φ=1.3(약한 종속)만으로 **완결성 51%→67%(15%p 낙관),
누락량 973→511(거의 2배 과소보고).** **그리고 2-source 에서는 φ 를 추정할 방법이 없다.**
⟹ 그 경우의 보고서 문안: *"`N̂`은 하한, `Ĉ`는 상한으로만 해석. **'이만큼 놓쳤다'는 보일 수 있으나
'충분히 탐색했다'는 주장하지 않는다.**"* (§19.3 층 II 한계 문장과 **뭉치지 말 것** — 다른 손실이다.)

### 🔴 engineer 오류 정정 — lead 가 사용자에게 전달했던 것
engineer: *"CREST 부재 ⟹ P1 에 crest 스테이지가 있어 **2차 rc≠0 잠복**"*.
proposer 가 `payload/P1.sh` 를 **직접 읽고** 반증했다: **crest 는 이미 `if [ -n "$CREST" ]` 로
가드돼 있어 없으면 "생략(실패 아님)"이다.** `rc=3` 은 그 위쪽 `sei_qc_detect → SEI_QC="none"`(G16 미로드)다.

🔴 **그리고 진짜 위험은 반대 방향이다:**
> **"CREST 가 없으면 P1 은 실패하지 않고 **조용히 conformer 표집을 건너뛴 채 '성공'으로 돌아온다.**"*

**시끄러운 실패로 알았던 것이 실은 조용한 성공이었다.** 이 세션에서 같은 형태가 반복됐다
(B-3 / 400자 컷 / host 유실 / 이번 CREST). ⟹ **`degraded=true` + `warnings[]` 회신을 구속으로 건다.**

### 구현 구속 (coder)
1. **MOPAC ≥22.0 동봉**, **CREST 동봉**. **라이선스·SHA256·출처를 xtb 와 동일 형식으로 기록.**
2. **RDKit 은 공유결합 종 시드 전용으로 강등** — MMFF94 에 **Li 파라미터가 없고** ETKDG 는
   단일 공유결합 분자용인데 **우리 대상은 `Li⁺(EC)₃₋₅` 비공유 복합체다.**
   (§27.3a 판정은 *"xtb 가 없다"* 는 **거짓 전제** 위에 있었다 ⟹ 철회.)
3. **게이트는 계산 노드 진입점에서.** 로그인 노드 `--version` 금지.
4. 🔴 **PM7 MD 는 노드로컬 `$TMPDIR`** — Lustre 소파일 1,242 creates/s.
   **스텝당 파일 생성은 MDS 를 때린다.**
5. **conformer 는 GFN2 창 ≤0.13 eV 를 전부 DFT 로 승격 후 재정렬**(§16.1-B2 경계 보호)
6. 🔴 **축 3 출력은 포획 이력뿐. PM7·CP2K 에너지를 barrier 로 보고하거나 pruning 에 쓰지 마라.**

### 🔴 lead 판정 — 순서
**동봉·게이트는 재실행 패키지에 넣지 않는다.** 재실행은 **S1 단가 측정**이 목적이고 시간이 급하다.
**단 예외 1건**: **CREST 부재 시 `degraded=true`** 는 **재실행 패키지에 즉시 넣는다** —
없으면 P1 이 conformer 표집을 건너뛴 채 성공으로 돌아오고, **우리가 1,000 core-h 를 주고 사는
TS 단가가 과소평가된다.** 측정의 무결성 문제다.

### 신규 `[UNRESOLVED]`
**U-45**(MOPAC/CREST 의 KNL 실행 가능성 — G1~G3) · **U-46**(CP2K 5.1/6.1 의 BASIS/POTENTIAL
동봉 + 하전 고립분자 Poisson 분리) · **U-47**(ASE MOPAC 해석적 gradient)

---

## ADR-045: 축 3 폴백 **사전등록** — G1 실패 시 **(B) CP2K DFT**. 2-source 선언은 최후수단이다

**일자**: 2026-08-18 | **상태**: 확정 (사전등록 — **결과를 보기 전에 고정**)
**근거**: proposer §37.5 가 lead 에게 넘긴 판정 | **관련**: **ADR-014**, ADR-020, ADR-039(사전등록 선례), ADR-044

### 판정을 요구받은 것
동봉 MOPAC 이 **G1(KNL AVX-512 BW/DQ/VL 부재에서 실행)** 에 실패하면 남는 선택지가 정확히 둘:
| | 왕복 | 결과 |
|---|---|---|
| **(B) CP2K DFT(≠XTB) 확률적 MD** | 🔴 **1~2회** (3.5~7일. 총 7회 중 RT-1 소진, 6회 잔여) | 과학적으로 유효한 축 3 |
| **(C) 2-source 선언** | 0회 | 🔴 **ADR-014 의 "전수 탐색" 주장을 보고서에서 내려야 한다** |

proposer: *"내 입력은 값을 매기는 것까지다. **그 값이 왕복 1~2회보다 큰지는 네 판정이다.**"*
engineer: *"있으면 좋다 수준으로는 왕복을 안 낸다."*

### 🔴 결정 — **(B)를 사전등록한다.** 사용자의 제1 요구가 이것이기 때문이다
**이건 "있으면 좋은 것"이 아니다. ADR-014 의 본체다.** 사용자 원문:
> *"진행을 전면적으로 점검해야겠는데, **가능한 모든 reaction 을 찾는 것부터가 우선**이야. …
> 이 **가능한 반응 모두 탐색 부분에서 대부분의 시간이 소요**될 거야."*

**⟹ 전수 탐색은 이 프로젝트의 부수 목표가 아니라 재스코핑된 본체다.**
2-source 로 가면 **`N̂` 은 하한, `Ĉ` 는 상한으로만 해석 가능**해지고
(관측칸 3·모수 3 ⟹ **df=0, λ_AB 를 넣을 자유도가 없다**),
`[예시계산]` φ=1.3(약한 종속)만으로 **완결성 51%→67%(15%p 낙관), 누락량 973→511(≈2배 과소보고)**,
🔴 **그리고 2-source 에서는 φ 를 추정할 수단 자체가 없다.**
⟹ *"충분히 탐색했다"* 를 **주장할 수 없게 된다.** **그것이 사용자가 최우선으로 요구한 바로 그 주장이다.**

**⟹ 왕복 1~2회(달력 3.5~7일)는 이 요구를 지키는 값으로 지불한다.** 이것이 판정이다.

### 🟢 그러나 지금 지불하지 않는다 — 조건부다
**(B)는 두 관문이 *모두* 실패할 때만 발동한다:**
```
① 사이트 MOPAC 확인 1줄  (계산 0, 다음 패키지 편승, 왕복 0)
   ⟹ 있으면 끝. (B) 불필요.
② 없으면 → MOPAC 동봉 → G1(계산 노드에서 실행) 게이트
   ⟹ 통과하면 끝. (B) 불필요.
③ ①② 둘 다 실패해야 (B).
```
🔴 **①이 "없음"으로 나와도 판정은 안 바뀐다** — 그건 *"사이트가 안 깔아뒀다"* 이지
*"우리가 못 쓴다"* 가 아니다(ADR-044 §정정 2).
**MOPAC 은 NDDO 계열 소형 Fortran 코드로 AVX-512 를 요구하지 않으므로 G1 통과 개연성이 높다**
`[ESTIMATE]` ⟹ **(B) 의 기대 비용은 낮다.** 그래서 지금 미리 지불할 이유가 없다.

### 🔴 (B) 발동 시 **선행 조건** (proposer 요구 — 빼먹으면 (B)가 조용히 실패한다)
1. **U-46 선행 종결**: CP2K 6개 미측정(Quickstep 범위 / GPW·GAPW / **`$CP2K_DATA_DIR` 데이터파일** /
   xTB·DFTB 인터페이스 / psmp·popt / libint·libxc·ELPA)
   🔴 **데이터파일이 없으면 CP2K 는 죽는 게 아니라 기본값으로 조용히 *다른 계산*을 한다.**
   **이 세션에서 반복된 "조용한 성공" 형태의 다섯 번째다.**
2. 🔴 **CP2K 를 축 3 으로 쓸 때 `METHOD XTB` 금지, 반드시 DFT 레벨.**
   근거: engineer 확인 — **CP2K 내장 xTB = GFN1** ⟹ 축 2 와 같은 계열이 되어 축이 소멸한다.

### 기각 — xtb 를 축 3 으로 (engineer 권고, proposer 거부, lead 확정)
engineer 가 *"MOPAC 없으면 xtb 대체를 기본안으로"* 를 권고했다. **기각한다.**
축 2 가 이미 GFN2-xTB 다 ⟹ `S₂∩S₃≈min ⟹ N̂≈max` ⟹ **"전부 찾았다"는 거짓 확신.**
> proposer: **"xtb 축 3 은 값이 싼 게 아니라 값이 없다. 2-source 정직 선언보다 나쁘다 —
> 3-source 인 척하며 낙관 편향을 만든다."**

🔴 **이 논거는 engineer 자신이 §21.1 에서 세운 것이다.** 자기 논거에 자기 권고가 걸렸다.

### 🔴 G1 위험의 실제 소재 — lead 의 `[ESTIMATE]` 근거 정정 (proposer §37.6)
lead 는 *"MOPAC 은 NDDO 소형 Fortran 이라 AVX-512 를 요구하지 않으므로 G1 통과 개연성이 높다"*
고 적었다. **결론은 맞고 이유가 절반 틀렸다:**
> **ISA 위험은 MOPAC 자신의 코드가 아니라 링크된 BLAS/LAPACK 에 있다.**
> MOPAC 은 **대각화가 본체**라 BLAS/LAPACK 을 쓰고, conda-forge 배포는 MKL 또는 OpenBLAS 를
> 링크하는데 **둘 다 런타임 CPU 디스패치**를 한다(MKL 은 KNL 타깃 보유, OpenBLAS 도 커널 런타임 선택).
> ⟹ **위험은 낮다.**

🔴 **따라오는 구속 2건 (coder — 동봉 착수 시 반드시 적용):**
1. **"낮다"는 G1 을 생략할 이유가 아니라 G1 이 값싸게 끝날 것이라는 예측이다. 스모크는 그대로 돌린다.**
2. 🔴 **동봉 형태에 따라 위험이 다르다.** conda 경로는 런타임 디스패치라 안전하고,
   **정적 링크 tarball 은 빌드 타깃이 고정**돼 있어 이 논거가 **적용되지 않는다.**
   ⟹ **`"정적이니까 더 안전하다"는 거꾸로다.**
   참고: **동봉 xtb 6.7.1 은 정적인데 KNL 에서 돌았다 — 그 빌드가 보수적 타깃이었다는 뜻이지
   정적이 일반적으로 안전하다는 뜻이 아니다.** (표본 1건을 일반화하지 마라.)

### 🔴 이번 라운드가 남긴 방법론적 관찰 (proposer)
> **"이번 건에서 실제로 작동한 안전장치는 규약이 아니라 **'회신 원본을 직접 읽어라'** 였다.
> 내가 `sei_probe_report.cpu.json` 과 `sysprobe.py` 를 직접 판독하지 않았다면 프로브 키 19개에
> `mopac` 이 없다는 것을 못 봤을 것이다. …
> **요약 중계는 손실이 아니라 위양성을 만든다 — 없는 측정을 있는 것으로 만든다.**"*

**"손실"과 "위양성"의 구분이 핵심이다.** 요약이 정보를 깎는 것이라면 감수할 만하지만,
**없는 측정을 있는 것으로 만드는 것**은 방향이 다른 오류이고 **ADR-034·043 사고가 전부 이 형태였다.**
⟹ **판정에 쓰이는 사실은 요약이 아니라 원본에서 확인한다.**

### 🔴 발동 기준 개정 — 단일 임계를 **브래킷**으로 (proposer §37.7, lead 승인)
engineer 가 후보 B 발동 기준을 **`r ≥ 0.105 events/ps`** 로 세우고 *"`r` 은 값싼 PM7/xtb 궤적으로
재라"* 고 하면서 근거로 *"δ 는 소스 간 독립이라고 proposer 가 적었다"* 를 인용했다.
🔴 **proposer 의 문장이 아니다:**
| | 실제 |
|---|---|
| proposer 가 쓴 것 | δ(barrier 오차)는 **포획 *여부*의 상관**에 기여하지 않는다 |
| engineer 가 쓴 것 | δ 가 있어도 **사건율 `r` 의 *값*** 이 코드 간에 옮겨진다 |

**`r ∝ exp(−ΔG‡/k_BT)` 이므로 δ 에 지수적이다.** 1000 K 에서 δ=0.2/0.3/0.5 eV ⟹ **×10 / ×33 / ×331.**
⟹ **1~2 자릿수 흔들리는 측정치를 단일 임계에 넣으면 그 판정은 성립하지 않는다.**

🔒 **개정 (비용 0):**
```
r_xtb ≥ 3.5 /ps    →  후보 B 예산 안 — 통과 확정
r_xtb ≤ 0.003 /ps  →  탈락 확정
그 사이            →  🔴 **미결정.** 정직하게 남긴다.
                      ⟹ X1/X2 가 이미 만드는 xTB↔DFT 비교에서 **δ 를 실측**해 브래킷을 좁힌다
                         (**U-49**, X2 배치 편승, 비용 ≈0)
```
🔴 **그대로 뒀으면 (B) 발동 여부를 잘못된 확신 위에서 결정했을 것이다.**
**사전등록은 기준이 옳을 때만 보호막이 된다. 틀린 기준을 사전등록하면 틀림을 고정할 뿐이다.**

### 🟢 동봉 왕복 비용 = **0** (proposer 확인)
MOPAC 확인 1줄 · G1(ISA) 스모크 · CP2K `s/step` 파일럿(1,000 core-h) **전부 다음 패키지 편승.**
⟹ **①② 는 왕복을 하나도 쓰지 않고 닫힌다.**

### 사전등록의 의미 (ADR-039 선례)
🔴 **이 판정은 G1 결과를 보기 전에 고정됐다. 결과를 본 뒤에 고치지 마라.**
G1 이 실패했을 때 *"달력이 급하니 2-source 로 가자"* 는 **사후 합리화**이고,
G1 이 통과했을 때 *"어차피 (B)도 할 만했다"* 도 마찬가지다.

---

## ADR-046: **전제 교체는 사후 합리화가 아니다** — 그리고 축 3 의 진짜 제약은 core-h 가 아니라 **MDS**

**일자**: 2026-08-18 | **상태**: 확정 | **근거**: engineer §R23, proposer §37
**관련**: ADR-039·045(사전등록), ADR-043(프로브 구멍), §R10.2

### ① 🔴 KNL 이 우리가 **사전등록해 둔 실패행**을 정확히 때렸다
```
PM7 s/step = 3.0 × κ  →  κ=5.1 에서 15.3 s/step
§R10.2 사전등록 표: "15 s/step ⟹ 5 ps 불가. 축 3 재설계 필요"   ← 바로 그 행
```
🟢 **그러나 그 판정은 `24 h` 상한 아래에서 쓰였고, 사이트 상한이 `48 h` 로 밝혀지면 5.65 ps ⟹ 산다.**

🔴 **여기서 규약을 하나 세운다 — 이 구분이 사전등록 제도의 존폐를 가른다:**
> **사전등록 판정을 뒤집은 것과, 그 판정이 딛고 선 *전제*가 측정으로 교체된 것은 다르다.**
> **전자는 사후 합리화이고 후자는 정상적인 갱신이다.**
> **구별 기준: 전제가 바뀌었다는 것을 *결과를 보기 전에* 독립적으로 확인할 수 있는가.**

여기서는 `24 h → 48 h` 가 **사이트 큐 속성**이지 우리 결과가 아니므로 **정상 갱신**이다.
⚠ **그러나 `48 h` 는 아직 `[LITERATURE]` 다.** `qstat -Qf normal` 확인 전까지 **이 구제는 잠정**이며,
🔴 **확인이 실패하면 §R10.2 의 원래 판정("축 3 재설계")이 되살아난다.**

### ② 🟢 축 3 이 사는 진짜 이유 — **도달범위가 로그다**
`reach = k_BT·ln(N·t/τ₀)` ⟹ **aggregate 를 10배 깎아도 0.198 eV 밖에 안 잃는다.**
🟢 **반면 온도는 선형이다: 1000→1200 K 가 +0.222 eV, 비용 0.**
⟹ **aggregate 10배 = 온도 200 K.** 이 견적에서 가장 값싼 레버다(화학적 타당성은 proposer 판정).
🔒 확정 사양: 궤적 **5 ps** 고정, `N_replica` = **3,415/계**(봉투 10%) → 도달범위 **1.038 eV**.
목표 1.112 대비 −0.074 eV 이고 **온도 1,071 K 로 정확히 되산다.**
🟢 `4,000×5ps` ≡ `2,000×10ps` 인데 **전자가 wall 절반** ⟹ **짧은 궤적 × 많은 replica 가 공짜로 우월.**

### ③ 🔴 축 3 의 실제 제약은 **core-h 가 아니라 Lustre MDS 다**
ASE↔MOPAC MD 는 **스텝마다 프로세스를 띄운다** = 소파일 폭격.
```
[MEASURED] Lustre 소파일 1,241.5 creates/s
동시 replica 6,400(100 node) → 2,092 /s = 1.7×  🔴 우리 계획 규모에서 정확히 한계에 닿는다
```
🔴 **그리고 이것은 우리 잡이 느려지는 문제가 아니다:**
> **"MDS 를 8,305 노드가 공유한다. **남의 잡을 죽이고 사이트에서 차단당하는 경로**다."**

**⟹ 이건 비용 항목이 아니라 운영 리스크이며, 우리가 통제할 의무가 있는 종류다.**
🔒 **구속(coder)**: **3중 방어 — ①노드로컬 tmpfs ②궤적당 tar 1개 ③진입점 `df` 검증**
+ **`expected_file_ops_per_s` guard 축 신설.** ⟹ 파일 연산 `4×10⁸ → 4×10³` (5자릿수 감소).
🟢 **이 위험은 축 3 에만 있다** — 동봉 xtb 의 `--md` 는 단일 프로세스가 궤적 전체를 돈다.
⟹ **MOPAC 선택의 숨은 비용으로 기록한다. core-h 가 아니라 운영 리스크다.**

### ④ 🟢 후보 B 의 왕복이 절반으로 줄었다 — 질문을 쪼갠 덕이다
proposer 가 *"파일럿 궤적 1개"* 를 물었는데 engineer 가 **그것이 두 개의 다른 파일럿**임을 밝혔다:
`s/step`(**1,000 core-h, 편승 가능**) vs `사건율 r`(**≥60,000 core-h, 불가**).
🔴 **`r` 을 DFT 로 재려는 시도를 기각하고 더 싼 대안을 짝지었다:**
> **"`r` 은 화학과 온도의 성질이지 해밀토니안의 성질이 아니다 ⟹ PM7/xtb 궤적으로 재라."**
⟹ **후보 B 발동 판정이 왕복 1회 안에 끝난다** (proposer 가 우려한 1~2회의 절반).
🔒 판정 기준: **사건율 `r ≥ 0.105 events/ps` 면 후보 B 는 예산 안.**
🟢 **교차검증**: CP2K/PM7 단가비를 engineer 240× / proposer 222× 로 **독립 도출해 일치.**

### ⑤ 🔴 프로브 구멍 또 하나 — ADR-043 과 같은 구조
**G1(KNL ISA) 게이트를 우리 회신으로 확인할 수 없다. `cluster.cpu` 에 `flags` 필드가 없다.**
`[LITERATURE]` KNL = AVX-512 **F·CD·ER·PF** / Skylake = **F·CD·DQ·BW·VL** ⟹ **공통은 F+CD 뿐**
⟹ **Skylake 타깃 빌드는 KNL 에서 SIGILL.**
🔒 **`grep ^flags /proc/cpuinfo` 를 프로브에 추가.**
> engineer: **"MOPAC 때와 똑같이, 프로브하지 않은 것은 알 수 없다."**
**ADR-043 이 정한 규약의 두 번째 적용 사례다. 규약이 새 구멍을 스스로 찾아냈다.**

### 🔴 ⑤-b 온도 보상 **기각** — `T` 는 자유 파라미터가 아니다 (proposer §37.7)
engineer 의 *"aggregate 10배를 온도 200 K 로 산다"* 를 **기각한다.** 도달범위 식은 맞다
(proposer 가 1.038 eV 를 독립 복제했다). **그러나 `T` 는 ADR-024 의 온도 사다리
(600/1000/1500 K)가 이미 배정했다.**
🟢 **같은 aggregate 에서 1500 K 단이 이미 1.42 eV 를 준다 ⟹ 목표 1.112 eV 는 애초에 구속이
아니었고, −0.074 eV 부족분은 존재하지 않는 문제다.**
🔴 **그리고 메우면 안 된다**: 1000 K 단의 존재 이유는 도달범위가 아니라 **메커니즘이 덜 왜곡된
포획**이다(1500 K 에서 해리가 회합 대비 **0.78 eV 가짜 우위**). 1,071 K 로 올리면
**유일하게 신뢰도 높은 단을 오염시킨다.**

🟢 **대신 진짜 무료 레버 — 배분.** 600 K 단은 reach 0.57 eV 로 포획을 거의 못 하고 역할이
**대조군**이다 ⟹ 균등 1/3 은 낭비. 🔒 **600/1000/1500 = 15/55/30** ⟹ 1000 K 단 reach
**0.944 → 0.987 eV.** 비용 0.

🔒 **보고 규약**: 축 3 포획은 **단별로 분해 보고**하고, **"1500 K 단에서만 잡힌 반응"은
메커니즘 왜곡 후보로 표시**한다. **표시 없이 network 에 넣으면 §20.2 경고가 그대로 실현된다.**

### 🟡 ③-b MOPAC `DRC` — 조건부 수용. **성공하면 ③의 I/O 위험이 대부분 사라진다**
`DRC` 는 **스텝당 fork 를 제거**한다 ⟹ MDS 위험의 근원을 없앤다.
proposer 판정: 실행규약이 요구하는 것은 열욕이 아니라 (A)(B)(C)이고 **초기속도를 MB 표집한
NVE 앙상블**이면 만족한다. **조건 3개:**
① **MB 표집**(🔴 DRC 기본값의 단일 모드 여기 **금지** — 그건 표집이 아니라 **유도**다)
② 에너지 표류 기록·보고 ③ 표류 시 **사후 유효온도로 단 재배정**
⚠ **DRC 가 ①을 지원하는지 `[미확인]` ⟹ U-47 확장. 미지원이면 ASE + 3중 I/O 강제.**

### ⑥ 사용자 질의 우선순위 변경 (engineer 요청 — 승인)
🔴 **`normal` walltime 상한 확인을 1번으로 올린다.**
**§R23 의 축 3 생존 · §R22 의 재실행 wall · §R21 의 P1 체인 — 셋 다 그 한 값에 걸려 있다.**

---

## ADR-047: DRC 의 `T_eff ≈ T/2` 보정 · **U-49 를 `r` 파일럿보다 앞으로** · engineer 철회 2건

**일자**: 2026-08-18 | **상태**: 확정 (🟡 축 3 물리 판정은 proposer 재소환 시 확인)
**근거**: engineer §R25, proposer §37.7 | **관련**: ADR-045·046, ADR-024(온도 사다리)

### ① engineer 철회 2건 — proposer 가 둘 다 옳았다
**(a) 온도 보상 철회.** *"aggregate 10배를 온도 200 K 로 산다 — 가장 값싼 레버"* 를 철회.
> engineer 자평: 🔴 **"봉투에서 예비비를 두 번 세는 것과 같다.** §R18.5 에서는 §R8.4 예비 용처를
> 확인하고서야 '자유 여유'를 말했던 규율을, **온도에는 적용하지 않았다."**

**(b) `r` 전이 철회 — 이번 라운드 오류 중 결과가 가장 나빴을 것.**
proposer 의 *"δ 는 포획 **여부의 상관**에 기여하지 않는다"* 를
*"δ 가 있어도 사건율 `r` 의 **값**이 코드 간 옮겨진다"* 로 넓혀 읽었다. **다른 명제다.**
⟹ **후보 B 발동 판정이 뒤집혔을 수 있다.** (ADR-045 브래킷 개정으로 이미 구제)

### ② 🔴 신규 위험 — DRC 의 `T_eff ≈ T/2` (확률적 표류가 아니라 **계통 인자**)
```
최소화 구조에서 T 로 MB 초기속도 → 전 에너지가 운동에너지
평형 후 등분배 KE:PE = 1:1  ⟹  T_eff ≈ T/2   (600→300, 1000→500, 1500→750 K)
reach ∝ T  ⟹  합집합 1.402 → 0.70 eV
```
🔴 **사다리 전체가 한 단 내려간다. (a)에서 방금 해소된 문제보다 이쪽이 크다.**

🔒 **결정 — proposer 조건 ③ 을 `표류 시` → `항상` 으로 넓힌다.**
**기구는 proposer 가 이미 설계했고(사후 유효온도로 단 재배정) 발동 조건만 넓히면 된다. 비용 0.**
🔴 **표집 온도를 2배(1200/2000/3000 K)로 올려 맞추는 안은 기각**: SCF 열화가 온도 페널티를 넘고
**3000 K 수렴성은 `[미확인]`** 이다. **평형화 후 출발이 훨씬 싸다.**
🟡 **이 보정은 안전 방향으로의 조건 확대이므로 lead 가 승인한다. 다만 축 3 착수 시
proposer 확인을 받는다** — 물리 판정 자체는 그의 영역이다.

### ③ 🔒 순서 변경 — **U-49(δ 실측)를 `r` 파일럿보다 앞으로**
ADR-045 의 브래킷은 δ 에 크게 의존한다:
| δ 실측 | 브래킷 | 폭 |
|---|---|---|
| **0.30**(현행 가정) | 0.0032 ~ 3.41 | 🔴 **1,057×** |
| **0.15** | 0.0184 ~ 0.599 | **32×** |
| 0.10 | 0.0329 ~ 0.335 | 10× |
> 🔴 **"①을 건너뛰고 ②를 하면 3 자릿수 브래킷에 던지는 것이다."**
> 🔒 **순서: ① U-49(δ, X1/X2 편승 = 비용 0) → ② `r_xtb` 파일럿 → ③ 후보 B 판정.**
**δ 없이는 `r` 을 재도 판정이 안 서는데, δ 가 있으면 `r` 측정의 값이 33배 오른다.**
⚠ engineer 자기 정정: *"§R23 의 '후보 B 판정이 왕복 1회 안에 끝난다'도 과장이었다."*

### ④ 15/55/30 은 **aggregate 비율이지 core-h 비율이 아니다**
고온 단일수록 ps 당 단가가 비싸다(§R11: 반응 사건 중 SCF 수렴 열화 +5~20%).
`[ESTIMATE]` 600K ×1.00 / 1000K ×1.15 / 1500K ×1.30 ⟹ **core-h 배수 1.173×**,
예산 고정 시 실 aggregate 17,076 → 14,564 ps, 합집합 1.402 → **1.381 eV**.
🟡 **`N_replica` 표는 ~15% 낙관.** 🟢 **그러나 reach 손실 0.02 eV 뿐(`ln` 이므로) — 판정 무영향.**
🔒 **coder 구속: `core-h 비율 = aggregate 비율 × 온도 페널티`.**

### ⑤ 🔴 engineer 자기감사 — 오류 9건과 **패턴 2개**
MOPAC 부재 / 팩킹 방향 / P3 "불일치" / crest rc≠0 / P1b=15·P1=5 / `%chk` 절감 /
P5 천장 폭발 / 온도 레버 / `r` 전이.
> **ⓐ 확인 안 한 것을 확인된 것처럼 쓴다**
> **ⓑ 이미 배정되었거나 대가가 붙은 것을 "무료"로 센다**
> 🔴 **9번(남의 논거를 내 결론에 유리하게 넓혀 읽음)은 별종이고 가장 위험하다.**

🟢 **9건 전부 왕복을 쓰기 전에 잡혔다 — teammate 직접 왕복의 값이다.**
🔴 **그러나 ⓐⓑ 는 스스로 잡았어야 했다.** engineer 가 §R17 5.5 에 두 줄을 추가했다:
① **부재·미확인은 프로브 대상 목록을 열거해 확인한 뒤에만 보고**(= ADR-043)
② **"무료 레버"라 부르기 전에 다른 요구사항에 이미 배정됐는지 확인**(= 신규)

🔒 **②를 팀 상설 규약 10번으로 승격한다.** lead 도 같은 실수를 했다 —
engineer 의 "온도 200 K 무료 레버"를 사용자에게 그대로 전달했다.

---

## ADR-048: 🔴 **`cores_observed != cores_requested` 는 판단하지 말고 버린다** — P6 는 조용히 오염된다

**일자**: 2026-08-18 | **상태**: 확정 | **근거**: engineer §R26
**관련**: ADR-036(폴백은 `null`), ADR-041, ADR-046

### 발견 — array 버그의 진짜 위험은 P5/P1b 가 아니라 **P6** 다
`plan.py:459-463` 의 **태스크당 1코어 하드코딩**이 살아 있을 때:
| | 무슨 일이 나는가 | 발견되는가 |
|---|---|---|
| P5 · P1b | 1코어 ⟹ wall **15~64배** ⟹ **즉사** | 🟢 **시끄럽다. 발견된다** |
| 🔴 **P6**(κ 앵커) | `cores = 1/16/64` 를 **의도적으로 다르게** 요청하는데 셋 다 1코어를 받는다. **G16 이 1코어 위에 16/64 스레드를 오버서브스크립션한다** | 🔴 **잡이 정상 종료하고 "16스레드"·"64스레드" 측정점이 회신에 실린다** |

🔴 **결과: `κ` 가 약 16배 틀리고 스케일링 `S` 가 무의미해진다.**
**그리고 그 `κ` 가 다음 라운드 전체의 단위가 된다** — 봉투·일정·5개월 판정이 전부 그 위에 선다.

> engineer: **"이게 이번 재검산의 진짜 산출물이다. 천장 숫자보다 이쪽이 크다 — 우리가 이 라운드
> 내내 싸운 실패 부류('데이터처럼 보이는 쓰레기')의 정점이고,
> **조용한 실패는 시끄러운 실패보다 항상 비싸다.**"*

### 🔒 결정 — 하드 게이트
> **`cores_observed`(payload 실측) != `cores_requested` 이면 그 태스크를 `[INVALID]` 로 버린다.**
> 🔴 **판단하지 말고 버린다.** 보정하거나 해석하지 않는다.

**이유**: 오버서브스크립션된 측정점은 **틀린 값이 아니라 다른 양(量)** 이다. 보정 계수를 곱해
살리려 하면 **`[MEASURED]` 라벨이 붙은 채로 오염이 전파된다**(ADR-034 계보).
**ADR-036 이 폴백값을 `null` 로 만든 것과 같은 논리** — **코드가 읽을 수 있는 형태로 무효화한다.**

🔒 **적용 범위: P6 만이 아니라 코어 수를 측정 변수로 쓰는 모든 항목.**

🔴 **알려진 약점 (critic3·coder2 공동 지적, 다음 판 수정 예정)**:
현재 게이트 면제 판정 `item_cores_are_the_measurement()` 이 **항목 키 접두사(`P6_t`)에 의존**한다.
⟹ **키 이름이 바뀌면 조용히 면제가 풀린다** — 그러면 P6 가 게이트에 걸려 측정이 통째로 날아간다.
🔒 **더 나은 표현: `Item` 에 명시적 플래그 `cores_are_measured=True`.**
⚠ **P6 항목 키를 바꾸는 사람은 이 절을 먼저 읽어라.** 지금은 키 이름이 안 바뀌므로 잠복 위험이다.


### 이 세션의 "조용한 실패" 목록 — 이것이 **여섯 번째**
| # | 무엇 | 겉보기 |
|---|---|---|
| 1 | B-3 Gaussian freq 파서 | 회신 정상, 전부 `fail` |
| 2 | 거부 메시지 400자 컷 | 메시지가 오긴 온다 |
| 3 | `host` 유실 | JSON 정상 형태 |
| 4 | CREST 부재 | **성공으로 돌아옴**, 단가 과소 |
| 5 | CP2K 데이터파일 부재 | **다른 계산을 조용히 수행** |
| 6 | 🔴 **P6 오버서브스크립션** | **정상 종료 + 그럴듯한 측정점** |
**여섯 건 모두 크래시가 없다. 그래서 테스트가 못 잡는다.**

### 부수 — engineer 가 자기 함정을 자기가 밟을 뻔했다 (오류 10번)
```
1링크 상한 CAP = cores × max_wall = 64 × 48 = 3,072
P1b 22원자 예산 3,094   ← 0.7% 초과
⟹ links 2 ⟹ 천장 6,144(예산의 1.99배) ⟹ 총 23,208 > guard 21,000 ⟹ 제출 거부
```
🔴 **역산 설계에서 `max_wall` 은 불연속 지점이고, 0.7% 초과가 천장을 100% 늘린다.**
🔒 규칙: **array 태스크 예산은 `cores × max_wall` 을 넘지 않는다. 넘으면 링크를 늘리지 말고 쪼갠다
(체이닝은 P1 전용). clamp 경계의 95% 를 넘는 값은 쓰지 마라.**
⚠ engineer 기록: **"패턴 ⓑ를 상설 규약에 올린 *직후* 같은 패턴이 또 나왔다 — 규약이 필요하다는 증거."**

🟢 **재검산 결과 두 큐 시나리오 모두 통과**(48 h·24 h 모두 총 천장 **20,136 ≤ 21,000**).
**큐가 24 h 로 밝혀져도 guard 를 다시 안 만진다.**

### 🔴 책임 귀속 정정 — engineer 가 내 관대함을 거부했다
lead 는 ADR-047 에 *"온도 레버 오류는 engineer 만의 것이 아니라 우리 둘의 오류"* 라고 적었다.
engineer 반박:
> **"원 오류는 내 것이다. **견적을 내는 쪽이 '이 레버가 이미 배정됐는가'를 확인할 책임을 진다.**
> 중계자에게 그 검증을 기대하는 설계였다면 **그게 더 나쁜 설계다.**"*

**받아들인다.** 🔴 **책임을 나누면 규칙이 약해진다.** lead 의 잘못은 *"검증 없이 전달한 것"* 이고
그것은 별개의 잘못(ADR-043 계보)이지, **원 오류의 지분이 아니다.** 두 가지를 섞지 않는다.

---

## ADR-049: 재실행 최종 범위 — **P3 제거, P7 은 게이트 뒤로.** 그리고 파생값 `[UNCHECKED]` 규약

**일자**: 2026-08-18 | **상태**: 확정 | **근거**: engineer §R27, coder2 실행 대조
**관련**: ADR-048, ADR-046(MDS), ADR-024, §R23.3(d)

### 🔒 lead 판정 ① — **P7(CP2K `s/step`)은 U-46 스모크 뒤로. 게이트 채택**
**P7 은 lead 가 "편승이니 넣어라"로 승인한 항목이다.** engineer 가 일방적으로 빼지 않고
**"게이트를 걸어라"까지만 지시하고 판단을 되돌린 것이 옳다.** 판정한다: **게이트를 건다.**

🔴 **근거는 여유(core-h)가 아니라 정확성이다.** proposer 경고:
> **"데이터 파일이 없으면 CP2K 는 죽는 게 아니라 **조용히 다른 계산을 한다.**"**

⟹ **게이트 없이 돌리면 "엉뚱한 계산의 `s/step`"을 재고, 그 값이 후보 B 판정에 들어간다.**
**ADR-048 에서 방금 정한 것과 같은 부류다** — 오염된 측정은 틀린 값이 아니라 **다른 양(量)** 이고,
`[MEASURED]` 라벨이 붙은 채 전파된다. **이 세션 "조용한 실패"의 일곱 번째가 될 뻔했다.**

### 🔒 lead 판정 ② — **P3 제거**
🔴 **P3 는 RT-1 에서 이미 `pass` 했다.** 단가(0.1004 core-h)·수렴률(31.7%)·candidate 분포를
확보했고 스레드 수 의문도 닫혔다. ⟹ **이미 측정된 것을 다시 재지 않는다.**

```
현재 20,592 (여유 1.9%)  →  P3 제거 20,092 (4.3%)  →  +P7 게이트 19,092 (9.1%)
```
🟢 **여유 문제와 정확성 문제의 해법이 같았다. 정확성이 1차 이유이고 여유는 부수다.**

### 🔒 guard 22,000 기각 — 확정 (RT-1, **KNL core-h**)
> 🔴 **UNIT WARNING added 2026-08-19 by rule 28.** Every number in this entry is **KNL core-h**.
> B0's guard is **36,000 KNL**, which is NUMERICALLY LARGER and is **NOT a raise** — it is
> `15,000 REFERENCE × κ 2.4`, and RT-1's 21,000 KNL is only 8,750 reference, i.e. **stricter**.
> **The lead read this entry against B0's figure once and reported a raise that had not happened.**
> The PRINCIPLE below (§R24.1: suspect the spec before the guard) is LIVE and unchanged. See ADR-077.
coder2 가 *"여유 1.9% 뿐이니 22,000 으로?"* 라고 물었고 engineer 가 기각했다. **지지한다.**
> **§R24.1 이 금지한 바로 그 거래다: "가드가 사양을 거부하면 가드를 올리기 전에 사양을 의심하라."**
**여유가 없다는 것은 가드를 올릴 이유가 아니라 사양을 다시 볼 이유다. 다시 보니 뺄 것이 둘 있었다.**

🔒 **여유 2% 는 결함이 아니라 기능으로 유지**하되, guard 거부 시 **어느 항목이 넘겼는지**를 출력한다 —
**반사적 반응이 "숫자를 올린다"가 아니라 "어느 항목을 의심한다"가 되도록.**
🔒 **절단 순서 사전 확약: P7 → P3 → P6 1스레드 태스크 → 그 다음은 engineer 판정.**

### 🔴 engineer 오류 11번 — 그리고 새 규약
**§R24 의 P1b 행은 "수정 전 12,288 / 수정 후 4,760" 둘 다 틀렸다**(실제 7,810 → 4,738).
- `12,288` = 자기 `min_wall_h=48` 을 적용한 값
- `4,760` = **링크 절상을 무시하고 "천장=예산"이라 적은 값**

🔴 engineer 자평: **"`ceiling = cores × clamp × links` 를 §R26 에서 내 손으로 써놓고,
§R24 에서는 그 식을 P1b 에 돌리지 않았다. 그리고 `min_wall_h=48`(P1b)은 내가 P5 에서 진단한
바로 그 병인데 같은 문서 안에서 고치지 않았다."**

🔒 **상설 규약 11번:**
> **표에 들어가는 파생값은 반드시 코드로 계산해 넣는다. 암산으로 채운 셀은 `[UNCHECKED]` 로
> 표시하고, 표시 없이 넣지 않는다.**

🟢 **근거**: 오류 10번은 engineer 가 **스크립트를 돌려** 잡았고, 11번은 coder2 가 **계획을 실행해**
잡았다. **두 번 다 "실제로 돌린 것"이 잡았다.** ADR-036·041·042 와 같은 계보다.

### 🟢 독립 수렴 1건
P1b 예산 수정값이 **coder2 의 (A) 와 engineer 의 §R26.1 이 문자 그대로 동일**하게 나왔다.
**서로 다른 경로에서 같은 값에 도달한 두 번째 사례**(앞: CP2K/PM7 단가비 240× vs 222×).

### 재실행 최종 범위 (고정)
```
P5 array(22, min_wall 0.5) · P1b array(3, 종별, 22원자 예산 3,072) · P1 체인 · P6(κ앵커)
P7 = U-46 스모크 통과 시에만 발주        P3 = 제거(RT-1 에서 측정 완료)
guard 21,000 [물리 천장] · wall 은 큐에서 판독
게이트 3개: cores 실측 일치 / links 전부 1 / Σ reserved ≤ guard
```

---

## ADR-050: 🔴 **사용자 결정 — MOPAC 배제, 도구 집합 재정의, 그리고 완결성 주장의 재구성**

**일자**: 2026-08-18 | **상태**: 확정 (사용자 직접 결정)
**관련**: 🔴 **ADR-044·045 를 부분 대체**, ADR-014, ADR-020, ADR-023

### 사용자 원문
> *"**MOPAC 은 배제**하고, **Gaussian, VASP, LAMMPS, xTB** 로 패키지를 한정해.
> 만약 정말 필요하다면 **CP2K 를 추가해도 좋아**.
> **"전수 조사했다" 란 표현을 "xx 방법론들 하에 가능한 반응을 모두 조사했다" 로 표현을
> 바꾸면 문제가 없을 듯 해.**"*

### ① 도구 집합 재정의
| | 이전 | **지금** |
|---|---|---|
| 허용 | Gaussian16 · VASP · xTB | **Gaussian16 · VASP · LAMMPS · xTB** |
| 조건부 | — | **CP2K** (*"정말 필요하다면"*) |
| 배제 | (MOPAC 동봉 예정이었음) | 🔴 **MOPAC** |

🔴 **`LAMMPS` 는 새로 열린 것이다.** 지금까지 우리 논의에 없었다.
⚠ **ReaxFF 는 사용자가 이전에 명시적으로 배제했다**(ADR-014 라운드). **LAMMPS 허용이
ReaxFF 허용을 뜻하지 않는다.** 이 구분을 흐리지 마라.

### ② 🔴 **축 3(PM7) 은 죽었다** — ADR-044·045 의 전제가 사라졌다
ADR-044 는 *"축 3 = PM7 유지, MOPAC 동봉"* 이었고 ADR-045 는 *"동봉이 G1 에서 실패하면 CP2K"* 였다.
**사용자가 MOPAC 자체를 배제했으므로 그 경로 전체가 무효다.**
🔒 **ADR-044 의 "MOPAC 동봉" · ADR-045 의 게이트 순서(①확인 →②동봉 →③G1)는 폐기한다.**
🟢 **CREST 동봉은 유효하다** — CREST 는 xTB 생태계이고 배제 대상이 아니다.

### ③ 🔴🔴 완결성 주장의 재구성 — **이것이 이 결정의 본체다**
```
이전:  "전수 조사했다"                        ← 절대적 주장. 2-source 로는 방어 불가
지금:  "xx 방법론들 하에 가능한 반응을 모두 조사했다"   ← 방법 상대적 주장
```
🔴 **ADR-045 의 딜레마가 이것으로 해소된다.** 나는 *"2-source 면 '충분히 탐색했다'를 주장할 수
없고, 그것이 사용자 제1 요구이므로 왕복 1~2회를 지불한다"* 고 판정했다.
**사용자가 요구 자체를 재정의했으므로 그 지불 근거가 사라졌다.**

⚠ **그러나 재구성이 완결성 추정을 *불필요*하게 만들지는 않는다.** 여전히 남는 질문:
> **"그 방법론들 안에서 우리는 수렴했는가?"**
이것은 여전히 포획–재포획의 대상이고, **소스 수가 줄면 종속성 추정이 어려워지는 문제는 그대로다.**
🔴 **다만 주장의 범위가 좁아졌으므로 필요한 보증 수준도 달라진다 — 그 판정은 proposer 몫이다.**

### 🔴 lead 반성
사용자는 원래 *"불가능하다면 그것 또한 내게 알려주고"* 라고 말했다.
**나는 ADR-045 에서 CP2K 사전등록을 "과학 대 달력"으로 틀 지어 혼자 판정했고, 그것이 사용자
제약과 충돌한다는 사실을 올리지 않았다.** coder2 가 가드 테스트 앞에서 멈추고
*"내가 지우면 사용자 결정을 코더가 되돌리는 것"* 이라며 올린 뒤에야 드러났다.
🔴 **사용자가 "요구사항"이라 부른 것을 내가 재해석해 트레이드오프로 만들면, 사용자는 자기 요구가
거래되고 있다는 사실 자체를 모른다.** ⟹ **제약과 충돌하는 판정은 판정 전에 올린다.**
🟢 **이번 재구성은 사용자만이 할 수 있는 종류의 해법이었다** — 우리 중 누구도
"주장의 범위를 좁힌다"는 선택지를 제시하지 못했다.

### 후속 (즉시)
1. **coder**: 허용 집합을 `{g16, vasp, lammps, xtb}` + 조건부 `cp2k` 로 갱신. 가드 테스트 2건 갱신.
   **MOPAC 프로브는 유지하되 "배제됨"으로 표시**(다시 후보로 올라오지 않게).
2. **proposer**: 🔴 **축 3 재판정** — MOPAC 없이, 재구성된 주장 아래에서 무엇이 축 3 인가.
   **LAMMPS 가 무엇을 여는가**(λ_out? 축 3? ReaxFF 는 여전히 배제).
3. **보고서 문안**: 최종 산출물의 완결성 문장을 **방법 상대형**으로 통일한다.

---

## ADR-051: 축 3 = **세우지 않는다.** estimand 가 바뀌었고, 필요한 독립성은 **다른 물리가 아니라 다른 난수**다

**일자**: 2026-08-18 | **상태**: 확정 | **근거**: proposer §38
**관련**: **ADR-044·045 최종 대체**, ADR-050, ADR-020, ADR-039, ADR-047

### ① 축 3 — 세우지 않는다. 폴백만 **사전등록**
**MOPAC 배제가 축 3 의 *실체*를 죽였고, ADR-050 의 주장 재구성이 축 3 의 *필요성*을 죽였다.
두 사건이 같은 방향이다.**

🔴 **lead 가 놓친 것**: 진짜-DFT 확률적 MD 를 우리는 **CP2K 에만** 매핑해왔는데,
**Gaussian16 에 `ADMP`/`BOMD` 가 있다** (`gaussian.com/admp` 직접 조회 — `MaxPoints`/`StepSize`
(기본 0.1 fs)/`NKE`/`FullSCF`, 반경험·HF·DFT 지원).
⟹ **허가·설치·U-46 전부 0.** 게다가 **비주기 GTO 라 CP2K 의 "하전 고립분자 Poisson 분리를
빼먹으면 조용히 틀린다"는 실패 모드가 아예 없다.**

🔒 **사전등록 발동 규칙(§38.3.4)**: E1 재발견률 `k/n`
**≥0.85 불발동 / 0.60~0.85 표적 발동 / <0.60 은 "축을 더하는 게 틀린 처방"**
(proposer 예상: 0.60~0.85 — **예상을 미리 적어 사후 합리화를 막는다**).

### ② 🔒 CP2K 철회 — 그리고 **가드 테스트는 건드리지 않는다**
사용자 조건은 *"정말 필요하다면"* 인데 **재구성 후 필요하지 않고, 필요해져도 G16 이 같은 물리를
비용 0 으로 준다.** ⟹ **P7 ↔ 가드 충돌이 닫힌다.**
🔴 **proposer 의 구분이 핵심이다:**
> **"철회는 **가드를 통과할 필요를 없애는 것**이지 **가드를 바꾸는 게** 아니다."**

**되살아날 조건(G16 게이트 실패 + 축 3 발동 지시)이 오면 lead 가 혼자 판정하지 않고 사용자에게 올린다.**

### ③ LAMMPS — 축 3 ❌, λ_out 부활 ❌. 여는 것은 정확히 둘
- **축 3 ❌**: 결합 절단 불가 / ReaxFF 배제선 유지 / 🔴 **`fix bond/react` 는 템플릿 기반이라
  축 1 과 같은 생성기** ⟹ `S_A∩S_B≈min` — **3-source 인 척하는 2-source.**
- **λ_out ❌**: ADR-038 의 철회 사유 5개를 원문에서 꺼내 판정한 결과, LAMMPS 가 해소하는 것은
  ①입력 작업량 ②빌드 부담뿐이고 **지배 사유 ③"맞춤 EC⁻ 力場이 하중부재인데 ADR-015 가
  검증장치(2k AIMD)를 삭제했다"와 ④인간시간은 엔진과 무관**하다.
  🔴 **"사전등록 규칙을 도구 가용성 변화로 고치는 것은 사전등록을 없애는 짓이다."**
- 🟢 **실제로 여는 것**: (i) 기존 두 폴백 분기의 **"사용자 설치 허가 미확보" 위험 소멸**(문구만
  갱신, 임계값 불변) (ii) **제안 L1(조건부)** — V2 의 *외부 대조군*. **U-41(문헌 Li⁺ 배위 통계
  실재 여부)이 공백으로 닫힐 때만.** P2g 생산 경로로는 ❌(조성마다 사람이 파라미터 조달 ⟹
  문헌 CN 과 똑같이 **ADR-001 이전성 위반**).
- **`lammps` 는 회신 19키에 없다 ⟹ `[NOT MEASURED]`.** 🟢 `sysprobe.py` 에 이미 있어 다음 회신에서
  자동 측정된다. **그래서 위 판정은 전부 가용성에 의존하지 않게 설계됐다.**

### ④ 🔴🔴 **estimand 가 바뀐다 — 이것이 이 절의 본체다**
```
N :  "화학적으로 가능한 모든 반응"  →  "방법론 집합 M 이 도달 가능한 반응"
```
> **"CR 은 원래 후자를 추정하는 도구였고, 전자와 같다는 것이 *추가 가정*이었다.
> ⟹ 재구성은 가정을 얹은 게 아니라 **원래 있던 가정을 제거한다.**"**

⟹ **전임의 정량화는 같은 무게를 갖지 않는다.** 세 진술이 갈린다:
| 진술 | 판정 |
|---|---|
| `df=0` (2-list 에 λ_AB 자유도 없음) | 🟢 **그대로 참** — 분할표의 산술 |
| φ=1.3 ⟹ 15%p 낙관 / 누락 2배 | 🟡 **산술 참, 적용 부분적** — φ 의 **지배 성분(공유 구조적 맹점)이 estimand 밖으로 나간다**(두 소스 다 못 보는 반응은 **정의상 `N` 의 원소가 아니다**). 난이도 이질성만 남고, **더 작다는 방향은 확정** |
| **"2-source 에서는 φ 를 추정할 방법이 없다"** | 🔴 **M-상대 estimand 에서는 거짓** |

### ⑤ 🔒 2-source 로 충분하다 — 단 장치 3개. **D1 이 축 3 을 대체한다**
**D1 — seed-split CR + rarefaction** (🔴 **비용 0 · 왕복 0 · 패키지 변경 0**)
> **"M-상대 estimand 에서 필요한 독립성은 *다른 물리*가 아니라 **다른 난수**다."**
축 2 replica 를 독립 seed 로 A/B 이분 ⟹ **독립성이 가정이 아니라 설계로 보장된 두 소스.**
**이미 돌린 궤적을 분할만 한다.** 이질성은 남지만 **Chao1 `N̂=S_obs+f₁²/(2f₂)`
(Chao 1984, Scand.J.Statist. 11:265 — 서지 확인, 본문 미확인)이 부호가 증명된 하한**을 준다
⟹ **"방향 모르는 편향"이 "방향 아는 구간"으로 바뀐다.**
⚠ 축 1(결정론적)에는 난수가 없다 ⟹ **깊이/규칙 ablation 으로 따로 재고 두 값을 합치지 마라.**

**D2 — E1 재발견률을 `Ĉ_M` 과 *같은 문단에***
🔴 **재구성의 대가다:**
> **"방법 상대적 주장은 자기참조적이라 그 자체로는 반증 불가능하다 —
> **아무것도 못 찾는 방법론도 자기 도달집합은 100% 탐색한다.**
> D2 가 유일한 탐지기다. 표를 나누면 독자는 `Ĉ_M` 만 인용한다."**

**D3 — `xx` 전량 명시 + 아래첨자 표기** (아래 ⑥)

### ⑥ 🔒 보고서 문안 — `xx` 의 답은 **"소스 이름이 아니라 소스 + 절단 하이퍼파라미터 전량"**
`M` = {(S2-A) 규칙집합 R, 생성깊이 d≤D, ΔG 컷오프, flux 임계, 열화학 레벨 ;
(S2-B/C) 상자 ~100원자, 궤적 N×t ps, 온도 사다리 600/1000/1500 K (15/55/30), seed s개}
> **"파라미터를 빼면 `M` 이 정의되지 않고, 정의되지 않은 주장은 검증 불가능하다"**
> — 도달집합은 방법만이 아니라 **절단**이 정한다(`reach ≈ k_BT·ln(N·t)`).
🔴 **`"양자화학 방법론"`·`"DFT 와 반경험적 방법"` 같은 부류명 금지** — 사실상 절대 주장으로 되돌아간다.

🔒 **`N̂` → `N̂_M`, `Ĉ` → `Ĉ_M`. 맨 기호 금지.**
> **"표 안의 맨 `N̂` 은 절대 모집단 추정치로 읽히고, **본문 한 문장의 한정어는 표가 인용될 때
> 따라가지 않는다. 한정어를 기호 안에 박는 것이 유일하게 안전하다.**"**
**해석 규약: `N̂_M` 은 하한, `Ĉ_M` 은 상한.**

### ⑦ 🔴 처방이 뒤바뀐다
**M-상대 estimand 에서는 `Ĉ_M` 이 낮을 때의 올바른 처방이
"축을 더하라"가 아니라 "표집을 더 하라"다.** 축을 더하는 것은 다른 질문의 답이다.
⟹ **축 3 의 가치가 *통계적 식별*에서 *주장 범위의 확대*로 이동한다.**
🟢 **이 재정의가 xtb-축3 기각을 더 강하게 만든다** — 도달집합을 안 넓히므로 **재구성된 주장을
강화하지도 못한다.**

### 정직한 약점 (proposer 자진 기재)
1. **E1 분해능 부족**: 성분 6종이면 **6/6 을 맞춰도** 참 재발견률 95% 단측 하한이 **0.607**
   `[CALC]`(12/12→0.779, 15/15→0.819, 20/20→0.861) ⟹ **U-50: 준거 ≥12 항목 + 반응 단위 계수**
2. **U-51 seed 독립성**: replica 초기조건이 같은 스냅샷 풀의 상관 구간에서 나오면 **D1 전체가 무너진다**
3. **U-52 G16 ADMP thermostat 미확인**: `NKE` 초기여기 ⟹ **`T_eff ≈ T_init/2`** 예상.
   🟢 **ADR-047 DRC 보정과 같은 형태이므로 기구 이식 가능**하나 **인자 실측 필요.**
   🔴 **보정 없이 쓰면 ADR-024 사다리가 한 단 어긋나고, 크래시 없이 그렇게 된다.**

### 🔴 가장 급한 구속 — **미래의 누군가에게 거는 것이다** (coder2 정정)
**발견 원장에 `seed_id`·`generation_depth` 를 기록한다. D1 의 전제이고 사후 복원 불가다.**

🔴 **lead 는 이것을 "동결 중이니 critic 판정 후에 넣어라"로 지시했다. 전제가 틀렸다.**
> coder2: **"발견 원장은 코드에 존재하지 않습니다.** ADR-027 의 산물이고 **본 파이프라인
> S1~S4 는 착수 금지** 상태입니다. 동결 때문에 못 넣는 게 아니라 **고칠 대상이 없습니다.**"

⟹ 🔴 **그래서 오히려 더 위험하다: 원장을 *처음 만드는 사람*이 놓치면 그때부터 사후 복원 불가가
발동한다. 동결이 풀려도 할 일이 없어서 그대로 흘러갈 수 있는 형태다.**
**이건 "지금 할 일"이 아니라 "미래의 누군가에게 거는 구속"이다. 그래서 ADR 에 남긴다 —
`HANDOFF` 는 coder 가 교체되면 읽히지 않을 수 있다.**

🔒 **원장을 만드는 사람에게:**
1. `seed_id` · `generation_depth` **두 필드를 반드시 남긴다**
2. 🔴 **두 값을 하나의 컬럼으로 합치지 마라** — 합치면 A/B 분할이 **축 1(결정론적) 발견을
   섞어 오염**시킨다. 축 1 에는 난수가 없다
3. 🔴 **`seed_id` 는 `sei_pilot/seeding.py::provenance(seed, …)` 의 `seed` 와 *같은 정의*여야 한다.**
   그 함수가 이미 시드·RNG 종류·변위량을 회신용으로 만들고 있고 docstring 이
   *"시드 없는 결과는 폐기 대상이다"* 라고 적고 있다.
   **두 정의가 갈리면 "같은 진실이 두 곳에" 사고가 또 난다**(이 세션에서 6회 발생)


### 열지 않기로 한 것 (기록만, `[UNRESOLVED]` 로도 안 올림)
**LAMMPS + zero-shot foundation MLIP.** 원리적으로 ADR-037 이 GPU 부재로 죽인 차선①을
CPU 추론으로 되살릴 수 있다. **열지 않는다:**
① 🔴 **사전학습 신경망 퍼텐셜은 패키지가 아니라 방법론이고, ReaxFF 선례를 보면 사용자가
방법론 수준에서 선을 긋는다 ⟹ proposer 가 판정할 사안이 아니라 사용자에게 물을 사안**
(단 proposer 는 묻자고 주장하지 않는다)
② MACE-MP-0 계열은 전하 채널이 없어 **EC 와 EC⁻ 를 구별 못 한다**
③ **새 도구가 생겼다고 설계를 다시 여는 전형**
> *"`[UNRESOLVED]` 로도 안 올렸다 — 열린 것처럼 보이면 다음 라운드에 또 판다."*

---

## ADR-052: 🟢 **`normal` = 48 h 확인, `long` 미사용** — 그리고 #2 결함은 **고치는 게 아니라 지운다**

**일자**: 2026-08-18 | **상태**: 확정 (사용자 직접 확인) | **관련**: ADR-046·048·049, §R22~§R27, critic3 #2

### 사용자 답
> *"`long` 은 존재하지만 **`normal` 이 48 h** 야. **`long` 큐는 사용하지 않을 거고 `normal` 만 사용**할 거야."*

### ① 🟢 이것이 닫는 것 — 여러 절의 `[LITERATURE]` 유보가 한 번에 해소된다
| | 상태 |
|---|---|
| §R22·§R24 재실행 wall 계산 | 🟢 **48 h 전제가 확인됨. 유효** |
| §R26 재검산 (48 h 칸) | 🟢 유효. 24 h 칸은 **불필요해짐** |
| ADR-046 ① *"48 h 는 아직 `[LITERATURE]`"* | 🟢 **해소.** 전제 교체가 정당했음이 확인됨 |
| 게이트 (b) 24 h 시나리오 / P1b 부분 실행 | 🟢 **발동하지 않음.** `[PROVISIONAL]` 유지하되 사용 안 함 |

⚠ **P1 최장 스테이지는 여전히 `[ESTIMATE]` 47.8 h(κ=6.8, 최장 45%)로 여유 0.2 h 다.**
engineer 가 *"이것을 '성립'이라 부르지 않는다"* 며 걸어둔 **사전 확약**은 그대로 살아 있다:
🔒 **최장 스테이지 실측 > 40 h ⟹ (C) 계 축소 발동.**

### ② 🔴 critic3 #2 — **배선을 고치는 게 아니라 선택 로직을 지운다**
critic 발견: `resolve_wall_limit()` 이 계산한 `queue_selected` 를 **아무도 읽지 않고**,
실제 `-q` 는 별도 정적 경로로 정해진다 ⟹ **sizing 과 제출이 다른 큐를 가정할 수 있다.**

🟢 **사용자가 `normal` 하나로 못박았으므로 그 분기가 사라진다.**
🔒 **결정: "선택된 큐가 `-q` 로 나가게 배선"이 아니라 "큐 선택 로직 자체를 제거"한다.**
```
❌ 고치기: queue_selected → 제출 스펙 배선   (안 쓰는 기능을 살리는 것)
✅ 지우기: 큐 = normal 고정.  선택 로직 삭제 ⟹ 발산할 경로가 구조적으로 사라진다
```
🔴 **다만 wall 상한은 계속 *읽는다*.** ADR-036 원칙 — **측정할 수 있는 것을 하드코딩하지 않는다.**
`normal` 의 `resources_max.walltime` 을 읽어 sizing 에 쓰고,
**48 h 가 아니면 크게 경고**한다(사용자 말과 클러스터가 다를 수 있고, 그때 알아야 한다).

**⟹ 이 결함의 올바른 처방은 배선이 아니라 삭제다. 가장 안전한 코드는 없는 코드다.**
⚠ **다른 사이트로 이식할 때 선택 로직이 필요해지면 그때 되살린다.** 되살리는 법을 주석에 남긴다.

### ③ 🔴 그러나 **#2 가 드러낸 병 자체는 유효하다**
발동 조건이 사라졌다고 해서 **"계산해놓고 아무도 안 읽는다"는 부류**가 해결된 것은 아니다.
같은 형태가 **네 건** 확인됐다(`host` / wall 상한 / P5 dual-seed / `queue_selected`).
🔒 **생산자→소비자 경계 검사는 예정대로 이번 판에 넣는다.** #2 가 우연히 무해해진 것이지
**검사가 불필요해진 것이 아니다.**

### 🟢 lead 기록
lead 는 *"`long` 큐가 0비용 1순위 해법"* 이라고 사용자에게 전달했고, **그 해법은 배선되지
않았었다.** 사용자가 `normal` 만 쓰겠다고 함으로써 **그 미배선이 무해해졌다 — 운이 좋았던 것이지
우리가 잘한 것이 아니다.** critic 이 찾지 않았으면 **24 h 사이트에서 그대로 터졌을 것이다.**

---

## ADR-053: 🟢🟢 **`n_nodes ≥ 200` 실측 — 5개월 계획이 산다.** 그리고 🔴 **진짜 제약은 바이트가 아니라 inode 다**

**일자**: 2026-08-18 | **상태**: 확정 (`[MEASURED]`, 사용자 실행)
**관련**: **§R21.2(h) 분기 판정**, ADR-046, ADR-049

### ① 🟢🟢 동시 노드 수 — **`[MEASURED — 하한] n_nodes ≥ 200`**
```
$ sed -n 's/.*"host": ...' task_*.json | sort -u | wc -l
200
```
**200 task 가 200 개의 서로 다른 노드에서 돌았다.** `normal` 이 노드 독점이라는 `[LITERATURE]` 와
일치하며, **그 순간 우리가 200 노드를 점유했다는 뜻이다.**

🔒 **engineer §R21.2(h) 표에 대입:**
| κ \ 동시노드 | 100(옛 가정) | **200** | 300 |
|---|---|---|---|
| 3.4 | 23.1주 🔴 | — | 13.9 🟢 |
| **5.1** | **29.9주 🔴** | 🟢 **19.7주** | 16.3 🟢 |
| 6.8 | 36.7주 🔴 | — | 18.6 🟢 |

⟹ **5개월(21.5주) 안쪽. 계획이 산다.**
🔴 **죽이던 것은 κ 가 아니라 `n_nodes=100` 이라는 우리 `[ASSUMPTION]` 이었다** — engineer 가
§R21 에서 정확히 그렇게 예측했고, **그 예측이 실측으로 확인됐다.**

⚠ **한정어를 지운다**: 이것은 **하한**이고 **"그 순간 점유"이지 "상시 확보"가 아니다.**
(coder2 가 `hosts_note` 에 박아둔 경고 그대로 — **그 경고가 없었으면 지금 상한으로 읽었을 것이다.**)
**할당량·큐 정책이 실제 상시 가용량을 정한다.**

### ② 🔴 새 제약 — **inode. 아무도 이 축을 보지 않았다**
```
/scratch  kbytes 217,846,408 / limit 107,374,182,400   ⟹ 용량은 0.2% 사용. 여유 100 TB
          files     778,249 / limit     1,000,000      ⟹ 🔴 **78% 소진. 여유 221,751 개**
```
🔴 **우리는 저장공간을 바이트로만 봤다**(ADR: *"scratch 가용 7,708 TB vs %Chk 1.9 TB ⟹ 위험 소멸"*).
**틀린 축을 봤다. 바이트는 0.2% 인데 inode 는 78% 다.**

**왜 위험한가**: 우리 워크로드는 **소파일 다량 생성형**이다 — pool 3,213 종 × (입력·로그·chk·fchk…),
TS 205 건, 축 2 replica 수천 개, 그리고 **파일럿 자체가 200 개 task 파일을 만들었다.**
🔴 **inode 를 다 쓰면 쓰기가 실패하고, 그건 용량 부족과 다른 오류로 나타나 진단이 늦어진다.**

🟢 **그리고 이것은 engineer 가 축 3 에서 경고한 MDS 부하와 *다른* 문제다** —
그건 *속도·남의 잡*, 이건 *우리 계정의 하드 한도*. **둘 다 소파일에서 오지만 발현이 다르다.**

🔒 **engineer 에게 넘긴다**: ① `n_nodes ≥ 200` 으로 봉투·일정 재계산
② **inode 예산을 새 축으로 추가** — 종당·잡당 파일 생성 수를 세고 221,751 안에 드는지.
③ 안 들면 **tar 묶기·중간파일 삭제·`$TMPDIR` 활용**을 사양에 넣는다(축 3 의 3중 방어와 같은 계열).

### ③ 부수 — `qstat` 답과 합치면
`normal` = 48 h 확정(ADR-052) + `n_nodes ≥ 200` ⟹ **§R22 재실행 사양의 두 전제가 모두 실측으로 확인됐다.**

---

## ADR-054: 🔴 **inode 는 18배 초과다** — 그리고 **저장 쿼터 ≠ 계산 할당**. 5개월은 여전히 조건부

**일자**: 2026-08-18 | **상태**: 확정 | **근거**: engineer §R28 | **관련**: ADR-053, ADR-046, §R22.2, §R23.4

### ① 🔴 **같은 항목이 한 축에서 1.2%, 다른 축에서 90% 다**
```
현행 파일 배치 총계  3,991,051 inode  =  여유 221,751 의 **18.0배**  =  한도 1,000,000 의 4.0배
지배항: surrogate xTB 앵커 400,000 건 × 9 = 3,600,000  ⟹ **총량의 90%**
```
🔴 **그 항목은 §R22.2 에서 "봉투의 1.22%, 비용 문제가 아니다"로 통과시킨 바로 그 항목이다.**
**core-h 축에서 1.2% 인 것이 inode 축에서 90% 다.**
⟹ **우리는 "저장은 바이트로 본다"는 축 하나만 보고 위험 소멸을 선언했다**(가용 7,708 TB vs 필요 1.9 TB).
**바이트는 0.2%, inode 는 78% 였다. 틀린 축이었다.**

계수는 코드에서 셈: **G16 실행당 8 inode**(디렉터리 포함) · **잡당 5** · xtb 실행당 9 `[ESTIMATE]`.
🟢 부수 확인: **P1/P1b/P5/P6 에 tar 반출도 `$TMPDIR` 사용도 없다**(grep 확인).

### 🟢 처방 — **새 기구 없음. §R23.4 의 3중 방어를 그대로 재사용**
①노드로컬 `$TMPDIR` ②**잡당 tar 1개 반출** ③진입점 `df -T | grep lustre` 즉시실패
④guard 에 **`expected_inodes_persistent > 150,000` 거부 축** 추가
⟹ **3,991,051 → 12,000 (여유의 5.4%, 18.5배 여유). 332배 감소, 계산비용 0.**

🔴 **④는 §R23.4 의 `expected_file_ops_per_s` 와 *별개 필드*다:**
> **속도는 MDS(남의 잡), 개수는 쿼터(우리 계정). 합치면 하나가 조용히 안 지켜진다.**

### ② 🔴 **lead 오류 — 저장 쿼터를 계산 할당으로 읽었다**
`lfs quota` 는 **저장 쿼터**이고 **계산 할당(SBU/node-h)이 아니다.** 내가 그것을 "할당량 확인"으로
사용자에게 물었다. engineer 경고: **"섞으면 ADR-043 재발이다."**

🔴 **아무도 안 적은 두 번째 봉투:**
```
과금 node-h = 수요/64 (duty 무관)
  κ=3.4 → 108,906   |   κ=5.1 → **163,359**   |   κ=6.8 → 217,812
⟹ 할당이 16만 node-h 미만이면 **동시 노드 수와 무관하게 캠페인이 성립하지 않는다.**
🔴 [NOT MEASURED]
```

### ③ 5개월 판정 — 🟡 **여전히 조건부. 조건 1개 해소, 3개 남음. 그리고 여유가 0 이 됐다**
engineer 가 전임 표를 **스크립트로 재계산**해 `κ=5.1 / 200노드 = 19.7주` 를 재현했다
(1칸 정정: `κ=3.4/300` 은 13.9 → **14.0**, 1일 차, 무해).

🔴 **그러나 19.7주는 *재계산 0회* 값이고, 그 가정은 원계획에 없었다:**
```
κ=5.1, 상시 200노드 :  재계산 0회 19.7주 🟢 | 1회 22.7주 🔴 | 2회 25.7주 🔴   (5개월 = 21.5주)
§R18.4 원계획      :  13.5 / 16.5(1회) / 19.5(2회)   ⟹ **2회까지가 계획의 여유였다**
```
⟹ **재계산 여유가 2회 → 0회.** ⚠ **우리는 이번 한 세션에 재계산급 사건을 세 번 겪었다**
(κ 오판 / array 1코어 / P1b 링크 절상).

🔒 **남은 조건 4개**: (i) `κ ≤ 5.1` (ii) `f ≥ 0.85`(상시 가용률) (iii) **할당 ≥ 163 k node-h**
(iv) **재계산 0회** — 🔴 **(iv)가 가장 약한 고리다.**
🔴 **죽이는 변수가 `n_nodes` 에서 `κ` 로 옮겨갔을 뿐이다. 재실행이 여전히 단일 임계 경로다.**
⚠ **비관 κ=6.8 이면 200노드에서도 23.1주 = 죽는다.**

### ④ 🟢 재실행 사양 — **변경 0건. 그대로 인도**
7개 항목을 두 실측(48 h, 200노드) + inode 축에 전부 대조했고 전부 유효하다.
**재실행 패키지 자체 inode ≈ 853 = 여유의 0.38%** ⟹ **새 축이 재실행을 구속하지 않는다.**

### 🔴 앵커 층의 **성립 조건**이다 — 최적화가 아니다
engineer §R28.7:
> **"'앵커를 줄여라'가 아니다. 규율 B(tar 반출) 채택이 앵커 층의 *성립 조건*이다.**
> **B 면 잡 59,133 개까지 여유, A(현행) 면 총 실행 22,175 건 상한 = 계획의 5.3% ⟹ 성립 불가."**

🔒 **⟹ tar 반출은 "하면 좋은 것"이 아니라 "안 하면 앵커 층이 없는 것"이다.**
**과학 사양(앵커 수)을 줄일 필요가 없다. 파일 배치 규율만 바꾸면 된다.**
⚠ **이것은 proposer 판정 사항이 아니라 구현 구속이다.** 다만 proposer 는 **"앵커를 줄이라는
요구가 아니다"** 를 알아야 한다 — 모르면 스코프를 자를 것이다.

### 🔒 lead 판정 — proposer 재소환은 **재실행 회신 이후로 미룬다**
engineer 가 proposer 에게 물으려던 것: *"ADR-051 로 축 3 이 빠진 자리에 무엇이 들어왔나?
D1(비용 0)만이면 수요 −6.5%(22.7 → 22.0주)가 실재한다."*

🔴 **미루는 근거는 engineer 자신의 논법이다**: *"레벨 판정은 차이 10% 인데 부족분은 80% 다.
κ 앞에서 2차항이다."*
**지금 κ 는 `[ESTIMATE] 3.4~6.8` 로 2배 스프레드이고, 그것이 19.7주와 23.1주(사망)를 가른다.**
⟹ **κ 가 2배 흔들리는 동안 6.5% 를 정밀화하는 것은 틀린 항을 최적화하는 것이다.**
🟢 **재실행이 κ 를 실측하면(P6 앵커) 그때 proposer 를 띄워 6.5% 와 함께 판정한다.**
⚠ **engineer 가 혼자 판정하지 않고 올린 것은 옳다**(패턴 ⓑ 회피). **미루는 것은 나의 판정이다.**
### 🟢 engineer 가 밟지 않은 유혹
**팩킹 `4/S` 를 여유 회복 레버로 다시 팔지 않았다** — §R22.3 이 이미 `S=4`(이득 0) 보수 가정으로
확정했고 `S` 는 **P6 가 잴 값**이다. **"그게 패턴 ⓑ 다"** 라고 스스로 적었다.
§R28.12 에 **이번 절에서 밟지 않은 유혹 6건**을 목록으로 남겼다.

---

## ADR-055: 🔒 **κ 판정 문턱 사전등록** — 그리고 **어떤 실측도 해소하지 못하는 조건이 하나 있다**

**일자**: 2026-08-18 | **상태**: 확정 (사전등록 — **데이터 도착 *전*에 고정**)
**근거**: engineer §R28 후속 | **관련**: ADR-039·045(사전등록 선례), ADR-048, ADR-054

### 🔒 입력 유효성 (ADR-048 — 판단하지 말고 버린다)
```
P6 태스크의 cores_observed != cores_requested  ⟹ [INVALID], κ·S 산출에서 제외
🔴 유효 측정점이 2개 미만이면 κ 는 "미측정"이다.
   **문헌 유도값 5.1 로 되돌아가지 않는다.**
```
🔴 **마지막 줄이 핵심이다.** 실측이 실패했을 때 조용히 `[ESTIMATE]` 로 복귀하면
**`[NOT MEASURED]` 가 `[MEASURED]` 라벨을 달고 계획에 들어간다** — ADR-034·043 의 형태.

### 🔒 판정 문턱 (상시 200노드 · **재계산 0회** 기준, §R28.2)
| κ 실측 | 주 | 판정 |
|---|---|---|
| **≤ 5.1** | ≤19.7 | 🟢 계획 유지. **단 재계산 여유는 여전히 0회** |
| **5.1 ~ 6.0** | 19.7~21.4 | 🟡 아슬. **그때 여유 회복 레버를 연다** — proposer 재소환 → 팩킹 `S` 실측 반영, **이 순서로** |
| **> 6.0** | >21.5 | 🔴 **스코프가 아니라 *창(window)* 을 다시 연다** |

🔴 **`κ > 6.0` 에서 "자르자"가 첫 반응이면 틀린 레버다.**
§R21.2(g): **절단 배수 총합 ×4.0 < κ.** *"자르는 것으로는 못 막는다"* 는 판정은 그대로 유효하다.

### 🔴 어떤 실측도 해소하지 못하는 조건 — **재계산 0회**
> engineer: *"위 문턱은 **전부 재계산 0회 값**이다. **κ 가 5.1 로 나와도 '재계산 한 번도 안 한다'가
> 남는다.** 그 조건은 실측으로 해소되지 않는다 — **창을 늘리거나 계산분을 −12% 하는 것 외엔
> 방법이 없다.**"*

🔴 **이것을 사용자에게 알린다.** 5개월 판정의 네 조건 중 **(iv) 재계산 0회만은 어떤 측정으로도
닫히지 않는다.** 원계획은 **재계산 2회를 여유로 잡고 있었고**, KNL 판명으로 그것이 0 이 됐다.
⚠ **우리는 이번 한 세션에만 재계산급 사건을 세 번 겪었다**(κ 오판 / array 1코어 / P1b 링크 절상).
⟹ **"재계산이 한 번도 없을 것"은 우리 이력과 배치되는 가정이다. 그렇게 기록한다.**

### 🔴 조건 (ii) `f ≥ 0.85` 는 **이번 재실행으로도 측정되지 않는다** (coder2 확인)
engineer 가 의심한 것이 사실로 확인됐다 `[MEASURED — 코드]`:
```
common.sh:131      … > "${SEI_JOB_DIR}/started.json"     ← `>` = truncate
pbs.sh.tmpl:26     export SEI_JOB_DIR="{{JOB_DIR}}"      ← **배열 인덱스가 안 들어간다**
⟹ P5 의 22 array 태스크가 **같은 파일을 덮어쓴다.**
🟡 `executions.jsonl` 은 append 라 22줄이 남지만 **`host` 필드가 없다**
   ⟹ "몇 번 떴나"는 세지고 **"몇 개 노드에 떴나"는 못 센다**
```
🔒 **⟹ "생산 형상(64코어·장 wall)의 동시 노드 수는 이번 재실행으로도 측정되지 않는다."**
⚠ **사용자가 실측한 `n_nodes ≥ 200` 은 1코어·1분 task 200개에서 나온 값이다.
생산 형상은 64코어·수 시간이고, 동시성이 다를 수 있다.**

### 🔒 lead 판정 — **고치지 않는다. 인도 후로 미룬다**
고치는 비용은 **한 줄**(`executions.jsonl` 에 `host` 추가, append 라 array 동시 기록에 안전)이고
coder2·engineer 둘 다 **인도 후로 미루자**고 했다. **동의한다. 그리고 근거를 하나 더 댄다:**
🔴 **P5 는 22 태스크다. 22 개로는 `f ≥ 0.85`(≈170노드 상시)를 측정할 수 없다.**
**표본이 목표 규모의 1/9 이라 그 한 줄을 넣어도 조건 (ii)는 안 닫힌다.**
⟹ **넣는 대가(critic 부분 재확인 1회)가 얻는 것보다 크다. 다음 판에 넣되 생산 형상에서 잰다.**

⚠ **그러나 조건 (ii)가 열려 있다는 사실은 지워지지 않는다.** ADR-055 의 네 조건 중
**(ii)와 (iv)가 재실행으로 닫히지 않는다** — (i)κ 와 (iii)할당만 닫힌다. **그렇게 기록한다.**

### 🟢 inode — 재실행은 안전, 생산은 다르다 (coder2 실측)
```
[MEASURED] 인도본 dry-run 후 sei_pilot_work :   6 개
[MEASURED] 패키지 추출본 자체                : 137 개 (vendor/xtb 포함)
[ESTIMATE] 재실행 1회 실행 시                : ≈ 520 개  ⟹ 여유의 0.2~0.4%
```
engineer 추정 `≈853` 과 **자릿수 동일**. 🔴 **단 재실행 1회 기준이고, 생산(pool 3,213종)은
자릿수가 다르다** — ADR-054 의 18배 초과가 그 영역이다. **두 숫자를 섞지 마라.**

### 🟡 함께 살아 있는 사전확약
**P1 최장 스테이지 실측 > 40 h ⟹ (C) 계 축소 발동** (ADR-052). 회신에 그 값이 실린다.

### 🔴 트립와이어가 **자기 존재 이유를 어겼다** (critic3, 2026-08-18)
`③ 최장 스테이지 트립와이어`를 넣은 직후 critic 이 부분 재확인에서 찾았다:
```
1. collect.py 의 res["longest_stage"]=… 한 줄을 지워도  **714건 중 0건이 깨진다**
   ⟹ collect_p1() 을 통과해 최종 결과까지 가는지 보는 **진입점 테스트가 0건**
2. exceeds_tripwire=True 가 나와도 res["warnings"] 에 **안 실린다**
   (같은 함수 세 줄 아래 degraded_reasons 는 싣는데 여기만 빠짐)
   ⟹ 발동해도 **사람이 pilots[].longest_stage 를 따로 찾아야 한다**
```
🔴 **ADR-041 이 이미 세 번 잡았던 그 구멍이, 이번엔 *그 구멍을 막으려던 장치 자신*에서 재발했다.**

⚠ **그리고 이건 가상 시나리오가 아니다**: ADR-052 기준 P1 최장 스테이지 `[ESTIMATE]` 최악 칸이
**47.8 h** 이고 트립와이어가 **40 h** 다 — **여유 0.2 h.**
**이번 제출에서 실제로 발동할 개연성이 낮지 않다.**

🔴 **⟹ lead 의 수동 의무는 아직 해제되지 않았다.**
나는 *"내 의무가 코드로 넘어갔다"* 고 적었다. **넘어가지 않았다.**
**수정이 착지하고 진입점 테스트로 검증될 때까지, 회신이 오면 내가 `breakdown` 에서 직접
최장 스테이지를 뽑아 40 h 와 대조한다.**

### 🟢 사전등록의 값
**숫자를 본 뒤에 문턱을 정하면 사후 합리화다.** ADR-039(X3 브래킷)·ADR-045(축 3 폴백)에 이어
**세 번째 사전등록**이고, engineer 가 **요청받지 않고 스스로** 했다.

---

## ADR-056: 🟢 **RT-1 재실행 패키지 인도 확정** — 그리고 🔴 **문서가 도구를 깨뜨리는 결합을 발견**

**일자**: 2026-08-18 · **판정자**: lead · **상태**: 확정

### 결정
`source_digest ca757f4cfac0d30c` 를 **인도본으로 확정**하고 사용자에게 인도한다.

```
source_digest       ca757f4cfac0d30c        (BUILD_STAMP.json, 실측)
build_stamp check   ✅ tarball 이 현재 소스와 일치
전체 스위트         Ran 718 tests … OK (skipped=8), exit 0    (실측, 24.4 s)
critic3             OK — 되돌리기 실험 [M][N] 2건으로 독립 재현
```

### 인도 직전에 나온 것 1 — 🔴 **내 문서 편집이 빌드를 막고 있었다**
압축 대비로 `05_STATE.md` 최상단에 재개 블록을 넣었더니 `**Current phase**:` 줄이 **151행**으로
밀렸다. `src/session_digest/docparse.py:99` 는 `text.splitlines()[:12]` — **앞 12줄만** 스캔한다.

```
tests/test_session_digest.py::TestAgainstRealDocs::test_real_docs_parse_sanely  → RED
make_package.sh 는 테스트 RED 면 빌드를 거부한다
```

⚠ **인도본 자체는 무결하다.** `pilot_package` 밖이라 `source_digest` 에 영향이 없다. 그러나
**다음에 무엇이든 고치면 빌드가 안 되는 상태**였다.

🔴 **하필 `digest.sh` 는 내가 "압축 후 첫 행동"으로 지정한 도구다.** 압축 직후 돌렸으면 실패했다.

**조치**: 헤더 2줄을 **복사가 아니라 이동**으로 최상단(3–4행)에 되돌렸다. 복사였으면 값이 두
곳에 사는 형태 — 우리가 여섯 번 당한 그것이 된다. 재개 블록은 최상단에 그대로 둔다.

### coder2 는 (a) 코드 수정을 권했다. 채택하지 않았다 — 근거는 범위가 아니다
coder2 의 논거는 원칙적으로 옳다: *"도구가 문서 구조에 대해 세운 가정이 틀린 것이지 문서가
잘못된 게 아니다. 문서를 도구에 맞추는 건 거꾸로다."*

그럼에도 지금 고치지 않는 이유는 **이 실패가 시끄러웠기 때문**이다.

> 🔒 **시끄러운 실패는 지금 고칠 필요가 없는 실패다.**
> `test_sanity_fails_when_convention_breaks` 는 "문서 규약이 바뀌면 **조용히 빈 다이제스트가
> 아니라** RED 로 터진다"는 목적으로 만든 검사다. 그 검사가 설계대로 작동했다.
> 우리가 여덟 번 기록한 "조용한 실패"와 **반대 부류**다.

인도 몇 시간 전에, critic 을 태우지 않고, 내가 첫 행동으로 지정한 도구를 건드리는 것은 비용
대비 나쁘다. **스캔 윈도 확장은 다음 판.**

### 대신 문서 쪽에 함정 표시 (코드 0줄, `source_digest` 불변)
`05_STATE.md` 헤더 **바로 아래**에 주석으로 박았다. 🔴 **처음엔 헤더 *위*에 넣었고, 그 순간
헤더가 11–12행으로 밀렸다** — 12행은 스캔 윈도의 마지막 줄이다. **경고문을 쓰다가 경고 대상
함정을 내가 밟았다.** 주석을 헤더 아래로 옮겨 3–4행을 회복했다.

> 🔒 **일반화**: 불변식을 **글로** 지키려 하면, 그 글 자체가 불변식을 깨는 편집이 된다.
> 표시는 지켜야 할 것 **아래**에 둔다.

### 인도 직전에 나온 것 2 — **721 vs 718 vs 710** 세 갈래 테스트 개수
```
710   낡은 백그라운드 출력   → source_digest 308884324b43a963 짜리. 낡은 스냅샷. 폐기.
718   critic3 · coder2 · 실측 스위트   → 권위값
721   digest.sh 화면 상단
```
`digest.py:152` 는 `def test_` 로 시작하는 줄을 **정적으로 센다**. 차이 3건의 정체:

```
tests/test_pbs_script_shape.py 안 def test_submit  × 3
  → 가짜 스케줄러 스텁이 구현하는 **사전검사 인터페이스 메서드** `test_submit(spec)`.
     TestCase 가 아닌 스텁 클래스 소속이라 수집되지 않는다.
721 − 3 = 718.  🟢 **누락된 테스트는 없다.**
```

🔴 **그런데 나는 이 유령을 두 번 쫓았다.** 두 번째는 `unittest --list-tests` 가 이 파이썬에
없어서 `collected: 0` 이 나왔고, **719건 전부가 "수집 안 됨"으로 찍혔다.** 하마터면 그것을
발견으로 보고할 뻔했다 — **내 실패 유형 C/D 의 재발**(측정 실패를 결함으로 읽기).

> 🔒 **규약 14 추가**: 진단 화면에 뜨는 수치가 권위값과 다르면, **먼저 그 수치의 산출식을
> 읽어라.** 두 수치를 나란히 놓고 원인을 추측하지 마라. `digest.sh` 의 "테스트 N개"는
> `grep -c 'def test_'` 이지 수집 개수가 아니다 — **과대보고하는 진단 통과값**이다.

`digest.sh` 표기를 "정적 `def test_` 개수"로 바꾸는 것도 **다음 판**.

### 🔴 그런데 개수보다 값어치가 큰 것이 나왔다 (coder2 독립 확인)
lead 와 coder2 가 **서로 다른 방법으로 독립적으로** 같은 결론에 도달했다. 그런데 coder2 쪽은
**반대 방향**을 하나 더 닫았다.

```
unittest 로더 수집          718
AST(최상위 클래스 기준)      718     ← 로더와 정확히 일치
AST(ast.walk, 중첩 포함)     721     ← digest.sh 의 계산 방식
🔴 정의됐지만 수집 안 된 것   **0건**
```

> 🔒 **개수가 안 맞을 때 가장 나쁜 설명은 "어떤 테스트가 조용히 안 돈다"이다.**
> 그게 아니라는 것을 확정한 것이 "721 의 정체" 보다 값어치가 크다.

특히 **전임 coder 가 실제로 밟았던 함정**(`HANDOFF §0.2b-4`: *같은 이름의 클래스가 앞 정의를
덮어써 새 테스트가 **한 번도 실행되지 않음***)이 **현재 트리에 없음**이 함께 확정됐다.
lead 의 조사는 "차이 3건의 정체"까지만 갔고 이 방향은 비어 있었다.

**`test_submit` 의 정체도 coder2 설명이 정확하다**: "스텁 메서드"가 아니라 **스케줄러 어댑터의
실제 API 이름**(`qsub -h` 무부작용 사전검사)이고, 가짜 어댑터가 그것을 흉내낸 것이다.
시그니처가 `(self, spec)` 이라 **수집되면 오히려 잘못이다.**

**다음 판 ⑧ 의 구체적 계산 규칙**: `ast.walk` 가 아니라 **최상위 `TestCase` 서브클래스의
메서드만** 센다. 그러면 로더 수집분과 정의상 일치한다.


### 다음 판에 올린 것 (이 ADR 에서 2건 추가)
```
+ docparse.py 스캔 윈도 확장 (또는 문서 전체에서 헤더 탐색)
+ digest.sh 의 "테스트 N개" 표기를 산출식과 일치시키기
```

---

## ADR-057: 🔴 **리뷰 범위가 코드에서 끝나 있었다** — README 정합성, 그리고 **테스트가 빌드를 죽인 사건**

**일자**: 2026-08-18 · **판정자**: lead · **상태**: 🟢 critic3 §41 **통과**. 부산물 2 는 **ADR-059 로 이관**

### 무엇이 일어났나
critic3 가 `ca757f4cfac0d30c` 에 OK 를 준 뒤, lead 가 **tarball 을 풀어 사용자가 실제로 받는
파일**을 읽었다. 코드와 어긋나 있었다.

```
                 README        동봉 코드
core-h 상한       5,000        budget.py:42  21000.0
wall 상한         24 시간       budget.py:42  48.0
총 계산량         2,694.8      ~19,000
항목표            P1/P1b/P3/P5  P1/P1b/P5/P6_t1·t16·t64 + probe 3종
```
🔴 **P3 가 살아 있었다**(ADR-049 로 삭제). 🔴 **P6 가 한 글자도 없었다** — κ 측정, 이 파일럿의
**존재 이유**다. ⟹ **인도 중단.**

### 판정 근거 — 왜 이것이 "문서 사소 오류"가 아닌가
> **사용자는 README 를 보고 계산 할당량을 신청한다.**
> "5,000 상한"을 읽으면 **신청을 4배 작게 낸다.**

**ADR-041 그대로다**: 부품은 맞고 사람이 읽는 면이 값을 떨어뜨린다. critic 이 검증한 `budget.py`,
`plan.py` 는 전부 옳았다. **옳은 부품이 틀린 사용을 낳는 경로가 열려 있었다.**

### 🔒 진짜 원인은 개인의 부주의가 아니다
```
critic3  §37~§40 에서 코드만 봤다
coder2   §33~§40 에서 코드와 테스트만 봤다
lead     인도 직전까지 tarball 을 풀어보지 않았다
```
**셋이 같은 곳을 안 봤다.** 세 사람이 독립적으로 같은 것을 놓쳤다면 그것은 부주의가 아니라
**리뷰 범위가 코드에서 끝나도록 짜여 있었다**는 뜻이다.

> 🔒 **규약 15**: 인도물 리뷰는 **소스가 아니라 사용자가 받는 산출물**에서 끝난다.
> **개인을 고치면 재발하고 범위를 고치면 안 한다.**

### 조치 (coder2, §41)
1. README 를 `budget.py`/`plan.py` 로 **실제 계획을 세워 파생**. 손으로 옮겨 적지 않음
   (64 core/node · `normal` 48 h 기준: 예상 소비 **16,679** / 예약 **19,091** / guard 21,000)
2. 🔒 `tests/test_readme_matches_code.py` (8건) — README 의 기계 검증 블록 ↔ 코드 상수 대조.
   되돌리기 [O] 코드만 변경 → FAIL 3, [P] SPEC-BLOCK 삭제 → **FAIL 5**(자기 검사 포함)
3. README 에 🔴 **"P6 를 빼지 마세요"**(빼면 나머지가 *"몇 배 단위인지 모르는 숫자"*)와
   🔴 **"`normal` 이 48 h 가 아니면 제출하지 마시고 알려 주세요"** 명시

**lead 실측 확인**: `stamp ✅ · source_digest 79624c4f182e8c14 · Ran 726 tests OK exit 0 ·
dist .stale 잔재 0 · /tmp 누수 0 · tarball 추출본에 낡은 리터럴 잔존 0`

### 🔴 부산물 1 — **테스트가 환경을 오염시켜 빌드를 죽였다** (새 부류)
```
cp: error writing '…/inputs/p5_species/…': No space left on device      /tmp 100%
원인: tests/test_account_submission.py 에 tearDown 부재 → sei_acct_* 2,130개 누적
```
🔴 **코드 결함이 아니라 테스트가 산출을 막은 형태**는 우리 기록에 없던 부류다.

**그리고 더 나쁜 것**: 빌드가 중간에 죽으면 **`dist/` 가 `.stale.*` 로 옮겨진 채 남는다** —
즉 **인도본이 제자리에 없다.** 그 상태에서 `ls dist/` 를 하면 **"아직 안 만들었나 보다"** 로
읽힌다. **실패했는데 실패로 안 보인다** — 조용한 실패의 친척(9번째).
🟢 `tearDown`+`addCleanup` 으로 고침(증가 0 확인). ⚠ `/tmp` 는 여전히 89% — 다음 판에 이름만 올림.

### 🔴 부산물 2 — **새 검사가 자기가 막으려던 형태를 한 단계 위에서 반복하는가** (critic3 판정 대기)
```
tests/test_readme_matches_code.py:36   PKG_ROOT/README_USER.cpu.md   ← 소스를 검사
사용자가 읽는 것                        tarball 안 README_USER.md     ← 복사본
```
**검사는 소스를 지키는데 인도물은 복사본이다.** 복사 단계가 깨지면 **검사는 초록인 채로
사용자는 틀린 문서를 받는다.** ⚠ **이번에 실제로 복사 도중 빌드가 죽었다 — 가정이 아니다.**

⟹ critic3 에게 **"지금 고칠 값어치가 있는가, 다음 판인가"** 를 물었다.
**현재 인도본 README 는 lead 가 직접 추출해 확인했고 맞다 — 구멍은 다음 빌드에 대한 것이다.**
그 구분을 유지해 판정하도록 명시했다.

---

## ADR-058: 🟢🟢 **계산 할당은 구속조건이 아니다** (사용자 실측) — 그러나 **κ 는 그대로 남는다**

**일자**: 2026-08-18 · **근거**: 사용자 회신 · **상태**: 확정

### 사용자 회신
> *"계산 할당 잔량은 **1오더 이상 더 많이** 남았어."*

```
필요(κ=5.1 가정)   ≥ 163,359 node-h
잔량               ≥ 1,600,000 node-h  (1오더 이상)
⟹ 여유 배수 ≥ 10×
```

### 무엇이 닫히나
🟢 **5개월 조건 중 "계산 할당" 항이 닫힌다.** 이 축은 더 이상 판정에 관여하지 않는다.
10배 여유는 κ 가 사전등록 문턱(ADR-055)의 최악값으로 나와도 뒤집히지 않는 크기다.

### 🔴 무엇이 **닫히지 않나** — 이쪽이 더 중요하다
```
κ (노드 속도 배수)     ✗ 그대로.  할당이 많아도 **노드가 느린 것은 안 빨라진다**
wall-clock / 큐 처리량  ✗ 그대로.  normal 48 h · n_nodes≥200 이 상한
inode (ADR-054)        ✗ 그대로.  18배 초과. **바이트가 아니라 개수 축이다**
```
> 🔒 **할당은 core-h 축의 제약이고, 5개월은 wall-clock 축의 제약이다. 둘은 다른 축이다.**
> core-h 가 남아돌아도 **48 h 큐와 노드 속도가 달력을 정한다.**

ADR-053 에서 `n_nodes ≥ 200` 이 확인되어 **병렬 폭**은 이미 확보됐다. 그러므로 남은 단일
지배 변수는 **κ 다** — 그리고 κ 는 P6 로만 알 수 있다. **RT-1 재실행의 값어치가 오히려 올라갔다.**

### 🔴 이것으로 방법론을 다시 열지 **않는다**
할당이 넉넉하다는 사실은 *"더 비싼 level of theory 를 감당할 수 있다"* 는 유혹을 만든다.
**지금은 그 판단을 할 수 없다.** 이유:

> **κ 를 모르면 "감당 가능"이 수치가 아니다.** κ 는 core-h 를 wall-clock 으로 바꾸는 환율이고,
> 환율을 모르는 채 "예산이 10배"라고 말하는 것은 **단위 없는 숫자**다.

⟹ `proposer` / `engineer` 재spawn 은 **κ 실측 이후**로 유지한다(ADR-054 방침 불변).
🔴 **그리고 파일럿을 키우지 않는다.** 파일럿은 예산을 쓰라고 있는 게 아니라 **질문에 답하라고**
있다. guard 21,000 유지 — §R24.1 *"가드를 올리기 전에 사양을 의심하라"*.

### 부수 확인 — 🔴 **영구히 안 도는 검사 8건** (lead 실측)
스위트의 `skipped=8` 전부가 같은 사유다.
```
tests/test_qcnames.py::TestAgainstRealPyscf  8건 전부
  skip 사유: 'pyscf 없음 — 이름 검증을 실제로 확인할 수 없다'
```
🔴 **`pyscf` 는 ADR-050 의 허용 엔진 집합(Gaussian16 / VASP / LAMMPS / xTB, 조건부 CP2K)에
없다.** ⟹ **이 8건은 여기서도 클러스터에서도 영원히 돌지 않는다.**

그 docstring 은 *"'그럴듯한 추측'을 넣지 않았는지 **실제로** 확인한다"* 고 적혀 있다.
**즉 '실제로 확인한다'는 검사가 실제로는 한 번도 확인한 적이 없다.**

⚠ **지금 인도를 막지는 않는다** — 이 검사가 지키려는 것은 기저 **이름**이고, 실제 인도 경로에서
그 이름을 판정하는 것은 pyscf 가 아니라 **Gaussian16 자신**이다(동봉 `gen` 기저 + G16 파싱).
⟹ **다음 판**: 이 8건을 (a) 삭제하거나 (b) G16 기준으로 다시 쓰거나 (c) 영구 skip 임을
명시하라. **셋 중 무엇이든, "돌 것처럼 보이는데 안 도는 상태"로 두지 마라.**

> 🔒 **규약 16**: `skip` 은 "이번엔 못 잰다"와 "영원히 못 잰다"를 구분해 적는다.
> 후자가 전자의 옷을 입고 있으면 **검사 개수가 안전감을 위조한다.**


---

## ADR-059: 🔒 **빌드 후 산출물 검증 관문** — 그리고 🔴 **lead 가 없는 노출을 있는 것으로 만들었다**

**일자**: 2026-08-18 · **판정자**: lead · **근거**: critic3 (A)(B)(C) + lead 실측 · **상태**: 구현 중

### 🔴 먼저 정정 — 내 서술이 과장이었다
lead 가 이렇게 썼다: *"이번에 실제로 복사 도중 빌드가 죽었다 — **가정이 아니다.**"*

critic3 의 정정:
> *"이번 세션의 실제 사고(disk-full)는 `make_package.sh` 의 `set -eu` 가 이미 막았다.
> '깨진 tarball 이 스탬프를 통과'한 게 아니라 **'빌드가 죽어서 아예 안 나갔다'**였다."*

lead 재확인(`make_package.sh:5` = `set -eu`, 복사 단계 전부 bare 명령):
```
cp -r 실패 → 스크립트 사망 → tar czf 도달 못 함     ⟹ 방어선이 작동한 사건이었다
```
🔴 **내가 잰 것은 "빌드가 죽었다"이고, 나는 그것을 "방어선이 뚫렸다"로 옮겨 적었다.**
**없는 노출을 있는 것으로 만든 것** — 요약을 중계하면 위양성이 생긴다는, 이미 기록된 내 유형이다.

> 🔒 **규약 17**: 위협을 보고할 때 **"관측한 사건"과 "그 사건이 뚫었다고 내가 추론한 것"을
> 분리해 적는다.** 리뷰어가 lead 의 위협 서술을 받아 적지 않고 **방어선이 이미 있는지 먼저 본 것**이
> 이번 리뷰의 최대 성과다. 그게 없었으면 **이미 막고 있는 것을 막느라 이번 판을 썼을 것이다.**

### 그럼에도 구멍은 실재한다 (좁아졌을 뿐)
```
build_stamp.py 의 tarfile 참조: 0건   ← lead 실측. tarball 을 열어 대조하는 경로가 아예 없다
남는 통과 경로: cp 가 exit 0 을 내며 부분 실패 / 향후 리팩터로 set -e 가 깨지는 경우
```
🔒 **표현을 고친다: "지금 노출돼 있다"가 아니라 "방어선이 얇다".**

### critic3 의 (A)(B)(C) — 직접 재현 위에서
**재현**: `dist/*.tar.gz` 를 임시로 옮기고 `test_build_stamp.py` 실행 → **4건 전부
`skipped 'tarball 이 없다'`**. 되돌리면 4건 `ok`. 그리고 `[1/5] 테스트(23행) < [3/5] tar(36-54행)`
순서 재확인.

**(A) 허용 불가. 🔴 그리고 교착과 무관하게 고칠 수 있다** — 이것이 이 판정의 열쇠다:
> *":12-13 주석의 교착은 **'낡은(이전 빌드) tarball 을 새 빌드 전에 검사해서 막힌다'** 는 것뿐이다.
> 우리가 요구하는 건 다른 질문이다 — **'방금 이 실행에서 새로 만든 tarball 을 검사하라.'**
> 이건 순환이 아니다.* 새 tarball 은 새 소스에서 갓 나온 것이라, 검사가 실패하면 원인은
> **패키징 단계 자체의 버그**이고 사람이 고쳐 다시 빌드하면 그만이다."

🔒 **"검사 대상이 없어서 못 고치는 교착"과 "검사 대상이 방금 생긴 뒤의 관문"은 다른 것이다.**
스크립트 주석이 기록한 교착은 전자이고, 우리가 넣는 것은 후자다. **주석을 근거로 후자를
포기하는 것은 오독이다.**

**(B) 지금 그대로면 초록 불빛뿐이다** — `_member("README_USER.md")` 를 기존 클래스에 얹으면
그 클래스가 빌드 안에서 **항상** skip 되어 파이프라인에서 **단 한 번도 실행되지 않는다.**
**(C) 지금 고쳐라** — 10~15줄, 실행시간 +1초 미만.

### 🔒 lead 판정
```
GO. 단 (1) 검사 추가 + (2) tar czf 뒤 관문 배선을 **함께** 한다.
    무엇을 검사할지(critic) + 언제 검사할지(순서) 는 함께여야 보호가 된다.
```
**[6] 실패 시 거동 = (다) 남기고 exit 1.**
🔴 **(나) `.stale` 복구는 범주적 배제**: `BUILD_STAMP.json` 이 함께 복구되면 **낡은 tarball 과
낡은 스탬프가 서로 일치**해 `build_stamp check` 가 ✅ 를 낸다 — **실패가 완전히 건강해 보인다.**
낡은 산출물 계열 중 최악의 형태다.
(가) 삭제는 *"파일이 없다 = 아직 안 만들었나 보다"* 로 오독된다.

🔒 **표시 파일에 기대지 마라 (요구사항)**: **검증 실패는 사람들이 이미 돌리는 게이트를 통해
드러나야 한다.** 표시가 존재하는 동안 `build_stamp.py check` 가 ✅ 를 내면 안 된다.
**이번 사건의 교훈이 "구조가 아니라 습관으로 막혔다"인데, 표시 파일은 다시 습관이다.**

### 🔴 범위 (못으로 박음)
```
✅ tarball 안 README_USER.md 에 code_truth()/spec_block() 재실행 + tar czf 뒤 관문
❌ per_file 전체를 tarball 과 대조 / source_digest 를 인도물에 재계산  ← **다음 판. 이름만.**
❌ 그 외 무엇도
```

### 왜 "다음 판"으로 미루지 않았나
critic3:
> *"매번 '다음 판'으로 미루는 **관성 자체가 반복된 실패 원인**이었다."*

🔴 **'다음 판 목록'이 이미 8건이고, 이번 README 사고도 거기 들어갈 뻔했다.**
**미루는 규칙이 옳다는 증거보다 미뤄서 물린 증거가 많다.**

### 오늘의 상태에 대한 정확한 문장
```
오늘 인도본이 무결한 것은 lead·critic3·coder2 가 **각각 습관적으로 스위트를 빌드 밖에서
돌렸기 때문**이고, 빌드 파이프라인이 보장한 것이 아니다.
```
🔒 **습관이 실패한다는 것은 우리가 이미 아홉 번 기록했다.**

---

## ADR-060: 🟡 **inode 여유 ≈ 200,000 확인** — 축은 **확인됐을 뿐 해소되지 않았다**

**일자**: 2026-08-18 · **근거**: 사용자 회신 · **상태**: 확정(단, 정밀값 1건 미정)

### 사용자 회신
> *"약 **20만개**의 파일 개수 여유가 남았어."*

### 🔴 이것은 **확인**이지 **해소**가 아니다
ADR-054 는 여유 `221,751`(= `lfs quota` 실측 `778,249 / 1,000,000`)을 가정하고 세워졌다.
사용자 회신은 그 가정을 **뒤집지 않고 확인한다.** 결론의 방향은 그대로이고 여유만 조금 얇아진다.

```
                       초과배수   처방 후 점유   처방 후 여유   재실행 패키지
사용자 회신 200,000      20.0x        6.0%         16.7x          0.43%
ADR-054  가정 221,751    18.0x        5.4%         18.5x          0.38%
```
🟢 **어느 값을 쓰든 §R23.4 3중 방어의 결론은 견고하다**(`3,991,051 → 12,000`, 계산비용 0).
🟢 **재실행 패키지는 여유의 0.43% 다** ⟹ **이 축이 RT-1 인도를 구속하지 않는다.** 인도 진행 가능.

### 🟡 정밀값 1건 미정 — 🔴 **드리프트로 단정하지 않는다**
`221,751` 과 *"약 20만"* 의 차이는 두 가지로 읽힌다:
```
(a) 같은 값의 반올림       — 사용자가 221,751 을 느슨하게 말한 것
(b) 실제 감소 21,751 inode — 그 사이 다른 작업이 소비한 것
```
🔴 **(b) 로 단정하면 없는 발견을 만드는 것이다**(규약 17). 지금 자료로는 구분할 수 없다.
⚠ **다만 (b) 라면 새 축이 하나 생긴다**: **inode 여유는 우리가 쓰지 않아도 줄어든다.**
5개월 캠페인 동안 여유가 단조 감소하면 계획 시점의 6.0% 가 실행 시점에는 다를 수 있다.

🔒 **⟹ engineer 재소환 시 첫 항목**: `lfs quota` 를 **다시 재서 두 시점을 비교**하고,
(a)/(b) 를 판정한 뒤 필요하면 **여유를 상수가 아니라 감소하는 양으로** 모델링하라.
**지금은 하지 않는다** — κ 앞에서 이것도 2차항이다(ADR-054 논법 그대로).

### 🔒 이것으로 사용자 미답 질문은 **0건**
```
① 계산 할당 잔량   🟢 ADR-058 — 1오더 이상 여유. 축 자체가 닫힘
② inode 여유       🟢 본 ADR — ≈200,000. 축은 열려 있으나 처방이 이미 있고 RT-1 을 구속 안 함
```

### 5개월 조건 현황 (ADR-054 §③ 갱신)
```
(i)   κ ≤ 5.1              🔴 미측정 — **P6 로만 알 수 있다. 단일 임계 경로.**
(ii)  f ≥ 0.85 (상시 가용률) 🔴 미측정 — 재실행 회신으로 부분 판정
(iii) 할당 ≥ 163k node-h    🟢 **해소** (ADR-058, 여유 ≥10×)
(iv)  재계산 0회            🔴 **가장 약한 고리.** 여유 2회 → 0회
```
🔴 **(iii) 이 닫혔다고 (iv) 가 나아지지 않는다.** 할당은 core-h 축, 재계산은 wall-clock 축이다.
**오히려 (iii) 해소로 남은 셋이 전부 wall-clock 축으로 정렬됐다 — 달력이 유일한 전선이다.**

### 🔴 그리고 inode 처방은 **본계산 착수 전 구현 구속**이다
ADR-054: *"tar 반출은 '하면 좋은 것'이 아니라 '안 하면 앵커 층이 없는 것'이다."*
```
규율 A(현행) → 총 실행 22,175 건 상한 = 계획의 5.3%  ⟹ 앵커 층 성립 불가
규율 B(tar)  → 잡 59,133 개까지 여유
```
🔒 **과학 사양(앵커 수)을 줄일 필요가 없다. 파일 배치 규율만 바꾸면 된다.**
⚠ proposer 가 이것을 모르면 **스코프를 자르려 할 것이다.** 재소환 시 **첫 문장으로** 알릴 것.

---

## ADR-061: **Build-output verification gate shipped** — and two rules about checkers that check themselves

**Date**: 2026-08-18 · **Decided by**: lead · **Status**: 🟢 **shipped.** critic3 PASS (all four items independently re-instrumented)
**Note**: first ADR written in English (user instruction, 2026-08-18 — see STATE §0-c).

### Outcome
```
source_digest 79624c4f182e8c14   UNCHANGED since §41 — every edit is outside pilot_package/
735 tests OK (skipped=8 standalone) · stamp ✅ · gate: Ran 8 tests OK · no VERIFICATION_FAILED
```
🟢 **The delivered artifact is byte-identical to the one critic3 passed in §41.** Only the build
pipeline changed.

### What was built (ADR-059 decision, implemented)
1. `make_package.sh [6/7]` — after `tar czf`, open the real tarball and re-run the assertions.
2. Test selection **by discovery, not by name** (`tests/packaged_gate.py`, AST scan for
   `tarfile.open(`). **Raises if discovery returns 0** — an empty set must not read as "nothing to do".
3. On failure: keep the tarball, write `VERIFICATION_FAILED.json`, and `build_stamp.py check`
   refuses to report ✅ while the marker exists.

🔒 Point 2 was added because naming the class in the gate would mean **every future tarball test
has to be wired in by hand, and someone eventually forgets** — the exact habit-dependence this
whole episode was about removing.

### Measured: the blind window has a size
```
standalone     Ran 735 … OK (skipped=8)     ← all 8 are pyscf (ADR-058)
build state    skipped=22                    ← tarball + .sha256 + BUILD_STAMP all moved aside
blind window   22 − 8 = 14 tests that ran ONLY outside the build
gate covers    8   (TestM2DecisionReachesTheTarball 4 + TestPackagedReadmeMatchesCode 4)
```
🔴 **Not zero.** Still skipped in build state and **not** discovered:
`TestStampRecordsContentHash` (2), `TestWrongRootIsNotReportedAsStale` (2) — they do not open
tarballs, they assert on stamp/sha256 semantics.

🟢 **Not reopened, and the reason is not schedule**: `make_package.sh:148` runs `build_stamp.py
check` at `[7/7]`, so the tool those tests exercise **does** run inside the build.
⟹ **artifact-assertion blind window = 0; tool-guard coverage remains outside the build.**
⚠ Second-order, next round, name only: *running a tool does not verify that tool's own guards.*

### 🔒 Rule 18 — decide a gate's failure direction before writing it
> *"A new gate must have its failure direction decided before it is written. A gate that falls
> toward 'pass' is worse than no gate, because it makes people believe they are covered.
> What I got by luck in §42, I put in by design in §43."* — coder2

**Earned, not theorised.** The gate's first version malfunctioned: run from the repo root,
`import context` died with `ModuleNotFoundError` and unittest reported it as **one failing test** —
so *"verification failed"* and *"verification never ran"* produced identical output.
🟢 It fell toward **fail**, so it was noticed within minutes. Had it fallen toward pass, the gate
would have been decoration from birth and nobody would have known.
🟢 Side effect: the malfunction **accidentally proved the marker path** — `check` refused ✅ and the
marker cleared itself on the next successful build. **An accident verified the check.**

### 🔒 Rule 19 — a checker that names its targets by a token it must itself contain will match itself
The **first** discovery criterion was the bare string `tarfile.open`; the code searching for that
token **contained** that token, so the checker treated itself as a target. Narrowed to
`tarfile.open(` (paren-anchored).

🔴 **Correction (critic3, verification (d))**: the shipped criterion is **not** self-matching, and
this ADR must not be read as saying it is. `TestBuildGate` references `packaged_gate.OPENS_TARBALL`
**by attribute rather than inlining the string**, so it does not trip the paren-anchored scan.
critic3 confirmed this by writing a **third, independent AST scanner from scratch** and comparing
sets — exact match, two classes. **The self-match history describes the superseded version.**
⟹ The fix removed the *property*, not just the symptom. A future reader should not go hunting for
a live bug that no longer exists.

🔴 **Second instance in this project.** Ancestor (`HANDOFF §0.2b-5`): the previous coder tested a
duplicate-checker by **duplicating the checker itself**; the override made the checker disappear,
so nothing failed at all.

**Rule 19 (final wording, extended per coder2's proposal — accepted):**
> **Before trusting any discovery set, print it and read it — and state what the set *excludes*,
> not only what it includes.**

The second half comes from coder2's own analysis of a *different* error it made in the same hour:
it computed `14 → 0` over **the set its own checker defines**, then reported that as coverage of
**the property we care about**.
> 🔒 *"In both cases I let the checker's own definition stand in for the thing I care about."*

**That is the general form of both failures**, and it is why "opens a tarball" ≠ "depends on the
built artifact" had to be said out loud.

### Lead errors this round (recorded)
1. Reported the disk-full build death as *"the defence was breached"* when `set -eu` had in fact
   caught it. **Measured "the build died", wrote "the defence failed"** (Rule 17, ADR-059).
2. Reproduced the skip behaviour by moving only `*.tar.gz` while leaving `BUILD_STAMP.json`,
   got `FAILED (failures=1, errors=1)`, and nearly reported it. `make_package.sh:17-18` moves all
   three; **the state I constructed does not occur.** Second time this day of building an
   impossible state and reading its output as a finding.
3. Scoped the gate to "README only", which left `TestM2DecisionReachesTheTarball` — the class that
   exists *because the lead once read a stale extract* — outside the gate. **coder2 followed the
   scope exactly; the scope was wrong.**

### 🔒 The unifying shape (coder2, while holding) — **a name standing in for the property**
Rules 18 and 19 are two faces of one failure, and coder2 named it after the fact:

```
"opens a tarball"              stood in for   "depends on the built artifact"   (discovery criterion)
"README only"                  stood in for   "the artifact"                    (lead's scope)
"the checker's own definition" stood in for   "the property we care about"      (the 14→0 claim)
```
> 🔒 **Three instances, one shape.** Each time, a *name* that was easy to check was substituted for
> the *property* that mattered, and the substitution was invisible because everything downstream of
> it was internally consistent.

This is ADR-041 (*"the parts are right and the assembly line drops the value"*) one level up: there,
correct components produced a wrong deliverable; here, correct checks measured a wrong set.

> 🔒 **Rule 20: when a check passes, state the property it establishes — not the name of the thing
> it ran on.** If those two sentences are not obviously the same, the gap between them is the bug.

⚠ **Note on provenance**: the lead did not detect any of the three; each was surfaced by the person
who had just made the error, unprompted, while under instruction to hold and change nothing.
**That is the behaviour that produced this round's findings** — and it is worth more than the gate.


### critic3's verification method — worth copying
It did not re-run coder2's tests and agree. It built its own instruments:
```
(a) throwaway tarball-opening class, run in BOTH polarities
    true  → Ran 9 tests OK   (auto-discovered with zero registration)
    false → FAILED, exit 1   (the whole gate process fails)
(b) stripped the [6/7] block from a COPY, confirmed `bash -n` parses, then located what catches it:
    TestBuildGate::test_gate_exists_and_runs_after_packaging inspects make_package.sh's own text
    and is part of the standard 735-test run ⟹ deleting the gate is caught WITHOUT a full build
(c) hand-wrote VERIFICATION_FAILED.json with its own reason string into a scratch dist/,
    ran build_stamp.py check against it → refuses OK, exit 1, echoes the injected reason back,
    even though everything else in that dist was internally consistent
(d) wrote a THIRD independent AST scanner from scratch; set matched exactly.
    Also triggered the zero-discovery fail-safe by monkeypatching the finder to return []
```
🔒 **(a) is the part most reviews skip.** A revert going RED only proves the test is *connected*.
Running the true case as well proves **discovery happened without registration** — which is the
actual claim. **Checking the wiring vs. checking the property — Rule 20, in practice.**

### Final state at delivery
```
source_digest  79624c4f182e8c14        (unchanged since §41 — every edit was outside pilot_package/)
suite          Ran 735 tests OK (skipped=8, all pyscf)
gate           Ran 8 tests OK
stamp          ✅   dist/ clean, no VERIFICATION_FAILED.json
sha256         a6ec544e3d3a6030d597d8b8ad8b287daf08b3949f0415c6046c91140db5c498
               ⚠ transfer checksum only — NOT an identity metric (gzip embeds mtime;
                 this changes on every rebuild). Identity is source_digest.
```

---

## ADR-062: 🔴 **RT-1 round trip 2 failed — `rstrip()` misuse truncated a module name.** And the gates held

**Date**: 2026-08-18 · **Decided by**: lead · **Evidence**: `src/dist/sei_probe_report.cpu.json` [MEASURED]
**Status**: root cause confirmed; fix in progress (coder2)

### The defect — one line
```python
sei_pilot/sysprobe.py:483    tok = tok.rstrip("(default)").strip(":,")
```
`str.rstrip("(default)")` does not remove that **suffix**; it removes any trailing character in the
**set** `{ ( d e f a u l t ) }`.
```
cluster truth  gaussian/g16.c01.linda    →  'a' stripped, 'd' stripped, 'n' stops
we produced    gaussian/g16.c01.lin      →  a module that does not exist
job result     ModuleCmd_Load.c(208):ERROR:105: Unable to locate a modulefile ...  rc=3
⟹ P1 · P1b · P5 · P6_t1/t16/t64 all failed. κ, S, TS unit cost: unmeasured.
```
🔒 **User confirmed the correct name: `gaussian/g16.c01.linda`.**

### 🔴 Why review did not catch it — it was right 10 times out of 13
Enumerated against the real `modules_raw`: **13 tokens altered, 10 altered correctly** (they
genuinely ended in `(default)` — the intended behaviour). **Only the three `gaussian/*.linda`
entries were corrupted**, and the corruption produced a **perfectly plausible module name**.

> 🔒 **A bug that is correct on the majority of its inputs and plausible on the rest is not
> detectable by reading the output.** Our review looked at the parsed list and saw a sane list.

### 🔴 The deeper failure — Rule 20 again, and this one cost the whole run
```
software.g16      = ""        (no g16 on PATH)
plan              n_skipped: 0, all 9 items scheduled as runnable
same package locally: those items SKIP
```
⟹ availability was concluded from **a name appearing in a parsed list**, never from loading the
module or finding the binary.
```
check that ran   : "a gaussian-ish string exists in modules[]"
property claimed : "G16 will run inside the job"
```
**Not the same sentence.** ADR-061's Rule 20 was written about test-set definitions two hours
earlier; here the identical shape appears in *capability detection* and converts a string bug into
a 100% science loss. **The rule generalises beyond checks — it applies to any inference from a proxy.**

### 🟢 What the gates did right (first real-incident test)
```
longest_stage.exceeds_tripwire = null
note: "no stage records — the tripwire CANNOT BE DETERMINED (not measured)"
```
**It fell toward "unknown", not toward "pass"** — Rule 18 (ADR-061) under an actual failure, not a
constructed revert. Likewise `wall_limit_verified: true` / `cores_per_node_is_login_fallback: false`
reported measured provenance rather than assumed values.
🔒 **The failure was loud, correctly attributed, and cost ~0** (jobs died in ~6 s).

### 🟢 What was measured and survives — this is not a wasted round trip
```
throughput   200 submitted / 200 accepted / 0 rejected / 200 started / 200 finished
             max concurrent 200, on 200 DISTINCT hosts; first start 53 s; all done 125 s
queue wait   1 node 60 s · 4 nodes 57 s · 16 nodes 58 s          ⟹ effectively no queueing
queue wall   normal = 48.0 h  [MEASURED, qstat -Qf]              ⟹ ADR-052 assumption CONFIRMED
cores        pbsnodes -a: 68 detected → 64 requested (not a login fallback)
vasp_std     present, 6.4.3, /home01/q656a01/local/bin/vasp_std
mopac        genuinely absent from `module avail` — ADR-043 stands, uncorrupted by this bug
```
🟢 **ADR-053's `n_nodes ≥ 200` is now [MEASURED], not inferred**, and ~60 s queue wait is strongly
favourable for the availability factor `f` (5-month condition (ii)).

### 🔴 Calendar cost — this is round trip 2 of RT-1
Round trip 1 died on an ORCA parser applied to Gaussian logs; this one on a truncated module name.
**Both were single-line defects in the layer between our code and the site, both produced
plausible-looking output, and neither was visible without the cluster.**
⚠ 5-month condition (iv) is *"zero recomputation"* with **zero margin** (ADR-054). Pilot round
trips are not production recomputation, but they consume the same calendar.
🔒 **The correct response is not to hurry — it is to stop shipping names we have never loaded.**

### Follow-ups
```
(1) suffix removal as a suffix + audit the file for other multi-char strip() misuse
(2) regression fixture from the REAL modules_raw — must contain all three .linda entries
    AND the ten legitimate (default) cases (a fixture with only c01.linda would pass a
    fix that special-cases "linda" — same class of error)
(3) availability established by loading, not by name matching
🔴 The confirmed name is TEST DATA, not a fallback. Replacing one unverified name with another
   unverified name repeats the defect.
```

---

## ADR-063: RT-1 failure was **four defects, not one** — and two of them made verification lie

**Date**: 2026-08-18 · **Decided by**: lead · **Status**: fix built (`b8375e9d18326553`), critic3 full re-verification in progress
**Amends**: ADR-062 (lead's diagnosis was correct but incomplete)

### The four defects
```
D1  rstrip("(default)") removes a CHARACTER SET, not a suffix       ← lead found this one
      gaussian/g16.c01.linda → gaussian/g16.c01.lin
      13 tokens altered, 10 of them CORRECTLY (real "(default)" suffixes)
D2  the truncated name was BAKED INTO config/env_paths.json as the default
      ⟹ the job requests the CONFIGURED name, not the parsed one
      🔴 fixing D1 alone would have left the run failing identically
D3  `module load` printed ERROR:105 and still EXITED 0 on this site
      ⟹ the fallback chain never fired; gaussian/g16.a03 — which WORKS — was never tried
D4  our own tests asserted `gaussian/g16.c01.lin` as the expected value
      ⟹ the suite was GREEN while encoding a module name that does not exist
```

### 🔴 D4 — a test that freezes our own output is not a test
`test_gaussian_module_priority.py` encoded the bug's output as ground truth. **The suite did not
merely fail to catch the defect; it actively protected it** — any correct fix would have turned
the suite red, which is the strongest possible pressure to preserve a bug.

> 🔒 **Rule 22: an expected value derived from our own code tests only that the code has not
> changed. It cannot test whether the code is right.** Regression fixtures for anything crossing
> the boundary to an external system must come from **captured external output**, verbatim.

The new fixture is copied verbatim from `cluster.modules_raw` in the real cluster reply.
🔒 coder2's reasoning, which is the point: *"hand-writing it would have encoded what we **imagine**
the cluster prints."*

### 🔴 The confirmation was laundered through the user — this one is the lead's
The bad config value was recorded as **"user-confirmed" (§30.1)**. What actually happened:
```
1. our parser truncated the module list
2. lead showed the user the PARSED list and asked which to use
3. user answered "c01.lin"           ← the only options we offered were our own corrupted output
4. we recorded the value as externally confirmed
```
> 🔒 **Rule 21: a confirmation is independent only if the value did not originate with us.**
> When asking the user to confirm a value, **state where the value came from**, so they can judge
> whether their confirmation carries information. Otherwise we ask them to sign our own errors.

⚠ The user had no way to detect this. **The failure is entirely the lead's** — the question was
posed without provenance. Contrast: the 2026-08-18 confirmation of `gaussian/g16.c01.linda` **is**
independent, because that value was read from `cluster.modules_raw`, which never passes through
our parser. **The distinction is the provenance of the value, not the confidence of the answer.**

### coder2's correction to ADR-062's Rule-20 framing — accepted
ADR-062 said availability was concluded "from a name in a list, never from loading". The data
says otherwise: at plan time the package **did** verify by loading —
`how: "module(verified)" … gaussian/g16.a03 → /apps/.../g16` — it verified using **the one name
that happened to be intact**, then the job requested the **configured** name.
```
🔴 The gap was not "we never loaded anything".
   It was "the value we verified and the value we requested were different values."
```
Same family as *"the check guards the source, the user receives the copy"* (ADR-057) and
*"'opens a tarball' vs 'depends on the artifact'"* (ADR-061). **Third instance of a name standing
in for the property.**

### Fixes accepted
```
D1  suffix removal; audit found 4 strip-with-argument sites, only this one wrong [critic verifying]
D2  config corrected to measured names: c01.linda default; b01.linda / a03.linda / a03 fallbacks
D3  success = "the binary appears and is executable"; payload WALKS the candidate list and
    records modules_tried in the reply ⟹ a wrong name now fails over to a working one
D4  fixture verbatim from cluster.modules_raw; fails on pre-fix code (ADR-042)
```
**lead verified in the shipped tarball** (not the source): default `gaussian/g16.c01.linda`,
fallbacks present; every remaining `.lin` string is a comment documenting the bug.

### ⚠ Our test suite has now aborted two builds
Temp-dir leaks (`test_pbs_script_shape` 8 incl. a module-level helper called 12×/run,
`test_gaussian_module_priority` 1, `test_g16_adapter` 1) filled `/tmp` → `cp` failed → build
aborted → `dist/` left in `.stale.*`. Fixed via `addCleanup` + a single temp root with `atexit`;
measured before == after.
🔴 **"Disk-space preflight in make_package.sh" is no longer hypothetical. Priority raised.**

### 🟢 What held
`longest_stage.exceeds_tripwire` returned **`null`, not a pass**, under a live failure — Rule 18
(ADR-061) tested by an actual incident rather than a constructed revert, and it behaved as designed.

### 🔴 Second revert-experiment trap — **an invalid experiment that PASSED** (coder2, self-reported)
Asked to prove the fix is not `linda`-specific, coder2 first injected an early `return` for names
ending in `linda` **on top of the corrected logic**. The general path underneath was still correct,
so the suite passed.
```
it would have concluded: "my tests are too weak"
the truth was:           "my experiment was not the thing I claimed to be testing"
```
Redone faithfully (**the old `rstrip`** plus a `linda` exception) it fails 3 tests.

> 🔒 **Rule 23: an experiment that does not reproduce the hypothesis proves nothing — in either
> direction. A passing revert is not evidence that the tests are weak.**

**Two distinct revert traps are now on record**, and both produced a green suite that looked like
information:
```
ADR-042  partial revert    — reverted less than the fix, so the残 fix kept the suite green
ADR-063  infidelity revert — reverted something OTHER than the hypothesis, suite green
```
🔒 The common form: **a green suite is only information if you can state exactly what was broken
to produce it.**

### Fixture generalised — the name is test data, not the answer
`TestFixIsNotLindaSpecific` requires that names built from the old `{( d e f a u l t )}` charset
survive: `tool.ault`, `tool.fated`, `tool.deft`, `tool.ude`, `x.lua`, `x.el`.
🔒 **`linda` was one instance of a class**; a fix (or a test) that special-cases it would leave the
class open. coder2 also recomputed the "ten legitimate `(default)` tokens" count independently
rather than accepting the lead's figure — it reconciles: **10 legitimate + 3 corrupted = 13 altered.**

### Residual named, deliberately not fixed
Plan-time module verification still runs on the **login node**; a module that loads there but not on
a compute node still reaches submission. **The job-side candidate walk catches it at ~6 s instead of
a wasted queue slot.** 🔒 Accepted as named rather than fixed — recording it so it is not
rediscovered as a defect.

### critic3 verdict: PASS — with two corrections to our own record
Neither changes the shipping decision; both were found because this round's stated standard was
*"stating precisely what is and is not true matters more than the finding"*, applied to us.

```
audit count      claimed 4 live strip-with-argument sites   actual 5
                 omitted criteria/g16.py:185  line.strip().lstrip("#")
                 🟢 safety conclusion unchanged (single-char, same reasoning as rstrip("*") ×2)
pre-fix failures claimed 2                                  actual 5
                 only 2 are the .linda assertions; 3 come from TestFixIsNotLindaSpecific
                 and test_helper_removes_suffix_not_character_set
test count       lead's GO quoted 740                       actual 743
                 🔴 the stale number was the LEAD's: GO was sent from coder2's first
                 self-report and never updated after the fixture grew by 3 tests
```

### 🔒 Rule 24 — a revert result has a shelf life
critic3's reading of the "2 vs 5" gap: the revert ran **before** `TestFixIsNotLindaSpecific` was
added at the lead's request, and was never re-run against the grown file.
> **A revert result is evidence about the file as it stood when it ran. Nothing was wrong when
> measured; it went stale when the file grew. Re-run reverts after the test file changes.**

**Third stale-measurement shape on record**, after ADR-042(b)/(c). 🟢 Direction matters here:
the fixture is a **stronger** guard than reported, not weaker.

### How critic3 verified D3 — real instruments, not mocks
```
built actual PATH shims for `module` and `g16` reproducing the site behaviour
  (three bad candidates print ERROR:105 and exit 0; only g16.a03 makes the binary appear)
then ran `source qc_adapter.sh; sei_qc_detect` for real:
  SEI_QC_MODULE_TRIED  all four candidates walked, in order
  SEI_QC_MODULE        lands on gaussian/g16.a03 — the one that actually worked
  SEI_QC               gaussian16
```
🔒 **D3 confirmed end to end.** This is the defect that would otherwise have burned a second queue slot.

### D4 sweep — one acted on, one accepted as named
```
ACTED   test_gaussian_module_priority.py:286
        """사용자 확정값 `gaussian/g16.c01.lin` 이 설정 한 곳에서 오는가."""
        🔴 carries BOTH the truncated name AND the laundering claim, three lines above
           assertions that now correctly test .linda — Rule 21 preserved verbatim inside
           the very file that caused the incident. Doc-only fix, outside source_digest.
NAMED   test_g16_adapter.py LOG_* fixtures — expected values rest on our own understanding
        of the G16 log format with no instance to check against (D4's structural shape).
        🟢 Already self-acknowledged in the file's docstring with a named mitigation
           (route smoke on the real cluster) ⟹ a tracked risk, not a new finding.
           Next-round list.
```

### 🟢 Laundering sweep — no second instance
critic3 checked every config field recorded as confirmed:
```
sizing.json core-count map · accounts.json 4 mappings
   → quote the USER'S OWN STATEMENTS ABOUT THEIR OWN SYSTEMS.
     The value did not originate with us ⟹ the confirmation carries information. Clean.
qc_levels.json "lead 확정" entries
   → methodology decisions, a different category, not subject to this risk.
```
🔒 **This is the operational form of Rule 21**: the test is not *"did the user say yes"* but
*"where did the value come from before we showed it to them"*.

### Temp-dir leak — verified beyond the three named files
Each of the three individually 0→0; then a whole-`/tmp` census of every `sei_*` entry across the
full 743-test standalone run: **5→5, net zero.**

### 🔒 Rule 25 — a snapshot taken mid-experiment carries the experiment
coder2 self-reported, unprompted, **after** the lead had already verified and delivered:
```
backup taken MID-experiment ⟹ the backup contained an injected defect
restore from it ⟹ the contaminated version came back
caught because the digest read ea34633d… instead of b8375e9d…
```
> **Restore points must be taken before the first mutation, or they restore the defect.**

🔴 **The second half is sharper than the first:**
> *"The digest is what caught it. **If I had judged by 'the tests pass' I would have shipped the
> contaminated file**" — the three failures it caused were inside the file I was mid-way through
> editing."*

**The suite could not see the damage because the damage was inside the file whose expectations
were themselves being edited.** The identity metric sits outside that loop, so it could.
🔒 **This is the argument for having an identity metric at all — now demonstrated rather than asserted.**

**coder2's refinement, which is the generalisable half — *not diligence, a metric*:**
> *"I did not notice the contamination by being careful; I noticed because `ea34633d…` ≠
> `b8375e9d…` on a line I run reflexively. Had the digest not existed, the suite would have told me
> '3 failures in the file you are editing' and I would have kept editing."*

🔒 **The identity metric must live outside the loop being edited.** A check that shares a fate with
the thing it checks cannot report on it — the suite's expectations were inside the contaminated
file, so the suite's silence was structural, not negligent.
🔒 And the corresponding discipline: **run the identity check reflexively, not when suspicious.**
It caught this because it was habitual, at a moment when nobody suspected anything.

And the disposition to keep:
> *"I could not fully reconstruct the ordering afterwards, and I am not going to pretend I could.
> The end state is verified by measurement, not by narrative."*

🔒 **Do not reconstruct sequences you did not record.** A verified end state beats a plausible
story about how it was reached.

**lead re-verified after this report** — `stamp ✅ · b8375e9d18326553 · 743 OK · sha256 45a693a9…
matching the sidecar · AST confirms zero `linda` in the executable body of `strip_module_markers`
and `parse_module_avail`.` **Nothing delivered needed retracting** — but that is known only because
the tree was measured again. **The report arrived after the lead's verification and after delivery**;
reporting it closed the exact window this team has been burned in repeatedly.

### 🔒 Corollary to Rule 24 — say which revert produced the number
The "2 vs 5" gap had **two** independent causes, not one:
```
the test file grew after the measurement                    (Rule 24)
the rerun reverted only the CALL SITE, leaving the helper   ⟹ 2
full pre-fix (helper body AND call site)                    ⟹ 5   ← the honest figure
```
> **State which revert produced the number. "Pre-fix" is ambiguous whenever a fix touches more
> than one site.**

### 🔒 The honest limit of a mock — why the shim had to exist
coder2, on critic3's instruments:
> *"my tests would have accepted a fix that only handled non-zero exits."*

**A mock encodes the failure mode you already imagined.** `module load` printing `ERROR:105` **and
exiting 0** is not a failure mode anyone imagines — it had to be **observed on the site**, then
reproduced with a real PATH shim. 🔒 Recorded in `HANDOFF §0` so the shim is not later "simplified"
back into a Python mock.

---

## ADR-064: 🟢🟢 **RT-1 SUCCEEDED — κ = 1.207 [MEASURED].** The estimate was pessimistic by ~4×

**Date**: 2026-08-19 · **Evidence**: `cpu_machine_pilot_results/sei_probe_report.cpu.json` · **Status**: confirmed

### The number that was blocking everything
```
P6_t1    1 thread   1836 s      cores_observed 1   valid
P6_t16  16 threads   214 s      cores_observed 16  valid     ref 177.3 s (Ryzen 7800X3D, RT-1c)
P6_t64  64 threads   138 s      cores_observed 64  valid
────────────────────────────────────────────────────────────
κ = 1.207          prior [ESTIMATE] 3.4 / 5.1 / 6.8  ⟹ **base estimate was 4.2× pessimistic**
S = 1.551 (16→64)  production packing gain 4/S = 2.58
```
🟢 **Every core-h in `03_COMPUTE_PLAN.md` carried the label "a number whose unit we do not know".
That label is now removed.**

### 🔴 Unresolved normalisation — engineer's first task, do not skip it
**User-confirmed 2026-08-19: the node has 68 physical cores and we request 64. No SMT in our count.**
```
KNL    16 threads = 16 PHYSICAL cores
Ryzen 7800X3D  16 threads = 8 physical cores (SMT2)
⟹ κ = 1.207 compares equal THREAD counts over unequal PHYSICAL core counts
⟹ per physical core, KNL is ~2.4× slower
```
🔒 **Which convention the budgets were derived in decides whether the conversion factor is 1.207
or ~2.4.** Both are far better than 5.1, so no decision flips — but **the number must not be
applied before the convention is fixed.** 🔴 This is precisely the class of result that looks like
good news and is measured in the wrong units; it is flagged rather than used.

⚠ Report's own caveat, preserved: *"[MEASURED — this system, this job type]. Do not generalise to
other workloads. Does not apply to codes other than G16."*

### 🟢 U-27 closed as a by-product — λ_out without MD survives
```
G16 NonEq + SMD:  nonequilibrium_supported true · smd_worked true · iefpcm_fallback_needed false
```
**ADR-038/039 (obtain λ_out with no MD) depended on this and it holds.**

### 🟡 P1b — two different ratios, and only one of them is ours
```
cost_ratio_unweighted_mean = 4.068   (level2/level1, full stages)  ← engineer's line: ≤3.5 in budget
r_composite = 1.142 (hco3) · 1.0365 (li_ec2) · 1.3004 (li_ec_cation)  ← 🟢 THE NUMBER WE USE
              true range 1.0365–1.30, mean ≈ 1.16
              🔴 CORRECTION 2026-08-19: this ADR originally wrote "1.04–1.14", omitting the
              third species. The lead had all three values on screen and narrowed the range by
              omission, then reported "composite is very nearly free" to the user on that basis.
              Caught by engineer5 while re-checking the raw JSON rather than citing this text.
              🔒 No judgement flips (1.16 mean is still cheap), but the top of the range is 30%,
              not 14%. **A range narrowed by omission propagates silently — engineer5 had already
              repeated it once before checking the source.**
gen_penalty = 1.0                                                   ← gen basis route costs nothing
r_high = 1.5284 (hco3)
```
🔒 **ADR-032 adopted composite, so the governing figure is `r_composite` ≈ 1.04–1.14 — composite is
very nearly free.** Reading 4.068 as "over budget" would be applying the ratio of a path we chose
not to take. **Two numbers named similarly, one relevant: exactly the substitution this project
keeps making.**
⚠ `double_execution` warning: 13 stages ran ≥2× and were overwritten in the same job dir
(`li_ec2_cation_A` = 282.7 core-h = 76 % of P1b). Reported values are the LAST run. Next round.

### 🔴 P1 — failed, and the failure is chemical rather than infrastructural
```
302.4 core-h · wall 4.74 h    (ts_qst2 220.8 · irc_reverse 56.2 · irc_forward 25.4)
imaginary frequencies: exactly 1, at −105 cm⁻¹        ✅ a TS converged
IRC: both directions fell to the SAME minimum → verdict "same", rule R3
```
🔴 **−105 cm⁻¹ sits on the window edge (−100).** A mode that soft is usually a hindered rotation or
a shallow saddle, not a reaction coordinate — **consistent with the IRC result.** QST2 converged to
a saddle that is not the ring-opening TS.
🟢 **The cost datum survives**: one TS attempt = 302 core-h. ⚠ But it is the cost of a **failed**
attempt; a successful path may differ, and the retry cost is not yet known.
🔒 **This is a proposer question, not a coder one** — QST2 endpoints/guess, or IRC step count.

### 🔴 P5 — empty, cause not established
`14 species requested / 0 converged / 41 s wall / 0 stages executed`. The user deleted a stuck array
job (reported as `sei_P1b`, but P1b passed and P5 is empty), so the most likely explanation is that
the deleted array was P5. **Not confirmed. Recorded as unknown rather than assumed.**

### Cost and infrastructure
```
consumed 671.7 core-h of 19,091 reserved  (3.5 %)
throughput 200/200 accepted·started·finished, 0 rejected, 200 distinct hosts
queue wait 88–107 s at 1/4/16 nodes
tripwire   exceeds_tripwire = false, longest stage 3.45 h ≪ 40 h   [lead obligation discharged]
```

### 🔒 Consequence — the three standing prohibitions are lifted
```
"no pipeline implementation — U-05 open, axis 3 pending the pilot"
    → U-05 closed (ADR-027) · axis 3 settled (ADR-051) · pilot complete   ⟹ LIFTED
"no further methodology refinement — diminishing returns while unit costs are [ESTIMATE]"
    → unit costs are now [MEASURED]                                        ⟹ LIFTED
```
🔴 **The critical path is no longer a measurement. It is the S2 pool build.**

---

## ADR-065: 🔴🔴 **Three pilot readings in ADR-064 were wrong. The raw JSON disproves them and the summaries do not.**

**Date**: 2026-08-19 · **Found by**: proposer5 (§39.1), independently verified by the lead in the raw JSON
**Amends**: ADR-064 · **Status**: confirmed

### The field no summary consults
`pilots[P1b].rt1b.raw_steps` carries `converged` per step. It appears in no summary, in no
`criteria` block, and not in `status`.
```
opt+freq attempted            6   (3 species × 2 levels)
opt+freq CONVERGED            3
species with BOTH levels converged   1 — hco3_anion, 5 atoms, NO LITHIUM
Li-containing opt+freq converged     1 of 4
li_ec2_cation = Li⁺(EC)₂      converged at NEITHER level; 282.7 core-h, error_termination
```

### Correction 1 — `r_composite`. **The planning assumption was right all along.**
```
hco3_anion    (3.129+0.444)/3.129 = 1.142   both terms converged            VALID
li_ec_cation  (5.031+1.511)/5.031 = 1.300   A converged, C converged        VALID
li_ec2_cation (282.7+10.33)/282.7 = 1.036   🔴 denominator DID NOT CONVERGE  VOID
```
🔴 **Any ratio `(base+increment)/base` is driven toward 1 by inflating the base, and an optimiser
that never converges inflates it without bound. `1.0365` measures how long the optimiser spun
before the wall clock stopped it.**
```
DEFENSIBLE: r_composite = 1.14 – 1.30  (n = 2).    ADR-032 planned on 1.25.
⟹ Composite is NOT "nearly free". It costs what we budgeted.
```
🔴 **The lead reported "composite is very nearly free" to the user, twice.** First from a range
narrowed by omission (1.04–1.14, dropping 1.3004); then, after correcting that, from a range that
still contained the void point (1.0365–1.30). **Both corrections were made from the summary rather
than the raw steps.** The error survived one correction because the correction used the same source.

### Correction 2 — `r_high = 0.3816` is not merely unphysical, it is void
`li_ec_cation_B_high_optfreq`: 1.92 core-h, `converged: false`, `error_termination`. The numerator
is the cost of a failure. **The only valid `r_high` in the pilot is 1.5284, on a 5-atom anion.**
⚠ And `missing: []` was published for that species, because `missing` keys on **whether a cost
number exists**, not on whether the run succeeded.

### Correction 3 — 🔴 **P1's verdict is an artifact. The IRC never ran.**
```
n_frames_forward = 1        n_frames_reverse = 1
barrier_fwd_eV  = null      barrier_rev_eV  = null
hash_c_forward == hash_c_reverse        9 covalent bonds == 9 covalent bonds
```
**One frame per direction. The single frame IS the starting structure — the transition state.**
Rule R3 ("both directions fell to the same minimum") was applied to **two copies of the TS**.
A ring-opened product has one fewer covalent bond; neither endpoint is ring-opened.

🔒 **And the endpoint machinery worked perfectly, including its own ±0.2 Å threshold-sensitivity
check, which reported `flips: 0, threshold_sensitive: false` — robustness of a comparison of a
structure with itself.**

> 🔴 **Rule 20 in its purest form.** The check was *"the two endpoint geometries are isomorphic"*.
> The property claimed was *"both directions of the path lead to the same minimum"*. The gap is
> **whether the IRC produced a path at all** — and `n_frames`, `normal_termination` and the
> energies were all sitting in the returned report.

**The lead reported to the user that P1 was "a failure that makes scientific sense — QST2 converged
to a shallow saddle". That reading was itself an artifact of the same gap.** The correct verdict is
`indeterminate`, not `fail`.

### 🔴 The finding worth more than the three corrections — **every failure involved Li⁺**
`Li⁺(EC)₂`, 21 atoms, burned 283 core-h without converging: **56× a 12-atom species, which no size
scaling explains.** The physical reading is a floppy Li⁺–carbonate coordination manifold plus SMD —
a nearly flat surface the optimiser wanders.
```
ADR-027 D-5   puts Li⁺(EC)₃(PF6⁻)-type complexes in the pool as our representation of 3-body chemistry
ADR-029/032   build the entire S1 ladder on Li⁺(solvent)ₙ clusters
⟹ THE SPECIES CLASS THE DESIGN LEANS ON IS THE CLASS THAT DID NOT CONVERGE.
```
🔴 New **U-55**. Blocks pool sizing, the S1 ladder, and ADR-027 D-5. Must be measured before the
pool is sized — it is `B1-D`, the first item of the launch batch.

### What is NOT affected
🟢 **κ, S, `gen_penalty`, throughput, queue timings, U-27 are direct measurements and stand.**
It is specifically the quantities produced **by dividing one calculation by another** that are
contaminated — **because division is where a failure hides.**

### 🔒 Blocking coder constraints (proposer5 §39.12, adopted)
```
1. A derived quantity must be `null`, never a number, when ANY input step has converged == false.
2. No chemical verdict from an IRC unless BOTH directions terminated normally with ≥5 points and
   >0.05 eV of descent. Otherwise `indeterminate`, NEVER `fail`.
   🔴 "The TS is wrong" and "the IRC did not run" must not share an exit code — they have
   identical symptoms and opposite prescriptions.
```

### 🔒 The meta-finding
`status: pass` was returned for P1b because `criteria` contains only `scf_converged_level1/2` and
`diffuse_scf_pathology`. **The SCF converged inside individual steps of optimisations that then
failed.** This is `cores_observed` one layer up: **the check ran, the property did not hold, and
the disproof was in the returned JSON in a field no summary reads.**

---

## ADR-066: 🔴 **P1's root cause found at ZERO cost — the QST2 endpoints were never optimised.** And P1 is not evidence against QST2.

**Date**: 2026-08-19 · **Found by**: proposer5 §39.4(g), reading two 11-line text files in the
delivered package · **Verified independently by the lead, every claim** · **Status**: confirmed

### The inputs were in our own package the whole time
`src/pilot_package/inputs/li_ec_radical_{reactant,product}.xyz` — **not on the cluster.** The
zero-cost diagnostic was available before the 302 core-h run and after it.
```
line 2 of both files:  "GUESS GEOMETRY (idealized, not optimized)."     ← written in English
```

**Lead-verified, every number:**
```
planarity     all 7 heavy atoms z = 0.000000 in BOTH files; the 4 H at ±0.880/±0.850
              🔴 CORRECTED 2026-08-19 (ADR-100). This read "all 11 HEAVY atoms" — 11 is the
              TOTAL atom count wearing the word "heavy". Measured: C3 H4 Li O3 = 11 total,
              7 heavy. The two halves of the original line contradicted each other, since it
              also placed 4 H at ±0.880. 🟢 NO CONCLUSION CHANGES — every heavy atom IS at
              z=0, so Cs-planar-by-construction, ADR-066/067/080 all stand.
              ⟹ both endpoints are Cs-planar BY CONSTRUCTION
ring bonds    C1-O2 1.399 · C1-O5 1.399 · O2-C3 1.400 · C4-O5 1.400 · C3-C4 1.398
              🔴 five bonds drawn equal. A real cyclic carbonate has C(sp²)-O 1.33-1.36,
                 O-CH2 1.44-1.46, C-C 1.52. No such molecule exists.
C-H           all four = 1.062 Å
Li            (0, 4.24, 0) in BOTH — byte-identical. 1.85 Å from the carbonyl O in both.
              🔴 Li⁺ was not permitted to move, when Li⁺ migration to the nascent alkoxide is
                 very likely PART of the true coordinate.
product       = reactant with atom 3 (and its two H's) translated. The other eight coordinates
              are byte-identical ⟹ the carbonate fragment does not respond to ring opening at all.
d(O2-C3)      1.400 (closed) → 3.088 (open). Exactly one bond differs — the intended coordinate.
```

### One cause explains everything observed
QST2's premise is that its endpoints are **optimised minima**. It was handed two non-stationary
planar structures differing by a rigid CH₂ translation, so it optimised toward the saddle of an
**artificial rigid path**.
```
· a rigid-fragment saddle has small curvature   ⟹  −105 cm⁻¹ is exactly what that looks like
· two Cs endpoints give a Cs path, and a stationary point inside a symmetric subspace routinely
  has exactly one imaginary mode that is the SYMMETRY-BREAKING out-of-plane mode rather than the
  reaction coordinate  ⟹  a textbook way to produce precisely what our gate asks for
· a low-curvature mode makes the first IRC step fall below the path-gradient threshold
  ⟹  the 2-point forward termination and the reverse l123 crash
```
🔒 **No window threshold and no IRC setting would have rescued this.**

### 🔴 The correction that matters most — **P1 is not evidence against QST2**
It was never given QST2's preconditions. proposer5 had been letting P1's failure colour its
preference for the relaxed-scan route and **withdrew that colouring unprompted**:
> *"My preference for the relaxed-scan route stands on its own arguments — but it must not be
> justified by P1's failure, and I had let that colouring in. Correcting it is the difference
> between a bake-off and a formality."*

⟹ **U-56 is sharper, not resolved: the TS success rate is not "0 of 1". It is UNMEASURED**, because
the single attempt ran outside the method's stated preconditions and counts in neither direction.
🔒 **No S3 production may start until a TS search has succeeded once under conditions we control.**

### proposer5's own error, left visible with the correction attached
It wrote that both IRC endpoints having 9 covalent bonds meant "neither is ring-opened". **Backwards
— 9 is the OPENED count, 10 the closed.** §39.4(a)'s conclusion is untouched (the 80 µeV descent,
the 2 forward points and the l123 termination each independently establish the IRC never left the
saddle). 🟢 **But the correction produced a finding the misreading had hidden:**
> **For a late TS the covalent graph cannot distinguish the TS from its own forward product.**
> A matching forward hash can therefore *never* confirm the forward IRC moved — for any late TS,
> in any reaction. **Only the energy can.**

⟹ An independent argument for the energy clause of constraint C-2, and it means **a topology-only
IRC gate is structurally blind to exactly this case.**

### 🔒 Fifth instance of one shape
After `cores_observed`, the `rstrip()` module name, availability-from-a-name-in-a-list, and
`converged` in `raw_steps`:
> **The disqualifying fact was written down in the artefact itself and no step read it.**
> Here it was written **in English, in the second line of the file, by whoever built the input.**

### ⚠ This is not a coder error and must not be recorded as one
The pilot's job was to measure the core-h of a QST2 stage, and **for that an idealised guess is a
perfectly reasonable input.** ADR-064's cost arithmetic is sound and survives intact.
🔴 **What went wrong is that a COST probe carried CHEMICAL acceptance criteria**
(`imag_freq_count`, `irc_endpoints_distinct`), so it rendered a chemical verdict it could not earn,
and the team spent a round on it.

> 🔒 **C-10: a cost probe must not carry a chemical pass/fail.**

### Revised prescription (before any retry)
```
C-8   optimise BOTH endpoints and verify zero imaginary frequencies FIRST.
      A TS search must REFUSE TO START otherwise — a precondition, not a warning.
C-9   break the symmetry: optimise in C1, perturb the planar guess out of plane
      let Li move freely — and if it relocates on ring opening, THAT IS THE PRODUCT,
      and it is itself a result worth recording
      fix the solvent (P1 ran in acetonitrile ε 35.7, not EC:EMC ε ≈ 18-20 — a factor of two
      on the reaction field for a charge-localising ion-pair reaction)
then  run the bake-off
```

🟢 **The zero-cost diagnostic returned more than the 302 core-h run did**: one identified cause, a
retry whose preconditions are now met, three constraints that generalise past P1, and a refutation
of the diagnostician's own leading hypothesis before anything was resubmitted.

---

## ADR-067: 🔒 **The round had ONE defect, not three.** proposer5 withdraws its own headline finding; U-55 is downgraded to UNDECIDED

**Date**: 2026-08-19 · **Withdrawn by**: proposer5 §39.1(e-bis), unprompted · **Every claim verified by the lead**
**Amends**: ADR-065 (U-55 overstated by the lead), ADR-066 · **Status**: confirmed

### What was withdrawn
> *"Li⁺-coordinated species have a floppy coordination manifold our protocol cannot optimise"* —
> which proposer5 had called *"the most consequential thing in the pilot"* and had already sent to
> engineer5 as grounds to revise the S2 line. **The lead promoted it to U-55 and reported it to the
> user as the finding that mattered most.**

### Why — verified in the input file, at zero cost
**All fourteen `inputs/p5_species/*.xyz` declare `idealized, NOT optimized` in their own header.**
`li_ec2_cation` — the 283 core-h non-convergence — is not merely unoptimised:
```
EC2 = EC1 + (0, 0, 4.200) for ALL TWENTY atoms, exactly
      ⟹ eclipsed, parallel, exact translational copies; mirror plane at z = 2.1
Li at (0, 2.400, 2.100)  — sitting exactly ON that mirror plane
Li–O   2.100 and 2.100   (identical to 3 d.p.; ~0.15–0.20 Å too long)
O–Li–O 179.45°           linear
Li–O=C  90.27°           🔴 Li sits PERPENDICULAR to the carbonyl, over the π face.
                            That is not a coordination geometry — Li⁺ binds the O lone pair
                            (Li–O=C ≈ 120–140°), not the π system.
```
To reach a minimum the optimiser must bend O–Li–O, rotate **both** ligands ~90°, splay them apart
and repair every bond length — 🔴 **and several of those gradients are exactly zero at the start,
by symmetry.** An optimisation launched from a symmetric stationary point of the wrong index cannot
move along the symmetry-breaking coordinates until numerical noise breaks the symmetry, **and G16
detects symmetry by default.**

⟹ **283 core-h without convergence is fully explained without invoking any property of the molecule.**

### 🔒 UNDECIDED, not refuted
A floppy surface and a bad start are **not exclusive**, and P1b cannot separate them.
**"Undecided" is the honest word.** proposer5 told engineer5 not to inflate the pool budget on it.
🔴 **The lead's ADR-065 wording — "the species class the design leans on is the class that did not
converge" — overstated a hypothesis as a finding.** Corrected here rather than edited away.

### 🔒 ONE cause, not three
```
P1's "chemical failure"          ┐
r_composite ≈ 1.04               ├── all three: idealised, unoptimised, over-symmetric input
the "floppy manifold" hypothesis ┘   geometries, each of which DECLARED ITSELF AS SUCH in a line
                                     nobody read
```
🟢 **That is a much better result than three separate problems — it is one fix.**

### 🔴 The consequence most likely to be missed, because it looks like a trend
```
 5 atoms   hco3_anion       3.13 core-h
12 atoms   li_ec_cation     5.03
21 atoms   li_ec2_cation  282.74   ← non-converged
```
> **A hand-idealised geometry gets worse as a starting guess the larger the molecule is.**
> Five atoms are hard to draw wrongly; twenty-one atoms with a metal centre and two ligands are
> hard to draw rightly. **So the overhead from a bad guess grows with size in the same direction,
> and with a similar shape, as genuine size scaling.**

🔒 **NO SIZE-SCALING LAW MAY BE FITTED TO THE P1b/P5 UNIT COSTS.** If a `core-h ∝ N^k` term exists
anywhere in `03_COMPUTE_PLAN.md` and its `k` was sanity-checked against these three points, **it is
fitted to input quality, not to chemistry.**

### 🟢 This strengthens ADR-065 rather than weakening it
`r_composite = 1.0365`'s denominator is not merely "a failure" — it is **"the cost of climbing out
of a badly drawn, over-symmetric starting geometry", which has no counterpart in production at
all.** Use **1.14–1.30**; ADR-032 planned on 1.25 and was right.
🔒 And the gate defect stands untouched: `status: pass` was published while 3 of 6 optimisations
failed, because `criteria` inspects only the SCF.

### B1-D gains a null control as a result
🔴 If B1-D runs from the same idealised inputs it would **confirm the withdrawn hypothesis
spuriously — measuring the input generator and reporting it as chemistry.**
```
arm 1   properly generated conformers (ETKDG+MMFF, symmetry OFF, C1, no coplanar guesses)
        → "what does this class actually cost"
arm 2   the same species from the idealised geometries          (nearly free)
        → arm2 ⊖ arm1 = "how much of the pilot's cost was the guess"
🟢 arm 1 also retires R-4 ("does the ETKDG conformer route work") in the same batch, because it is
   that route exercised on the hardest species we own.
```

### 🔒 Rule requested by proposer5, adopted
> **Before attributing a computational failure to the chemistry, check the input.**
> Three conclusions this round had the same cause, and in all three the disqualifying fact was
> written in the artefact and unread. **The chemistry hypothesis is the expensive one, and it was
> the second thing to check every time.**

### On the withdrawal itself
proposer5 left the superseded paragraph standing with a supersede marker, *"because deleting a
wrong hypothesis hides that it was tested"*, and this is its **third** self-correction in one
delivery (the bond-count misreading, the endpoint hypothesis, and this). 🔒 **It withdrew a finding
it had already sent to another teammate as grounds for revising their numbers — the most expensive
kind to retract, and it did so unprompted.**

---

## ADR-068: 🔴 **The digest's unresolved register has been reporting a subset** — and the fix is a design choice, not a tidy-up

**Date**: 2026-08-19 · **Found by**: proposer5, while checking that its own append had not broken
the tooling · **Verified by the lead** · **Status**: register patched by hand; mechanisation is a coder item

### The defect
```
docparse.py:116        lines = find_section(secs, "미확정")
                       ⟹ that literal string, in 05_STATE.md, and nowhere else

05_STATE.md  ## 미확정      → U-01…U-11, U-14   (12 items)   ← the only list read
02_METHOD_SPEC.md            headed "미해결"     → never read
03_COMPUTE_PLAN.md           no such section     → never read
04_REVIEW_LOG.md             no such section     → never read

live set runs to U-59.
```
🔴 **The STATE resume block instructs the next session to run `./src/digest.sh` FIRST.** That tool
has been reporting an unresolved set that stops at U-14 — **U-15 onward, including U-15 itself
(the question this round was asked to resolve), U-30, U-41, U-49…U-52 and the new U-53…U-59, are
invisible to it.**

🔒 **The parser is not broken. It does exactly what it says.** The failure is that a register we
consult as authoritative was answering a narrower question than the one we were asking — **the same
shape as `cores_observed`, `raw_steps.converged`, and the unread `.xyz` headers, now at the level
of our own tooling.**

### Immediate action (lead, done)
`U-53…U-59` written into `05_STATE.md`'s `미확정` section by hand, with a 🔴 banner on the section
and a warning inside the resume block stating that the list is a subset and where the rest live.
⚠ `U-15…U-52` are **not** backfilled — 38 items transcribed by hand is how transcription errors
enter a register whose whole value is being trustworthy.

### The design choice — 🔒 **(b), with the duplication made mechanical AND checked**
proposer5 declined to fix it and put the choice up, correctly: `05_STATE.md` is the lead's,
`src/` is coder's, and the options are not equivalent.
```
(a) widen the parser to match "미해결" and read all four documents
    ⟹ complete, but "one place to look" becomes "four places deduplicated by a regex",
      and four owners' lists merge
(b) 05_STATE.md stays the single register; every U-item is entered there
    ⟹ preserves the single register, but creates the same-fact-in-two-places coupling
      this project has been burned by repeatedly
```
**Adopted: (b), with the register line GENERATED from the owning document, not hand-written.**

🔒 **The reason (b)-mechanical is not the duplication trap we keep hitting**: a *generated*
duplicate whose staleness is **detectable** is categorically different from a hand-maintained one.
⟹ **The generator must ship with its own staleness check** — regenerate, diff against the
committed register, fail on any difference. **Without that check this is exactly the
`config` vs `parsed module name` failure again**, and it must not be implemented without it.

### ⚠ Blocking condition on the implementation
There is **no coder on the team**. This is a next-round coder item and must not be attempted as a
documentation edit. **The register stays hand-patched and visibly marked as a subset until then.**

### 🔒 The general form
> **A register outside the loop is only useful if it is actually consulted — and this one was
> consulted while quietly reporting a subset.**
> A tool that answers a narrower question than the one being asked of it is more dangerous than a
> tool that fails, because the answer arrives in the shape the asker expected.

---

## ADR-069: 🟢 **The team asked for LESS than its ceiling.** Commit ~15 k, reserve 69 k — and P1 never ran the production protocol

**Date**: 2026-08-19 · **proposer5 §39.13 + engineer5 §R35.2**, 5 direct rounds, no escalation
**Status**: recut ready; awaiting the user's release decision · **Zero compute run**

### The recut — sequencing instead of scope-cutting
engineer5's pessimistic ceiling was **~69,000 ref-core-h**, resting on `u_cheap ≈ 96.3` — a raw mean
over n=3 whose dominant point is a **283 core-h non-convergence**. The two clean points are 3.13 and 5.03.
```
if the bulk pool resembles the clean points   600 species ≈  3,700 ref-core-h
if it resembles the raw mean                  600 species ≈ 57,780         ⟹ 15× spread
```
> 🔒 proposer5: *"The right move is not to cut B1's scope to fit 69,000 — it is to **refuse to
> commit** 69,000, and sequence instead."*
```
B0 (GATE — what is asked for)      ~5,300 – 14,700 ref-core-h   = 7–22 % of the ceiling
   B0-D  Li⁺Lₙ probe, THREE arms: subject (generated conformers) / control (idealised) /
         r_high (high level from the same conformer)
   B0-F  TS bake-off, 6 attempts, AT COMPOSITE, 2 of them production-sized (20–30 atoms)
B1 (600 species)                   NOT COMMITTED. Sized by rule once B0 returns:
                                   N₁ = min(600, remaining / (u_measured × r_composite))
```
🟢 engineer5 adopted it **in full** and recorded it *"as an improvement, not a negotiated
compromise — cheapest-validation-first applied against my own number before I got there."*
🔒 **The accuracy advocate asked for less money than the throughput advocate had offered.** That is
the designed tension producing something neither would have produced alone.

### 🔴 Fourth P1 finding — it ran at the HIGH level
```
level2 = G-1 = wB97XD/def2-TZVPPD    ← HIGH (our SP layer)
level3 = G-3 = wB97XD/def2-SVPD      ← composite's geometry + Hessian layer
P1  hessian_level = "level2"
```
**P1's QST2, frequency and both IRCs all ran at def2-TZVPPD. P1 did not exercise the production
protocol at any stage.** (lead-verified in `config/qc_levels.json`.)

### 🔴 ADR-035's pre-registered measurement fired and returned NOTHING
ADR-035 kept `IMAG_WINDOW = (−2000, −100)` on an explicitly unverified premise — *"a basis change
shifts imaginary-frequency magnitudes by only tens of cm⁻¹"* — and named **P1b as the thing that
would settle it** (reopen-condition #1, marked 필수), since P1b runs the same species at two bases.
```
P1b's high-level runs did not converge on the Li species ⟹ no cross-basis frequency comparison exists
and the single −105 cm⁻¹ came from the HIGH basis, while production Hessians come from the CHEAP one
```
⟹ 🔒 **The premise is not "still unverified" — it is UNVERIFIABLE from anything we hold.**
🟢 It does not block us (§39.4(c) replaces the instrument rather than recalibrating the number),
**but the record must say the pre-registered measurement was attempted and returned nothing, rather
than letting it lapse silently.**
⚠ `recalibrated_for_cheap_basis: false` is *correct* for this run — **for the opposite reason to
the one everyone assumed: it was never the cheap basis at all.**

### 🔴 ADR-034 ground #3 has never been measured
*"A high-level TS = 172 h = 8 chain links"* is an estimate, and κ=2.4 rescaling (8→9) **rescales an
unmeasured number.** We hold exactly one high-level TS datum: 4.74 h wall at **11 atoms** — not
comparable to a production species. ⟹ **2 of B0-F's 6 attempts are production-sized (20–30 atoms)
so the ground finally gets a datum. That is the only place in the recut that ADDS.**

### 🔒 C-12 — a fifth instance of the same shape
`qc_levels.json:_ts_method` records: *"[my decision — proposer confirmation requested] ORCA used
NEB-TS; G16 has no NEB, so I ported to QST2, with a fallback to `opt=(ts,calcfc)` if it fails."*
**That confirmation was never given.** And the fallback is keyed on *QST2 failing to converge*, not
on *the TS being wrong*. **QST2 converged, so the fallback never fired.**
> 🔒 **C-12: a fallback conditioned on non-convergence cannot catch convergence to the wrong
> answer. Fallbacks are conditioned on the ACCEPTANCE TEST, not the exit status.**

### 🔴 κ is a code-and-workload ratio, not a hardware ratio
Measured on the P6 **SCF** probe; KNL is weak on memory-latency-bound and poorly-vectorised code.
```
gradient-dominated work (TS opt, MD, pool opt+freq)   κ ≈ 2.4
Hessian-heavy work (Option C, every freq stage)       likely WORSE   [UNQUANTIFIED]
out-of-core MP2                                       possibly much worse   [UNQUANTIFIED]
```
🟢 Flagged rather than given an invented factor. engineer5 had been treating κ as a hardware ratio
across several rounds and accepted the correction.

### Option C (87–116 k) — reserve, release nothing, and pre-register the release rule
engineer5's 30–40 % was **per species**; Option C is a property of the **reaction**
(Δ molecule count ≠ 0), and any species in *any* association/dissociation reaction needs the
high-level Hessian — with Li⁺ coordination everywhere, 30–40 % is more likely an **under**estimate.
```
route R1–R4 through Option C at ZERO incremental cost, then ask whether the shift is
  a BIAS      systematic ⟹ apply as an additive correction through ADR-027's σ_r machinery.
                            ROLLOUT COST ZERO.
  a VARIANCE  scattered  ⟹ not correctable; only then pay 87–116 k
```
🔒 **ADR-018's principle applied to a cost decision: not "is composite accurate here" but "is its
error the kind that can be absorbed". Up to 116 k turns on it.**

### Demo 2 — the purchase, stated so it is legible to the user
🔴 **E2 does NOT need a second system.** LIBE's FEC/VC/FSI/TFSI supply free hold-out chemistries
*inside* system 1, and E2 is the repeatable development gate.
> **E3 is the one-shot acceptance and is the only thing that genuinely requires a second system.**
> ⟹ **0.70 M buys ONE pre-registered prediction against pre-existing external gas data, on a system
> we never looked at.** Put it to the user in those words, not as "transferability evidence".

### DFT MD — no level seam, and the reason is the whole argument
engineer5's 200–1,040 was **low by ~5×** (a plane-wave-GGA cost profile applied to a GTO hybrid).
proposer5's redesign closes most of it: **the MD must not use the production functional.**
```
its only observable is a shell POPULATION COUNT, robust to the functional ⟹ PBE-D3 + small basis
🔒 and it creates NO LEVEL SEAM, because NO MD ENERGY EVER ENTERS THE NETWORK —
   the MD supplies WEIGHTS; energies stay at production level on the clusters
```
🟢 **Independently, this is exactly the level of the user's in-house fine-tuned SevenNet-0
(PBE, BJ-D3).** proposer5 chose PBE-D3 for this job before knowing the MLIP existed.

---

## ADR-070: 🟢 **MLIP MD is admissible as the solvation-shell falsifier — and is a BETTER instrument than the DFT MD it replaces.** Conditional on provenance.

**Date**: 2026-08-19 · **proposer5 §39.14** · **Status**: conditional; three provenance questions with the user
**Context**: the user owns a fine-tuned **SevenNet-0** (trained at **PBE**, **BJ-D3** available during MD)

### Why it qualifies as a falsifier — structural, not preference
A falsifier's requirement is not accuracy; it is that **its failure mode be independent of the one
it tests** (ADR-015/020's capture–recapture logic on a different problem). The continuum's four
failure modes:
```
① outer shells replaced by a structureless dielectric ⟹ differential packing entropy smeared out
② enumerates discrete minima ⟹ if the liquid is a continuous manifold, the discretisation IS the error
③ the n·RT·ln(c°/c_solvent) standard-state correction — a modelling choice worth ~0.05–0.1 eV per ligand
④ no dynamics
```
**An explicit-solvent MLIP MD shares none of the four.**

> 🔒 **The continuum's error is MODEL-FORM — the physics is deliberately replaced. The MLIP's error
> is INTERPOLATION — the physics is fitted. They can correlate by exactly one route: if the MLIP was
> fitted to data generated under the continuum's own approximations.**

### It changes class, not just cost
proposer5's original DFT-MD request was **deliberately a weak falsifier**: 10 ps ≪ the ns-scale Li⁺
exchange time, so it samples fluctuations *about* a shell, not equilibrium *between* shells.
An MLIP is 10³–10⁶× cheaper ⟹ ns–µs is reachable and it can be an actual ergodic sampler.
> **For a distribution question, sampling dominates: a converged distribution from a slightly wrong
> PES beats an unconverged one from an exact PES — provided you can bound how wrong.**
🔒 proposer5 would take it over the DFT MD **even if the DFT MD were free.**

### 🔴 Three provenance questions, each of which can make it a NO
```
1. reference labels computed on   periodic condensed-phase boxes ⟹ independent
                                  isolated clusters in implicit solvent ⟹ inherits ① and ②;
                                  the independence is ILLUSORY
2. training configs generated by  MD / AIMD / active learning ⟹ independent
                                  normal-mode or random displacement about cluster minima ⟹
                                  sampling centred on the SAME minima the continuum enumerates.
                                  🔴 Correlated blindness — and it appears in NO RMSE the model reports.
3. electrostatics                 short-range cutoff only ⟹ 🔴 the CIP⇌SSIP equilibrium spans
                                  Li⁺···PF6⁻ ≈ 2–7 Å, straddling a typical 5–6 Å cutoff.
                                  A short-range model can get first-shell Li–O right and the
                                  CONTACT-ION-PAIR FRACTION wrong — and the CIP fraction is not a
                                  side quantity, it IS the S1 question.
+  who runs it, on what hardware  ADR-037 dropped the GPU package; §27.3(c) recorded "zero-shot
                                  MLIP eliminated by GPU absence". OUR ability to run it is not
                                  established. If the user runs it, our cost ≈ 0.
```

### 🔴 Scope cut — the charge channel bites on half the question
```
🟢 pre-reduction electrolyte   every species has fixed charge (Li⁺, PF6⁻, neutral EC/EMC) — fine
🔴 the shell of EC⁻            ADR-051 recorded that MACE-MP-0-class models CANNOT DISTINGUISH
                               EC FROM EC⁻ ⟹ unavailable unless reduced species were in training
```
⟹ The MLIP supplies **the larger half**; the EC⁻ shell stays with the static route or stays
declared-unknown. ⚠ Temperature trap: slow exchange creates a standing temptation to run hot,
**which reintroduces the high-T bias precisely to fix the problem the MLIP was meant to solve.**
Run at physical temperature and pay in trajectory length; a hot arm is separate and separately reported.

### 🔴🔴 The literature cuts harder than expected — in our favour
```
[SEARCH-SUMMARY] The EXPERIMENTAL EC coordination number DOES NOT CONVERGE:
                 NMR read as up to 6 · Raman much lower · one report gives 2 above 0.5 M
```
proposer5's original argument was *"literature CN does not exist for an unstudied electrolyte."*
🔒 **The true statement is stronger: it does not converge even for the studied one.**
⟹ **The case for COMPUTING the shell rather than looking it up does not depend on transferability
at all — it holds for system 1, today.** And it caps V-1: **CN cannot be a validation target.**

```
[ABSTRACT-LEVEL, read directly] Skarmoutsos, Ponnuchamy, Vetere & Mossa, arXiv:1411.7171
  Li⁺ preferentially coordinates the LESS polar carbonate (DMC), attributed to tetrahedral
  packing causing dipole cancellation.
```
🔴🔴 **A published, independent instance of the exact failure mode named for the continuum.** A
cluster–continuum sees electrostatics plus a dielectric and would rank the *more* polar solvent
first; the condensed-phase result is the opposite.
⟹ **The risk is not slightly-wrong populations. It is a BACKWARDS RANKING of shell composition.**
⚠ That result is force-field-dependent, but the *mechanism* is a real condensed-phase effect no
continuum can represent regardless.

### 🟢 An external anchor for ADR-067
```
[SEARCH-SUMMARY] PC neutron diffraction:  Li···O = 2.04(1) Å,  ∠Li···O–C = 138(2)°
our inputs/p5_species/li_ec2_cation.xyz:  Li–O   = 2.100 Å,   ∠Li–O=C   =  90.3°   (lead-verified)
```
Distance close; **the angle is off by ~48° against a well-determined parameter.**
⟹ ADR-067's correction now rests on an external measurement rather than only on chemical judgement:
**that input is not merely unoptimised — it is *wrong against measurement* in the one coordinate
that defines how Li⁺ meets a carbonyl.**

### 🔒 Pre-registered decision rule (V-3) — written NOW because disagreement is the informative outcome
```
<10 pp     adopt continuum weights
10–30 pp   adopt MLIP weights and carry the spread as an uncertainty axis
>30 pp     🔴 the continuum is REJECTED as a weight source; unstudied systems get the shell as an
           UNWEIGHTED uncertainty axis        ← the branch that costs us something, which is why
                                                it is written before the measurement
```

### 🔒 Hard quarantine — and it is not arbitrary
> **The MLIP may validate/reject candidate 1 and set the uncertainty band. It may NOT supply
> production weights for ANY system, INCLUDING system 1.**

"Including system 1" looks over-strict; it is not. If system 1 used MLIP weights and system 2
(LiTFSI, no MLIP) used continuum weights, **any difference in E3 performance is confounded between
the chemistry and the method** — and E3 is a single shot and our strongest deliverable. Same method
on both, in both V-3 branches. 🔒 **The architecture holds either way, which is how we know the
constraint is not arbitrary.**

### Cost
```
🟢 DFT-MD request WITHDRAWN     releases 130–700 ref-core-h
   V-2a (DFT single points at the MLIP's own reference level, stratified frames)
                                ≈ 1,000–4,000 [proposer5 ESTIMATE, low confidence] — engineer5 to price
   V-1, V-2b                    ≈ 0  (B0-D already computes those clusters at production level;
                                      one extra column)
```
⚠ **V-2a's read-out is NOT force RMSE** — it is the **relative energy of competing shell
stoichiometries**, since populations depend on relative free energies (~0.05 eV target).

### proposer5's own retraction, third of the round
> §39.3 candidate 1 said *"the same physics breaks both — a floppy manifold is the physical reason
> both for the optimiser failure and for the continuum being weakest here."* **Retracted** — it
> rested on the hypothesis withdrawn in ADR-067.

🟢 And **B0-D now does double duty**: arm 1 converging cleanly kills the floppy hypothesis; arm 1
still failing supports it. **One experiment, two questions, no extra cost.**

---

## ADR-071: 🔒 **The MLIP seam runs between SUPPORT and WEIGHTS** — and the provenance we received answered the least relevant half

**Date**: 2026-08-19 · **proposer5 §39.15** · **GPU records discrepancy resolved by the lead**
**Amends**: the lead's seam reasoning in ADR-070, which was right in kind and incomplete

### 🔴 The lead's reasoning was too loose to draw a line
The lead argued: *"a seam in geometry is not the same object as a seam in thermochemistry."*
Correct in kind. **But the MLIP does not output geometry.**
> **It outputs a POPULATION, and a population is a free-energy difference in disguise:**
> `P(A)/P(B) = exp(−ΔG_AB/kT)`. **Taking the weights IS importing PBE-D3 thermochemistry.**
> At 298 K, telling 10 pp from 50 pp requires ΔG to ~0.04 eV, and PBE for Li⁺–carbonate ligand
> exchange is not obviously that good.

🔒 **ADR-026's seam was fatal because two levels appeared on opposite sides of a SUBTRACTION** —
a reaction ΔG is a difference of species energies, so the difference inherits an offset that never
cancels. **Here nothing is subtracted; no MLIP number is an addend in any energy expression.**
That is why the line falls where it does rather than at "admissible / inadmissible":
```
USE 1  THE SUPPORT   which Li⁺(EC)ₘ(EMC)ₙ(PF6⁻)ₖ compositions OCCUR, and which never do.
                     Structural — set by sterics, ionic radius, packing.
                     🟢 ADMISSIBLE FOR PRODUCTION. No thermochemical seam.
USE 2  THE WEIGHTS   ...and with what probability.  exp(−ΔG/kT) at PBE-D3 = a thermochemical import.
                     🟡 Falsifier and uncertainty band ONLY. Never production weights.
USE 3  energies / barriers into the network.   🔴 FORBIDDEN — that is ADR-026, not reopened.
```
🟢 **And the seam-free use is the higher-value one**, by proposer5's own §24.1 argument (the one
ADR-032 was adopted on): **a hole is worse than noise.** A missing species removes every reaction
through it and is a **structural zero capture–recapture cannot see.** The support tells us which
clusters to enumerate at our own level, **converting potential holes into computed species.**
⚠ proposer5's own footnote against itself: the packing result motivating all of this (Li⁺
preferring the *less* polar carbonate) is a **ranking** claim and therefore lives in USE 2.

### 🔴 The provenance answered the base model — the least relevant part
```
SevenNet-0 = NequIP-architecture equivariant GNN, pretrained on MPtrj
             (Materials Project relaxation trajectories, ~1.5M structures, VASP/PBE)
             🔴 INORGANIC CRYSTALLINE SOLIDS. No molecular liquids, no organic carbonates,
                no explicit solvent, no liquid-phase configurational sampling.
```
⟹ **Essentially everything that makes this model applicable to Li⁺ in a carbonate liquid came from
the FINE-TUNING — which is exactly what we still have not been told.**
🔒 proposer5: *"Not a complaint about the user: the question asked and the question answered are
different, and my job is to notice rather than file 'SevenNet-0, PBE' as though provenance were
discharged."*

**And the architecture answers the electrostatics question, not in our favour:**
```
NequIP-class = local message passing, receptive field ~10–15 Å,
               NO explicit long-range Coulomb, NO charge channel
⟹ first-shell Li–O is well inside it. The CIP⇌SSIP balance is NOT —
   and that is the observable deciding whether Li⁺ stays on the reduced species.
```

### 🟢 SevenNet parallelises through LAMMPS — already permitted
ADR-050 permits LAMMPS. **No new package, no exception needed.** Genuine and unanticipated convenience.

### 🔴 BJ-D3 is not a preference, and being ASKED as a preference is itself the finding
```
labels were PBE, no D3   ⟹ the network learned UNDISPERSED PBE. Switching D3 on at MD time adds a
                            term it was never trained against, on top of a fit that may already
                            have absorbed dispersion-like behaviour. 🔴 DOUBLE-COUNTING RISK.
labels were PBE-D3(BJ)   ⟹ D3 MUST be on; turning it off is the error.
```
⟹ *"SevenNet supports BJ-D3, switchable during MD"* is a **flag, not a reassurance**: it presents
as a runtime choice something the labels fix. 🔒 **That it can be asked as a preference tells us the
labels have not been specified.**

### 🟢🟢 V-1′ closes a placeholder we have carried since the pilot — worth having on its own
```
config/graph_layers.json   Li-O: 2.4 Å
provenance                 🔴 [PLACEHOLDER-ESTIMATE: 실측 필요]
                           "must be replaced by the Li–X RDF first minimum from P1 structures
                            and P2 AIMD trajectories. Until replaced, every R2/R3 endpoint verdict
                            computed with this value is PROVISIONAL."
🔴 P2 WAS DELETED (ADR-033). The trajectory that was supposed to supply this does not exist.
```
**The MLIP supplies exactly that quantity as a pure structural observable with no seam.**
🔒 **Worth having even if the shell-population question were abandoned entirely.**
⚠ Reminder of what this touches: every `R2`/`R3` IRC endpoint verdict — including P1's — was
computed against a placeholder cutoff and is provisional.

### 🔒 GPU records discrepancy — RESOLVED by the lead (proposer5 flagged it as not theirs)
```
ADR-037's decisive ground   "CONSUMER ELIMINATION (not cost)" — the user's tool restriction
                            (VASP/Gaussian/xTB) killed P4's only consumer, the GPU-DFT offload
                            via pyscf + gpu4pyscf. "Even if the measurement were accurate there is
                            no plan item to put the value into."
BRIEF §3                    at least 6× H100 — THE HARDWARE EXISTS
```
🔒 **"We do not ship a GPU probe package" ≠ "there is no GPU."** Different facts; no contradiction.
🔴 **But any text reading "eliminated by GPU absence" is wrong and must be corrected** — it would
cause a future reader to rule out capacity that is actually available.
🟢 And it does not bind the MLIP path at all: **SevenNet runs through LAMMPS and never touches
pyscf/gpu4pyscf.**

### Where proposer5 is less worried than the lead, and more
```
🟡 LESS  charge transfer in the NEUTRAL shell. Li⁺–carbonate is a hard closed-shell cation making
         an ion–dipole/polarisation contact; transfer into Li 2s is small. GGA self-interaction
         error does its damage in radicals, mixed-valence systems, CT complexes and transition
         states — a Li⁺···O=C dative contact is none of those.
         ⟹ adequate for STRUCTURE, marginal for RELATIVE ENERGETICS — the USE 1 / USE 2 split
           arrived at independently, from the physics rather than from the seam argument.
🔴 MORE  (i) THE EXCESS ELECTRON: GGA over-delocalises it across several solvent molecules instead
             of localising it — a known severe failure, and EC⁻ is exactly that object.
             🟢 This coincides with the missing charge channel ⟹ the EC⁻ scope boundary has TWO
                independent reasons and holds even if a charge channel appeared.
        (ii) plain PBE UNDERBINDS MOLECULAR LIQUIDS by ~10 % in density — and packing is the very
             mechanism the shell composition is attributed to.
```

### Checks (V-1′, V-1″, V-2b)
```
V-1′  Li–O and Li–P/Li–F RDFs with running coordination number: first-peak, FIRST-MINIMUM, n(r).
      Anchors: Li···O ≈ 2.0 Å, ∠Li···O–C ≈ 138° [SEARCH-LEVEL]. Li–P/Li–F gives the CIP fraction —
      the observable most at risk from the finite receptive field.
      🔴 NOT against the EC coordination number (U-65: the experiments do not converge).
V-1″  NPT density vs ~1.2 g cm⁻³ for EC:EMC 3:7 + 1M LiPF6. Cheapest global test of the packing,
      and an MPtrj-pretrained model applied to a molecular liquid is exactly where this fails.
      >5 % off ⟹ USE 2 is dead on arrival; USE 1 may survive.
V-2b  🔒 THE TEST THAT DECIDES USE 1 vs USE 1+2, and nearly free — RIDES ON B0-D.
      Compare PBE-D3 against our production level on Li⁺(L)ₙ LIGAND-EXCHANGE ΔG.
      ≲0.05 eV ⟹ USE 2 admissible with quantitative weight; disagree ⟹ weights cannot rank shells,
      support still fine.
```

### U-06 — what this touches, and what the register must NOT record
🟢 **Touches**: the existence/identity question for a **structural** role on the **primary** system.
🔴 **Does NOT touch the S2-C discovery role**, for two independent reasons: no charge channel ⟹
cannot distinguish EC from EC⁻ ⟹ **cannot do reduction chemistry at all**, which is the mechanism
we are trying to discover; and bond breaking is out-of-distribution for a model fine-tuned on
equilibrium liquid configurations over a crystal-relaxation pretraining.
🔒 proposer5: *"ADR-051 recorded the foundation-MLIP question as one for the user, not for me. The
user has acted on the structural side. **It does not follow that the discovery side is open — I am
not inferring it and I am not asking for it.**"*
Also untouched: transferability (no model for system 2) and the ADR-018 barrier surrogate.

---

## ADR-072: 🔴 **V-2a was priced four times and three were wrong** — a rejected option's number travelled as an adopted one

**Date**: 2026-08-19 · **engineer5 §R35.8, proposer5 §39.16** · **Lead verified the final arithmetic**
**Status**: settled at ≈11,700 ref-core-h; only Q5 (ENCUT/PAW) still moves it, by tens of percent

### The pricing chain
```
4,000 – 60,000   engineer5, "a REAL cost basis from §R16.8"     🔴 R16.8 is labelled [ESTIMATE]
  600 –  8,000   "10× drop — box pinned at 40–100 atoms"        🔴 40–100 was never anchored
  700 –  5,000   "box up, settings down, roughly offsetting"    🔴 still the wrong box
≈11,700 (9,000–15,000)   ← derived box (158 atoms), corrected exponent
```
🔒 **The lead relayed the first three to the user as good news.** All three were wrong, and two were
wrong in the favourable direction.

### 🔴 Where `40–100 atoms` came from — this is the round's shape in one fact
engineer5, unprompted and precisely:
> *"TOLD TO ME — verbatim, in proposer5's chat message. I did not derive it, infer it, or check it
> against their primary document. I have now read §39.16 directly: **it names a REJECTED
> cluster-shortcut option (~60–120 atoms) that proposer5 explicitly ruled out. The number attached
> to the option they rejected is what reached me.**"*

🔴 **A number attached to a discarded option travelled into the pricing of the adopted one.**

And the part that generalises:
> *"This is the exact 'cite the summary, not the source' failure this whole session has been about,
> and **I told proposer5 to avoid it four rounds ago in almost those words, then didn't apply it to
> their own message to me.** That's the fault, and it's mine, not a shared one — proposer5's
> drafting slip and my failure to verify it are two separate errors that happened to compound."*

🔒 **Giving someone a rule does not install it in yourself.** The rule was correct, recent, and
authored by the person who then broke it — **against a message from the very person he had given it
to.**
🔒 And refusing to split the fault is right: **two independent errors that compound are not one
shared error, and calling them one hides that either alone was sufficient.**

### 🔴 `[ESTIMATE]` replaced by `[ESTIMATE]`, called "real"
```
docs/03_COMPUTE_PLAN.md:3980
  단위 비용 내역 [ESTIMATE] (PBE-D3(BJ), ENCUT 600 eV, k-spacing 0.03 Å⁻¹)
     static SCF 30–250 core-h/displacement    ← an 8× range INSIDE the estimate
```
proposer5 flagged their own V-2a figure as an unanchored guess and **asked engineer5 to replace it
with a real basis.** engineer5 supplied R16.8 — **which is itself labelled `[ESTIMATE]`.**
🟢 The substitution was still an improvement (R16.8's estimate is *structured*, terms broken out,
where proposer5's was a single number) — 🔴 **but "real cost basis" is a claim that number cannot
carry, and the lead repeated it to the user as "실제 앵커".** Third instance today of a derived
characterisation outcompeting its own source.

### 🟢 Two self-caught errors in the same message
```
· engineer5 re-derived ≈11,700 on its OWN anchor rather than accepting proposer5's number —
  and while doing so caught its own arithmetic slip: it had used exponent 2.4, where R16.8's own
  two endpoints give 2.314.   🔒 LEAD-VERIFIED: ln(250/30)/ln(250/100) = 2.314 exactly.
· it had written that Γ-only vs k-mesh was "routed to the user" — wrong; it is proposer5's own
  method call (§39.16(d)) and was never pending anything.
```

### 🟢 The structural event worth more than the number
**proposer5 asked "is R16.8 MEASURED?" about the number being used to price *their own request*.**
A confident-sounding "real anchor" made their V-2a look better founded, and they had every incentive
to let it stand. **They checked it anyway.**
🔒 Second time in this round the accuracy advocate undercut a number that flattered its own proposal
(the first: asking engineer5 to re-price their own guess).
> **The designed tension is not producing compromises. It is producing audits in the direction from
> which neither party benefits.**

### Disposition
```
V-2a  ≈11,700 ref-core-h  [ESTIMATE derived from an ESTIMATE — R16.8's per-displacement static-SCF
      cost is itself [ESTIMATE] with an internal 8× range (30–250 core-h)]
      🔴 label attached to the NUMBER, not the paragraph
      Only Q5 (ENCUT / PAW dataset version) still moves it — by tens of percent, not a factor.
🔴 V-2a is comparable in size to the whole B0 gate batch (5,300–14,700). It is NOT small, and the
   two "good news" reductions the lead relayed were both artefacts.
🔒 V-2a is not requested. It arises only if MLIP provenance (Q1–Q3) passes.
```

---

## ADR-073: 🔴 **We have never checked whether VASP can compute anything** — ~~and a reported observable rests on it~~
### ⚠ SUPERSEDED IN PART BY ADR-074 — the struck clause is FALSE. The correct target is ADR-014's transferability requirement, and it is LARGER.

**Date**: 2026-08-19 · **proposer5 §39.17**, from asking engineer5 one question about a small item
**Lead-verified: every claim** · **Status**: two probe items added; V-P1 escalated to the user at zero cost
🔴 **AMENDED BY ADR-074** — the downstream attribution in the title and in §"critical-path item" is wrong. Read ADR-074 before quoting anything from this entry.

### How it surfaced
proposer5 asked whether engineer5's periodic-VASP cost anchor (§R16.8) was `[MEASURED]` or
`[ESTIMATE]`. engineer5 checked `plan.json` and answered honestly: **never measured; RT-1's task
list is G16-only, zero VASP entries.** 🔒 **The consequence is far larger than the item that
surfaced it.**

### 🔴 The critical-path item rests on the same nothing
```
V-2a   MLIP validation SPs                17,000   [ESTIMATE²]   ← the small item
🔴 §26.4  LATTICE ENERGIES (LEDC, LiPO2F2)         [ESTIMATE²]   ← the critical-path item
       ⟹ ΔG_precip ⟹ LiF : Li2CO3 ratio ⟹ ADR-003 AXIS (b), A REPORTED OBSERVABLE
       🔴🔴 SUPERSEDED BY ADR-074 — THIS CHAIN IS WRONG. Kept, not deleted.
          02_METHOD_SPEC.md:3517 — class A (LiF, Li2CO3, Li2O, LiOH) uses EXPERIMENTAL ΔG_f°(s)
          and explicitly "VASP를 쓰지 않는다". Only class B (LEDC, LiPO2F2) uses VASP.
          ⟹ LiF:Li2CO3 does NOT depend on the unmeasured VASP basis.
          🔒 The CORRECT consequence is LARGER: class A's experimental anchor is itself a
             known-answer dependency (the class ADR-014 outlaws). For an unstudied electrolyte
             every solid is class B ⟹ the experimental route does NOT transfer, the VASP route does.
             V-P1/V-P2 gate ADR-014's transferability requirement, not a budget line.
       includes finite-displacement phonons — flagged in §26.4 as the bulk of the pessimistic figure
```

### 🔴🔴 Cost is the smaller half — "the binary exists" was never tested against "VASP runs"
RT-1 measured `vasp.6.4.3` 🟢 (which closes half of U-24: ≥6.3, so r2SCAN-D4 is available). **But a
VASP binary with no POTCAR library computes nothing, and POTCARs are licensed separately from the
source — building the code does not produce them.**
```
lead-verified grep over docs/ and src/ for POTCAR|potpaw|pseudopotential|PAW dataset
  → every hit is proposer5's own §39.17, written today. BEFORE IT: ZERO.
```

### 🔒 The lesson was learned for a different code and never transferred
```
03_COMPUTE_PLAN.md:5997
  | basis set·pseudopotential 데이터 동봉 ($CP2K_DATA_DIR) | [NOT MEASURED] — 실무상 가장 자주 깨진다 |
03_COMPUTE_PLAN.md:6038
  echo "CP2K_DATA_DIR=$CP2K_DATA_DIR"; ls "$CP2K_DATA_DIR" 2>/dev/null | head -30
```
**We wrote the probe command for CP2K's pseudopotential directory and never wrote the analogous one
for VASP's POTCAR.** The lesson was learned, the instrument was built, and it was not carried across.
🔒 **Rule 20 applies to any inference from a proxy — including a proxy that worked for a different
code.** Same shape as RT-1's two lost round trips, where availability was inferred from a name.

### 🔴 The VASP-specific silent failure is the WRONG VARIANT, not the missing file
```
POTCAR ABSENT     → VASP stops. Loud. Survivable.
🔴 WRONG VARIANT  → VASP runs perfectly and returns DIFFERENT ENERGIES.
   Li vs Li_sv (semicore 1s in valence) · O vs O_h · F vs F_h · P vs P_h
   — all valid, all different.
```
For V-2a this is a **validity** question, not a quality one: it asks whether the MLIP is faithful
**to its own reference**, and Materials Project uses a **defined** POTCAR set (`Li_sv` among them).
**Wrong variant ⟹ any disagreement is ours rather than the model's, and we would have paid the full
cost to measure our own inconsistency.**
⟹ **POTCAR variant joins Q5** — the same argument already made for ENCUT, now with a mechanism.

### Two items fix it; the first costs zero core-hours
```
V-P1  POTCAR INVENTORY — 0 core-h, a directory listing. 🔒 ESCALATED TO THE USER AS C3.
      Which VARIANT directory exists for each of C · H · O · Li · P · F, plus any version stamp.
      🔴 REPORT THE NAMES, NOT A BOOLEAN — a boolean cannot answer the variant question and
         buys a second round trip to ask it.
V-P2  VASP LAUNCH SMOKE — minutes. One tiny cell (rocksalt LiF, 8 atoms, Γ-only, low ENCUT).
      Proves the binary launches under MPI on a COMPUTE node, POTCARs are consumed, output appears
      — and returns the project's FIRST VASP core-h datum of any kind.
      🔴 STATE records that P6 — the item that produced κ — was the ONE item with no cheap smoke
         gate in front of it, and that this was named as a defect at shutdown. DO NOT REPEAT IT.
```
🟢 engineer5's 20-frame phasing gate is now the project's first VASP cost measurement, so instrument
it (core-h/frame, memory, wall, k-points, ENCUT, POTCAR variants, atom count): **one gate anchors two
consumers.** ⚠ Honest limit: a liquid-box datum does **not** size a crystal phonon supercell —
different system, different settings, and phonons are finite-displacement *sets*. It establishes the
machine's VASP throughput class only.

### 🔒 Why the reserve was NOT raised again
proposer5, declining the move that would have looked more cautious:
> *"`Reserve 17,000` stood on exponent uncertainty; it now stands on 'no measurement anywhere in the
> lineage'. **I am not raising it further, because a bigger number derived from the same nothing is
> not more conservative — it is more confident.** V-P1 and V-P2 replace the guess, and they cost
> approximately nothing."*

---

## ADR-074: 🔴 **The VASP escalation was attributed to the wrong observable — and the correct target is bigger**

**Date**: 2026-08-19 · **proposer5 §39.18, correcting itself against its own §26.4** · **Lead-verified**
**Amends**: ADR-073's downstream attribution (and the lead's relay of it to the user)

### The false link
ADR-073 recorded, from proposer5 and relayed by the lead to the user:
> *"unmeasured VASP ⟹ ΔG_precip ⟹ the LiF : Li2CO3 ratio ⟹ ADR-003 axis (b), a reported observable."*

**The middle link is false, and `02_METHOD_SPEC.md:3517` — which proposer5 wrote — says so:**
```
| A. 실험 열역학이 확립된 무기 고체 | LiF, Li2CO3, Li2O, LiOH |
  🔴 VASP를 쓰지 않는다. 실험 ΔG_f°(s) 를 앵커로 쓰고, 우리 계산은 용액상 쪽만 담당한다.
  ⟹ 이음매가 "DFT↔DFT" 에서 "DFT↔실험" 으로 바뀐다 — 엄격히 낫다 |
class B = LEDC, LiPO2F2 (VASP). Class-A species are run in VASP ONLY to derive the δ correction.
```
⟹ **LiF and Li₂CO₃ do not depend on VASP for their thermodynamics.**
🔒 proposer5: *"Exactly the failure I have spent this round catching in others: a chain quoted
without its middle link checked. Mine this time, and against my own document."*
⚠ **The lead relayed the chain to the user without checking the middle link either.**

### 🔴 But the correct consequence is LARGER, and it inverts §26.4's own reasoning
§26.4's class-A route is an **experimental anchor** — a **known-answer dependency**, the exact class
**ADR-014 outlawed**.
```
For an UNSTUDIED electrolyte there is no experimental ΔG_f°(s) for its novel solids.
⟹ EVERY solid is class B.
⟹ THE EXPERIMENTAL ROUTE DOES NOT TRANSFER. THE VASP ROUTE DOES.
```
🔴 §26.4 chose experiment specifically to convert a DFT↔DFT seam into a DFT↔experiment seam and
called it **"엄격히 낫다"** (strictly better). 🔒 **It is strictly better for accuracy on system 1
and strictly worse for transferability, and that was not seen at the time.**
It degrades gracefully — most Li-ion electrolytes still produce LiF and Li₂CO₃, so δ can usually
still be anchored — **but the production path for NOVEL solids is VASP and only VASP.**

> ⟹ **V-P1 and V-P2 do not gate a budget line. They gate whether the pipeline can meet ADR-014's
> top-level requirement for any electrolyte at all.** If VASP does not run on this cluster, we
> cannot handle a novel solid in **any** system, studied or unstudied.

🔒 **The escalation gets STRONGER from the correction, not weaker** — but it must arrive in the
correct form: not *"a reported observable rests on zero VASP measurement"* but **"the
transferability requirement rests on a code we have never run and whose pseudopotential library we
have never looked for."**

### Fallback ladder, so the escalation does not arrive without a plan
```
F-1 (preferred)  class-B precipitation becomes a DECLARED UNCERTAINTY AXIS.
                 ADR-021 already represents precipitation as a reversible pair with a computed K_sp;
                 if K_sp is unavailable, SCAN it over a physically bounded range and report the
                 composition's SENSITIVITY instead of a number.
                 🟢 Cost zero · element-agnostic ⟹ IT TRANSFERS · and for an unstudied electrolyte
                    it is the only honest treatment regardless.
                 Loss: the organic precipitation channel becomes a band, not a value.
                 🔒 Same principle as ADR-018 and §39.3 candidate 3 — convert an unknown into a
                    declared axis rather than a fabricated value.
F-2              cluster-extrapolated lattice energy in G16. 🔴 Poor here: LEDC is an IONIC, LAYERED
                 crystal, so the Madelung sum converges conditionally and cluster extrapolation is
                 unreliable exactly where we need it. A sanity bracket on F-1's scan range, NOT a value.
F-3              literature thermodynamics for LEDC. [UNVERIFIED — not checked]. Cheap, and should be
                 checked BEFORE F-1 is adopted: if the data exist, class B shrinks to LiPO2F2 alone
                 and this becomes minor FOR SYSTEM 1. ⚠ It still does not transfer — which is F-1's point.
```

### Unchanged
`U-69/U-70`, `V-P1`, `V-P2`, the 17,000 reserve, POTCAR variant added to Q5. **Only the downstream
attribution moved.**

### 🔒 The sharpest statement of this round's failure mode, by the person who made it
engineer5, on the POTCAR miss:
> *"I named this exact failure class for CP2K myself, in my own earlier text, and never checked
> whether the same risk applied to VASP. **That's not an excuse, it's the finding: I had the
> pattern in hand and didn't run it against a second code.**"*

---

## ADR-075: 🟢 **MLIP accepted for production. V-2a released 17,000 → ~2,500.** And F-1 becomes the DEFAULT, not the fallback

**Date**: 2026-08-19 · **proposer5 §39.21/§39.22** · **User answers: periodic box · MD+density-varied configs · PBE labels · RDF+NPT density VALIDATED · ENCUT 520 / Li_sv · >200k structures, 400–500 atoms**
🔒 **User directive: "Do not question the MLIP's reliability further. Design the workflow around using it."** U-62/U-66 closed.

### 🟢 The SUPPORT/WEIGHTS restriction DISSOLVES — it does not narrow
ADR-071 restricted the MLIP to structural support because weights are `exp(−ΔG/kT)` and taking them
imports PBE thermochemistry **we had no way to check**.
> 🔒 proposer5, adopting the lead's reading: *"That was an argument about an UNCHECKED quantity.
> A validated RDF/CN is a MEASUREMENT of that quantity, against experiment."*
> **And it is stronger than the test I proposed, because V-2a could never have detected an error in
> PBE itself.** The coordination-number distribution *is* the population distribution — `n(r)` to
> the first minimum is literally the mean CN.

⟹ **USE 2 (weights) is admissible for production.**
🔴 Residual scope point, **not a reliability question**: an RDF is a **one-dimensional,
species-averaged projection**. A total Li–O CN of 4.0 is equally consistent with `m=4,n=0`,
`m=2,n=2` or `m=1,n=3` — **a total Li–O RDF cannot separate EC oxygen from EMC oxygen**, and the
composition split is precisely the estimand. ⟹ **question C** (partial or total-only); if total
only, the partials are **post-processing of the existing trajectory — zero new sampling.**

### 🟢 D3 — the lead's rule supersedes proposer5's own
```
proposer5   "D3 must match the LABELS"      — an a priori consistency ARGUMENT
adopted     "D3 must match the VALIDATION"  — because a validation is a MEASUREMENT
```
And a validated density **excludes both failure directions at once**: double-counted D3 ⟹ over-bound
⟹ density too high; no dispersion ⟹ PBE underbinds molecular liquids ⟹ too low by 10–20%.
🔴 **Workflow constraint**: whatever the validated runs used goes into production **unchanged**.
**Nobody "improves" it toward label-consistency later** — that would discard the only empirical anchor.
🟡 proposer5's inference (not asserted): a validated NPT density **suggests D3 was ON**. **Question A settles it.**

### 🔴 EC⁻ — the architecture is the constraint, not the training set
NequIP/SevenNet takes positions + species and returns **one** energy. **No charge input** ⟹ for
identical nuclear positions it cannot return different energies for EC and EC⁻.
🔴 **Adding reduced species to training makes this WORSE**, not better — the network sees two labels
for near-identical inputs and learns an average.
**But two cases, and only one is blocked:**
```
the electron-transfer event itself       🔴 permanently impossible for this architecture.
                                            🟢 We do not need it — S1 barriers are ours.
the shell of an ALREADY-FORMED reduced   🟡 POSSIBLE: EC⁻ is GEOMETRICALLY distinct
species                                     (pyramidalised / ring-opened) ⟹ "this geometry ⟹ this
                                            energy" is learnable implicitly.
                                            🔴 And a bare EC⁻ needs a compensating background, but
                                            Li⁺·EC⁻ AS A NEUTRAL CONTACT PAIR DOES NOT — which is
                                            exactly what our chemistry makes (P1's system is
                                            LiEC•, charge 0, mult 2).
```
⟹ **question B**, and **the second half is the tell**: an open-shell radical labelled
non-spin-polarised is mislabelled regardless of what was in the set.

### 🟢 V-2a → V-2a′. Release ~14,500 of 17,000.
```
V-2a                    MLIP vs PBE            — cannot detect an error in PBE ITSELF
user's RDF + density    MLIP+PBE vs EXPERIMENT — detects both, ON THE OBSERVABLE WE CONSUME
```
🔒 **proposer5 killed its own 17,000 core-h item because a test the user had already run is stronger
than the one it designed.**

🔴 **But re-aimed, not deleted.** The one thing an RDF structurally cannot see:
> **An RDF is dominated by the bulk of the distribution. A rare or absent composition whose MLIP
> energy is spuriously too high would never be sampled, would not move the RDF measurably, and
> would enter our pool as a STRUCTURAL ZERO** — the class capture–recapture cannot detect
> (§24.1, the argument ADR-032 was adopted on).
```
V-2a′  STRUCTURAL-ZERO PROBE. CONSTRUCT the near-absent compositions by first-shell ligand
       substitution; compare MLIP against periodic DFT.
       🔴 They CANNOT be drawn from the trajectory — BEING ABSENT IS THE PROPERTY UNDER TEST.
          That constraint is the design.
       20–30 configurations · ENCUT 520 · Li_sv · Γ-only · the validated D3 · ~2,500 [proposer5]
       ⟹ engineer5 re-pricing on its own anchor
```

### 🔴 The resize does not discharge the label — proposer5 applied the lead's warning to itself
> *"That cut came from a SCIENTIFIC argument, not a cost measurement.
> **We need LESS of the unmeasured thing. The unmeasured-ness is undiminished.**
> The `[ESTIMATE derived from an ESTIMATE]` label SURVIVES THE RESIZE."*

### 🔴 And a second thing the V-P2 cancellation does not discharge
```
"VASP runs on this system"      ← about VASP. Established by the user. ✅
"OUR JOB SCRIPT INVOKES VASP"   ← about OUR CODE. Established by nothing.
```
🔒 **This is the RT-1 lesson, not a doubt about the user's claim.** G16 was present and the user
could certainly run it; **our package still failed twice** — an ORCA parser applied to Gaussian
logs, and a truncated module name. **The failure was never "the code doesn't work"; it was "our
plumbing doesn't reach it."**
🟢 **No new item**: V-2a′'s first sub-gate (5 constructed frames) **is** the integration test — the
first time our pipeline invokes VASP at all. Three purposes at no extra cost: residual scatter, the
project's first VASP cost datum, integration verification.
🔴 **Standing instruction: if those 5 fail, read it as PLUMBING before reading it as PHYSICS.**
That is ADR-067 pointed at our own code — **and it is the reading P1 needed and did not get.**

### 🔴🔴 F-1 is the DEFAULT, not the fallback — U-72 RESOLVED
§26.4's VASP route is **not self-sufficient**, because it depends on an experimental anchor:
```
ΔG_lattice(class B) = VASP(class B) + δ,   δ = VASP(class A) − EXPERIMENT(class A)
🔴 For an unstudied electrolyte a novel solid may have NO experimental analogue at all
   ⟹ δ CANNOT BE ANCHORED, and the VASP number carries an uncorrected systematic error of
     unknown size — EVEN THOUGH VASP RUNS PERFECTLY.
```
> ⟹ **F-1 inverts status: it is the PRODUCTION treatment for solids without experimental anchors,
> and VASP+δ is the SPECIAL CASE that works only where anchors happen to exist.**
```
RULE (element-agnostic ⟹ transfers):
  experimental anchor EXISTS for the class  ⟹ VASP + δ
  NO anchor for the class                   ⟹ F-1: K_sp as a DECLARED UNCERTAINTY AXIS, scanned
                                               over a bounded range; composition SENSITIVITY
                                               reported instead of a value
```
🟢 Cost zero, element-agnostic — **the same move as §39.3 candidate 3 and ADR-018 for the third
time: convert an unknown into a declared axis rather than a fabricated value.**
F-2 stays a bracket, never a value. F-3 is worth a cheap check **for system 1 only** — 🔴 it cannot
change the rule, **because the rule exists precisely for the case where no literature exists.**

### Handover spec (MLIP ensemble produced off-cluster, user's own code)
```
🔴 extxyz with metadata IN THE COMMENT LINE — not frames and metadata as two files.
   That is the failure this project has hit six times: a fact in one place, its qualifier in another.
🔴 seed_id AND trajectory_id as separate columns; seed_id shares its definition with
   sei_pilot/seeding.py::provenance. ADR-051 — UNRECOVERABLE after the fact.
🔴 N_FRAMES IS NOT THE SAMPLE SIZE. Consecutive MD frames are correlated and Li⁺ residence times
   are hundreds of ps to ns. 120 frames at 1 ps stride are far fewer than 120 independent shell
   compositions, and every population uncertainty computed from them is too small by the
   autocorrelation factor.
   🟢 ADOPTED AS A REQUIREMENT, NOT A PREFERENCE: multiple independent seeds rather than one long
      trajectory — free here, and it simultaneously satisfies ADR-051's D1, which needs independence
      BY DESIGN rather than by assumption. One choice, two requirements.
```

### The quarantine — the seam half dissolves, the E3 half survives
🔴 The E3 confound is untouched: **system 1 has an MLIP, system 2 does not, so any difference in E3
performance is confounded between chemistry and method — and E3 is a single shot.**
🟢 Resolution costs nothing: **same method on both for the REPORTED prediction**, and use the MLIP on
system 1 to **quantify what the continuum loses.** That difference is itself a headline result, and
a **method-validity statement transfers even though the model does not.**

### Register
```
🟢 CLOSED    U-62, U-66 (user directive) · U-70, U-71, V-P2, the §39.18 escalation
🟢 RESOLVED  U-72 by the anchor-existence rule above
🔴 OPEN      U-69 (VASP cost — never measured; the label survives the resize)
🆕 U-74      our pipeline has never invoked VASP. No new item — V-2a′'s sub-gate carries it.
🔴 BLOCKING ON THE USER   A (which D3 setting was validated) · B (Li⁺·EC⁻ in training, spin-polarised)
```

---

## ADR-076: 🔴 **The two solvation halves must not carry the same σ** — and the EC⁻ boundary is two boundaries, not one

**Date**: 2026-08-19 · **proposer5 §39.25**, correcting the lead's framing · **User answers: D3 was ON; reduced species NOT in training**

### User answers — both blocking items closed
```
A  D3 was ON during the validated MLIP runs
   ⟹ 🔒 PRODUCTION INHERITS D3 ON, UNCHANGED. Nobody "improves" it toward label-consistency later.
      🟢 proposer5's inference was right: a validated NPT density did imply D3 was on.
B  reduced species such as EC⁻ were NOT in the training set
   ⟹ 🟡 the EC⁻ scope boundary HOLDS. MLIP supplies the PRE-reduction shell (the larger half);
      the post-reduction shell stays with the static route.
🟢 Nothing downstream moves, because §39.3 placed the reduced half with the static route BEFORE B
   was asked. **That is the argument for choosing architectures before answers.**
```

### 🔴 The lead's framing was too strong — it is TWO boundaries
The lead asked this be recorded so *"a future reader does not conclude the boundary is liftable by
retraining"*. **True of one case, false of the other, and the distinction is the value of the record.**
```
CASE 1  THE ELECTRON-TRANSFER EVENT (EC → EC⁻ at fixed geometry)
        🔴 NOT liftable by retraining, ever. Architectural — no charge channel — and adding
           reduced species makes it WORSE (two labels for near-identical inputs ⟹ an average).
        🟢 We do not need it: S1 barriers are computed at our level, never by the MLIP.
CASE 2  THE EQUILIBRIUM SHELL of an ALREADY-FORMED reduced species
        🟡 IS in principle liftable — neutral Li⁺·EC⁻ pairs with spin-polarised labels — because
           EC⁻ is GEOMETRICALLY distinct, so "this geometry ⟹ this energy" is learnable implicitly
           without a charge channel.
        🔴 With a specific hazard worth recording: the model would learn a SINGLE-VALUED function
           of geometry through a region where the true surface is DOUBLE-VALUED — it would smooth
           the avoided crossing. Tolerable far from the ET seam (where an equilibrium shell sits);
           not near it — which is Case 1 arriving by another route.
```
⚠ And a guard the other way: **"architectural" is about THIS architecture, not MLIPs as a class** —
charge-conditioned and charge-equilibration models exist. A future reader should conclude *this one
cannot, and more data is the wrong lever* — **not that no MLIP could.**

### 🔴🔴 The real answer to "what does the static route now owe" — σ, not cost
**Cost: unchanged.** Reduced-species cluster opt+freq are already pool members.
**Uncertainty: the two halves now have DIFFERENT EPISTEMIC STATUS and must not carry the same σ.**
```
PRE-reduction    weights validated against EXPERIMENT      ⟹ small σ, production-usable
POST-reduction   continuum ALONE, NO FALSIFIER — exactly what §39.3 called unacceptable:
                 "a continuum calculation of a floppy manifold will always return populations
                  and cannot detect that it is wrong"

🔴 ASSIGNING BOTH THE SAME σ WOULD LAUNDER THE VALIDATED HALF'S CREDIBILITY ONTO THE UNVALIDATED
   ONE — and it would be INVISIBLE IN THE OUTPUT.
```
🔒 **This is Rule 21's laundering pattern in a new place**: credibility travelling to a value that
did not earn it, because the two sit in one array. ⟹ **pre-reduction uses validated weights;
post-reduction stays §39.3 candidate 3 — a declared uncertainty axis, not a weighted point value.**

🟢 **And one thing is recoverable free**: V-3's residual measures the continuum's error, and the
continuum is *the same method* applied to the reduced species.
🔴 **Honest caveat that fixes the direction**: a radical anion is more polarisable with a more
diffuse charge distribution, so the continuum error is plausibly **larger** ⟹ **the transferred
residual is a LOWER BOUND, not an estimate.**
🔒 Same treatment ADR-015 gives capture–recapture: **a bound whose direction is known beats a point
value whose direction is not.**

### 🔴 Declared limitation for the final report — named, not absorbed
> **The post-reduction shell is computed by a route we knowingly could not falsify.**
> We accept it with a lower-bounded uncertainty **and we say so** — consistent with ADR-050's
> method-relative claims.

### Consolidated MLIP workflow (§39.25(b)) — every input now fixed
```
FIXED     D3 ON · PBE labels · ENCUT 520 · Li_sv · POTCARs /home01/q656a01/PBE_64
          periodic box · off-cluster ⟹ 0 cluster core-h
IN SCOPE  pre-reduction shell · SUPPORT and WEIGHTS · USE 2 production-admissible
OUT       post-reduction shell · anything entering the network as an energy
SAMPLING  ≥8–10 INDEPENDENTLY EQUILIBRATED seeds (not slices of one parent run)
          🔴 R̂ and ESS on the SHELL COMPOSITION, per variable — NOT on the energy
             (a liquid's potential energy decorrelates in ps; first-shell ligand identity does not.
              R̂ on energy reads ≈1 while the consumed quantity has not mixed at all.)
HANDOVER  extxyz with metadata IN THE COMMENT LINE · seed_id AND trajectory_id as separate columns
          · the validation manifest, since production settings inherit from it
E3 GUARD  same method on BOTH systems for the reported prediction; the MLIP quantifies what the
          continuum loses — a METHOD-VALIDITY statement, which transfers even though the model does not
```

### 🔒 Lead's own failure, recorded
The lead requested approval for **"B3"** across many turns **without ever describing what B0-D and
B0-F actually compute.** Corrected only when the user asked *"B3가 뭘 돌리라는 거야?"*
> **Asking for approval of an abbreviation is asking for a signature on something unread.**
proposer5 accepted the same fault for §39.5 leaving them as labels.

---

## ADR-077: **B0 build round** — four corrections, three of them to people correcting each other

**Date**: 2026-08-19 · **coder6 stages 1–2b + diagnostics · proposer5 §39.26–§39.29 · lead rulings**
**Status**: B0 package in build; `critic7` spawns the moment 2d lands (user instruction)

### 🔴 The MTD thermostat: three conditions, one variable at a time
```
condition            start geometry     bias    <T> final   T_eff/T_set   warning
MTD idealised        idealised          ON      625–680 K   1.56–1.70     YES
MTD pre-optimised    GFN2 --opt tight   ON      564 K       1.41          YES
plain MD pre-opt     GFN2 --opt tight   NONE    395 K       0.99          NONE
```
```
🟢 THE THERMOSTAT IS CORRECT — plain MD holds 395 K against 400 K, zero warnings
🟡 THE INPUT causes a large TRANSIENT (702 K vs 484 K over the first 200 steps) — ADR-067 again
🔴 THE BIAS POTENTIAL causes the PERSISTENT excess: 564 K vs 395 K from the SAME geometry, ~+170 K
```
🔒 **A metadynamics bias does work on the system by construction — it IS the search mechanism.
Elevated temperature is intrinsic to MTD, not a defect.** The pre-registered tree offered
"input" or "thermostat"; the answer was **"input partly, and mostly a third thing that is not a
fault at all."**

> 🔒 **A pre-registered decision tree protects against post-hoc rationalisation. It does not
> protect against an omitted variable.** Second instance — after R36.3, where a pre-registered
> trigger was written against a variable the filesystem did not have.
🟢 coder6 ran the plain-MD control **because the binary omitted a variable it could see in the
config it had just written** (`$metadyn` is a separate block from `$md`). It cost ~10 s.

### 🔴🔴 "An exact match between an assumed input and an observation is a FIT, not a confirmation"
```
proposer5's ASSUMED excess PE  0.30 eV   → ΔT = 258 K   vs observed 258.8 K   ← EXACT
coder6's MEASURED value        1.0495 eV → ΔT = 902 K   = 3.5× the observation
  E(idealised) − E(GFN2 optimised) = −20.575515 − (−20.614082) Ha   [MEASURED]
```
🔴 **The lead reported the exact agreement as "I verified the arithmetic myself".** It verified
nothing: the input was assumed, not measured.
🔒 proposer5's sharper diagnosis of its own error:
> *"The defect isn't that 0.30 eV was wrong. It's that I **solved for it** — took the observed ΔT,
> inverted the relation to get the ΔE that would produce it, judged that plausible, and presented
> the plausibility as support."*
> **One free parameter fitted to one observation matches by construction. The tighter it looks,
> the more persuasive the error.**
🟢 The conclusion survives — the measured excess is more than sufficient — **but the agreement was
never evidence, and the three-condition experiment is what decided it.**

### 🔴 U-55's observable was mis-chosen — kinetics for a curvature question
proposer5 withdrew its own §39.26(a) sentence (*"the dissociation rate is a direct measurement of
how floppy the cluster is"*).
```
U-55 asks about THE SHAPE OF THE PES NEAR THE MINIMUM — curvature.
A dissociation rate is KINETIC. And on an MTD trajectory it can NEVER be a rate at a defined
temperature, because the elevated temperature IS the search mechanism operating.
```
🟢 **The direct observable was already being computed** — B0-D runs opt+**freq** on every species:
```
ν_min · N(ν < 50 cm⁻¹) · HESSIAN CONDITION NUMBER (λ_max/λ_min over real modes)
🔴 Not a better proxy — CLOSE TO THE CAUSE. A quasi-Newton optimiser's convergence rate is
   governed by the Hessian condition number; many near-zero eigenvalues ⟹ ill-conditioned ⟹
   slow convergence. "Floppy" and "expensive to optimise" are connected MECHANICALLY.
⟹ correlate against MEASURED opt cycles and core-h over all 23 species.
  Holds ⟹ U-55 decided, AND a cheap predictor of which production species will be expensive,
           usable on species we have never run.
  Fails ⟹ the leading hypothesis is excluded.
🟢 cost ZERO · TEMPERATURE-INDEPENDENT · covers all 23, where a rate covered only those that
   happened to dissociate.
```
**The count survives as SEARCH HYGIENE**, relabelled *"dissociation events at an uncontrolled
effective temperature (1.41–1.70×, bias-driven, irreducible)"*.
🟢 And **arm 3 partially repairs U-60**: same species, both levels, same conformer — restoring the
cross-basis frequency comparison ADR-035 pre-registered and P1b lost. ⚠ Real modes, not the
imaginary one — **but that is the harder case: low-frequency modes are the most basis-sensitive
part of a Hessian.** Zero cost.

### 🔴 `T_eff` is not a constant, and not even a property of the engine
```
measured, SAME setpoint, SAME $md block:   1.70  /  1.41  /  0.96
xtb MTD   runs HOT      G16 ADMP expected to run COLD (T_eff ≈ T_init/2, U-53, unmeasured)
```
🔒 **Emit `temperature_requested_k` AND `temperature_measured_k`, never one field.** coder6 wrote
into the docstring that it must never become a stored correction factor — *"xtb runs at 1.65×" is
exactly the number that would get stored.*
🔴 **New U-75**: `ADR-047 §②` derives `T_eff ≈ T/2` for DRC from equipartition — *"평형 후 등분배
KE:PE = 1:1 ⟹ T_eff ≈ T/2"*, propagating to *"reach ∝ T ⟹ 합집합 1.402 → 0.70 eV"* and dropping
ADR-024's temperature ladder a rung. **Same shape as the 0.30 eV: a clean factor, derived not
measured, load-bearing for a scope decision** — and one of its premises is *a minimised starting
structure*, which is precisely what was just falsified for our inputs. **Not asserted wrong; flagged
as resting on an unmeasured factor of the class just falsified for a different engine.**

### 🔴 The guard's UNIT inverted the lead's reading
```
lead wrote     "B0 could submit up to 21,000 and nothing would stop it"
ResourceGuard  counts cores × wall_h ON THE MACHINE THE JOB RUNS ON = KNL core-h (plan.size_job:464)
RT-1's 21,000 KNL = 8,750 REFERENCE  ← BELOW B0's approved 15,000. MORE restrictive, not less.
correct guard  15,000 ref × κ 2.4 = 36,000 KNL — NUMERICALLY LARGER, a STRICTER ceiling
```
🔒 **Third unit failure of the session** (κ hardware-vs-workload · `cal·mol⁻¹·Å⁻²` vs `dyn/cm` ·
this). **A number in the wrong unit does not look wrong — it looks like the answer.** The lead's
looked like a *safety finding*, which is worse: it would have driven a change in the dangerous
direction.
🟢 Caught because coder6 **went to the code rather than to the lead's message.** The defence adopted
is structural: `B0_APPROVED_REFERENCE_CORE_HOURS = 15000.0` is the authority and **the KNL figure is
derived in one function and can never be typed independently.**

### 🔴 `xtb` writes its success banner to STDERR
```
lead-reproduced: rc=0 · "normal termination" in stdout ×0 · in stderr ×1
⟹ a Python runner testing stdout concludes EVERY xtb run failed — silently, holding a good trajectory
🟢 not a live defect (P3.sh uses 2>&1) — AND THAT IS WHY IT SURVIVED: a shell pipeline is immune,
   a Python runner is not, and we were about to write Python runners.
```
🔒 **Third direction the same lesson arrived from:** banner ABSENT and run fine (§0.2b-3) · banner
PRESENT with a thermostat fault · banner UNFINDABLE and run fine.
⟹ **The banner is not a health signal in either direction, on either stream.** `xtb_health()` judges
on **content** — frames produced, energies parsed and finite.

### Also landed
```
· guard 36,000 KNL + 6 h tripwire, BOTH halves: prevention (≤6 h wall) and DETECTION
  (a PBS-killed job writes `run` and never `finish` — without this it simply DISAPPEARS, and a job
  that vanishes from the accounting is how a ceiling is exceeded while every number looks fine).
  Works only because R31.2a put `cores`+`host` on the run append. Abort core-h labelled a LOWER BOUND.
· B0-D 19 → 23: an OPEN-SHELL STRATUM. The 19 were all closed-shell singlets while HALF THE
  PRODUCTION POOL IS OPEN-SHELL. u_cheap partitioned per stratum, NEVER pooled.
· HOMO/SOMO on all 23 — `charge < 0` was a proxy; gas-phase EC has a NEGATIVE adiabatic EA, so the
  neutral doublets are exactly where SOMO boundness is live and the proxy would skip every one.
· ε scan rides on B0-F: 27 SPs, zero cost. The true mixture ε must lie BETWEEN the pure components,
  so it bounds the error of not knowing ε WITHOUT knowing ε.
· stopping rule: "until the new-conformer discovery rate falls below threshold, capped at 20 ps",
  🔴 with the cap REPORTED WHEN IT BINDS, or a truncation looks like convergence (ADR-015 §1 at
  conformer scale).
· `.stale.2042619/` removed — it held the RT-1 round-2 package that FAILED (truncated module names).
  Recorded before removal. 🔒 coder6's addition to §45.1: OPEN the .stale and find out WHICH build
  it is — the tell was a directory NEWER than its contents.
```

---

## ADR-078: **arm 2 cut to 3 species** — and the input generator has no placement rule at all

**Date**: 2026-08-19 · **coder6 stage 2c · lead ruling + independent measurement**
**Status**: DECIDED (arm 2) · the geometry finding STRENGTHENS ADR-067

### 🔴 The finding: two hand-drawn Li placements that contradict each other
coder6 was told to build arm 2 out of `tools/make_p5_species.py`'s **own** ligand blocks and
`li_at()` placement — *"so the control is provably THE SAME PROCEDURE that made the contaminated
inputs, rather than your imitation of it."* It reused them, and found the generator contains
**only two Li complexes, both hand-placed, disagreeing in BOTH distance and angle.**

🔒 **Lead re-measured directly from the shipped `.xyz` files rather than accepting the report**
(R21: a confirmation is independent only if the value did not originate with us):
```
file                              n    d(Li–O)   d(O=C)   ∠Li–O=C
li_ec_cation.xyz                  11    1.850     1.200    180.00
li_ec_radical.xyz                 11    1.850     1.200    180.00
li_ec_radical_reactant.xyz        11    1.850     1.200    180.00   ← P1's ACTUAL TS endpoint
li_ec_radical_product.xyz         11    1.850     1.200    180.00   ← P1's ACTUAL TS endpoint
li_ec2_cation.xyz                 21    2.100     1.200     90.27
experimental                                               ≈138(2)°
```
🔴 **Both are wrong, in OPPOSITE directions from experiment**, and they differ from each other by
**89.7°** and by 0.25 Å. ⚠ **Only the 90.27° was ever written down** (§39.1(e-bis)). The 180.00°
appears in NO document — and it is the geometry P1's transition-state endpoints actually ran on.
🟢 **Lead found the two `_reactant`/`_product` files independently; coder6's report covered the
three `p5_species` files.** Same value, wider blast radius.

### 🟢 It STRENGTHENS ADR-067 rather than complicating it
ADR-067 blamed the 283 core-h non-convergence on an **over-symmetric start** — Li on a mirror
plane, several symmetry-breaking gradients exactly zero at t=0 — reasoning from the 90.27° file.
```
🔴 180.00° is ALSO a placement on a symmetry element: Li collinear with the C=O axis.
   And it is 180.00 EXACTLY — placed on the axis BY CONSTRUCTION, not landed there.
⟹ BOTH shipped complexes are pathologically symmetric, in TWO DIFFERENT WAYS, and neither
  symmetry was chosen — both were drawn. ADR-067 now rests on 5 files and 2 independent
  symmetry pathologies instead of 1 file and 1.
```
🔒 The generalisation this licenses: **hand-drawn = on a symmetry element**, because a person
drawing a complex places the atom on the axis or in the plane. That is a *reason* the input class
is pathological, not an observation that it happened to be. It is why C-9 exists.

### The ruling: arm 2 runs on the **3 shipped species only**; the other 20 are arm-1-only
coder6 offered (a) 3 shipped only · (b) all 23 with groups reported separately, never pooled ·
(c) drop arm 2. It implemented (b) and asked to be told (a): *"I would rather be told (a) than have
(b) quietly become 'the control said X'."* **Ruled (a).**

🔴 The two groups do not answer the same question, and that — not "genuine vs weaker" — is why:
```
shipped  (3)   RETROSPECTIVE  was RT-1's 283 core-h an artefact of the input WE ACTUALLY USED?
                              🟢 n=3 is not a small sample. It is the ENTIRE POPULATION of that
                              question — those are the only bad starts we ever paid for.
extended (20)  PROSPECTIVE    in production, does pre-optimisation pay for itself?
                              🔴 UNANSWERABLE HERE: the geometries come from a builder we do not
                              intend to ship. arm1⊖arm2 would vary because the invented rule
                              varied, inseparably from the species.
```
🔴 **The decisive fact, which coder6 could not have had**: ADR-077 removed arm 2's main job hours
earlier. U-55 is now decided by `curvature.u55_panel` against **arm 1's** measured opt cycles and
core-h over all 23. That panel needs **zero** species of arm 2.

🟢 Three things (a) buys beyond correctness:
```
· coder6's second concern DISSOLVES FOR FREE — `LI_OFFSET_Y_ANG = 4.24` was chosen for EC's
  carbonyl and had no business on an octahedral PF6⁻. Under (a) there is no PF6⁻ in arm 2.
  The question stops existing rather than being answered.
· ~20 opt+freq runs returned to a margin of 870 reference core-h on 15,000 — 5.8%.
· 🔒 A STRUCTURE THAT CANNOT BE MISREPORTED BEATS A WARNING NOT TO MISREPORT IT.
  coder6's (b) shipped a `warnings[]` entry telling the reader to separate the groups.
  The warning depends on the reader; the absence does not. Same shape as C-10.
```
⚠ **Knowingly accepted cost**: no naive-start data on any open-shell species. The naive-start
penalty is a GEOMETRY effect, not a spin effect, and buying open-shell coverage with an arbitrary
rule buys a number that cannot be interpreted.
🔒 `arm2.py`'s extended path stays in the tree, **unwired and tested**. If B1 needs a prospective
measurement it needs a *declared, consistent, documented* builder — written when it is the
deliverable, not as a side effect of a control.

### MTD sizing: approved at the **ceiling**, with three conditions
coder6 refused to extrapolate the 74 s MTD figure — correct: with a discovery-rate stopping rule,
per-species MTD wall time **is not a constant**, and a forecast would be a fabrication. Sized
against `max_time_ps = 20 ps` as a physical ceiling (§R24.1's ceiling-vs-consumption distinction).
```
· reservation and expected consumption REPORTED AS TWO NUMBERS, never one — a ceiling headline
  makes the batch look 3–4× its cost and I make a bad call on the margin
· 🔴 report WHEN THE CAP BINDS, per species. If the discovery-rate rule rarely fires and 20 ps
  terminates most species, the STOPPING RULE IS MIS-TUNED — and a truncation that is not
  reported LOOKS EXACTLY LIKE CONVERGENCE (ADR-015 §1 at conformer scale, third occurrence)
· 🔴 if the ceiling-sized reservation exceeds the guard, DO NOT RAISE THE GUARD (§R24.1).
  The available fixes — lower the cap, drop an arm, return to the user — are the lead's to choose.
```

### Also landed in 2c/2d-prep
```
· 🔴 UNIT TRAP CAUGHT STRUCTURALLY: λ ∝ ν² in mass-weighted coordinates, so the Hessian condition
  number is (ν_max/ν_min)², NOT ν_max/ν_min. The unsquared form understates the spread by a
  square root and 🔒 WOULD NOT LOOK WRONG — IT WOULD LOOK LIKE THE ANSWER (fourth unit incident).
  A test asserts the squared form AND that it differs from the unsquared one.
· the relabel went into the FIELD NAME — `dissociation_events_at_uncontrolled_effective_temperature`
  — because a field name travels into every downstream table and a document does not. The record
  also carries `is_a_floppiness_measurement: false` and a forwarding address to `curvature.u55_panel`.
· 🔴 NO correlation threshold hard-coded. `verdict` is `None`; "holds vs excluded" is proposer5's
  judgement against the reported n and ρ. Hard-coding a cutoff now is how −100 cm⁻¹ got into M2.
· arm 2 RAISES `PreoptimisationForbidden` if handed the pre-optimisation — an exception whose
  message says what would be lost, not a comment.
· ligand coordinates are IMPORTED via `importlib` from the real generator, not retyped; a test
  compares them against the files that generator wrote. Retyping one block fails 2 tests.
· coder6 self-reported a `.replace("identical","identical")` no-op inside an assertion. It passed
  and it tested something real — 🔒 which is exactly why the class costs us. §0.2b-4's shape.
```

---

## ADR-079: **U-75** — the `T/2` factor is correct physics derived for an engine that no longer carries the ladder

**Date**: 2026-08-19 · **proposer5 §39.30 · lead independently verified both line references**
**Status**: 🟡 **PARTLY RESOLVED — the finding is settled; the RESOLUTION is conditional on one fork**

### 🟢 The finding, verified at the lines rather than taken from the report
```
01_DECISION_LOG.md:3557   ADR-047 §② derives T_eff ≈ T/2  FOR DRC                       ✔ lead-confirmed
01_DECISION_LOG.md:3876   the 600/1000/1500 K (15/55/30) ladder AND `reach ≈ k_BT·ln(N·t)`
                          belong to (S2-B/C)                                            ✔ lead-confirmed
```
🔴 **A CATEGORY ERROR, not a numerical one.** ADR-047 derived the factor for **DRC — a
mechanism-following device** (stationary point, MB velocities, NVE). The ladder is now owned by
**(S2-B/C) reactive MD — a sampling device.** ADR-024's ladder was PM7/axis-3 and ADR-050/051
killed that engine. **The correction was derived for an engine and protocol that no longer exist
in the plan, and then applied to the ladder anyway.**

🟢 **The physics itself is correct and proposer5 looked for an error and did not find one.** For a
classical harmonic system in NVE started at a minimum, the microcanonical temperature is
`E/(N_df k) = T/2`. It raised and then **discarded an objection of its own** (that "reach" is
extremal and should follow total energy rather than the time-average) — it does not survive.
🔒 **Recording the discarded objection, because checking it was the work.** An answer that shows
what it rejected is worth more than one that shows only what it concluded.

**Four premises: P1 NVE/no thermostat · P2 true minimum · P3 harmonic PES · P4 equilibration.**
```
🔴 P1 IS FALSE for the engine that now carries the ladder — MEASURED, not argued: coder6's plain
   MD from an optimised structure holds 395 K against a 400 K setpoint, zero warnings, 0.96.
🔴 P4 ("평형 후") was ASSUMED AND NEVER CHECKED, doubly so: no equilibration time is given or
   estimated, and the trajectories are 10 ps and DELIBERATELY REACTIVE.
   🔒 A REACTIVE TRAJECTORY IS NEVER EQUILIBRATED — traversing to products IS THE POINT.
   The split is invoked over a window where its premise is unsatisfiable BY CONSTRUCTION.
```
And which ensemble is right is not close: NVE-from-a-minimum suits *following a mechanism*;
**NVT suits sampling, because `reach ≈ k_BT ln(Nt/τ)` needs a defined temperature to mean anything.**

### 🔴 This is a SCOPE RISK. The pre-registered documentation-fix branch DOES NOT FIRE
The lead pre-registered: *"if the ladder is identical under all three readings, U-75 is a
documentation fix and I close it as such."* It is not identical.
```
(i)   T_eff = T/2   300/500/750 K      reach 0.70 eV
(ii)  T_eff = T     600/1000/1500 K    reach 1.402 eV (1.381 with §④'s penalty)
(iii) proposer5's reading = (ii), by construction, once S2-C is NVT
```
1.40 eV covers essentially every elementary SEI barrier; 0.70 eV covers ring-opening and loses much
of the rest. 🔴 **And every `Ĉ_M` completeness claim is a claim about the REACHABLE SET**, so under
(i) all of them are claims about a much smaller one.
🔒 proposer5's framing, adopted: *"a scope risk whose resolution happens to be free, which is a
good position rather than a reason to downgrade it."*

### The proposed resolution — 🟡 CONDITIONAL, because proposer5's own measurement may break it
> *"Specify S2-C's reactive MD as thermostatted (NVT) at the ladder temperature; then `T_eff = T`
> by construction and U-75 closes by design. **Don't measure the factor — eliminate the condition
> that creates it.** Cost 0."* S2-C's protocol is not yet written, so this is a DECISION, not an
> experiment. 🟢 The right shape: **dissolve the condition rather than calibrate around it.**

🔴 **Lead's challenge, from proposer5's OWN §39.29 data:** `02_METHOD_SPEC §2.3` defines S2-C as
*"reactive MD 발견기 (MLIP **편향** MD / nanoreactor)"* … *"다수의 **고온/편향** MD"*.
**편향 = BIASED.** And the three-condition experiment measured:
```
MTD pre-optimised, THERMOSTAT WORKING CORRECTLY   T_eff/T_set = 1.41
plain MD pre-optimised, NO BIAS                   T_eff/T_set = 0.96
⟹ "specify it NVT ⟹ T_eff = T by construction" IS FALSE WHENEVER A BIAS IS ON.
  NVT is NECESSARY AND NOT SUFFICIENT. The thermostat is not what fails — the bias does work
  on the system, which proposer5 itself ruled is INTRINSIC TO THE METHOD, not a defect.
```
🔴 **And a consequence larger than the temperature**: under a bias, barrier crossing is driven by
**deposited bias**, not thermal activation. `reach ≈ k_BT·ln(N·t/τ)` presumes thermal activation.
⟹ under a biased protocol **the reach formula's FORM is wrong, not merely its T** — a bigger
correction than the factor of 2 just removed, to the same quantity, in an unknown direction.
🔒 And then ADR-051 §⑥'s `M`-definition at :3876 is **INCOMPLETE**: it names the temperature ladder
as a cutoff and names **no bias parameters**, so height/width/deposition rate would be undeclared
cutoffs — which violates that ADR's own rule that a completeness claim is unverifiable unless
every cutoff is named. **That matters independently of U-75.**

⚠ The slash in *"고온/편향"* is load-bearing and cannot be resolved by reading: "high-temperature,
i.e. biased" and "high-temperature and/or biased" are different specifications. **Returned to
§2.3's author.** If it was left open deliberately, it is an OPEN SPECIFICATION, not a reading
question, and that is itself the answer.

### 🟢 Lead's partial answer to the gap proposer5 named — offered to be attacked, not accepted
proposer5's own stated gap: *"I checked which engine owns the ladder and I checked that the
thermostat works. **I did not establish that nobody needs NVE.**"* Lead's reasoning:
```
NVE buys (1) energy conservation as a FREE integrator-quality diagnostic — real, but replaceable
        by monitoring a Nosé–Hoover chain's conserved quantity
        (2) unperturbed dynamics — matters only when a RATE is read off the trajectory
🔴 NOTHING DOWNSTREAM READS A RATE OFF S2-B/C. It is a discovery device feeding the append-only
   ledger; rates come from S3 barriers and S4. ⟹ thermostat perturbation costs CAPTURE
   PROBABILITY, not any reported number.
```
If a third thing NVE buys exists, that is the answer that settles it.

### 🔒 Rule 29 (new)
> **When a correction factor is inherited, re-check WHICH ENGINE IT WAS DERIVED FOR before
> re-checking its arithmetic.** ADR-047's factor was arithmetically flawless and applied to the
> wrong protocol, and no amount of verifying the algebra would have found that. Same family as
> rule 20 (a proxy that worked for a different code) — **this is that rule for a NUMBER rather
> than a CHECK, which is why it evaded a team that had already learned rule 20.**

---

## ADR-080: **C-9 is broadened** — hand-built geometries are systematically symmetric, not randomly wrong

**Date**: 2026-08-19 · **proposer5 §39.30(e), independently re-measured · lead ruling**
**Status**: C-9 spec AMENDED · cheap half in 2d · point-group detection deferred to production

### 🔴 C-9 as written misses four of our five files
C-9: *"never submit from a guess whose heavy atoms are all coplanar."*
```
li_ec2_cation                   Li on a MIRROR PLANE      ∠Li–O=C =  90.3°   −48° from ≈138°
li_ec_cation / li_ec_radical /
  _reactant / _product          Li on a C2 ROTATION AXIS  ∠Li–O=C = 180.0°   +42°
```
proposer5 re-measured all four rather than taking the lead's numbers, and supplied the mechanism:
**EC alone is C2v with its C2 axis along y, and Li at `(0, 4.240, 0)` sits ON that axis**, so the
complex stays C2v — exactly as `li_ec2`'s Li sits on a mirror plane.
🔴 **A collinearity on a rotation axis is NOT a coplanarity. C-9's test cannot see it.**

### 🔒 The generalisation — worth more than the confirmation
> **Hand-built geometries are not RANDOMLY wrong, they are SYSTEMATICALLY SYMMETRIC.**
> A person placing an atom "sensibly" puts it on an axis or in a plane *because that is what looks
> right* — and **symmetry is the worst possible direction of error for an optimiser**, because the
> gradient along the symmetry-breaking coordinate is **exactly** zero at t=0.
> Two files, two different implicit rules, both landing on a symmetry element is what that bias
> predicts. ⚠ n=2 SUPPORTS rather than establishes — but the mechanism is standard practice, not
> a fit to our data.

**C-9 REVISED**: *never submit from a guess in which any atom lies on a symmetry element of the
remaining fragment — axis, plane, or centre — unless the species genuinely has that symmetry.
Detect the point group and perturb off it.*

### The ruling: cheap half now, detector later
Full point-group detection is production work. **B0 barely exercises C-9** — arm 1 starts from GFN2
`--opt tight` conformers, and arm 2 uses the three shipped files **deliberately unperturbed**,
because reproducing the bad start IS the control. What must not ship is a check that reads as a
guarantee it does not give:
```
· the check must NOT be readable as a symmetry check — put it in the NAME, since a name travels
  into every downstream table and a docstring does not (coder6's own mechanism, reused)
· EMIT WHAT IT EXCLUDES, as data: the symmetry elements not covered (rotation axes, inversion
  centres, improper axes), so coverage cannot be inferred where there is none. §R19/§R20.
· a cheap targeted collinearity test ONLY if genuinely cheap. 🔒 If it starts growing, STOP and
  emit the exclusion — an honest gap beats a half-built detector that passes for the wrong reason.
🔴 scope-protected: if it exceeds ~1 h, the whole C-9 item moves to after critic7. A late 2d costs
  more than a delayed annotation, because critic7 is idle until 2d lands.
```
⚠ `COPLANAR_TOL_ANG 0.10 Å` / `OUT_OF_PLANE_KICK_ANG 0.25 Å` remain open as *values*, but
**the test they parameterise is the wrong test for four of five files.** A better tolerance on a
test that cannot see the failure buys nothing. To be said in the constants' own comment.

### 🟢 Arm-2 ruling independently confirmed, with a stronger reason than the lead's
proposer5 found no downstream consumer of a per-species naive-start penalty (U-55 is on the
curvature panel against **arm 1**; production uses arm 1; engineer5's pool failure-rate term is
arm 1; arm 3's `r_high` uses arm 1's conformer; §39.27(a) already routes B0-F's endpoints through
arm 1), and added the reason the lead did not have:
> 🔒 **"Arm 2's question is RETROSPECTIVE — *was the number we already published an artefact?*
> Extending it to 20 would be asking a retrospective question about species for which we never
> published a number."**

🟢 **ADR-067 is strengthened, not complicated**: with Li on the C2 axis the P1 complex is **C2v, not
merely Cs** — MORE frozen coordinates, so a low-curvature symmetry-breaking imaginary mode is
*more* likely, not less. No conclusion is disturbed (the IRC verdict is geometry-independent at
ΔE = 80 µeV; the topological-distinctness check involves only C and O; §39.28's 1.0495 eV was
**measured on the actual file**; B0-F never sees this geometry).

### 🔒 Rule 30 (new) — proposer5's self-reported defect, and it refused to inflate it
> §39.4(g) said Li sits *"in a linear C=O···Li arrangement"* — **the linearity was OBSERVED and
> never QUANTIFIED**, while §39.14(g) quantified the analogous 90.3° against experiment and called
> that file *"wrong against measurement"*. **Same defect in two files; a measurement applied to one
> and a qualitative word to the other.** 180° is +42° where 90.3° is −48° — comparably wrong — and
> it was listed as one item among five rather than as the file's largest structural error.
>
> **Rule 30: a qualitative word where a number was available is a measurement not taken. Asymmetric
> application across comparable objects is the tell — the file that got the word looks fine next to
> the file that got the number.**

🟢 proposer5 declined to hold its own shutdown over this: *"no inference moves; the correction is to
the completeness of a description, not to a conclusion — **and inflating it would be the mirror of
the error I have spent this round guarding against.**"* Correct, and recorded because calibrating a
self-reported defect *downward* is as much a discipline as reporting it at all.

### engineer5 shut down
`03_COMPUTE_PLAN.md` flushed with a READ THIS FIRST block (LIVE table, SUPERSEDED table with line
refs, rules, open items); VASP's ①/② split placed in three locations. Its parting risk — the line
it predicts will fail next — is recorded in `05_STATE.md §0-h` **with its direction**, which is the
part that could not be written from inside its own document.

---

## ADR-081: **U-75 resolved in form** — the reach claim is made only over methods whose reachable set is defined

**Date**: 2026-08-19 · **proposer5 §39.30(f) · lead ruling + lead measurement of the xtb binary**
**Status**: FORK RULED · 🔴 one blocker discovered by measurement, routed

### 🟢 §2.3 was an OPEN SPECIFICATION, not an ambiguous sentence
proposer5, reading its own text as its author: **it used 편향 in two senses within four lines** —
the title's *"MLIP 편향 MD / nanoreactor"* means a **bias method**, while item (2)'s
*"고온 편향은 분기비를 왜곡한다 (Arrhenius 외삽…)"* means **the statistical skew from running hot.**
Item (2)'s concern is thermal and not a metadynamics concern at all — a bias potential does not
distort branching through Arrhenius; it distorts it by depositing bias in visited wells.
🔒 §2.3 is a **candidate survey** (same `놓치는 반응 유형 / K1 / K2 / 고유 가치 / 예상 크기`
template as S2-A and S2-B). It describes what S2-C *could* be; it never specified what it *would*
be. **The slash is a genuine and/or ⟹ a decision to take, not a reading to recover.**

### The ruling: **(i) + the ledger/denominator split**
```
UNBIASED NVT at the ladder   declared method, CLOSED-FORM reach → CONTRIBUTES TO Ĉ_M
BIASED / nanoreactor         additional discovery → APPEND-ONLY LEDGER,
                             🔴 EXCLUDED from the reach claim
```
🔒 **ADR-027's ledger/working-network split applied one level up: the ledger takes everything; the
CLAIM is made only over methods whose reachable set is defined.** A reaction found only by the
biased arm is still found, still recorded, still enters the network — **it simply does not enter
the denominator.** Costs nothing scientifically.

🟢 **The deciding argument is transferability, not convenience** (proposer5):
> Under (ii) there is no closed form, so **the reachable set becomes a PER-SYSTEM MEASUREMENT.**
> For an unstudied electrolyte we could not know what reach our schedule achieved without measuring
> it there — 🔴 **the known-answer dependency ADR-014 outlawed, arriving through a HYPERPARAMETER
> instead of through a species list.**

🔒 **Generalised (lead)**: *any* quantity that must be measured per-system to interpret our own
claim reintroduces ADR-014's dependency, whatever it is called. New attack surface, transferable.

⚠ **Accepted cost, recorded as accepted rather than solved**: unbiased thermal MD is the weaker
discovery engine, and §2.3's own item (3) — rare bimolecular events essentially unsampled — bites
hardest exactly on the channel to the gas products.

### 🔴🔴 NOT ALL NVT IS CANONICAL — and the fix specified does not exist in the engine
proposer5's §5, which attacked its own §39.30(b):
```
Berendsen holds ⟨T⟩ well and DOES NOT sample the canonical ensemble (velocity rescaling
suppresses fluctuations). 🔴 reach ≈ k_BT·ln(N·t/τ) DEPENDS ON THE TAIL, NOT THE MEAN.
🔴 Our only measurement (0.96) confirms EXACTLY the quantity Berendsen holds well.
```
🔒 proposer5: *"the check (mean temperature) standing in for the property (canonical distribution)
— and I supplied that check myself in §39.30(b) as though it settled the ensemble."* **Rule 20's
shape for the fifth time this session, this time inside the work that was correcting it.**

It marked *"xtb's `$md` default is Berendsen"* as `[TO BE VERIFIED — not asserted]`.
🔴 **Lead verified against the shipped binary. The result is STRONGER than the hypothesis:**
```
strings vendor/xtb/bin/xtb | grep -iE "berendsen|nose|hoover|langevin|andersen|bussi|csvr|thermostat"
  → "Berendsen THERMOSTAT on"
  → "thermostating problem"
  → NOTHING ELSE.                  namelist: `nvt=$` is a BOOLEAN TOGGLE, not a selector.
```
🔴 **xtb 6.7.1 contains exactly ONE thermostat and it is Berendsen.** No Nosé–Hoover, no Langevin,
no Andersen, no Bussi/CSVR. ⟹ *"specify a Nosé–Hoover chain or Langevin thermostat — cost zero"*
**is not a specification we can meet on that engine. It is not a config change; the option is absent.**
🟢 The underlying point survives fully and is the important half. Only the remedy failed.

**Three routes, ranking requested from proposer5 (not a survey):**
```
(A) reach-claiming arm → MLIP + LAMMPS. LAMMPS has `fix nvt` (Nosé–Hoover chain) and
    `fix langevin`, is ALREADY PERMITTED, and is already how the MLIP parallelises.
    ⚠ but the MLIP has NO CHARGE CHANNEL and reduced species are NOT in training (U-64,
      user-confirmed) — which is the chemistry S2 exists to find.
(B) keep xtb and BOUND the fluctuation deficit rather than eliminate it. Name the measurement.
(C) xtb-Berendsen MD → LEDGER, OUT OF THE DENOMINATOR, consistent with §3's own rule.
    🔴 may gut the denominator. **If (C) leaves it too thin to support `Ĉ_M`, that is a FINDING,
    not a failure, and it is far better heard now than after S2 runs.**
```

### 🔒 Rule 31 (new)
> **A remedy is not free until the option is confirmed to EXIST in the engine.** "Specify X, cost
> zero" prices the *decision* and silently assumes the *capability*. Here the decision was free and
> the capability was absent, and the gap was invisible from any document — only the binary had it.
> ⟹ **`strings` on the actual binary is a zero-cost capability check. Run it before pricing a
> specification at zero.**

### 🟢 The M-definition needs more than the lead asked for
If (ii) were ever taken, :3876 would need hill height, deposition interval and width — and
proposer5 named the one the lead did not: 🔴 **the collective-variable definition, which determines
the reachable set far more than the hill parameters do, and is the parameter most likely to be
omitted because it is a CHOICE rather than a NUMBER.** Under (A) the thermostat likewise joins the
M-definition alongside the ladder. 🔒 **A hyperparameter that is a choice hides better than one
that is a number, and ADR-051 §⑥'s rule is only as good as the list it is applied to.**

---

## ADR-082: **U-75 CLOSED** — reach is declared as an upper bound; (C) would have removed the estimator

**Date**: 2026-08-19 · **proposer5 §39.31 (final) · lead verified the disqualification at the lines**
**Status**: 🟢 **U-75 CLOSED.** No user decision. proposer5 shut down.

### Ranking: **(B) ≫ (C) > (A)**

**(A) disqualified on CHEMISTRY, not plumbing.** The MLIP has no charge channel and reduced species
are not in training (U-64), and §39.21.3 established that is **architectural, not a data gap**.
🔴 **S2 exists to discover reduction chemistry; an engine that cannot represent the reduced species
would sample the unreduced electrolyte forever and never find a reduction reaction.**
🔒 **A correct thermostat on absent chemistry is worth nothing.** Generalises past this decision.

**(C) — the lead asked the wrong question and proposer5 answered the right one.**
Lead asked *"does the denominator stay thick enough?"*
```
SURVIVES   S2-A enumeration (reach from its OWN cutoffs — no temperature anywhere)
           S2-B TS-search-on-edits
🔴 WHAT DIES IS NOT COVERAGE — IT IS THE ESTIMATOR.
```
🔒 **Lead verified at the lines rather than accepting it, because it carries the whole ruling:**
```
01_DECISION_LOG.md:3862  "이미 돌린 궤적을 분할만 한다"      D1 OPERATES ON MD TRAJECTORIES  ✔
01_DECISION_LOG.md:3865  "⚠ 축 1(결정론적)에는 난수가 없다"   axis 1 carries NO randomness    ✔
```
⟹ **removing the xtb MD removes the ONLY stochastic source D1 requires — and D1 is what made
2-source capture–recapture work after axis 3 was dropped.** (C) is consistent in form and
**structurally disqualifying in effect.** A form-consistent option that silently deletes the
estimator is precisely the kind the lead would have taken.

### 🟢 (B) — the answer, and it costs nothing
```
MEASUREMENT (a statistic over frames WE ALREADY HAVE):
  canonical   Var(T_inst) = 2T²/N_df
  measured    Var(T_inst) from the trajectory
  DEFICIT     f = Var_meas / Var_canon     ← REPORT IT. DO NOT CORRECT WITH IT.
🔴 DIRECTION IS KNOWN: Berendsen suppresses fluctuations ⟹ fewer high-energy excursions
   ⟹ THE CANONICAL FORMULA OVERSTATES REACH.
```

🔴 **The error is a mislabelled SET, not a wrong `Ĉ_M` — and this is the part the lead had wrong.**
The lead was treating the fluctuation deficit as something that might bias `Ĉ_M`. It does not:
`Ĉ_M = 1 − f₁/N` comes from observed discovery statistics and correctly estimates coverage of
**whatever was actually sampled.** What is corrupted is **the LABEL**: we would say *"95% of
everything up to 1.4 eV"* having achieved 95% of everything up to something less.
🔒 **An overclaim about SCOPE, not about COVERAGE.**

🟢 **⟹ The fix is one character and it is free: declare reach as an UPPER BOUND — `≤ 1.4 eV` —
with the measured `f` printed beside it as the evidence that it IS a bound.** Same treatment
ADR-015 gives capture–recapture. §39.25(c): **a bound whose direction is known beats a point value
whose direction is not.**

🔒 **No user decision. proposer5 declined an escalation channel the lead had explicitly offered**
— *"I'm not manufacturing an escalation"* — on the grounds that (B) changes no tool, no scope, no
budget, and declaring a bound instead of an estimate is within our discretion. The only thing the
user ever sees is a reach line reading `≤` rather than `=`. **Recorded because the failure mode
being guarded against was inventing a decision to hand upward.**

### The two constants — both of coder6's nominations resolved, both upward
🔴 **`NOISE_FLOOR_CM1` — REMOVED. The floor was the wrong instrument.** With trans/rot projected
out, a genuinely sub-1 cm⁻¹ internal mode is essentially never physical for a bound complex (a
near-free methyl rotor is ~10–30 cm⁻¹; a floppy Li–O torsion ~5–20) ⟹ it is a **convergence
artefact**, and coder6's two failure directions are **not symmetric** — the assumption the floor
was chosen under.
> 🔴 proposer5, past both of us: **"The condition number is the wrong summary statistic. One mode
> moving it 3,600× means it isn't a robust predictor — a floor only decides WHICH SINGLE NUMBER
> DOMINATES."** The lead was arguing about where to put the floor.
```
1  remove the floor
2  TRIMMED κ_k = (ν_max/ν_(k))², k DECLARED, reported for k = 1, 2, 3
   🔒 coder6's own mechanism — the choice in the DEFINITION — applied to the STATISTIC,
      where the fragility actually lives
3  🟢 KEEP the sub-5 cm⁻¹ count, RELABELLED a CONVERGENCE DIAGNOSTIC, not physics.
   🔴 A species with many such modes is telling us ITS OPTIMISATION DID NOT CONVERGE —
      WHICH IS U-55's QUESTION. **The thing the floor discarded is itself a measurement of the
      property under study.** Same shape as the MTD dissociation count: RELABEL, DON'T DISCARD.
      Twice in one day.
🟢 FREE FALSIFIER, unrequested: is the κ–cost correlation STABLE ACROSS k?
   present only at k=1 ⟹ driven by one artefact mode, SPURIOUS
   stable across k=1,2,3 ⟹ real, and U-55 is genuinely decided
   ⟹ the predictor finally has a way to FAIL, which is what it was missing.
```
🔴 **`SOFT_MODE_CM1 = 50.0` — proposer5 broke its own rule setting it, and found it itself.**
§39.4(c) on `Ω_min`: *"Do NOT hard-code a threshold this round. That is how −100 got there."*
It wrote `SOFT_MODE_CM1 = 50` **two sections later** — same object, a threshold under a
decision-making observable, asserted rather than calibrated.
🟢 **Ruling: make it not need calibration.** Report `n_soft` as a **curve** `N(ν < x)` for
x = 10, 25, 50, 100, 200 cm⁻¹ ⟹ the threshold is visible, the correlation picks whichever x
actually predicts, **and that becomes the calibration — measured rather than asserted.**
⚠ **Until the curve exists, `50` is `[ASSERTED]` and may not be cited as calibrated.**

🔒 proposer5: *"Third time this round the same move resolved a threshold I couldn't justify — the
ε bracket, the two bias settings, and now this: **design so ignorance of the right value doesn't
block us, and let the data pick.**"*

### 🔒 Rule 32 (new)
> **A rule written about one object does not transfer to the next object of the same kind without
> someone checking — and the AUTHOR is the least likely person to notice, because they know they
> already wrote it.** proposer5's `Ω_min` rule and its own `SOFT_MODE_CM1`, two sections apart.
> **Fourth distinct instance this session of a defence that existed and was not applied one step
> sideways** (rule 20's CP2K→VASP; the PFL trigger variable; the thermostat decision tree's
> omitted bias variable; this).

### 🔴 Registered while verifying — U-52 inherits the category error
`:3896` **U-52** reads: *"G16 ADMP thermostat 미확인: `T_eff ≈ T_init/2` 예상. 🟢 **ADR-047 DRC
보정과 같은 형태이므로 기구 이식 가능**하나 인자 실측 필요."* — it plans to **port ADR-047's
mechanism to ADMP.** ADR-079 established that mechanism was derived for the wrong protocol.
⟹ **U-52's transplant is a transplant of a category error**, and it carries the same warning:
*"보정 없이 쓰면 ADR-024 사다리가 한 단 어긋나고, 크래시 없이 그렇게 된다."*

### proposer5 shut down
`§39` closed at `§39.31` with `§39.0`'s resume block current. It reversed **three of its own
positions** this round — the floppy-manifold hypothesis, §39.26(a)'s observable, and §39.30(b)'s
ensemble claim — **each time before anyone caught it, and each time naming the sentence it was
withdrawing.** 🔒 Two of this round's four largest findings came from it attacking its own work
rather than someone else's. Re-spawn under a NEW name; `§39.0` is what the successor gets.

---

## ADR-083: **U-55's primary endpoint is PRE-REGISTERED** — 18 correlations at n=23 select a winner by construction

**Date**: 2026-08-19 · **coder6 stage 2d · lead ruling**
**Status**: PRE-REGISTERED BEFORE ANY DATA EXISTS. Reopenable by a proposer; not by a result.

### 🔴 The ladders made the fragility a measurement, not an argument
On a frequency list carrying one 0.4 cm⁻¹ artefact mode:
```
κ_1 (untrimmed)   20,475,625     ← ONE mode
κ_2                    3,365.5   ← trimming ONE mode recovers the clean value EXACTLY
κ_3                    1,692.2
```
**A factor of 6,000 between k=1 and k=2, from a single mode.** proposer5's *"the condition number
is the wrong summary statistic; a floor only decides WHICH SINGLE NUMBER DOMINATES"* (ADR-082) is
no longer an argument. ⚠ **But this came from a SYNTHETIC fixture with a deliberately inserted
mode. It demonstrates the FRAGILITY; it is not evidence about our species** — and it must not be
used to choose k, which would be ADR-077's "a fit is not a confirmation" in a new costume.

### 🔴 The real defect is not readability — it is multiple comparisons
3 predictor families × the ladders × 2 responses = **18 correlations at n=23 species.**
coder6 named it itself in a caveat: *"picking the largest of 18 coefficients is a
multiple-comparisons selection; treat this as a POINTER into the table, never as the result."*
🔒 **A caveat depends on the reader — and the reader is a tired lead looking for an answer.
Replaced with structure.**

```
PRIMARY (decision-making, pre-registered 2026-08-19)    κ_2  vs  opt_cycles
SECONDARY (exploratory pointers, NEVER decision-making) the other 17
```
**Rationale — and it had to be available BEFORE the data, which is the test it must pass:**
- **`opt_cycles`, not `core_hours`.** proposer5's mechanism is that a quasi-Newton optimiser's
  convergence *rate* is governed by the Hessian condition number; **cycles is the direct observable
  of that rate.** Core-hours confounds it with system size and level — a real effect pointing the
  same way, which is **U-59's trap** (input quality degrades with size, confounded with genuine
  scaling *in the same direction and with a similar shape*).
- **k=2, not k=1 or k=3.** k=1 is dominated by the single lowest mode, **a priori the mode most
  contaminated by incomplete convergence** — proposer5's mechanism, not an observation about our
  numbers. k=3 discards more than the argument requires. **k=2 is the minimal trim.**

🔒 The pre-registration, its date and its rationale go **in the output**, so the report carries the
commitment rather than a later document claiming one was made.

### 🔴 A circularity inside proposer5's own design, closed
ADR-082 ruled the `n_soft(x)` curve *"the calibration — measured rather than asserted."* Correct as
far as it goes, and incomplete:
> 🔒 **The curve CALIBRATES x. The same data cannot then VALIDATE the predictor at that x.**
> Selecting x on a dataset and quoting its ρ from that dataset is circular — the coefficient is
> inflated by the selection.
```
n_soft(x) curve → role: CALIBRATION ONLY. Selects x. Does NOT validate.
                  🔴 the ρ at the winning x may NOT be quoted as evidence the predictor works.
                  Validating the calibrated x needs a SECOND dataset — B1 can supply it.
```
Recorded as a **role field in the output**, not prose, so a later quotation is refuted by the
record itself. **Third instance of the selection-then-confirmation family** (the 0.30 eV fit;
the "expected value derived from our own code", rule 22; this).

### Reading order for the B0 report — four things, not eighteen
```
1  kappa_stability FIRST. Correlation only at k=1 ⟹ STOP: the rest is one artefact mode.
2  the PRIMARY cell: κ_2 vs opt_cycles, with n_used and n_dropped beside it.
3  n_convergence_artefacts — many ⟹ that species' optimisation did not converge, which changes
   what row 2 means.
4  everything else, only if 1–3 leave a question open.
```
🟢 **The full table stays.** The ladders are the point, and an auditable table beats a curated
summary that cannot be checked.

### Also landed
```
· NOISE_FLOOR_CM1 REMOVED, with a test asserting `hasattr(...)` is False so it cannot return quietly
· SOFT_MODE_CM1 = 50 kept ONLY as a historical label, marked `[ASSERTED] not calibrated`, with a
  test asserting the marker survives ⟹ it cannot be cited as calibrated
· sub-5 cm⁻¹ modes KEPT and relabelled `n_convergence_artefacts`
  🔒 THIRD TIME IN TWO DAYS the answer was RELABEL, DO NOT DISCARD — the MTD dissociation count,
     C-9's coverage, and now these. Each time the thing about to be thrown away was a measurement
     of the very property under study.
· symmetry_trace() at three checkpoints (preopt input · post-MTD conformer · final DFT geometry).
  🔴 `symmetry_broke = None` when fewer than two were measured — "cannot be told" MUST NOT fall
  toward "it broke" (rule 18, reached for unprompted for the third time). "Nothing symmetric at the
  start" is reported as NOT a breaking failure — a different fact.
· 🟢 imaginary_mode_verdict() — the suspected gap was REAL: the count WAS shared between B0-D
  minima (want 0) and B0-F transition states (want exactly 1). **SAME COUNT, OPPOSITE EXPECTATION**
  — nasty because neither side looks wrong alone. Now directional, and an imaginary mode on a
  supposed minimum points at the symmetry fingerprint as the likely cause.
· 🔴 NOTHING IS PERTURBED. `_is_instrumentation_only` is in the output and a test asserts the wording.
· coder6 self-report: changing scalars to ladders broke `b0_species_panel` (5 ERRORs) because the
  panel was COPYING curvature fields into its own record — a second copy that drifted the instant
  the source changed. Repaired to ONE SOURCE (`flatten_predictors()`) rather than by adding three
  more copies, with the reasoning written at the site. ⚠ **A green module test is not a green
  tree**: the sub-suite was 34 OK while the package was broken.
```

---

## ADR-084: **U-67 CLOSED at 2.75 Å** · the real G16 eigenvalue block arrived and carried four traps

**Date**: 2026-08-19 · **user supplied both · lead verified the block before relaying it**
**Status**: 🟢 U-67 CLOSED · orbital parser's `[UNVERIFIED]` closable on the eigenvalue half

### 🟢 The block is provably the P1 TS species — three independent facts agree
```
n_alpha_occ 25 · n_beta_occ 24  ⟹ multiplicity 2   matches the report's charge 0 / mult 2
25 + 24 = 49 electrons          ⟹ charge 0 for     C3H4LiO3 = 3(6)+4(1)+3+3(8) = 49
C3H4LiO3                         is the IRC endpoint fragment in `pilots[0].detail.irc`
```
🔒 Not a plausible-looking log — **the same calculation**, cross-checked against two fields it could
not have been fitted to. **Lead extracted this with a regex rather than by eye**, per rule 21.

### 🔴 FOUR TRAPS, two of which would have silently halved the parse
```
1  LEADING WHITESPACE DIFFERS BY SPIN
   ' Alpha  occ. eigenvalues --'   ONE leading space
   '  Beta  occ. eigenvalues --'   TWO leading spaces
   🔴 `^Alpha|^Beta` matches EVERY alpha line and NO beta line ⟹ 25 of 49 orbitals, a
      clean-looking HOMO, and NO ERROR. Use `^\s*`.
2  `occ.` TAKES TWO SPACES, `virt.` TAKES ONE
   'Alpha  occ.'  vs  'Alpha virt.'
   🔴 a single literal space misses every OCCUPIED line and matches only the VIRTUALS
      ⟹ it returns a HOMO that is actually a LUMO. Use `\s+`.
3  🔴🔴 THE BETA LUMO IS NEGATIVE: −0.00368  (alpha LUMO +0.03618)
   ⟹ OCCUPANCY MUST COME FROM THE `occ.`/`virt.` LABEL, NEVER FROM THE SIGN.
   ⚠ and this bites hardest exactly where we are least covered — the REDUCED species, where
     the SOMO can genuinely be positive.
4  🔴 HOMO ≠ SOMO, AND THEY COINCIDE HERE BY LUCK
   alpha HOMO −0.30464 · beta HOMO −0.34581 ⟹ max = −0.30464, correct on THIS log
   but  HOMO = max(alpha_homo, beta_homo)   ·   SOMO = alpha[n_alpha−1] when n_alpha > n_beta
   🔴 in a strongly spin-polarised species the beta HOMO can sit ABOVE the alpha HOMO, and then
      "the higher" returns a DOUBLY OCCUPIED orbital and calls it the SOMO.
      **A test can be right about one and wrong about the other.**
```
⚠ **Values per line are NOT constant**: 5 normally, **4** on the last beta occ line, **1** on the
last alpha virt (44.62393). A parser assuming 5 drops or invents entries.
🔒 **One risk this log does NOT cover, kept declared**: Gaussian's fixed-width fields let
large-magnitude values run together with no separator (`-100.12345-99.12345`). Everything here
separates cleanly. **One real log validates the shapes it contains and nothing else** —
`format_validation()` must record WHICH shapes it has now seen.

### 🟢 U-67 CLOSED — Li–X RDF first minimum fixed at 2.75 Å by the user
```
graph_layers.json   Li-O: 2.4 [PLACEHOLDER-ESTIMATE]  →  2.75 [MEASURED, MLIP RDF first minimum]
```
🔴 **Widening by 0.35 Å. Every Layer-I R2/R3 endpoint verdict computed under 2.4 was PROVISIONAL
and must be RECOMPUTED, not grandfathered.**
🔴 The provenance string names P1/**P2** as the intended source and **P2 was deleted (ADR-033)** —
it has been pointing at something that does not exist. Source is now the user's MLIP RDF.
🟢 **A first minimum is the right place to cut** — the radial density is lowest there, so membership
is least sensitive to small geometry changes. **2.4 Å was not merely a guess; it was a guess
INSIDE the shell.**
⚠ The user wrote **Li–X**, generically ⟹ applied as a non-element-resolved cutoff and **marked as
such**, so nobody later assumes a per-element table exists.

### 🔒 Rule 33 (new)
> **A supplied artefact must be verified against something it could not have been fitted to, before
> it is used to validate anything.** Here: electron count from the molecular formula, and
> multiplicity from a separate report field. **Both were derivable without trusting the block, and
> both agreed.** Without that step, "the parser matched the sample" only shows the sample matched
> the parser. Companion to rule 21 — 21 is about who produced a *number*, 33 is about what
> independently constrains an *artefact*.

---

## ADR-085: **the real log found two bugs** — one predicted, one that only exists where the concept does not

**Date**: 2026-08-19 · **coder6 · lead ruling on the reading order**
**Status**: orbital `[UNVERIFIED]` CLOSED for the shapes the block contains · U-67 applied

### 🟢 `format_validation()` on the user's real block
```
orbital_format_recognised True · orbital_lines_matched 12 · orbital_verdict matched
n_alpha_occ 25 · n_beta_occ 24 · derived multiplicity 2 · total electrons 49
alpha_homo −0.30464 · beta_homo −0.34581 · alpha_lumo +0.03618 · beta_lumo −0.00368
```
🟢 **Traps 1–3 the parser already survived**: `RE_EIGEN` uses `^\s*` and `\s+`, and occupancy comes
from the `occ.`/`virt.` label. `bound.py`'s use of the sign is for **boundness, not occupancy** —
correct, and now stated at the site rather than left to be re-derived.

### 🔴 Trap 4 was a real bug — HOMO returned under the SOMO's name
`highest_occupied` returned `max(all occupied)` as `homo_or_somo`. **Right on this log by luck.**
```
homo_hartree   max(alpha_homo, beta_homo)                 → what the BOUND check consumes
somo_hartree   alpha[n_alpha − 1] when both spins present → the orbital with no beta partner
warns          homo_is_not_the_somo when they diverge
```
🔒 **The existing beta-higher test asserted the HOMO and was SILENT about the SOMO** — right about
one, blind to the other, which the lead could only suspect. **A test can be correct and still not
cover the thing it appears to cover.**

### 🔴🔴 The second bug — and it is the more valuable one
```
a RESTRICTED (RKS) log prints ONLY `Alpha occ.` lines and NO Beta block  ⟹ n_beta = 0
⟹ `n_alpha > n_beta` fires ⟹ EVERY closed-shell species reports a SOMO for a DOUBLY-OCCUPIED
   orbital — ALL 19 of B0-D's closed-shell singlets, silently, into bound.py.
```
🔴 **coder6 introduced it WHILE FIXING TRAP 4**, and caught it only because the closed-shell fixture
failed. Fixed by requiring **both spin sets present**; `is_unrestricted` is emitted rather than
inferred, and a restricted log derives multiplicity 1 with a note that every orbital is doubly
occupied.

### 🔒 Rule 34 (new)
> **A fix that splits one concept into two must be checked against the inputs where the SECOND
> concept DOES NOT EXIST.** Trap 4 split HOMO from SOMO; the RKS case is where "SOMO" has no
> referent at all — and the alpha/beta framing that makes the split natural is precisely what makes
> that case invisible. **The fix for one conflation created another**, in the same edit.

⚠ Also split `format_validation`'s verdict **per parser**. A single combined verdict said
*"AT LEAST ONE PARSER MATCHED NOTHING"* on an eigenvalue-only block — **correct about frequencies
and read as a failure of the thing that had just succeeded.** C-2's shape: a verdict that cannot
distinguish *"did not apply"* from *"failed"*.

### 🟢 U-67 applied — and it FLIPPED A VERDICT on the real trajectory
```
Li-X 2.4/2.3/2.5 [PLACEHOLDER-ESTIMATE] → 2.75 Å [MEASURED, MLIP RDF first minimum]
under 2.4 Å    19 intact / 1 dissociated
under 2.75 Å   20 intact / 0 dissociated
```
🔴 **The "dissociation" at 2.4 Å was an artefact of a cutoff drawn INSIDE the shell — the old value
was manufacturing an event.** Independent evidence for what could previously only be argued from
RDF theory. **Both numbers are pinned by a test**, so if the old table ever stops flipping a
verdict, the "recompute, do not grandfather" instruction has lost its instance and we find out.
Applied to every element with `_not_element_resolved` (the user gave Li–X generically) and the dead
**P2** provenance recorded.

### 🔴 The lead's reading order was defective in BOTH directions — replaced
ADR-083 said *"kappa_stability first; if the correlation lives only at k=1, stop."* coder6:
*"the pre-registered primary is κ₂ — a tired reader could take 'stop at step 1' as licence to skip
the primary."* Correct, and it is worse than that:
```
over-covers   "stop" reads as licence to skip the primary
under-covers  the primary can fail WITHOUT the correlation living only at k=1 — present at k=1
              and k=3 but not k=2 and the gate never fires, while the primary has failed
🔴 A gate testing for ONE SPECIFIC FAILURE was placed where THE DECISION goes. Rule 18, broken by
   the lead who wrote it: the gate's POSITION was decided before its FAILURE DIRECTION.
```
🔴 **But `primary_survives` must NOT be a boolean** — a boolean needs a ρ cutoff, and ADR-082 banned
those here (*"that is how −100 cm⁻¹ got there"*). Ruled:
```
primary                 κ₂ vs opt_cycles — ρ, n_used, n_dropped, + the PRE-REGISTRATION stamp
primary_ladder_context  the same correlation at k=1 and k=3 BESIDE it
primary_verdict         None, with verdict_is_a_judgement_for: "proposer"
interpretation_rule     the rule IN WORDS, in the record
🔒 STATE THE RULE AND SHOW THE NUMBERS; DO NOT EVALUATE THE RULE.
revised order  1 primary + ladder context TOGETHER (a framing, not a stop-gate — the primary is
                 never skipped and never read naked)
               2 n_convergence_artefacts   3 everything else, only if 1–2 leave a question open
```

### ⚠ What the fixture does NOT close — kept declared
```
· run-together fixed-width values (−100.12345−99.12345) — every value here separates cleanly
  ⟹ stays [UNVERIFIED], asserted by a test against PROVENANCE.md
· the supplied copy is TRUNCATED (12 matched lines): the 1-value last-alpha-virt line and the
  4-value last-beta-occ line are absent ⟹ variable-values-per-line only PARTLY covered
```
🔒 *One real log validates the format it contains and nothing else* — carried verbatim in the
provenance file, not in a document.

### 🟢 coder6 will hold the lead to its own caveat
The 6,000× κ-ladder figure came from a **synthetic fixture with a deliberately inserted 0.4 cm⁻¹
mode**. coder6 is writing that into the pre-registration record itself, so *"it demonstrates
fragility, it is not evidence about our species, and it was NOT used to choose k=2"* survives in
the artefact rather than in a claim someone must later be trusted about.

---

## ADR-086: **a critic and a coder may run in parallel — but only against a FROZEN `dist/`**, and a spawn must be verified by MODE, not existence

**Date**: 2026-08-19 · **lead**, after the first post-restart spawn ran in the wrong mode for ~2 minutes
**Status**: ADOPTED · binds every future spawn · supersedes nothing, tightens §0-i's verification rule

### Context
§0-i sequenced the restart as: verify handoff → restart tmux → spawn `critic7` (§0-f) → spawn a new
coder. All four were attempted. The two spawns **succeeded and did useful work**, and were still
wrong: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` lives in the PARENT directory's `.claude/settings.json`,
so launching the lead from `sei_formation/` produced **plain background subagents** — no agent panel,
no names, no user↔teammate session, no surfaced permission requests. See §0-k for the full shape.

### Decision (a) — verify the MODE
🔴 **`ListAgents` must report a tmux pane for a teammate. `Subagents (n)` means the team is NOT on.**
§0-i's existing rule — *"verify a teammate exists via `ListAgents` before recording it as spawned"* —
was written for a **silent spawn FAILURE** and is insufficient for a **silent spawn DEGRADATION**.
Existence was never in doubt here; both agents ran immediately.
🟢 `sei_formation/.claude/settings.json` now carries the two keys, so either launch directory works.
**This adds a file not listed in `00_PROJECT_BRIEF §5`; recorded here rather than left to be found.**

### Decision (b) — the parallel-work rule
A critic verifies the **shipped tarball** (ADR-057); a coder edits **`src/`**. These do not collide
**only while `src/dist/` is frozen**. Therefore:
```
· the coder MAY NOT run src/make_package.sh, nor move/delete anything in src/dist/
· the LEAD releases a rebuild, after the critic reports
· a RED [stamp] is the EXPECTED state in that window and MUST NOT be "fixed" by rebuilding
· HANDOFF_CODER6 §H step 3 already says two build_stamp FAILures are normal after editing src/.
  🔴 That is the ONLY sanctioned red. Any OTHER red is a real failure and stops the coder.
```
Both briefs must carry this, in the brief itself — not as a lead instruction sent afterwards.

### 🔴 The cost, recorded because this project's rule is that negative results are not deleted
`coder7` was stopped ~90 s in, mid-refactor, leaving `criteria/g16.py` (+263) and `criteria/p5.py`
(+21) on disk with **the suite at 3 failures / 13 errors** — the field rename `route` → `route_echoed`
reaching consumers that still say `route`, with no test added. The lead attempted to restore the two
files from the tarball and **the sandbox denied the `cp`**; the tree was left as coder7 left it and
the diff saved to `src/salvage/*.patch`.
🔒 **This is attributed drift, and it is still drift.** It is logged in §0-k so that
`HANDOFF_CODER6 §H`'s *"expect 1122 OK"* is not read as current. **The next coder's FIRST task is a
green suite** — finish B-1 with tests, or restore from `src/dist/sei_pilot_cpu.tar.gz` and re-land.

### 🟢 What was bought for that cost — a FOURTH proof of the 70-column truncation
Rebuilding the requested route from `config/qc_levels.json`'s job_type templates and cutting at 70
chars **reproduces all three RT-1 stored strings byte-for-byte**; the lost ts tail is exactly
`test,maxcycles=100) freq`. This is stronger than §B-1's three proofs and it **retires the
`[UNKNOWN]` on `freq`.**
🔴 **It does NOT retire the one on `nosymm`.** The reconstruction shows what the TEMPLATE requested,
not what G16 received — a different claim. §B-2's `[UNKNOWN — the stored route is truncated]` stands.

### Also
🔴 The names `critic7` and `coder7` are **burned** (spawned, then stopped). Per the standing rule that
a reused name routes messages to the old agent, the next pair is **`critic8` / `coder8`**.

---

## ADR-087: **a field that contradicts its own declared contract** — `partition()` ships a pooled convergence rate under a note saying it never pools

**Date**: 2026-08-19 · **Raised by**: `critic8` (stage 1) · **Confirmed independently by the lead** (re-derived, not accepted on report) · **Status**: ADOPTED, fix queued to `coder8` ahead of B-2
**Artefact**: `src/dist/sei_pilot_cpu.tar.gz`, `source_digest 4a484eb71ef2b36d` — the SHIPPED tarball (ADR-057), not the source tree.

### The defect
`sei_pilot/bound.py::partition()` returns, in ONE dict:
```
docstring          "Split probe records into the three groups that must never be averaged together."
_per_stratum_note  "🔴 u_cheap and the convergence rate are reported PER STRATUM and NEVER POOLED."
convergence_rate   n_conv / float(len(in_stats))        ← POOLED ACROSS STRATA, ten lines below the note
```
Lead's own repro (19 closed-shell all converged + 4 open-shell none converged):
```
top-level convergence_rate  0.8260869565      ← a complete open-shell stratum failure is INVISIBLE
per_stratum closed_shell    1.0
per_stratum open_shell      0.0
```
It reaches the report: `orbitals.py:405` → `409 "bound_partition"` → `b0_species_panel`.

### 🔴 Why this is not "a missing caveat" — it is the THIRD HAT of the dominant failure class
The report **refutes its own field**. That is the same shape as §0-j's route truncation, where `"freq"`
is absent from a stored route whose log yielded 27 frequencies. Same class, third instance, new surface.
🔒 **Record the class, not only the instance** — this class has now appeared in a parser (route), in a
statistic (this), and in an availability check (Rule 20's `module load`). It is not a parser problem.

### 🔴🔴 THE SECOND LAYER, AND IT IS THE DANGEROUS ONE — a caveat on the WRONG AXIS
`_denominator_note` sits **directly on the pooled field** and correctly explains a *different* axis:
that the denominator excludes unbound and tripwire-aborted species. A reader sees a red-flagged note
attached to the number and concludes the field has been thought about.
🔒 **A number wearing the wrong caveat is more dangerous than an uncaveated one.** This is §0-h's
adjacency pattern (① reads as handled, the eye stops at ①), and it is why the fix **must not be another
caveat string**. A second note beside the first is precisely how this survived review until now.

### The ruling
```
1  the pooled field either GOES AWAY or becomes structurally unreadable as a rate. NOT a caveat.
2  🔴 `n_converged` and `convergence_denominator` ship beside it and are the pooled numerator and
   denominator — any reader reconstructs the pooled rate in ONE division. Removing `convergence_rate`
   alone leaves the defect fully available. What the top level exposes is a deliberate decision.
3  the regression test must go RED on current code, and its fixture must DISTINGUISH:
   19/19 + 0/4 distinguishes pooled from per-stratum; 19/19 + 4/4 does not (coder6's family (i)).
4  🔴 ORDER — **SUPERSEDED BY ADR-088, WHICH INSERTS C-1 WIRING AHEAD OF THIS ITEM.**
   This line originally read "green suite → this → B-2" and `coder8` correctly followed it straight
   from this document into B-2, skipping the C-1 BLOCKER. 🔒 **THE LEAD'S DEFECT, not the coder's**:
   two orderings existed in two ADRs and the coder read the one written first. Canonical order is
   **ADR-090's**, and no ADR may carry a work order again — see ADR-090.
```

### 🔒 The process rule this round also settled
`critic8` sent the MAJOR **directly to `coder8`** as well as to the lead. That is fast and it is also how
a work order gets reordered without a ruling — `coder8` was mid-way through the mandatory green-suite
task. ⟹ **A critic may notify a coder directly, but only the lead sequences the fix.** Both were told.
⚠ And the lead **re-derived the finding before ruling on it** rather than relaying it. `critic8`'s report
was correct but understated by two layers, both of which changed the prescribed fix. 🔒 **Relaying a
teammate's finding at the teammate's own severity is not review.**

### What `critic8` verified clean in the same pass (so it is not re-verified)
THE GUARD (single authority `B0_APPROVED_REFERENCE_CORE_HOURS = 15000.0`, derived in one function, no
path admits a typed KNL number; 36,000 KNL vs 21,000 confirmed same-ceiling-different-unit, NOT a raise
— §R24.1 intact) · `b0_plan.size()`/`check_against_guard` nulls confirmed DELIBERATE · the ADR-084/085
orbital traps, incl. a constructed RKS-only input proving the SOMO fix where the one real log cannot ·
C-9 against all 5 real shipped geometries · a constructed exactly-degenerate covariance through the
hand-rolled Jacobi (coder6's nomination 3, previously untested) · `readiness.evaluate`'s single `elif`
at BOTH polarities · ADR-083 pre-registration present with `primary_verdict` hardcoded `None` ·
the 6 h tripwire DETECTION half implemented (PREVENTION half confirmed still NOT wired — already
tracked, not a new finding) · the three declared constants each declared exactly once
(`execlog.py:48`, `guards.py:62`, `guards.py:71`), no duplicate literals.

---

## ADR-088: 🔴🔴 **BLOCKER — C-1's guard was never wired to the function that produces the number it was written to prevent**

**Date**: 2026-08-19 · **Raised by**: `critic8` (stage 2, from the re-run the lead insisted on) · **Independently re-derived by the lead from the real cluster report** · **Status**: BLOCK on any composite-methodology number; fix ordered to `coder8` ahead of ADR-087
**Artefact**: tarball `source_digest 4a484eb71ef2b36d` · evidence `cpu_machine_pilot_results/sei_probe_report.cpu.json`

### The defect
`criteria/p1b.py::cost_ratios()` decides usability **purely by cost-presence**. Its inner `cost()` returns
`e.get("core_hours")` and nothing else; `missing` is `[k for k,v in ... if v is None]`. **`converged` is
named in the function's own docstring as a field of `steps` and is never read.** Neither `p1b.py` nor
`collect.py` imports `guards` at all.

Lead's own re-derivation (exact, from the returned report):
```
li_ec2_cation  A_cheap_optfreq  282.7378 core-h  converged=FALSE
               C_high_sp_on_cheap 10.3289        converged=True
   r_composite = (a+c)/a = 293.0667/282.7378 = 1.0365     PUBLISHED as a real number
li_ec_cation   B_high_optfreq     1.9200        converged=FALSE
               A_cheap_optfreq    5.0311        converged=True
   r_high      = b/a = 1.9200/5.0311 = 0.3816             PUBLISHED as a real number
```
🔴 **`guards.py:122-123` cites this exact number as its reason to exist**: *"non-convergence is not a
measurement of anything -- ADR-065, where r_composite = 1.0365 was published over a 283 core-h
non-convergence."* The guard was written naming the incident, and was never connected to the producer.
**C-10 is an ADOPTED constraint, unenforced on the only path that matters.**

### 🔴 THE CLASS — Rule 20, applied to a GUARD instead of to a capability
```
check that ran     : "guards.derived_or_null exists, is correct, and is well-tested in isolation"
property claimed   : "derived quantities are guarded against non-convergence"
```
Identical in shape to the RT-1 loss (*"a gaussian-ish string exists in `modules[]`"* ⟹ *"G16 will run"*).
🔒 **A guard's existence and a guard's reach are different properties.** This project has now paid for
that distinction twice, once with a whole cluster round trip.

### 🔴 WHY IT SURVIVED — a partial guard that fires often enough to look like it works
`li_ec2_cation_B_high_optfreq` has `core_hours=None` **AND** `converged=False`, so its `r_high` did come
out `None` — via the `missing` path, **for the wrong reason.** ⟹ the existing mechanism catches a
non-convergence **by accident** whenever the step also failed to record cost, and misses it whenever the
step **burnt cost and still did not converge**. 🔒 ⟹ **"extend `missing`" is the WRONG fix** — that is the
half-working mechanism itself.

### 🟢 THE STRONGEST EVIDENCE — the code's output set and ADR-065's discard set coincide exactly
```
published by the code   r_composite {1.0365, 1.142, 1.3004}   r_high {0.3816, 1.5284}
ADR-065, derived BY HAND r_composite  1.14–1.30 (n=2)          r_high  1.5284 only (n=1)
```
**The two numbers ADR-065 threw out by hand are precisely the two the code publishes unguarded.**
⟹ ADR-065 was a human performing C-10's job manually, once, on one report. **Nobody will do that for B0-F.**

### 🔴 SCOPE — `critic8` scoped this too narrowly and the lead corrected it
`critic8` blocked "the composite-ratio path, not B0-D's conformer arms". **B0-D's arm 3 IS `r_high`** —
`b0_plan.py:128-130` (`"stage": STAGE_DFT_HIGH, "arm": 3, "note": "r_high, from ARM 1's conformer"`), and
STATE's own arm list reads *"(generated conformers / idealised control / r_high)"*. It does not route
through `cost_ratios()` **today only because B0 collector wiring is NOT STARTED — and that wiring is on
`coder8`'s own task list.** ⚠ A block scoped as "composite only" reads as *"B0-D is clear"*, after which
arm 3 gets wired straight into the unguarded function. 🔒 **A scope measured against an unwired state
expires when our own work order wires it.**

### The ordered fix
```
· cost_ratios() consults CONVERGENCE, not cost-presence, and does so THROUGH `guards` —
  no second hand-rolled definition of "usable" (two definitions is the recurring failure)
· a ratio over a non-converged input is `None` PLUS A STATED REASON. Never a number, never a silent drop
· 🔴 the reason must distinguish `None because MISSING` from `None because DID NOT CONVERGE` (C-2's
  principle: "wrong" and "did not run" must not share an exit)
· regression fixture uses the REAL numbers above — they go RED on current code AND they discriminate
· ORDER: C-1 wiring → ADR-087 bound.py → B-2 nosymm → B-5 → NOT STARTED
```

---

## ADR-089: **a green suite did not prove a completed rename** — the Python↔shell boundary has no test that runs without the real engine

**Date**: 2026-08-19 · **Found by**: `coder8`, while closing the B-1 red tree · **Status**: ADOPTED as a standing rule

Finishing coder7's `route` → `route_echoed` rename, `coder8` found **three** consumers the patch had not
reached. One was a genuine test FAIL. **The other two were invisible to every test we own:**
```
payload/P1b.sh:228        read s["route"] ≡ None once the key was gone — would have silently broken
                          routes["step1"] keyword checks (wrong ANSWER, not an error)
payload/P5.sh:116         hard KeyError the moment real G16 output exists — LATENT: P5 is `skipped`
payload/qc_adapter.sh:312 same KeyError in the smoke-level collector — LATENT for the same reason
```
Both latent ones are unreachable here because **there is no g16 on this box**, so the suite is green with
them broken.

🔴 **⟹ THE GREEN SUITE WOULD HAVE CERTIFIED AN INCOMPLETE RENAME.** Two of the five touched files could
not speak. And the P1b one is the worse of the three: it returns a **wrong answer**, not an error.
🔒 **STANDING RULE: when a rename crosses the Python↔shell boundary, `grep` is the authority and the test
suite is not.** The shell side has no test that runs without the real engine, so "the suite is green" is
evidence about the Python half only. ⚠ This is the silent-failure class again — *the rename looked
finished because the only consumers able to complain were the ones already fixed.*

### 🔴 And a companion caution on the revert evidence in the same round
`coder8`'s revert experiment returned **3 FAIL + 26 ERROR**. Reverting to pristine DELETES the new
functions, so the tests raise `AttributeError` — which proves they **TOUCH** the new code and **not** that
they would catch a *subtly wrong* implementation, which is the actual risk. Per §0.2(a), a mostly-ERROR
revert means the experiment changed the wrong thing. **At most 3 of 25 tests are demonstrated to
discriminate.** ⟹ Mutations that KEEP THE API INTACT were ordered instead (`ROUTE_ECHO_WRAP_COLUMNS`
70→80 · `route_record_from_stored_string` returning `is_complete=True` · `require_keyword_known_absent`
returning instead of raising · dropping the continuation-line join · re-emitting the legacy `route` key);
each must produce **FAIL**, never ERROR.
🔒 **A revert that removes a symbol tests presence. Only a mutation that preserves the symbol tests the
property.** ⚠ An arithmetic reconciliation is also outstanding — the file holds 25 test methods and
`3 + 26 = 29`; `coder8` was asked which selection it actually ran rather than have the lead guess.

---

## ADR-090: 🔴🔴 **THE GUARD LAYER IS UNREACHED BY DEFAULT — 13 of 16 guards have no caller, and no test anywhere asserts reach**

**Date**: 2026-08-19 · **Third instance raised by** `critic8` (P1.sh / C-12) · **Generalised and measured by the lead** · **Status**: ADOPTED. This supersedes the three instances as the primary finding of the round.

### How we got here — three instances in one session, all the same shape
```
ADR-087  bound.py::partition()      ships a pooled convergence_rate under its own "NEVER POOLED" note
ADR-088  p1b.py::cost_ratios()      never reads `converged`; guards.py:122 cites the resulting 1.0365
NEW      payload/P1.sh:79           `if ! grep -q "Normal termination" "$TS_LOG"` — the fallback fires
                                    ONLY on abnormal termination. guards.fallback_decision's docstring
                                    names this verbatim: "QST2 converged -- to a saddle of the wrong
                                    coordinate -- so the fallback never fired and 302 core-h bought a
                                    wrong answer." 🔴 P1.sh IS the script that produced RT-1's real
                                    ts_qst2.log, and B0-F's TS bake-off reuses it.
```

### 🔴 THE MEASUREMENT — the lead swept every guard for an external caller, on the SHIPPED tarball
```
WIRED (1)      symmetric_placement_flags   (conformers.py:640 — the ONLY genuine external call)
🔴 CORRECTED TWICE. Originally `WIRED (3) irc_verdict · symmetric_placement_flags · coplanarity`.
   `irc_verdict` matched `p1.py:283`'s dict KEY `"irc_verdict": ir.get("verdict")` (critic8).
   `coplanarity` matched TWO DOCSTRING MENTIONS in `linalg.py:7,27` (coder8, AST-verified).
   🔴 **TWO OF THE SWEEP'S THREE POSITIVE CLAIMS WERE WRONG — a 67 % false-positive rate on
   exactly the claims that say "this is safe".** See ADR-092 and ADR-094.
NO CALLER (13) unconverged_inputs · derived_or_null · irc_direction_ok · heavy_atoms ·
               perturb_out_of_plane · endpoint_report · ts_precondition ·
               require_ts_precondition · fallback_decision · tripwire_record ·
               detect_tripwire_aborts · spend_core_hours · cost_probe_violations
```
⚠ **Honest partition of those 13** — they are not all the same:
```
(A) consumer EXISTS and does the job wrongly  → the three instances above. BLOCKER/MAJOR class.
(B) consumer NOT STARTED (B0 collector, submission wiring) → legitimate TODAY, and it is exactly
    how (A) is created later: the wiring gets written and the guard is not remembered.
```
🔴 **`require_ts_precondition` is category (A) and was not on anyone's list.** C-8 says *"a TS search must
REFUSE TO START unless both endpoints are optimised with zero imaginary frequencies — a precondition,
not a warning."* `payload/P1.sh` contains **no precondition check of any kind** (grep: no `precondition`,
no endpoint `imag`/`freq` gate). ⟹ **C-8 is an adopted constraint, unenforced, on a script that has
already run on the cluster.** That makes **three adopted constraints unenforced on live paths**: C-1
(ADR-088), C-8 (here), C-12 (P1.sh fallback).

### 🔴🔴 THE MECHANISM — why all three shipped, and it is not carelessness
```
grep -rln <guard> tests/    →  tests/test_guards.py · tests/test_b0_guard_and_tripwire.py
grep those tests for the CONSUMER (p1b / collect / cost_ratios / P1.sh)  →  NONE
```
**Every guard test exercises its guard in isolation. Not one test anywhere asserts that a guard is
REACHED from the code it protects.** ⟹ The suite is *structurally incapable* of detecting
existence-without-reach, so a guard can be written, tested, documented with its own historical incident,
and never called — and every signal we own stays green.
🔒 **This is Rule 20 at the level of the test suite itself**: "the guard is tested" was our proxy for
"the guard protects something". **A guard's existence, its correctness, and its reach are three
properties, and we were only ever measuring two.**

### The ruling
```
1  🔴 A guard is UNFINISHED until a test asserts it is REACHED FROM ITS CONSUMER. Isolation tests are
   necessary and not sufficient. This applies to every C-N constraint.
2  the C-1 fix (ADR-088) must land WITH such a reach test, and it is the template for the rest.
3  a REACH INVENTORY is required: classify all 13 into (A) or (B), by execution, not by reading.
   Category (A) items are defects now. Category (B) items get a named blocking entry so the wiring
   cannot be written without them.
4  🟢 **the shell bridge is NOT a design decision — IT ALREADY EXISTS. Reuse it.**
   `payload/qc_adapter.sh` calls Python four times already via
   `PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$@" <<'PY'` (lines 38, 64, 125, 292). C-12's gate in
   `P1.sh` and C-8's precondition become calls to `guards.fallback_decision` /
   `guards.require_ts_precondition` through that same pattern.
   🔴 **No `sei_guard` shim, no new mechanism, no proposal needed.** An earlier draft of this ADR
   asked for one; that was the lead inventing a mechanism the codebase already had — rung 2 of
   "look before you write". ⚠ The one real constraint stands: **the shell must not restate the rule.**
   It asks Python and obeys the answer.
5  🔒 CANONICAL WORK ORDER lives HERE and nowhere else:
      🔴 REVISED 2026-08-19 after ADR-092. B-1 / B-2 / B-5 / ADR-087 are DONE. Remaining, in order:

      1  🟢 DONE  C-2 wiring  `criteria/p1.py` → `guards.irc_verdict`   [lead-verified by AST]
      2  🟢 DONE  C-1 wiring  `criteria/p1b.py::cost_ratios` → `guards.unconverged_inputs`
            [lead-verified: 1.0365 → None, 0.3816 → None, reasons kept separate]
      3  κ integrity  `collect_p6` → `execution_audit`                           [ADR-092]
      4  THE REACH TEST, once, covering 1-3 and the rest: 🔴 AST-based CALL detection, NOT grep
         (ADR-092 — a name-match check reproduces the defect that mis-scored `irc_verdict`).
         Plus: `collect.py:89`'s false "every collector" claim deleted or made true.
      5  C-8 wiring   `payload/P1.sh:55-72` → `guards.require_ts_precondition`, via the EXISTING
         `python3 - <<'PY'` bridge (item 4 of this ADR)
      6  C-12 wiring  `payload/P1.sh:79` → `guards.fallback_decision`, same bridge
      7  C-10 wiring  `criteria/p1.py:265` → `guards.cost_probe_violations`      [ADR-091, MAJOR]
      8  blocking entry for `require_nosymm_if_needed` (category (B), zero callers — the 5th instance)
      9  NOT STARTED: composite route strings · B0 collector wiring · payload/PBS (6 h PREVENTION half)

   🔒 Items 1-3 are BLOCKERs and share ONE root shape. 🔴 Do not let item 4 be written as nine
   separate patches — the reach test is the deliverable that stops the tenth instance.
   ADR-087 is DONE. 🔴 **No other ADR may carry a work order** — see the process note below.
```

### 🔒 PROCESS DEFECT, THE LEAD'S OWN, LOGGED BECAUSE IT COST A MISDIRECTED TASK
ADR-087 closed with `ORDER: green suite → this → B-2`. ADR-088 then closed with `ORDER: C-1 → ADR-087 →
B-2`. **Two orderings in two documents.** `coder8` finished ADR-087, read ADR-087's own ORDER line, and
moved to B-2 — **skipping the BLOCKER.** It followed the document correctly; the document was wrong.
⚠ **This is "the same truth in two places", the failure this project has logged six times, committed by
the lead inside the very ADRs recording the other instances of it.** A teammate reading the artefact
nearest its own task will always find the stale copy first.
🔒 ⟹ **Work order is a single field in ONE place (ADR-090 §5). ADRs record decisions, not sequence.**
ADR-087's ORDER line has been struck and points here.

---

## ADR-091: **the fourth instance, and a FALSE RATIONALE in the code** — `execution_audit` reaches 4 of 9 collectors while its docstring claims "every collector", and the uncovered one that matters is κ

**Date**: 2026-08-19 · **Raised by**: `critic8` stage 3 (the 4th instance deliberately; the collector gap as an explicit *"side note, not investigated further"*) · **Measured and ruled by the lead** · **Status**: ADOPTED. Extends ADR-090; the lead's ADR-090-era ruling on nomination 4 is QUALIFIED here.

### The fourth instance (MAJOR, not BLOCKER)
`criteria/p1.py:265` — `status = "pass" if passed else ("undetermined" if undetermined else "fail")`,
assigned directly. `guards.cost_probe_violations` is never consulted, and **C-10's own docstring names P1
as one of its four founding instances.** `critic8` ran the guard against the **real shipped P1 pilot
result**: it fires all three violation categories today. Live, not constructed.
**Severity MAJOR**: ADR-066 already instructs readers not to trust P1's verdict, so the number is not
load-bearing *now*. 🔴 **That is masking, not mitigation — the ADR-066 caveat does not travel when B0-F
reuses the path.** Queued after B-5.

### 🔴🔴 THE FINDING THAT REVERSES A LEAD RULING — a false claim serving as a design rationale
`collect.py:89` states, **as the argument the design was accepted on**:
> *"`execution_audit` is already called from every collector"*
```
CALLS (4)     collect_p1 · collect_p1b · collect_p3 · collect_p5
DOES NOT (5)  collect_p6 · collect_p4 · collect_node_probe · collect_throughput · collect_queue_wait
```
🔒 **The lead accepted nomination 4 (`execution_audit` as host for the integrity block) on "uniform reach,
no second mechanism". The reach is 4 of 9.** ⟹ **RULING QUALIFIED: the host is still right, the
justification was false, and the gap is a defect.** ⚠ `critic8`'s evidence had been *"called identically
from 4 collectors"* — accurate, and the lead had already told it that this was a proxy claim. **The proxy
was for the word "every".**

### 🔴 THE STAKES ARE NOT UNIFORM ACROSS THE FIVE — one of them is κ
`collect_p6` is the κ measurement. κ is the **single dominant variable of the 5-month schedule** (condition
(i); STATE: *"P6 로만 알 수 있다. 단일 임계 경로"*). ⟹ **The one number that gates the entire calendar has no
double-execution audit and no `executions.jsonl` integrity check.** A double-counted or truncated P6 record
moves κ, and κ moves every week-count in the plan (`weeks(κ,N) = 4.0κ(100/N) + 9.5 + 3.0·n_recomp`).
🔒 **This was inside a sentence its author marked as not worth investigating.**

### 🔴 A NEW SHAPE, HARDER THAN ADR-090's — "wired, but not everywhere"
ADR-090's instances were *zero callers*. This one **has callers**, so a caller-count check cannot see it.
⟹ **Two mechanisms are required, deliberately:**
```
(i)  every public guards.py function has ≥1 caller outside guards.py   [catches all 4 of ADR-090]
(ii) 🟢 NOT a registry. For the one live case, `execution_audit`: make `collect.py:89`'s claim
     TRUE (or scope it in code, naming any genuine exemption as a fact), then ONE test asserting
     every collector that must audit does.                             [catches 4-of-9]
```
🔒 **Total cost of both: one test file, ~20 lines, no new mechanism.** An earlier draft asked for a
declared-call-site registry verified as a set. 🔴 **A registry that drifts from the code is a fresh
instance of the disease it was meant to detect** — and (i) plus a truthful docstring already cover every
case found. **Do not build (ii) as a registry.**
⚠ **And do not force a caller onto `guards.heavy_atoms`** to satisfy (i) — it is an internal helper of
`coplanarity`, not a C-N guard. 🔒 **A check that produces a false positive teaches people to ignore it**
(HANDOFF §0.2b-6, `build_stamp --root`). `collect_queue_wait`'s exemption, if real, must be stated **in
code as a fact**, not left as silence — silence is how 4-of-9 reads as 9-of-9.

### 🔒 TWO PROCESS OBSERVATIONS, ONE PER PARTY

**`critic8` — the item framed as incidental has now been the payload twice.** Stage 1 dropped nomination 2
as a formality → it produced the first BLOCKER. Stage 3 filed the collector gap as *"side note, not
investigated further"* → it reverses a lead ruling and lands on κ. 🔒 ⟹ **"side note" / "not investigated
further" is the signal to spend ten more minutes, not fewer.** Its instinct for what is *interesting* is
excellent; its instinct for what is *load-bearing* is the one to distrust.

**The lead — the double work-order defect RECURRED, in the message immediately after ADR-090 logged it.**
Stage 3 was defined twice: first `(a) scope · (b) 4-collector reach · (c) execlog · (d) cost_probe_violations`,
then *"STAGE 3 — one task: THE REACH INVENTORY"* with those four demoted. `critic8` executed the earlier
list exactly, labels included, and **the reach inventory — the item `coder8` actually needs — went undone.**
🔴 ADR-090 §5 put work order in one document and the lead then issued orders by message, which is the same
failure in a new channel. 🔒 ⟹ **EXTENDED RULE: work order lives in ADR-090 §5; messages REFERENCE it and
never restate it. Restating is how the second copy is made — the channel is irrelevant.**

---

## ADR-092: 🔴🔴 **the sweep that found the class fell to the class** — `irc_verdict` is unwired, C-2 is unenforced, and κ's collector audits nothing

**Date**: 2026-08-19 · **Raised by**: `critic8` (reach inventory, stages 3b + 4) · **Both re-derived by the lead** · **Status**: ADOPTED. Corrects ADR-090's own measurement.

### 🔴 THE LEAD'S SWEEP WAS WRONG, BY THE DEFECT IT WAS HUNTING
ADR-090's `WIRED (3)` included `irc_verdict`. It is not wired. The only occurrence outside `guards.py` is
```
sei_pilot/criteria/p1.py:283      "irc_verdict": ir.get("verdict"),      ← a dict KEY. Not a call.
```
`criteria/p1.py` does not import `guards` at all. The sweep was `grep -rn "\bNAME\b" | grep -v guards.py | wc -l`
— **a name-occurrence count standing in for a call.** 🔒 **The lead inferred "is called" from "the name
appears": Rule 20, committed inside the instrument built to detect Rule 20 violations.** Demonstrated in
8 lines of stdlib `ast`:
```
irc_verdict actually CALLED in p1.py?  ->  False
irc_verdict name APPEARS in p1.py?     ->  True
```
🔒 ⟹ **CONSEQUENCE FOR THE FIX (supersedes ADR-091 (i)): the reach test must detect a CALL, not a name.**
`ast.walk` for `Call` nodes matching the guard name — stdlib, ~15 lines, still one test file. **A grep-based
caller check reproduces this exact defect and would have certified `irc_verdict` as protected.**

### 🔴🔴 BLOCKER — C-2 is unenforced, in the script the whole review draws its evidence from
`criteria/p1.py::evaluate_irc()` records `n_frames_forward`/`n_frames_reverse` and **gates on none of C-2's
three clauses**: no `normal_termination`, no `IRC_MIN_POINTS` (5), no `IRC_MIN_DESCENT_EV` (0.05 eV).
`critic8`'s constructed case: a 2-frame IRC pair (below the 5-point minimum), forward intact / reverse
dissociated ⟹ `evaluate_irc` returns `passed=True`, which drives `evaluate_p1`'s `status="pass"` directly.
🔴 **C-2 is the constraint born from the P1/ADR-066 incident, and this is that guard, unreached, in the
script that produced the real logs this review has drawn from throughout.**
⚠ On the real RT-1 data it happened not to matter — `n_frames = 1` per direction was classified "same" and
failed anyway, for the unrelated ADR-065 reason. **That is coincidence, not protection**: the same path
returns `True` as soon as a short trajectory's endpoints merely look distinct, which a genuinely
truncated-but-real IRC does easily. **Ranked above the `cost_ratios` BLOCKER.**

### 🔴🔴 BLOCKER — `collect_p6` audits nothing, and P6 is κ
`payload/P6.sh:19,51` sources `common.sh` and uses `sei_stage` — **so `stage_events.jsonl` and
`executions.jsonl` ARE produced in P6's job_dir.** `collect_p6` simply never calls `execution_audit` on
them. `critic8`'s adversarial case: `anchor_t16` run **twice** in `stage_events.jsonl`, a malformed
`executions.jsonl` line, and `p6_anchor.json` carrying `wall_s=999999.0` ⟹ `collect_p6` returns
`status="pass"`, `valid=True`, `kappa=5640.152` labelled **`[MEASURED]`**, with the `execution_audit` key
absent entirely and **zero warnings**. The only check performed is ADR-048's thread-count agreement, which
is orthogonal to whether the number came from one clean run.
🔒 **κ is the single critical path of the 5-month schedule, and it has WEAKER integrity protection than
P1's core-h totals.** The data to catch this was already on disk and was never read.

### 🟢 The corrected inventory, and the striking part
```
WIRED (2)     symmetric_placement_flags · coplanarity
UNWIRED (14)  after folding internal helpers into their sole entry point's fate
(A) defect now — every unwired guard WITH any traceable consumer:
    derived_or_null · irc_verdict · fallback_decision · cost_probe_violations ·
    require_ts_precondition (C-8: payload/P1.sh:55-72, no precondition check before the QST2 launch)
(B) genuine deferred scope — zero consumer anywhere:
    perturb_out_of_plane (C-9's perturbation step) · tripwire_record / detect_tripwire_aborts /
    spend_core_hours (B0 collector wiring)
collectors    collect_p6 = (A). collect_p4 / node_probe / throughput / queue_wait = (B), each
              confirmed by reading its payload script: they produce no stage_events/executions at all.
              (collect_throughput has its OWN starts/task_${TID}.json — the very pattern execlog.py's
              FALLBACK_REMEDY names as the C-10 target.)
```
🔒 **ZERO (A)-suspects turned out to be fine.** Every unwired guard that had a consumer was a real defect.
⟹ **"unwired" was never the interesting variable — "has a consumer" was.** A guard with a consumer and no
call is a defect with probability 1 in this codebase, on a sample of five.
⚠ `critic8` also declined to close at a tidy 5-and-5: `collect_p1`'s `execution_audit` warnings reach
`res["warnings"][]` but **nothing makes a duplicate-execution or malformed-log finding change
`status`/`valid`** — reported, not gated. Open, not a new BLOCKER.

---

## ADR-093: **a guard wired to an input that can NEVER satisfy it** — the fourth property, found while fixing the third

**Date**: 2026-08-19 · **Found by**: `coder8`, while wiring C-2 · **Status**: ADOPTED. Extends ADR-090/092.

### The near-miss
C-2 needs `n_points ≥ 5` per IRC direction. The obvious source was `collect._g16_last_geometry_xyz`,
already there and already used by the topology check. **It deliberately keeps only the LAST orientation
block** — correct for endpoint comparison, its actual job. Reusing its frame count as C-2's `n_points`
would have made `n_points ≡ 1`, **permanently below the threshold**.
⟹ C-2 would have been **wired, reached, tested, and structurally unsatisfiable forever.**
Fixed by reading the raw IRC logs and counting all orientation blocks via `g16.parse_geometries()` for the
Gaussian branch; the ORCA branch falls back to the topology check's frame count (which IS the full
trajectory there) and, lacking G16 termination/energy telemetry, correctly reports `indeterminate` rather
than inventing permission (Rule 18).

### 🔴 WHY THIS IS WORSE THAN AN UNWIRED GUARD
```
unwired guard          the reach test (ADR-092 item 4) catches it
guard on a dead input  the reach test PASSES. The call is there. The test is green.
```
⚠ Its failure direction is safe — every P1 verdict falls to `indeterminate`, the pessimistic half, which
per §0-h does eventually get noticed. 🔴 **But the repair a reader reaches for is "C-2 is too strict, relax
it"** — converting a fail-safe into a real hole **with the reach test still green.** That is the danger,
and it is not hypothetical: this project has relaxed a threshold under exactly that pressure before
(§R24.1 exists because of it).

### 🔒 THE PROPERTY LADDER — four rungs, each one paid for
```
1 EXISTENCE       the guard is written                     ← we measured this
2 CORRECTNESS     it is right in isolation                 ← we measured this
3 REACH           its consumer actually calls it           ← ADR-090/092. Four instances. Unmeasured.
4 SATISFIABILITY  the input it is fed CAN satisfy it       ← ADR-093. Unmeasured.
```
🔒 **A reach test is necessary and NOT sufficient.** ⟹ **Every guard wiring lands with a POSITIVE case that
actually passes**, not only a negative case that correctly refuses. A guard that can only ever say `None`
is indistinguishable from a broken one — coder6's family (i), one rung up.
🟢 `coder8` applied this unprompted in the C-1 fix: alongside the two incident fixtures that must return
`None`, it added a genuinely-converged fixture that **must return a real number.**

---

## ADR-094: **the grep sweep was wrong on 2 of its 3 "safe" claims** — and both errors pointed the same way

**Date**: 2026-08-19 · **`irc_verdict` caught by `critic8`, `coplanarity` by `coder8`, both AST-verified by the lead** · **Status**: ADOPTED. Final correction to ADR-090's inventory.

```
the lead's sweep claimed  WIRED (3)  irc_verdict · symmetric_placement_flags · coplanarity
truth, by ast.walk        WIRED (1)  symmetric_placement_flags   (conformers.py:640)

irc_verdict    matched  p1.py:283   "irc_verdict": ir.get("verdict")     ← a dict KEY
coplanarity    matched  linalg.py:7,27  two DOCSTRING MENTIONS of `guards.coplanarity`
```
🔴 **Two of three positive claims wrong: a 67 % false-positive rate, on precisely the claims that say
"this one is safe."** A name-occurrence check is not "slightly imprecise" — as a reach instrument it is
worse than useless, because its errors are concentrated in the direction that stops investigation.

🔒 **AND BOTH ERRORS POINTED THE SAME WAY.** Neither mistake ever said "this guard is unwired when it is
wired." Both said **"wired"** about something unreached. ⚠ That is §0-h's documented direction — *every
logged instance of this class resolves toward "we are in better shape than we are"* — and it held again,
twice, in a single 16-row table built specifically to look for trouble.
🔒 ⟹ **When an instrument's errors are asymmetric, the count is not the finding — the DIRECTION is.**
A reach check whose false positives all read as safety is a check that manufactures confidence.

🟢 **The AST version is now `tests/test_guard_reach.py`, 8 tests, green**, and it forces every public
`guards.py` function into exactly one of four buckets — `INTERNAL_HELPERS`, `DEFERRED_NO_CONSUMER_YET`,
`KNOWN_OPEN_DEFECTS`, `EXPECTED_REACHED` — failing if a function has no bucket or more than one.
🔒 **The `KNOWN_OPEN_DEFECTS` bucket asserts the remaining three STILL have zero callers**, so the suite
stays honest about what is not done rather than going quiet about it. That is the part that makes this a
guard against the tenth instance and not just a fix for the first nine.

---

## ADR-095: 🔴 **B0-F's "ref-core-h" was KNL core-h all along** — the batch has been sized against a ceiling 2.4× too tight

**Date**: 2026-08-19 · **Unit anomaly spotted by** `engineer6` · **Traced to the raw record and settled by the lead** · **Status**: ADOPTED

`engineer6`, pricing C-8's endpoint pre-optimisation, noticed that B0-F's existing `1,814 ref-core-h`
is exactly `6 × 302.4` — the raw P1 anchor with **no ÷κ applied**, under a label saying `ref`.
🔴 **It then compared its own KNL-convention totals against the user's 15,000 REFERENCE ceiling and
reported a ~25 % breach.** The two halves of that report cannot both stand. Lead traced it:
```
P1 anchor      302.4 core-h, wall 4.74 h   ⟹ implied cores 63.8 ≈ ncpus 64
               cores × wall ON THE KNL NODE  ⟹  this is KNL core-h, not reference
B0-F existing  6 × 302.4 = 1,814 KNL  =    756 REFERENCE
B0 pessimistic          18,738 KNL    =  7,808 REFERENCE
ceiling                 15,000 REFERENCE  =  36,000 KNL
BREACH?        18,738 KNL vs 36,000 KNL  ⟹  NO. 48 % margin, WITH C-8 fully included.
```
⟹ **C-8's endpoint pre-optimisation fits inside the approved budget with room to spare.** The cost
axis of the item-5 decision is closed.

### 🔴 The more important consequence
**B0 may have been sized against a ceiling 2.4× tighter than the real one for several rounds.**
ADR-078 cut arm 2 from 23 species to 3. Whatever its other merits, **a batch cut for a phantom
overrun is a real loss of measurement.** ⚠ Do not reverse ADR-078 on this basis alone — its
reasoning was not purely budgetary — but **re-derive any sizing decision whose binding argument was
"it does not fit."**

### 🟢 The direction, for once, was the safe one
Mislabelling KNL as reference makes a batch look **more expensive than it is**. That is the opposite
of §0-h's documented failure direction (*"we are in better shape than we are"*). 🔒 **Every other
instance logged on this project pointed the dangerous way; this one did not.** Worth recording
precisely because it breaks the pattern — the pattern is a tendency, not a law, and treating it as a
law would have made this one harder to see.

🔒 **RULE: a cost figure carries its unit in the same cell as its number.** `ref-core-h` in a column
header is not a unit; it is a hope. §R24.1 forbids raising a guard to fit a plan — it does not
forbid discovering that the guard was being read in the wrong unit.

---

## ADR-096: 🔴 **302.4 core-h is biased LOW, and the caveat that shipped with it pointed the wrong way**

**Date**: 2026-08-19 · **IRC-truncation bias by** `proposer6` · **`crest_absent` bias found by the lead in the report's own unread `warnings[]`** · **Status**: ADOPTED. Supersedes any use of 302.4 as a central estimate.

ADR-064 recorded *"the cost datum survives … but it is the cost of a failed attempt."*
🔒 **A caveat with no direction attached.** A reader takes *"cost of a failure"* to mean **cheaper than a
success** — i.e. conservative. **It is the opposite.** The identified bias ledger:
```
LOW   IRC truncation   irc_forward bought 2 points of maxpoints=30; irc_reverse crashed in l123.
                       302.4 is NOT the cost of a completed workflow.
LOW   crest_absent     pilots[0].warnings says verbatim the TS unit cost EXCLUDES conformer search
                       and is therefore an UNDERESTIMATE ([ESTIMATE] 5-15 % of the workflow).
                       Explains why the three stages sum to exactly 302.4 — crest contributed nothing.
HIGH  level2 vs level3 level2 costs more per cycle than the production level.
```
**Two of three point low.** ⟹ **Quoting 302.4 is an error in the OPTIMISTIC direction** — §0-h's recorded
direction of no-self-correction. ⚠ **Two known biases of opposite sign with unquantified magnitude means
the total is not a bound in either direction.** Not conservative — uninformative. **An honest range with a
hole in it beats a number.**

🔒 **This was a re-reading of a number we already had, at zero compute cost**, and one of its two
low-pointing biases was sitting **unread in the report's own `warnings[]` array** the whole time.

### 🟢 What DOES survive from RT-1 (`proposer6`, lead-confirmed)
```
FULL     wall 4.74 h · longest_stage 3.45 h ≪ 40 h tripwire (the lead's standing obligation IS
         discharged) · queue waits · 200/200 submitted-accepted · 200 distinct hosts · 671.7 core-h
LOWER    ts_qst2 = 220.8 core-h, domain "normally-terminated QST2, 14-atom open-shell doublet,
BOUND    level2+SMD, converged from a rigid symmetric non-stationary pair". A symmetric subspace has
         fewer effective DOF ⟹ plausibly FEWER cycles than a real search.
DEAD     "one TS attempt = 302 core-h"
```
🟢 **And the double-execution question is CLOSED, from the record, without the cluster.** `proposer6`
correctly refused to assume. `pilots[0].execution_audit.stage_run_counts` = `{ts_qst2: 1, irc_forward: 1,
irc_reverse: 1}` ⟹ **P1 ran each stage exactly once.** The `double_execution` warning is `pilots[1]` (P1b)
only. The amber row stays amber. ⚠ The parsed report has now been richer than assumed **twice** (§0-j was
the other) — **look one level deeper before declaring a fact unobtainable.**

---

## ADR-097: **the reach test can never be verified at the artefact** — ADR-057's blind spot, named by `critic8`

`tests/` has never shipped and should not — it is dev/CI tooling, structurally distinct from the runtime
package. 🔴 **But this is the first round whose primary deliverable is a TEST'S EXISTENCE rather than
runtime behaviour.** `critic8` verified all four wirings by direct execution against the shipped files —
a full ADR-057-compliant claim about *what ships now*. It is **not**, and structurally cannot be, a claim
that *a regression test exists which will catch a future revert*: that claim's evidence is guaranteed to
be absent from anything ADR-057 permits a critic to inspect.
```
BUILD_STAMP.json records  source_digest · n_files · per-file hashes
it records NOTHING about  which tests passed — though the suite IS a build gate (1204 OK this round)
```
⟹ a critic reviewing a future artefact must **trust a report** that the reach test exists and is green —
**exactly what R21/ADR-041 exist to prevent.**
🟢 `critic8`'s proposal, adopted as a next-round item, not built now: **`BUILD_STAMP.json` (or an adjacent
file) records which NAMED tests passed for a given digest — identity and result only, never content.**
Same code-field/human-warning split `execlog.py` already uses, one level up at the build itself.

---

## ADR-098: 🔴 **an unlabelled TEST FIXTURE inside an ADR was read as measured data** — and the fixture was the lead's

**Date**: 2026-08-19 · Caught by `proposer6` (what does it MEAN?) and independently by `engineer6` (could it EXIST?) · **Cause: the lead** · **Status**: ADOPTED

`engineer6` made `19/19 closed-shell vs 0/4 open-shell converged` its **"most load-bearing single number"**,
cited `[MEASURED]`. 🔴 **It is the lead's construction** — written in ADR-087 to demonstrate that a pooled
`convergence_rate` hides a dead stratum, reused in ADR-088 to specify a *discriminating* fixture. Its only
occurrence in this log is a line about how to design a regression test.

**Every measured `converged` record the project owns — 17 step records, 3 species:**
```
hco3_anion     A True · B True · C True · D_builtin True · D_gen True
li_ec_cation   A True · B FALSE · C True · D_builtin True · D_gen True
li_ec2_cation  A FALSE · B FALSE (no cost) · C True
```
⟹ **THERE IS NO MEASURED OPEN-SHELL opt+freq CONVERGENCE STATISTIC AT ALL.** The two Li complexes that
failed are the U-55 class, not an open-shell stratum.

🔒 `HANDOFF §0.3` already says *"대조군 출력에는 반드시 라벨을 붙여라"* — and it exists because a **coder's**
labelled control was once misread by a **lead**. **This time the LEAD wrote the unlabelled fixture INSIDE
AN ADR**, the document type most likely to be quoted as fact. **RULE EXTENDED: a constructed number carries
`[FIXTURE — CONSTRUCTED, NOT MEASURED]` on the same line as the number. Prose context is not a label.**

🟢 **Both specialists refused to assume, by DIFFERENT routes; either alone would have caught it.**
`[UNVERIFIED PROVENANCE]` is adopted as a third label — we had no state for *"I cannot trace this."*

🔒 **THE TALLY: 302.4 core-h (ADR-096) · the 0/4 anchor (here) · B0-F's "ref-core-h" (ADR-095).
Three numbers in two days. NO arithmetic errors among them. All three were a number separated from the one
fact that makes it mean something.**

---

## ADR-099: 🟢 **USER RELEASES B0** — and rules a TWO-STAGE optimisation: rough first, then tight opt+freq

**Date**: 2026-08-19 · **Decision: the user, directly** · **Status**: ADOPTED — this closes the sixth of the six standing user decisions

> *"B0를 돌려볼게. 단분자 계산이 아니니까 rough한 계산으로 먼저 돌리고, 이 계산이 끝난 이후 tight한
> 조건에서 opt+freq 계산을 하는게 좋겠어."*

**B0 IS RELEASED.** The user additionally rules the optimisation protocol, on the grounds that these are
**not single-molecule calculations** — Li⁺ solvation complexes are floppy, multi-minimum systems:
```
STAGE 1   rough / loose optimisation      — get into the basin cheaply
STAGE 2   tight opt + freq, from stage 1's converged geometry  — the certification
```
🟢 **This does NOT relax C-8 or `proposer6`'s Tight requirement.** The *final* certification is still
`opt=(tight,calcfc,...) freq` with `n_imag == 0`; stage 1 is a cheaper approach to the same endpoint.
`proposer6` named Tight as the one thing it would refuse to relax — **it survives, and arrives cheaper.**
🟢 It also attacks the failure `proposer6` pre-registered against itself: **CalcFC on a hand-drawn guess
gives an initial Hessian with tiny/negative eigenvalues and erratic first steps.** Starting Tight from a
loose-converged geometry is strictly better conditioned than starting it from `GUESS GEOMETRY (idealized,
not optimized)`.

### 🔴🔴 THE ONE WAY THIS GOES SILENTLY WRONG — `nosymm` MUST BE ON **BOTH** STAGES
§0-g measured it: a GFN2 `--opt tight` optimisation **moved every interatomic distance and did not break
the exact degeneracy** — the gradient along the symmetry-breaking coordinate is exactly zero, so an
optimiser relaxes everything except the one thing that matters.
⟹ **If stage 1 runs without `nosymm` and without the out-of-plane perturbation, G16 re-detects and
re-imposes the point group, stage 1 converges ON the symmetry element, and stage 2 inherits it.** Stage 2
would then be a tight, freq-certified, fully converged calculation **on the wrong structure**, and every
log would say "converged."
🔒 **B-2's `nosymm` requirement and C-9's perturbation apply to the ROUGH stage, not only the tight one.**
The perturbation must happen **before stage 1**, not between the stages. A new `endpoint_opt_rough`
job_type is required alongside `endpoint_opt_freq`, and BOTH go in `_nosymm_required_job_types`.
⚠ Corollary: `proposer6`'s F1 emit-list must be captured at **stage 1's** convergence as well — point
group and ∠Li–O=C at stage-1 exit is the cheapest possible detection of this failure.

---

## ADR-100: **a count that travelled without the word for what it counts** — and `[FIXTURE]` becomes a first-class label

**Date**: 2026-08-19 · **Chain: lead → ADR-066 → `proposer6`, caught by `engineer6`** · **Status**: ADOPTED

### The defect and its propagation
`01_DECISION_LOG.md:5367`, on a line headed **"Lead-verified, every number"**, read:
> *"planarity — all **11 heavy atoms** z = 0.000000 in BOTH files; H's at ±0.880/±0.850"*

Measured by the lead from the shipped files: `C3 H4 Li O3` = **11 total, 7 heavy**, all seven heavy at
z = 0.000000. 🔴 **11 is the TOTAL count wearing the word "heavy" — and the same line placed 4 H at ±0.880,
so its two halves contradicted each other.**
🟢 **No conclusion moves.** Every heavy atom IS at z=0; Cs-planar-by-construction, ADR-066/067/080 stand.
🔴 **But it is load-bearing for SIZE**, and it propagated: `proposer6` read the species as half again as
large and wrote **"14-atom"** — a value no source ever contained. `engineer6` caught it by opening the file.
🔒 **One error propagating, not two independent ones.** ⟹ **a count must travel with the word for what it
counts.**

### 🔒 The sharper half, which `proposer6` recorded against itself
`grep -rn "14-atom" docs/` returns **only its own text**. It did not carry a stale number — **it produced
one**, inside a sentence otherwise made of measured values (220.8 core-h, level2, SMD), which is what made
it readable. And the correct value was in **its own document**, `02_METHOD_SPEC.md:7349`, attached to the
very quantity it was labelling: *"220.8 core-h for the QST2 stage on an **11-atom system**"*.
🔒 **Not an information gap — a failure to read the sentence being paraphrased.** ⚠ And the error ran in
the **optimistic** direction (§0-h), inside an argument that other people's numbers were biased optimistic.
🔴 **Consequence**: the production-tier extrapolation off the 220.8 anchor is `(30/11)³ ≈ 20×` under N³,
not `(30/14)³ ≈ 10×` — **~2× more severe than its own label implied.** The bias ledger on 302.4/220.8 is now
**four low-side items against one high-side**.

### 🟢 `[FIXTURE]` — adopted as a first-class label (proposer6's proposal)
ADR-098's mislabel had a structural cause: the vocabulary was `[MEASURED]` / `[ESTIMATE]` /
`[LITERATURE]`, with **no token for "constructed for a test"**. ⟹ a fixture must be forced into one of the
three or left bare. 🔒 **A missing category does not produce a gap; it produces a mislabel, and the
mislabel lands on the most authoritative-looking token available.**
```
[FIXTURE]  a value constructed for a test. 🔴 MAY NEVER BE AN INPUT TO A DECISION.
[UNVERIFIED PROVENANCE]  a value that cannot be traced to a raw record (ADR-098)
```
⚠ `proposer6`'s asymmetry, which is why this is not solvable by care: **a stale measurement usually carries
a date, a species, a machine — staleness is detectable ON the number. Constructedness is detectable only
AT THE SOURCE.** `0/4` looks exactly like `0/4`.

### 🟢 And a falsifier repaired rather than defended
`proposer6` found that ADR-098 broke its own pre-registered falsifier: *"if the rate falls…"* was relative
to the `0/4` anchor, so with no anchor **it was not falsifiable** — the exact defect it demands from
others. It **withdrew** the relative clause and kept the two absolute ones (F3's ≤3-restart termination;
the structural half measured against experimental ≈138°, which is **external and therefore cannot have
been constructed by us**).
🔒 **The falsifier that died was the only one anchored to an INTERNAL number.** That is a general rule
about where to attach a falsifier, not an accident of this fixture.

### ⚠ A pattern deliberately NOT claimed
All three measured convergence failures are on the two Li complexes (non-Li converged 5/5), and those two
are exactly the ones ADR-080 showed on symmetry elements. **`proposer6` declined to claim it** — n = 3
species, with at least three rival explanations unexcluded (Li complexes floppy for non-symmetry reasons;
the Li basis/ECP path; the charge state). 🔒 **The honest weight of a consistency at n=3 is "do not update
much" — and it was the easiest place in this round to overclaim in one's own favour.**

---

## ADR-101: **the two-stage endpoint protocol, ruled** — same level, thresholds only; and the user's call removed a weakness the proposer had registered against itself

**Date**: 2026-08-19 · **Protocol ruled by the user (ADR-099); parameters by `proposer6` (§39.38); priced by `engineer6` (§R38.12)** · **Status**: ADOPTED

```
STAGE 1  #p nosymm {func}/{basis} {solv} opt=(loose,maxcycles=100) Int(Grid=UltraFine)
         no CalcFC, no freq
STAGE 2  #p nosymm {func}/{basis} {solv} opt=(tight,calcfc,maxcycles=200) freq Int(Grid=UltraFine)
         from stage 1's converged geometry; opt and freq in ONE route so the Hessian is taken at
         the geometry the opt actually converged to
```
⚠ Gaussian's numeric `Opt=Loose` values are `[UNVERIFIED]`. **Do not copy them from documentation —
G16 prints the active criteria in the log; record them from there.**

### 🔴 SAME LEVEL — and the reason is a SAMPLING argument, not a cost one
**Stage 1 produces a starting GEOMETRY, which carries no claim; stage 2 produces a CERTIFICATE.**
*"Certified on the wrong surface"* is the error of **transferring a claim** across surfaces — stage 1
transfers none, so a cheaper rough level does not commit **that** error.
🔴 **It commits a different one, and it is silent.** A cheaper surface can order basins differently:
stage 1 *selects* a basin, stage 2 optimises honestly inside it, and `n_imag == 0` is **TRUE**. The
certificate is honest and **the minimum is the wrong one** — invisible to every internal check
because **nothing is inconsistent**. Li⁺ complexes have near-degenerate coordination isomers
separated by less than any cheap surface's error; **that is the content of U-55.**
🔒 **The user's own stated reason for staging — *"단분자 계산이 아니니까"* — names precisely the species
class for which a cheap rough stage is least safe.**
🔴 **The grid is part of the level.** A coarser grid is a different surface and reintroduces the
basin error through a door nobody watches. `Int(Grid=UltraFine)` explicit in both stages.

### 🔒 THE LEAD'S STATED MECHANISM FOR Q1 WAS WRONG; THE RULING SURVIVED ON BETTER REASONS
The lead ruled `nosymm` onto stage 1 provisionally, arguing a symmetric stage 1 makes stage 2
*"certify the wrong structure with every log saying converged."* 🔴 **That holds only if `nosymm` is
missing from BOTH stages.** With `nosymm`+CalcFC+an honest `freq`, an on-element structure gives
`n_imag ≥ 1` and C-8.3 blocks it ⟹ **a symmetric stage 1 costs restarts at tight price, not
correctness.** The ruling stands for three better reasons:
```
(i)   fully silent only if `nosymm` is forgotten TWICE, and stage 1 is far the easier to forget —
      "it's only a rough opt" is exactly the sentence that omits it
(ii)  perturbing late throws away stage 1's work, re-done inside stage 2 at tight thresholds
(iii) without `nosymm` on stage 1, G16 UNDOES the perturbation at step 1 (B-2) — it may as well
      not exist
```
🟢 **And the perturbation is applied ONCE, before stage 1, never re-applied between stages** —
re-kicking a converged geometry displaces it off a real minimum. If stage-1 exit is still on the
element, the correct response is **stage 2's CalcFC imaginary eigenvector: a MEASURED direction,
strictly better than a random kick.**

### 🟢 THE USER'S PROTOCOL CALL REMOVED A WEAKNESS THE PROPOSER HAD REGISTERED AGAINST ITSELF
`proposer6` pre-registered that **CalcFC on a hand-drawn guess gives an initial Hessian with
tiny/negative eigenvalues and erratic first steps — and P1's species lives exactly there.** Staging
takes the protocol's one analytic Hessian at a **loose-converged** geometry instead. In its own
words: *"the user's instinct corrects a weakness I had flagged in my own recommendation and could
not remove without this staging."*
🟢 Second, independent benefit: **stage 1's geometry is a CHECKPOINT** — under the cumulative
384 core-h/endpoint budget, a stage-2 kill restarts from there rather than from the guess.

### 🟢 Q3 DISCHARGED AT ZERO COMPUTE — the stage-1 Hessian was already paid for
**Stage 2's `CalcFC` IS a Hessian at stage-1's exit geometry**, computed at step 1 before anything
moves. ⟹ **`n_imag` at stage-1 exit exists free in every run; nobody was emitting it.**
`config/f1_required_observables.json` now emits `n_imag_entering_tight_stage` plus
`stage1_exit_structural_set` (point group · ∠Li–O=C · max out-of-plane, purely geometric).
🔒 **A stage-1 exit whose point group is not C1 is a DEFECT REPORT ABOUT OUR ROUTE, not a fact about
the molecule** — and it reports before a single tight cycle is spent.

### Execution shape (`engineer6` §R38.12, adopted)
```
2 jobs per attempt, not 3 — stage 1+2 inside ONE PBS job per endpoint (the handoff is a file read,
   not a resource need); the two ENDPOINTS submit in PARALLEL (worst-case added wall 12 h → 6 h)
6 h / 384 core-h cap PER ENDPOINT, cumulative across both internal stages
🔴 terminal status records WHICH STAGE was running at kill. `stage1_budget_exhausted` and
   `stage2_budget_exhausted` never collapse, and NEITHER is `non_converged`.
   🔒 C-2's principle in a FOURTH place, reached independently from restart semantics (proposer6)
   and from budget accounting (engineer6), neither quoting the other.
```
### Where two-stage would be wrong (asked and answered narrowly)
`same-level rough` — **not wrong for any class**; one optimisation, one surface, an intermediate
stop, worst case cost-neutral. `cheaper-level rough` — **wrong for exactly B0's class**. `GFN2 rough`
— **not for endpoints** (§0-g: moves every distance without breaking the degeneracy). GFN2/CREST
keeps conformer generation only, applied **symmetrically**, output never an endpoint.
**Falsifier**: if stage-1-exit geometries differ from single-stage tight-from-guess geometries by
more than the convergence tolerance **on the same surface**, the intermediate stop is not neutral.
🟢 **Free to test — the pilot runs one endpoint both ways, which also measures the saving.**

### ADR-101 addendum — the priced envelope (`engineer6` §R38.12/§R38.13), and an honest read of it
```
                        per endpoint, core-h [KNL]
stage 1 (loose, full level, nosymm, UltraFine)   2.6 – 10.6    ← repriced upward; see below
stage 2 (tight + CalcFC + freq)                  4.9 – 30.4    unchanged; already priced as dominant
TWO-STAGE total                                  7.5 – 41.0
ONE-STAGE (tight from the guess)                12   – 45
```
🔒 **`engineer6` found its own gap when repricing**: its first pass had implicitly priced stage 1 as a
cheaper/default-settings job and **never applied the open-shell / `nosymm` / UltraFine multiplier stack**.
The Q2 ruling did not reverse that — **it made it visible.** Stage 1 went 3.0–4.0 → 2.6–10.6.

⚠ **READ THE COST CASE HONESTLY: it is now WEAK, and it is not why we are doing this.** Two-stage still
points below one-stage, but the ranges **nearly overlap at the top end (41.0 vs 45)** where they
previously did not. **Direction unchanged, margin narrowed.**
🟢 **The justification is PHYSICAL, not economic**, and it survives the narrowing untouched:
```
· the protocol's one analytic Hessian is taken at a LOOSE-CONVERGED geometry rather than at
  `GUESS GEOMETRY (idealized, not optimized)` — removing the tiny/negative-eigenvalue failure
  proposer6 had pre-registered against its own recommendation
· stage-1 exit `n_imag` and point group arrive FREE, before a single tight cycle is spent
· stage 1 is a CHECKPOINT: a stage-2 `budget_exhausted` kill re-pays only stage 2 (4.9–30.4)
  instead of the full two-stage cost. 🔒 That is the decision-relevant number for B0-F's EXPECTED
  spend — the 384 core-h/endpoint cap is a scheduler ceiling and does not move.
```
🔴 **Do not defend two-stage on cost.** If a successor re-derives the envelope and finds the overlap has
closed, **the protocol still stands on the three physical grounds above.** Recording this now so the
weaker argument cannot be mistaken for the load-bearing one later.

---

## ADR-102: **the ninth instance, in the round's own deliverable** — `endpoint_prep.sh` had no caller, and the rough route silently dropped the grid

**Date**: 2026-08-19 · **Both lead-caught by reading the artefact** · **Status**: ADOPTED

### (a) `Int(Grid=UltraFine)` was omitted from the ROUGH route — within the hour of the warning being written
`proposer6`'s Q2 ruling said, verbatim: *"**The grid is part of the level.** A coarser grid is a different
surface and reintroduces the basin error **through a door nobody watches**."* First implementation:
```
endpoint_opt_freq   #p nosymm {func}/{basis} {solv} Int(Grid=UltraFine) opt=(tight,calcfc,…) freq
endpoint_opt_rough  #p nosymm {func}/{basis} {solv} opt=(loose,maxcycles=200)       ← NO GRID
```
⟹ stage 1 on G16's **default** grid = a different surface = a **cheaper-level rough stage**, the exact
thing the same-level ruling forbids: a cheaper surface orders basins differently, stage 1 SELECTS one,
stage 2 certifies honestly inside it, `n_imag == 0` is **TRUE**, the minimum is wrong, and **nothing
internal is inconsistent so no check we own can see it.**
🔒 **The warning was written down and the defect walked through the named door inside the hour. That is an
argument for writing warnings down, not against.**

🟢 **FIXED, AND GUARDED BY PROPERTY RATHER THAN STRING.** `tests/test_endpoint_route_parity.py`
(lead-written) asserts the two routes' **surface tokens** — everything outside `opt=(…)` and the `freq`
token — are **identical**. Discrimination sweep, pristine outside `/tmp`, sha256 `605d951db6b5a9a9`, each
mutant JSON-checked, restore byte-verified:
```
M1  remove Int(Grid=UltraFine) from rough  [THE REAL DEFECT]   → FAILED (2)
M2  diverge the basis on rough                                 → FAILED (1)
M3  drop nosymm from rough                                     → FAILED (1)
M4  rough IDENTICAL to tight  [positive control]               → FAILED (1)
restore                                                        → OK
All FAILs, no ERRORs.
```
🔒 A per-token surface check makes a future grid/basis/solvent divergence **impossible to introduce
silently** — same shape as the reach test: **guard the property, not the string.**

### (b) 🔴 `endpoint_prep.sh` HAS NO CALLER — the ninth instance, inside the fix for the first eight
```
grep -rn endpoint_prep   plan.py · run.sh · b0_plan.py   →  NOTHING
collect.py:808           collect_endpoint_prep()          →  exists and is tested
```
**A payload script that exists, is tested, has a collector, and is unreachable from `./run.sh`.** It was
scoped out honestly (*"parallel two-endpoint submission — out of this scope"*), and that scoping is
defensible; **the consequence is that the user cannot launch anything.**
⚠ **And note the ASYMMETRY in our own instrumentation**: `test_producer_consumer.py` caught the coder the
moment it added **a payload artefact nobody reads.** It did **not** catch **a collector whose producer is
in no plan.** 🔒 **We instrumented one direction of the producer↔consumer edge and not the other** — a
next-round item, and a fifth face of the dominant class.

### 🟢 Two judgements by `coder8` that were better than the instruction
**`rough_level` resolved by DELETING the field, not populating it.** With rough at the same level there is
no separate value to hold; `ROUGH_LEVEL="$TIGHT_LEVEL"`, one env var, no branch. **Populating it would have
created a second copy of one truth** — ADR-090's disease. It removed a config key to implement a ruling.

**Refusing to write the CalcFC-Hessian parser without a real log**, and its reason, which generalises the
lead's own rule one level up: *"a hand-typed fixture of a format I don't have a real example of is exactly
the 'copy a number from documentation' trap — just at the FORMAT level instead of the VALUE level."*
🔒 **`[UNVERIFIED]` applies to a format, not only to a number.** `n_imag_entering_tight_stage` stays `null`
until the pilot's own log verifies the parser. **Free to compute is not free to parse.**

---

## ADR-103: 🔴 **`--emit-script` is broken for every item in the shipped tarball** — and the first face of the same defect is a comment three lines above the crash

**Date**: 2026-08-19 · **Found by the lead USING the package, not testing it** · **Status**: fix ordered to `coder8`

```
clean extract of src/dist/sei_pilot_cpu.tar.gz @ 12c793d774e87d08 · preflight rc=0
$ python3 -m sei_pilot.cli submit --emit-script <ANY ITEM> --profile cpu
  cli.py:702   wall_h=wall_h or entry["wall_h"]        KeyError: 'wall_h'
P1 · P5 · P6_t16 · endpoint_prep_reactant — ALL crash identically. Suite green at 1232.
```
**Diagnosis**: `wall_h` is not a field of a *planned* entry — it is **injected later**, at `plan.py:978`'s
`entry.update({"wall_h": wall, "chain_links": links, …})`, during sizing/reservation. `cmd_emit_script`
(cli.py:474) takes an entry straight from `planned` and hands it to `build_spec`, **skipping the step that
populates it.** Submit goes through sizing first, so it has the key.

### 🔴🔴 THE FIRST FACE OF THIS DEFECT IS A COMMENT THREE LINES ABOVE THE CRASH SITE
`cli.py:470`:
> *"🔴 실제 제출과 **같은 함수**로 큐를 정한다. 자기만의 폴백을 두었더니 emit 은 `-q normal` 을 보여주는데
> 제출본에는 `-q` 가 없었다."*

**emit and submit diverged once already — on the queue — and it was fixed by routing THAT ONE VALUE through
the same function.** The class, *emit and submit build `entry` by different paths*, was never fixed.
🔒 **A fix applied to the instance instead of the class, with the instance's own postmortem sitting at the
crash site.** Tenth instance of the round's shape, and the most on-the-nose.

### ⚠ And the test that claims this property is green
`test_pbs_script_shape.py` is documented as guarding **`제출본 ≡ emit-script`**. It passes. ⟹ it exercises
`build_spec` with a **hand-made entry that already has `wall_h`**, and never traverses the CLI path.
🔴 **ADR-041 says verify AT THE ENTRY POINT with real fixtures. This is that rule violated inside the test
written to enforce the property it fails to check.** A hand-made fixture verifies the CLI you imagined —
`HANDOFF §0.4`'s exact warning, one level up.

### The fix, ordered as the CLASS
```
1  emit-script and submit obtain `entry` from THE SAME sizing path.
   🔴 NOT an `entry.get("wall_h", …)` at the crash site — that patches the symptom and leaves
   emit ≠ submit for the next field to diverge on.
2  the test goes through `cmd_emit_script`, not `build_spec`, and must go RED on current code.
3  positive control: the emitted script for one item is BYTE-IDENTICAL to what submit would write.
   That is the property the old test claims and does not test.
```
⚠ **Impact**: `--emit-script` is the only way to run ONE item. Until fixed the user must run all ten via
`./run.sh` — survivable, since the re-run logic only re-runs failures, but the project's first real
calculation cannot be launched in isolation.
### 🔒 CORRECTION TO THIS ADR, BY THE LEAD, SAME DAY — the impact claim was inferred from a proxy
The heading above says *"broken for every item in the shipped tarball."* **The CRASH is real and
reproduced. The IMPACT claim was wrong.** Root cause (`coder8`): the sizing block that injects `wall_h`
only runs for an entry whose `status == "planned"`. On this dev box **there is no QC engine**, so every
Gaussian item is `skipped` — unsized — and `cmd_emit_script` handed the unsized entry to `build_spec`.
🔴 **On the cluster, g16 IS present, those items ARE planned, and they ARE sized.** So the claim
*"the user cannot launch one item in isolation"* was a statement about the CLUSTER inferred from a
measurement on a box that differs in exactly the variable that matters.
🔒 **Rule 20, committed by the lead, inside an ADR about a fix-the-instance-not-the-class failure.**
⚠ **And the positive case is STILL UNVERIFIED at the time of writing.** `coder8`'s fix makes the skipped
case refuse cleanly (rc=3, skip reason printed — verified by the lead on a clean extract). **That it EMITS
for a planned item is not established**: `coder8` verified four items, all of them the skipped case, and a
lead attempt to reach the planned branch with a `g16` PATH shim was not picked up by detection.
🔒 **"It no longer crashes" and "it emits" are two claims, and only the first is measured.**
⟹ verification ordered. Until it lands, `./run.sh` (all ten items) is the path that IS verified to work.

🔒 **Found by RUNNING the delivered artefact from a clean extract. 1,232 green tests did not find it.**
Two round trips were already lost to defects at the code↔site boundary that *"produced plausible output and
were invisible without the cluster"* — **this one was visible without the cluster, and only to someone who
used it.**

---

## ADR-104: 🟢 **USER RULING — implicit solvent is PCM at ε = 18.5 from B1 onward; B0 stays SMD and its results transfer**

**Date**: 2026-08-19 · **Decision: the user, directly, while the pilot was already running** · **Status**: ADOPTED

> *"B1 단계부터는 implicit solvent는 PCM을 사용할 거야. dielectric constant는 18.5를 사용해."*
> *"B0는 SMD로 유지하고 어차피 system에 따라 convergence 이슈는 SMD, PCM이 바뀌는 것 만큼이나 다르게
> 발생할 테니, SMD로 진행한 B0 결과값을 그대로 사용해도 전혀 문제 없어."*

```
FROM B1 ONWARD   implicit solvent = PCM, ε = 18.5 (numeric, never by solvent name)
B0               stays SMD. Its u_meas / r_comp / κ transfer to B1 sizing unchanged.
```
🟢 **ε = 18.5 is consistent with the project's own record**: `solvent.py:7` states EC:EMC 3:7 has
ε ≈ 18–20, against acetonitrile's 35.7 — *"roughly a factor of two on the reaction field."* 18.5 sits inside
the documented range.

### 🟢 The ruling DISSOLVES the C-5 blocker rather than satisfying it
C-5's entire refusal machinery exists because **SMD generic requires 7 descriptors for EC:EMC that nobody
has** — blocked on *"the 5 literature values for EC and EMC"*, and with the further problem that
**volume-fraction weighting of SMD descriptors is UNVALIDATED** (SMD was parameterised on pure solvents).
🔒 **PCM needs one number, and the user supplied it.** `solvent.epsilon_scan_line(epsilon)` already exists
and already sets ε **numerically, never by solvent name** — the mechanism is present and unwired.
⟹ **A dependency removed rather than met. That is the stronger resolution.**

### 🔒 The transfer argument, accepted as the user's call
The lead flagged that B0-measured `u_meas`/`r_comp` under SMD would size a B1 that runs PCM — an
`[UNQUANTIFIED-TRANSFER]`. **The user overruled on the ground that convergence behaviour varies by system
at least as much as it varies between SMD and PCM**, so an SMD-derived distribution is not a
model-specific artefact. **That closes the concern.** Recorded as the user's reasoning, not the lead's.

---

## ADR-105: 🔴🔴 **C-5 is wired into ONE payload — the eleventh instance, and it is live in the running pilot**

**Date**: 2026-08-19 · **Lead-measured by AST while the pilot was in flight** · **Status**: OPEN — first item of the next round

```
payload with a C-5 precheck        endpoint_prep.sh          ONLY
qc_adapter.sh:150 sei_qc_input     solvent=lvl.get("solvent_line", "")
                                   ⟹ the STATIC line from config/qc_levels.json
config level1/2/3 solvent_line     "scrf=(smd,solvent=acetonitrile)"      ε 35.7
solvent.solvent_line() callers     NONE outside solvent.py   [AST, not grep]
solvent.epsilon_scan_line()        NONE outside solvent.py   [AST, not grep]
```
⟹ **In the pilot now running:**
```
endpoint_prep_reactant   REFUSES at the C-5 precheck → exit 4, terminal_status
                         `solvent_descriptors_missing`. 384 core-h reserved, ~0 consumed,
                         🟢 ZERO chemistry — the refusal working exactly as designed.
P1 · P1b · P5            NO C-5 precheck. 14,464 core-h run in ACETONITRILE ε 35.7,
                         against EC:EMC's ε ≈ 18.5. UNREMARKED.
```
🔴 **This is ADR-066/067's incident recurring, and C-5 is the constraint written to prevent it.** The guard
is correct, is tested, and reaches **one** payload. **Eleventh instance of the round's shape.**
⚠ Note the shape is now the *inverse* of ADR-090's: those guards had **zero** callers. This one has **one**,
which is worse, because a single call site makes the guard look wired.

### 🔒 HOW TO READ THE PILOT REPLY — this is binding on whoever reads it
```
🟢 USABLE          cost figures — u_cheap, r, κ, wall, queue, throughput.
                   Continuum-SCRF cost is insensitive to WHICH continuum model; the electrostatics
                   solve dominates either way.
🔴 NOT USABLE      any CHEMICAL value — barrier, ΔG, TS geometry, IRC verdict.
                   These are ACETONITRILE results and cannot support an EC:EMC claim.
🔒 That split IS C-10: condition on chemistry, never adjudicate it. It applies here to a whole batch.
```
⚠ **And `endpoint_prep`'s `solvent_descriptors_missing` is a RESULT, not a failure** — it is the first live
demonstration that the C-5 refusal fires before spending core-h. Report it as such (C-2's principle: a
refusal and a wrong answer must not share an exit).

### The fix, ordered as the CLASS — first item of the next round
```
1  route qc_adapter.sh's solvent through solvent.py so EVERY item passes the SAME solvent decision.
   🔴 NOT a second precheck copied into each payload — that is what produced one-of-many here.
2  the PCM/ε=18.5 line comes from `epsilon_scan_line`-style numeric ε, never a solvent NAME.
3  a reach test in the AST style of tests/test_guard_reach.py: assert solvent.py has an external
   caller, and that no payload emits a solvent line by any other path.
4  🔴 the ε sensitivity scan's PURPOSE has changed and must be restated. The old ordering ruling was
   "the scan runs first and may make the descriptors moot". The descriptors are now moot by ADR-104.
   The scan's remaining value: does the barrier move by >0.05 eV between ε = 3 and ε = 90?
     · insensitive ⟹ ε = 18.5 vs 35.7 never mattered, and acetonitrile was overweighted all along
     · sensitive   ⟹ ε = 18.5 IS load-bearing and needs its composition stated (EC:EMC ratio)
```
⚠ **`solvent.py`'s C-5 docstring, refusal message, and module title all say "SMD".** They describe a model
the project is leaving at B1. Do not delete the SMD reasoning — B0 ran on it — but the module must stop
presenting SMD as *the* production solvent.

---

## ADR-106: 🟢 **USER DOMAIN KNOWLEDGE CLOSES TWO ITEMS** — ε sensitivity is SENSITIVE, and 18.5 is the conventional EC/EMC 3:7 value

**Date**: 2026-08-19 · **Source: the user, from their own experience** · **Status**: ADOPTED. Closes the ε sensitivity scan and the composition question in one step.

> *"dielectric constant sensitivity는 sensitive하다는게 내가 이미 경험적으로 알고 있고, 18.5는 EC/EMC 3:7
> base electrolyte에 보편적으로 사용되는 값이니 의심하지 말고 그대로 사용해."*

```
ε sensitivity   SENSITIVE.  [USER-DOMAIN]  — not measured by this project, and not to be re-measured.
ε = 18.5        the conventional value for an EC/EMC 3:7 base electrolyte.  [USER-DOMAIN]
composition     EC/EMC 3:7 — the question the lead raised is answered; do not re-open it.
```

### 🟢 WHAT THIS CLOSES
**(1) The ε sensitivity scan is DROPPED.** Its only remaining purpose (ADR-105 §4) was to decide whether
the barrier moves >0.05 eV between ε = 3 and ε = 90 — i.e. whether ε is load-bearing at all. **The user has
answered it.** Running a scan to re-derive a fact the domain expert already holds is not verification, it is
expenditure. 🔒 It was never a plan item, so nothing is de-budgeted — but it is off the forward scope, and
`solvent.py:23`'s *"ORDERING (Q2 ruling): the eps sensitivity scan runs FIRST"* is **SUPERSEDED**.

**(2) `solvent.py:97`'s `blocked_on` is void.** It reads *"the 5 literature values for EC and EMC, pending
the eps sensitivity scan"*. Both halves are now moot: the descriptors are moot by ADR-104 (PCM needs no SMD
descriptors), and the scan is dropped here. **The refusal must stop citing a blocker that no longer exists.**

### 🔴 AND IT STRENGTHENS ADR-105 RATHER THAN SOFTENING IT
ADR-105 offered two branches for reading the acetonitrile results: *insensitive ⟹ ε 18.5 vs 35.7 never
mattered and acetonitrile was overweighted*; *sensitive ⟹ ε 18.5 is load-bearing*.
🔴 **The sensitive branch is the true one.** ⟹
```
· ADR-066/067's concern about acetonitrile was CORRECT, not overweighted
· the running pilot's chemical values are MORE invalid, not less. ε 35.7 vs 18.5 is a factor of
  ~2 on the reaction field, on a quantity the barrier is known to be sensitive to.
· \U0001f512 the ADR-105 reading rule hardens: NO chemical value from P1/P1b/P5 may support an
  EC:EMC claim. Cost figures remain usable — SCRF cost is insensitive to WHICH continuum model.
```

### 🔒 A NEW PROVENANCE LABEL — `[USER-DOMAIN]`
ADR-098/100 established that **a missing label category does not produce a gap; it produces a mislabel, and
the mislabel lands on the most authoritative-looking token available.** The vocabulary was
`[MEASURED]` / `[ESTIMATE]` / `[LITERATURE]` / `[UNVERIFIED PROVENANCE]` / `[FIXTURE]` — **none of which fits
"the domain expert who owns this project knows this from experience."**
```
[USER-DOMAIN]   a fact supplied by the user from their own expertise.
                🟢 MAY be an input to a decision — unlike [FIXTURE].
                🔴 MUST NOT be cited as this project's measurement, and MUST NOT be
                   re-derived by spending compute to confirm it.
                ⚠ If a future result CONTRADICTS a [USER-DOMAIN] value, that is a finding to
                   RAISE, not to silently average with. Take it back to the user.
```
🔒 Without this token, *"ε is sensitive"* would have been written `[MEASURED]` by the next reader — the
exact failure that produced ADR-098's `0/4`. **The label exists so the value stays both usable and honest
about where it came from.**

⚠ **The lead raised the composition question once and the user answered it definitively. It is closed.**
Recorded here so a successor does not re-open it as an open question.

---

## ADR-107: 🔴🔴 **The array items were never task-dispatched.** One root cause, five symptoms, ≥944 core-h burned, and both P1b and P5 are VOID for this round

**Date**: 2026-08-20 · **Decided by**: lead (acting for the user, who handed over the role for this window)
**Evidence**: `cpu_machine_pilot_results/sei_pilot_work/` — the user returned the raw logs alongside the
parsed JSON, as §0-o.2 demanded. Everything below is read off that tree, not inferred.

### The defect
```
plan.py:274    P5  submitted as array=(1,22)   -> rendered "#PBS -J 1-22"  (jobs/P5/P5.qsub)
plan.py:303    P1b submitted as array=(1,3)    -> rendered "#PBS -J 1-3"   (jobs/P1b/P1b.qsub)
P5.sh:73       while read ... done < "$D/tasks.tsv"      <- iterates the WHOLE list
P1b.sh:108     done < "$D/targets.tsv"                   <- iterates ALL THREE species
```
Neither payload reads `PBS_ARRAY_INDEX` / `SLURM_ARRAY_TASK_ID`. **The only payload in the package that
reads an array index is `payload/probe_throughput.sh:8`** — the one item that was written as an array from
the start. P5 and P1b became arrays later (§R22.8/§R22.9) and inherited nothing.

`templates/pbs.sh.tmpl:26` compounds it: every task of an array gets the **same** `SEI_JOB_DIR`, the same
`SEI_KEY` and the same `SEI_LOGICAL_KEY`. So N tasks, on N different nodes, executed the identical workload
into one shared directory on `/scratch`.

🔒 This is the same shape as ADR-048 (`array is 1 core per task`, hardcoded): **a design change to arrays was
made without checking which assumptions of the pre-array design it broke.** ADR-048 fixed the resource
assumption. Nobody checked the *work-partitioning* assumption, which had never needed to exist before.

### The five symptoms, all measured
```
1  P1b concurrency   executions.jsonl: 3x "action":"run", hosts node2660/2661/2662, 0x "finish"
                     stage_events.jsonl: 7 of 13 stages ran 3 times each
                     steps/li_ec2_cation_B_high_optfreq/: THREE G16 processes (Gau-13681/48768/
                     52931.rwf, 322 MB each) sharing ONE job.chk and ONE job.log.
                     "Normal termination" count: 0. Killed by the user's qdel.
2  P1b ORDER BROKEN  hco3_anion_C_high_sp_on_cheap ran 643-670 s while the step that PRODUCES its
                     input geometry, hco3_anion_A_cheap_optfreq, ran 512-681 s.
                     ⟹ C consumed a cheap geometry that was still being written.
                     ⟹ even the rc=0 stages cannot be attributed to a known input.
3  P5 total loss     22 tasks raced on the fixed path tasks.tsv (written with ">"), most read an
                     empty or partial file, the loop body ran zero times, all 22 exited in 38 s.
                     species/ is empty; p5_results.json rows = []; 0/14 species converged.
                     module_load.log is interleaved output from 22 nodes.
                     state/ holds P5.done.json (node2906, rc=0) AND P5.failed.json (node2909, rc=1).
4  ACCOUNTING        P1b reported core_hours_total = 322.1 (= the 12 stages/*.json summed; critic9
                     re-added them to 322.08). A FLOOR on what was actually spent is
                     3 tasks x 64 cores x 4.92 h = >=944 core-h, where 4.92 h is
                     max(end_epoch) 1787145212 - min(start_epoch) 1787127473 over those same 12
                     stage markers. Stage markers are shared across tasks, so duplicate
                     consumption is invisible to the budget.
5  AUDIT BLIND       collect.py:82 execution_audit() detects duplication only via stage_events.
                     P5 died before reaching sei_stage, so it has no stage_events, so the report
                     says "duplicate_execution": false while links_executed lists "P5" 22 times.
```

### Rulings

**R-1 🔴 Every P1b number from this round is VOID, not merely untrusted.** Symptom 2 removes provenance:
we cannot say which run produced the geometry any rc=0 stage consumed.
🔴 **`critic9` supplied a stronger and more general basis for this than symptom 2, and it is the one to
quote**: of the 13 stages, 7 demonstrably ran three times; the other 6 show one run plus `skip_done`
because they happened to be short enough (single points) to finish before the other tasks reached them.
But a stage marker is written **after** the computation, so "looks singly-executed" never proves it was.
⟹ the basis for VOID is **not "contamination proven everywhere"** — it is **"cleanliness cannot be proven
anywhere"**, which covers all 13 stages instead of 7. A TOCTOU gap, not a counting argument. This is a stronger statement than
the standing ADR-088 quarantine, and it does not lift when ADR-088's C-1 gating lands (it already has, in
`sei_pilot/criteria/p1b.py`). `r`, `r_composite`, `r_high` remain **unmeasured**.

**R-2 🔴 P5 measured nothing.** 0/14. U-59's prohibition on fitting a size-scaling law to P1b/P5 unit costs
is unaffected and un-weakened: there are still no points to fit.

**R-3 🟢 P6 stands, pending `critic9`.** κ = 1.218, speedup(16→64) = 1.588. P6_t1/t16/t64 are **three
separate items, not an array** (`plan.py:317` refused to make them one, precisely because `select=` cannot
vary per task) — so this defect cannot have touched them, and `cores_observed == cores_requested` holds for
1/16/64. ADR-048's failure mode is excluded. `critic9` is verifying this against the raw logs because κ is
the unit of every subsequent estimate.

**R-4 🟡 P1's cost figures are candidate-usable, pending `critic9`.** 527.8 core-h, wall 8.26 h,
breakdown ts_qst2 267.8 / irc_forward 125.7 / irc_reverse 134.3. P1 was a chain, not an array, so the
defect does not reach it. Its `executions.jsonl` shows run 1 / skip_done 2, which is the B-1 chain fix
behaving as designed — `critic9` is confirming that reading rather than assuming it.

**R-5 🔴 U-56 stays UNMEASURED and no S3 production starts.** P1's chemistry (imag −48.4 cm⁻¹ outside the
−2000…−100 window; IRC endpoints identical, rule R3) counts in **neither** direction: the run was in
acetonitrile ε 35.7, which ADR-106 hardened from "overweighted concern" to "the sensitive branch is the
true one." A TS attempt outside the method's stated preconditions is not a TS failure.
⚠ Separately, the report flagged itself: `c10_cost_probe_violations` records that P1, a **cost** probe,
is carrying `status: "fail"` plus chemical `fail_reasons` — the §39.4(g) R-4 / ADR-090/091 violation — and
that the collector did **not** act on it. The guard detected the mislabel and shipped it anyway.

**R-6 🟢 A guard worked, and it should be said.** `endpoint_prep_reactant` returned
`solvent_descriptors_missing` / "C-5 refuses to proceed with acetonitrile" and spent 0.0 core-h. That is
ADR-105's wiring stopping the exact class of waste this ADR is otherwise about.

**R-7 🔒 No array item may be resubmitted until per-task dispatch lands with a test that reproduces the
concurrency.** A test that only proves "task 1 runs its share" passes on a broken implementation. The
regression test must fail on today's code for the reason today's code is broken.

**R-8 🔒 The budget guard cannot be trusted for array items** until symptom 4 is fixed. `max_core_hours`
21,000 was compared against a number that under-counted actual consumption by ~3x on the one array item
that got to run. Treat the guard as advisory for arrays, load-bearing for everything else.

### 🔴 R-9 — the round left both broken items in a state where `./run.sh` will NOT retry them
`cli.py:588-601` branches on done / failed / submitted:
```
P5   state/P5.done.json EXISTS  (written by node2906, rc=0, having computed nothing)
     -> is_done() -> "이미 완료 → 건너뜀 (멱등 재개)".  0/14 species, never retried.
P1b  only state/P1b.submitted.json (qdel killed the payload before it could mark anything)
     -> is_submitted() -> "이미 제출됨(진행 중) → 건너뜀".  Not running. Never retried.
```
🔒 This is a **re-entry of the exact accident `cli.py:591-595`'s comment was written to prevent** — *"실
클러스터에서 P1/P1b/P5 가 rc=3 으로 죽은 뒤 `./run.sh` 를 다시 쳐도 아무 일도 일어나지 않았을 것이다"* —
arriving through a different door: not a stale `failed` marker this time, but a **false `done`** that one
racing array task was able to write on behalf of the whole item. A fix that closes one door and not the
class is how this returns a third time. Assigned to `coder9` as A-1e: per-task markers, item-level `done`
only when every task is accounted for, and the same treatment for `common.sh:122`'s idempotent-resume check.
🔴 **And `--force` does not save us.** `cli.py:588` returns on `is_done()` with **no `and not args.force`**
— that guard exists only on the `is_failed` and `is_submitted` branches. So:
```
P1b  submitted-only  ->  ./run.sh --force DOES resubmit it
P5   false done      ->  ./run.sh --force does NOT. The done marker outranks force.
```
⟹ The only remaining escape for P5 is deleting or renaming `state/P5.done.json` by hand — and the user's
standing instruction for this window is **delete nothing without permission**. The code has manoeuvred the
user into a corner whose only exit is the one action they forbade. `coder9` must build an explicit
"un-run this item" path (named items, printed before it acts — blanket force-over-done would burn the
core-h of the items that *did* succeed). Until that lands, the cluster-side `state/` question goes back to
the user as a question, not an action.

### 🟢 `critic9` INDEPENDENT VERIFICATION (2026-08-20) — all five symptoms confirmed, plus two additions
Recorded in `04_REVIEW_LOG.md`. Verdict: not a BLOCK; the diagnosis stands. Confirmed against the raw logs:
symptom 2's epochs to the digit; symptom 3's interleaving shown with `cat -A` (two messages concatenated
with no newline between them — a genuine fd race, not repeated output); P5's rc distribution measured as
**rc=1 x21, rc=0 x1** (lead re-confirmed) — and the single rc=0 is exactly the task whose false `done`
marker now blocks resubmission (R-9). κ = 1.218 cleared: `declared == requested == cores_observed ==
nprocshared` on all three P6 tasks, distinct hosts, and 216/177.3 = 1.218 checks out. P1's 527.822 core-h
cleared: run 1 / finish 1 / skip_done 2 under *different* link names (`P1_c1`, `P1_c2`) — the B-1 chain
guard declining to re-run a finished link, which is the opposite of duplication. C-5's refusal cleared as a
genuine guard (`solvent_precheck.err` carries the human-readable reason; `module_state=loaded`, so G16
itself was fine).
🟢 **ADDITION**: the `.btr` files show `A_cheap_optfreq` was touched by **at least two hosts**, so the
contamination is slightly wider than symptom 1 as written. Conclusion unchanged.

### 🔴 THE MTIME TRAP — `critic9` raised a MAJOR here and the lead OVERTURNED it. Read this before timing anything.
`critic9` measured `steps/*/job.log` mtimes out to epoch 1787176578 and derived 13.68 h elapsed and
**2,626 core-h**. That is wrong, and the way it is wrong is worth more than the number was:
```
state/P5.done.json                          mtime 1787176572   CONTENT epoch 1787127510
jobs/P1b/stages/p1b_hco3_anion_A_...json    mtime 1787176577   CONTENT end_epoch 1787127681
jobs/P5/p5_results.json                     mtime 1787176687
results/sei_probe_report.cpu.json           mtime 1787176690
jobs/P6_t1/executions.jsonl                 mtime 1787176575
```
P5 finished in 38 s and stamped its marker at 1787127510 — yet that marker file's mtime is 13.6 h later.
**Every file in the tree, P5 and P6 and P1b and results alike, has an mtime inside a ~2 minute window.**
That is one `cp`/`rsync` without `-p`, not a simultaneous kill. 🔒 **mtimes in the returned tree are
TRANSFER times. The only valid time evidence is the epochs written INSIDE the files** (`stages/*.json`,
`executions.jsonl`, `started.json`, `*.done.json`). Anyone timing anything from this tree must be told
this — it is a trap that produced a confident 2.8x error on the first attempt.

### 🔴 BUT THE HALF critic9 GOT RIGHT: >=944 IS A FLOOR AND MUST NEVER BE QUOTED AS A CENTRAL VALUE
The stage markers cover only up to 1787145212. After that, `li_ec2_cation_B_high_optfreq` started and ran
until the `qdel` — **and that stage has no marker file at all**, because it never finished. That interval
is not recoverable from any file content in this tree. `executions.jsonl`'s first `run` (1787127429,
node2661) is also 44 s earlier than the first stage marker, so the start moves slightly too.
```
>=944 core-h    [MEASURED, FLOOR]  stage-marker interval only
actual burn     2,605.5 core-h     [MEASURED] from PBS accounting -- see below
```

### 🟢 SETTLED THE SAME DAY — the user supplied `qstat -x -f` and the real number is 2,605.5 core-h
```
P1b 23631761[]   stime Wed Aug 19 17:16:59  ->  obittime Thu Aug 20 06:51:13   = 13.5706 h
                 Exit_status 1 · comment "Job Array Began ... and terminated"
                 walltime requested 48:00:00, died at 13.57 h  ⟹ NOT a walltime kill (the qdel)
                 executions.jsonl has 3 `run` and ZERO `finish` ⟹ all three tasks were still
                 alive when it was killed ⟹ 3 x 64 x 13.5706 h = 2,605.5 core-h ACTUAL, not a bound
P5  23631751[]   stime 17:16:59 -> obittime 17:20:37 = 218 s, Exit_status 0, "finished"
                 per-task run→finish ~38 s ⟹ ~15 core-h. The 218 s parent window is start stagger.
```
⟹ the lead's floor of ≥944 understated the real figure by **2.76x**. The floor was honestly labelled a
floor, and it still cost nothing to be wrong — but it is the reason R-12's rule (never fill an unknown
with a bound) is written the way it is.

🔴 **AND THE MTIME TRAP ENTRY NEEDS AN HONEST AMENDMENT.** `critic9`'s withdrawn estimate was **2,626
core-h — within 0.8% of the truth.** The method was still invalid: mtimes are transfer times, and
`state/P5.done.json`'s mtime sits 13.6 h after the epoch inside it, which no timing argument survives. It
landed close because the user copied the tree **five minutes after the kill** (job death 21:51:13Z, copy
window 21:56:12–21:58:10Z), so for *P1b specifically* transfer time ≈ end time. 🔒 **A right answer from
an invalid method is still an invalid method** — the same mtimes give a 13.6 h error on P5. But recording
only the rebuttal, and not that the rebutted number was nearly right, would be its own kind of dishonesty.

🟢 Environment fact recovered from the same dump: `Resource_List.knl_cluster_mode = quadrant`,
`knl_memory_mode = cache` ⟹ **these are KNL nodes**, consistent with the 68 cores/node probe and with the
glossary's `KNL core-h` unit. No action; recorded so the unit question is never re-derived.
🔒 The only way to settle it is PBS's own accounting — `qstat -x -f 23631761[]` or the site accounting
log's `resources_used`. Not in the tree. **Ask the user.** Until then the true figure stays unlabelled
rather than being filled in with the floor, which is exactly the substitution ADR-098/100 are about.

### 🔴 THE TWELFTH INSTANCE IS ALREADY SCHEDULED — `endpoint_prep` product, and it is prevented for one line
`critic9`'s forward sweep (lead re-verified every line reference below). The defect's exact shape:
`templates/pbs.sh.tmpl:26` bakes `SEI_JOB_DIR` at render time, so array expansion cannot separate it; and
`common.sh:76` keys `sei_stage` markers on the stage NAME alone, with no task discriminator.
```
ARRAYS TODAY     probe_throughput  SAFE (reads the index)  ·  P5 BROKEN  ·  P1b BROKEN
WOULD INHERIT    P1.sh:52,72,124,161   crest/ts_qst2/ts_opt/irc_${dir} — fixed names. P1 is a chain
                 today, so it is fine; parallelising several TS guesses as an array breaks it at once.
🔴 NEXT ONE      endpoint_prep.sh:133,186  endpoint_rough / endpoint_tight — NO role suffix, while the
                 product endpoint is already in scope (§0-m, §0-o.5). Merging reactant+product as
                 array=(1,2) with role mapped to the index is instance twelve, immediately.
🟢 PROTECTED     P6_t1/t16/t64 and probe_queuewait cannot become arrays: their per-task select= /
                 node count differ, and merging P6 would delete the thread-scaling S it exists to
                 measure. plan.py:317-323 wrote the reason down. Structural, not luck.
P4 (GPU)         single species today. A species screen would make it the next array candidate.
```
🟢 **AND THE FIX IS ALREADY IN THE REPOSITORY, TWICE.** `probe_throughput.sh:8-9` reads the index and
splits its output into `starts/task_${TID}.json`; `P6.sh:51` parameterises the marker name itself as
`sei_stage "anchor_t${NP}"`. Nothing needs inventing — the two working patterns are the spec.
🔒 Assigned as A-1f (put the role into `endpoint_prep`'s stage names now, one line, plus a comment saying
to ship product as a second Item rather than an array — `plan.py:317-323`'s stated reason applies verbatim)
and A-1g (**index dispatch alone is not enough**: if every task still regenerates `tasks.tsv` with `>`, the
race survives and is merely masked by the content being deterministic — which is precisely where P5 died).
`critic9` holds a five-point checklist and will diff `coder9`'s patch against it.

### 🟢 U-76 RESOLVED SAME DAY — it was a counting UNIT disagreement, and the lead rules for 22
`p5_task_budgets()` produces **22**; the `tasks.tsv` the round generated has **18** rows. `critic9` found
the cause: the two count different things. `tasks.tsv` enumerates **species x seed** (14 + 4 dual-seed =
18), and the cheap-level run for the 4 `cheap_level_too` species is not a row at all — it is spliced in
*inside* `run_one()` at `P5.sh:69-71`. 18 rows + 4 spliced cheap runs = the 22 that `_p5_runs()` counts.
Neither number was wrong; they were units.

🔒 **LEAD RULING: the unit is the RUN, and there are 22.** Reasons, in order:
```
1  plan.py:273 already said so       "실행 1건 = array 태스크 1개"
2  the budget only works that way    p5_task_budgets() sizes each task by N^3. A task that ran a
                                     primary AND a cheap run would not match either budget.
3  it makes dispatch trivial         one line = one task = one G16 job. Nothing conditional inside
                                     the loop body, so nothing for an array index to get wrong.
4  one enumeration, not two          the 18-row list and the 22-run list must stop coexisting.
```
⟹ `tasks.tsv` becomes 22 rows carrying `(species, seed, level)`, and the payload selects `runs[TID-1]`.
🟢 `coder9` had already reached the same design independently while this was being adjudicated —
`_p5_runs()`'s docstring now carries the rule and names the accident it prevents. Convergent, not copied.
⚠ Whichever way this had gone, one of the two numbers had been silently wrong in every wall and budget
figure built since §R22.9. That is the part to remember: **the bug was not either count, it was that both
existed.**

### 🔒 R-10 — the c10 violation stays reported, but it gets WIRED to the channel that already exists
`critic9` was asked what the collector should have done when it detected that P1, a cost probe, was
carrying a chemical verdict. Ruling, adopting `critic9`'s recommendation:
```
A  report it and ship (today's behaviour)      🟢 KEEP
B  auto-correct status to a neutral value      🔴 REJECT — criteria/p1.py:363-372's own comment says
                                                  this is a LEAD scope decision, not an implementation
                                                  one. A coder silently overturning that is the
                                                  category of error ADR-079 is about.
C  refuse to emit the report                   🔴 REJECT — ADR-092 measured a 67% false-positive rate
                                                  on this guard family. One false positive destroying
                                                  an entire cluster round-trip (RT ~= 3.5 calendar
                                                  days) is a far worse trade than a mislabel.
```
🔴 **But A has a missing wire, and that wire is the whole cost of the defect.** `cli.py:923
collect_unresolved()` lifts P1's four IRC items into `unresolved_for_lead` and contains **not one line**
about c10 — while `report.py:176`'s own comment defines that field as *"판정 대기 중인 규약 = lead 가
여전히 눈이 먼 항목"*, which is precisely what a c10 violation is. Measured on this round's artifact:
`unresolved_for_lead == []`, and `c10_note` sits nested inside `pilots[0]` where a reader of the top-level
summary never meets it. **That nesting is the literal path by which the next reader concludes "P1 failed"
means the chemistry failed — and U-56 turns from UNMEASURED into a phantom 0/1.**
⟹ Assigned to `coder9` as **A-5**: if any `pilots[*].c10_cost_probe_violations` is non-empty, raise an
entry into `unresolved_for_lead`. This is not moving from A to B — it is connecting an existing
"waiting on the lead" signal to the existing "lead reads this" channel. Outside ADR-090 §5's ordering, so
it is registered as its own item rather than smuggled into that list.

### 🔒 R-11 — no work inside a payload that the planner's budget model does not represent
From `critic9`'s partial review of the patch. `P1b.sh:132-141` gave the stagewise measurement (8 G16 runs)
and the U-27 NonEq smoke (up to 6) to *the last species task* — the 22-atom one, whose budget
`plan.py:134` sets at **3,072 core-h = 64 cores x 48 h, i.e. 0% headroom**. The payload comment said so
itself: *"예산표(§R24.1)는 이 몫을 어느 태스크에도 배정하지 않았다"*, marked "[코더 결정, lead 확인 요망]".
🔴 **The lead did not confirm it.** Knowing the budget table does not cover the work and adding a comment
is not a mitigation — the planner's guard cannot see inside a payload, so the failure mode is a silent
wall-kill leaving partial data and no marker. **That is this round's failure, replayed.**

**RULING: stagewise + U-27 become a fourth array task with their own budget line.** The lead verified the
dependency question before ruling, because splitting work that *does* have a sibling dependency is how
symptom 2 happened:
```
stagewise  P1b.sh:145  TSGEOM = ${SEI_WORKDIR}/jobs/P1/ts.xyz, else a package input
U-27       P1b.sh:220  U27_SRC = ${SPEC_DIR}/${U27_F}, a package input
```
Neither consumes a sibling task's output, and P1's geometry is already guaranteed by `depends_on=["P1"]`.
⟹ separation is strictly safer than the status quo. 🔒 `plan.py:311-313`'s constraint is untouched: the
ratio `r_composite=(A+C)/A` must complete **inside one task**, so the three species tasks keep their
boundaries; task 4 carries only the measurements that are not per-species.
⚠ Task 4's budget must be *derived* (same N³ rule, real atom count) and its provenance stated — not chosen.

### 🔒 R-12 — stage markers must carry the build digest, or the next round inherits this one's contamination
`critic9` found R-9's defect **one layer down**. `common.sh:95-118`'s `sei_stage` skips any stage whose
marker says `rc=0`, and the marker records nothing about *which build produced it*. So resubmitting into
the existing `jobs/P1b/` — whose `stages/*.json` are the contaminated ones from this round — makes the
**fixed** code read "already done" and inherit the poisoned values. `--force` does not reach it;
`sei_stage` never sees `args.force`.
```
R-9   state/<key>.done.json    a false ITEM-level completion   -> blocks resubmission
R-12  jobs/*/stages/*.json     a false STAGE-level completion  -> silently inherits bad data
```
🔒 Same shape, two layers. Fixing only one returns the other next round.
**RULING**: reuse what exists — `src/build_stamp.py`'s `source_digest` already identifies the package
build. `sei_stage` records it; resume requires `rc=0` **and** a digest match; a mismatch re-runs **loudly**;
a marker with no digest field counts as a mismatch, which is exactly what invalidates this round's set.
⚠ The returned tree is evidence and stays untouched. The cluster-side `jobs/P1b` and `jobs/P5` are a
**rename**, never a delete, and the user decides.

### 🔴🔴 R-14 — THE NEXT SUBMISSION WOULD REFUSE EVERYTHING. A user ruling is required, and the lead will not substitute for it
`coder9` wired ADR-105 properly: `config/qc_levels.json`'s five hardcoded `solvent=acetonitrile` lines are
gone, and every payload now asks `solvent.resolve_solvent_line()`. With `solvent_policy.model = null`,
that resolver refuses, the smoke gate stops each payload before any real work, and P1 / P1b / P5 /
endpoint_prep all return **0 core-h**. 🟢 That is the correct state to be blocked in — loud, not silent.
🟢 And `coder9` declined to write the `scrf=(pcm,read)` deck from memory. **That refusal is the right
call** and is exactly what ADR-105 exists to produce.

But the scope underneath is contradictory, and it is not the lead's to resolve:
```
ADR-104 (USER RULING)   PCM ε = 18.5 from B1 onward.  **B0 stays SMD.**
C-5 (standing)          SMD generic needs 7 EC:EMC descriptors nobody has, and volume-fraction
                        weighting of SMD descriptors is UNVALIDATED (SMD was fit on pure solvents).
⟹                       If B0 stays SMD, B0 can never be submitted. ADR-104 dissolved C-5 for B1 only.
```
The pilot is a **cost** probe, and ADR-106 already states cost is insensitive to which continuum model —
which would make PCM ε 18.5 usable for B0 without touching any chemical claim. 🔒 **The lead is NOT
ruling that.** ADR-104 is a user ruling with the user's own reasoning attached; overturning its B0 half is
the user's call, and the lead's job here is to present it, not to route around it. Held as an open question
with the refusal left in place.
⚠ When it is answered: the deck format gets proven by **one route smoke job**, never by a full
resubmission. A fabricated deck costs a 3.5-day round trip to discover.

### 🔒 R-13 — a test may not read the user's results tree
`test_route_truncation_b1` errored 4x, and not because of anything in the patch: it reads
`cpu_machine_pilot_results/sei_probe_report.cpu.json`, and the user re-dropped that tree. Two findings:
- 🟢 **Nothing was lost.** The three 70-column strings reconstruct byte-for-byte from
  `_HISTORICAL_JOB_TYPES_PRE_B2` inside the test file itself — which is precisely what that test proves.
- 🟢 **The artifact is gone because the bug is fixed.** This round's report carries complete routes plus
  `route_echo_completeness_evidence: "reassembled 2 echoed line(s), block closed by delimiter, parentheses
  balanced"`. B-1's reassembly works; 70-column truncation is no longer produced.
**RULING**: freeze the three strings as a fixture in `tests/`, cut the live-tree read, and **write down in
the test that its evidentiary strength drops** — once both sides come from one file it no longer witnesses
what the cluster actually stored. That link died with the artifact; pretending otherwise is the mislabel
ADR-098/100 is about. Add the stronger current fact (completeness evidence) as its own assertion.
🔒 General: **fixtures live in `tests/`.** A test rooted in a mutable user-owned directory goes red for
reasons that have nothing to do with the code — which is exactly what happened.

### 🔒 R-15 — the new duplicate-run warning must key on OVERLAP, not on "a different host"
`coder9` implemented A-2 as "same logical key runs on ≥2 hosts" and flagged the consequence itself: P1's
chain links share a logical key by design, so a legitimate chain resume landing on another node fires it.
In a project with ADR-092's 67% false-positive history, a warning that cries on correct behaviour is worse
than no warning. `executions.jsonl` already carries `run` and `finish` epochs ⟹ **warn only when two
intervals actually overlap** (a `run` with no `finish` counts as overlapping — unknown end, stay
conservative). Sequential resumes stop firing; this round's three P1b hosts still do. Rename it to mean
concurrency, since that is what it will then detect.

### MINOR items registered, not fixed
- `results.queue_wait_probe`'s 64-node entry reads `"status": "still_queued"`. It was never submitted at
  all — `config/sizing.json` capped it and `state/probe_qw_capped.failed.json` records that cleanly. The
  probe's own status string is the only place that misleads. (`critic9`)
- `06_GLOSSARY.md`'s label table was missing `[USER-DOMAIN]` (since ADR-106), and now also
  `[MEASURED, FLOOR]` and `[UNRECOVERABLE FROM THIS TREE]`. 🟢 Lead added all three on 2026-08-20 — an
  absent label does not stay absent, it gets replaced by the most authoritative-looking one in reach.
- `critic9` re-verified **every** file:line citation in this ADR (18 of them). Zero errors.

### What this cost, and the one thing it bought
≥944 core-h burned on P1b for zero usable output, plus ~13 core-h of P5 thrash. Against a 21,000 core-h
guard that is survivable. 🟢 What it bought: the failure is **fully diagnosable from the returned tree**,
because §0-o.2's "ask for the RAW LOGS alongside the parsed JSON" was followed. The parsed JSON alone
reports `"duplicate_execution": false` and would have sent us looking for a chemistry problem that does
not exist. **That instruction paid for itself in one round.**


---

## ADR-108: 🟢 **USER RULINGS on the four items ADR-107 left open** — B0 moves to PCM ε 18.5, the two false markers may be renamed, the freeze lifts after review

**Date**: 2026-08-20 · **Decided by**: the user, directly · **Status**: ADOPTED

```
① B0 solvent      -> PCM ε = 18.5. The B0-stays-SMD half of ADR-104 is SUPERSEDED.
② state/P5.done.json                  -> rename permitted
③ jobs/P1b, jobs/P5 (cluster-side)    -> rename permitted
④ dist/ freeze (ADR-086)              -> lift AFTER critic9's review passes, not before
```

### ① is the half of ADR-104 that could not be executed
ADR-104 ruled *"B0는 SMD로 유지"*. C-5 then made that unexecutable: SMD generic needs 7 EC:EMC descriptors
nobody has, and volume-fraction weighting of SMD descriptors is UNVALIDATED. ⟹ B0-as-SMD had no path to
submission at all. 🔒 The B1 half of ADR-104 (PCM, ε numeric, never by solvent name) is **unchanged**; this
extends it backwards to B0. 🟢 Consistent with ADR-106's own finding that **cost is insensitive to which
continuum model** — and B0 is a cost probe, so nothing chemical rides on the switch.
⚠ Before any expensive submission, the `scrf=(pcm,read)` deck format is proven by **one route smoke job**.
`coder9` refused to write that deck from memory (ADR-105's whole purpose); a fabricated deck costs a 3.5-day
round trip to discover. **The smoke goes first, alone.**

### ②③ are renames, never deletes
The user's standing instruction for the hand-over window was *delete nothing without permission*, and it is
why the lead left two known-bad markers in place rather than clearing them. Both are now permitted **as
renames** — the artefacts stay on disk as evidence. 🔒 `cpu_machine_pilot_results/` is untouched regardless:
that is the returned evidence tree, not a working directory.

### 🔴 WHAT ACTUALLY HAS TO RE-RUN — the answer is NOT "B0 again"
The user asked directly whether B0 must be repeated. It must not, and saying so precisely matters more than
the re-run itself:
```
RE-RUN, MANDATORY      P1b   VOID (ADR-107 R-1). 4,738 core-h.
                       P5    0/14, nothing ran. 2,926 core-h.
                       endpoint_prep  never ran -- C-5 refused it. 384 core-h.
DO NOT RE-RUN          P6    κ = 1.218 stands (3 items, not an array; critic9 cleared it)
                       P1    527.822 core-h stands. Chain, not an array. ADR-106: cost is
                             model-insensitive, so the SMD-acetonitrile run's COST transfers to PCM.
                       probes  done
OPEN, USER'S CALL      P1 again -- for CHEMISTRY this time, not cost. U-56 (TS success rate) is
                       UNMEASURED and blocks every S3 number, and PCM ε 18.5 is the first setting in
                       which a TS attempt would actually count. Roughly 528 core-h to find out.
```
⟹ the next round is **P1b + P5 + endpoint_prep ≈ 8,048 core-h** against a 21,000 guard, not a full B0.


### 🔴 ADR-108 ADDENDUM — ruling ① could not be executed when it was made, and one more item shares the gate
Found by `critic9` while reviewing the patch, confirmed by the lead against the code:

**(a) `pcm_numeric` refuses unconditionally.** `solvent.py:207-217` validates `policy["epsilon"]` and then
raises regardless — the emission path was deliberately left unbuilt (ADR-105 scoped this round to wiring
only). ⟹ with all three legal values of `solvent_policy.model`, **no chemical item can emit a deck today**.
The user's ruling arrived before the code could act on it. Sequence corrected:
```
1  build the pcm_numeric emission path (scrf `read` extra-input section through sei_qc_input)
2  critic9 review        3  lift ADR-086, rebuild
4  ROUTE SMOKE ALONE     <- this is where the deck format is proven
5  P1b + P5 + endpoint_prep (+ P1 if the user wants U-56 answered)
```
🔒 Writing a candidate deck is now **allowed, and only for the smoke.** The prohibition was never "do not
write a deck" — it is "do not send an unverified deck into a production run". `coder9` is instructed to
label the candidate `[UNVERIFIED — cluster route smoke required]` **and to enforce it in code**: a
`deck_verified` flag that lets the smoke through while P1/P1b/P5/endpoint_prep stay refused. Without that
enforcement, "the user approved PCM" silently becomes "everything is open", and 8,048 core-h rides on a
deck nobody has run. That substitution is this project's most repeated failure.

**(b) P6 shares the solvent gate, and this was written nowhere.** `P6.sh` never calls `sei_qc_smoke`, but it
does call `sei_qc_input` with job type `sp`, whose template carries `{solvent}` — so the κ anchor refuses
too. `critic9` verified it by running the real config, not a mutant:
`resolve_solvent_line(load_policy(), None)` → `SolventUndecided`.
🟢 **No action, and no loss**: κ = 1.218 is settled from this round and is not being re-run (ADR-108).
🔴 Recorded because the fact was absent from every document: **if κ ever needs re-measuring** — new node
type, new G16 version — it is gated behind the same solvent decision as the chemistry items, and whoever
schedules that will not expect it.


### 🔒 ADR-108 READING RULE — check `deck_verification.json` BEFORE trusting any cost number from the next round
`deck_verified` is being set **true** with the PCM deck still unproven on real hardware. The lead is opening
that gate deliberately (a separate smoke round costs a guaranteed 3.5 days and buys only chemistry this
round does not use), and `critic9` cleared it. But the acceptance carries a reading rule that must not be
lost between rounds:
```
G16 accepts scrf=(pcm,...) and ignores only the read section  -> PCM overhead still paid -> COST VALID
G16 rejects the syntax and the job runs effectively gas-phase -> no PCM overhead -> COST UNDER-ESTIMATED
```
The second branch is `[UNVERIFIED]` — nobody has a real G16 log for this deck. **The first real log settles
which happened**, via `deck_verification.json` and the raw-context evidence field.
🔴 So: **no `r`, `r_composite`, or P5 unit cost from the next round may be quoted until that file has been
read.** A low-biased cost number is worse than a missing one, because it looks usable.

🔴 And the field itself was almost a mislabel. `criteria/g16.py:472 parse_scrf_dielectric()` matches
`eps=...` anywhere in the text, so **G16 merely echoing the input satisfies it** — the docstring said so and
the field was still called `eps_matched`. Renamed to say only what it observes, and it now carries the raw
line, its number, and surrounding context so a human can tell an input echo from G16's own SCRF block.
🔒 The label `[UNVERIFIED — cluster route smoke required]` stays attached even with the gate open:
**opening a gate and declaring a thing verified are different acts**, and only one of them has happened.

---

## ADR-109: 🟢 **USER RULING — U-56 splits into U-56a/U-56b, and U56-2 is adopted: the two new endpoint items are B0-F grounds, not a P1 revival**

- **Status**: Accepted (user ruling, 2026-08-20)
- **Date**: 2026-08-20
- **Stage**: B0-F / S3 gate
- **Resolves**: the U-56 redefinition mandate (05_STATE.md standing state after ADR-108); the
  "does U56-2 read as a P1 revival" governance question `proposer7` explicitly escalated.
- **Context**: The user permanently excluded P1 (TS full-run pilot item) — "P1은 빼고, 앞으로도
  넣지 마." That closed the only measurement path for U-56 (TS success rate), which blocks all S3
  production. `proposer7` was respawned with the redefinition as agenda item 1 and delivered
  §39.39: U-56 had fused a GATE question and a SIZING question into one scalar; the gate as
  written was arithmetically unreachable (6/6 wins still leave the 95% lower bound of p at 0.607,
  and S3 sizing consumes 1/p). It also found §39.32(g) condition 3 already dead under ADR-108
  (SMD wording vs the PCM ε 18.5 ruling) — a compliant B0-F run would have counted in neither
  direction — and re-stated it by ε with a new condition 8 (the solvent deck must be *applied*,
  not merely accepted).
- **Decision** (all three are the user's):
  1. **The U-56a/U-56b split stands.** U-56a = binary feasibility (has ONE TS search met all
     eight §39.39(b) conditions end to end). U-56b = per-attempt success fraction + cost
     distribution, measured DURING S3 wave 1. **The S3 production block hangs on U-56a only.**
  2. **U56-2 is the gate instrument** (4 single-ended attempts / 3 endpoint certifications,
     §39.39(d)). The two new endpoint-certification items (R-A product, 11 atoms; R-C reactant,
     21 atoms) are **ruled NOT a P1 revival**: they certify endpoints for the B0-F bake-off,
     which is the surviving purpose; P1's QST2 full-run framing stays dead. U56-1 ⊂ U56-2, so a
     budget cut later is a CUT, not a re-plan.
  3. **engineer7 spawn is released** for pricing §39.39(g) + §39.40(g) — the 21-atom endpoint
     certification is the only budget driver and is unpriced. Units per §R38.4 raw-KNL
     convention.
- **Lead verification recorded with the ruling** (details in 05_STATE.md §0-p): single-ended TS
  outside `P1.sh` is FEASIBLE (adapter job_types already carry ts_opt / ts_opt_from_guess / freq /
  irc_*; missing only a relaxed-scan template + a standalone Item — coder10 scope); the
  §39.26(d) role→index mapping has tested machinery but NO emitter yet (Ω and the scan coordinate
  both block on it); vendored xtb 6.7.1 `$wall` logfermi + `$metadyn` combined run VERIFIED BY
  EXECUTION on the dev box (RT-1 discipline; cluster re-check rides the next submission's smoke).
- **Consequences**: §39.40's MTD (metadynamics) adoption proceeds on its own §39.40(d)-first
  order (the free GFN2 PES scan gates the pilot); it is NOT coupled to this ruling. The next
  submission round gains the U56-2 items only after engineer7's pricing and a critic pass —
  nothing is added to the batch currently in flight.
- **Revisit trigger**: engineer7's pricing pushes the round over the user-approved ceiling
  (then cut to U56-1 per the pre-registered rule); or the B0 reply invalidates the in-flight
  reactant endpoint / deck verification that U56-1/2 both presuppose.

---

## ADR-110: 🔴🔴 **`b0_conformers.json`'s xtb cost anchor was 33× too high — ADR-107's accounting failure, recurring in a new substrate**

- **Status**: Accepted (finding + ruling, 2026-08-20)
- **Date**: 2026-08-20
- **Stage**: B0-D / MTD pricing (§39.40/§R39 series)
- **Resolves**: §39.44 (proposer7), §R39.20 (engineer7)
- **Context**: The shipped `config/b0_conformers.json` documents `_observed`: "5 ps, 11 atoms, 12
  threads, 74 s wall" for an xtb metadynamics run. Every document computing an xtb cost from this
  (`0.247 core-h`) multiplied **wall-time × threads-requested (12)** — but proposer7's direct
  re-measurement (dev box, single-thread, clean methodology) showed the same job's real cost is
  0.0074–0.0271 core-h, and that xtb's own thread scaling for this workload saturates at 4 threads
  (1T 1.00× → 2T 1.40× → 4T 2.02× → 8T 2.01×, no further gain). **The anchor charged 12 threads for
  work that could use at most ~4** — a **33× overcount**, not a measurement error in the raw wall
  time itself.
- **Decision / Finding**:
  1. 🔴 **Same failure class as ADR-107, different substrate.** There, array tasks duplicated work
     and the reported core-h was arithmetic about work that never happened as counted. Here,
     threads were requested and billed but never usable by the workload — arithmetic about
     capacity that was never spent. Both jobs completed normally and reported a "measured" core-h
     that looked entirely ordinary; neither shape is visible without checking the parallel
     efficiency, not just the wall clock.
  2. 🟢 **Every downstream xtb figure this session repriced favourably.** MTD per-ps cost was
     28–54× too high (§R39.5/.13/.18); quench-per-frame ~290× too high. `κ_xtb`'s bracket, GFN2
     N-scaling exponent (engineer7's 3.24 → retracted to 2.01, proposer7's clean re-measurement),
     and the stage-0/pilot cost functions all repriced down after correction — direction is
     uniformly favourable (real cost lower than believed), magnitude is large.
  3. 🟢 **P3's cluster-side xtb anchor (0.10038 core-h/attempt) is SEPARATELY VERIFIED CLEAN** —
     lead confirmed by direct source read: `payload/P3.sh:103,114` both pass `-P 1` (single
     thread) to xtb. This was the one open escalation from engineer7's §R39.20 (κ_xtb's bracket
     rests partly on this figure); it does not carry the same defect.
  4. 🟢 **`collect.py`'s core-h ledger is wall-clock-based, not CPU-time-based** — lead confirmed
     by direct source read: `sei_pilot/units.py:79` (`core_hours = n_cores × wall_hours`) via
     `sei_pilot/criteria/cost.py::breakdown_core_hours`. proposer7's separate finding (xtb's
     `/usr/bin/time` USER time reads ~3.8× wall at 4 threads, an OpenMP busy-wait artefact) does
     **NOT** additionally inflate the pipeline's own accounting — the ledger never reads CPU time.
  5. 🔴 **But the mechanism behind (4) is exactly what created the bad anchor, and it is now a live
     guard-refusal risk, not a historical curiosity.** `total_cores` in a stage record reflects the
     JOB's ALLOCATED cores (whatever `cores_per_task` resolves to), not xtb's internal `-P` thread
     count. Any future xtb Item using the whole-node convention (`cores_per_task=None`) will bill
     core-h — and inflate its §R26.3 physical CEILING — by the ratio of allocated cores to actual
     xtb threads: a 64-core allocation for a 4-thread job inflates the ceiling by ~16×, and at
     `min_wall_h` floors the effect compounds further (engineer7 computed ~1,000× ceiling
     inflation for a representative case) — **large enough that the guard could refuse an
     otherwise-affordable package over cores nobody used.**
- **Ruling**: `cores_per_task` MUST be set EXPLICITLY (small integer, matching the xtb `-P`/thread
  count actually used) for every xtb-based Item — `cores_per_task=None` (whole-node) is FORBIDDEN
  for xtb Items. Sent to coder11 as an implementation requirement ahead of stage 0 / P-U2′ / any
  MTD cluster Item being built. `≤4 cores, knee at 2` is proposer7's own characterisation and
  remains a **numbered hypothesis, not yet a rule** — dev-box thread scaling may not transfer to
  KNL (weaker cores could scale differently); stage 0 re-measures it on the cluster before it is
  treated as settled.
- **Consequences**: No DFT figure moves (all G16-anchored, independent of xtb). §R39.15/.18/.19's
  MTD and stage-0 economics are superseded by §R39.20's repriced versions (SUPERSEDED table,
  `03_COMPUTE_PLAN.md:247`). Nothing in the batch currently in flight is affected.
- **Revisit trigger**: stage 0's cluster-side re-measurement of xtb thread scaling, if it disagrees
  with the dev-box result; or discovery of a second config-shipped anchor built the same way.

---

## ADR-111: 🔴🔴 **C-2 passed an IRC that connected the TS to nothing — and P1's own IRC cost was confirmed a floor by the same reading**

- **Status**: Accepted (proposer7's self-correction of their own constraint, 2026-08-20)
- **Date**: 2026-08-20
- **Stage**: S3 / U-56a gate (§39.32(g) condition 7)
- **Resolves**: §39.53 (proposer7); confirms §R39.29/.30's engineer7 escalation independently
- **Context**: proposer7 re-read P1's raw IRC logs (no computation, files already in the tree) and
  found two things at once, reached by two independent routes converging on the same unmeasured
  factor — engineer7 from cost accounting (§R39.29), proposer7 from the logs themselves.
- **Finding 1 — the constraint defect**: C-2 requires (i) both IRC directions terminate normally,
  (ii) ≥5 points, (iii) |ΔE| > 0.05 eV. P1's actual run satisfies all three LITERALLY — 31 points
  each direction, `"Maximum number of steps reached."` (a normal Gaussian link exit, not an error),
  ΔE = 0.143/0.147 eV — **while the energy was still descending at a CONSTANT, non-decreasing rate
  at the final point in both directions** (no plateau near a stationary point). C-2 exists to
  certify "the IRC connects the TS to two distinct minima"; as worded, it is satisfied even when
  the IRC connects the TS to nowhere in particular, because the path ran out of its point budget
  mid-descent. Same SCOPE-defect shape named repeatedly this round (a guard that exists, is
  reached, and is individually correct on each literal clause, yet does not cover what its name
  claims). **Load-bearing**: C-2's pass/fail feeds directly into proposer7's own §39.32(g)
  condition 7 for U-56a — a truncated IRC could have certified U-56 success.
- **Finding 2 — P1's IRC cost is confirmed [MEASURED, FLOOR]**: the same log reading that exposed
  the C-2 gap also settles engineer7's open escalation from §R39.29 (lead had independently
  confirmed truncation from the same logs, message crossing recorded there). A path still
  descending at a constant rate at cutoff rules out `t=1` (converged as measured); proposer7
  reads it as `t≈2` being close to central rather than pessimistic, explicitly declining to name
  a number between 1 and 4 (naive linear extrapolation implies ~4× but IRC accelerates past the
  saddle shoulder, so linear extrapolation overstates it). **Two people, two independent methods
  (cost accounting vs raw log reading), converging on the same unmeasured factor — the strongest
  evidence available that the factor is real.**
- **Decision (fix, proposer7's own constraint, sent to coder11 for implementation)**:
  ```
  C-2.1  emit the IRC's termination reason as data (Gaussian already prints it verbatim)
  C-2.2  IF terminated by max-points (not convergence) THEN verdict = `indeterminate`, NEVER `pass`
         (vocabulary already reserved; `fail` already forbidden for this class)
  §39.32(g) condition 7 AMENDED: "C-2 passes AND both directions terminated by convergence,
         not by max-points"
  ```
  Honest cost, stated by proposer7 rather than hidden: under the corrected rule, **the one IRC run
  this project has now returns `indeterminate`, not `pass`** — and every future TS attempt must
  budget for an IRC that actually completes, not one sized to the old (unexamined) constant.
- **Deferred, deliberately**: making `maxpoints` a per-reaction derived value (proposer7's own
  free-predictor idea — a soft imaginary mode, |ν_imag|, already measured by the preceding freq
  stage, should predict how many points a full IRC needs) is NOT adopted yet. No exponent is
  known; calibrate from the first two IRCs that actually complete, don't assert now.
- **Explicitly NOT checked, stated as an artefact limit rather than an oversight**: whether the
  truncated IRC's final points were even heading toward the intended products. Unanswerable from
  this run specifically — it is the acetonitrile-contaminated, VOID round (ADR-105) — "haven't
  looked" and "this file can't say" are different claims, and proposer7 kept them distinct.
- **Consequences**: no DFT figure in §R39 moves on Finding 1 (a gate-wording fix, not a cost
  change). Finding 2 sharpens §R39.29's still-open re-audit (does U56-2's new IRC share the same
  `maxpoints=30` truncation risk) from "suspected" to "confirmed present in the only IRC data this
  project has."
- **Revisit trigger**: the first two IRC jobs that terminate by convergence rather than max-points
  — they calibrate both `t` (the cost floor's true multiplier) and the |ν_imag|→points-needed
  relationship in one measurement each.

### 🔴 ADDENDUM to ADR-111, same day — the fix ruling (§39.55), and a self-correction to the fix

proposer7's own §39.53 wording for condition 7 ("both directions terminated by convergence") would
have PERMANENTLY blocked any cheap fix from ever closing U-56a, forcing every gate attempt onto the
expensive converged-IRC path (engineer7's costed Option A) — not the intent, corrected same day.

**Ruling: plain cheap fix (a single terminal optimisation per direction, engineer7's "Option B")
is REJECTED as insufficient — accepted only as "B+".** Plain B's failure mode is silent and wrong:
near a bifurcation, a terminal opt from the truncated endpoint can land in the wrong basin, still
terminate normally, and produce a structure — exactly this round's recurring "quietly wrong, not
loudly failing" defect shape.

**B+**: run the terminal optimisation from TWO different points on the truncated path (the last
point, and roughly the 20th of 30) per direction. Both starting points sit on the same descending
branch by construction — if the local basin is well-defined, they MUST converge to the same
minimum; if they diverge, that is bifurcation, not noise, no threshold needed. Cost ≈12% of a
21-atom attempt (vs Option A's +50–200%).

**Calibration, third hierarchical-overlap design this round** (same shape as the SP ladder): R-A
(the actual U-56a gate case, 11 atoms, cheapest) ALSO gets a real converged IRC (Option A) in the
same run, so B+ is checked against ground truth on the one reaction where both exist.

**Final `§39.32(g)` condition 7**: IRC connection must be ESTABLISHED via (a) both directions
converge, OR (b) max-points termination + B+ agreement between the two sampled points — AND, under
either, the reverse endpoint matches the certified reactant within RMSD tolerance. (b) is not a
relaxation of (a); it trades convergence for an additional measurement (a) never required. `C-2.2`
reads: max-points termination AND (B+ disagreement OR B+ not run) ⟹ `indeterminate`.

**What this preserves**: T21-se stays ~6,371 (+12%, not +50–200%), so the Δ_shell matched pair
(ADR-109's S3-strategy item) stays submittable. Under Option A applied uniformly, a t≈5 truncation
factor would make a single 21-atom attempt unsubmittable alone, pulling engineer7's "n=3 not
submittable" limit down to n=2 and taking the matched pair with it.

**Risk accepted, not hidden**: B+ only detects bifurcation BETWEEN its two sampled points — a
branch splitting PAST the last IRC point is invisible to it (both terminal opts could agree on the
same wrong basin). Only R-A's calibration bounds this, and only for that one reaction. A known
sequencing exposure follows from this: if R-A's converged IRC is later found to disagree with its
own B+ result, B+ is falsified retroactively and every non-gate attempt already submitted that
round returns `indeterminate` in hindsight — discovered AFTER submission, not before. The
alternative was accepting non-submittability instead; this exposure was chosen deliberately and is
recorded here so it is not rediscovered as a surprise.

---

## ADR-112: 🔴🔴🔴 **P1's "TS" is not the reaction's saddle — it is Li⁺ hopping on an already-open-ring surface. Every IRC-cost figure anchored on it measures the wrong job.**

- **Status**: Accepted (proposer7's finding, 2026-08-20)
- **Date**: 2026-08-20
- **Stage**: S3 (invalidates the sole existing "production" TS data point; reorders the IRC-gate work)
- **Resolves**: §39.56; supersedes the IRC-cost reasoning in §R39.29–.32 wherever it treats P1's
  saddle as a reaction saddle
- **Context**: Following ADR-111's IRC-truncation finding, proposer7 read P1's own freq output
  (no computation — data already in the tree) to check whether the imaginary mode itself was
  trustworthy, since engineer7 had flagged P1's TS mode (−48.4 cm⁻¹) as unusually soft for a C–O
  cleavage TS (typical 200–800 cm⁻¹).
- **Measurement**:
  ```
  imaginary mode        −48.4416 cm⁻¹      reduced mass 7.1479 amu (≈ Li's atomic weight 6.94)
  per-atom displacement  Li = 0.792 — 2.6× the next-largest; every other atom ≤ 0.31
                          mode norm 0.9962 ⟹ Li ALONE carries 63% of the squared mode amplitude
  Ω (overlap with the intended bond coordinate, §39.4(c)):
      O2–C3 (the intended alkyl C–O cleavage)   0.022   — essentially zero
      O2–C1 (R-B channel, carbonyl)             0.008
      O5–C4                                     0.002
  d(O2–C3) = 3.184 Å — THE ALKYL C–O BOND IS ALREADY BROKEN AT THIS "TS". The ring is already open.
  ```
- **Finding**: this saddle does not sit between the closed and open ring — it sits ON the already-
  open product surface, and its imaginary mode is Li⁺ hopping between two coordination sites, not
  the ring-opening coordinate at all. **This single explanation replaces three separate mysteries
  from ADR-111 with one cause**: the soft mode, the IRC going nowhere in 30 points, and both
  directions descending slowly and near-symmetrically are all symptoms of a shallow cation-hopping
  saddle with no real energy range to traverse — not three independent problems.
- **Consequences, reversing the direction of ADR-111's IRC-cost reasoning**:
  1. **Do not increase IRC budget for this class of saddle** — spending more only walks further
     down the wrong path. Confirms engineer7's own stated worry (§R39.31 item 3) was correct.
  2. **engineer7's anchor is worse than "two errors of opposite sign, net undetermined"** (their
     own §R39.32 §3 self-diagnosis) — **there is no net to compute.** The anchor is a 30-point IRC
     of lithium hopping on the product surface, unrelated in EITHER direction to the true ring-
     opening IRC cost. The truncation multiplier `t` is not merely unbounded — it is **unmeasured
     by this data point, full stop.** `260.000 core-h` remains an accurate measurement — of the
     wrong job.
  3. **proposer7's own `1/|ν_imag|`-based `maxpoints` predictor (registered one section earlier in
     ADR-111) loses its only anchor and is self-withdrawn.** −48.4 cm⁻¹ is a spectator-mode
     measurement; it calibrates nothing until a genuinely correct TS is available.
  4. **Ordering fix**: ADR-111's addendum (B+) remains valid AS A GATE MECHANISM, but must run
     AFTER Ω is checked, not before — a terminal optimisation on a path that isn't the reaction
     coordinate establishes nothing. **Ω → IRC → B+.**
- **The free gate variable changes from `|ν_imag|` to `Ω`**: engineer7 had proposed skipping IRC
  spend when the imaginary mode is too soft to complete within budget. Soft mode + HIGH Ω is a
  genuinely floppy TS worth walking; soft mode + Ω≈0 is a WRONG SADDLE. `|ν_imag|` alone cannot
  distinguish these; `Ω` can, and `Ω` is already defined (§39.4(c)). **U-57 (Ω threshold
  calibration) is not needed for this case** — U-57 exists to adjudicate ambiguous/borderline
  cases, and Ω=0.022 with 63% spectator-cation mode character and a bond already at 3.18 Å is
  unambiguous under any reasonable threshold. Ω should always be EMITTED (data, not verdict — the
  C-3 pattern already used elsewhere); U-57 only judges genuinely marginal cases.
- **🔴 URGENT implementation gap, sent to coder11 as a priority reorder**: NO production path
  currently computes Ω at all — §39.26(d)'s role→index mapping machinery exists but has ZERO
  callers (already found during ADR-109's verification). If U56-2's attempts run before this is
  wired, they can produce saddles with no Ω check — the exact condition that let P1's failure go
  undetected for two rounds. **Ω emission moved ahead of the C-2/condition-7 work in coder11's
  queue** — C-2 exists to examine a path Ω has already judged worth walking, not to substitute for
  that judgment.
- **What this finding does NOT say** (proposer7's own scope discipline, kept explicit):
  - **Not a QST2 refutation** — §39.32(f) already withdrew "P1 is evidence against QST2." The
    endpoint was an uncertified planar guess; C-8 exists precisely to prevent this and was not
    enforced for P1 historically.
  - **Does not touch cost arithmetic** — 527.822 core-h remains an accurate measurement, of the
    wrong job.
  - **Unrelated to the acetonitrile contamination** (ADR-105) — the spectator mode and the 3.18 Å
    bond length are not artefacts of the wrong dielectric.
- **Revisit trigger**: the first genuinely-Ω-gated TS attempt that reaches a real ring-opening
  saddle — it is the first data point that can re-anchor the `|ν_imag|`→`maxpoints` relationship
  and give `t` an actual measurement.

---

## ADR-113: 🔴🔴🔴 **The submission harness silently skipped a resubmit round — "done" means only "the wrapper exited," not "this config was ever run" — the two-clause fix and why one clause alone is not enough**

**Date**: 2026-08-21 · **Decided by**: lead, on proposer8's escalation (§39.80, `02_METHOD_SPEC.md`) · **Status**: ADOPTED

### Context
The EpsInf bracket round (§39.73) was submitted to answer one question: does supplying `EpsInf`
remove the L1110 segfault regardless of value (plumbing defect, proposer7's prediction) or only at
a specific value (real physical dependency)? The round returned. Only ONE new arm actually ran
(`endpoint_prep_reactant_epsinf_full`, EpsInf=18.5, converged). The base arm
(`endpoint_prep_reactant`, meant to run at EpsInf=1.0) never ran at all — proposer8 confirmed this
decisively: its rendered `.gjf` deck has no `EpsInf` line whatsoever, not even the wrong value, and
its `.qsub` file has no `SEI_QC_EPSINF` export. Its logged crash is the PRE-FIX crash from the
previous day, re-served as if it were this round's answer.

**Scope, worse than the base item alone**: this round's submission actually only touched three
things — the new `endpoint_prep_reactant_epsinf_full` key, `P1` (retried, failed again for its own
unrelated reason, rc=6), and `P6_t1/t16/t64` (retried, now done). Every item carrying a done marker
from the previous day — `endpoint_prep_reactant`, all 20 `P5` tasks, all 4 `P1b` tasks, the probes
— was silently skipped. Yesterday's stated recovery ("one EpsInf fix, four items recovered:
endpoint cert, P5's 20, P1b's 8, r_composite") had not started.

**A second, independent defect compounds it**: `results/plan.json`'s `extra_env` is `{}` for `P5`,
`P1b`, and `P6_t*` — only the two `endpoint_prep_*` items ever carried `SEI_QC_EPSINF` at all. Even
a correctly-forced re-run of P5 today would reproduce all 17 of its sentinel crashes, because the
payload wiring for EpsInf was only ever added to `endpoint_prep.sh`, never to `P5.sh`/`P1b.sh`.

### Root cause, two separate clauses
```
(i)  the done marker is written from the WRAPPER's exit code, not from parsed content.
     A segfaulted job writes `done`: the base endpoint item's marker says rc=0 while its own
     terminal_status.json says not_converged; P5's 20 markers all say rc=0 while all 20 stage
     records say rc=1. §39.69(d) already ruled rc is not evidence of success for a VERDICT —
     this is the same defect one layer up, in the SUBMISSION-TRACKING layer.
(ii) is_done(key) (state.py:92, before this ADR) was a pure marker-PRESENCE check —
     os.path.exists("state/<key>.done.json") and nothing else. Nothing compared the marker
     against the CURRENT plan entry. Changing an item's config (adding SEI_QC_EPSINF) had no
     way to invalidate an old marker; only a manual --rerun KEY could, and nobody knew to
     invoke it because nothing said the spec had changed.
```
**Both clauses are required.** Clause (ii) alone (a configuration fingerprint check) is necessary
but not sufficient: if a SAME-config resubmission crashes again, its marker would still say `done`
(clause (i)'s bug), and a future submission with the identical (still-crashing) config would then
correctly-but-uselessly match on the fingerprint and skip a job that has never actually produced
anything but a crash. Clause (i) alone is not sufficient either — even a content-correct marker
still needs SOMETHING to notice when the plan's config has changed underneath an old, valid marker.
The two failure modes are independent and compose into a silent, absorbing loss: a crashed
computation gets marked done, and every future round then declines to re-run it, forever, until a
human happens to notice by hand.

**Precedent that should have generalized and did not**: `payload/common.sh::sei_stage` already
checks a `pkg_fingerprint` on internal STAGE checkpoints within one job. The equivalent check
never existed at the ITEM level, across submission rounds.

### Decision — the two-clause fix
```
CLAUSE (ii), LANDED (coder12, this round):
  state.py::spec_digest(entry) — sha256[:16] over computation-defining plan fields
    (key, payload, extra_env, nodes, array, chain_links, cores_per_node, gpus).
    Deliberately EXCLUDES account/partition/pkg-root, which change WHERE an item runs,
    not WHAT it computes.
  Store.done_spec_status(key, digest) -> match | stale | unknown
  submit_entry writes spec_digest into the submitted marker.
  At submit time:
    match   -> skip (correct, unchanged behaviour)
    stale   -> reset_item (markers moved to .reset.<epoch>, NEVER deleted) + loud print
               + AUTO-RESUBMIT
    unknown -> (every marker on disk as of this ADR, since none pre-date the digest field)
               still SKIPPED, with a printed warning to use --rerun KEY manually.
               Deliberately NOT auto-rerun: the existing workdir's P1b/P5/P6/probe markers
               all pre-date digests, and auto-rerunning all of them on this rule alone would
               burn thousands of core-h nobody asked for today.
  tests/test_done_spec_digest.py (4 tests).

CLAUSE (i), RULED 2026-08-21, routed to coder12 to implement:
  The done marker itself must be written from PARSED CONTENT (the same success signal
  terminal_status.json already computes correctly), not from the wrapper's exit code.
  Until this lands, a same-digest resubmission of a still-broken item will mark itself
  done again and be silently skipped by clause (ii)'s own correct-fingerprint logic —
  clause (ii) closes the "config changed" hole, not the "config didn't change but it
  still failed" hole.
  RETRY-POLICY RULING (coder12 identified a real trap, resolved by reusing existing
  infrastructure rather than inventing a parallel one): payloads deliberately `exit 0`
  on a chemistry `not_converged` result (failure-as-data, §39.69(d)) — a naive
  "write failed whenever terminal_status != converged" rule would auto-resubmit every
  legitimate negative chemistry result every round, burning core-h for zero new
  information. RULED: the done marker's `outcome` field carries the SAME cause_class
  taxonomy already established (§39.69/§39.77): chemical | budget | protocol | engine |
  unknown. Auto-resubmit ONLY on the PLUMBING-shaped classes (protocol, engine, unknown
  — nothing chemically informative happened); NEVER on chemical or budget outcomes (a
  real completed answer, negative or not).

CLAUSE (ii) SCOPE CLARIFIED 2026-08-21 (coder12 pushback, correct, ADR's original text
was ambiguous about which fingerprint feeds which check):
  `pkg_fingerprint` stays OUT of `spec_digest` (the auto-resubmit-triggering digest) —
  including it would force-rerun every done item on ANY package edit, thousands of
  core-h per rebuild, and `sei_stage` already does the equivalent invalidation at the
  stage level inside one job; item-level digest does not need to duplicate that.
  `pkg_fingerprint` IS still recorded in the marker, but only as raw material for the
  MANUAL, analysis-side confounded-bracket check (§39.80(h)) — never as an auto-trigger.
```

### The policy sub-question, deliberately left open here
`stale -> auto-resubmit` (rather than `stale -> block, demand --rerun`) is coder12's engineering
choice, reasoned as: the item's core-h is already reserved and printed by preflight, so an
auto-resubmit is not a surprise spend, and the opposite failure (silent skip) is exactly what this
round already cost. Not overridden here — routed to engineer9 for a cost-exposure read before being
treated as settled project-wide, since it is a real behaviour change with real cost consequences
beyond this one item.

### A naming worth keeping — proposer8's diagnosis of WHY this was hard to catch
**"DESIGNED-BUT-NOT-RUN, REPORTED AS PLANNED."** The returned report does not say the low arm
failed — it says nothing distinguishing at all: `plan.json` carries `"status": "planned"`,
`"skip_reason": null`, and the top-level rollup's `n_skipped = 0`. There is no field anywhere in
the returned artefacts whose value differs between "this ran and produced X" and "this was silently
skipped and X is stale from before." Mechanical, zero-cost prevention (§39.80(h)): before comparing
any multi-arm experiment, assert (a) each arm's done-marker epoch is later than the round's own
submit epoch, AND (b) the arm's own rendered input deck actually contains the value that defines
the arm. (b) is the strong assertion — a timestamp can be argued about; an input file that does not
contain the independent variable cannot.

### Consequences
- The EpsInf bracket remains genuinely UNTESTED (not confirmed, not refuted) as of this ADR — one
  converged data point (EpsInf=18.5: n_imag=0, E=−349.620897959 Hartree, G=−349.578085 Hartree,
  lowest three real frequencies 77.0220/106.9681/151.7485 cm⁻¹, recorded as the pre-registered
  comparison reference in §39.80(c)) is consistent with invariance, with strong dependence, and
  with everything between. Do not read either conclusion from it.
- Re-run spec: fresh-key (`endpoint_prep_reactant_epsinf_unity`, never the base key, never
  `--force`) stands. 🔴 **SUPERSEDED same day (§39.81, proposer8, withdrawing their own clause
  before it shipped): "both arms full re-run, 130 core-h" (design A) replaced by design (C) — both
  arms FREQ-ONLY from the stored `endpoint_tight.chk` checkpoint, ~5-10 core-h.** Not a cost
  compromise: the fixed-geometry design has a ~4-orders-of-magnitude tighter noise floor (SCF
  convergence, ~1e-8 Ha) than the full-reopt design (optimizer instability, measured 5.6 meV —
  LARGER than the effect being bounded, meaning design A could only ever have returned "not
  resolved," misread as "invariant"). Justified by C-8.2/C-8.3 certifying a geometry, not a
  trajectory, and by line-numbered confirmation that EpsInf is read only at Hessian construction
  (never during Berny optimization cycles) — so a stationary point at one EpsInf value is
  stationary at any value, energy/gradient being EpsInf-blind. Self-contained falsifier: compare
  the two arms' printed force matrices; identical ⟹ residual (EpsInf changing the optimizer's PATH,
  which the fixed-geometry design can't see) closed by measurement; not identical ⟹ premise wrong,
  fall back to design (A), pay the 130 core-h — the fallback is named in advance, not improvised.
  Also removes the `pkg_fingerprint` confound by construction (both arms same package/round/
  checkpoint) rather than needing the double-run-both-arms mitigation design (A) required.
- **Digest bug found same day (critic11)**: `SPEC_DIGEST_FIELDS` (clause ii's fingerprint) included
  `cores_per_node`, a LIVE cluster probe result for whole-node items, not static config — a shift
  in the cluster's visible node configuration between rounds could spuriously mark a genuinely
  completed item `stale` and auto-resubmit it for no computational reason. Wasted core-h, not wrong
  results. Routed to coder12 to exclude or condition it.
- P5/P1b's missing `SEI_QC_EPSINF` wiring must land (routed to coder12) before ANY recovery round
  for those items is submitted — otherwise the exact same silent-failure shape recurs one level
  down: a "fixed" round that reproduces the identical crash because the fix was never wired to the
  item that needed it.

### Revisit trigger
Clause (i) landing (done markers content-derived) and the P5/P1b EpsInf wiring landing are both
prerequisites — not just recommendations — for submitting any P5/P1b recovery round. Do not submit
one without both confirmed in source, since a repeat of this exact incident is now falsifiable at
zero cost per proposer8's own check (grep the rendered deck for the arm's defining value before
submitting).

### Addendum, 2026-08-21: engineer9's cost-safety read of clause (ii)'s `spec_digest`
Traced to source, not description. `stale → auto-resubmit` is SAFE on cost grounds — an item's
core-h ceiling is reserved by `guard.reserve()` unconditionally in `plan.py::build_plan()`, which
never consults marker state, BEFORE `store.is_done()` is even checked (only inside `cmd_submit`'s
loop) — an auto-resubmit structurally cannot push a round past a guard that round already passed.
Three exposures found, one serious:
- **A** (same root as the `cores_per_node` bug above, sharpened): latent this round (every marker
  predates the digest, stays `unknown`/skip-only), but ARMS next round — a node-detection value
  differing on a resume flips EVERY item's digest at once, auto-resubmitting the entire workdir
  (~1,700 core-h on this workdir, plus a full round's calendar, no prompt). Fix: exclude
  `cores_per_node`, or cap the blast radius (refuse auto-resubmit past N items stale in one pass).
- **B, the serious one — a FALSE NEGATIVE, live today, not latent.** `SEI_QC_LEVEL` (`--level
  g1|g2`) lives in `common_env` (`cli.py:697`), not in `entry["extra_env"]`, not in
  `SPEC_DIGEST_FIELDS`. `./run.sh --level g2` against a g1-done workdir returns `match` on every
  item and silently assembles a report claiming g2 results that are actually g1 — same hole covers
  `SEI_QC_MODULE`/`SEI_QC_LOGIN_PATH`. This SAVES core-h while CORRUPTING THE ANSWER — the mirror
  image of everything else this ADR is about, on the most computation-defining knob in the
  package. Routed urgent to coder12 (fold `common_env` into the digest, or move `SEI_QC_LEVEL`
  into per-item `extra_env`) and to critic11 for a dedicated check.
- **C**: `chain_links` flips the digest only when a wall-cap change happens to alter the rounded
  link count — non-monotone coverage, contradicts the digest's own WHERE/HOW exclusion principle.
  Minor, not blocking.
- **Evidence preservation**: `reset_item` protects markers and stage checkpoints but not the job
  directory itself, which gets overwritten on resubmit — the exact mechanism that destroyed P1's
  IRC logs. Fix: rename `jobs/<key>` before auto-resubmit too, same pattern as the markers.

---

## ADR-114: Internal CPU wall-time cap raised 24 h → 48 h — supersedes ADR-004 item 2, standing user ruling

- **Status**: Accepted
- **Date**: 2026-08-21
- **Stage**: Infra
- **Resolves**: `sei_pilot/budget.py`'s `DEFAULT_MAX_WALL_H` and its ADR-004 citation, which had gone
  stale relative to a fact the codebase already knew in a different place.
- **Context**: ADR-004 (2026-08-17, before any real cluster access) set "A2 = wall-time 상한 24 h"
  as **engineer's assumption**, confirmed only in the sense of "the assumption engineer made going
  in was accurate," not a site measurement. ADR-052 (later, direct user confirmation on the real
  cluster) established the `normal` queue's real wall is 48 h, and `plan.py`'s
  `EXPECTED_QUEUE_WALL_H = 48.0` was already updated to match. `budget.py`'s `DEFAULT_MAX_WALL_H`
  was not — it stayed at 24.0, still citing ADR-004. **User ruling, direct, standing**: the cluster
  wall-time limit is 48 h, not 24 h, from now on. Not open for debate.
- **What this actually touches, traced by coder13, not guessed**:
  1. `PROFILE_GUARDS["cpu"]["max_wall_h"]` (`budget.py:42`) was **already 48.0** — the live CPU
     guard path (`guard_for_profile("cpu")`, what every `cli.py` entry point actually calls) has
     been correct since §R24.1's KNL re-pricing. This ADR does not change CPU planning behavior
     through that path.
  2. `DEFAULT_MAX_WALL_H = 24.0` (`budget.py:24`) is the `ResourceGuard.__init__` constructor
     default, reached only when `ResourceGuard()`/`build_plan(guard=None)` is called WITHOUT an
     explicit profile guard. `cli.py`'s three `build_plan()` call sites always pass an explicit
     `guard_for_profile(...)`, so this default is not live in the shipped submit/preflight/collect
     paths today — but it is a real, reachable public default (`plan.py:1287`:
     `guard = guard or budget_mod.ResourceGuard()`) that a future caller could hit silently. Bumped
     to 48.0 for the same reason a stale default is never left "because nothing calls it today."
  3. `PROFILE_GUARDS["gpu"]["max_wall_h"] = 24.0` (`budget.py:43`) is **NOT touched**. The GPU
     profile targets a physically separate machine (no PBS/Slurm queue, no `qstat -Qf` wall
     measurement anywhere in its path) — nothing in its history ties its 24 h to "the cluster"
     ADR-004/this ruling are about; it has never cited ADR-004. Flagged to lead as ambiguous per
     their instruction rather than silently bumped; no ruling received to change it, so it stays.
  4. `U56_ENDPOINT_21ATOM_WALL_H = 24.0` (`plan.py:191`) is **NOT touched** — a separate, deliberate
     engineer7-priced cost cap (§R39, `[ADOPTED]`), coincidentally also 24 h, unrelated to the
     cluster's queue wall.
  5. Several comments in `plan.py`/`cli.py` narrate a **past incident** involving a 24 h queue
     scenario (the `long`-vs-`normal` queue mismatch bug that motivated pinning "gate reads the
     queue == submission goes to that queue," §R24.2(1), predating ADR-052). Left as historical
     record, not live values — same convention as other past-incident narration elsewhere in this
     file; only `STALE_LITERALS`-style *current-fact* reintroduction is forbidden, not history.
- **Decision**: `DEFAULT_MAX_WALL_H` (`budget.py:24`) raised 24.0 → 48.0, comment updated to cite
  this ADR instead of ADR-004 alone. No other constant changed under this ADR.
- **Rationale**: ADR-004's 24 h was always a pre-access assumption; ADR-052 already measured the
  real number and one code path (`EXPECTED_QUEUE_WALL_H`) already reflected it. The user's ruling
  here is the second, direct confirmation of the same fact and closes the one place code still
  quoted the superseded assumption as if it were current.
- **Consequences**: None observed in the live CPU planning path (already 48 h there). Closes a
  latent "silently wrong if ever reached" default. Full suite re-run clean after the change
  (`tests/test_units_budget.py`, `tests/test_plan_report_e2e.py` both checked directly for any
  assertion depending on the old default — none found; the tests that pass `max_wall_h=24`
  explicitly do so as an arbitrary scenario value for wall-derivation math, unrelated to this
  default).
- **Revisit trigger**: If the GPU machine is ever put behind a real scheduler with its own queue
  wall, revisit whether its 24 h should track this ruling too — not automatic, needs its own check
  against that machine's real policy.
- **Addendum, 2026-08-21 (lead, correcting this entry against the actual landed code)**: point (4)
  above ("`U56_ENDPOINT_21ATOM_WALL_H`... NOT touched") is STALE — after this entry was first
  written, the user issued a direct follow-up ruling that 48 h applies everywhere without
  per-item review, including this constant. `plan.py:191` now reads `U56_ENDPOINT_21ATOM_WALL_H
  = 48.0`, changed on that instruction. `U56_ENDPOINT_21ATOM_CORE_H` (`plan.py:198`, 1536.0) was
  explicitly NOT changed — confirmed by direct read, still 1536.0. Net effect: inert for E21's
  actual behavior, since at 64 cores 1536 core-h is exhausted at 24 h wall regardless of the wall
  cap being 24 or 48 — the budget ceiling binds first either way. Flagged, not silently fixed:
  whether E21's core-hour ceiling should also move now that 48 h of wall room exists is a real
  cost/science question (more wall room could let a slower-converging attempt finish instead of
  getting wall-killed, but that only matters if 1536 core-h itself is also raised) — not decided
  here, revisit with proposer/engineer if E21 actually gets wall-killed under the current budget.

---

## ADR-115: 🟢 **The wavefunction-instability hypothesis for R-A's IRC crash is FALSIFIED on its own stated criterion** — the integrator hypothesis is now last-standing but has never been positively tested

- **Status**: Accepted
- **Date**: 2026-08-22
- **Stage**: S3 / U-56
- **Resolves**: §39.114(2)'s first of two competing, non-substitutable hypotheses for why
  `U56_RA_scan`'s and `U56_RA_qst2`'s IRC both die in the Bulirsch-Stoer corrector.
- **Evidence** (PBS job 23731675, `cpu_machine_pilot_results/u56_diagnostics_2026-08-21/`, read
  directly from the raw `.log` files by lead and independently re-derived by proposer):

  | probe | geometry | beta-MO coeff | termination | lowest instability eigenvalue | `<S**2>` |
  |---|---|---|---|---|---|
  | stage 1 | R-A IRC forward, arc 1.70908 (Point 4) | 33.38 | Normal | **+0.1419360** | 0.7549 |
  | stage 2 | R-A IRC forward, arc 6.83462 (Point 19/20) | 38.87 | Normal | **+0.1842609** | 0.7546 |

  Both report `The wavefunction is stable under the perturbations considered.` / `The wavefunction
  is already stable.` Eigenvalues are clearly positive, not marginal. Spin contamination is
  negligible (0.7546-0.7549 against the exact doublet value 0.7500). `EigRej = -1` at both
  geometries: no basis function was rejected at G16's linear-dependence cutoff.
- **The criterion this is judged against was pre-registered, not chosen after the fact.** Each
  deck's own `manifest.json`, built before submission, states: "NO instability (already a genuine
  local minimum in orbital space) FALSIFIES 'unstable wavefunction' and points to the IRC
  integrator/numerics instead (§39.113(e))." The result satisfies that clause at both probed
  geometries. This is the project's standing rule 6 working as intended — a self-authored spec run
  against a case it could have failed.
- **Convergent, independent support**: critic14 had already assembled counter-evidence against the
  same hypothesis from data on disk, at zero spend (§1d) — all 66 SCF cycles in the failing IRC
  converged; zero basis functions were rejected at the linear-dependence cutoff; the *certified*
  `endpoint_prep_product` carries the same warning magnitude as R-A's failing plateau, so the
  coefficient does not discriminate pass from fail; `U56_RB_scan` terminates normally with the same
  warning; and the coefficient oscillates 32-38 then plateaus rather than growing monotonically.
  Two independent lines of evidence now point the same way.
- **Residual gap, flagged rather than hidden** (proposer §39.118, re-derived from `irc_forward.log`):
  arc 6.83 (Point 20) is the last **successfully converged** point. The crash itself occurs roughly
  20 failed corrector sub-iterations later, while trying to reach Point 21, with the angle between
  gradients escalating 31° → 59° before `Maximum number of corrector steps exceded`. So stage 2
  probed the geometry immediately **upstream** of the failure, not the failure geometry itself — the
  divergent trial geometries were not probed. 🔴 **CORRECTED 2026-08-22 by critic15 (04_REVIEW_LOG.md
  25차 배치)**: this entry originally claimed those geometries "were never converged to anything that
  could be probed" and called the region "untestable by construction, not by omission." **That
  justification is false.** `irc_forward.log` lines 21790-30456 contain 20 fully-specified
  `Input orientation:` blocks (last at `:30018`), each followed by a converged `SCF Done`, with zero
  convergence failures — and `tools/build_u56_ra_stability_probe.py` already parses this log. The gap
  is **closable for ~0.7 core-h**, by omission, not by construction. The clause is struck; the ruling
  itself stands (it never depended on that clause). Whether to spend the ~0.7 core-h on a fifth probe
  at the true crash geometry is an open option, not a requirement — see `05_STATE.md` §1e. Additionally, `stable=opt` here tests only internal
  (same-reference) UHF-type instability via the `<AA,BB:AA,BB>` matrix, not external or complex
  instability — which is exactly the test proposer10's own criterion called for, so this is a scope
  note, not a shortfall against the criterion.
- **What this does NOT establish.** Falsifying one hypothesis does not confirm the other; §39.114(2)
  said so before either was run, and it still holds. The integrator/numerics hypothesis is now the
  only explanation left with positive support, but it **has never been positively tested** — stage 4
  (`irc=(restart,recorrect=never)`) never started. "Surviving by elimination" is not "confirmed",
  and this ADR must not be cited as if it were.
- **Consequence — stage 4 is promoted.** It was one of two parallel non-substitutable tests; it is
  now the single highest-priority remaining diagnostic in the round. If it succeeds, the integrator
  hypothesis is confirmed and R-A's IRC has a fix. If it crashes again under `recorrect=never`, that
  does **not** resurrect the wavefunction hypothesis (this ADR stands either way) but it does leave
  **neither** leading explanation confirmed — an unresolved anomaly sitting under the project's
  strongest TS candidate, where nobody has yet seen this IRC walk cleanly into a product basin.
  That outcome would need its own ruling, not an extension of this one.
- 🟢 **A loophole nobody had checked closes in this ruling's favour** (critic15, §25차 배치): the
  probes ran from a **fresh** guess and could therefore have converged to a different SCF solution
  than the one the IRC was actually carrying — in which case they would have certified the stability
  of a wavefunction the crash never involved. They did not. Probe and IRC energies agree to
  **2e-9 and 2.6e-8 Hartree** at the two geometries: same solution. The falsification applies to the
  wavefunction the IRC actually had, which is the only one that matters.
- **Scope limit — 11 atoms only.** Both probes are the 11-atom R-A system. Nothing here transfers to
  the 21-atom cation-radical case; see ADR-117 and proposer §39.120.
- **Revisit trigger**: stage 4's result; or any future case where an IRC in this class crashes at a
  geometry whose wavefunction *can* be converged and probed directly.
- **Reading rule attached to the MO-coefficient warning** (proposer §39.119, adopted): the recurring
  `**** Warning!!: The largest alpha/beta MO coefficient` at magnitudes 32-39 (11-atom) and 71-79
  (21-atom) reads as a **diffuse-basis representation artifact** — def2-SVPD approaching, but not
  crossing, linear dependence — not a chemistry signal. Supported by three measured facts:
  `EigRej = -1` at all three probed geometries; no `stable=opt` instability at either 11-atom point;
  ideal spin contamination. `EigKep` shrinks with system size (4.2-4.5e-5 at 173 basis functions →
  1.06e-5 at 334, the certified `rc_reactant`), consistent with the artifact reading. Stated
  falsifiers, none tested here: `EigRej` turning positive; an actual `stable=opt` instability;
  guess-dependence of the converged energy; energy kinks correlating with the coefficient.
  **This does NOT change C-8's certification criteria** — the reading is well-supported at 11 atoms
  and unproven at 21, which is precisely what ADR-117's stage 3 exists to settle.

---

## ADR-116: 🟢 **Track B items 5 and 6 RULED — `U56_RA_scan` accepted, `U56_RA_qst2` rejected, `U56_RB_scan` rejected.** Item 7 was never substantively gated on this diagnostic and stays open

- **Status**: Accepted
- **Date**: 2026-08-22
- **Stage**: S3 / U-56
- **Resolves**: the three Track B final verdicts proposer10 held pending the SCF/integrator
  diagnostic (§1d).
- **Item 5 — R-A method bake-off: ACCEPT `U56_RA_scan`, REJECT `U56_RA_qst2` outright.**
  §39.113(a)'s comparison between the two attempts was always independent of the SCF question; the
  hold existed because a wavefunction pathology, had one been found, could in principle have
  contaminated both. ADR-115 removes that worry rather than supplying new positive evidence.
  `relaxed_scan`'s candidate stands on what it already had (Ω = 0.839, B+ agreement); `qst2`'s leans
  spurious and is now formally out.
- **Item 6 — R-B candidate: REJECT.** R-B's IRC never crashed and was never a subject of this
  diagnostic at any point — the hold was procedural bundling, not a substantive dependency. Its
  three independent legs stand entirely untouched by today's data: Li-dominated imaginary mode;
  §39.116's non-distinct "minimum" (declared saddle and declared minimum differ by a maximum
  pairwise-distance change of 0.0203 Å); and §39.117's break-bond overshoot (reactant 1.4317 Å →
  saddle 4.1348 Å, already fully severed at the saddle). Three different methods, three independent
  legs, none of which this diagnostic could have moved.
- **Item 7 — G-SCAN-2 pre-relaxation protocol: STILL OPEN.** The missing input is a
  Li-coordinate/mapping-protocol ruling that none of the four diagnostic jobs could ever have
  supplied. Like item 6 it was bundled procedurally; unlike item 6 it is not resolvable on present
  data. It does not block stage 3 or stage 4 and must not be reported as pending-on-diagnostics.
- 🔴🔴🔴 **RETRACTED, 2026-08-22, same day, before any downstream action — U-56a IS NOT CLOSED.**
  This entry originally read: *"U-56a is the binary feasibility gate for starting S3 production and
  is keyed to `endpoint_prep_product`'s certification... It is not keyed to any TS candidate's fate.
  Neither stage 3 nor stage 4 gates U-56a."* **Every clause of that is wrong.** Caught by critic15
  (`04_REVIEW_LOG.md` 25차 배치) and independently re-verified by lead against the primary sources
  before this retraction was written.

  **What the sources actually say:**
  1. **ADR-109 Decision 1** (`01_DECISION_LOG.md:9047`) — the user ruling this note claimed merely to
     *clarify*: *"U-56a = binary feasibility (has ONE TS **search** met all eight §39.39(b)
     conditions end to end)."* A TS **search**, all **eight** conditions, **end to end** — not one
     endpoint certification.
  2. **§39.32(g) condition 7** (`02_METHOD_SPEC.md:11519-11525`) — the IRC verdict must pass C-2 in
     **both** directions, established by EITHER convergence OR `maxpoints` + B+ agreement, and in
     both branches the reverse endpoint must match the certified reactant. Endpoint certification is
     condition **1**, one of eight.
  3. **`05_STATE.md:520`** — *"the endpoint certification FAILED — U-56a's **prerequisite 1** is NOT
     satisfied."* The §2 phrase proposer11 leaned on (`this is what actually closes U-56a`) meant
     "the last remaining **prerequisite**", not "the whole gate". proposer11 explicitly flagged that
     it was relying on that phrasing and asked for it to be checked; the check is this entry, and the
     phrasing had been misread.
  4. **`U56_RA_scan/u56_attempt.json`** — the harness itself keys the verdict to the IRC:
     `"판정(C-2 IRC verdict, U-56a pass)은 수집/리뷰 단계가 한다"`.
  5. **Measured, read directly**: `irc_completion_forward.json` and `irc_completion_reverse.json`
     both report `normal_termination: false`, `maxpoints_reached: false`, `truncated: true`. Branch
     (a) fails (Error termination, `irc_forward.log:30457`). Branch (b)'s own precondition
     (`maxpoints` reached) is **also** false. Neither branch of condition 7 is satisfied.

  **This ADR contradicted itself in the same document**: item 5 above restates §39.113(1)'s
  `low_confidence` downgrade of R-A's **reverse** arm as unchanged, while the retracted note declared
  the gate closed on the strength of the same candidate.

  **Correct statement**: for `U56_RA_scan` — now the *sole surviving* candidate, since items 5 and 6
  above just rejected the other two attempts — condition 1 is satisfied and **condition 7 is not**.
  **U-56a is OPEN.** **Stage 4 DOES gate U-56a**, and stage 4 alone is not sufficient: the reverse
  arm additionally needs a longer or redone IRC to lift its `low_confidence` status. That second
  requirement was invisible in every project document until this retraction and is now tracked in
  `05_STATE.md` §1e and §2.

  **Direction of the error**: not core-h — a silently-passed stage gate that would have unblocked S3
  production. §39.32(g) closes with an explicit prohibition against exactly this failure, citing
  "the entire lesson of P1 — 302 core-h that count in neither direction." **Lead's own failure mode,
  recorded rather than buried**: this ruling ratified a teammate's inference without reading
  ADR-109's actual text, one turn after the same lead cited engineer12 for the "measured but not
  read" defect class. Standing rule 6 applies to the lead's rulings too, and did not get applied
  here — it took a critic round to catch it, which is the control that has now caught a
  result-changing defect in every review round this session.

  What survives from the retracted note: ADR-115 does modestly strengthen R-A's candidate by removing
  one residual doubt on the arc-6.83 geometry, and proves nothing new beyond that. The conditional
  risk stands and is still tracked, not acted on: if stage 3 returns UNSTABLE, that becomes a
  class-level question about C-8's sufficiency which could in principle reach back to R-A's own
  (lower-magnitude) certificates.

---

## ADR-117: 🔴 **PBS 23731675 was a SUBMISSION failure, not a prediction failure** — stages 3 and 4 both MUST RUN, as two separate hardened hand-submitted jobs; and the resubmit recipe's own core count is defeated by the deck unless one line changes

- **Status**: Accepted
- **Date**: 2026-08-22
- **Stage**: Infra / S3
- **Context**: PBS job 23731675 ran all four diagnostic decks sequentially inside one job requesting
  `select=1:ncpus=1:mpiprocs=1` and `walltime=02:00:00`, via an ad-hoc `submit_diagnostics.pbs` with
  no SIGTERM trap, no `wall_exhausted` marker, and no stage chaining. It was killed:
  `=>> PBS: job killed: walltime 7244 exceeded limit 7200`. Stages 1 and 2 completed (see ADR-115);
  stage 3 was killed mid-SCF at Cycle 8 of its *initial* SCF; stage 4 never started.
- **Root cause, stated without softening** (engineer §R39.79 §1): **submission failure.**
  §R39.78 — engineer11's own pricing, on record before this was submitted — priced item 3 *alone* at
  3-30 core-h, wrote "at 1 core: 3-30h wall", and explicitly recommended 4-8 cores to cut worst-case
  wall under 8h. The submitting script consulted none of it. This is the project's recurring
  "measured but not read" defect class in a new substrate, and standing rule 6 applies directly: the
  correct number existed and was not read at the moment it was load-bearing.
- **The prediction method is validated, not impugned.** Items 1+2 were priced 0.8-4.8 core-h
  combined and measured **1.242 core-h** (0.514 + 0.728, both Normal termination) — near the
  optimistic floor of a band derived from real per-stage log timings, not from the retracted S₂₁
  cube law. Item 3's 8 killed SCF cycles give a measured ~341 s/cycle, which tightens the *bare-SCF*
  sub-estimate (1.5-2.8 → 1.1-1.7 core-h) but leaves the 2-10× `stable=opt` multiplier untouched —
  8 cycles of pre-stability-test SCF carry zero signal on the multiplier, which *is* the open
  scientific question. Revised item 3: **~2.2-17 core-h [ESTIMATE]**, down from 3-30, cutting mainly
  the pessimistic tail.
- **Both stages MUST RUN** (proposer §39.120/§39.121, engineer §R39.79 §3, no disagreement between
  them):
  - **Stage 3** — stage 3 produced *no science result at all*; the SCF was converging normally when
    the clock ran out (Cycle 7 DIIS error 1.19e-4 and decreasing, Cycle 8 in progress). ADR-115's
    11-atom stable result does **not** transfer: different molecule, ~2× the MO-coefficient
    magnitude in a regime that tracks charge rather than atom count, and this target is an
    already-relied-upon *certificate* rather than an open candidate. Decision-relevance: UNSTABLE
    reopens whether C-8's `n_imag = 0` + normal-termination criteria are sufficient for the whole
    cation+open-shell class (touching T21-se completion risk and possibly other certificates);
    STABLE closes the §39.115 loophole cleanly.
    🔴 **SCOPE CAVEAT, whatever stage 3 returns** (critic15, C6-5): every job in this batch is
    `Charge = 0 Multiplicity = 2` — all five production jobs and all four diagnostic decks — and
    `endpoint_prep_rc_reactant` is a **neutral** Li(EC)₂ doublet (`li_ec2_radical_reactant`). The
    claim that MO-coefficient magnitude "tracks net charge rather than atom count", which propagated
    §39.113(c) → §R39.78 → §39.120 → this ADR, therefore rests on a dataset with **zero charge
    variance**. Stage 3 must run regardless, but its result must NOT be reported as a statement about
    "the cation+open-shell class": STABLE would be misread as clearing cation chemistry, UNSTABLE as
    indicting it, on a measurement containing no cation. Report it as what it is — a 21-atom neutral
    doublet at 334 basis functions.
  - **Stage 4** — promoted to the single highest-priority remaining diagnostic by ADR-115.
- **Two separate PBS jobs, never re-bundled.** §39.114(2) makes stage 3 and stage 4 independent,
  non-substitutable tests; a shared walltime budget means one overrunning starves the other, which
  is exactly what just happened. They may run concurrently; they need no ordering relative to each
  other.
- **Sizing** (engineer §R39.79 §3(a), deliberately sized off the *original* 3-30 core-h ceiling
  rather than the tightened 2.2-17 figure — margin is not cut against an untested extrapolation
  past cycle 8):
  - stage 3: 4 cores, `walltime=16:00:00` (worst case 30 core-h / 4 ≈ 7.5 h, >2× factor)
  - stage 4: 1 core, `walltime=30:00:00` (1.5× the pessimistic 20 core-h bound at 1 core)
  - Both comfortably inside ADR-114's 48 h cap.
- 🔴 **DEFECT IN THE RECIPE, caught by lead before submission — the 4-core sizing is inert as
  staged.** Both staged decks carry `%nprocshared=1` on line 1 (verified directly:
  `3_rc_reactant_21atom/stability_probe.gjf` and `4_irc_recorrect_restart/irc_recorrect_probe.gjf`;
  each `manifest.json` independently records `"nprocshared": 1`). In Gaussian 16 an explicit
  `%nprocshared` Link0 line **overrides** the `GAUSS_NPROCSHARED` environment default that
  §R39.79's script skeleton exports. Submitted as written, stage 3 would reserve 4 cores and run on
  1 — and the 16 h walltime, sized against a 4-core assumption, would be **under** the 1-core
  worst case of ~30 h. That is a repeat of the identical failure this ADR exists to prevent, one
  layer down. Engineer flagged the mismatch as "silent-underuse risk, not a crash risk" and routed
  the deck-edit question elsewhere; the walltime interaction makes it a repeat-kill risk, and the
  decision is lead's, not coder's, because the decks live under `cpu_machine_pilot_results/` —
  a standing read-only tree.
  **Ruling — two acceptable paths, user picks; do not submit §R39.79's skeleton unmodified:**
  1. **Preferred (4× faster turnaround)**: copy **the deck FILES** to a fresh **writable** directory
     outside `cpu_machine_pilot_results/`, set `%nprocshared=4` in stage 3's copied `.gjf`, and
     submit from there. The returned tree stays untouched, satisfying the standing restriction;
     record the copy path in `05_STATE.md` for provenance. Stage 4 stays at 1 core and needs no edit.
  2. **Zero-touch fallback**: submit stage 3 as staged at `ncpus=1` with `walltime=45:00:00`
     (inside the 48 h cap). Identical core-h — these are compute-bound single SCF jobs — at roughly
     4× the wall-clock latency. Correct, just slower.

  🔴 **THREE CORRECTIONS from critic15 (`04_REVIEW_LOG.md` 25차 배치), all landed above and all
  mechanical — the recipe was NO-GO as first written:**
  - **The `GAUSS_NPROCSHARED=4` export in §R39.79's skeleton must be DELETED, not commented out.**
    Lead's original reasoning (explicit `%nprocshared` beats the env default) reached the right
    conclusion by the wrong route. The stronger and actually binding fact: **`GAUSS_NPROCSHARED` is
    not a Gaussian 16 variable at all** (G16 uses `GAUSS_PDEF`), so the export is a no-op regardless
    of precedence. Verified from the repository, not from memory: `grep -rn "GAUSS_" src/ tools/`
    yields only `GAUSS_EXEDIR` / `GAUSS_SCRDIR`, and every production job sets cores in the deck
    (`U56_RA_scan/irc_forward.gjf:1` reads `%nprocshared=64`, matching its qsub). Left in — even
    commented — it silently hands 1 core to the next person who deletes a `%nprocshared` line
    trusting the environment to cover it.
  - **The fallback's walltime was under-margined**: 32 h against the same 30 core-h bound is a
    **1.07×** factor, where the primary path was given >2× and stage 4 1.5×. Raised to 45 h above.
  - **"Copy the deck DIRECTORIES" was wrong** and is corrected to "copy the deck FILES": copying
    stage 3's directory wholesale drags along its stale mid-write `stability_probe.chk` and ~155 MB
    of `Gau-*` scratch, reintroducing the exact truncated-checkpoint risk the clean-restart ruling
    below argues against. Copy **`.gjf` + `probe_point.xyz` + `manifest.json` only**. Stage 4's
    `.chk` is different — it is genuine *input* and must travel **byte-exact** (verified identical to
    `irc_forward.chk`, md5 `87a378633c55f4df0021f133943cfe97`). critic15 read both `.gjf` files end
    to end: self-contained, relative `%chk`, inline `gen` basis, inline PCM `read` block, no `@`
    includes — copying itself breaks nothing.

  🟢 **Independently verified OK, no action needed** (critic15): stage 3 at 16 h / 4 cores and stage 4
  at 30 h / 1 core are both safely margined (re-derived ≈1.05 core-h/point from the original IRC, so
  ≤10 points ≈ 11 core-h; even a repeat corrector crash costs the measured 13.4 core-h and fits).
  **`%mem=4GB` is adequate** — stage 3 already ran 8 cycles at 334 basis functions with `.int` and
  `.d2e` at **0 bytes**, i.e. fully direct, no disk spill. **The recipe is CLEAR of the
  `plan.py`/`spec_digest`/`cause_class`/`cli.py` stale-branch trap** — it invokes no `sei_pilot`
  entry point, so there is no path to firing `U56_RA_scan`'s 336 core-h.
- **Stay hand-submitted; do NOT move to `payload/U56.sh`** (engineer §R39.79 §4, adopted). The
  argument for the payload was real — SIGTERM trap, `wall_exhausted` marker, stage chaining, exactly
  the machinery whose absence caused this — but today's root cause was never a payload limitation.
  Fixing it needs zero contact with `plan.py`, `spec_digest`, `cause_class`, or `cli.py`'s
  stale-branch ordering, whereas wiring these in as real Items adds surface to the very mechanism
  §1d spent a round fencing off: the `extra_env`/spec_digest stale-resubmit path that runs *before*
  the `cause_class` check and could auto-fire `U56_RA_scan`'s measured 336 core-h to repeat a known
  crash. Instead the ad-hoc script is hardened: one stage per job, plus a `trap ... TERM` writing a
  kill marker. That trap is **best-effort and `[ASSUMPTION]`-flagged** — it relies on this site's
  PBS sending SIGTERM before SIGKILL with a grace window nobody has confirmed. Even best-effort it
  converts "silent kill, read the `.e` file to find out" into "a marker names which stage died and
  when," which is the specific gap this failure exposed.
- **Stage 3 restarts CLEAN, not from its checkpoint** (engineer §R39.79 §3(c)). Its
  `stability_probe.chk` is 3,940,352 bytes against 5,861,376 / 5,869,568 for the two completed
  runs — consistent with a job killed before writing post-SCF data, but **unverifiable here**: no
  G16, `formchk`, or `chkchk` binary exists on this machine, so nothing confirms which SCF cycle its
  density corresponds to or whether the SIGKILL left it mid-write (`[NEEDS VERIFICATION]`). The
  saving is ≤0.77 core-h against a full-run estimate of ~2.2-17 core-h; the downside is a
  `guess=read` that either errors out or, worse, converges silently to the wrong state. Trivial
  saving, real and unquantified risk — start clean.
- 🔴 **AN UNPRICED STAGE-4 FAILURE BRANCH, and it is a wrong-conclusion risk rather than a cost
  risk** (critic15, C6). Everyone — proposer, engineer, lead — priced only the *malformed-route*
  branch ("fails at ~zero cost, itself informative"). Nobody priced the branch where the route is
  **accepted but `recorrect=never` is silently dropped**, because `irc=restart` takes its options
  from the checkpoint rather than the deck. Stage 4 would then reproduce the identical crash, and the
  natural reading — "the integrator hypothesis is dead too" — would be **unsupported**, leaving the
  project with a false negative on its last-standing explanation. **Mandatory zero-cost check before
  interpreting stage 4's result**: grep the new log for `Recorrection delta-x convergence threshold:`
  — it prints once per corrector step in the original `irc_forward.log`. **If that line still
  appears, the option did not take effect and the run carries no information about the hypothesis.**
  This check is part of the recipe, not optional commentary.
- **Stage 4 is uncorrupted and resubmits exactly as staged.** Its
  `irc_forward_recorrect_probe.chk` was copied from `U56_RA_scan/irc_forward.chk` at deck-build time
  (`generated_at_utc 2026-08-21T11:44:37Z`), well before this submission ran, and the killed job's
  loop never `cd`'d into `4_irc_recorrect_restart/`. Note that stage 4's route
  (`irc=(restart,recorrect=never)` + `geom=check guess=read`) remains **unsmoked** — a malformed
  route fails at ~zero cost, which is itself informative, per this project's standing treatment.
  Stages 1/2 did clear the `stable=opt` half of the `route_syntax_status: NEEDS VERIFICATION` flag
  by real execution; that clearance covers stages 1/2/3's route only.
- **Scratch, flagged and NOT deleted.** Stage 3's directory holds ~155 MB of orphaned SCF scratch
  (a 157,253,632-byte `Gau-53946.rwf` plus `.d2e`/`.int`/`.skr`/`.inp`); the whole diagnostics tree
  is ~176 MB. Nothing was or may be deleted — standing restriction, and it is the user's call once a
  clean stage-3 run succeeds. Separately: this covers only the **returned** copy; the compute-node
  `$GAUSS_SCRDIR` was not and cannot be checked from here, and a walltime SIGKILL commonly orphans
  scratch there too. The user should check cluster scratch quota before resubmitting.
- **Budget**: no `deck_verification.json` exists for these ad-hoc decks — checked, and correct by
  design, since hand-submitted decks bypass the harness (ADR-108's reading rule therefore has no
  input here, stated explicitly rather than silently skipped). Consumed so far: **~2.01 core-h
  measured**. Pessimistic resubmit ceiling ~50 core-h. Guard moves 12,709.39 / 21,000 (60.5%) →
  at most ~12,761 / 21,000 (60.8%). Not meaningful.
- **Revisit trigger**: a second wall kill on either resubmitted stage; or any future decision to
  wire diagnostic decks into `plan.py` as real Items, which would need its own ADR and a fresh look
  at the stale-resubmit path.

## ADR-118: 🟢🟢 **U-56a IS CLOSED — the S3 feasibility gate's binary question answers YES.** One TS search (`U56_RA_scan`) has met all eight §39.32(g)-as-amended conditions end to end

**Date**: 2026-08-25. **Status**: accepted. **Author**: team-lead (organizer), on proposer13's
rulings (§39.131-134) and critic17's independent verification (04_REVIEW_LOG.md batches 36-42).

### Decision

**U-56a — ADR-109 Decision 1's binary feasibility question, "has ONE TS search met all eight
conditions end to end" — is answered YES and the gate is CLOSED**, on `U56_RA_scan` (R-A, the
11-atom ring-opening), at level3 (wB97XD/gen), PCM acetone eps=18.5.

The closing evidence, this round: Candidate B (`irc=(calcfc,reverse,recorrect=never,stepsize=2,
maxpoints=70)`, a from-scratch reverse IRC at f=0.20 of the nominal step) walked 70 points to arc
4.77975 (≥ the 4.27 floor) with ZERO corrector non-convergence warnings, through the exact region
that killed the original reverse IRC and the f=1.0 restart; its B+ terminal optimisations (Points
35/70) then agreed (`energy_delta_ev = 4.197e-4` ≤ 1.0e-3 eV) and the `last` endpoint matched the
certified reactant (`distance 1.3324e-4 Å` ≤ 0.05 Å on the declared break bond; `energy 2.673e-4 eV`
≤ 1.0e-3, below the ~4e-4 marginal line) — with the reactant's certified energy backfilled from its
own certification log per §39.132 (`[MEASURED, from endpoint_tight.log]`), NOT from any fixture
channel. Condition 7's reverse branch was the last open conjunct; it closes on this data (§39.133,
critic17-confirmed cold, 42차).

### Per-condition provenance (critic17's requirement: say what was re-checked, by whom, when)

| # | condition | status | provenance |
|---|---|---|---|
| 1 | certified reactant, Opt=Tight + n_imag==0 | MET | prior record (`endpoint_certs.json`), cited by §39.133, not re-derived this round |
| 2 | `nosymm` every route; point group recorded as data | MET (substantively) | `nosymm`: **exhaustive cold audit this round** (critic17 42차): 16/16 evidence-bearing routes, honoured per G16's own `C1 NOp 1` banners in all 9 evidence logs. "As DATA" half: **primary-log-verified, NOT machine-emitted** — ruled substantively met / formally incomplete / non-blocking (§39.134); wiring `parse_point_group` into the F1 emit-list is a named, non-gating coder item |
| 3 | ruled solvent applied (acetone eps=18.5, §1c switch) | MET | re-confirmed on every log this diagnostic round (ADR-108 checks), cited §39.133 |
| 4 | level3, not level2 | MET | every log this round labeled level3, cited §39.133 |
| 5 | Li unconstrained, final position recorded | MET | tracked covariate (`li_displacement_ang`), cited §39.133 |
| 6 | no cost-probe dual purpose (C-10) | MET | by original design of `U56_RA_scan`, cited §39.133 |
| 7 | IRC verdict passes C-2, both directions | **CLOSED THIS ROUND** | forward: §39.122 (prior). reverse: §39.133, **re-derived fresh** (proposer13) and **independently reproduced cold** (critic17 42차) |
| 8 | PCM eps=18.5 deck verified as APPLIED (ADR-108) | MET | confirmed on every deck this round, cited §39.133 |

Conditions 1/3/4/5/6/8 stand on already-settled project record cited (not re-derived) by §39.133;
condition 2's `nosymm` half and condition 7's reverse branch are the two independently re-derived
from cold this round. This table is the ADR-116 lesson applied: the closure states exactly what was
re-checked and what is citation.

### Scope and residual risk — stated at closure, not discovered later

- **This closes U-56a ONLY** — the binary "is this pipeline capable of producing one fully-verified
  TS" question. It does NOT measure U-56b (per-attempt success rate, an S3 wave-1 measurement), does
  NOT certify the R-A product (separate, already-tracked gap: forward walks toward an uncertified
  product; condition 7's ruled text binds the reverse endpoint to the certified reactant only), and
  does NOT close Track B item 7 (G-SCAN-2 mapping protocol, its own external-anchor plan stands).
- **"Matches the certified reactant" is the ruled sense, not geometric identity** (§39.134): the
  organic core agrees to RMS 0.006 Å while Li tilts up to 0.48 Å about a RETAINED O_carbonyl contact
  (1.861→1.854 Å; Li–O_ether non-bonded >3.3 Å throughout) — measured grounds excluding the
  coordination-isomer hazard, stronger than the energy screen alone. Do not conflate with
  `li_displacement_ang = 0.0573 Å` (mid-vs-last, different comparison).
- **Residual risk at forward's already-accepted parity, not zero** (§39.124(3) pre-commitment):
  R-1/R-2 stay open — B+ cannot see a bifurcation past its last sampled point, either direction.
- The tight-vs-loose systematic consumes 41.3% of the 1.0e-3 eV reactant-match tolerance; this
  round's value (2.673e-4 eV) is below even the systematic. Future reactant_match readings must
  report the measured `energy_delta_ev`, not the boolean (README rule, standing).

### Follow-ups (named, non-gating)

1. Wire `parse_point_group()`/`stored_point_group` into the F1 emit-list; rename or relabel the
   `heavy_atom_coplanarity_only` heuristic away from point-group-adjacent naming (§39.134's
   label-collision risk). Coder item, batch with the next real code round.
2. `make_package.sh` rebuild + hash verification — the package has diverged from `src/` across 10
   files; REQUIRED before anything ships from the package (standing since 37차).
3. R-10 (session_digest render >80 lines) still open.

**Revisit trigger**: any evidence that `U56_RA_scan`'s TS or IRC evidence chain was defective
(would reopen condition 7); a bifurcation surfacing past B+'s last sampled point (R-1/R-2 firing).

**Addendum (same day)**: proposer13's §39.135 formalizes the condition-2 reading this ADR rests on —
explicit ruling (a): the 42차 exhaustive audit DISCHARGES the "as DATA" clause for this
already-completed chain (recorded `[MEASURED, audit 42차]`), since wiring the emitter cannot reach
backward into finished jobs and the primary logs are the only source either way; emitter wiring stays
a named follow-up for FUTURE chains. §39.135 also carries the full per-condition provenance table in
paste-ready form (consistent with the table above) and corrects a transcription nit (distance
1.3324e-4 Å, per critic17's cold re-derivation — the value this ADR already uses).
