# coder → lead 인계 문서 (파일럿 인도 패키지)

---

## 🔴🔴 미래 코드에 걸린 구속 — **ADR-051. 지금 코드에 없다. 그래서 잊힌다**

> **발견 원장(discovery ledger)에 `seed_id` 와 `generation_depth` 를 기록할 것.**
> **🔴 사후 복원 불가다.** 기록 안 하면 나중에 못 되살린다 — `host` 유실과 같은 형태다.

**⚠ 이 구속의 대상 코드는 아직 존재하지 않는다.** 발견 원장은 ADR-027(원장 ↔ 작업 network
분리)의 산물이고 **본 파이프라인 S1~S4 는 착수 금지 상태**다. 즉 **"고칠 곳이 없어서" 이
구속은 지금 반영할 수 없고, 바로 그래서 원장을 처음 만드는 사람이 놓치기 쉽다.**
⟹ **원장을 만드는 순간 이 절을 먼저 읽어라.**

### 왜 필요한가
proposer 가 축 3(PM7, MOPAC 배제로 사망)을 대체하는 장치를 세웠다 — **D1: seed-split CR**.
> **"M-상대 estimand 에서 필요한 독립성은 *다른 물리*가 아니라 **다른 난수**다."**

축 2 replica 를 **독립 seed 로 A/B 이분**하면 **독립성이 가정이 아니라 설계로 보장된 두 소스**가
된다. 이미 돌린 궤적을 나누기만 하므로 **비용 0 · 왕복 0 · 패키지 변경 0**.
🔴 **그런데 `seed_id` 가 원장에 없으면 분할 자체가 불가능하다.** 궤적을 다시 돌려야 하고,
그건 비용 0 이 아니다.

### 🔒 구체 요구
| 필드 | 대상 | 🔴 주의 |
|---|---|---|
| `seed_id` | 축 2(xTB 반응성 MD 등) **난수 기반** 발견 | A/B 이분의 **유일한 키** |
| `generation_depth` | 축 1(결정론적 열거) 발견 | 축 1 은 난수가 없어 seed 가 무의미하다 |

🔴 **두 값을 하나의 컬럼으로 합치지 마라.** 성격이 다르다 — 하나는 난수 스트림 식별자,
다른 하나는 생성 깊이다. 합치면 A/B 분할이 축 1 발견을 섞어 오염시킨다.

### 🟢 이미 있는 자산 (재사용하라, 새로 만들지 마라)
`sei_pilot/seeding.py` 의 `provenance(seed, amplitude_ang, original, perturbed)` 가
**시드·RNG 종류·변위량**을 회신용 dict 로 만든다. docstring 이 이미 이렇게 적고 있다:
> *"회신 JSON에 그대로 실을 재현 정보. **시드 없는 결과는 폐기 대상이다.**"*
⟹ 원장의 `seed_id` 는 이 함수의 `seed` 와 **같은 정의**여야 한다. 두 정의가 갈리면
"같은 진실이 두 곳에" 사고가 또 난다.

---

## 🔴 리뷰 상태 — **미리뷰 구간: §28 ~ (2026-08-18 현재)**

> **이 표를 먼저 보라. "어디까지 검증됐는가"가 흐려지는 것이 낡은 tarball 보다 위험하다.**

| 구간 | 내용 | critic 리뷰 |
|---|---|---|
| ~ §27 | core-h 일원화 · `probe_queuewait` 4곳 정합 | 🟢 **`OK`** — `04_REVIEW_LOG.md` 최신 항목, 대상 sha `8050a1d211be` |
| **§28** | `README_USER.cpu.md` 갱신 (문서만) | 🔴 **미리뷰** |
| **§29** | Gaussian **module 우선 탐지** (실클러스터 `rc=3` 3건 대응) | 🔴 **미리뷰** |
| **§30** | 모듈 확정 + 🔴 **재실행 논리 수정** (`is_submitted()` 가 실패 항목에도 True 였다) | 🔴 **미리뷰** |
| **§31** | `probe_throughput` **host 집계 유실 수정** (lead 부분 동결 해제분) | 🔴 **미리뷰** |
| **§32** | CREST `degraded` (ADR-044) + wall 상한 **큐 판독**(`wall_limit_source`) | 🔴 **미리뷰** |
| **§33** | 재실행 사양 (§R22/§R24): 태스크당 코어·예산표·guard 21,000·P6·sysprobe·CPU flags | 🔴 **미리뷰** |
| **§34** | 착지 (§R26/§R27/ADR-048/049): 게이트 3개·P6 코어 실측 게이트·P3 제거·`long` 큐 | 🔴 **미리뷰** |
| **§35** | ADR-050 허용 엔진 집합 (사용자 직접 결정) | 🔴 **미리뷰** |
| **§36** | 게이트를 **항목 단위 차단**으로 (lead 판정). 부분 실행 가능성 표시 | 🔴 **미리뷰** |
| **§37** | critic3 FIX-THEN-RUN 대응 (치명적 2 + 중대 1 + 사소 3) | 🔴 **미리뷰** |
| **§38** | ADR-052 큐 로직 **삭제** + **생산자→소비자 경계 검사**(테스트) | 🟢 **critic3 `OK`** |
| **§39** | critic `OK` 후 배치: 빌드 출력 `source_digest` 우선 · P1 최장 스테이지 트립와이어 | 🟢 3건 통과 / 1건 지적 |
| **§40** | 🔴 **트립와이어가 자기 존재 이유를 어기고 있었다** (critic3 지적) | 🟢 **critic3 `OK`** |
| **§41** | 🔴 **동봉 README 가 코드와 전 항목 불일치** (lead 발견) + 테스트 임시파일 누수 | 🟢 **critic3 `통과`** |
| **§42** | 🔒 **빌드 후 산출물 검증 관문** — 검사는 소스를, 사용자는 사본을 받던 구멍 | 🔴 **부분 재확인 대기** |
| **§43** | 🔒 관문을 **이름 지정 → 자동 발견**으로 (lead: 범위가 좁았다) | 🔴 **부분 재확인 대기** |
| **§44** | 🔴🔴 **RT-1 cluster failure: module name truncated. Three defects, not one.** | 🔴 **review pending** |

🔴 **현재 인도판 = `source_digest b8375e9d18326553` · 740 tests OK · `[stamp] ✅`**

> 🔒 **Why the module tests use real PATH shims, not Python mocks — do not "simplify" this.**
> The RT-1 loss happened because on this site `module load <nonexistent>` **prints
> `ModuleCmd_Load.c(208):ERROR:105` and still exits 0.** Our code read the exit status as success,
> so it never tried the fallbacks — and a module that works (`gaussian/g16.a03`) was sitting in the
> list, untried.
> 🔴 **A mock encodes the failure mode you already imagined.** "Fails but returns 0" is not a mode
> anyone imagines; it had to be *observed on the cluster* and then reproduced with a real shim.
> My own tests would have accepted a fix that only handled non-zero exits.
> ⟹ The verification builds executable `module`/`g16` shims on `PATH` and runs `sei_qc_detect`
> for real. **If you replace them with mocks, you delete the only thing that reproduces the
> incident.**
>
> 🔒 **Measurement hygiene — read this before reporting a "regression".**
> The suite runs in **≈23 s on a quiet machine** (735 tests). If you see multi-minute runs,
> that is **machine load or `/tmp` pressure, not a code regression** — several agents on this box
> have driven load average past 20, and a full `/tmp` once killed a build outright (§41.4).
> 🔴 **A timing change read as a code change has cost this team real rounds.** Check `uptime` and
> `df -h /tmp` before concluding anything from a slow run.
> Likewise: `skipped=8` standalone vs `skipped=22` during a build is **normal** — `make_package.sh`
> moves `dist/` aside first, so tarball-opening tests skip (that gap is what the `[6/7]` gate closes).
(tarball sha256 `ec2bb8ef321f` / `436b7574b88a` — 🔴 **재빌드마다 바뀐다**(gzip mtime).
**동일성 비교는 `source_digest` 로 하라.** critic 이 되돌리기 실험 후 재빌드했을 때
sha256 만 보고 '소스가 바뀌었나' 하고 놀란 적이 있다.)
(§32 반영본. 이전: `f9f31caef240`(§31) → `ab894eef0e63`(§30).)
(§29 의 `9dddebdd4e8a / 626 tests` 는 **§30 이 대체했다.** lead 가 그 낡은 값으로 동결을 선언했다가
정정했다 — **§0.7 이 예고한 "해시가 한 판 뒤처진 지시"가 그대로 재현됐다.**)

**lead 판정(2026-08-18): §28~§31 을 조정 완료 후 한 번에 리뷰시킨다.** 왕복 비용이 같기 때문이다.
🔴 **critic 최우선 지목 항목 = §30 의 재실행 논리.** 사용자에게 안내한
*"다시 실행하면 실패한 것만 다시 돕니다"* 가 **수정 전에는 거짓이었다.**
**검증은 실제 회신 JSON(`cpu_machine_pilot_results/`)을 픽스처로 삼아 진입점에서 하라(ADR-041).**


## 🔴 coder6 세션 (2026-08-19) — **별도 파일**: `src/HANDOFF_CODER6.md`

> **B0 실행 패키지 작업은 그 파일에 있다. 이 파일에 붙이지 않았다** — 3,000줄 아래 묻히기 때문이다.
> 이 파일(§0, §45)은 여전히 전부 유효하고, `HANDOFF_coder6.md` 는 한 세션의 델타다.
> `source_digest 4a484eb71ef2b36d` · 1122 tests OK · gate OK · `[stamp] ✅`
> 🔴 그 파일의 **"DELIBERATELY ABSENT vs MERELY UNFINISHED"** 표를 먼저 읽어라 —
> 의도적으로 비워 둔 것을 "고치면" 안 된다(단가 null, `fits: None`, 빈 descriptor 표).

---

## 0. 후임 coder 에게

문서에 있는 것은 안 쓴다(ADR / METHOD_SPEC / COMPUTE_PLAN / REVIEW_LOG 를 읽어라).
**내 머릿속에만 있고 어디에도 안 적힌 것**만 적는다.

### 0.1 건드리면 안 되는 곳 (동결. 풀려면 lead 판정)

| 대상 | 왜 |
|---|---|
| `config/accounts.json` 의 `-A` 매핑 | 세 진입점이 `resolve_account` 단일 소스라 안 갈린다. **그리고 `etc` 가 유효한지 아직 모른다** — 실클러스터에서 `수용 7·거부 0` 이 나왔지만 `-q` 수정과 동시에 바뀌어서 **분리되지 않았다.** |
| `ncpus` 기본값 64 | 사용자 정본 스크립트는 32다. **사이트 제한인지 그 잡의 사정인지 모른다.** `config/sizing.json` + `--ncpus-per-node` 로 덮을 수 있게만 해뒀다. |
| `vendored`(xtb) 최우선 | Gaussian 은 module 우선으로 바꿨지만 xtb 는 **동봉본 우선**이다. 이유는 재현성(우리가 검증한 6.7.1). `test_vendored_still_wins_for_xtb` 가 지킨다. |
| `size_job()` 의 값 | `500.0 / 1008.0(63링크) / 5.0` 이 critic 대조값이다. **값이 바뀌면 회귀다.** 단 `probe_queuewait` 는 예외(아래). |

### 0.2 🔴 되돌리기 실험의 함정 2종 — **이것부터 읽어라**

`§0.4` 의 "수정 전 코드에서 깨지는지 확인한다" 절차를 쓸 때 **그 확인 자체가 거짓이 되는**
두 가지 경우가 있다. 나는 둘 다 밟았다.

**(a) 되돌린 파일이 깨져서 난 오류를 "결함 탐지"로 착각한다.**
슬라이스 편집으로 코드 블록을 뒤바꿨더니 파일이 구문 오류가 났고, 테스트는 `FAIL` 이
아니라 **import ERROR** 를 냈다. 그대로 넘겼으면 *"3건이 깨진다"* 대신 *"1건 에러"* 를
근거로 삼았을 것이다 — **되돌린 것이 아니라 부순 것이었다.**
⇒ **되돌린 파일의 구문을 먼저 확인하라**(`python3 -c "import ast;ast.parse(open(f).read())"`).
그리고 **FAIL 과 ERROR 를 구분해서 읽어라.** ERROR 는 대개 실험이 잘못된 것이다.

**(b) 복원했는데 안 고쳐진 것처럼 보인다 — `__pycache__`.**
되돌리기 실험 뒤 원본을 복원했는데도 2건이 계속 실패했다. 코드는 이미 맞았고,
**테스트가 되돌린 코드의 `.pyc` 를 보고 있었다.** 30분을 썼다.
⇒ **되돌리기 실험 뒤에는 `find . -name __pycache__ -exec rm -rf {} +` 하고 다시 확인하라.**

🔴 **lead 도 이 세션 초반에 같은 함정에 걸렸다** — 낡은 `.pyc` 를 보고 "패키지 결함"이라고
보고했다. **lead 와 coder 가 각각 한 번씩 당했다.** 사람이 기억할 종류가 아니다.

### 0.2d 🔴 `src/dist/.stale.2042619/` — REMOVED 2026-08-19. What it was, so nobody looks for it.

**Recorded BEFORE removal, deliberately.** §45.4 warns about silent cleanup; the difference
between this and that is that the record went in first.

```
directory        src/dist/.stale.2042619/          created 2026-08-18 15:39
contents         sei_pilot_{cpu,gpu}.tar.gz + .sha256 + BUILD_STAMP.json, all dated Aug 18 14:54
source_digest    79624c4f182e8c14                  built_at_utc 2026-08-18T05:54:29Z, n_files 75
```

🔴 **It was not a neutral aborted build. It was the RT-1 round-2 DELIVERED package — the one that
failed on the cluster.** Verified by opening the tarball rather than by trusting the summary:

```
.stale tarball   config/env_paths.json  default   "gaussian/g16.c01.lin"     ❌ does not exist
                                        fallbacks  g16.b01.lin ❌ · g16.a03.lin ❌ · g16.a03 ✅
current tarball  config/env_paths.json  default   "gaussian/g16.c01.linda"   ✅
                                        fallbacks  g16.b01.linda · g16.a03.linda · g16.a03
```
Those are the truncated names from the `rstrip("(default)")` defect (§44.2/ADR-062). Every
Gaussian item in that run died in ~6 s with
`ModuleCmd_Load.c(208):ERROR:105: Unable to locate a modulefile`. **Only the last fallback,
`gaussian/g16.a03`, was ever a real module — and it was never tried, because `module load`
exits 0 on this site even when it fails (§44.4).**

🔒 **Removed by lead ruling, and the evidence argument INVERTS here.** §45.1's warning is that a
`.stale.*` reads as *"never built"*. A `.stale` holding a **known-broken, previously-delivered**
tarball is worse than that: it reads as a *spare artefact*, and someone could pick it up and ship
it. Everything it could testify to is already in ADR-062/063 in a far more usable form.
**Keeping the bytes added nothing and kept a package we know fails inside `dist/`.**

⚠ **What this says about the failure mode, and it is the reusable part**: a build can abort and
leave a *previously delivered* artefact stranded, not merely a scratch one. So *"check for
`VERIFICATION_FAILED.json` and `.stale.*` before concluding anything"* (§45.1) needs a second
clause — **open the `.stale` and find out WHICH build it is.** Its age was the tell: contents
dated 14:54, directory created at 15:39.

### 0.2c 🔴 `/tmp` ON THIS BOX IS REAPED **WITHIN** A SESSION (coder6, 2026-08-19)

This is not "the user cleared /tmp". It is an environment property, and it invalidates any
workflow that keeps state in `/tmp` **between two steps of your own work**.

**How it bit me.** I parked pristine copies in `/tmp/sei_revert_bk/` for a set of revert
experiments. Between two runs the directory vanished, so every `cp` restore failed — and
**the five reverts accumulated on top of each other.** The last one reported `failures=5`,
which I would have written down as one defect's blast radius. It was five defects at once.
`cp` printed its error into a stream I was skimming for the `OK`/`FAILED` line.

```
observed in one session:   /tmp 77 % used, 879 M free   →   1 % used, 3.7 G free
                           (and every sei_* leftover gone, mine included)
```

🔴 **This is a NEW cause for Rule 23's trap** (an experiment that does not reproduce the
hypothesis proves nothing). The known causes were partial revert, infidelity revert, and a
stale revert result. **Silently stacked reverts is a fourth, and it comes from the filesystem,
not from the reasoning.**

🟢 **Fix that works — use it, do not re-derive it.** `/tmp/revert_harness.py`-style discipline:
```
1. keep the pristine copy OUTSIDE /tmp, or re-verify it exists on every iteration
2. rebuild the mutated file FROM THE PRISTINE COPY each time — never mutate the current file
3. REFUSE TO START if the pristine copy is missing (a number measured against an unknown file
   state is not evidence)
4. syntax-check the mutated file before running (§0.2(a): ERROR ≠ FAIL)
5. assert byte-identity with the pristine copy after each restore
6. print the pristine sha256 once, at the top, so the whole table is attributable
```

⚠ And the corollary the lead added, which is the more important half: **a cleared filesystem
does not fix a leak, it postpones it.** The thing that filled `/tmp` was **our own test suite**
(§44.6). `make_package.sh` now has a `[0/7]` disk preflight that **refuses before touching
`dist/`** rather than dying mid-flight — but if the temp-dir count starts climbing during a run
again, that is a regression in §44.6's `addCleanup`/`atexit` fixes, **not housekeeping.**
Measure it: `ls -d /tmp/* | wc -l` before and after a full suite. It must be equal.

### 0.2b 내가 밟아서 알아낸 다른 함정 (문서 어디에도 없다)

1. **`gfnff_topo` 캐시** — xtb 는 GFN-FF 토폴로지를 작업 디렉터리에 캐시하고 **다음 실행에서
   재사용**한다. 같은 디렉터리에서 여러 구조를 연속 실행하면 2회차부터 1회차 토폴로지가
   적용돼 **591 eV 짜리 가짜 편차**가 나온다. 나는 이걸 "Issue #1118 재현"으로 보고할
   뻔했다. **xtb 실행마다 디렉터리를 격리하라.**
2. **xtb 는 셀 밖 좌표를 랩한 *뒤* 토폴로지를 만든다** → 경계를 가로지르는 분자가 조각난다
   (물이 17.01/1.01 amu 로 갈라지는 것을 봤다). **주기계 입력 좌표는 셀 안에 두어라.**
3. **xtb 6.7.1 은 주기계 GFN-FF SP 에서 정상 에너지를 내고도 `normal termination` 배너를
   안 찍는다**(`gfnff_setup: Could not read topology file` 경고와 함께).
   **배너로 성패를 판정하면 멀쩡한 결과를 전부 버린다.** 판정은 "에너지 파싱 + 유한값"으로.
4. **같은 이름 클래스/함수가 앞 정의를 조용히 덮는다.** 새 테스트를 기존과 같은 이름으로
   붙였다가 **새 테스트가 한 번도 실행되지 않았다.** 되돌린 코드에서도 전부 통과해서 알았다.
   지금은 `TestNoDuplicateTestClassNames` 가 `tests/` 와 `sei_pilot/` 양쪽을 AST 로 검사한다.
5. **가드를 가드로 시험하면 가드가 사라진다.** 중복 검사기를 시험하려고 **그 검사기 클래스
   자신**을 중복시켰더니, 덮어쓰기로 검사기가 없어져 아무 실패도 안 났다. **다른 대상으로 시험하라.**
6. **`build_stamp.py check --root` 오지정** — 저장소 루트가 아닌 곳을 주면 예전에는
   "파일 68개 삭제됨 / tarball 낡음" 오경보가 났다. 지금은 root 오류라고 말한다.
   **오경보는 진짜 경보를 못 믿게 만들어 낡은 tarball 보다 위험하다.**
7. **PBS 는 첫 비지시어 줄에서 지시어 파싱을 멈춘다.** 선택적 지시어를 빈 문자열로 치환하면
   헤더 한가운데 빈 줄이 생기고 뒤의 `#PBS` 가 통째로 무시될 수 있다.
   `squeeze_directive_blanks()` 가 그걸 없앤다. **템플릿을 고칠 때 이 함수를 우회하지 마라.**

### 0.3 테스트 지도 (어느 파일이 무엇을 지키는가)

| 파일 | 지키는 것 |
|---|---|
| `test_pbs_script_shape.py` | PBS 스크립트 형태(사용자 정본과 일치), 거부 메시지 미절단, **제출본 ≡ emit-script**, `probe_queuewait` 네 곳(표시·예약·사전검사·제출) 연동, 중복 정의 금지 |
| `test_gaussian_module_priority.py` | module > binary 우선순위, 최신 모듈, 실패 사유 구분, **실패는 재시도·완료는 건너뜀** |
| `test_units_budget.py` | core-h 정의 단일화, `size_job` 값 불변 |
| `test_integration_paths.py` | Gaussian 로그 → `collect_p1` → 판정 전 구간, 폴백 시 `cores_per_node = null` |
| `test_u27_noneq.py` | U-27 스모크 (목 g16, **양성/폴백/음성 대조 3종**) |
| `test_basisset.py` | `gen` 기저 원소 커버리지 |
| `test_payload_shell.py` | payload 가 존재하는 함수만 부르는가(셸에 컴파일러가 없다) |
| `test_build_stamp.py` | tarball ≡ 소스(내용 해시), root 오지정 구분 |

🔴 **양성 대조(내가 일부러 주입한 위반)가 여러 곳에 있다.** 보고서에 `[양성 대조 — 주입]`
라벨을 붙였는데, **라벨이 없던 판을 lead 가 발견 목록으로 오독**해 critic 에게 헛조사를
시킨 적이 있다. **대조군 출력에는 반드시 라벨을 붙여라.**

### 0.4 회귀 테스트 절차 (이게 이 세션의 가장 값진 산출물이다)

> **회귀 테스트는 수정 전 코드에서 깨지는 것을 확인하기 전까지 존재하지 않는 것으로 간주한다.**

이 절차가 실제로 잡은 것: 새 테스트가 한 번도 실행되지 않은 것(0.2-4), 동일성 테스트가
같은 인자를 두 번 넣는 항등식이었던 것, `to_dict()` 400자 컷이 실제 경로에 남아 있던 것.
**전부 "통과"로 보이던 상태였다.**

그리고 테스트 픽스처는 **진짜 생성기**로 만들어라. `args` 는 `cli.build_parser().parse_args()`,
`env` 는 `cli.build_env()`. 손으로 채우면 **"내가 상상한 CLI"를 검증하게 된다** — 실제로
손으로 만든 `env` 에 `vendored: {}` 를 넣어 P3 가 빠졌고, 그 결과 lead 와 숫자가 안 맞았다.

### 0.5 아직 안 한 일과 그 이유

| | 상태 |
|---|---|
| **V1b** (NVE drift + Δt² 스케일링) | 코드 완성, 예행 통과. **lead 지시로 중단.** `src/experiments/p2g/run_v1b.sh`. 평형화 2 ps + NVE 5 ps ×2 ≈ 2.5 h |
| **V1c / V1d** | 미착수. **V1b 판정②(Δt² 비)가 실패하면 돌리지 마라**(lead 지시) |
| **V2** (Li⁺(EC)₄ RDF) | 미착수. 규모는 **300~500원자**(lead 정정. 1,000~3,000은 λ_out *생산*용이다). 시점은 X3 결과가 정한다 |
| **검사 B** (`authority.json` — 결정의 부재를 잡는 검사) | 제안만. `HANDOFF §13`. 인도 후 |
| **L5 / L6 자동화** | 미착수 |
| **본 파이프라인 S1~S4** | **착수 금지** 상태 그대로 |

### 0.6 미해결 채로 인도되는 것 (믿고 쌓지 마라)

- **M2 임계(`IMAG_WINDOW_CM1 = -2000~-100`)의 근거 문장이 잘못 서 있다.** 내가 "창 폭이
  넓다"고 적었는데 lead 지적대로 **위험은 전부 하한 −100 에 몰려 있다.** 숫자는 안 바꿨고
  proposer 판정 대기다. `criteria/p1.py` + `HANDOFF §15.1`.
- **QST2 + `gen` 조합을 H2 스모크(`sp`)가 덮지 않는다.** 형식만 검증했고 **G16 이 없어
  실행 못 했다.**
- **`-q` 수정과 헤더 형태 5건 중 무엇이 4/4 거부를 풀었는지 모른다.** 한 번에 바꿨다.
- **`/apps/commercial/G16/g16/g16` 이 계산 노드에 있는지 모른다.** 이번 판에서 잡·probe 가
  직접 확인해 기록하게 했다 — **다음 회신이면 확정된다.**

### 0.7 lead 와 일하는 법

lead 는 **출력을 보고 그것이 무엇의 출력인지 확인하지 않는 실수**를 이 세션에서 여러 번 했다:
`85` 를 실제 제출 노드 수로 읽음, 내 양성 대조를 발견으로 읽음, 트리 해시가 한 판 뒤처진 채로
지시. **근거를 되물어라.** 실제로 내가 되물어서 헛계산 두 건을 막았다(V2 규모, 85노드).
그리고 **보고 끝에 항상 `sha256` 을 선언하라** — lead 의 확인 대상이 어긋나는 일이 세 번 있었다.

### 0.8 사용자 클러스터에 대해 알아낸 것

```
CPU        Intel Xeon Phi 7250 (KNL) — 68 core / 1 socket / 1 thread, RAM 101 GB
           🔴 KNL 이라 코어당 성능이 일반 Xeon 과 크게 다르다. 봉투 전체가 이 위에 있다.
sizing     감지 68 → 요청 64 (config/sizing.json 의 usable_cores)
스케줄러    PBS. `sinfo` 없음(SLURM 전용) → partitions 가 항상 빈 목록이다.
           **그래서 큐 폴백이 필요했다** — 이걸 모르면 `-q` 누락이 다시 난다.
큐          normal. 필터 훅 `job_submit_filter` 가 있다.
계정        probe/xtb → etc, Gaussian → gaussian, VASP → vasp (사용자 진술)
Gaussian    module `gaussian/g16.c01.lin` (사용자 확정). 바이너리 /apps/commercial/G16/g16/g16
           — 로그인에는 있고 계산 노드에는 없다(추정, 다음 회신에서 확정)
파일시스템   Lustre. scratch 20,537 TB / home 759 TB
처리량      200/200 수용, 동시 200+, 전체 132 s, 시작지연 61 s
큐 대기     1/4/16 노드 전부 64~67 s
```

### 0.9 지금 상태

`635 tests OK` · `[stamp] ✅` · **cpu `ab894eef0e63` / gpu `48184a5452b5`**
완료: probe×3, P3. **재실행 대상: P1 / P1b / P5 (2,130 core-h).**
사용자가 같은 디렉터리에서 `./run.sh` 를 다시 치면 **실패한 것만** 다시 돈다(이번 판에서 고쳤다).

---


> **이 파일은 정본이 아니라 상세 기록이다.** 요약에 담기지 않는 근거·제거 기록·재현
> 절차를 남긴다. 보고 자체는 lead 에게 직접 한다.
>
> ### 🔴 통신 수단 — 추측하지 말고 **호출해서** 확인한 결과 (2026-08-17)
> ```
> SendMessage → Error: No such tool available. SendMessage is disabled for this session,
>                      in subagents as well as here.
> ListAgents  → Error: No such tool available. ListAgents is disabled for this session.
> ```
> lead 가 `.claude/agents/sei-coder.md` 의 `tools:` 에 두 도구를 **추가한 뒤에도** 이렇다.
> ⇒ **agent 정의 변경은 이미 떠 있는 세션에 반영되지 않는다.** 적용하려면 coder 를
> **다시 spawn** 해야 한다. 그때까지 보고는 최종 출력 텍스트 + 이 파일로 간다.
>
> ⚠ 이 항목 자체가 "같은 사실이 두 곳에" 의 또 다른 형태다 — **agent 정의 파일**과
> **살아 있는 세션의 실제 도구 목록**이 어긋나 있고, 정의 파일만 갱신됐다.
> lead 는 정의 파일을 근거로 "coder 는 지금 쓸 수 있다"고 판단했고 그건 사실이 아니었다.
>
> ⇒ **교훈(양방향)**: 도구·환경의 가용성은 **문서(내 헤더든, agent 정의든)를 근거로
> 단정하지 말고 한 번 호출해 보라.** 5초면 끝난다. 이전 헤더가 `05_STATE.md` 72행을
> 근거로 "비활성"이라 적은 것도 같은 잘못이었다 — 결론은 맞았지만 **확인해서 맞힌 것이
> 아니었다.**
>
> 작성: coder / 2026-08-17 / 대상 스펙 `03_COMPUTE_PLAN.md` §R2-6 + §11.5

---

## 0. ✅ 인도 가능 — critic MAJOR 1건 수정 완료 (12차, 2026-08-17)

```
dist/sei_pilot_cpu.tar.gz  108K   ✅ BUILD_STAMP 검증 통과
dist/sei_pilot_gpu.tar.gz  109K   ✅
Ran 382 tests ... OK   (+7 신규)
두 프로파일 dry-run (clean 추출본)  →  cpu 10항목 / gpu 2항목 정상
```

### 고친 것 — `guard_source` 를 **값에서 파생**시켰다
`ResourceGuard.describe()` 신설. `self.max_core_hours / max_wall_h / max_gpu_hours / profile`
로부터 문장을 만든다. `guard_for_profile()` 이 `profile` 을 넘긴다.
```
cpu: "cpu 프로파일 / 5000 core-h / 24 h wall/잡. 근거: … 상한을 넘는 잡은 제출 자체가 되지 않는다."
gpu: "gpu 프로파일 / 60 core-h / 24 h wall/잡 / 4 GPU-h. 근거: …"
--max-core-hours 1234 → "1234 core-h" 로 **따라온다** (리터럴이었을 때의 실패 지점)
```
**테스트 7건 추가**: 값↔서술 결합, CLI 재정의 추종, **낡은 리터럴(`4,000`/`3,150`/`2,000`)
재유입 거부**, GPU-h는 0이면 표시 안 함, "제출 자체가 되지 않는다" 문구 유지,
그리고 **회신 JSON 통합 지점**에서 `guard.max_core_hours` ↔ `guard.guard_source` ↔
`report.profile` 이 서로 모순되지 않는지.

---

## 0-A. 인도 준비 — 빌드 신선도 가드 + lead 정정 반영 (11차, 2026-08-17)

### 🟢 지금 상태: **critic 재리뷰 대기. 인도 가능.**
```
dist/sei_pilot_cpu.tar.gz  108K   ✅ 소스와 일치 (BUILD_STAMP 검증)
dist/sei_pilot_gpu.tar.gz  109K   ✅ 소스와 일치
Ran 375 tests ... OK
```

### ① 🔴 빌드 신선도 가드 — **"다음엔 못 잡는다"에 대한 답**
lead가 `dist/*.tar.gz`(16:49) vs `payload/qc_adapter.sh`(17:01) mtime을 **우연히 눈으로 비교해**
낡은 패키지를 잡았다. 그 방식은 반복되지 않으므로 자동화했다 — `src/build_stamp.py`.

* 빌드 시 소스 트리의 **내용 해시**를 `dist/BUILD_STAMP.json` 에 기록
* `make_package.sh` 가 빌드 직후 **자기 검증**, 실패 시 빌드 자체를 실패시킨다
* 🟢 **`./src/digest.sh`(L3)가 매 세션 자동 표시** — 세션 열 때마다 보인다
* mtime이 아니라 **내용 해시** 기준(거짓 경고가 나면 사람이 경고를 무시하게 된다).
  `PROFILE` 처럼 빌드가 스스로 쓰는 파일은 제외.

**작동 실증**: 이번 라운드에서 내가 `run.sh`/`P4.sh`/`README_USER.gpu.md` 를 고치자
가드가 즉시 *"tarball 이 현재 소스보다 낡았다 — 변경: README_USER.gpu.md, payload/P4.sh, run.sh"*
로 잡아냈고, 재빌드 후 해소됐다. **설계대로 내 수정을 잡았다.**

### ② `[SMOKE — not H100]` + 메모리 상한 환산 금지 (ADR-030 A10)
lead의 실제 실행값(RTX 4070 SUPER)으로 검증:
```
measurement_label : [SMOKE — not H100]
max_atoms_completed : None      ← 🔴 회신용 필드는 비움(지시대로)
max_atoms_on_this_gpu : 66      ← 원값은 버리지 않음
memory_ceiling_transferable : false
```
H100/A100이면 `[MEASURED — target GPU]` 로 바뀌고 상한이 살아난다.
GPU 모델을 모르면 `[UNVERIFIED GPU]` — **추측하지 않는다.**

### ③ 🔴 lead 정정 수용 — `LD_LIBRARY_PATH` 자동 설정 **철회**
lead 반증을 내가 재확인했다:
```
env -u LD_LIBRARY_PATH python -c "import gpu4pyscf"  →  IMPORT_OK 1.8.1
(현재 LD_LIBRARY_PATH 는 비어 있음)
```
경로 문제가 아니라 **`nvidia-*-cu12` 패키지 부재**였다. `run.sh` 의 경로 조작 코드를
**제거**했고, 다시 들어오지 못하게 테스트로 막았다
(`test_runsh_does_not_manipulate_ld_library_path` — 주석 외의 LD_LIBRARY_PATH 사용을 거부).
`nvidia-smi` 를 위한 PATH 확장만 남겼다(WSL에서 실제로 필요하며 검증됨).

### ④ 🔴 false negative 차단 — lead 논거를 코드로
> *"고칠 수 있는 환경 문제가 능력 측정값으로 둔갑하는 것"*

P4가 import 실패를 **분류**한다:
`gpu_failure_class ∈ {likely_fixable_environment, module_not_installed, other}`.
`libnvJitLink` / `libcusolver` / `cannot open shared object file` 등이 보이면
**"고칠 수 있는 환경 문제"** 로 표시하고 pip 명령을 화면에 출력한다.
⚠ **"억지로 설치하지 마세요, 설치 불가도 답"** 원칙은 그대로 유지 —
**"진짜 불가"와 "고칠 수 있었는데 몰라서 포기"를 구분**할 뿐이다.
`README_USER.gpu.md` 도 lead 문안대로 교체(설치 목록을 **한 번에** 제시하는 이유 포함).

---

## 0-A. 🔴 BLOCKER 수정 — 범함수 이름 + 이름 사전검증 도입 (10차, 2026-08-17)

lead가 **실행으로** 잡은 BLOCKER. 우리 박스에 GPU와 pyscf가 있어 **이번엔 수정도 실행으로 검증**했다.

### 무엇이 틀렸나 — 로컬에서 재현 확인
```
pyscf 2.14.0 (seigpu env) 에서 libxc.parse_xc():
  FAIL  wb97x-d3     ← payload/P4.sh 가 쓰던 이름
  OK    wb97x-v, wb97x-d, wb97x-d3bj, wb97m-v
```
🔴 `wb97x-d3` 는 **오타가 아니라 그럴듯하게 틀린 이름**이었다. 문자열로는 완벽해서
정적 검토도 우리 테스트도 못 잡았고, **SCF를 시작하고 나서야** 터졌다.

### 고친 것
| # | 수정 |
|---|---|
| 1 | `XC = "wb97x-v"` — 단순히 "도는 이름"이 아니라 **ADR-029 생산 레벨과 일치**시켰다. P4의 목적이 "생산 레벨이 GPU에서 얼마나 빠른가"이므로 이것이 옳다 |
| 2 | 기저는 `def2-tzvp` 유지(권고 수용). 🔴 **`level.production_basis: "def2-TZVPPD"` 와 "환산 시 기저 함수 수 차이를 반영하라"는 경고를 JSON에 명시** |
| 3 | 🔴 **`sei_pilot/qcnames.py` 신설 — 이름 사전검증 관문.** `preflight_pyscf()` 가 SCF **전에** `libxc.parse_xc` + `gto.basis.load` 를 호출하고, 실패하면 **유효 후보 목록 + "아마 이것을 의도했을 것이다"** 를 출력하고 즉시 종료(rc=5) |
| 4 | **ORCA smoke를 넓혔다.** 예전 smoke는 `BP86/def2-SVP` 만 돌려 **생산 키워드를 한 번도 검증하지 않았다.** 이제 `sei_orca_header()` 로 **두 레벨(+SMD)을 H2에 실제로 적용**해 수초 만에 검증하고, 실패 시 후보 목록·수정 위치·ORCA 원문 25줄을 출력 |
| 5 | **`gpu_model: null` 버그** — `nvidia-smi` 를 PATH·`/usr/lib/wsl/lib`·`/usr/local/nvidia/bin` 순으로 찾고, 그래도 없으면 **cupy**로 채운다. GPU 메모리·개수도 함께 기록 |
| 6 | 메모리 스캔에 **시간 예산(기본 1,200 s)** — 큰 GPU에서 이 단계가 끝없이 길어져 GPU-h 예산을 먹는 것을 막는다. 중단 시 "max_atoms_ok 는 **하한**"임을 명시 |

### 검증 (🟢 실행으로)
```
로컬 pyscf 로 재현        →  wb97x-d3 FAIL / wb97x-v OK 확인
preflight 차단 확인       →  잘못된 이름에서 SCF 전에 예외 + 후보 목록 출력
python3 -m unittest ...   →  Ran 351 tests ... OK   (+19 신규, pyscf 없는 환경은 8건 skip)
seigpu 환경에서 재실행     →  19건 전부 실행, OK
실제 GPU(RTX 4070 SUPER)  →  P4 완주 실행 중 (아래 결과 참조)
```
신규 19건은 **원래 실패 모드를 재현하는 입력**(`wb97x-d3`)을 쓴다. 그리고
`KNOWN_GOOD_XC` 의 **모든 이름이 실제로 parse 되는지** 검사해 "그럴듯한 추측"이
목록에 들어오는 것을 막는다. payload 셸에 박힌 문자열도 직접 검사한다
(`test_p4_uses_production_functional`, `test_orca_smoke_covers_the_real_production_keywords`).

### 🔴 남는 위험 — 정직하게
* **ORCA 키워드는 여전히 `[UNVERIFIED]`다.** 우리는 ORCA를 갖고 있지 않다.
  넓힌 smoke가 **사용자 클러스터에서 수초 만에** 판정하지만, 그 전까지는 모른다.
* `KNOWN_GOOD_XC` 는 pyscf 2.14.0 기준이다. 다른 버전에서 다를 수 있어 후보 목록을
  **런타임에 다시 검증**해서 출력한다(하드코딩된 목록을 그대로 믿지 않는다).
* CP2K(P2)의 범함수/기저 이름은 이번 수정 범위 밖이다. 같은 유형의 위험이 남아 있으며
  1-step smoke가 부분적으로만 덮는다. **다음 순번으로 올린다.**

---

## 0-A. CPU/GPU 패키지 분리 + P5 추가 (9차, 2026-08-17 — 사용자 지시)

### 산출물이 둘이 됐다
```
src/dist/sei_pilot_cpu.tar.gz   (102 KB)  → HPC 클러스터   회신: sei_probe_report.cpu.json
src/dist/sei_pilot_gpu.tar.gz   (102 KB)  → GPU 머신       회신: sei_probe_report.gpu.json
```
**코드는 하나다.** `plan.default_items(profile)` 이 항목 집합만 분기하고, 빌드 시
`PROFILE` 파일과 프로파일별 `README_USER.md` 만 갈아 끼운다(복제 금지 지시 준수).

| | CPU 패키지 (10항목) | GPU 패키지 (2항목) |
|---|---|---|
| 항목 | probe_node, probe_throughput, probe_queuewait, P1, P1b, P2, P2ext, p2_scaling, P3, **P5** | probe_gpu_node, P4 |
| 백엔드 | SLURM → PBS → 셸 | **셸(nohup) 기본** (`--use-scheduler`로 해제) |
| 가드 | **5,000 core-h** / 24 h | **4 GPU-h** + 60 core-h / 24 h |

### 🔴 가드: 4,000 → **5,000** (네 규칙대로)
P5(330) 추가 후 128 core/node 기준 **예약 총량 3,941 core-h**로 3,800을 넘었다 ⟹ 5,000으로 상향.
사용자 문구도 함께 고쳤다. **"상한 초과 잡은 제출 자체가 안 된다"는 성질은 그대로**이며
프로파일마다 그것을 테스트로 고정했다(`test_guard_exists_in_every_profile`).

### 🔴 P4의 CPU 기준값 — **(a)안 채택**
GPU 패키지가 **같은 머신의 CPU로 기준 계산을 포함**한다. 정확도(1e-5 Ha)와 속도비가
동일 조건에서 나온다. (b)안(사전 계산 동봉)은 우리 환경에 QC 코드가 없어 **불가능**하다 —
없는 것을 있다고 쓰지 않았다.
⚠ **속도비의 분모가 "GPU 머신의 CPU"이지 "HPC 노드의 CPU"가 아니다.** 이 사실을
GPU 사용자 문구와 회신 JSON 양쪽에 명시했고, 사후 보정용으로 `probe_gpu_node`가
그 머신의 core 수·CPU 모델을 함께 잰다. 또한 이 CPU 기준 계산분(30 core-h)을
가드에 계상해 **critic N-1(P4의 CPU 참조가 가드 밖)이 함께 해소**됐다.

### P5 — 단일 숫자가 아니라 **곡선**
대표 **14종**을 결정론적으로 생성했다(`tools/make_p5_species.py`, 검증 테스트 포함):
* 원자수 **3 / 5 / 6 / 7 / 10 / 11 / 15 / 20 / 21** (pool 상한 22 근처까지)
* 전하 **−1 / 0 / +1**, **개각 4종**(EC•⁻, EMC•⁻, CH3O•, Li(EC)•)
* 전 종을 **ADR-029 기본 레벨**로, 4종은 **값싼 레벨로도** → 소분자에서의 단가비
  (P1b는 40~80원자에서 쟀다. 소분자에서 다를 수 있다)

회신은 **종별 원자료**(`n_atoms, charge, mult, core-h, wall, SCF 반복수, opt 사이클, 수렴여부`).
🔴 **평균을 내지 않는다** — 곡선 적합은 받는 쪽 몫이다. 요약값은 전부 `diagnostics`(참고용)로
분리했고 원자료가 정본임을 필드에 박았다. 판정은 `≤90 / 90~150 / >150` 3분기이며
**`threshold_basis: "wB97X-D3/def2-TZVP/SMD"` 라벨**과 "고수준에 그대로 적용하지 마라"는
caveat을 항상 함께 낸다. 우선순위는 **P1 다음, P1b 앞**(지시대로), **P1과 독립**이다.

### 검증
```
python3 -m unittest discover -s tests   →  Ran 327 tests ... OK  (+35 신규)
두 프로파일 dry-run (우리 박스)          →  각각 정상. cpu 10항목 / gpu 2항목
clean 추출 후 실제 실행 (양쪽)           →  회신 파일 2개 생성 확인
merge 실증                              →  파일럿 6건 손실 0, 프로파일 태그 정확, 경고 0
```
신규 테스트 35건은 lead가 지목한 **두 실패 모드를 재현하는 입력**으로 짰다:
* **프로파일 혼입** — 항목 집합 완전 일치, 교집합 공집합, 미커버 항목 0, payload 파일 존재,
  `P4 ∉ cpu` / `P1·P5 ∉ gpu` 개별 고정
* **머지 손실** — 파일럿/실패/미해결 개수가 입력 합과 일치, payload 내용 보존,
  프로파일 원본 블록 보존, **양성 대조군**(같은 id가 양쪽에 있으면 덮어쓰지 않고 경고 /
  같은 프로파일 2개면 `cpu_2`로 보관하고 경고)

---

## 0-A. 📌 사용자에게 전달할 문구 (2벌, 그대로 복사)

**① CPU 클러스터에 보낼 것 — `sei_pilot_cpu.tar.gz`**
> ```bash
> tar xf sei_pilot_cpu.tar.gz && cd sei_pilot_cpu
> ./run.sh --dry-run      # 5분. 제출 없이 환경만 점검
> ./run.sh                # 실제 제출
> ```
> 필요한 것은 `python3`(3.6+) 하나뿐이고 pip/인터넷 불필요합니다.
> 계산량은 **5,000 core-hour / 잡당 24시간**으로 하드 제한되며 초과 잡은 제출조차 되지 않습니다.
> 끝나면 **`sei_pilot_work/results/sei_probe_report.cpu.json`** 하나만 회신해 주세요.

**② GPU 머신에 보낼 것 — `sei_pilot_gpu.tar.gz`**
> ```bash
> tar xf sei_pilot_gpu.tar.gz && cd sei_pilot_gpu
> ./run.sh --dry-run      # 1분. GPU/CUDA/python 스택 점검
> ./run.sh                # 실제 실행 (배치 스케줄러 없이 백그라운드)
> ```
> `gpu4pyscf`/`pyscf` 가 없으면 **"이 머신에서는 GPU-DFT를 쓸 수 없다"는 측정 결과로
> 기록하고 정상 종료**합니다. 억지로 설치하지 마세요 — 그것도 답입니다.
> GPU 4시간 / 24시간 wall로 제한됩니다.
> 끝나면 **`sei_pilot_work/results/sei_probe_report.gpu.json`** 하나만 회신해 주세요.

**③ 두 파일이 도착하면 (lead가 실행)**
> ```bash
> cd src/pilot_package && PYTHONPATH=. python3 -m sei_pilot.cli merge \
>     sei_probe_report.cpu.json sei_probe_report.gpu.json -o merged.json
> ```
> 손실 없이 합치고, 프로파일이 섞였으면 경고를 띄운다.

---

## 0-B. L4 배치 통합 계획기/검증기 인도 (8차, 2026-08-17)

`./src/batch.sh` — **배치를 제출하기 전에** 이것으로 검증한다. lead 판정대로 **(A) 계획기/검증기**까지만.

### 무엇을 하는가
왕복 1회 = 달력 3.5일이고 🔴 **RT-3을 쪼개면 1.5~2.0주**다. 그래서 이 도구는
**왕복을 늘리는 배치를 제출 전에 거부**하고, 거부할 때 **대가를 주 단위 숫자로 함께 낸다.**
("위반입니다"만 말하면 사람은 규칙을 우회한다.)

| 규칙 | 내용 |
|---|---|
| V1 | RT 미배정/미정의 RT 참조 (미배정은 조용히 사라진다) |
| **V2** 🔴 | `must_not_split` RT 안에 사람 회신 지점 2개 이상 → **ERROR + 대가 표시** |
| V3 | 선행 작업이 뒤 왕복에 있는 의존 역전 |
| V4 | wall > 24 h (ADR-004) → 체인 분할 필요 |
| V5 | RT당 사용자 개입 1회 초과 → 달력 비용(일→주) 계산 |
| V6 | 왕복 총 횟수가 확정 구조(7)를 초과 |
| **V7** 🔴 | **ADR-027 자료구조 규칙** — 원장 가지치기 / 가지친 network에서 완결성 계산 / 두 시계 수동 동기화 **전부 금지** |
| V8 | RT-3 stage 오타(=의존성 누락) |

`show`(구조 열람) / `validate`(판정, 종료코드 1=불성립) / `drift`(config ↔ 문서 어긋남).

### 🔴 두 가지 발견 — 둘 다 lead/engineer 판단이 필요하다

**(a) 왕복 목표치가 문서 안에서 갱신됐다.**
§R3.4 L4 레버 표는 `왕복 8회 → 5회`인데, §R8.5(Round 8)에서 **7회로 확정**됐고 ADR-019가 재확인했다.
상충이 아니라 **갱신**으로 판단해 계획기는 최신값 **7**을 기준으로 판정한다.
근거를 `config/rt_plan.json`의 `_historical_note`에 남겼다. **다르게 보면 알려달라.**

**(b) 🟢 RT-3 임계경로에 달력 2일이 숨어 있을 수 있다 — engineer 확인 요망.**
§R8.5는 `… → thermo DFT 3일 → xTB TS 앵커 2일 → …` 로 **직렬** 서술했고 총 7.5일 = 단순 합이다.
그런데 **둘 다 '열거·여과' 산출물만 필요해 보인다.** 병렬이면 **임계경로 7.5일 → 5.5일**
(왕복은 그대로 1회, 순수 이득 2일).
🔴 **내가 임의로 병렬화하지 않았다.** 처음엔 병렬로 인코딩했다가 문서와 어긋나는 것을 보고
직렬(문서 그대로)로 되돌렸고, **테스트로 그 재발을 막았다**
(`test_dag_critical_path_matches_declared_days`). 대신 `open_questions[Q-RT3-PAR]`로 남겼다.
자원 경합(같은 큐·core 예산)으로 실제 직렬일 수 있어 **engineer 판단이다.**

### 검증
```
python3 -m unittest discover -s tests   →  Ran 290 tests ... OK  (+40 신규)
./src/batch.sh validate src/config/work_items.example.json  →  🟢 통과 (왕복 7회, 24.5일)
고의 위반 5종 주입                        →  V2·V3·V4·V7 ERROR + V8 WARN 전부 적발, rc=1
./src/batch.sh drift                     →  ✅ 일치
```
40개 테스트는 **규칙마다 통과/위반 쌍**으로 구성했다(양성 대조군 없는 "안 터졌다"는 검증이 아니다).
드리프트 점검은 개발 중 **자기 파서 결함**(굵게 표기 `| **7** |`)을 스스로 잡아냈고 그것도 테스트에 넣었다.

### 범위 밖으로 두고 넘어간 것
- `work_items.example.json`의 core-h/wall은 전부 `[ESTIMATE]`다. **구조 검증용이지 견적이 아니다.**
  RT-1 회신이 오면 `[MEASURED]`로 갈아끼운다.
- (B) 실제 DAG 실행기(Snakemake + 파일큐)는 **미착수**. RT-1 회신 후로 미룬다.

---

## 0-A. L3 개선 3건 반영 (7차, 2026-08-17)

lead가 직접 사용하고 올린 3건, 전부 반영. **1번이 가장 중요했고 가장 많이 고쳤다.**

### #1 신선도(staleness) — "낡은 것을 최신인 척" 차단
이 저장소에 **git이 없다.** 그래서 두 개의 독립 신호를 결합했다(`freshness.py`):
* **(a) 파일 mtime** — 이력이 없어도 즉시 얻는 **하한**. 파일이 12일 전 것이면 그 안의 모든 줄은 ≥12일이다.
* **(b) 스냅샷 관측 이력** — 매 실행마다 **절 단위 내용 해시**를 남겨, 안 바뀌었으면 `last_changed`를 이어받는다. 실행을 거듭할수록 정확해진다.
* 나이 = `max(a, b)`. **둘 다 하한이므로 나이를 과소평가하지 않는다** — 과대평가는 "확인해 보라"는 신호일 뿐이지만 과소평가는 잘못된 확신이다.
* 표기: 관측 이력이 있으면 `⏳9일 경과`, 없으면 **`≥3일 경과`**(아는 것보다 더 아는 척하지 않는다).
* 🔴 **「다음 액션」 절이 임계일(기본 7일) 이상 안 바뀌면 [1] 위에 경고 배너**를 띄운다:
  *"아래 [1] 항목이 이미 끝난 일일 수 있다. 문서를 먼저 갱신하라."*
* 회귀 테스트 8건 — 9일 스냅샷 주입 시 전 항목 `⏳` + 배너, 절이 바뀌면 시계 리셋, mtime만으로도 하한 작동.

### #2 카운트 불일치
헤더 `미해결 위험 22건` ↔ 하단 `위험 25` 는 **정의가 달랐다**(열린 것 vs 전체).
라벨에 차이를 명시했다: `위험 25(미해결 22) · 미확정 14(열림 3)`. 두 줄이 일치하는지 테스트로 고정.

### #3 취소선/해소 배너를 [0]에서 제외
`~~`로 시작하거나 `해소/CLOSED/Superseded` 를 포함하면 [0]에서 뺀다.
🔴 단 **스스로 `[UNRESOLVED]`/`미해결`/`판정 중` 이라고 선언한 블록은 그 단어가 있어도 숨기지 않는다**
(예: *"…해소되지 않았다 [UNRESOLVED]"*). 살아 있는 이슈를 숨기는 것이 노이즈보다 나쁘다.

### 🟢 덤 — 검수 중 발견해 함께 고친 것
`RT-1 파일럿 실행 — 사용자`(**임계 경로 맨 앞**)가 [1]에 9개 중 하나로 묻혀 있었다.
**액션의 소유자를 인식**하게 만들어(`— 사용자`, `proposer:`, 소제목 `외부 대기`)
**사용자 소유 액션은 [3]으로 올린다.** 지금 [3]에 그 한 건만 떠 있다 — 정확히 맞는 상태다.

검증: `Ran 244 tests ... OK` (+17). 실제 docs에서 [4]가 lead의 최신 변경(ADR-026/027, U-05 closed)을 즉시 표시하는 것도 확인했다.

---

## 0-X. L3 세션 상태 자동요약 인도 (6차, 2026-08-17)

`./src/digest.sh` — 세션을 열 때 이것부터 실행한다. **문서를 요약하지 않고 행동 범주로 분리**한다.

| 블록 | 내용 |
|---|---|
| **[0] 지금 프로젝트를 좌우하는 것** | 05_STATE 상단의 미해소 🔴 하이라이트 최대 3건 |
| **[4] 지난 세션 이후 바뀐 것** | 🟢 **스냅샷 대비 diff** — ADR 신규/상태변경, U-NN 상태변경, R-NN 신규/해소, 진행 로그 신규, 문서 분량 급변. **재오리엔테이션 세금의 본체가 "그동안 뭐가 바뀌었지?"이므로 맨 위에 둔다** |
| **[3] 내가 답해야 하는 것** | 사람만 답할 수 있는 항목 |
| **[1] 지금 당장 할 수 있는 것** | 선행조건이 다 풀린 항목 + 진행 중 액션(진행 중 우선 정렬) |
| **[2] 막혀 있는 것** | 무엇이 막고 있는지(`↳ 막는 것: U-05`)와 함께 |

부가: 산출물 상태(패키지 KB·테스트 수), 미해결 위험 건수, 팀 현황, `--full` 시 위험·게이트·**구현 구속조건**·최근 로그.

### 설계에서 신경 쓴 것
1. **세 범주 배타성**을 테스트로 못박았다. 겹치면 "지금 할 수 있는 것"의 신뢰도가 떨어지고,
   그러면 아무도 이 도구를 안 본다.
2. **분류 우선순위를 명시**했다: 해소됨 → 사람만 답 가능 → teammate 대기 → 열린 질문(기본값 사람).
   🔴 개발 중 실제로 **Q15(proposer 판정 대기)가 [3]으로 새는 버그**가 났고 테스트가 잡았다.
3. **`docs/` 는 절대 쓰지 않는다.** 스냅샷은 `.session_state/` 에만. 이것도 테스트로 고정.
4. **조용한 실패 금지.** 문서 규약이 바뀌어 파싱이 무너지면 빈 다이제스트가 아니라
   `--check` 가 종료코드 1로 실패한다. 식별자 없는 항목 건수도 하단에 항상 표시된다.
5. 기본 출력은 **한 화면(60줄 미만)**. 길면 안 읽고, 안 읽으면 35~50 h 절감이 0이 된다.

### 검증 (🟢 이번엔 실행 검증이 된다 — ADR-004 제약 밖)
```
python3 -m unittest discover -s tests   →  Ran 382 tests ... OK  (+190 신규)
./src/digest.sh                          →  실제 docs/ 8,700줄에서 정상 출력
diff 실증                                →  가짜 ADR·로그 추가 → [4]에 즉시 표시, 원복 후 "변경 없음"
문서 무결성                              →  실행 전후 docs/ mtime 불변 (테스트로도 고정)
```
35개 테스트: 파서 9 · 분류 10 · diff 4 · 렌더/CLI 7 · **실제 docs 대상 5**.

### 남은 한계 (정직하게)
- 파싱은 **우리 팀 문서 규약**에 의존한다. 규약이 바뀌면 `--check` 가 실패로 알리지만,
  **고치는 것은 사람 몫**이다.
- `05_STATE.md` 의 "다음 액션" 목록이 낡으면 다이제스트도 낡은 것을 보여준다.
  도구는 문서보다 정확할 수 없다. (관측: 현재 3·4·5번 항목이 이미 완료된 것으로 보인다 —
  lead가 정리하면 [1]의 신호 대 잡음비가 올라간다.)
- 요약 문장은 **원문 발췌**다. 의미 압축(LLM 요약)은 하지 않았다 — 결정론적이지 않고
  틀렸을 때 사람이 알 수 없기 때문이다. 대신 모든 항목에 `↳ 05_STATE.md:176` 출처를 단다.

### 📌 나중에 반영할 구속 4건 (지금 구현 안 함 — 기록만, lead 지시)
1. **S2-B 탐색 단계에서 barrier cutoff 금지** (ADR-020 — 독립성의 성립 조건)
2. **강성 ODE에서 species별 절대 허용오차(atol) 개별 지정** — H2O·HF는 `atol ≈ 1e-12 M` 급 (ADR-021)
3. **로그선형 포획–재포획 모형에 난이도 공변량 필수** (ΔG_rxn, 변하는 결합 수, 분자도, 종 크기)
4. **`MOPAC ≥ 22.0`** 명시 + 🔴 **PM7 궤적 ≤ 5 ps 상한** (ADR-023)

---

## 0-Y. 🔴 critic BLOCKER 2건 수정 완료 (5차, 2026-08-17)

둘 다 **실제 버그**였고 재현했다. 그리고 lead 지적대로 **기존 테스트가 원리적으로 못 잡는
종류**였다 — 수정과 함께 넣은 회귀 테스트가 **수정 전 코드에서 실제로 실패하는 것을
확인**했다(아래 표의 마지막 열).

### B-1 체인 재실행 시 전체 워크플로 재계산

| 수정 | 내용 |
|---|---|
| **① 논리 키 멱등성** | `JobSpec.logical_key` 신설 → 체인 전 링크가 같은 논리 키를 공유. 템플릿이 `SEI_LOGICAL_KEY` 를 export 하고, `common.sh` 는 **논리 키 완료 마커**를 본다. ⇒ 링크 0이 정상 종료했으면 링크 1은 **즉시 종료**한다 |
| **② 단계 체크포인트** | `sei_stage` 가 `stages/<name>.json` 의 `rc:0` 을 보고 **이미 끝난 단계를 건너뛴다.** P1/P1b/P3/P2 전부에 자동 적용(공통 층에 넣었다). ⇒ 링크 0이 진짜 wall에 잘렸을 때 링크 1이 **이어받는다** = self-chaining 약속이 실제로 성립 |
| **③ 이중 실행 감사** | `executions.jsonl` / `stage_events.jsonl` 에 실행·건너뜀을 append. `collect.execution_audit()` 가 단계별 실행 횟수를 세어 **2회 이상이면 `duplicate_execution: true` + 경고**("결과가 덮어써졌다. CREST/NEB-TS는 비결정론적이라 다른 TS로 수렴했을 수 있다") |
| **④ CP2K 부분성공 함정** | CP2K는 내부 WALLTIME에 걸려도 **rc=0으로 종료**한다 → 체크포인트가 "성공"으로 남아 다음 링크가 md를 통째로 건너뛸 뻔했다. `P2.sh` 가 목표 스텝 미달이면 `sei_invalidate_stage md` 로 무효화 |

**함께 고친 MAJOR 2건** (같은 코드 경로라 분리가 더 위험하다고 판단):
* **M-1** 체인 부분 제출 실패 → `chain_partial_submit` 을 `failures[]` 에 기록(+`links_submitted`)
* **M-2** 링크 0 실패 후 링크 1 성공 시 논리 키의 `failed` 마커를 **셸이 직접 제거** ⇒ "데이터는 있는데 상태만 영구 fail" 소멸. 회귀 테스트 있음

### B-2 s(t) 시간축 10배 압축

| 수정 | 내용 |
|---|---|
| **① 스텝 번호 직접 파싱** | `parse_cp2k_mulliken_spin` 이 각 Mulliken 블록 **직전의 `MD\| Step number` / `MD\| Time [fs]`** 를 함께 붙여 반환(두 CP2K 출력 계열 모두 시도) |
| **② 시간축 결정 우선순위** | `resolve_frame_times()`: 블록 시각 → 스텝×dt → **명시 stride** → 추정 stride(경고) → 프레임 순번(**신뢰 불가** 표시). 어떤 경로를 썼는지 `time_axis_source` 로 항상 회신 |
| **③ payload가 stride를 명시** | 템플릿의 Mulliken 주기·timestep을 파라미터화(`{{MULLIKEN_EVERY}}`, `{{TIMESTEP_FS}}`)하고 `cp2k_common.sh` 가 그 값을 **s(t) 추출기에 직접 넘긴다** + `p2_meta.json` 에 기록. 추정에 의존하지 않는다 |
| **④ .ener 주기 정렬** | 템플릿에 `&PRINT/&ENERGY/&EACH MD {{MULLIKEN_EVERY}}` 를 명시해 두 출력 주기를 같게 맞췄다(코드가 방어하지만 애초에 어긋나지 않게) |
| **⑤ 신뢰 불가 시 승격 금지** | `evaluate_spin` 이 `time_axis_source` 를 보고, 신뢰 불가면 `⟨s⟩>0.85` 여도 **`provisional_pass` 로 승격하지 않는다** |
| **⑥ 창 허용오차 2%** | 🔴 **테스트를 쓰다가 발견한 2차 결함**: 6000 step(3 ps) 런의 마지막 Mulliken 프레임은 2995 fs라 `>= 3.0 ps` 검사를 **5 fs 차이로 탈락**한다. 샘플링 격자는 끝점에 닿지 못하므로 2% 허용오차를 뒀다. 이게 없으면 B-2를 고쳐도 "진짜 3 ps인데 창 부족" 오판이 남는다 |

### 회귀 테스트 — **수정 전 코드에서 실패함을 확인**

| 테스트 | 수정 전 |
|---|---|
| `tests/test_payload_shell.py` (신규 6건) — **bash payload를 실제로 실행**. 링크 0 성공 후 링크 1이 재계산하지 않는가 / 링크 0이 죽으면 이어받는가 / 실패 마커 정리 / 이중 실행 감사 / 논리 키 export / `submit_chain` 논리 키 전파 | **2건 FAIL** |
| B-2 7건 (다중 프레임, stride 10, 스텝번호 없음, **비정수 stride**, 신뢰도 분류, 3 ps end-to-end) | **5건 FAIL** |

⇒ "테스트 통과가 곧 정확성이 아니다"라는 지적을 받아, **이번엔 테스트가 버그를 잡는지를 먼저 검증**했다.

---

## 0-Z. IRC 끝점 판정 — proposer §12 반영 완료 (4차, 2026-08-17)

**현재 구현이 ADR-003 축(b)를 만드는 반응을 선택적으로 죽인다**는 proposer 논거를 수용하고
`02_METHOD_SPEC.md §12.3`의 **2층 그래프 + 속도론적 병합**으로 교체했다.

| 규칙 | 구현 | 검증 테스트 |
|---|---|---|
| **R1** Layer C(공유결합, Li 제외)가 다름 → distinct | `criteria/endpoints.py` | `test_R1_covalent_change_is_distinct` |
| **R2a** Layer C 동일 + **실체(entity) 수 변화** → distinct | 두 층 합친 그래프의 연결 성분 수 | 🔴 `test_R2a_ion_pair_formation_is_distinct` — **옛 규약이면 기각됐을 `ROCO₂⁻+Li⁺ → ROCO₂Li` 형 반응이 이제 통과함을 직접 고정**(`endpoint_distinct_C_only == False` 인데 verdict=distinct) |
| **R2b** 실체 수 동일 + Layer I만 다름 → **속도론** τ=0.1 eV | barrier 양방향 < τ → 병합 / 하나라도 ≥ τ → distinct | `test_kinetic_merge_below/above_tau` |
| **R2b barrier 미지** → **undetermined** (병합도 분리도 안 함) | 사람 검토 플래그 + `unresolved_for_lead` | 🔴 `test_R2b_without_barrier_is_undetermined_not_rejected` |
| **R3** 두 층 모두 동일 → same | | `test_R3_identical_is_same` |

### 함께 지킨 §12.4의 4개 지시
1. **R1→R2a→R2b→R3 순서대로** 구현. Layer C / Layer I를 분리 저장(해시·결합목록 각각).
2. **판정 근거 전량 기록**: `endpoint_distinct_C_only`, `endpoint_distinct_with_Li`,
   `entity_count_change`(+양쪽 실체 수), `barrier_fwd_eV`, `barrier_rev_eV`,
   `merge_rule_applied`, 두 층의 WL 해시. ⇒ **규칙이 또 바뀌어도 재계산 없이 재판정 가능.**
3. 🔴 **Li–X 임계를 하드코딩하지 않았다** — `config/graph_layers.json` (ADR-001 데이터/코드 분리).
   값에 `[PLACEHOLDER-ESTIMATE: 실측 필요]` 를 명시했고, **±0.2 Å 민감도(판정 뒤집힘)를
   매 판정마다 계산해 회신**한다. 뒤집히면 `unresolved_for_lead` 에 "RDF로 실측해 확정하라"가 올라간다.
4. **R2b는 자동 승인하지 않는다** — `human_review_required: true` + lead 회신 항목 생성.

### 스키마 영향 (1.1 유지, 필드 추가)
`pilots[].status` 에 **`undetermined`** 를 추가했다. R2b-미지를 `fail`로 적으면
**§12.2의 위음성이 회신 단계에서 되살아나기 때문**이다. 사유는
`version.SCHEMA_EXTENSIONS` 에 기계가 읽는 형태로 기록했다.

### 남긴 위험 (§12.5 그대로)
- R2b barrier의 신뢰성 — P1 파일럿은 이 barrier를 **계산하지 않으므로** 배위 재배열 쌍은
  구조적으로 `undetermined` 가 된다. 이것은 버그가 아니라 정직한 상태다.
- Li 접촉의 거리 정의는 경계 요동을 원리적으로 남긴다 → 민감도 보고로 크기를 드러낸다.

---

## 0-A. lead 판정 반영 현황 (3차, 2026-08-17)

| lead 판정 | 상태 |
|---|---|
| 가드 기본값 **4,000** 채택 ("타협 불가는 가드의 *존재*에 대한 것") | ✅ 2차에서 이미 반영. 사용자 문구·README·run.sh 헤더 전부 4,000. `./run.sh` 만으로 전량 실행되며 `--full` 은 하위호환 별칭으로만 남았다 |
| wall 24 h + "상한 초과 잡은 제출 자체가 안 된다" 유지 | ✅ 불변. `test_guard_is_still_enforced_at_the_new_value` 로 고정 |
| 결정 6건 승인 (.sif 미동봉 / P2 환원상태 / P3 경고 등) | ✅ 그대로 유지 |
| P3의 "S2-A fanout에 직접 대입 금지" 경고 **유지** (U-04 확정 후에도) | ✅ 유지. `criteria/p3.py` 의 `interpretation_note`, 테스트로 고정 |
| IRC 끝점 규약은 proposer 판정 대기 — **그 선택이 JSON에 기록되게 하라** | ✅ 3차 구현 → **4차에서 §12.3 규칙으로 교체됨(위 §0)** |

### IRC 규약(`[UNRESOLVED: IRC-CONV]`) 기록 방식 — 재계산 없이 뒤집을 수 있게 했다

판정이 나중에 바뀌어도 **1,000 core-h를 다시 쓰지 않도록**, 두 규약의 결과를 **둘 다** 계산해 회신한다(비용 ≈ 0, 그래프 해시 두 번).

```
pilots[P1].detail.irc.endpoint_comparison = {
  convention_used : "covalent_only(include_ionic=False)",
  status          : "[UNRESOLVED: IRC-CONV] proposer 판정 대기 …",
  method          : "Weisfeiler-Lehman 그래프 해시 (WL 한계 명시)",
  bond_criterion  : "d < 1.25 x (r_i + r_j), Cordero 반경(Å)",
  ionic_elements_excluded : ["Li","Na","K","Mg","Ca"],
  primary     : {include_ionic:false, distinct:…, hash_forward/reverse, n_bonds…},
  alternative : {include_ionic:true,  distinct:…, hash_forward/reverse, n_bonds…},
  conventions_agree : true|false
}
```

* **두 규약이 같은 결론이면** `unresolved_for_lead[]` 에 "정보용, 조치 불필요"로 남는다.
* 🔴 **결론이 갈리면** ("이 TS는 Li 배위만 바뀐 것에 가깝다") 그 사실을 눈에 띄게 올리고,
  **"재계산 없이 `alternative` 를 읽으면 반대 규약의 결과"** 라고 조치까지 적어 준다.
* 회귀 테스트 2건: 개환은 두 규약이 일치함 / Li만 이동한 쌍은 규약이 갈림.

---

## 0-B. lead 판정 3건 — 반영 완료 (2026-08-17, 2차)

| 변경 | 상태 | 반영 위치 |
|---|---|---|
| **1. 하드가드 2,000 → 4,000 core-h** (wall 24 h 유지) | ✅ 완료 | `sei_pilot/budget.py:23` `DEFAULT_MAX_CORE_HOURS=4000.0`. 가드 이력을 주석으로 남김. `ORIGINAL_R2_6_MAX_CORE_HOURS=2000.0` 은 회귀 테스트용으로만 보존 |
| **2. P1b 분리·재단** (동일 기하 위 SP/grad/Hessian + opt5 양쪽 level, ~400 core-h, `diffuse_scf_pathology` 경고) | ✅ 완료 (1차에서 이미 §11.5대로 구현) | `payload/P1b.sh`, `criteria/p1b.py`. 우선순위를 90→**75(P1 직후)** 로 올림 — "중요한 곳은 S1이 아니라 S2 thermo 예산"이라는 지시 반영 |
| **3. P2 환원상태 1 ps → 3 ps, 3분기 판정** | ✅ 완료 | `criteria/p2.py` — 판정 코드명을 지시대로 `reject_pbe` / `provisional_pass` / **`undetermined`** 로 통일, 판정 창 `SPIN_VERDICT_WINDOW_PS = 3.0` 신설 |

**가드 4,000에서 승인된 전 항목이 계획된다**는 것을 회귀 테스트로 고정했다
(`test_default_guard_runs_the_whole_approved_package`: 예약 3,355 core-h / 상한 4,000,
`skipped_for_budget == []`). 2,000이었다면 P1이 잘렸다는 계산도 테스트로 남겨 두었다
(`test_guard_2000_cannot_fit_probes_plus_P1P2P3`) — 나중에 누가 가드를 되돌리려 할 때
근거가 되도록.

### 변경 3에서 내가 추가로 넣은 안전장치 (지시에 없던 것, 사유 있음)

P2(1 ps) + P2ext(+2 ps)를 **별도 잡**으로 두었다(P2ext는 P2의 restart에 의존).
따라서 P2ext가 죽으면 실제 확보 궤적이 1 ps인데 판정만 3 ps인 척할 위험이 있다. 그래서:

* 궤적 길이를 meta가 아니라 **실제 `s(t)` 시계열에서** 계산한다(`trajectory_ps`).
* `⟨s⟩ > 0.85` 인데 창이 3 ps 미만이면 **`provisional_pass` 로 승격하지 않고
  `undetermined`** 로 떨어뜨린다. ("1 ps는 값싼 거부권이지 값싼 승인이 아니다"를
  코드로 강제한 것이다.)
* 반대로 **`⟨s⟩ < 0.3` 기각은 짧은 창에서도 확정**으로 둔다(평형 전에 이미 번졌으면
  회복이 없다는 §11.5 근거).
* `spin_localization` 블록에 `mean_s / min_s / max_s / slope_per_ps / drifting /
  trajectory_ps / window_satisfied / series_downsampled(최대 200점)` 를 전부 싣는다.
* 창이 모자라면 `pilots[P2].warnings[]` 에 "판정을 승인으로 쓰지 마라" 를 남긴다.

이의가 있으면 알려달라. 되돌리기는 `p2.py` 상수 하나다.

## 1. 구현한 것

산출물: **`src/dist/sei_pilot_package.tar.gz` (76 KB)** — 사용자에게 이것 하나만 보내면 된다.

| 파일 | 역할 |
|---|---|
| `src/pilot_package/run.sh` | 사용자 진입점. `--dry-run` / 기본(제출) / `--collect` / `--status` / `--full` |
| `sei_pilot/plan.py:47` `default_items()` | 프로브·파일럿 10개 정의(예산·우선순위·전제조건·근거) |
| `sei_pilot/plan.py:157` `size_job()` | 🔴 core-h 예산 → wall 역산. **자원 상한을 스케줄러가 강제**하게 만드는 핵심 |
| `sei_pilot/budget.py:36` `ResourceGuard` | 하드가드(core-h/GPU-h/wall). 숫자는 여기 한 곳에만 |
| `sei_pilot/cli.py:113` `cmd_submit()` | 멱등 제출 + afterany 자기연쇄 + collector 사전 체인 |
| `sei_pilot/scheduler.py` | SLURM → PBS(Pro/Torque) → 순수셸 어댑터. 템플릿 분리 |
| `sei_pilot/sysprobe.py` | A1/A2/A3/A8, I/O, 소프트웨어 인벤토리, **Q2 outbound**, **클러스터 GPU** 파서 |
| `sei_pilot/probes.py` | **many-task 처리량**·**큐 대기** 분석 (engineer "절대 빼지 마라" 항목) |
| `sei_pilot/criteria/p1.py` | 허수진동 정확히 1개(−2000~−100 cm⁻¹) + IRC 두 극소 판정 |
| `sei_pilot/criteria/p1b.py` | 두 level **단계별** 단가비 + `diffuse_scf_pathology` 경고 |
| `sei_pilot/criteria/p2.py` | 드리프트(meV/atom/ps) + SCF 발산 + 🔴 **s(t) 3분기 판정** |
| `sei_pilot/criteria/p3.py` | candidate 분포 + 시도당 core-h + 수렴률 |
| `sei_pilot/criteria/p4.py` | 에너지 차 < 1e-5 **Hartree** + H100:1노드 속도비 |
| `sei_pilot/report.py:48` | `sei_probe_report.json` (schema **1.1** = §R2-6의 1.0 전 필드 유지 + 확장) |
| `payload/*.sh` | 노드에서 도는 실제 계산 (P1/P1b/P2/P2ext/p2_scaling/P3/P4 + 프로브 3종) |
| `inputs/` | EC+Li 라디칼 폐환/개환 구조, **148원자 EC8/EMC4/LiPF6 box**(결정론적 생성), CP2K 템플릿 |
| `tools/make_box.py` | box 생성기(고정 시드). 밀도 1.06 g/cm³, 분자간 최소거리 2.06 Å |
| `src/make_package.sh` | 테스트 → dry-run 스모크 → tarball → 지문. 실패하면 패키지를 만들지 않는다 |

**스키마 확장(1.0 → 1.1)**: `provenance`(패키지 지문·시드·시각), `guard`(예약/생략 사유),
`cluster.cpu`·`filesystems`·`scheduler_detail`, `pilots[].breakdown`·`warnings`,
`unresolved_for_lead[]`, `throughput_probe`의 3개 필드. 사유는
`sei_pilot/version.py:SCHEMA_EXTENSIONS`에 기계가 읽을 수 있는 형태로 박아 뒀고 JSON에도 실린다.

---

## 2. 스펙과 다르게 한 것 / 스펙에 없어 내가 결정한 것

1. **가드 기본값 4,000** — §11.5 + lead 승인. §0 참조. (해소됨)
2. **P2를 환원상태(charge −1, LSD)로 돈다** (중성 궤적 별도 실행 없음).
   근거: 한 궤적으로 드리프트 + s/step + 🔴 ADR-005 s(t)를 **동시에** 얻는다.
   중성을 따로 돌면 비용 2배에 s(t)는 여전히 못 얻는다.
   부작용: LSD라 s/step이 닫힌껍질 대비 **보수적 상한**이다 — 회신 JSON에 명시된다.
   길이는 P2(1 ps) + P2ext(+2 ps) = **3 ps**이며, 실제 확보량이 모자라면 판정이
   자동으로 강등된다(§0의 안전장치).
3. **큐 대기 프로브 예약을 85 node 합계로 잡았다.** 처음엔 1 node로 잡았는데 그러면
   가드가 실제 소비의 1/85만 막는다(= 가드 무력화). 이 수정으로 예산이 90 → **363 core-h**
   가 됐다. 이 값이 §5-2의 "§R2-6 예산표에 없는 항목" 지적의 근거다.
4. **P3 열거 모드 = `b2f2_graph_edit`(참조 구현)**. ADR-006의 S2-A(fragment-recombine +
   LIBE pool)는 **아직 조건부(P0 미확정)** 라 그 엔진을 구현하지 않았다.
   🔴 그래서 회신 JSON에 **"이 candidate 분포를 S2-A fanout 견적에 직접 대입하지 마라.
   엔진 무관하게 믿을 수 있는 값은 시도당 core-h와 수렴률이다"** 라는 경고를 자동으로 싣는다.
   P0가 확정되면 `libe_pool_recombine` 모드를 추가하면 된다(자리 마련해 둠).
5. **P1의 QC 코드 = ORCA 우선**(qchem/psi4는 미구현 stub). 스펙이 코드를 지정하지 않았다.
   용매는 SMD/acetonitrile — **단가 측정용 선택이며 S1 본계산의 용매 모델 결정이 아니다**
   (코드 주석·JSON에 명시).
6. **`./run.sh` 기본 동작 = 계획 출력 → 15초 중단 기회 → 제출.** lead의 "3동작" 요구와
   "비싼 계산을 조용히 돌리지 마라" 요구를 동시에 만족시키는 절충이다.
   비대화형(배치)에서는 대기 없이 진행한다.
7. **`.sif` 미동봉** — 우리 박스에 apptainer/docker가 없어 **빌드할 수단이 없다.**
   없는 것을 있다고 쓰지 않았다. 대신 `containers/manifest.json` 훅과 `modules.conf` 훅을
   만들어 사용자가 넣으면 자동 인식된다. 현재 탐색 순서는 실질적으로 모듈 → 바이너리 → skip.

---

## 3. 실행/검증한 것 (전부 실제로 돌린 결과)

```
python3 -m unittest discover -s tests      →  Ran 192 tests ... OK  (critic BLOCKER 2건 수정 후 재실행. skip 0건)
src/pilot_package/run.sh --dry-run          →  이 박스(스케줄러·QC·GPU 없음)에서 전 항목 graceful skip
SEI_NO_PROMPT=1 run.sh (실제 제출)          →  로컬 nohup 백엔드로 probe_node + collector 완주,
                                               유효한 sei_probe_report.json 생성 (I/O 1038 MB/s,
                                               smallfile 36.5 k/s, Q2 https=True 실측)
run.sh 재실행                                →  "이미 완료 → 건너뜀" (멱등 재개 확인)
tar 풀고 clean 환경에서 dry-run              →  검증 통과, 지문 일치
src/make_package.sh                          →  dist/sei_pilot_package.tar.gz (76 KB)
```

**테스트로 잡은 실제 버그 3건**(전부 수정됨):
- 잡 스크립트에 `A && B` 명령을 직접 박아 **B가 계측·마커 밖에서 실행**되던 문제
  (collector가 완료 마커를 먼저 찍고 나중에 돌았다) → 명령을 별도 `.cmd.sh` 파일로 분리
- `graph_hash`의 색 압축이 원자 순서에 의존 → **IRC 끝점 동형 판정이 깨짐** → 정렬 후 라벨링
- `probe_node.sh`의 중첩 heredoc이 깨져 `node_probe.json`이 `exit 0` 한 줄이 되던 문제

**192개 테스트가 덮는 범위**: 단위 변환 왕복, 자원 가드, wall 역산·체인, 마커 멱등성,
SLURM/PBS/local 인자·템플릿 렌더링·afterany 체인, 클러스터 출력 파서 전종, P1~P4 판정
(정상/2개 허수/창밖/IRC 동일극소/드리프트/SCF발산/**s(t) 3분기·3 ps 창·짧은 창 강등**/표류),
처리량·큐대기 분석,
JSON 스키마, 동봉 구조 무결성(연결성·겹침·밀도·표적 인덱스), 열거기 결정성·원자가.

---

## 4. 🔴 검증하지 못한 것 (critic이 정적으로 봐야 할 곳)

우리 환경에 스케줄러·QC 코드·GPU가 없다(ADR-004). 아래는 **사용자 클러스터에서 처음
도는 순간이 최초 검증**이다. 코드에 `[UNVERIFIED]` 주석으로 전부 표시했다.

| 대상 | 완화 장치 |
|---|---|
| ORCA 키워드·출력 파일명(`*_NEB-TS_converged.xyz`, `_IRC_F_trj.xyz`) | 🔴 본계산 전 **수초짜리 smoke 테스트**. 실패 시 1,000 core-h를 쓰지 않고 즉시 종료 |
| CP2K 기저/유사퍼텐셜 파일명, Mulliken 스핀 열 위치 | 1-step smoke + `s_of_t.dat` 이중 경로(파서 실패해도 원본 보존) |
| `xtb --path` 문법 | 실패는 "수렴률 0"이라는 측정값으로 기록 |
| gpu4pyscf API | import 실패도 "이 클러스터에선 GPU-DFT 불가"라는 측정 결과로 회신 |
| sbatch/qsub 수용 여부, 사이트 QoS·배열 상한 | `--dry-run` + 제출 실패의 부분 격리 + `failures[]` |
| P1 초기 구조가 **진짜 그 반응의 TS로 수렴하는가** | 보장 못 한다. 그래프·기하 무결성만 검증됨. TS 여부는 파일럿의 판정 기준이 스스로 판단 |

---

## 5. engineer 스펙에서 발견한 결함·모호한 지점 (engineer 전달 요망)

1. ~~§R2-6 D-7(2,000)과 §11.5(4,000) 충돌~~ → **lead 판정으로 해소(4,000).**
2. 🔴 **큐 대기 프로브 비용이 §R2-6 표에 없다.** 실제로는 128 core/node 기준 363 core-h로
   P2(400)에 맞먹는 최대 항목 중 하나다. "~4 node-h"라는 서술은 맞지만 core-h로 환산하면
   패키지 예산의 12%다. 예산표에 넣어야 한다.
3. **P3의 "반응체당 candidate 수"는 엔진에 종속된 양인데 §R2-6은 엔진을 지정하지 않았다.**
   ADR-006이 조건부라 나는 대입 금지 경고를 붙였다. P0 확정 후 재정의 필요.
4. ~~P1의 "IRC가 서로 다른 두 극소" 판정 방법 미정의~~ → **해소.** proposer §12.3의
   2층 그래프 + τ 병합으로 교체했다(§0). 내 원래 구현(Li 제외)은 ADR-003 축(b)를
   죽이는 오류였고, proposer 논거가 옳다.
5. **P2 "재시작 파일 크기" 회신 항목**은 CP2K가 wall 이전에 restart를 남겨야 얻어진다.
   나는 CP2K `WALLTIME`을 스케줄러 wall의 90%로 넣어 스스로 멈추게 했다.

---

## 6. 사용자에게 전달할 문구 (그대로 복사해서 쓰면 된다)

> 첨부한 `sei_pilot_package.tar.gz` 를 클러스터 로그인 노드에 올리시고:
>
> ```bash
> tar xf sei_pilot_package.tar.gz
> cd sei_pilot_package
> ./run.sh --dry-run      # 5분. 아무것도 제출하지 않고 환경만 점검합니다.
> ./run.sh                # 실제 제출 (계획을 보여주고 15초 뒤 진행)
> ```
>
> 필요한 것은 `python3`(3.6+) 하나뿐이고 `pip install` 도 인터넷도 필요 없습니다.
> 계산량은 스크립트 내부에서 **4,000 core-hour / 잡당 24시간**으로 하드 제한됩니다
> (상한을 넘는 잡은 제출 자체가 되지 않습니다).
> 잡이 잘리거나 중간에 실패해도 `./run.sh` 를 다시 실행하시면 이어서 진행합니다.
>
> 끝나면 **`sei_pilot_work/results/sei_probe_report.json` 파일 하나만** 회신해 주세요.
> 판단하실 것은 없습니다 — 성공/실패 판정은 전부 스크립트 안에 들어 있습니다.

(가드 4,000이 기본값이므로 추가 플래그는 필요 없다. `--full` 은 하위호환 별칭으로만 남겨 뒀다.)

---

## 7. 다음 작업 후보 (내가 착수하지 않은 것)

- S1/S2/S3 본 파이프라인 — **착수 금지 지시대로 손대지 않았다.**
- `libe_pool_recombine` 열거 모드 (P0 확정 후)
- Q-Chem / psi4 어댑터 (현재 ORCA만)
- 회신 JSON을 읽어 §R2-1/§R2-3/§R2-5를 자동 재계산하는 도구 (engineer가 원하면)

---

## 8. Gaussian16 전환 / gen 기저 / dual-seed (이번 배치)

### 8.1 실행하다가 잡은 결함 3건 (테스트는 초록불이었다)

| # | 결함 | 영향 | 왜 못 잡았나 |
|---|---|---|---|
| B-3 | payload 가 `sei_stage` 를 못 본다 | 잡 템플릿이 `sei_job_main bash <cmd>` 로 **새 프로세스**를 띄워 셸 함수가 상속되지 않는다. P1/P1b/P2/P2ext/P3/P5 **전부** 첫 `sei_stage` 에서 죽고 단계 체크포인트·core-h 분해가 통째로 소실 | 테스트의 **가짜 payload 가 스스로 `common.sh` 를 source** 하고 있었다. 가짜가 진짜보다 환경을 잘 갖추면 테스트는 거짓 통과한다 |
| B-4 | `P3.sh` 가 `xtb` 를 절대경로 없이 호출 | `rc_opt=127` 로 opt 가 조용히 실패 → **최적화되지 않은 기하 위에서 수렴률**을 재고 있었다 (환경 문제가 능력 측정값으로 둔갑) | 폴백 `[ -f xtbopt.xyz ] \|\| cp ...` 이 실패를 삼켰다 |
| B-5 | `P1.sh` 가 ORCA 시절 함수 `sei_orca_header` 를 계속 호출 | **P1(최우선, 1,000 core-h)이 첫 줄에서 `command not found`**. 큐를 기다린 뒤에야 드러난다 = 왕복 1회 소실 | 어댑터를 G16으로 재작성할 때 P1만 포팅에서 빠졌고, 셸에는 컴파일러가 없다 |

**구조적 방어를 붙였다** (`tests/test_payload_shell.py`):
- `test_no_payload_calls_an_undefined_sei_function` — payload 가 부르는 모든 `sei_*` 가
  실제로 정의돼 있는지 정적 검사. 셸의 컴파일러 역할.
- `test_every_payload_using_sei_stage_can_reach_its_definition` — 진짜 payload 가
  `common.sh` 에 닿는가.
- `test_sei_stage_is_available_to_a_payload_that_does_not_source_common` — 새 payload 가
  source 를 빠뜨려도 런타임에는 살아남는가 (`export -f` 2차 방어).

### 8.2 `gen` 기저 (lead 지시 ②)

* `inputs/basis/def2-TZVPPD.gbs`, `def2-TZVPD.gbs` — BSE gaussian94, 원소 `H,Li,C,O,F,P`, ECP 없음.
* route 는 `wB97XD/gen`, 기저 블록은 좌표 뒤. **분자에 등장하는 원소만** 내보낸다
  (없는 원소까지 넣었을 때 G16 동작을 확인하지 못했으므로 확실한 쪽을 택했다).
* preflight 는 "키워드가 유효한가"가 아니라 **"동봉 블록이 등장 원소를 덮는가"** 를 본다.
  못 덮으면 `.gjf` 를 **쓰기 전에** 종료(rc=3)하고 없는 원소·고칠 파일을 출력한다.
* `tests/test_basisset.py` (21건) — 요구 원소 집합, 동봉된 **모든 입력 분자**의 커버리지,
  체크섬과 파일 내용 일치.

### 8.3 P5 독립 시드 (lead 지시 ③)

* `sei_pilot/seeding.py` — G16 opt 에는 난수가 없으므로 독립성은 **시작 기하**에서 온다.
  `random.Random(seed)` 로 등방 섭동(기본 0.10 Å), 시드 0 = 원본.
* 대표 4종 (`ch3o_radical`, `ec`, `ec_radical_anion`, `li_ec2_cation`) — 크기 5~21원자,
  전하 −1/0/+1, 개각/닫힌껍질을 고루 덮게 골랐다.
* 회신에 시드·진폭·최대변위·최단원자간거리와 **해석 주의**(진폭이 작으면 과소평가,
  크면 과대평가)가 함께 실린다. σ 계산은 하지 않는다 — 원자료만 넘긴다.
* P5 실행 14 → 22회. 예산 330 → 430 core-h. 전체 3,860 / 5,000 core-h 로 가드 안.

### 8.4 내가 정한 것 (확정 아님 — 판정 필요)

1. **G-1/G-2 ↔ level2/level1 매핑.** lead 는 G-1/G-2 로 말했고 우리 구조는
   `level1(값싼)/level2(주)` 단가비 쌍이다. `level2←G-1`, `level1←G-2` 로 두었다.
   근거는 TZVPD 가 TZVPPD 보다 작다는 것뿐. `config/qc_levels.json` 의
   `_interpretation` 에 명시했고, 바꾸려면 그 파일만 고치면 된다.
2. **P1 의 TS 탐색법.** ORCA 판은 NEB-TS(양끝단)였는데 G16 에 NEB 가 없다.
   가장 가까운 대응인 **QST2** 로 포팅하고, 실패 시 단끝단 `opt=(ts,calcfc)` 폴백.
   어느 경로였는지 `ts_method.json` 에 남는다. **단가는 경로마다 다르다** —
   회신 해석 시 함께 읽어야 한다. proposer 확인 요망.

---

## 9. P2 계열 제거 — **되살리기 위한 기록** (git 이력이 없으므로)

lead 지시로 `P2`(CP2K PBE AIMD) · `P2ext`(s(t) 3 ps 창) · `p2_scaling`(노드 스케일링)을
제거했다. 근거는 **ADR-015 §7 "개발기 AIMD = 0"** — 이들이 재던 것의 **소비자가 사라졌다**
(명시된 근거가 폐기된 ADR-005의 G-AIMD 분기를 가리키고 있었다).

### 무엇을 지웠나
| 지운 것 | 무엇이었나 |
|---|---|
| `payload/P2.sh` | CP2K PBE AIMD 1 ps + 환원상태 궤적 |
| `payload/P2ext.sh` | 궤적 1 ps → 3 ps 증량 (s(t) 판정 창) |
| `payload/p2_scaling.sh` | CP2K 1/2/4 node 스케일링 |
| `inputs/cp2k_aimd.inp.tmpl` | AIMD 입력 템플릿 |
| `inputs/electrolyte_box.xyz` + meta | 전해질 상자 (C/H/O/Li/P/F) |
| `tools/make_box.py` | 그 상자 생성기 |
| `sei_pilot/criteria/p2.py` | 에너지 표류, Mulliken 스핀 s(t), 3분기 판정(`reject_pbe`/`provisional_pass`/`undetermined`), `resolve_frame_times()`(B-2 수정) |
| `collect.collect_p2` | 위 판정의 취합 |
| `tests/test_criteria.py` 의 `TestP2`/`TestP2Spin`/`TestP2Scaling` (229줄) | |
| `tests/test_plan_report_e2e.py` 의 s(t) 3 ps 경로 (66줄) | |

### 되살릴 때 필요한 것
1. **B-2 수정을 다시 넣어야 한다.** `p2.resolve_frame_times()` 는 "프레임 인덱스 ≠ 시간"
   버그(s(t) 시간축이 10배 압축)를 고친 것이다. 같은 실수를 반복하기 쉽다.
2. **3 ps 판정창 + 2 % 허용오차.** 3 ps 요청이 2995 fs 에서 끝나는 것을 실패로 보지 않기 위한 것.
3. **전해질 상자의 고전 力場 파라미터는 존재하지 않았다** (AIMD 라 필요 없었다).
   고전 MD 로 되살린다면 파라미터 출처를 먼저 정해야 한다 — 지어내면 안 된다.

### 대체된 것: `P2f` (CP2K FIST 스모크, < 50 core-h)
proposer §28.2 로 **CP2K 는 FIST(고전 MD) 엔진으로 남는다**(ADR-012 λ_out 경로).
그래서 재는 것이 **단가에서 가용성으로** 바뀌었다 — "도는가"만 본다. 스케일링은 재지 않는다.
- 입력은 **SPC/E 물**(Berendsen et al. 1987, 출판값)이다. 전해질 고전 力場을 우리가
  **지어내지 않기 위해서**다 — 지어낸 수치는 언젠가 물리 결과로 오인된다.
- 판정 로직이 없으므로 `criteria/` 모듈이 없다. `collect.collect_p2f` 가 직접 본다.

## 10. 항목별 계정 매핑 (PBS `-A`)

이 클러스터의 계정은 프로젝트가 아니라 **소프트웨어 단위**다. 전역 `--account` 하나를
전파하면 어떤 값을 넣어도 절반이 틀리고, PBS 는 계정이 틀리면 **제출 자체를 거부**한다.

- **단일 출처**: `config/accounts.json`. `Item` 은 `account_key`(어떤 소프트웨어인가)만 든다.
  `tests/test_accounts.py` 가 `plan.py` 에 계정 문자열이 박히지 않았는지 정적으로 검사한다.
- 매핑: probe→`etc`, gaussian→`gaussian`, xtb→`etc`, cp2k→`etc`(**미확인**), vasp→`vasp`
- **미확인은 조용히 쓰이지 않는다**: dry-run 표에 `etc?` 로 표시되고 경고 블록이 뜬다.
- 덮어쓰기: `--account cp2k=<이름>` (여러 번 가능) / `--account <이름>`(전역)
- 큐 기본값 `normal`

## 11. 이기종 노드 sizing

- `cores_per_node_login` / `cores_per_node_compute` / `cores_per_node_detected` **분리**
- 폴백 순서: 계산 노드 조회 → `--cores-per-node` → 🔴 로그인 값(시끄러운 경고)
- **감지 68 → 요청 64** 변환은 `config/sizing.json` 한 곳에서 온다
  (사용자 확인 "68 core system, 64코어만 사용"; engineer §R18 `select=1:ncpus=64`).
  감지값을 그대로 요청하면 잡이 큐에서 영원히 안 뜬다.
- 출처가 항상 함께 표시된다: `core/node : 64 (출처: pbsnodes -a / 감지 68 → 요청 64 …)`

---

## 12. RT-1b 흡수 (P1b) · M2 임계 결정

### 12.1 P1b 가 재는 5수 (engineer §R16.6 RT-1b)
대상 3종은 `p5_species/manifest.json` 에서 **5 / 12 / 22 원자에 가장 가까운 종을 유도**한다
(id 를 payload 에 박으면 종 교체 시 한쪽만 갱신된다).

| # | 값 | 어떻게 |
|---|---|---|
| 1 | `u_cheap` | **[A]** G-3(def2-SVPD) opt+freq 단가 |
| 2 | `r_high` | **[B]** G-1(def2-TZVPPD) opt+freq / A |
| 3 | 🔴 `r_composite` | **(A + [C]) / A**, C = G-1 SP on A 기하 — ADR-032 판정의 입력 |
| 4 | `gen_penalty` | **[D]** 같은 기저(def2-TZVPP)를 gen 경로 vs 내장 키워드 |
| 5 | SCF 실패율 | 기존 단계별 측정(sp/force/freq/opt5)에서 나온다 |
| + | `ΔG(composite − 전량고수준)` 3종 | 추가 비용 0. `G_composite = G_cheap − E_cheap + E_high_SP` |

**engineer 사양과 다르게 한 것 1건**: engineer 는 gen 페널티를 *"내장 def2TZVPP vs gen
def2TZVPPD"* 로 적었는데, 그 비교는 **gen 오버헤드와 diffuse 비용을 섞는다.**
같은 기저(def2-TZVPP)를 두 경로로 넣어 gen 만 분리하고, diffuse 는 gen 안에서
따로 뺀다(G-1 SP / G-4gen SP). **요청한 "분리"가 그렇게 해야 실제로 이뤄진다.**

- 판정은 하지 않는다. ADR-032 규칙(|ΔG| < 0.05 채택 …)의 경계값은 **회신에 함께 싣되
  적용은 받는 쪽**이 한다. `_who_applies` 필드에 명시.
- 측정이 빠진 비율은 **None** 이고, `note` 로 *"None 을 1.0 으로 대치하지 마라 — 그 순간
  총액 추정이 조용히 낙관 쪽으로 틀어진다"* 를 함께 보낸다.
- 동봉 기저 4벌: `def2-TZVPPD`(G-1) · `def2-TZVPD`(G-2) · `def2-SVPD`(G-3) · `def2-TZVPP`(G-4gen)
- 예산 400 → **700 core-h**. 전체 **2,948 / 5,000** 으로 가드 안.

### 12.2 M2 임계 (`IMAG_WINDOW_CM1`) — **명시적 결정, 숫자는 안 바꿨다**
ADR-032 로 판정 Hessian 이 값싼 기저(SVPD)에서 나오게 됐다.

**결정: 재보정 불요.** 창 폭 1,900 cm⁻¹ 는 기저 변경에 따른 허수진동수 크기 변동
(통상 수십 cm⁻¹)을 충분히 덮는다. `criteria/p1.py` 에 근거를 주석으로 남겼다.

🔴 **다만 이 판단에는 확인되지 않은 전제가 있다**: "수십 cm⁻¹" 은 문헌 통념이고
**우리 계에서 실측한 값이 아니다.** 그래서 두 가지를 했다:
1. 판정 결과에 `imag_window` 블록을 실어 **어느 레벨·어느 기저의 Hessian 이었는지**를
   항상 함께 남긴다(전에는 창만 있고 출처가 없었다 — 재해석 불가 상태였다).
2. `who_can_change: proposer` 로 못 박았다. **임의 변경 금지.**
   P1b 가 같은 계를 두 기저로 돌리므로 **이 전제를 사후 검증할 수 있다.**

## 13. "같은 진실이 두 곳에" — 구조적 대책 제안 (구현 안 함)

여섯 번 반복됐고 이제 critic 이 리뷰 전에 예측할 수 있는 수준이 됐다.
지금까지의 대응은 **사후 개별 대처**였다: `envpaths.py`(경로), `config/accounts.json`(계정),
`config/sizing.json`(코어 수), `config/qc_levels.json`(범함수·기저).
**패턴은 이미 있다 — "권위 파일(config/) 하나 + 코드는 읽기만".** 빠진 것은 **강제 장치**다.

**제안: `authority.json` + 빌드 시 `consistency_check.py`**
1. **권위 등록부** `config/authority.json` — "이 사실의 유일한 출처는 이 파일의 이 키다"를
   나열한다. 예: `cores_per_node → config/sizing.json`, `functional/basis → qc_levels.json`,
   `imag_window → criteria/p1.py:IMAG_WINDOW_CM1` (코드가 출처인 경우도 등록한다).
2. **검사 A(값)**: 등록된 값의 **리터럴이 다른 파일에 나타나면 실패.**
   지금 `tests/test_accounts.py` 가 계정에 대해 하는 일을 일반화한 것이다.
3. **검사 B(결정)**: 등록부의 각 항목은 `decided_by` + `decided_because` 를 요구한다.
   비면 실패 → **"결정이 없는 채로 기본값이 남아 있는" 상태 자체를 잡는다.**
   이번 M2 건이 정확히 이 유형이었고, 값 검사(A)로는 잡히지 않는다.
4. **검사 C(외부 도구)**: 외부 코드 이름(범함수·기저·키워드)에 **검증기가 붙어 있는가.**
   붙어 있지 않으면 실패. `wb97x-d3` 사고를 사전에 잡는 검사다.

**가장 싼 첫 걸음은 검사 B다.** 값이 아니라 *결정의 부재*를 잡으므로 리터럴 스캔보다
오탐이 적고, 이번처럼 "숫자는 맞는데 근거가 없는" 경우를 유일하게 잡는다.
지시가 있으면 착수한다.

---

## 14. 인도 전 확인 절차 (🔴 mtime 으로 판단하지 마라)

lead 가 두 번 낡은 사본을 보고 판단했다. 한 번은 `dist/` mtime, 한 번은 추출본의 `p1.py`.
**mtime 은 신뢰할 수 없다** — 그래서 `build_stamp.py` 를 만들었다. 확인은 이 두 줄로 한다:

```bash
# 1) tarball 이 현재 소스와 같은가 (mtime 아니라 **내용 해시**)
python3 src/build_stamp.py check --root . --dist src/dist

# 2) 특정 수정이 tarball **안에** 들어갔는가
tar xOzf src/dist/sei_pilot_cpu.tar.gz sei_pilot_cpu/sei_pilot/criteria/p1.py | grep -n IMAG_WINDOW
```

⚠ `--root` 는 **저장소 루트**다. `--root src` 로 주면 예전에는 *"파일 68개 삭제됨 / tarball
이 낡았다"* 는 **오경보**가 났다(내가 실제로 그렇게 호출해 오경보를 냈다).
**오경보는 진짜 경보를 믿지 않게 만들어 낡은 tarball 보다 더 위험하므로** 고쳤다 —
이제 root 가 틀리면 *"--root 가 잘못됐을 가능성이 크다"* 라고 말한다.

### 새로 추가한 방어
- `TestWrongRootIsNotReportedAsStale` — root 오류를 staleness 로 오보하지 않는가
- `TestM2DecisionReachesTheTarball` — 🔴 **소스에 있는 것이 tarball 안에도 있는가.**
  소스만 보는 검사로는 "lead 가 낡은 추출본을 봤다"는 격차를 잡을 수 없다.
  tarball 을 실제로 풀어서 `IMAG_WINDOW_PROVENANCE` · `r_composite` · `-A` 컬럼 ·
  기저 4벌을 확인한다.

---

## 15. 🔴 미해결 — critic 판정 대기 (인도 전에 닫아야 할 수도 있다)

### 15.1 M2 임계의 **근거 문장이 잘못 서 있다** (숫자가 아니라 논거)

현재 `criteria/p1.py` 에 적힌 내 결정:

> *"창 폭 1,900 cm⁻¹ 는 기저 변경에 따른 허수진동수 크기 변동(통상 수십 cm⁻¹)을
> 충분히 덮는다 ⇒ 재보정 불요"*

🔴 **lead 지적으로 이 논거가 잘못 서 있음이 드러났다.** 폭이 아니라 **경계까지의 거리**가
문제다:
- 상한 −2000 은 여유가 크다. 위험이 **전부 하한 −100 에 몰려 있다.**
- 얕은 TS 에서 SVPD ↔ TZVPPD 차이가 수십 cm⁻¹ 만 나도 −120 → −90 이 되어
  **판정이 뒤집힌다.**
- diffuse 함수 유무는 **라디칼 음이온에서 특히 민감**한데, 우리 계(EC 라디칼 음이온)가
  정확히 그 경우다.

즉 "폭이 넓다"는 상한에 대한 진술이고, **위험이 있는 쪽에 대해서는 아무 말도 하지 않는다.**
숫자는 여전히 맞을 수 있으나 **적어둔 근거는 그 결론을 지지하지 않는다.**

**지금 고치지 않은 이유**: 인도 게이트가 통과한 직후이고, `p1.py` 를 건드리면 tarball 이
다시 움직여 게이트를 재개해야 한다(사용자 회신 1회 = 달력 3.5일). lead 지시도 대기다.

**닫는 방법 2가지** (lead 판정 대기):
1. **critic 판정 후 한 번에 수정** — 기본안. 게이트 안정.
2. **근거 문장만 즉시 교체** — 숫자 불변. `decision` 을 *"관건은 폭이 아니라 하한 −100
   까지의 거리이며, 이 계는 diffuse 민감도가 큰 라디칼 음이온이므로 재보정 필요 여부는
   proposer 판정 사항"* 으로, `recalibrated_for_cheap_basis: False → "pending_proposer"`.
   tarball 재빌드 1회.

🔴 **어느 쪽이든 숫자는 내가 바꾸지 않는다.** 과학적 임계는 proposer 판정 사항이다.

**사후 검증 경로는 이미 패키지 안에 있다**: P1b 가 같은 3종을 G-3(SVPD)/G-1(TZVPPD)
두 기저로 돌린다. 두 기저의 허수진동수 차이가 실측되므로, **"수십 cm⁻¹" 이라는 전제
자체를 회신 데이터로 검증할 수 있다.** 다만 그건 왕복 1회 뒤의 일이다.

### 15.2 실행으로 검증하지 **못한** 것 (critic 이 알아야 한다)

우리 박스에 Gaussian16 도 CP2K 도 없다. 아래는 **형식만 검증했고 실행하지 못했다.**

| 항목 | 검증한 것 | 검증 못 한 것 |
|---|---|---|
| QST2 `.gjf` | 분자 지정 2벌, 좌표 11+11, 기저 블록 위치 | G16 이 **두 번째 분자 지정 뒤의 `gen` 블록**을 받는가 |
| `gen` 기저 | 원소 커버리지, 블록 문법, `****` 구분 | G16 이 실제로 파싱하는가 |
| `%mem` 유도 | 노드 RAM → GB 변환 | galloc 실패가 안 나는가 |
| IRC route | route 문자열 생성 | `irc=(calcfc,forward,maxpoints=30)` 수용 여부 |
| CP2K FIST 입력 | 자리표시자 치환, SPC/E 출판값 | CP2K 가 이 입력을 도는가 |

⇒ **패키지의 `sei_qc_smoke` 가 본계산 전에 H2 로 route 를 실제 검증하고, 실패하면
비용을 쓰지 않고 중단한다.** 위 위험의 상당수는 거기서 잡히도록 설계했지만,
**QST2 의 두 번째 분자 지정 + gen 조합은 H2 스모크가 덮지 않는다**(스모크는 `sp` 다).
critic 이 이 구멍을 어떻게 볼지 듣고 싶다.

---

## 16. critic `FIX-THEN-RUN` 대응 — BLOCKER 2 + MAJOR + MINOR (완료)

### 16.1 B-3 — P1 판정이 Gaussian 로그를 파싱 못 했다 (여덟 번째, 형태는 "부분 이식")

ORCA→G16 전환에서 **IRC 경로는 옮기고 freq 경로는 안 옮겼다.** 결과: P1 이 1,000 core-h 를
태우고 진짜 TS 를 찾아도 회신은 무조건 `fail(no_frequencies_parsed)`.

🔴 **호출부(`collect_p1`)만 고치면 또 부분 이식이 된다.** 그래서 **파서 체인 자체**를 고쳤다 —
`p1.parse_frequencies` 가 `orca → gaussian → generic` 순으로 시도한다. 누가 부르든 먹는다.

**같은 계열 결함을 하나 더 발견했다**: payload 는 TS 로그를 `ts_qst2.log`(또는 폴백 시
`ts_opt.log`)로 남기는데 `collect_p1` 은 **존재하지 않는 `tsopt.log`** 를 찾고 있었다.
⇒ payload 가 남기는 `ts_method.json` 의 `log` 필드를 정본으로 쓰고, 이름 목록은 폴백으로만
둔다. 못 찾으면 `warnings` 에 남긴다(조용히 실패하지 않는다).

### 16.2 B-4 — P2f 가 CP2K 를 절대 못 찾았다
`cp2k_common.sh` 는 `SEI_CP2K` 를 export 하는데 `P2f.sh` 는 **`SEI_CP2K_BIN`**(어디서도
설정되지 않는 이름)을 봤다. ⇒ CP2K 가 있어도 항상 `exit 3`, 회신은 "CP2K 없음"으로
**거짓 보고**. ADR-012 λ_out 착수 판단을 오도한다. 변수명 통일로 수정.

### 16.3 MAJOR (lead 판정) — 폴백 값은 `null` 로 낸다
lead 판정대로 **하드 exit 은 넣지 않았다**(프로브 패키지에서 코어 수 하나 때문에
I/O·큐대기·P1·P3 측정까지 잃는 대가가 더 크다). 대신 **소비자가 읽을 수 없는 형태**로 만들었다:

| 키 | 값 |
|---|---|
| `cluster.cores_per_node` | 🔴 **`null`** (계산 노드에서 온 값만 여기 앉는다) |
| `cluster.cores_per_node_source` | `"probe_node (계산 노드에서 실행)"` 등, 미확정이면 `null` |
| `cluster.cores_per_node_login_fallback` | `24` — 버리지 않고 **다른 키에** 보존 |
| `cluster.cores_per_node_note` | *"의도적으로 null 이다 … 이 값으로 봉투를 계산하지 마라"* |
| `unresolved_for_lead[]` | `severity: blocker`, ADR-034 사고를 근거로 명시 |

**경고 문자열은 사람만 읽는다. `null` 은 코드도 읽는다.**

### 16.4 MINOR — 죽은 CP2K 코드 정리
`sei_cp2k_input` / `sei_spin_series` / `sei_cp2k_smoke` 제거. `cp2k_common.sh` 는 이제
`sei_cp2k_detect` + `sei_cp2k_launcher` 둘뿐이다(46 → 32줄).

🔴 **정리 중에 알게 된 것**: `sei_cp2k_smoke` 는 **이미 지워진** `sei_cp2k_input` 과
**이미 지워진** `inputs/electrolyte_box.xyz` 를 부르고 있었다 — **도달 불가라
표면화되지 않았을 뿐 이미 깨져 있었다.** critic 의 *"나중에 재사용되면 깨진다"* 는
가정법이 아니라 이미 사실이었다.

### 16.5 회귀 테스트 — **경로를 실행한다** (critic 구속)
`tests/test_integration_paths.py` (19건). 테스트를 늘린 게 아니라 **통합 경로를 통과**시킨다.

1. **Gaussian 로그 원문 → `collect_p1` → `evaluate_p1` → status** 전 구간
   (`test_criteria.py` 는 ORCA 픽스처만 있어 이 경로가 한 번도 실행된 적이 없었다)
2. **목 `cp2k` 를 PATH 에 놓고 `P2f.sh` 를 실제 실행** — 🔴 **양성 대조군**.
   음성 대조군(PATH 비움 → `exit 3`)도 함께 둔다. 이게 없으면 "CP2K 가 없다"와
   "탐지 로직이 깨졌다"를 구별할 수 없다.
3. **폴백 → `null` 규칙**

**🔴 수정 전 코드로 되돌려 실제로 FAIL 하는지 확인했다: 19건 중 12건 FAIL.**
(파서 3 · P2f 4 · null 규칙 5) 통과가 곧 정확성이 아니라는 것을 두 번 확인했으므로,
이제 회귀 테스트는 **반드시 수정 전 코드에서 깨지는 것까지 확인**하고 보고한다.

### 16.6 상태
`539 tests OK` (skipped 8) · `[stamp] ✅` · CPU 19 M / GPU 140 K · 예약 2,948 / 5,000 core-h

### 16.7 손대지 않은 것
🔴 **M2 (b) 는 지시대로 건드리지 않았다.** §15.1 에 논거의 결함(폭이 아니라 하한 −100 까지의
거리가 관건)을 기록해 뒀다. **proposer 판정 사항이다.**

---

## 17. P2f 제거 + U-27 NonEq 스모크 (인도 직전 2건)

### 17.1 ① P2f / CP2K 층 **완전 제거**
근거 둘(독립): proposer §30 이 λ_out 을 고전 MD 대신 **G16 비평형 PCM** 으로 얻는 경로를
찾아 소비자가 사라졌고, 남은 값(가용성)은 `probe_node` 가 이미 회신에 싣는다.

**지운 것**: `payload/P2f.sh`, `payload/cp2k_common.sh`(파일째),
`inputs/cp2k_fist.inp.tmpl`, `inputs/water_box.xyz`(+meta), `tools/make_water_box.py`,
`plan.py` 의 P2f 항목과 `CP2K_CODES`, `config/accounts.json` 의 `cp2k` 계정,
`collect.collect_p2f`, 관련 테스트(물상자·FIST·목 cp2k 실행 12건).

🟢 **결과: 패키지의 계산 코드가 Gaussian16 + xtb 둘뿐이다** — 사용자 요구 그대로다.
예약 2,948 → **2,900 core-h**.

**🔴 되살릴 때 필요한 것** (CP2K 는 축 3 DFT MD 폴백에서 다시 필요해질 수 있다,
proposer §27.3c):
1. **가용성 보고는 지우지 않았다.** `sysprobe.SOFTWARE_TARGETS` 의 `cp2k`/`cp2k.psmp`/
   `cp2k.popt` 와 `probe_node.sh` 의 탐지는 그대로다. 테스트도 그 예외를 명시한다
   (`test_cp2k_layer_is_fully_removed` 가 `probe_*` 를 제외한다).
2. **목(mock) cp2k 바이너리**로 만든 양성 대조군 테스트를 지웠다. 되살릴 때는
   `git` 이력이 없으므로 이 문단의 방식을 다시 쓰라 — 목이 `-i/-o` 를 파싱해
   `MD| Step number` 와 `PROGRAM ENDED AT` 을 뱉으면 된다. **양성 대조군 없이는
   "CP2K 가 없다"와 "탐지 로직이 깨졌다"를 구별할 수 없다**(B-4 가 그래서 살아남았다).
3. FIST 입력은 SPC/E(Berendsen 1987) 출판값이었다. 전해질 고전 力場은 **없었고,
   되살린다면 파라미터 출처를 먼저 정해야 한다 — 지어내면 안 된다.**

### 17.2 ② U-27 — G16 `NonEq` 스모크 (P1b 에 1건)
**재는 것은 λ_out 값이 아니라 "이 루트가 도는가"다.** 회신 `p1b.u27_noneq`:
`route_accepted` · `nonequilibrium_supported` · `solvent_model_used`(smd|iefpcm|null) ·
`smd_worked` · `iefpcm_fallback_needed` · `routes{step1,2,3}` · `failed_at_step` ·
`g16_excerpt`(마지막 15줄) · `lambda_out_hartree_indicative`(**참고용**, `_value_caveat` 동봉).

- SMD 실패 시 **IEFPCM 폴백을 자동 시도**하고 어느 쪽이 통했는지 남긴다.
- 실패해도 P1b 를 죽이지 않는다 → 수집부가 `undetermined` 로 받는다(`fail` 아니다).
- **λ_out 본계산은 구현하지 않았다.** S1 파이프라인이고 착수 금지다.
- core-h 증가: 최적화 1 + 단일점 2 (10원자). **예산 700 유지, 보고 불요 수준.**

**🔴 lead 지시와 다르게 한 것 1건 — 대상 종 선택**
지시는 *"P1b 가 이미 쓰는 종 중 **가장 작은 것**"* 이었다. 그런데 P1b 의 3종은
`hco3_anion(−1)` · `li_ec_cation(+1)` · `li_ec2_cation(+1)` 로 **하나도 중성이 아니다.**
절차가 "중성 N → 환원종 R" 이므로 음이온을 또 환원하면 **−2** 가 되어 무의미하다.
더 작은 중성종(`h2o`, `co2`)이 있으나 **H2O⁻ 는 결합하지 않는다** — SCF 가 발산하면
우리는 "NonEq 가 안 된다"고 **잘못 결론**낸다. **측정하려는 것과 다른 이유로 실패하는 것**이다.

⇒ **`ec`(10원자, 중성, 닫힌껍질)** 를 쓴다. EC 라디칼 음이온은 이 프로젝트의 실제
대상이고 결합 상태가 알려져 있다. 새 입력 파일은 만들지 않았다(이미 동봉된 종이다).
선택은 `manifest.json` 의 **`u27_reference` 플래그 한 곳**에서 오므로 바꾸려면 그것만 옮기면 된다.

⚠ 환원종 다중도는 닫힌껍질↔이중항 뒤집기로 **가정**했다. 틀리면 SCF 가 수렴하지 않고,
그 사실도 회신에 남는다(우리가 값을 고르지 않는다).

### 17.3 회귀 테스트 — 경로 실행 (critic 구속)
`tests/test_u27_noneq.py` (16건). 목(mock) `g16` 을 PATH 에 놓고 **`P1b.sh` 를 끝까지 실행**한다.
🔴 **대조군 3종**:

| 목 모드 | 무엇을 확인하나 |
|---|---|
| `accepting` | SMD+NonEq 가 되는 경우 — route 3개가 기록되는가, 본래 5수가 밀려나지 않았는가 |
| `rejecting` | SMD+NonEq 만 거부 → **IEFPCM 폴백이 실제로 도는가**, 그 사실이 회신에 남는가 |
| `hostile` | 어떤 NonEq 도 거부 → 🔴 **U-27 실패가 P1b 를 죽이지 않는가**, 실패 지점·G16 원문이 남는가 |

하나만 두면 "되는 것"과 "탐지 로직이 늘 참을 돌려주는 것"을 구별할 수 없다.

### 17.4 상태
`542 tests OK` (skipped 8) · `[stamp] ✅` · CPU 19 M / GPU 136 K · 예약 **2,900 / 5,000 core-h**

---

## 18. ① 정정 — P2f 제거 → **P2g 신설** (xtb GFN-FF 주기계)

CP2K 관련은 §17.1 대로 전부 제거된 상태 그대로다. 그 자리에 **P2g**(엔진: 동봉 xtb,
계정 `etc`, 예산 20 core-h)를 세웠다. 예약 합계 **2,920 / 5,000 core-h** — 가드 안.

### 18.1 🔴 V1 을 **우리 박스에서 직접 돌렸다.** 답이 나왔다 — 그리고 한 번 틀렸다

| 단계 | 결과 |
|---|---|
| 1차 (같은 디렉터리에서 연속 실행) | 셀 10 % 이상 이동 시 **591 eV** 편차 → "Issue #1118 재현" |
| 2차 (**독립 디렉터리로 격리**) | 편차 **4.2e-5 Eh = 1.6e-7 Eh/atom** → **불변이다** |

🔴 **1차는 xtb 의 결함이 아니라 우리 것이었다.** xtb 는 GFN-FF 토폴로지를 `gfnff_topo` 에
캐시하고 다음 실행에서 재사용한다. 모든 이동을 같은 디렉터리에서 돌리면 2회차부터
**1회차의 토폴로지가 이동된 좌표에 적용**되어 가짜 편차가 나온다.

⇒ **하마터면 "(A) 경로가 깨졌다"는 가짜 BLOCKER 를 회신할 뻔했다.** 그 함정을 세 곳에 박았다:
`config/p2g.json`의 `_cache_pitfall`, `tools/p2g_v1.py` 주석, `test_p2g.py`의
`TestShiftsAreIsolated`(격리 코드가 사라지면 실패).

**부수 확인 2건** (둘 다 회신 JSON에 실린다):
- xtb 는 셀 밖 좌표를 랩한 **뒤** 토폴로지를 만든다 → 경계를 가로지르는 분자가 조각난다
  (물 분자가 17.01/1.01 amu 로 갈라지는 것을 직접 봤다). **입력 좌표는 셀 안에 두어야 한다.**
- xtb 6.7.1 은 주기계 GFN-FF 단일점에서 에너지를 정상 생성하고도
  `gfnff_setup: Could not read topology file` 경고와 함께 **normal-termination 배너를 안 찍는다.**
  배너로 성패를 판정하면 멀쩡한 결과를 전부 버린다 → 판정 기준을 "에너지 생성 + abnormal 없음"으로.

**허용오차는 원자당(1e-6 Eh/atom)으로 잡았다.** 총량 기준은 큰 상자를 자동으로 실패시킨다.
🔴 **데이터를 보고 문턱을 맞추지 않았다** — MD 에너지 보존에서 통상 쓰는 1e-5 Eh/atom 보다
10배 엄격하게 두었고, 실측(1.6e-7)은 그보다 두 자릿수 아래다.

### 18.2 V2 — Li–O RDF
`v2_li_o_rdf_first_peak_ang` · `v2_coordination_number` · 궤적 길이 · 버린 완화 구간 · core-h.
RDF 규격화는 **해석해로 검증**했다(균일 분포에서 g(r)→1, CN=(4/3)πr³ρ). 규격화가 틀리면
봉우리는 맞아도 **배위수가 조용히 틀리고**, 배위수는 proposer 판정의 입력이다.

**실측 비용**: 개발 박스에서 270원자 EC 상자 1 ps = **533 s(1 core)** → 50 ps ≈ **7.4 core-h**.
예산 20 core-h 는 2.7배 여유다. 🔴 **가드 안이며 lead 보고 불요 수준이다.**

### 18.3 🔴 lead 확인 요망 — V2 조성은 **내가 정했다**
사양은 "Li+(EC)₄ 액체"였는데 **주기계 셀의 전하 중성**을 어떻게 맞출지가 지시에 없었다.
① PF6⁻ 대이온 / ② 전하 있는 셀 + 보정 배경 / ③ 비주기 클러스터 중 **①**을 골랐다.
- ②는 GFN-FF 주기계에서 검증되지 않았고, ③은 "액체"가 아니라 클러스터라 RDF 의 의미가 달라진다.
- ①은 LiPF6/EC 로 **실제 전해질**이고 두 종 모두 이미 동봉돼 있다(새 입력 없음).
- 조성: Li 4 + PF6 4 + EC 16 = 192원자, 셀 13.54 Å, EC:Li = 4:1, 총전하 0.

**막고 물으면 왕복 1회(3.5일)를 쓰기 때문에 진행했다.** 결정은 `config/p2g.json` 의
`composition._decision` 한 곳에 있으니 뒤집으려면 그것만 고치면 된다.

### 18.4 상태
`566 tests OK` (skipped 8) · `[stamp] ✅` · CPU 19 M / GPU 148 K · 예약 **2,920 / 5,000 core-h**
P2g 전 경로(상자 생성 → V1 → MD → RDF)를 짧은 MD(0.5 ps)로 **실제 실행해 확인**했다.

---

## 19. 최종 정리 — P2g 는 패키지 밖으로, V1 은 실행 완료

### 19.1 패키지 최종 상태
정본 지시대로 맞췄다. **패키지에 남은 변경은 ①CP2K 제거 ②U-27 스모크 둘뿐이다.**

```
plan(cpu) = probe_node, probe_throughput, probe_queuewait, P3, P1, P5, P1b
tarball 안 P2g 흔적: 0
542 tests OK (skipped 8)   [stamp] ✅   CPU 19 M / GPU 136 K
예약 2,900 / 5,000 core-h
```

**P2g 자산은 지우지 않고 옮겼다** → `src/experiments/p2g/`
(`make_ec_box.py`, `p2g_boxes.py`, `p2g_v1.py`, `p2g_v2.py`, `inputs/`, `p2g.json`,
`P2g.sh.reference`, `test_p2g_experiment.py`, `run_v1.sh`).
경로를 보정해 **패키지 밖에서 그대로 돌아간다**(`./run_v1.sh` 로 재현).

### 19.2 ③ V1 — **실행 완료. 결과는 `src/experiments/p2g/FINDING_V1.md`**

| shift | ΔE (Eh) | ΔE (kcal/mol) | #bonds |
|---|---|---|---|
| 0.02 / 0.05 | 0 | 0 | 324 |
| 0.10 | 2.161e−05 | 1.356e−02 | 324 |
| 0.25 | 3.170e−06 | 1.989e−03 | 324 |
| 0.50 | 4.188e−05 | 2.628e−02 | 324 |

**최대 4.188e−05 Eh = 0.0263 kcal/mol = 1.55e−07 Eh/atom** (270원자 / 27 EC / 14.40 Å).
결합 수는 전 구간 324 로 동일 — **토폴로지가 위치에 따라 바뀌지 않았다.**

🔴 **판정하지 않는다.** 0.026 kcal/mol 이 허용 가능한지, 이것이 Issue #1118 의 MD drift 와
같은 현상인지는 proposer 몫이다. 우리가 잰 것은 **단일점 설정의 불변성**이지 MD drift 가 아니다.

🔴 **1차에서 591 eV 짜리 가짜 편차가 나왔다.** xtb 가 `gfnff_topo` 를 캐시·재사용하는데
모든 이동을 같은 디렉터리에서 돌렸기 때문이다. 격리 후 4.2e−05 로 떨어졌다.
**"(A) 경로가 깨졌다"는 가짜 BLOCKER 를 회신할 뻔했다.**

**부수 관찰 2건** — 둘 다 본 파이프라인에서 xtb 주기계를 쓸 때 필요하다:
1. xtb 는 셀 밖 좌표를 **랩한 뒤** 토폴로지를 만든다 → 경계를 가로지르는 분자가 조각난다
   (물이 17.01/1.01 amu 로 갈라지는 것을 봤다). **입력 좌표는 셀 안에 두어야 한다.**
2. xtb 6.7.1 은 주기계 GFN-FF SP 에서 에너지를 정상 생성하고도 normal-termination 배너를
   찍지 않는다. **배너로 판정하면 멀쩡한 결과를 전부 버린다.**

**V2 는 시작하지 않았다** — engineer 가 1,000~3,000원자를 요구했고 규모 결정은 lead 대기다.

---

## 20. 실클러스터 dry-run 실패 대응 (PBS 거부 4/4 + Gaussian 미탐지)

🔴 **우리 박스에는 PBS 도 Gaussian 도 없다. 아래 전부 `[UNVERIFIED — 사용자 클러스터에서만
확인 가능]` 이다.** 여기서 검증한 것은 **생성되는 텍스트의 형태**뿐이다.

### 20.1 진단 능력부터 — 우리는 원인을 **볼 수 없는 상태**였다
🔴 `format_feasibility` 가 거부 메시지를 `splitlines()[0][:66]` 으로 **첫 줄 66자만** 찍고
있었다. 그래서 `...encountere...` 에서 끊겼고 **원인은 잘려나간 뒷부분에 있었다.**
- 이제 **자르지 않고 접는다**(`_wrap`). 여러 줄도 전부 보존한다.
- 항목 키를 함께 찍고, *"전문을 그대로 회신해 주세요"* 안내를 붙였다.
- **`--emit-script <항목>`** 신설 — 제출될 `.qsub` **전문 + `.cmd.sh`** 를 그대로 출력한다.
  🔴 **제출과 같은 `build_spec()` 을 쓴다.** 별도 경로로 만들면 사용자가 보는 스크립트와
  실제 제출본이 달라지고, 그건 디버깅 자체가 거짓말이 되는 최악의 형태다.

### 20.2 PBS 스크립트를 **사용자 정본에 맞췄다**
| # | 항목 | 이전 | 지금 |
|---|---|---|---|
| 1 | shebang | `/bin/bash` | **`/bin/sh`** (정본과 동일) |
| 2 | `#PBS -V` | 없음 | **추가** |
| 3 | 지시어 순서 | -N, 자원, walltime, -o/-e, -q, -A | **-V, -N, -q, -A, select, walltime** (정본 순서) |
| 4 | `-o`/`-e` | 절대경로로 항상 출력 | **기본 생략**. 켜면 `$PBS_O_WORKDIR` 기준 상대경로 |
| 5 | 지시어 블록의 빈 줄 | 선택 지시어가 빈 줄로 남음 | **제거**(`squeeze_directive_blanks`) |
| 6 | `ncpus` | 감지값 고정 | `config/sizing.json` + **`--ncpus-per-node`** |
| 7 | `probe_queuewait` | 최대 85노드 | **상한 16**(`pbs.max_probe_nodes`), 축소 사실을 회신에 기록 |

🔴 **#5 가 중요할 수 있다**: PBS 는 **첫 비지시어 줄에서 지시어 파싱을 멈춘다.** 우리는
선택적 지시어를 빈 문자열로 치환했으므로 헤더 한가운데 빈 줄이 생겼고, **그 뒤의 `#PBS`
줄들이 통째로 무시됐을 수 있다.** 4건 *전부* 거부된 계통적 원인의 후보다.
(추측이다 — 확정은 `--emit-script` 회신으로 한다.)

### 20.3 Gaussian: `module load` 경로 추가
- `envpaths.resolve_qc_via_module()` — `module avail` 후보를 **실제로 `module load` 해 보고**
  `command -v g16` 이 나타나는지 확인한다. 이름이 목록에 있다는 것만으로는 부족하다.
- 🔴 **찾으면 잡 스크립트가 계산 노드에서 그 모듈을 실제로 load 한다**
  (`JobSpec.modules` → 템플릿 `MODULE_LINES`). **로그인 노드에서 찾아 놓고 계산 노드에서
  안 부르면 또 조용히 실패한다.** `module load` 실패는 잡을 죽이지 않는다(`|| echo`).
- 못 찾으면 SKIP 유지하되 사유에 **시도한 모듈 목록 + `module avail` 에 보인 QC 후보**를
  싣는다. 지금까지는 "없음"만 와서 **다음에 무엇을 물어야 할지 알 수 없었다.**

### 20.4 회귀 테스트 — 여기서 검증 가능한 것만 (`tests/test_pbs_script_shape.py`, 15건)
정본과의 **형태 비교**를 고정한다: shebang / `-V` / 지시어 순서 / `select` 형태 /
`-o`·`-e` 부재 / **지시어 블록에 빈 줄 없음** / `cd $PBS_O_WORKDIR` / module 블록 /
module 실패가 잡을 안 죽임 / **거부 메시지가 잘리지 않고 접히는가**(접힘 복원 후 토큰 검사).

### 20.5 상태
`561 tests OK` (skipped 8) · `[stamp] ✅` · CPU 19 M / GPU 140 K
🔴 **동결 해제 상태다. 이 수정판이 이전 인도판(`b59ccf60…`)을 대체한다.**

---

## 21. critic2 긴급 리뷰 대응 (결함 4건 + 내가 추가로 찾은 1건)

### 21.1 🔴 [치명] `to_dict()` 의 400자 컷 — **이번 라운드의 수정이 무효였다**
화면 출력(`format_feasibility`)의 66자 컷은 고쳤는데, **실제 파이프라인이 지나는**
`SubmissionCheck.to_dict()` 가 `message[:400]` 으로 여전히 잘랐다.
`submission_feasibility() → to_dict() → format_feasibility()` 순서라 400자 컷을 그대로 통과한다.

⇒ 절단을 **없앴다.** 크기가 궁금하면 `message_bytes` 로 본다.

🔴 **왜 못 잡았나**: 내 테스트 3건이 `feas` 딕셔너리를 **손으로 만들어** `to_dict()` 를 아예
거치지 않았다. **실제 경로가 커버리지에서 빠져 있었다** — B-3(부분 이식) 때와 같은 형태다.
`TestRealPathDoesNotTruncate` 가 이제 `to_dict()` 를 반드시 지난다.

### 21.2 🔴 [치명] `--emit-script` 가 `--level` 을 무시
`cmd_submit` 은 `SEI_QC_LEVEL` 을 넣고 `cmd_emit_script` 는 자기 딕셔너리를 만들어 안 넣었다.
**같은 `build_spec()` 을 써도 입력이 다르면 출력이 갈린다.** §20.1 에서 내가 한
*"디버깅이 거짓말이 되지 않는다"* 는 주장이 정확히 여기서 깨졌다.

⇒ `build_common_env(args, store, part)` 로 조립을 **한 곳에** 모았다. 키를 추가할 때도
한 곳만 고치면 된다(critic2 가 요청한 재발 방지 형태).
실물 tarball 검증: `--level g2` → `export SEI_QC_LEVEL="1"` 이 emit-script 출력에 나온다.

### 21.3 🔴 내가 추가로 찾은 것 — **사전검사가 실제 제출과 다른 스크립트를 검사했다**
`submission_feasibility()` 가 자기만의 `JobSpec` 을 만들고 있었다 → module 블록 없음,
`--ncpus-per-node` 미반영, `SEI_QC_LEVEL` 없음.
**사전검사가 통과해도 실제 제출이 거부될 수 있고, 그러면 사전검사의 존재 이유가 사라진다.**
critic2 가 `--emit-script` 에서 찾은 것과 **같은 결함의 더 큰 판**이다.
⇒ `build_spec()` 을 쓰게 고쳤다. 이제 제출·사전검사·emit-script 셋이 같은 조립을 쓴다.

### 21.4 [중대] 죽은 설정 키
`pbs.ncpus_per_node` / `pbs.emit_stdio_lines` 를 **아무도 읽지 않았다.** JSON 주석은 "여기
넣거나 플래그로 덮으라"고 했는데 거짓이었다 — 사용자가 JSON 을 고쳐도 조용히 무시되고
같은 이유로 또 거부됐을 것이다.
⇒ `build_spec` 이 읽는다. **우선순위: `--ncpus-per-node` > JSON > 감지값.** 주석도 정정했다.
🔴 **기본값은 그대로 두었다**(감지값 64). 32 가 사이트 제한인지 그 잡의 사정인지 모른다(lead 지시).

### 21.5 [중대] 인용한 "정본"과 실제 템플릿이 달랐다
테스트 docstring 이 인용한 정본은 `-V, -q, -N, -A, ...` 인데 템플릿은 `-N` 이 `-q` 보다 앞이었고,
순서 테스트가 그 상대순서를 검사하지 않았다.
⇒ 템플릿을 **정본 순서로** 맞추고, 테스트가 **6개 지시어 순서 전체**를 못박게 했다.
critic2 판단대로 이것이 4/4 거부의 원인일 가능성은 낮다 — 다만 **"정본과 같다"는 주장은
사실이어야 한다.** 테스트가 인용문과 어긋나면 그 인용문은 문서가 아니라 장식이다.

### 21.6 상태
`570 tests OK` (skipped 8) · `[stamp] ✅` · CPU 19 M / GPU 141 K
**sha256: cpu `8b231ede06f3` / gpu `8d9af9f37878`**
🔴 이 해시가 `a280de540dd3` 을 대체한다.

---

## 22. critic2 요구 테스트 형태 충족 + `-A etc` 대조 실험 지원

§21 에서 결함 4건은 이미 고쳤다. lead 가 명시한 **두 테스트 형태**가 아직 그 모양이
아니어서 채웠다.

### 22.1 전 구간 테스트 — `submission_feasibility()` **부터** 화면까지
이전 테스트는 `feas` 딕셔너리를 손으로 만들거나 `to_dict()` 만 따로 불렀다.
**`submission_feasibility()` 안에서 일어나는 일을 전혀 지나지 않았다** — 컴포넌트는
고쳤는데 경로를 안 탄 B-3 과 같은 형태(세 번째 반복).

`TestFullPathFromFeasibilityToScreen` 이 가짜 어댑터로 **535자 거부 메시지**를 흘려보내
`submission_feasibility → to_dict → format_feasibility → 화면` 전 구간에서 꼬리가
살아남는지 본다. (`test_message_is_longer_than_the_old_400_char_cut` 이 픽스처가 400자를
넘는지도 함께 지킨다 — 안 넘으면 이 테스트가 예전 버그를 못 잡는다.)

### 22.2 "제출본 ≡ emit 출력" 문자열 고정
`TestEmitScriptIsByteIdenticalToSubmission` — 두 경로가 같은 재료로 만든 스크립트가
**바이트 동일**한지, `--level g2` 가 실제로 스크립트를 바꾸는지(안 바뀌면 위 검사가
무의미하다) 함께 본다.

### 22.3 🔴 수정 전 코드로 되돌려 **7건이 실제로 깨지는 것**을 확인했다
```
to_dict 400자 컷 복원      → 3건 FAIL (전 구간 2 + to_dict 1)
SEI_QC_LEVEL 제거 복원      → 4건 FAIL/ERROR
```
통과가 곧 정확성이 아니므로, 이제 회귀 테스트는 **수정 전 코드에서 깨지는 것까지 확인**하고
보고한다.

### 22.4 lead 의 `-A etc` 가설 — 대조를 한 줄로 할 수 있게 했다
계정 변경은 이미 두 형태로 된다(확인 완료):
- `config/accounts.json` **한 곳** (probe/xtb → `etc`, gaussian → `gaussian`, vasp → `vasp`)
- CLI: `--account probe=vasp`(소프트웨어별) / `--account vasp`(전역)

README 에 **대조 실험 절차**를 넣었다:
```bash
./run.sh --dry-run                    # 현재 매핑
./run.sh --dry-run --account vasp     # 전 항목을 -A vasp 로
```
🟢 **§21.3 수정 덕분에 이 대조가 의미를 갖는다** — 사전검사가 이제 **실제 제출과 완전히
같은 스크립트**를 검사하므로, 두 dry-run 의 차이가 곧 실제 제출의 차이다.
(고치기 전이었다면 사전검사는 module 도 ncpus 도 다른 스크립트를 검사했을 것이다.)

### 22.5 상태
`579 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `2dd32cadac25` / gpu `c18941afbc04`** ← `8b231ede06f3` 을 대체

---

## 23. critic2 BLOCK 대응 — `#PBS -q` 누락

### 23.1 결함
`env["partitions"]` 는 **`sinfo` 로만** 채워지는데(`sysprobe.py:432`) `sinfo` 는 **SLURM 전용**이다.
대상은 PBS 전용 클러스터 → 항상 `[]` → `default_partition()` 이 `None` →
**모든 제출 스크립트에서 `#PBS -q` 가 통째로 빠졌다.** 사용자 정본에는 `#PBS -q normal` 이 있다.
그리고 `--emit-script` 는 자기 폴백 때문에 `-q normal` 을 **보여주고 있었다** —
§20.1 에서 내가 "최악의 형태"라 부른 그 실패가 이번 수정판에도 남아 있었다.

재현(우리 박스):
```
PBS(sinfo 없음): default_partition() -> None      /  emit 폴백 -> 'normal'
partition=None    -> #PBS  -V  -N  -A  -l  -l     ← -q 없음
partition='normal'-> #PBS  -V  -q  -N  -A  -l  -l
```

### 23.2 수정 (critic 제안 그대로)
1. **`cmd_emit_script` 가 `default_partition()` 을 쓴다** — 호출부를 하나로.
2. **`resolve_partition(env, args)` 신설** — `--partition > --queue > sinfo > config 의
   `queue_default`(사용자 확인값) 순. 🔴 **`None` 을 쉽게 내주지 않는다.**
   그래도 못 정하면 **조용히 지시어를 빼지 않고 크게 경고한다**(그게 이번 사고의 형태였다).
   화면에 **큐 출처**도 함께 표시한다.
3. **`cmd_emit_script(args, shell=None, store=None, env=None)`** — 주입 가능하게.
   **테스트가 불가능한 구조 자체가 결함이다.**

### 23.3 🔴 동일성 테스트를 진짜 진입점 호출로 다시 썼다 — 그리고 **두 번 틀렸다**
lead 지적대로 이전 판은 `build_spec(..., "normal", ...)` 로 두 "경로"에 큐를 **하드코딩**해
같은 함수를 두 번 부르는 **항등식**이었다. 새 판은 `cmd_submit` / `cmd_emit_script` 를
**실제로 호출**하고, args 도 **진짜 argparse 파서**로 만든다(손으로 채우면 기본값이 진짜와
달라져 "내가 상상한 CLI"를 검증하게 된다).

🔴 **그런데 첫 시도에서 새 클래스를 기존 클래스와 **같은 이름**으로 추가해, 파일 뒤쪽의
낡은 정의가 새 판을 통째로 덮었다. 새 테스트는 한 번도 실행되지 않았다.**
되돌린 코드에서도 33건이 전부 통과해 그 사실이 드러났다.
⇒ **"수정 전 코드에서 깨지는가"를 확인하지 않았다면 이 테스트는 영원히 장식이었을 것이다.**
지금은 되돌리면 **3건이 정확히 깨진다**(`-q` 누락 / 두 경로 불일치 / 지시어 블록 불일치).

### 23.4 상태
`581 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `acd51c64359b` / gpu `a6d9b5bce546`** ← `2dd32cadac25` 를 대체
🔴 실물 tarball 확인: PBS(sinfo 없음)에서 `('normal', 'config/accounts.json 의 queue_default')`

### 23.5 지시대로 **건드리지 않은 것**
`-A` 계정 매핑(세 진입점 모두 `resolve_account` 단일 소스, `etc` 유효성 미확정) ·
`ncpus` 기본값 64 · V1b.

---

## 24. critic2 잔해 2건 정리 + 중복 정의 구조적 차단

### 24.1 잔해 ① — 중복 클래스 정의 (내 슬라이스 편집이 만든 것)
`tests/test_pbs_script_shape.py` 에 `TestFullPathFromFeasibilityToScreen` 이 301행·530행
**두 번** 정의돼 있었다(바이트 동일). 뒤 정의가 앞을 덮어 앞쪽은 죽은 코드였다.
**지금은 내용이 같아 커버리지 손실이 없어서 더 위험했다** — 다음에 한쪽만 고치면 그 순간 재발한다.
⇒ 제거. **tests/ 는 패키지에 포함되지 않으므로 이 작업으로 해시가 바뀌지 않았다**(확인함).

### 24.2 잔해 ② — 죽은 `partition_warning()` + 인라인 중복
정의만 있고 호출처 0이었고, **실제로 화면에 뜨던 것은 `format_feasibility()` 안의 인라인
사본**이었다. 게다가 두 문구가 미묘하게 달랐다
(`-q 가 들어가지 않습니다` vs `-q 가 없습니다`) — 나중에 한쪽만 고치면 **어느 쪽이 사용자에게
보이는지 알 수 없어진다.** `envpaths.py` 가 "같은 유형 5번째"라 부른 그 패턴이다.
⇒ 문구를 소유하는 `partition_warning_lines()` **하나만** 남기고 인라인은 그것을 호출한다.
판정(`value is None`)은 호출부가 한다. 래퍼도 지웠다 — 지시대로 **하나만** 남겼다.

### 24.3 🔴 중복 정의를 **구조적으로** 차단 (lead 지시)
`ast` 로 **`tests/` 와 `sei_pilot/` 양쪽**의 top-level 클래스·함수, 그리고 클래스 내
메서드 중복을 검사한다. 한 라운드에 두 번 난 사고라 사람 눈에 맡기지 않는다.

**`[양성 대조 — 내가 주입한 것]`** 셋 다 실제로 잡는 것을 확인했다.
🔴 **아래 세 줄은 발견 목록이 아니다. 스캐너가 동작하는지 보려고 내가 일부러 넣은 중복이다.**
```
[양성 대조 — 주입] 클래스 중복(tests)  → {'test_pbs_script_shape.py': ['TestOptionalPieces']}
[양성 대조 — 주입] 메서드 중복(tests)  → {'...::TestMatchesUserCanonicalForm': [...]}
[양성 대조 — 주입] 함수 중복(제품 코드) → {'sei_pilot/units.py': ['core_hours']}
```
⚠ 이 표기가 없던 판을 lead 가 **발견 목록으로 오독**해 critic 에 `units.py` 최우선 조사를
지시했다. **형태가 틀리기 쉬웠다** — 앞으로 대조군 출력에는 항상 이 라벨을 붙인다.
`test_scan_covers_both_trees` 가 **검사 대상이 두 트리를 실제로 덮는지** 자체를 지킨다.

🔴 **검증 중에 이 실패 모드를 한 번 더 밟았다.** 처음에는 가드 클래스 **자신**을 중복시켜
시험했는데, 그러면 **가드가 스스로를 덮어 사라져서** 아무 실패도 안 났다.
"검사가 없어졌는데 통과" — 이번 사고와 똑같은 형태다. 다른 클래스로 다시 해서 확인했다.

### 24.4 상태
`585 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `e4b0504cd0f8` / gpu `c8760f04b120`** ← `acd51c64359b` 를 대체

### 24.5 지시대로 건드리지 않은 것
`-A` 매핑 · `ncpus` 64 · V1b. 범위를 넓히지 않았다.

---

## 25. core-h 정의 일원화 + `probe_queuewait` 사전검사 정합 + 대조군 질문 답변

### 25.1 ② critic 질문에 대한 답 — **실제 추적 파일을 편집했다. 빌드는 없었다.**
```
cp sei_pilot/units.py /tmp/u.keep                          # 백업
printf '\n\ndef core_hours(a, b):\n    return 0\n' >> ...   # 실제 파일에 주입
python3 -m unittest ...  → AssertionError (스캔이 잡음)
cp /tmp/u.keep sei_pilot/units.py                          # 즉시 복원
```
- **스크래치 사본이 아니라 추적 파일을 편집했다.** `sei_pilot/` 경로가 실제로 스캔되는지
  보려면 제품 파일이어야 했다.
- 🔴 **그 창(window) 동안 빌드도 스탬프도 없었다.** 순서:
  `주입 → 스캔 확인 → 복원 → 전체 테스트 → make_package.sh`. 빌드는 복원 **뒤**다.
- 검증: 현재 소스·tarball 모두 `core_hours` 중복 없음(AST), tarball ≡ 소스(sha256 일치),
  `core_hours(64,3600)=64.0`. **중복 스캔이 통과한다는 것이 곧 부재의 증거다.**
- ⇒ **어떤 tarball 에도 들어간 적 없고, 어떤 core-h 도 그 스텁으로 계산된 적 없다.**

### 25.2 ① `plan.py` 의 core-h 우회 계산 일원화
`size_job()` 과 array 특례가 `total_cores * wall * links` / `n_tasks * 1 * wall` 을
**자기가 계산**했다. 그 값이 `guard.reserve()` → 5,000 가드 판정과 화면의 "예약 core-h"
전부의 근원이다. 반면 `budget.record_measured()` 는 `units.core_hours()` 를 부른다 —
**계획값과 실측값이 다른 경로**였다.

**`units.core_hours_h(n_cores, wall_hours)` 를 유일한 정의로 두고 초 단위판이 그것을 호출**하게 했다.
🔴 **시간 단위판을 새로 만든 이유**: `plan.py` 는 wall 을 시간으로 들고 있어 초 API 만 쓰면
`wall*3600*(1/3600)` 왕복이 생겨 마지막 비트가 달라진다. 그러면 "계획값 == 실측값" 검사가
부동소수 문제로 흔들린다. (critic 은 `units.core_hours()` 호출을 제안했는데, 그대로 하면
왕복이 생긴다 — **의도는 같고 방법만 바꿨다.**)

🟢 **값 불변 확인** (critic 3케이스): `500.0` / `1008.0`(63링크) / array `5.0`.
`test_plan_does_not_compute_core_hours_itself` 가 정적으로 재발을 막는다.

⚠ 내 테스트 케이스 하나에서 **내가 기대값을 틀렸다**: 60 core-h / 256코어는 wall 하한
(`MIN_WALL_H=0.25`)에 걸려 예약이 **64** 가 된다. **코드가 맞았고 내가 틀렸다** —
코드를 기대에 맞추지 않고 기대를 고쳤다. 주석에 남겼다.

### 25.3 ②(추가) `probe_queuewait` — **실제 제출은 16노드, 그러나 사전검사는 85였다**
lead 질문의 답은 **절반만 맞다**:
```
[검증 — FakeShell + PBS 강제, 실제 렌더링]
  probe_qw_n1            select=1:ncpus=1:mpiprocs=1     ← 실제 제출
  probe_qw_n4            select=4:ncpus=1:mpiprocs=1     ← 실제 제출
  probe_qw_n16           select=16:ncpus=1:mpiprocs=1    ← 실제 제출
  check_probe_queuewait  select=85:ncpus=64:mpiprocs=64  ← 🔴 사전검사 (수정 전)
```
**실제 제출은 85로 나가지 않는다**(상한 16이 작동). **그러나 사전검사가 85×64 를 시험했고,
그 형태는 한 번도 제출되지 않는다.** 하필 `config/sizing.json` 주석에 *"85노드 요청이
거부됐다"* 고 적혀 있으니 **과거 거부된 형태를 재현해 다시 시험하던 셈**이다.
큐 상한이 있는 사이트면 **이 항목만 "거부됨"으로 떠서 실제로는 문제없을 3개 잡까지
사용자가 의심하게 된다.**

⇒ 분해를 `queue_wait_decomposition(env)` **한 곳**에 두고 제출·사전검사가 공유한다.
사전검사는 **실제로 나갈 가장 큰 잡**(16×1)을 시험한다. `max_probe_nodes` 가 바뀌어도
두 경로가 함께 따라온다(critic2 가 요청한 형태 — 16을 하드코딩하지 않았다).
수정 후: `check_probe_queuewait → select=16:ncpus=1:mpiprocs=1`.

**남은 표시 문제 (고치지 않음, 값에 영향)**: 계획 표는 여전히 `probe_queuewait ... 85` 를
보여준다. 예약 250 core-h 가 그 값으로 계산돼 있어 **바꾸면 가드 판정 값이 바뀐다.**
lead 가 "값이 바뀌면 멈추고 보고" 라 했으므로 **손대지 않았다.** 판단 요청.

### 25.4 회귀 테스트 — 수정 전 코드에서 **4건이 깨진다**
```
사전검사 형태 불일치 3건 (형태 일치 / 최대 잡 사용 / 85 미출현)
plan.py 우회 계산 1건 (정적 검사)
```

### 25.5 상태
`598 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `68af5d85109c` / gpu `ec0f69454345`** ← `e4b0504cd0f8` 를 대체
지시대로 `-A` 매핑 · `ncpus` 64 · V1b 미변경.

---

## 26. `cap` 연동 회귀 테스트 (lead 요구 (c) 강제)

lead 지적: *"대표값을 사전검사 쪽에 16으로 하드코딩하면 `max_probe_nodes` 가 바뀔 때 또
조용히 갈린다. **cap 을 바꿔가며 양쪽이 함께 따라오는지 고정하라 — 이게 (c)를 지키는
유일한 방법이다.**"* 맞다. `TestPrecheckFollowsTheCap` 을 추가했다.

`config.load` 를 가로채 **cap 만 바꾸고 실제 진입점(`cmd_submit`)을 그대로 돌린다**:

| cap | 실제 제출 | 사전검사 |
|---|---|---|
| 16 | `probe_qw_n1/n4/n16` | `select=16:ncpus=1` |
| 4 | `probe_qw_n1/n4` | `select=4:ncpus=1` |
| 1 | `probe_qw_n1` | `select=1:ncpus=1` |

**불변식**: 사전검사 spec ∈ 실제 제출 spec 집합 (cap 무관).
그리고 항목당 사전검사 잡은 **1개**임을 못박았다 — `qsub -h` 는 부작용이 있어 3개 다
시험하면 held job·삭제 실패 위험이 3배다(lead 근거 (b)).

### 🔴 두 위반 형태를 실제로 잡는 것을 확인했다
```
[위반 재현 — 주입] 사전검사에 16 하드코딩       → 2건 FAIL (cap=4 / 멤버십)
[위반 재현 — 주입] entry["nodes"]=85 그대로 사용 → 5건 FAIL
```
(위 두 줄은 **내가 일부러 만든 위반**이다. 발견 목록이 아니다.)

### 상태
`602 tests OK` (skipped 8) · `[stamp] ✅`

**sha256: cpu `58ba4389e470` / gpu `144a98cdc11f`** ← `68af5d85109c` 를 대체

---

## 27. `probe_queuewait` 표시·예약을 실제값으로 (lead 판정)

### 27.1 무엇이 틀려 있었나
```
이전:  표시 nodes=85 (= 1+4+16+64 **합계**)   예약 250.0 core-h
실제:  제출되는 것은 1+4+16 = **21 노드** (64는 상한 16에 걸려 생략)
```
🔴 **오표시의 대가가 이미 났다**: lead 가 표의 `85` 를 보고 *"85노드 요청이 거부됐다"* 는
**틀린 지시**를 보냈고 critic 이 반증했다. engineer 는 이 값으로 봉투를 계산한다.

### 27.2 수정 — 네 곳이 한 소스에서 나온다
`queue_wait_decomposition()` 을 **`cli.py` → `plan.py` 로 옮겼다**(순환 import 방지).
이제 ①계획 표시 ②예약 ③사전검사 ④실제 제출이 **같은 함수**를 본다.

```
표시   nodes = 21            (실제 노드합)
예약   44.80 core-h          (21 × 64 core/node × 0.0333 h)
비고   ⚠ [64] node 생략(상한 16)      ← 화면에 뜬다
사전검사 select=16:ncpus=1    실제 제출 1/4/16 × 1코어
합계   270.0 → 64.8 core-h
```

🔴 **wall 도 예산에서 역산하지 않는다.** `payload/probe_queuewait.sh` 는 `sleep 60` 이고
필요한 것은 "큐에서 언제 시작되는가" 뿐이다. 예산은 **상한**이지 목표가 아니다.
예전 `size_job` 은 예산을 다 쓰도록 wall 을 늘려서 **노드를 줄여도 예약이 250 으로 유지**됐다
— 그래서 노드만 고치는 것으로는 값이 안 맞았다.

⇒ `wall = min_wall_h`(선언된 필요시간 2분), `예약 = 노드합 × cpn × wall`.
🟢 **이 값은 스케줄러가 강제하는 상한과 정확히 같다**(노드 수·wall 둘 다 고정).
예전 250 은 상한도 실측도 아니었다. `test_reservation_equals_scheduler_enforced_ceiling` 이 이를 고정한다.

### 27.3 ⚠ 남은 가정 하나 — 과금 단위 (lead 확인 요망)
예약은 **노드 단위 과금**을 가정했다(보수적). 실제 제출 잡은 `ncpus=1` 이므로
**코어 단위 과금이면 실제 소비는 64배 작다**(44.8 → 0.7 core-h).
회신 JSON 의 `_reservation_basis` 에 이 가정을 명시했다. 보수적 쪽이라 가드 안전에는 문제없다.

🔴 **lead 가 예상한 "770 → 약 580" 과 내 실측 "270 → 64.8" 이 다르다.**
내 숫자는 PBS·64 core/node 환경에서 `build_plan` 을 직접 돌려 얻은 것이다(프로브 3항목만
계획됨 — 이 박스엔 G16/xtb 가 없어 나머지는 SKIP). lead 의 770/580 이 어느 환경 기준인지
확인이 필요하다. **감소 방향과 크기(250 → 45)는 lead 의 "약 60" 과 같은 자리수다.**

### 27.4 회귀 테스트 — `cap` 을 바꾸면 네 곳이 함께 움직이는가
`TestQueueWaitFourPlacesFollowOneSource` (7건). cap 만 바꾸고 실제 진입점을 돌린다.

| cap | 실제 제출 | 표시 | 사전검사 | 비고 |
|---|---|---|---|---|
| 16 | 1/4/16 | 21 | `select=16` | `[64] 생략` |
| 4 | 1/4 | 5 | `select=4` | `[16, 64] 생략` |
| 64 | 1/4/16/64 | **85** | `select=64` | (없음 — 이때는 85가 **사실**이다) |

⚠ 처음에는 *"85 는 어떤 cap 에서도 나오면 안 된다"* 로 썼다가 **틀렸다** — 상한이 없으면
85 가 맞다. 문제는 숫자가 아니라 **표시가 실제와 다른 것**이었다. 불변식을
`표시 == 실제 노드합` 으로 고쳤다.

**[위반 주입] `probe_queuewait` 특례를 제거 → 6건 FAIL** (내가 일부러 만든 위반이다).

### 27.5 상태
`609 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `8050a1d211be` / gpu `17c17368994f`** ← `58ba4389e470` 를 대체
지시대로 `-A` 매핑 · `ncpus` 64 · V1b 미변경. ②(plan.py core-h 일원화)는 §25.2 에서 완료,
**값 불변**(500.0/1008.0/5.0) — ①의 예약 변경과 구분해 테스트했다.

---

## 28. `README_USER.cpu.md` 갱신 (문서만)

지시 7항 전부 반영. **161 → 113줄** (낡은 것을 지우니 짧아졌다).

| # | 조치 |
|---|---|
| 1 | GPU 패키지 안내 **삭제** (ADR-037로 드롭) |
| 2 | P2 / P2ext 행 **삭제** (ADR-033/038로 제거) |
| 3 | 프로브 비용 ~370 → **64.8**, 총합 **2,694.8** 명시 |
| 4 | CP2K → *"계산에는 쓰지 않습니다. `probe_node` 가 **설치 여부만 기록**합니다"* |
| 5 | `sbatch --test-only` 중심 서술 → **`qsub -h` + `qdel`**, **완전 무부작용이 아님**과 `--no-precheck` 명시 |
| 6 | `--cores-per-node 64` 권고 **삭제** (이미 자동: 감지 68 → 요청 64) |
| 7 | 계정 `-A` 대조를 최상단 → **문제해결 표의 한 줄로 강등** |

**추가**: `⚠ [64] node 생략(상한 16)` 의 뜻 한 문단(왜 생략했나 · 실제로는 1/4/16 이 나간다 ·
`21 = 1+4+16` · **회신 JSON 에도 기록됨** · 올리려면 `max_probe_nodes`),
그리고 맨 위 **"지금 하실 일"** 3줄(`./run.sh` → 대기 → JSON 회신).

### 🔴 지우다가 필요한 것을 하나 지웠고, 테스트가 잡았다
*"로그인 노드에서 실행하세요"* 안내를 "여러 노드가 묶인 HPC" 절과 함께 통째로 지웠는데,
`test_cpu_readme_explains_multi_node_hpc_and_account` 가 실패했다. **낡은 것을 지우라는
지시였지 이건 아니었다.** 한 줄로 되살렸다.
⇒ 문서에도 회귀 테스트가 값을 한다는 사례다.

### 상태
`609 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `3f91ebd0e9c9` / gpu `0b4d55ece823`** ← `8050a1d211be` 를 대체
🔴 **코드·설정·테스트 미변경.** 바뀐 패키지 파일은 `README_USER.cpu.md` 하나다.

---

## 29. 실클러스터 회신 대응 — Gaussian 3항목 rc=3

### 29.1 원인 (회신 데이터로 확정)
```
plan.json        tools.g16 = {'how': 'binary', 'detail': '/apps/commercial/G16/g16/g16'}
계산 노드         software.g16 = ''                                    ← 없다
계산 노드 모듈     gaussian/g16.a03 / .a03.lin / .b01.lin / .c01.lin    ← 있다
결과             P1 / P1b / P5 전부 rc=3
```
로그인 PATH 에 바이너리가 보여 `binary` 로 잡혔고 ⟹ 잡 스크립트에 `module load` 줄이
**안 들어갔다.** 계산 노드에는 그 경로가 없었다.

🔴 **회신에서 추가로 확인한 것**: 수집 시점의 리포트에는 `module(verified)
gaussian/g16.a03 → /apps/commercial/G16/g16/g16` 이 남아 있다. **모듈 탐지 자체는
작동했고 같은 경로를 준다** — 제출 시점에만 바이너리가 먼저 잡혀 건너뛰어졌다.

### 29.2 수정 4건
1. **탐지 우선순위를 뒤집었다: `module(verified)` > `binary`.**
   모듈은 계산 노드에서 동작하도록 사이트가 만든 것이고, 로그인 PATH 의 경로는
   로그인 노드에서만 유효할 수 있다. 🟢 `vendored`(xtb) 최우선은 그대로다.
2. **바이너리를 찾아도 module 탐지를 항상 시도한다.** 예전 `if not software["g16"]`
   조건이 **이번 사고의 직접 원인**이었다. 그리고 후보 정렬을 고쳐 **최신
   (`gaussian/g16.c01.lin`)** 을 먼저 시도한다 — 예전에는 **가장 오래된 a03** 을 골랐다.
   `--gaussian-module <이름>` 으로 덮을 수 있다(목록에 없는 이름도 시도한다).
3. **실패를 구분한다.** 예전에는 전부 rc=3 이었다. 이제 `adapter.json` 에
   `module_load_failed` / `module_command_missing` / `loaded_but_binary_absent` /
   `loaded_but_not_runnable` / `absent` 를 구분해 남기고, payload 가 화면에도 찍는다.
   잡 안에서 **module 을 한 번 더 로드 시도**한다(사이트에 따라 `module` 함수가
   로그인 셸에서만 정의된다).
4. **`probe_node` 가 계산 노드에서 "모듈 로드 후 g16 이 보이는가"를 시험한다.**
   예전 인벤토리는 **로드 전** PATH 만 봐서 `g16=ABSENT` 로 보였다. 이제
   `g16_before_module` / `module_ok` / `modules_tried_failed` 를 회신에 싣는다.

### 29.3 ⚠ 추측하지 않은 것
`/apps/commercial/G16/g16/g16` 이 계산 노드에 있는지 **우리는 모른다.**
그래서 잡과 probe 가 **직접 확인해 기록**한다:
`login_binary_exists_on_compute_node` / `login_binary_executable`.
다음 회신이면 [UNVERIFIED] 가 사라진다.

### 29.4 회귀 테스트 (`tests/test_gaussian_module_priority.py`, 17건)
실클러스터 모듈 목록·바이너리 경로를 **픽스처로 그대로** 쓴다. 회신 JSON 이 있으면
그것으로도 검증한다(`TestAgainstTheRealClusterReport`).
**[위반 주입] 우선순위·정렬을 되돌리면 3건 FAIL** 확인.

🔴 **되돌리기 실험에서 두 번 걸렸다**: (a) 첫 시도는 슬라이스 편집이 파일을 깨뜨려
"FAIL" 이 아니라 **import 오류**가 났다 — 유효한 실험이 아니었다. (b) 복원 후에도 2건이
계속 실패했는데 원인은 **`__pycache__` 에 남은 되돌린 코드의 바이트코드**였다.
⇒ 되돌리기 실험 뒤에는 **`__pycache__` 를 지우고 다시 확인**해야 한다.

### 29.5 상태
`626 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `9dddebdd4e8a` / gpu `a38ba380a64b`** ← `3f91ebd0e9c9` 를 대체

---

## 30. Gaussian 모듈 확정 + 재실행 범위 (마지막 작업)

### 30.1 모듈 확정
`config/env_paths.json` 의 `gaussian_modules`:
```
default   : gaussian/g16.c01.lin        ← 사용자 확정
fallbacks : g16.b01.lin, g16.a03.lin, g16.a03
```
🔴 **이름을 코드에 박지 않았다** — `test_module_name_is_not_hardcoded_in_code` 가
`envpaths.py` / `cli.py` / `qc_adapter.sh` 를 검사한다(도움말 문구의 예시도 지웠다).
`--gaussian-module <이름>` 으로 덮을 수 있고, **`module avail` 에 안 보여도 시도한다.**
어느 것을 썼는지는 `adapter.json` 의 `module_requested` / `module_state` 에 남는다.

### 30.2 🔴 재실행이 성립하지 않았다 — 확인해서 잡았다
lead 가 *"그 동작이 이번 회신 상태에서도 실제로 성립하는지 확인하라"* 고 한 것이 옳았다.
**성립하지 않았다.**

```
회신 상태 재현:
  P3   done=True  submitted=False failed=False   → 건너뜀 (맞다)
  P1   done=False submitted=True  failed=True    → 🔴 "이미 제출됨"으로 건너뜀
```
`is_submitted()` 는 **실패한 항목에도 True** 다. 예전 논리는 `is_done` 다음 곧바로
`is_submitted` 를 봐서, **사용자가 `./run.sh` 를 다시 쳐도 P1/P1b/P5 는 아무 일도
일어나지 않았을 것이다.** `--force` 를 써야 했는데 그건 사용자가 알 수 없다.

⇒ 세 상태를 구분한다: `done` 건너뜀 → `failed` **재시도** → `submitted`(진행 중) 건너뜀.
🔴 재제출 직전에 **`clear_failed()` 로 실패 마커를 지운다** — 안 지우면 잡이 도는 중에
`./run.sh` 를 또 쳤을 때 **이중 제출**된다. `probe_qw_n*` 하위 잡도 같은 규칙을 쓴다.

🟢 **`--force` 를 써도 `done` 항목은 건너뛴다**(검사 순서가 `is_done` 먼저).
그래서 P3(500 core-h)를 헛되이 태우지 않는다. `test_done_item_is_never_retried_even_with_force`.

README 에 한 줄 넣었다: *"같은 디렉터리에서 `./run.sh` 를 다시 실행하시면 실패한 항목만
다시 돕니다. 이미 성공한 항목은 건너뜁니다."*

### 30.3 회귀 테스트
`tests/test_gaussian_module_priority.py` 26건.
**[위반 주입] 재실행 논리를 되돌리면 3건 FAIL** 확인
(분기 순서 / `clear_failed` 부재 / `--force` 시 done 재제출).

### 30.4 상태
`635 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `ab894eef0e63` / gpu `48184a5452b5`** ← `9dddebdd4e8a` 를 대체


---

## 31. `probe_throughput` 의 host 집계 유실 수정 (lead 부분 동결 해제분)

### 31.1 무엇이 틀려 있었나 — 🔴 **측정은 됐고 집계기가 버렸다**
engineer §R21.4(c) 가 *"200 task 로그의 hostname 을 유니크 카운트하라. 계산 비용 0"* 이라
요청했고, lead 는 회신 JSON 에 host 가 없는 것을 보고 *"기록이 안 됐으니 기록하게 하라"* 고
지시했다. **둘 다 그 전제가 틀렸다.**

```
payload/probe_throughput.sh   : task 마다 {"host": "$(hostname)"} 를 **처음부터 남기고 있었다**
sei_pilot/collect.py:436-441  : start_epoch / end_epoch 만 꺼내고 **host 를 읽고 버렸다**
```
⟹ 🔴 **부품(payload)은 맞았고 조립선(collector)이 값을 떨어뜨렸다.**
B-3(Gaussian 파서는 맞는데 `collect_p1` 이 ORCA 파서를 부름) · `to_dict()` 400자 컷과
**같은 형태이고, ADR-041 이 겨냥한 부류의 네 번째 사례다.**
크래시도 없었고 회신 JSON 도 정상 스키마였다 — **조용히 틀리는 부류다.**

🟢 **그리고 이것은 재실행이 필요 없다는 뜻이다.** 원본 `task_*.json` 200개가 사용자
클러스터에 그대로 있다(그 파일들에서 `jobs_started: 200` 이 나왔다). 사용자가 한 줄이면 닫는다:
```bash
sed -n 's/.*"host": "\([^"]*\)".*/\1/p' \
    sei_pilot_work/jobs/probe_throughput/starts/task_*.json | sort -u | wc -l
```

### 31.2 고친 것
| 파일 | 내용 |
|---|---|
| `sei_pilot/probes.py` | `host_metrics()` 신설 — `n_hosts` / `hosts_unique` / `hosts_histogram` / `tasks_with_host` / `tasks_without_host` / `tasks_per_host_max` / `hosts_note` |
| `sei_pilot/collect.py` | `collect_throughput()` 이 `rec["host"]` 를 수집해 `host_metrics()` 에 넘긴다 |

**설계 판단 3건:**
1. 🔴 **`n_hosts` 는 기록이 없으면 `0` 이 아니라 `None`** (ADR-036). `0` 이면 코드가
   *"노드를 0대 받았다"* 로 읽는다. *경고는 사람만 읽고 `null` 은 코드도 읽는다.*
2. 🔴 **히스토그램까지 싣는다.** 유니크 수만 있으면 *"8 task 가 2 노드"* 와 *"2 task 만 돌았다"* 를
   구분할 수 없다. **두 해석의 차이가 봉투 50배다**(engineer §R21.4).
3. 🔴 **`hosts_note` 가 과대주장을 미리 막는다** — *"그 순간 점유이지 상시 확보가 아니다"*,
   *"유니크 수가 task 수보다 크게 작으면 팩킹이고 그때는 독점 정책 가정이 반증된다"*.
   빠지면 다음 라운드에서 `n_hosts` 가 `n_nodes` **상한**으로 승격돼 인용된다(ADR-034 유형).

### 31.3 회귀 테스트 — `tests/test_throughput_hosts.py` (9건)
🔴 **진입점에서 시작한다**(ADR-041): **진짜 payload 실행 → `cli.cmd_collect` → 디스크의 회신 JSON**.
🔴 **픽스처를 손으로 만들지 않는다**(ADR-042): `task_*.json` 을 파이썬으로 지어내면
*"내가 상상한 payload 출력"* 을 검증하게 되므로, **인도본 `payload/probe_throughput.sh` 를
그대로 `bash` 로 실행**한다. 바꾼 것은 스크립트가 아니라 **환경뿐**이다 —
`sleep`(60초 대기 회피)과 `hostname`(여러 노드 흉내)을 PATH shim 으로 갈아끼웠다.

**[되돌리기 실험]** `m.update(probes.host_metrics(...))` 한 줄을 제거해 결함을 재현:
```
[ast] 구문 정상 — 되돌린 것이지 부순 것이 아니다   ← ADR-042(a) 확인
__pycache__ 제거 후 재실행                          ← ADR-042(b) 확인
결과: FAILED (failures=1, errors=4)  /  복원 후 9건 OK
```
🔴 **그리고 이 실험이 ADR-041 을 직접 입증했다**: 되돌린 상태에서도
**payload 단위 테스트 1건과 `host_metrics` 부품 테스트 2건은 그대로 통과했다.**
**부품 테스트로는 이 결함을 정의상 잡을 수 없다.**

⚠ 처음엔 5건이 전부 `ERROR`(KeyError) 였다. ADR-042(a) 대로 *"ERROR 는 대개 실험이 잘못된 것"*
이므로 트레이스백을 확인했고 — **단언 줄의 KeyError = 진짜 부재**였다. 다만 증거를 강하게
만들려고 **존재 단언을 먼저** 넣어 `FAIL` 로 보고되게 바꿨다.

### 31.4 상태
`644 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `f9f31caef240` / gpu `664900bb9688`** ← `ab894eef0e63` 를 대체
🔴 **재실행 조정(분할·wall·가드·팩킹)은 착수하지 않았다.** engineer Q1/Q3/Q5 + 사용자 답변 대기.


---

## 32. CREST `degraded` (ADR-044) + wall 상한을 **큐에서 읽기** (lead 요구)

### 32.1 CREST 부재 = **조용한 성공** 차단
engineer §R21.5(b)④ 는 *"crest 스테이지 때문에 `rc≠0` 이 한 번 더 난다"* 였는데
**proposer 가 `P1.sh` 를 직접 읽고 정정했고, engineer 도 철회했다.** 실제 위험은 반대였다:

> **CREST 가 없으면 P1 은 실패하지 않고, conformer 표집을 건너뛴 채 `pass` 로 돌아온다.**
> ⟹ 1,000+ core-h 를 주고 사는 **TS 단가가 과소평가된 채** 회신되고, 받는 쪽은 그것을
> 완전한 TS 워크플로 단가로 읽는다. `status` 도 `rc` 도 그 사실을 말하지 않는다.

🔴 **이 세션 네 번째 같은 형태다** (B-3 / `to_dict()` 400자 컷 / `host` 유실 / CREST):
**"시끄러운 실패"인 줄 알았던 것이 실은 "조용한 성공"이었다.**

| 파일 | 내용 |
|---|---|
| `payload/P1.sh:51-63` | 양 분기에서 `crest_status.json` 을 남긴다. **rc 는 바꾸지 않는다**(실패가 아니다) |
| `sei_pilot/collect.py` `p1_degradation()` | `crest_skipped` / `degraded` / `degraded_reasons` / `degraded_note`. 사유는 `warnings[]` 에도 넣는다(코드는 필드를, 사람은 warnings 를 읽는다) |

**설계 판단**: `status` 를 건드리지 않고 **`degraded` 라는 별도 축**을 만들었다.
🔴 `fail` 로 바꾸면 진짜 실패와 구분이 사라지고, **§30 의 재실행 로직(`failed` 는 재시도)이
멀쩡한 1,000 core-h 짜리 잡을 다시 돌린다.** 파일이 없으면 `False` 가 아니라 **`None`**(ADR-036) —
`False` 는 **없는 보증**을 만들어낸다.

### 32.2 wall 상한을 **큐에서 읽는다** (`resolve_wall_limit`)
engineer 사양의 `48 h` 는 `[LITERATURE — 사이트 문서]` 다. lead 판정: 하드코딩 금지.
🔴 **그리고 코드가 이미 그 병에 걸려 있었다**: `sysprobe` 가 `qstat -Qf <queue>` 로
`resources_max.walltime` 을 **수집해 `env["queue_info"]` 에 넣어두는데, `build_plan` 은
`partition_max_wall_h`(=`sinfo` 유래 ⟹ PBS 에선 항상 `None`)만 봤다.**
**측정해 놓고 안 쓰는 값이 또 하나 있었다 — `host` 유실과 같은 형태다.**

우선순위 `명시 인자 > 큐 실측 > 파티션 > 우리 캡`, 어느 경우든 우리 캡을 안 넘는다.
못 읽으면 **조용히 48 을 쓰지 않고** 화면·JSON 에 `[UNVERIFIED]` 로 크게 남긴다
(`wall_limit_source` / `wall_limit_basis` / `wall_limit_verified`).

### 32.3 회귀 테스트 (17건) — 전부 되돌려서 확인함
`tests/test_p1_degraded_crest.py`(8) · `tests/test_wall_limit_source.py`(9)
🔴 **픽스처를 손으로 만들지 않았다**: `crest_status.json` 은 **`P1.sh` 에서 그 파일을 쓰는
`printf` 줄을 뽑아 `bash` 로 실행**해 만든다(payload 가 형식을 바꾸면 테스트가 깨진다 — 그게 목적).
`queue_info` 는 **진짜 파서 `sysprobe.parse_qstat_queue`** 로 만든다.

```
[되돌리기 A] P1.sh 의 crest_status 기록 제거 → bash -n 정상 → FAILED (failures=7)
[되돌리기 B] build_plan 의 resolve_wall_limit 호출을 옛 줄로 → ast 정상 → FAILED (failures=3)
복원 후 전체: Ran 661 tests OK (skipped=8) · [stamp] ✅
```

### 32.4 🔴 내가 틀렸던 것 2건 (기록)
1. **"`%Chk` 가 패키지에 0건"** — **틀렸다.** `grep "Chk"` 로 찾았는데 코드는 소문자
   `%%chk=` 를 포맷 문자열로 쓴다. **grep 으로 부재를 단정한 것 자체가 ADR-036 위반이었다.**
   실제 생성기를 돌려 확인했다: 모든 `.gjf` 에 `%chk=<이름>.chk` 가 있다.
   ⟹ engineer 사양 (A′)("`%Chk` 지시자만 넣어라")는 **이미 구현돼 있어 할 일이 없다.**
   🔴 다만 **잡마다 자기 이름의 chk** 라 IRC 가 TS 의 Hessian 을 재사용하지 못한다 —
   `irc=(calcfc,…)` 라 **Hessian 을 방향마다 새로 계산한다(총 4회).** 절감하려면
   `ts_qst2.chk` 복사 + `rcfc` 가 필요한데, **G16 이 없어 검증 불가라 이번 판에는 넣지 않았다.**
2. **테스트 전제 2건이 틀렸다** — ① wall 축소 확인을 기본 항목으로 하려 했으나 그 env 엔
   QC 코드가 없어 P1/P5/P1b 가 생략되고 남은 프로브는 상한보다 훨씬 짧았다(**줄어들 잡이 없었다**).
   ② `degraded` 가 `fail` 을 만들지 않는지 보려 했으나 그 픽스처의 P1 은 로그가 없어 **원래부터
   `fail`** 이었다 ⟹ **대조 실험(crest 유무만 바꿔 status 비교)으로 교체.**
   **둘 다 코드가 아니라 테스트가 틀린 경우였다.**

### 32.5 상태
`661 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `530c0a433d99` / gpu `f36f99714fb6`**
⏳ **예산·분할·P6 는 미완**: engineer 에게 **예약값 정의(guard 가 무엇을 막는가)** 판정을 요청해 둔 상태.


---

## 33. 재실행 사양 구현 (§R22 / §R24) — 그리고 그 아래 깔린 전제가 틀려 있었다

### 33.1 🔴🔴 최우선이었던 것 — **array 태스크당 1코어가 산식에 하드코딩돼 있었다**
```
plan.py (구)  "array는 태스크 수만큼 곱한다 (200개 x 1코어 x wall)"
              reserved = units.core_hours_h(n_tasks * 1, wall)
```
`probe_throughput`(200 × 1분 × 1코어)에는 **옳았다.** 그런데 §R22 가 P5·P1b 를 array 로
바꾸면서 **그 기계장치를 그대로 물려받았다.** P5 최대 태스크 496 core-h 가 1코어면 **wall 496 h** 다.
⟹ **§R22·§R24 의 wall·천장 표 전부가 그 위에 서 있었다.**

🔴 **그리고 가드는 이 결함을 보지 못한다.** 되돌려서 확인했다: 1코어로 두면 core-h **천장은
거의 그대로**다(링크가 늘어 상쇄된다). 폭발하는 것은 **wall 과 링크 수**뿐이라
`budget_guard` 는 아무 말도 하지 않고 **잡만 wall-kill 된다.** 조용히 틀리는 부류다.
⟹ 그래서 `test_pilot_walls_stay_inside_the_queue_limit` 를 따로 뒀다.

### 33.2 두 통화를 분리했다 (§R24.1)
```
reserved_core_hours = 물리 천장 (cores×wall×links)  ← guard 는 여기에 건다. 스케줄러가 강제한다
expected_core_hours = 소비 전망                      ← 보고용. 강제되지 않는다
node_hours          = Σ(wall×links)                  ← 노드 단위 과금이면 이게 진실이다
```
셋 다 **정의 문자열을 값 옆에 싣는다**(`core_hour_field_definitions`).

### 33.3 🔴 내가 재검산해서 잡은 것 — engineer §R24.1 "수정 후" 표의 P1b 행이 틀렸다
| | engineer 표 | **코드가 계산한 값** |
|---|---|---|
| P1 | 9,216 | 🟢 9,216 |
| P6 | 1,944 | 🟢 1,944 |
| P5 | 4,238 | 🟡 4,380.9 (min_wall 2 h 바닥에 **15/22 태스크**가 걸림, 초과분 1,455) |
| **P1b** | **4,760 (1.00×)** | 🔴 **7,810** |

**P1b 원인: `3,094/64 = 48.34 h` 로 48 h 상한을 2% 넘는다** ⟹ 링크 2개 ⟹ 천장 6,144(1.99×).
4,760 은 **링크 절상을 무시한 도달 불가능한 값**이고, 같은 문서 "수정 전"의 12,288 은
`min_wall 48` 을 적용한 값이다. **셋 다 서로 다르다.**
⟹ 그대로 두면 총 천장 24,917 > guard 21,000 ⟹ **P1b(가장 값진 측정)가 조용히 SKIP 된다.**

### 33.4 🟡 PROVISIONAL 2건 — engineer 판정 대기 (코드에 라벨로 박아뒀다)
```
P1B 22원자 예산  3,094 → 3,072 (= 64×48, 정확히 1링크)   천장 6,144 → 3,072.  대가 −0.7%
P5  min_wall_h   2.0 → 0.5                                천장 4,381 → 3,128 (1.07×)
⟹ 총 천장 19,591 / 전망 17,179 / guard 21,000 (여유 6.7%). 생략 0건
```
🔴 **둘 다 engineer 자신의 규칙("편차를 wall 바닥값으로 덮지 말고 예산에 반영하라")의 적용이지
내가 만든 방법론이 아니다.** 그래도 확인 전까지 `# 🟡 PROVISIONAL` 이다.

### 33.5 🔴 P7(CP2K)은 **넣지 않았다** — lead 승인과 사용자 제약이 충돌한다
lead 가 engineer §R23 ②(CP2K s/step 편승)를 승인했는데, 구현하고 보니 **두 개의 가드 테스트가
막는다**:
```
tests/test_accounts.py:210        test_only_gaussian_and_xtb_remain
   "🔴 사용자 요구: 모든 DFT/반경험 방법론은 VASP·Gaussian·xtb 로"
tests/test_integration_paths.py:223  test_cp2k_layer_is_fully_removed
근거 ADR-037 / ADR-038 / ADR-039 (λ_out 재결 → CP2K 요구 소멸)
```
🔴 **그 테스트를 내가 지우면 사용자 결정을 코더가 되돌리는 것**이다. 스크립트는 완성해서
`src/experiments/p7_cp2k/` 에 사유와 함께 보관했다. **lead 판정이 "넣어라"면 10분이면 된다.**

### 33.6 그 외 반영
- **P6 = array 가 아니라 항목 3개**(`P6_t1/t16/t64`). PBS array 는 태스크마다 `select=` 를
  못 바꾼다. array 로 하면 (a) 셋 다 64 를 요청해 예약이 1,944→4,608 이 되거나
  (b) `probe_queuewait` 같은 전용 분해 코드를 또 만들어야 한다 — **(b)는 critic 이 유령 잡을
  잡았던 그 자리다.** 항목 3개면 새 분기가 0 이다. payload 는 **하나**를 공유한다.
- **sysprobe (ADR-043)**: 키워드 화이트리스트 확장 + **`head -400` 절단 제거** +
  `modules_raw`(전문) + **`software_probed`**(프로브 목록) + `mopac`/`nwchem`/`lammps` 등 추가.
  🔴 `software` 는 **순수 매핑으로 유지**했다 — `_probed` 를 그 안에 넣었더니 하위 소비자가
  전부 깨졌다(*"같은 자리에 다른 종류를 넣지 마라"*).
- **CPU `flags` (§R23.1 G1)**: `lscpu` + **`/proc/cpuinfo` 폴백**, `classify_isa()` 가
  KNL 전용/Skylake 전용 AVX-512 플래그를 구분하고 빌드 플래그 경고까지 낸다.
- **P1 `cost_bias`**: `hessian_count: 4` `[DERIVED — route 문자열에서 셈]` + 편향 두 항
  (crest 생략 −5~−15% / Hessian 4회 +10~+25%). *"P1 단가 = S3 생산 단가"로 옮기지 마라.*

### 33.7 되돌리기 실험 (ADR-042)
```
[A] array 태스크당 코어 → 1 하드코딩 복원 → ast 정상 → FAILED (failures=2)
[B] resolve_wall_limit 호출 제거          → ast 정상 → FAILED (failures=3)
[C] P1.sh 의 crest_status 기록 제거       → bash -n 정상 → FAILED (failures=7)
[D] collect 의 host_metrics 호출 제거     → ast 정상 → FAILED (failures=1, errors=4)
복원 후: Ran 678 tests OK (skipped=8) · [stamp] ✅
```
🔴 **[A] 에서 처음엔 1건만 깨졌다.** 가드가 못 보는 결함이라(33.1) **wall/링크를 직접 보는
검사를 추가**하고 나서 2건이 됐다. *"깨지는 걸 봤다"에서 멈추지 말고 **충분히 깨지는지**를 봐야 한다.*

### 33.8 상태
`678 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `d1053982a5f6` / gpu `b706522473ec`**


---

## 34. 재실행 착지 (§R26 / §R27 / ADR-048 / ADR-049)

### 34.1 🔴🔴 ADR-048 — **P6 는 array 코어 버그로 죽지 않는다. 그게 더 나쁘다**
| 항목 | 1코어를 받으면 | 결과 |
|---|---|---|
| P5 최대종 · P1b 22원자 | wall 747 h / 3,072 h | 🟢 **시끄럽게 즉사** — 발견된다 |
| **P6** | `%nprocshared=16` 을 1코어 위에 오버서브스크립션 | 🔴 **정상 종료한다** |

⟹ **"16스레드 측정점"이 회신에 실리고 κ 가 16배 틀린다. S 는 통째로 무의미해진다.**
**데이터처럼 보이는 쓰레기** — 이번 라운드 내내 싸운 실패 부류의 정점이다.

**하드 게이트 (판단하지 않고 버린다):**
- `payload/P6.sh` 가 **선언(항목 키) · 요청(`SEI_TOTAL_CORES`) · 관측(`%nprocshared`, `nproc`)** 셋을 싣는다
- `collect_p6()` 가 셋이 일치하지 않으면 `valid=False` + `[INVALID]` 사유를 달고
  **κ·S 산출에서 제외**한다
- `plan.sizing_gates()` 가 **제출 전에** 막는다(아래)

### 34.2 🔒 §R26.4 게이트 3개 — **하나라도 실패하면 제출하지 않는다**
```
(a) 모든 array/스레드 항목의 코어 수 == 선언값   ← P6 는 1/16/64 로 서로 달라야 한다
(b) array 항목의 링크가 전부 1                   ← array 체이닝은 천장을 계단식으로 올린다
(c) Σ 천장 ≤ guard.max_core_hours
```
실패 시 `format_gate_failures()` 가 **4-튜플 표(코어·wall·링크·천장/전망)** 를 그대로 찍는다.
🔴 **[critic3 사소 — 서술 정정]** 이 절은 원래 *"게이트 하나라도 실패하면 빈 목록 반환"* 이라고
적었는데, **§36 에서 항목 단위 차단으로 바뀐 뒤 이 문장을 갱신하지 않았다.** 실제 동작은:
**게이트 (a)/(b) = 그 항목만 빠짐 · 게이트 (c)(총 천장 > 가드) = 전체 중단**
(`--ignore-sizing-gates` 는 (c)에만 관계한다). **§36 이 정본이다.**
🔴 화면 문구를 바꿨다: 예전에는 `--max-core-hours <더 큰 값>` 을 권했는데 그게
**§R24.1 이 기각한 거래로 가는 문**이었다. 지금은 *"가드를 올리기 전에 사양을 의심하라"* +
**사전 확약된 절단 순서**(P7 → P3 → P6 1스레드 → engineer/lead)를 낸다.
(그 자리에 `~3,150 core-h` 라는 **낡은 리터럴**도 남아 있었다. 함께 제거했다.)

### 34.3 🔒 §R24.2(1) — **큐 하나 보고 24 h 라 단정하지 않는다**
`qstat -Qf` **전체**를 읽어(`parse_qstat_all_queues`) **walltime 최장의 사용 가능한 큐**를 고른다
(`longest_wall_queue`, `enabled=False`/`started=False` 제외).
사이트에 `long` 이 있으면 **비용 0 으로 wall 문제가 사라진다.**
🔴 이것은 이 패키지가 이미 밟은 함정의 반대편이다 — 파티션을 `sinfo` **한 곳에서만** 읽어
PBS 에서 `-q` 가 통째로 빠졌었다. **이번엔 하나만 보고 결론내지 않는다.**

### 34.4 확정·제거
- 🔒 **P1b 22원자 3,094 → 3,072** (= 64×48, 정확히 1링크). engineer §R26.1 과 **독립 수렴**
- 🔒 **P5 `min_wall_h` 2 → 0.5** (engineer 검산: 최소종 비관 0.34 h, 여유 1.5×)
- 🔒 **guard 21,000 유지** (22,000 기각 — *"가드를 올리기 전에 사양을 의심하라"*)
- 🔒 **P3 제거** — 🔴 **비용이 아니라 이미 측정됐기 때문이다**(RT-1 pass, 0.10038·31.7%).
  되살리는 법은 `plan.py` 의 주석 블록에 적어뒀다
- 🔒 **P7(CP2K)은 여전히 패키지 밖**(`src/experiments/p7_cp2k/`). U-46 게이트 + 사용자 제약
  두 가지 이유가 같은 결론을 가리킨다

### 34.5 검증 — **engineer 닫힌형과 대조**
```
48 h: probe 66 + P1 9,216 + P5 3,128 + P1b 4,738 + P6 1,944 = 19,091.4  여유 9.1%
      → engineer §R27 의 "P3 제거 + P7 게이트 = 19,092 / 9.1%" 와 **일치**
24 h: 총 17,555.4 (guard 통과) 🔴 **단 게이트 (b) 실패** — P1b 22원자가 64×24=1,536 을 넘어
      링크 2. 종을 가로질러 쪼갤 수 없으므로(§R22.8) **`long` 큐가 유일한 해법**이다.
      ⟹ 게이트가 제출을 막고 4-튜플 표를 낸다. 설계대로다.
```

### 34.6 되돌리기 실험 (ADR-042)
```
[E] cmd_submit 의 게이트 차단 제거 → ast 정상 → FAIL: test_sizing_gate_blocks_submission
복원 후 전체: Ran 679 tests OK (skipped 8) · [stamp] ✅
```

### 34.7 🔴 테스트를 고치며 **내가 만든 없는 규칙 1건을 자진 철회**했다
P3 제거로 깨진 테스트를 고치다가 *"생략 가능한 모든 항목은 `fallback_hint` 를 가진다"* 로
일반화해서 새 테스트를 썼는데, **그건 한 번도 참인 적이 없었다** — `fallback_hint` 를 가진
항목은 P3 하나뿐이었고 지금은 0 개다. **실제로 성립하는 불변식**(도구 부재 생략은 빈 사유로
사라지지 않는다)으로 되돌렸고 그 경위를 테스트 docstring 에 남겼다.
🔴 **없는 규칙을 테스트로 굳히는 것은 결함을 못 잡는 것보다 나쁘다** — 다음 사람이 그것을
근거로 삼는다.

### 34.8 상태
`679 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `4623019f0e11` / gpu `d3bbf59d9fa5`**


---

## 35. ADR-050 — 허용 엔진 집합 (**사용자가 직접 정했다**)

### 35.1 사용자 원문
> *"**MOPAC 은 배제**하고, **Gaussian, VASP, LAMMPS, xTB** 로 패키지를 한정해.
> 만약 **정말 필요하다면 CP2K 를 추가해도 좋아.**"*

🔴 **이 답은 내가 P7 을 넣지 않고 멈춘 결과로 나왔다.** 가드 테스트 2건이 사용자 제약을
코드로 굳힌 것이었고, **내가 지웠으면 사용자 결정을 코더가 되돌리는 것**이 됐다.
lead 가 자기 누락(ADR-045 에서 CP2K 를 사용자에게 올리지 않고 사전등록한 것)을 확인하고
사용자에게 올렸다. **멈춘 것이 답을 만들었다.**

### 35.2 구현 — **"있다"와 "써도 된다"를 분리했다**
`sysprobe.py`:
```
ALLOWED_ENGINES      = g16 / g09 / vasp_std / lammps / lmp / xtb / crest
CONDITIONAL_ENGINES  = cp2k*        ← "정말 필요하다면". U-46 게이트 통과 시에만
EXCLUDED_ENGINES     = mopac* (ADR-050) · reaxff (이전 사용자 결정)
engine_policy(name) → {allowed, conditional, reason}
info["engine_policy"] 로 **탐지 결과 옆에** 실린다
```
🔴 **탐지는 계속한다.** `mopac` 을 프로브 목록에서 지우면 다음 라운드에 누군가 다시 후보로
올리고, 회신에 없으니 또 "부재 확정"으로 오독한다 — **실제로 한 번 일어났다**(§R21.10).
⟹ **탐지는 유지, 정책으로 배제.** ADR-043 의 "찾아봤는가" 기록도 그대로 산다.

🔴 **LAMMPS 허용 ≠ ReaxFF 허용.** ReaxFF 는 사용자가 **이전에 별도로** 배제했고 그 결정은
살아 있다. 흐려지기 쉬워서 `EXCLUDED_ENGINES["reaxff"]` 의 사유 문자열에 그 문장을 박았고,
`test_lammps_allowed_does_not_imply_reaxff` 가 지킨다.

### 35.3 가드 테스트 2건 — **이번엔 갱신했다. 권한이 다르기 때문이다**
| 테스트 | 전 | 후 |
|---|---|---|
| `test_only_gaussian_and_xtb_remain` → `test_only_allowed_engines_remain` | "VASP·Gaussian·xtb 로" | ADR-050 집합 + **사용자 원문 인용** |
| `test_cp2k_layer_is_fully_removed` → `test_cp2k_layer_is_not_wired_into_the_package` | **금지** | **조건부 허용, 단 게이트 전에는 배선 금지** |

🔴 **docstring 에 사용자 원문을 그대로 인용**했다. 다음 사람이 *"코더가 제약을 완화했다"* 로
읽으면 안 되기 때문이다 — **사용자가 스스로 개정한 것**이다.

### 35.4 되돌리기 실험
```
[F] EXCLUDED_ENGINES 에서 mopac 제거 → ast 정상 → FAIL: test_mopac_is_excluded_but_still_probed
복원 후 전체: Ran 684 tests OK (skipped 8) · [stamp] ✅
```
⚠ **복원할 때 `cd` 가 남아 저장소 루트에 `sysprobe.py` 를 만들었다**(lead 가 경고한 "잔류 cwd"
함정). 테스트가 계속 실패해서 알아챘고, 파일을 지우고 절대경로로 복원했다.
**되돌리기 실험의 복원은 절대경로로 하라.**

### 35.5 아직 하지 않은 것 (lead 지시대로)
- **P7(CP2K)**: 이제 **허용되지만** U-46 게이트 미통과 + 축 3 설계 변경 가능성으로 **보류**.
  스크립트는 `src/experiments/p7_cp2k/` 에 완성돼 있다
- **LAMMPS**: 프로브 목록에 **이름만** 추가했다(존재 여부 조회). **설계는 건드리지 않았다** —
  proposer 가 "LAMMPS 가 무엇을 여는가"를 판정한 뒤에 한다
- **축 3(PM7)**: MOPAC 배제로 죽었다. 관련 스텁이 있으면 `# SUPERSEDED by ADR-050` 만 달고 둔다

### 35.6 상태
`684 tests OK` (skipped 8) · `[stamp] ✅`
**sha256: cpu `7dd91d57cc0c` / gpu `b1da254c7a35`**
🟢 **P7·LAMMPS 없이 인도 가능한 상태. critic 리뷰 준비 완료(§28~§35).**


---

## 36. 게이트를 **항목 단위 차단**으로 (lead 판정)

### 36.1 무엇이 틀렸나 — **내가 만든 실패 모드가 틀렸다**
내가 critic 브리핑에서 스스로 의심한 항목이었고, lead 가 판정했다:
> *"24 h 큐에서 총액은 가드를 통과하고(17,555) 위반은 **P1b 한 항목**이다.
> **P5·P1·P6 는 독립 측정이고 24 h 에서 정상이다.** 그것들까지 막으면
> 🔴 **사용자가 왕복 하나(3.5일)를 쓰고 아무것도 못 받는다.**"*

🔴 **게이트가 "조용히 틀린 측정"을 막으려다 "아무 측정도 못 하게" 만들고 있었다.**
방어가 과해져 목적을 삼킨 형태다.

### 36.2 고친 것
| 실패 종류 | 전 | 후 |
|---|---|---|
| **항목 단위**(코어 불일치 · array 링크>1) | 🔴 전량 차단 | 🟢 **그 항목만** 빠지고 나머지는 제출 |
| **전역**(총 천장 > 가드) | 전량 차단 | 전량 차단 **유지** — 회계가 어긋난 것이라 다른 문제다 |

- `sizing_gates()` → `blocked_items[]` / `blocks_everything` / `remedy`
- `build_plan()` 이 위반 항목을 `status="skipped"` + **`blocked_by_gate=True`** + `remedy` 로 표시
  🔴 **새 status 값을 만들지 않았다.** 만들면 그 값을 모르는 소비 경로가 조용히 생긴다 —
  이 패키지에서 이미 여러 번 난 형태다.
- 화면에도 전용 블록으로 크게 나온다(**`--ignore-sizing-gates` 없이도**). 사유 + **무엇을 하면
  풀리는지**(더 긴 큐 / `--queue <이름>`)를 함께 낸다.
- 🔴 **차단 항목의 예약(천장)은 합계에서 빼지 않았다.** 빼면 총액이 **낙관** 쪽으로 움직이는데
  가드는 그러면 안 된다. 그 사실을 `_reservation_note` 로 밝힌다.

### 36.3 🟡 [PROVISIONAL] 종 단위 부분 실행 — **가능하다. 다만 알리기만 한다**
lead 질문에 답한다: **구조적으로 이미 가능하다.**
P1b 의 array 는 **태스크 1개 = 종 1개**이고(§R22.8), 24 h 에서 걸리는 것은 **태스크 3(22원자)** 뿐이다.
`r_composite=(A+C)/A` 는 **종 안에서 완결**되므로 **남는 2종의 비는 그대로 유효**하다.
```
offending_tasks: [3]    runnable_tasks: [1, 2]    partial_run_possible: True
```
🔴 **자동 발동하지 않는다.** *"2종만의 `r` 이 8배→3배 축소에 쓸 만한가"* 는 **견적자 판정**이고,
잃는 것은 **크기 의존성의 상단**이다. 24 h 로 판명되면 engineer 를 다시 띄워 판정시킨다.

### 36.4 되돌리기 실험
```
[G] blocked_items 를 항상 빈 목록으로 → ast 정상 → FAIL 2건
    (test_only_the_violating_item_is_blocked · test_block_is_not_silent)
복원 후 전체: Ran 690 tests OK (skipped 8) · [stamp] ✅
```
🔴 **그리고 기존 테스트 하나가 나를 잡았다**: `test_sizing_gate_blocks_submission` 이
*"게이트 실패 시 아무것도 제출되지 않는다"* 를 단언하고 있었다 — **내가 만든 틀린 실패 모드를
테스트가 굳히고 있었던 것**이다. 사양이 바뀌었으므로 **사유를 적어 갱신**했다
(`test_sizing_gate_blocks_only_the_violating_item`).
🟡 **교훈**: 테스트가 깨졌을 때 *"테스트를 고칠 것인가 코드를 고칠 것인가"* 의 답은
**어느 쪽이 사양인가**로 정해진다. 이번엔 **테스트가 낡은 사양을 들고 있었다.**

### 36.5 🔴 critic 의 되돌리기 실험과 겹칠 뻔했다
작업 직전 트리가 `FAILED (9건)` 이고 `dist/` 해시가 바뀌어 있었다.
**"트리가 깨졌다"고 보고하기 전에 원인을 확인**했더니 `plan.py:776` 에
`per_task_cores = 1  # [되돌리기 실험 — 1코어 하드코딩 복원]` — **critic 이 내가 브리핑에
적어준 §33.1 재현 절차를 실행 중**이었다.
⟹ 손대지 않고 critic 에게 **복원값 + 4단계 절차**를 보냈고, 복원(11:40) 후에 작업했다.
🔴 **내가 "고쳤으면" 리뷰어의 실험을 오염시켰을 것이다.**
🔒 **그리고 그때 알아낸 것: tarball sha256 은 재빌드마다 바뀐다(gzip mtime).
동일성 비교는 `build_stamp` 의 `source_digest` 로 해야 한다.**

### 36.6 상태
`690 tests OK` (skipped 8) · `[stamp] ✅` · **`source_digest e2ade998db3fc8ec`**


---

## 37. critic3 `FIX-THEN-RUN` 대응 — **치명적 2 + 중대 1 + 사소 3**

critic3 가 지목 4항목을 전부 경로 실행으로 재현해 확인(문제 없음)한 뒤, **대조 도중 새로 3건**을
찾았다. 전부 **경로 실행으로 독립 재현한 뒤** 고쳤다.

### 37.1 🔴 치명적-1 — **P5 dual-seed 데이터가 통째로 샜다** (여섯 번째)
```
criteria/p5.py::normalize_rows() 가 복사하지 않던 것:
    seed / seed_provenance / failure_reason / g16_cpu_seconds / qc_code / route / level_label
collect_p5 가 읽지 않던 것:
    dual_seed_species / seed_pairs / _sigma_note
```
**재현**(코드 실행): 같은 id 의 seed 0/1 두 행을 `evaluate_p5` 에 넣었더니 결과 행에 **`seed` 키
자체가 없다.**
🔴 **dual-seed 종은 core-h 를 2배 써서 만든 데이터다.** 목적은 σ_protocol(프로토콜 재현성)
비교인데, seed 가 없으면 **어느 행이 0 이고 어느 행이 1 인지 회신만으로 알 수 없어 그 비교가
불가능하다.** ⟹ **2배 비용을 쓰고 목적을 잃는다.**
🔴 `failure_reason` 유실도 별개로 심각하다 — 미수렴 **원인**이 최종 리포트에서 사라지면
다음 왕복에 같은 질문을 다시 해야 한다.
🟢 **고침**: 7개 필드 복사 + `dual_seed_species`/`seed_pairs`/`sigma_note` 적재.
그리고 **시드 쌍이 미완성인 종을 경고로 낸다** — 한쪽 시드가 죽으면 σ 를 낼 수 없는데,
그 사실이 없으면 받는 쪽이 **불완전한 쌍으로 σ 를 계산**한다.

**"측정해 놓고 안 쓰는 값" 목록 (여섯 번째)**:
B-3 / `to_dict()` 400자 컷 / `--emit-script` 분기 / `host` / 큐 wall / **P5 seed**.

### 37.2 🔴 치명적-2 — **`long` 큐가 실존하면 게이트가 무력화됐다**
`resolve_wall_limit()` 이 `qstat -Qf` 전체에서 **가장 긴 큐**의 wall 을 채택했는데, 실제 `-q` 는
`cli.resolve_partition()` 이라는 **완전히 별도 경로**(`--queue` > sinfo > `accounts.json`)로 정해진다.
`grep` 확인: **`queue_selected` 를 읽는 코드가 패키지 전체에 0곳**이었다.
⟹ **sizing 은 `long`(120 h)을 가정해 게이트를 통과시키고, 제출은 `-q normal`(24 h)로 나간다.**
🔴 **그리고 그 무력화는 `long` 이 실존하는 순간 — 우리가 가장 기대를 거는 바로 그 상황 — 에 일어난다.**
§34.5 가 *"24 h 시나리오에서 게이트가 막아 설계대로 동작한다"* 고 적은 그 안전장치가 그때 꺼진다.

🟢 **고침**: **"게이트가 보는 큐 == 제출이 가는 큐"** 로 고정.
`build_plan(submit_queue=...)` 에 `cli` 가 `default_partition(env, args)` 를 넘긴다.
🔒 **더 긴 큐가 있으면 자동 전환하지 않고 알린다**(`longer_queue_available` + `--queue <이름>` 안내).
**큐 선택은 과금·접근권이 걸린 사이트 정책이라 코드가 조용히 정할 일이 아니다.**
불일치가 생기면 화면에 **"sizing 이 본 큐 ≠ 제출 큐 … wall-kill"** 경고를 크게 낸다.

### 37.3 🔴 중대 — override 가 게이트에 안 보였고, **표시와 제출도 갈렸다**
`ncpus_override`(`--ncpus-per-node` / `sizing.json`)가 **제출 시점(`build_spec`)에만** 적용됐다.
⟹ 계획 표와 게이트는 **덮이기 전 값**을, 제출은 덮인 값을 썼다 — **"보이는 것과 보내는 것이
다르다" 네 번째**다.
🟢 **고침**: `plan.ncpus_override_from_config()` 한 곳에서 계산해 **계획·게이트·제출이 같은 값**을 쓴다.
🔴 **그리고 P6 는 override 를 면제한다**(`item_cores_are_the_measurement`) —
**P6 의 코어 수는 사이징 파라미터가 아니라 측정 대상**이다. 적용되면 1/16/64 가 전부 같아져
S 가 무의미해지고, 런타임 게이트가 `[INVALID]` 로 버려 **예산 1,944 core-h 가 통째로 헛돈다.**
확인: `override=32` → `P1=32 P5=32` / **`P6_t1=1 P6_t16=16 P6_t64=64`**(면제됨).

### 37.4 사소 3건
- **`crest_path` 미사용** → 회신에 싣는다(**어느 CREST 를 썼는지**는 재현에 필요하다).
- **§34.2 서술 불일치** → §36 에서 항목 단위 차단으로 바꾼 뒤 문장을 안 고쳤다. 정정했다.
- **테스트 수 불일치** → 본 절 기준 **700**.
- 🟡 **tarball 재현 불가**(같은 소스도 sha256 이 매번 다름) → **규약으로 처리했다**:
  동일성은 `source_digest`. 빌드를 재현 가능하게 만드는 것(`tar --mtime` 등)은 **새 사양이라
  lead 승인 대기**.

### 37.5 되돌리기 실험 — 🔴 **첫 시도가 부분 되돌리기였다**
```
[H] normalize_rows 의 7개 필드 제거 + resolve_wall_limit 을 "가장 긴 큐"로 → FAIL 3건
[I] 🔴 그런데 seed 관련 2건이 안 깨졌다. 확인해 보니 **정규식이 `"seed"` 줄을 못 지웠다** —
    되돌리기가 **부분적으로만** 됐고 나는 그것을 "3건 깨짐"으로 넘길 뻔했다.
    ⟹ `"seed"` 줄만 정확히 제거해 재실험 → 그 2건이 정확히 깨짐(ERROR).
    ⟹ ADR-042(a) 대로 **존재 단언을 먼저** 넣어 FAIL 로 보고되게 바꿈.
복원 후 전체: Ran 700 tests OK (skipped 8) · [stamp] ✅
```
🔴 **교훈: 되돌리기 스크립트가 "적용됐는지"를 확인하지 않으면 부분 되돌리기가 통과한다.**
ADR-042 의 함정 (a)(파일이 깨짐) (b)(`__pycache__`)에 이은 **세 번째 형태**다.

### 37.6 상태
`700 tests OK` (skipped 8) · `[stamp] ✅` · **`source_digest ecdba8a324e2157a`**


---

## 38. ADR-052 큐 로직 삭제 + **생산자→소비자 경계 검사**

### 38.1 🔒 ADR-052 — **고치지 말고 지웠다**
사용자: *"`long` 은 존재하지만 **`normal` 이 48 h** 야. **`long` 은 사용하지 않고 `normal` 만**."*

§37 에서 나는 치명적-2 를 *"게이트가 제출 큐를 보게 배선"* 으로 고쳤는데, lead 판정은
**"배선하지 말고 지워라"** 였다:
> *"가장 안전한 코드는 없는 코드다. **발동 조건이 사라진 기능을 배선하는 것은 표면적만 늘린다.**"*

⟹ 큐 **선택** 로직을 지웠다(`longer_queue_available` = 항상 `None`).
🟢 **다만 wall 상한은 계속 읽는다**(ADR-036: 측정 가능한 것을 하드코딩하지 않는다).
🔴 그리고 **`normal` 이 48 h 가 아니면 크게 경고한다**(`queue_wall_surprise`) —
**사용자 말과 클러스터가 다를 수 있고, 그때 우리가 알아야 한다.**
🔒 **되살리는 법을 주석에 남겼다**: 다른 사이트로 이식하면 `longest_wall_queue()` 로 고르되
**반드시 그 큐를 실제 `-q` 로도 써라.** 둘을 따로 두면 이번 발산이 다시 생긴다.

### 38.2 🔴🔴 생산자→소비자 경계 검사 — **넣자마자 내 것을 잡았다**
lead 지시: *"같은 병이 네 번 났다(host / wall / P5 seed / queue_selected). 일회성 감사가
아니라 **테스트**로 막아라."*

`tests/test_producer_consumer.py` 를 넣고 돌리자마자:
```
sysprobe 가 수집했는데 아무도 읽지 않는 필드:
  ['engine_policy', 'modules_raw', 'modules_raw_note', 'queues_raw',
   'software_probe_note', 'user']
```
🔴 **`engine_policy`(ADR-050 엔진 정책)와 `modules_raw`(ADR-043 module 전문)는
이번 라운드에 내가 만든 것이다.** 두 ADR 의 **존재 이유 그 자체**인데 회신에 안 실리고 있었다.
**내가 고치던 병을 내가 그대로 저질렀다.** ⟹ `cli.build_env` + `report.py` 에 배선했고,
회신 JSON 에서 실제로 확인했다(`mopac 정책: allowed=False` 가 실린다).

**검사 구성**
| 검사 | 막는 것 |
|---|---|
| `TestSysprobeFieldsAreConsumed` | `collect_login` 이 만든 키를 아무도 안 읽으면 실패 |
| `TestPayloadArtifactsAreRead` | payload 가 쓴 아티팩트를 collector 가 안 열면 실패 |
| `TestKnownLostFieldsStayConsumed` | **이미 한 번 샌 4건**을 이름으로 못 박음(재발 방지) |

🔒 **면제에는 사유가 필수다**(`test_exemptions_carry_a_reason`). 사유 없는 면제는 검사를
껍데기로 만든다.

### 38.3 🔴 검사가 찾은 **휴면 유실 3건** (지금은 무해, 되살아나면 샌다)
| 아티팩트 | 지금 무해한 이유 | 되살아나는 조건 |
|---|---|---|
| `p3_attempt_quality.json` | **P3 가 ADR-049 로 계획에서 빠짐** | P3 부활 |
| `xtb_source.json` | 동상 (동봉본 vs 사이트본 **provenance**) | P3 부활 |
| `pystack.json` | **ADR-037 로 GPU 패키지 드롭** | GPU 패키지 부활 |
🔴 **셋 다 "고쳐서 무해한 게 아니라 안 돌아서 무해하다."** 화이트리스트에 그 사실을 사유로
적어뒀다 — **부활시키는 사람이 먼저 읽도록.**

### 38.4 되돌리기 실험
```
[J] 큐 선택 로직 복원                    → FAIL: test_no_queue_selection_happens_at_all
[K] report.py 의 engine_policy/modules_raw 배선 제거
                                         → FAIL: test_engine_policy_and_raw_modules_reach_the_report
복원 후: Ran 710 tests OK (skipped 8) · [stamp] ✅
```
🔴 **[K] 에서 내 예상이 틀렸다.** 나는 `test_every_collected_field_is_read_somewhere` 도 함께
깨질 것이라 적었는데 **안 깨졌다.** 이유: `engine_policy` 가 `cli.build_env` 에서는 여전히
참조되므로 **sysprobe 수준 검사는 통과**하고, **회신 JSON 까지 가는지는 그 검사가 안 본다.**
⟹ 🔴 **경계 검사는 "누군가 읽었다"까지만 보장하고 "최종 산출물에 실렸다"는 보장하지 않는다.**
그래서 `TestKnownLostFieldsStayConsumed`(이름으로 못 박는 검사)가 **대체가 아니라 보완**으로
필요하다. **문서에 쓴 예상을 실행으로 확인하지 않았으면 이 한계를 못 봤을 것이다.**

### 38.5 상태
`710 tests OK` (skipped 8) · `[stamp] ✅` · **`source_digest 308884324b43a963`**


---

## 39. critic `OK` 후 배치 — 빌드 출력 + 트립와이어 (§38 판정: `OK`)

critic3 가 `308884324b43a963` 에 **`OK` 유지** 판정을 냈고(되돌리기 실험 3종 직접 재수행 +
`collect_p1b`/`collect_p4` 확장 대조), lead 지시대로 **보류해 둔 두 건을 한 배치로** 넣었다.

### 39.1 ② 빌드 출력 — **사람이 먼저 보는 숫자를 바꿨다**
```
 ─────────────────────────────────────────────────────────────────
  source_digest : ecf8c7272aa15615   ← 🔒 동결·리뷰·인도본 동일성은 이 값으로
                  (소스 내용 해시. 소스가 실제로 바뀌어야 변한다)
 ─────────────────────────────────────────────────────────────────
  sha256 sei_pilot_cpu.tar.gz : e78cd0bc7585…
  ↳ sha256 은 **전송 무결성용**이다. 재빌드마다 바뀌므로 동일성 비교에 쓰지 마라.
```
🔴 **사고 경위**: 동결·리뷰 대상 지시를 tarball `sha256` 으로 내다가 **네 번 어긋났다.**
원인의 절반은 *"낡은 값을 인용한 것"* 이 아니라 **그 값이 애초에 동일성 지표가 아니었던 것**이다
— gzip 에 mtime 이 들어가 **같은 소스도 재빌드하면 sha256 이 달라진다.**
🟢 **도구(`build_stamp`)는 원래부터 내용 해시로 옳게 동작하고 있었다. 출력이 사람을 잘못된
숫자로 유도하고 있었다.** (가드 거부 화면이 `--max-core-hours` 를 권하던 것과 같은 부류다.)

### 39.2 ③ P1 최장 스테이지 트립와이어 — **계산이 필요한 안전장치는 발동하지 않는다**
`criteria/cost.py::longest_stage()` 신설 → `collect_p1` 이 `res["longest_stage"]` 로 싣는다.
```
{"stage": "ts_qst2", "wall_h": 41.0, "tripwire_h": 40.0, "exceeds_tripwire": true,
 "note": "🔴 … engineer 사전 확약에 따라 P1 계 축소(C)를 proposer 에게 올려야 한다.
          체인 링크를 늘려도 구제되지 않는다 — 단일 단계는 쪼개지지 않기 때문이다."}
```
🔴 **왜 파생값을 따로 싣는가**: `breakdown` 에서 계산해 낼 수 있지만, 이 프로젝트에서
**"값은 있는데 아무도 안 본" 사례가 여섯 번** 났다. **일곱 번째를 자초하지 않는다.**
🔴 기록이 없으면 `exceeds_tripwire = None`(**"안전"이 아니라 판정 불가**, ADR-036).
⚠ 트립와이어가 얇다: `[ESTIMATE]` 최악 칸 **47.8 h** (48 h 상한에 여유 0.2 h).

### 39.3 🔴 critic3 신규 발견 (비차단) — `collect_p4` **필드 단위** 유실
`p4_result.json` 은 **파일은 열리는데** `gpu_error / gpu_failure_class /
**gpu_fix_hint**(symptom·pip·why·ld_library_path) / memscan_* / oom_error /
n_basis_functions / gpu_count / cpu_reference_machine` 등 12개가 `criteria/p4.py` 에서 안 읽힌다.
**특히 `gpu_fix_hint` 는 GPU import 실패 시 구체적 pip 처방인데 통째로 사라진다** — 없으면 왕복 하나를 더 쓴다.
🟢 **ADR-037(GPU 드롭)로 지금 무해.** 화이트리스트에 사유와 함께 등록하고
**`pystack.json` 과 함께 고치라**고 상호 참조를 걸었다.
🔴 **그리고 내 경계 검사의 한계가 여기서 드러났다: 파일 단위만 보고 필드 단위는 못 잡는다.**
**critic 이 사람 손으로 잡았다.** 그 한계를 화이트리스트 주석에 적어 뒀다.

### 39.4 되돌리기 실험
```
[L] longest_stage 의 exceeds_tripwire 를 항상 False 로 → ast 정상 → FAIL: test_tripwire_fires_above_40h
복원 후: Ran 714 tests OK (skipped 8) · [stamp] ✅
```
⚠ **박스 부하가 높아(load average 22, 다른 agent 동시 실행) 전체 스위트가 25 s → 330 s 로
느려졌다.** 코드 문제가 아니다 — 개별 파일은 여전히 0.004 s 다.

### 39.5 상태
`714 tests OK` (skipped 8) · `[stamp] ✅` · **`source_digest ecf8c7272aa15615`**
🔒 **critic3 부분 재확인 대기**(변경 2건: 빌드 출력 · 트립와이어 필드).


---

## 40. 🔴 트립와이어가 **자기 존재 이유를 어기고 있었다** (critic3 지적)

### 40.1 무엇이 틀렸나 — **가장 아이러니한 결함**
§39 에서 나는 *"계산이 필요한 안전장치는 발동하지 않는 안전장치다"* 라며 최장 스테이지를
단일 필드로 뽑았다. critic3 가 그 한 줄을 지워봤다:
```
collect.py 의  res["longest_stage"] = cost.longest_stage(recs)  제거
  → 🔴 **718건 중 단 한 건도 안 깨졌다**
```
`longest_stage()` 단위 테스트 4건은 전부 **함수를 직접** 부르고,
**`collect_p1()` 을 거쳐 최종 결과까지 가는지는 아무도 안 봤다.**
⟹ 🔴 **ADR-041 이 겨냥한 그 구멍이, "측정해 놓고 안 쓰는 값"을 막으려고 만든 안전장치
자신에게서 재발했다.** 내가 직접 재현해 확인했다.

### 40.2 그리고 절반만 고쳐져 있었다 — **사람이 읽는 채널이 빠졌다**
같은 `collect_p1()` 안에서 **세 줄 위**의 `degraded_reasons` 는 이렇게 한다:
> *"필드는 코드가 읽고 `warnings` 는 사람이 읽는다 — **둘 다 필요하다.**"*

**트립와이어는 그 패턴을 안 따랐다.** `exceeds_tripwire: true` 가 나와도 `warnings[]` 에
아무것도 안 남아, 받는 사람이 **`pilots[].longest_stage` 를 따로 뒤져야** 했다.
⟹ **"사람이 뒤져야 하는 안전장치"를 절반만 없앤 셈이다.**

🔴 **그리고 이건 가상의 엣지케이스가 아니다**: `[ESTIMATE]` 최악 칸이 **47.8 h** 로
트립와이어(40 h)에 **여유 0.2 h** 뿐이라 **이번 제출에서 실제로 발동할 개연성이 낮지 않다.**

### 40.3 고친 것
```python
res["longest_stage"] = cost.longest_stage(recs)
if (res.get("longest_stage") or {}).get("exceeds_tripwire"):
    res.setdefault("warnings", []).append(res["longest_stage"]["note"])
```
+ **진입점 테스트 4건**(`TestTripwireReachesTheFinalResult`): **디스크에 진짜 `stages/*.json` 을
놓고 `collect_p1()` 호출** → 필드 도달 / 발동 시 `warnings[]` 도달 / 오경보 없음 /
**회신 JSON 까지 도달**.

### 40.4 되돌리기 — **두 줄을 각각** (critic3 요구)
```
[M] res["longest_stage"] 적재 줄 제거   → FAIL 1 + ERROR 3   (총 4건)
[N] warnings 확장 줄만 제거             → FAIL 2  (사람 채널 2건만 정확히)
복원 후: Ran 718 tests OK (skipped 8) · [stamp] ✅
각 되돌리기마다 **적용 여부를 먼저 단언**했다(함정 (c) 대비): "남은 개수 = 0" 출력 확인.
```
⚠ [M] 의 3건은 `ERROR`(KeyError)다 — 존재 단언을 앞에 둔 것은 1건뿐이라 나머지는 인덱싱에서
터진다. **FAIL 1건이 있어 증거로는 충분하지만, 내 기준(ADR-042(a))에는 미달이다.** 정직하게 적는다.

### 40.5 🔴 이번 라운드가 남긴 것 — **검사의 한계 3종**
```
1차 (내가 발견)      : 소비는 보장, **최종 산출물 도달은 미보장**
2차 (critic 발견)    : **파일 단위만 보고 필드 단위는 못 잡는다**
3차 (critic 발견)    : **안전장치 자신이 그 검사망 밖에 있었다**
```
🔴 **세 한계 모두 "돌려 보고" 찾았지 설계로 예측하지 못했다. 그리고 셋 다 사람이 잡았다.**
⟹ **검사는 사람을 대체하지 않고 사람이 볼 곳을 줄인다.**

### 40.6 상태
`718 tests OK` (skipped 8) · `[stamp] ✅` · **`source_digest ca757f4cfac0d30c`**


---

## 41. 🔴 동봉 README 가 코드와 **전 항목 불일치** (lead 발견) + 테스트가 빌드를 죽였다

### 41.1 무엇이 틀렸나 — **ADR-041 의 사용자 대면판**
lead 가 tarball 을 풀어 **사용자가 실제로 받는 파일**을 읽었다:
```
                  README        실제 코드
core-h 상한       5,000         21,000
wall 상한         24 시간        48 시간
총 계산량         2,694.8       ~19,000
항목표            P3 있음        P3 없음(ADR-049)
                  P6 없음        P6_t1/t16/t64  ← **κ 측정. RT-1 의 존재 이유**
```
🔴 **부품(`budget.py`/`plan.py`)은 critic3 가 검증한 대로 맞았다. 사람이 읽고 행동하는 면이
틀렸다.** *"부품은 맞고 조립선이 값을 떨어뜨린다"* 의 **사용자 대면판**이다.

🔴 **왜 비싼가**: 사용자는 README 를 보고 **할당량을 신청**한다. *"5,000 상한"* 을 읽고
19,000 이 예약되면 제출을 멈추거나, 더 나쁘게는 **할당을 4배 작게 신청한다.**
⚠ 그리고 **사용자가 이미 한 번 지적했다**(*"README 를 업데이트해"*). 그때 갱신된 문서가
**그 뒤에 정해진 재실행 사양을 따라오지 못했다.**

### 41.2 고친 것 — 수치를 **코드에서 파생**시켰다
`README_USER.cpu.md` 를 다시 썼다. **손으로 옮겨 적지 않았다** — `budget.py`/`plan.py` 로
실제 계획을 세워 나온 값을 넣었다(계산 노드 64 core/node · `normal` 48 h 기준):
```
예상 소비 16,679 core-h · 예약(천장) 19,091 · guard 21,000 / wall 48 h
항목: probe×3 · P1 9,216 · P1b 4,738 · P5 3,128 · P6_t1/t16/t64 24/384/1,536
```
**새로 넣은 것 2가지:**
- 🔴 **P6 가 무엇을 재는지** — *"같은 계산을 1/16/64 스레드로 3번 돌려 이 노드가 몇 배 느린지(`κ`)와
  G16 이 몇 스레드에서 꺾이는지(`S`)를 잰다. **이 두 값이 전체 계산 규모 산정의 단위다.**"*
  + **"P6 를 빼지 마세요"** 경고. 빼면 나머지가 *"몇 배 단위인지 모르는 숫자"* 가 된다.
- 🔴 **wall 이 48 h 가 아닐 때의 행동 지침** — *"제출하지 마시고 알려 주세요"*, 그리고
  dry-run 이 띄우는 경고 문구(`[UNVERIFIED]`)를 **그대로 인용**해 무슨 뜻인지 연결했다.

### 41.3 🔒 검사를 붙였다 — `tests/test_readme_matches_code.py` (8건)
README 에 **기계 검증 블록**(`SPEC-BLOCK`)을 두고 코드 상수와 대조한다.
`guard / wall / 항목 목록 / 예약·전망 합계` + **낡은 리터럴 재유입 거부**(`5,000 core-hour`,
`2,694.8`, `**24 시간**`) + **P6 설명 존재** + **48 h 행동 지침 존재**.

**되돌리기 (양방향):**
```
[O] 코드만 바꿈(guard 21000→17000) → FAIL 3건 (guard·항목·합계)
[P] README 의 SPEC-BLOCK 삭제      → FAIL 5건 (**test_spec_block_is_actually_parsed 포함**)
복원 후 8건 OK
```
🔴 **[P] 가 중요하다**: lead 가 경고한 *"새 검사를 만들면 그 검사 자신이 검사망 안에 있는지
먼저 확인하라"* 를 시험한 것이다. **검증 대상이 사라지면 조용히 통과하지 않고 RED 가 된다.**

### 41.4 🔴 그리고 빌드가 죽었다 — **테스트가 환경을 오염시켰다**
```
cp: error writing '…/inputs/p5_species/…': No space left on device
/tmp  3.7G  100% 사용
```
원인: **`tests/test_account_submission.py` 에 `tearDown` 이 하나도 없었다.**
`mkdtemp` 로 만든 디렉터리를 매 테스트마다 남겨서 **`/tmp` 에 `sei_acct_*` 가 2,130개** 쌓였다.
⟹ **코드 결함이 아니라 테스트가 환경을 오염시켜 빌드를 막은 형태다.**
🔴 **그리고 빌드가 중간에 죽으면 `dist/` 가 `.stale.*` 로 옮겨진 채 남는다** —
**인도본이 제자리에 없는 상태**가 된다(복구는 `.stale` 에서 하면 된다. 이번에 그렇게 했다).
🟢 고침: `tearDown` + `addCleanup` 추가. 실행 전후 임시 디렉터리 **증가 0** 확인.

### 41.5 검증 — **인도본(tarball 추출본)에서**
```
21,000 core-hour 1 · 48 시간 1 · P6_t1 2 · "빼지 마세요" 1 · "제출하지 마시고" 1 · 16,679 2
P3 잔존 0 · "5,000 core-hour" 잔존 0
Ran 726 tests OK (skipped 8) · [stamp] ✅
```

### 41.6 상태
`726 tests OK` · `[stamp] ✅` · **`source_digest 79624c4f182e8c14`**


---

## 42. 🔒 빌드 후 산출물 검증 관문 — **검사와 인도물 사이의 구멍**

### 42.1 구멍 (lead 발견, critic3 권고, 내가 조사)
```
검사 대상 : src/pilot_package/README_USER.cpu.md      ← mv 이전
사용자    : tarball 안 sei_pilot_cpu/README_USER.md   ← mv 이후
build_stamp.py 의 tarfile 참조 : 0건                   ← tarball 을 여는 경로가 아예 없었다
```
⚠ **정확히 적는다 — lead 가 자기 표현을 정정했고 그 정정이 옳다:**
*"이번에 복사 도중 빌드가 죽었다"* 는 사실이지만 **"방어선이 뚫렸다"는 과장**이었다.
`make_package.sh:5` 의 `set -eu` 가 잡아 **빌드가 죽었고 깨진 tarball 이 나가지 않았다.**
⟹ 🔴 **지금 노출된 것이 아니라 방어선이 얇은 것**이다. 남는 위험은 `cp` 가 exit 0 을 내며
부분 실패하는 경로와, 향후 리팩터로 `set -e` 가 깨지는 경우다.

### 42.2 🔴 두 사람이 **각각 절반씩** 옳았다
```
critic3 "검사를 추가하라"                  ← 무엇을 검사할지
lead    "빌드가 자기 산출물을 검사 못 한다"  ← 언제 검사할지
```
critic 권고만 넣으면 `make_package.sh` 안에서 tarball 이 `.stale` 로 치워져 **항상 skip** 된다
(교착 회피를 위해 **의도적으로** 그렇다). ⟹ **인도물이 만들어지는 바로 그 순간에만 눈을 감는
검사**가 된다. **둘을 함께 해야 보호가 된다.**

### 42.3 넣은 것
| | |
|---|---|
| `TestPackagedReadmeMatchesCode` (4건) | **tarball 을 열어** `code_truth()`/`spec_block()` 재실행 + **소스와 바이트 동일** 확인. tarball 없으면 skip(교착 회피 유지) |
| `TestBuildGate` (2건) | 관문의 **존재와 순서**(`tar czf` 뒤) 고정 + **표시가 있으면 `build_stamp check` 가 ✅ 를 못 내는지** |
| `make_package.sh` `[6/7]` | `tar czf` **뒤에** 그 검사만 지목 실행. 실패 시 `VERIFICATION_FAILED.json` + `exit 1` |
| `build_stamp.py` | 표시가 있으면 **가장 먼저** 보고 절대 ✅ 를 내지 않는다 |

🔒 **실패 시 거동은 (다) — 남긴다**(lead 판정):
- **(나) `.stale` 복구는 범주적 배제** — 낡은 tarball 과 낡은 스탬프가 **서로 일치**해
  `check` 가 ✅ 를 낸다. **실패가 완전히 건강해 보인다(최악).**
- **(가) 삭제는 실패를 지운다** — *"아직 안 만들었나 보다"* 로 오독된다.
🔴 **표시 파일만으로는 부족하다**(lead 요구): *"다음 사람이 그 파일을 본다"* 는 **습관**에
기대게 된다. ⟹ **사람들이 이미 돌리는 게이트**(`build_stamp check`)가 대신 말한다.

### 42.4 되돌리기 (2건 + 실사고 1건)
```
[Q] 관문 자체를 제거        → FAIL: test_gate_exists_and_runs_after_packaging
[R] tarball 안 README 만 오염 → 인도물 검사 FAIL 2건,  🟢 **소스 검사는 8건 OK 그대로**
                               ← 이것이 이번에 닫은 구멍의 정확한 형태다
복원 후: Ran 732 tests OK · [stamp] ✅
```

### 42.5 🔴 자진신고 — **관문의 첫 판이 오작동했다**
첫 구현은 저장소 루트에서 `python3 -m unittest tests.test_readme_matches_code....` 로 불렀는데,
그러면 `import context` 가 `ModuleNotFoundError` 로 죽고 **unittest 는 그것을 "테스트 1건 실패"로
보고한다.** ⟹ **검증이 실패한 것처럼 보이지만 실은 실행조차 안 된 상태.**
```
[6/7] 산출물 검증 … Ran 1 test … 🔴 산출물 검증 실패   ← 오작동
```
🟢 **다행히 실패 쪽으로 틀려서 눈에 띄었다.** 반대로 틀렸으면(항상 통과) **이 관문은 처음부터
장식이었을 것이고 아무도 몰랐을 것이다.**
🟢 **그리고 그 오작동 덕에 표시 파일 → `build_stamp check` 거부 경로가 실제로 작동하는 것을
계획에 없이 확인했다** — `check` 가 ✅ 대신 *"이 dist/ 는 산출물 검증에 실패한 상태다"* 를 냈다.
🔒 고침: `tests/` **안에서** 실행. 지금은 `Ran 4 tests … OK`.

### 42.6 상태
`732 tests OK` (skipped 22 — 그중 4건이 빌드 전 게이트에서 skip 되는 인도물 검사) · `[stamp] ✅`
🔴 **`source_digest 79624c4f182e8c14` — §41 과 동일하다.** 이번 변경은 전부
`tests/` · `make_package.sh` · `build_stamp.py` 로 **`pilot_package/` 밖**이라
**critic3 가 승인한 인도물 내용은 바뀌지 않았다.**


---

## 43. 🔒 관문을 **자동 발견**으로 — *"사람이 기억해야 작동하는 보호"* 제거

### 43.1 lead 가 자기 범위 지정을 정정했다
```
blind window during build   : skipped 22 − 8 = **14 tests**
covered by the §42 gate      : 4
⟹ TestM2DecisionReachesTheTarball was inside the uncovered 10
```
🔴 **CORRECTION (lead measured; my earlier report overstated this).**
I wrote `14 → 4 → 10 → now 0`. **The blind window is not 0 across the board.**
```
14  → gate now covers 8  → **artifact-assertion blind window: 0**
                           **tool-guard coverage: still outside the build**
still skipped in build state and NOT discovered by the gate:
    TestStampRecordsContentHash (2) · TestWrongRootIsNotReportedAsStale (2)
```
They are not discovered because they **do not open tarballs** — they assert on stamp/sha256
semantics. 🔒 **So the discovery criterion is self-consistent, but the set it defines is narrower
than the property we actually care about: "opens a tarball" ≠ "depends on the built artifact."**

🟢 Why this is **not** reopened (lead's reasoning, and the reason is not schedule):
`make_package.sh:148` runs `build_stamp.py check` at `[7/7]`, so **the tool those tests exercise
does run inside the build.** What remains uncovered is *tests of the tool*, not assertions about
the artifact.
⚠ **Second-order, next-round list, name only — do not act**: running a tool does not verify that
tool's own guards.
🔴 **그 클래스는 lead 가 낡은 추출본을 보고 오판한 사고 때문에 생긴 것이다.**
⟹ **빌드는 여전히, 이미 한 번 일어난 사고 유형을 자기 산출물에서 못 보고 있었다.**

🔴 **그리고 더 근본적인 지적**: 관문이 클래스 이름을 적어 두면
*"앞으로 tarball 을 여는 검사를 새로 만드는 사람은 관문에도 손으로 추가해야 하고 언젠가 잊는다.*
**우리가 방금 없앤 것이 바로 그 형태다 — '사람이 기억해야 작동하는 보호'."*

### 43.2 고친 것 — `tests/packaged_gate.py`
**이름을 적지 않는다.** AST 로 **실제로 tarball 을 여는**(`tarfile.open(`) 클래스를 찾아 전부 돈다.
```
make_package.sh [6/7]:  cd tests && python3 -m unittest -q packaged_gate
발견 결과            :  TestM2DecisionReachesTheTarball · TestPackagedReadmeMatchesCode
관문 실행량          :  4건 → **8건**
```
🔒 **규약 18 적용 — 고장 시 넘어지는 방향을 정했다**: 발견이 **0개면 예외를 던진다.**
발견이 조용히 비면 관문은 *"돌 것이 없다"* 며 **통과**하고, 그건 **있다고 믿게 만들어서 없는 것보다 나쁘다.**

**동반 검사 4건**(`TestBuildGate`):
관문 존재·순서 / **호출 줄이 클래스 이름을 하드코딩하지 않는가** / 발견 집합 == 실제 집합 /
**이미 사고를 겪고 만든 검사가 관문 안에 있는가**(이름으로 못 박음).

### 43.3 되돌리기 — lead 요구 (3) 그대로
```
[S] 새 tarball-여는 클래스를 추가하고 **아무 데도 배선하지 않음**
    → 발견 목록에 자동 포함 → 관문 RED (failures=1)  ✅ 잊어도 작동한다
    → 파일 제거 후 관문 OK
```

### 43.4 🔴 그 실험이 **내 검사의 자기지시적 오탐**을 드러냈다
`[S]` 실행 중 발견 목록에 **`TestBuildGate` 자신**이 끼어 있었다.
원인: 판정 기준이 `"tarfile.open"`(문자열)이었는데, **그 토큰을 검사하는 코드 자신이 그 토큰을
품고 있다.** ⟹ **검사기가 자기를 검사 대상으로 삼았다.**
🔒 고침: 판정 기준을 **`tarfile.open(`**(여는 괄호까지)로 좁혔다. 발견이 정확히 2개로 돌아왔다.
🟡 전임도 같은 형태를 밟았다(인수인계 §0.2b-5: **중복 검사기를 시험하려고 그 검사기 자신을
중복시켰더니 검사기가 사라졌다**). **자기지시적 오탐은 이 프로젝트에서 두 번째다.**

### 43.5 상태
`735 tests OK` (skipped 22) · `[stamp] ✅` · 관문 `Ran 8 tests OK` · 표시 없음
🔴 **`source_digest 79624c4f182e8c14` — §41 이후 불변.** 이번에도 변경은 전부
`tests/` · `make_package.sh` 로 **`pilot_package/` 밖**이다. **인도물 내용은 그대로다.**


---

## 44. 🔴🔴 RT-1 cluster failure — the module name was truncated. **Three defects, not one.**

### 44.1 What happened
Every Gaussian item died in ~6 s:
```
ModuleCmd_Load.c(208):ERROR:105: Unable to locate a modulefile for 'gaussian/g16.c01.lin'
⟹ P1, P1b, P5, P6_t1/t16/t64 all failed. κ, S and the TS unit cost: unmeasured.
```
Cost: **time, not budget** — the jobs died immediately.

### 44.2 🔴 Defect 1 — `rstrip` used as if it removed a suffix (`sysprobe.py:484`)
```python
tok = tok.rstrip("(default)")     # strips any trailing char in the SET { ( d e f a u l t ) }
"gaussian/g16.c01.linda" → "gaussian/g16.c01.lin"     a module that does not exist
```
🔴 **Why review missed it**: on the real cluster this line altered **13 tokens and 10 were altered
correctly** — they really did end in `(default)`. Only the three `gaussian/*.linda` entries were
corrupted, and the corruption produced a **plausible** name.
🟢 Fixed with `strip_module_markers()` — removes markers as **suffixes**, never as a char set.
🟢 **Audit of every `strip/rstrip/lstrip` with an argument in the package**: **5** call sites,
**only this one was wrong**.
🔴 **CORRECTED: I first reported 4 and missed `criteria/g16.py:185` `line.strip().lstrip("#")`**
(critic3 caught it). Single-char argument, same reasoning as `name.rstrip("*")` ×2 — so the
**safety conclusion is unchanged**, but the count in my report was wrong.
(`plan.py` `.strip(" /")` is a genuine char set.)

### 44.3 🔴 Defect 2 — **the truncated names were baked into config**
`config/env_paths.json` carried the parser's output as ground truth:
```
default   gaussian/g16.c01.lin      ❌ does not exist
fallbacks g16.b01.lin ❌ · g16.a03.lin ❌ · g16.a03 ✅   ← only the last one was real
```
🔴 **Fixing the parser alone would NOT have fixed the run.** The job requests the configured name.
🟢 Corrected to the measured names (`*.linda`), with the incident recorded in `_default_source`.

### 44.4 🔴 Defect 3 — `module load`'s exit status was treated as success
The reply says `module_state: "loaded"` for a module that **does not exist**: on this site
`module load` printed `ERROR:105` and still exited 0. So we never fell through to the fallbacks —
**`gaussian/g16.a03`, which works, was in the list and never tried.**
🟢 Fixed: the success criterion is now **"the binary appears and is executable"**, and the payload
**walks the candidate list**, recording `modules_tried` in the reply.
🔒 This is lead's criterion — *"could a wrong-but-plausible module name survive to submission
again?"* — answered structurally: a wrong name now fails over to a working one.

### 44.5 🔴 Defect 4 (found while fixing) — **our tests had frozen the bug's output as truth**
`test_gaussian_module_priority.py` fixtures asserted `gaussian/g16.c01.lin` etc.
**The tests were green while encoding a module name that does not exist.**
⟹ Corrected against the cluster reply, with provenance noted in the file.
🔒 New regression `tests/test_module_name_truncation.py` uses a fixture **verbatim from
`cluster.modules_raw`** — not hand-written, because a hand-written fixture would encode what we
imagined the cluster prints. **Per ADR-042 it fails on the pre-fix code** — and the count depends on *which* pre-fix state
you emulate, so both are recorded here rather than one bare number:
```
call site only reverted (helper left intact)  → 2 failures   (the .linda assertions)
FULL pre-fix (helper body AND call site)      → 5 failures   ← the honest figure
   + the 3 from TestFixIsNotLindaSpecific / test_helper_removes_suffix_not_character_set
```
🔴 **CORRECTED: I reported 2. The written record must say 5.** My "2" was measured *before*
`TestFixIsNotLindaSpecific` was added at lead's request, and I never re-ran the revert against the
grown file — and my rerun reverted only the call site, which leaves the helper-level tests passing.
🔒 **A revert result has a shelf life**: it is evidence about the file *as it stood when it ran*.
If the test file grows afterwards the number is stale even though nothing was wrong.
**Re-run reverts after the test file changes** — third stale-measurement shape logged.
🟢 Net effect is in our favour: the guard is **stronger** than I reported, not weaker.

### 44.6 🔴 And the build died twice — **our own test suite filled `/tmp`**
```
tests leaking temp dirs: test_pbs_script_shape (8, incl. a module-level helper called 12×/run)
                         test_gaussian_module_priority (1) · test_g16_adapter (1)
⟹ /tmp 100% → `cp` failed → build aborted → dist/ left moved aside in .stale.*
```
🟢 Fixed: `addCleanup` per test; the module-level helper now uses **one temp root + `atexit`**.
**Measured: temp-dir count before == after a full suite run (was +14).**
🔴 **This has now blocked two builds.** The next-round item *"disk-space preflight in
make_package.sh"* is no longer hypothetical.

### 44.7 🟢 What held
- `throughput_probe` / `queue_wait_probe` succeeded: **200/200 jobs on 200 distinct hosts, 0 rejected.**
- 🟢 **`longest_stage.exceeds_tripwire` came back `null`, not a pass.** **Rule 18 held under a real
  incident** — the gate fell toward "unknown". First time one of our gates was tested by a live failure.
- 🟢 `normal` wall **48.0 h confirmed by `qstat -Qf`** — the §R22/§R24 assumption is measured now.
- 🟢 MOPAC genuinely absent (ADR-043 stands, uncorrupted by this bug).

### 44.8 State
`743 tests OK` · `[stamp] ✅` · **`source_digest b8375e9d18326553`** (unchanged — the additions
were tests only)

### 44.9 🔴 The fixture had to be widened, and the first revert experiment was invalid
lead: *"A fixture with only `c01.linda` would pass with a fix that special-cases `linda` — which is
the same class of error as the original."*

**Widened**: the fixture is now every line of `cluster.modules_raw` carrying a gaussian entry or a
keyword-matching `(default)` token — **13 lines, containing all three `*.linda` names and all ten
legitimate `(default)` tokens** (10 is the exact count in the real reply).
**Added** `TestFixIsNotLindaSpecific`: all ten strips must still happen, and arbitrary names built
from the old `{ ( d e f a u l t ) }` charset (`tool.ault`, `tool.fated`, `tool.deft`, `x.lua`, …)
must survive. `linda` was only one instance of that class.

🔴 **My first revert experiment was invalid and I nearly drew a conclusion from it.**
I injected an early `return` for names ending in `linda` **on top of the corrected logic**, so the
general path underneath was still right and the suite passed. That does **not** reproduce
"a fix that special-cases linda". Redone faithfully — old `rstrip` + a `linda` exception — it fails
**3 tests**. ⟹ ADR-042(a) again: *an experiment that does not reproduce the hypothesis proves
nothing, in either direction.*

---

# §45 — EXIT FLUSH (coder2). Delta only: what is not in §0–§44.

I am being shut down. A teammate is not restorable, so this is what a successor would otherwise
have to rediscover. **Nothing here restates §0–§44.**

## §45.1 Site behaviours learned this session, not written elsewhere

🔴 **`modules_raw` has no `| head -400`. Do not put it back.**
The truncation was there to keep logs small. It is the reason the module list looked short, and a
short list is what made the wrong names look like the only names. Someone will re-add a `head` to
tidy the log. **The log being large is the feature.**

🔴 **The tarball's `sha256` is not reproducible; `source_digest` is.**
gzip writes the mtime into the stream, so rebuilding identical sources yields a *different*
`sha256`. ⟹ **two different sha256 values do not mean the sources differ**, and we burned time
twice believing they did. `source_digest` is a content hash over the source tree and is the only
identity claim to make. (It is also, per §44.5, what caught the contaminated restore.)

🔴 **`.stale.*` is a build artefact, not a leftover.** `make_package.sh` moves the old tarball
aside before running the suite — otherwise "dist is stale" fails the suite, which aborts the build,
which can never refresh dist. If you find `dist/` empty and a `.stale.*` beside it, the build
**aborted mid-flight** (twice: disk full). It looks exactly like "never built". Check for
`VERIFICATION_FAILED.json` and `.stale.*` before concluding anything.

## §45.2 First five minutes, next coder

```
1. Read §0. Then run:  python3 src/build_stamp.py check --root .
   Believe nothing about the tree until that prints ✅.
2. source_digest is identity. sha256 is not (§45.1).
3. docs/ belongs to other agents. src/ and tests/ are yours.
4. Absence is never established by grep (ADR-043). Run the generator and look at the output.
5. A regression test does not exist until you have watched it fail on FULL pre-fix code —
   helper AND call sites. And write down WHICH revert produced the number (§44.5).
6. Never snapshot mid-experiment (Rule 25).
```

## §45.3 🔴 Where I would look first if the re-run fails again — including hunches

Ordered by my own suspicion, highest first. **None of these are verified on the cluster**; they are
the places where our evidence stops.

1. **`command -v g16` proves a binary is on PATH. It does not prove Gaussian runs.**
   A wrapper script, a missing licence, or a broken Linda install all pass our check. Our success
   criterion moved from "module exit status" to "binary present" — that was the right direction but
   it is still a *proxy*. **The first real job is the first proof.** If jobs fail instantly with
   a licence or `l1.exe` error, this is the line, not the module logic.
2. **The `.linda` variant may want Linda-specific launch.** We treat `g16.c01.linda` as ordinary
   g16 with threads. If it wants `%NProcLinda`/`%LindaWorkers`, symptoms are: dies immediately, or
   runs but uses 1 core. **Symptom to check first: wall-clock ≈ 64× the expected single-core time.**
3. **Candidate-walk environment residue.** On a failed candidate we `module unload` and try the
   next. If `unload` is a no-op or partial on this site, candidate N+1 loads into a polluted
   environment. `modules_tried` in the ledger tells you the order actually taken — read it before
   theorising.
4. **κ and S are still unmeasured.** Budgets are forecasts. The guard binds on the *reserved*
   ceiling so we cannot overspend, but individual tasks can still hit the wall if S is much worse
   than assumed. **P6 is what measures S. If P6 is skipped or dropped, every downstream number is
   unanchored** — that is why README says "do not remove P6".
5. **Per-task `hostname` → `n_nodes`.** Costs nothing, but I have never seen PBS return these for
   a real array here. If every task reports the same host, `n_nodes` is wrong, not the cluster.

## §45.4 Code that is correct for a reason only I know — i.e. the lines someone will "simplify"

| Line | Why it is that way |
|---|---|
| `min_wall_h` floors are **not** used to absorb budget variance | Floors inflate the reserved ceiling, and the guard binds on the ceiling. Raising a floor to "make the numbers fit" spends real allocation. |
| Fallbacks are `null`, never `0`/`false` (ADR-036) | `0` reads downstream as *a measurement of zero*. `null` reads as *not measured*. Someone will "clean up the JSON". |
| `exceeds_tripwire: None` when there are no records | Not `False`. `False` means "checked, fine". With no records nothing was checked, and a `False` here makes the trip-wire pass silently forever. |
| Array tasks hardcode 1 core; gate (b) asserts all links == 1 | Deliberate, not an oversight. |
| `packaged_gate` **raises** when discovery finds 0 classes | Rule 18. An empty discovery that passes is worse than no gate — it manufactures confidence. |
| `build_stamp.check()` reads `VERIFICATION_FAILED.json` first and never returns ✅ while it exists; early returns **prepend** to `problems` | A later `return` that replaces the list would erase the earlier finding. |
| The module tests use real PATH shims | See §0. Do not convert them to Python mocks. |

## §45.5 What I am least sure of, stated plainly

**I verified the end state by measurement, not by narrative.** For the contamination episode
(§44.5) I could not reconstruct the ordering and did not try to. If something surfaces that implies
an edit I have no record of, **trust the tree and the digest over anything written above.**
