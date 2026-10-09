# Review Log

> critic 소유. 여기에만 append 한다. 다른 문서는 읽기 전용.

---

## 2026-08-17 — 1차 리뷰: `src/pilot_package/` 전체 (파일럿 인도 패키지)

**대상**: `src/pilot_package/` (sei_pilot 파이썬 모듈 + payload/*.sh + templates + inputs)
**산출물**: `src/dist/sei_pilot_package.tar.gz`
**방법**: 정적 검토(우리 환경에 스케줄러/QC/GPU 없음, ADR-004). budget.py/plan.py/cli.py/
scheduler.py/state.py/collect.py 전문 통독 + payload/*.sh 전문 통독 + criteria/p1,p2,p4.py +
xyzgraph.py + inputs/*.json 통독. tests/test_plan_report_e2e.py, test_state_scheduler.py에서
관련 테스트 존재 여부 확인(존재 = 커버됨, 부재 = 미검증 표시).

## 판정
**FIX-THEN-RUN** — 사용자에게 지금 보내면 안 된다. BLOCKER 1건이 P1(패키지의 핵심
목적물: S3 단가 스프레드 8배→3배 축소 실측)의 신뢰도를 직접 훼손한다. 코드 수정은
국소적(payload 셸스크립트 3개 + collect.py 소폭)이라 왕복 1회 안에 고칠 수 있는 규모다.

---

## BLOCKER

### B-1. `payload/P1.sh`(및 `P1b.sh`, `P3.sh`)가 자기 연쇄(chain) 재실행 시 **전체 워크플로를
처음부터 다시 돈다** — 체크포인트가 전혀 없다

- **근거 파일**: `sei_pilot/plan.py:160-173`(`size_job`), `sei_pilot/scheduler.py:141-160`
  (`Adapter.submit_chain`), `sei_pilot/templates/slurm.sh.tmpl:16`(`SEI_KEY={{KEY}}`),
  `payload/common.sh:64-67`(멱등성 판정이 `${SEI_KEY}.done.json` 기준), `payload/P1.sh`(전문,
  단계별 완료 마커 없음), `payload/P1b.sh`, `payload/P3.sh` 동일.
- **[확인]** `submit_chain`은 링크마다 **다른 key**를 쓴다
  (`spec.key if i==0 else "%s_c%d" % (spec.key, i)` — 예: `P1`, `P1_c1`, `P1_c2`).
  `common.sh`의 멱등성 판정은 `sei_state_dir()/${SEI_KEY}.done.json` 존재 여부만 본다.
  즉 **링크마다 다른 마커 파일을 보므로, 링크 0이 끝났다는 사실을 링크 1이 알 방법이
  common.sh 층에는 없다.** 이 설계가 성립하려면 payload 자신이 "이미 다 했다"는 것을
  어떤 형태로든 기록하고 재실행 시 건너뛰어야 하는데, `payload/P1.sh`를 처음부터 끝까지
  읽어도 그런 로직이 **전혀 없다.** CREST → NEB-TS → TSOpt(NumFreq) → Freq → IRC를
  스크립트가 실행될 때마다 무조건 처음부터 돌린다(각 단계 앞에 "이미 결과 파일이
  있으면 건너뛴다" 같은 검사가 없음). `P1b.sh`(SP/gradient/Hessian/opt5 ×2 level)와
  `P3.sh`(xTB 열거+시도)도 동일 구조 — 재실행 시 처음부터 다시 돈다.
  대조군: `payload/P2.sh`는 CP2K의 `EXT_RESTART`로 실제 이어달리기가 되도록 설계돼
  있다(`if [ -f "$D/p2-1.restart" ]; then ... EXT_RESTART ...`) — **P1/P1b/P3만 이 설계
  원칙이 빠졌다.**
- **[확인] 이것이 edge case가 아니라 기본 시나리오다.** `plan.py:size_job`으로 직접 계산:
  P1의 `core_hours_budget=1000`, `nodes=1`. `cpn`(cores/node) 32 (plan.py의 **기본 가정값**,
  `cpn = cores_per_node or env.get("cores_per_node") or 32`)에서
  `ideal_wall = 1000/32 = 31.25h > max_wall(24h)` → `wall=24h clamp`,
  `links = ceil(1000/(32*24)) = 2`. **즉 패키지 자신의 기본 가정(32 core/node)에서조차
  P1은 2-link 체인이 필요하다.** 실제 학술 클러스터의 흔한 코어수(16/24/28)에서는 더
  쉽게 걸린다. 그리고 이것은 우연히 빠뜨린 케이스가 아니라 **coder가 직접 테스트로
  고정해 둔 시나리오다**: `tests/test_plan_report_e2e.py::test_chain_links_recorded`가
  "작은 노드에서는 P1이 체인으로 나간다"는 것을 16-core/node로 명시적으로 검증한다.
  **그런데 그 테스트는 python 쪽 제출 로직(job id 개수, `--dependency=afterany`)만
  검증하고, bash payload가 재실행 시 실제로 무엇을 하는지는 전혀 실행하지 않는다**
  (FakeShell이 `sbatch`만 가로채지 실제 `P1.sh`를 실행하지 않음). 162개 테스트 중
  이 상호작용(체인 링크 수 ≥2 × payload의 무체크포인트 재실행)을 검증하는 테스트는
  **하나도 없다.**
- **어떤 입력에서 어떻게 틀리는가 (두 갈래 실패 모드)**:
  1. **(흔한 경우) 링크 0이 24h 안에 끝난다** — 라디칼 1개짜리 TS 탐색은 보통 24h를
     다 쓰지 않는다. 링크 0이 정상 종료(`exit 0`)하며 `P1.done.json`을 쓴다. 그런데
     `afterany` 의존성은 **선행 잡의 성패와 무관하게 발동**하므로, 미리 걸어둔 링크 1
     (`P1_c1`)이 **그대로 실행된다.** `P1_c1`은 자신의 마커(`P1_c1.done.json`)가 없으므로
     통과하고, `sei_qc_detect`→smoke→CREST→NEB-TS→TSOpt→Freq→IRC를 **처음부터 다시
     돈다.** 이번엔 같은 `job_dir`에 결과 파일(`tsopt.xyz`, `freq.out`, `irc_*.xyz`)을
     **덮어쓴다.** NEB-TS/CREST는 일반적으로 완전히 결정론적이지 않으므로(반복 최적화,
     스레드 스케줄링 의존), 두 번째 런이 **다른 TS**로 수렴할 수 있다. 최종적으로
     collector가 읽는 값은 "먼저 된 것"이 아니라 "나중에 덮어쓴 것"이며, 이 사실도
     회신 JSON 어디에도 남지 않는다. 결과: **불필요하게 core-h를 2배 태우고**(사용자가
     승인한 것은 "1000 core-h짜리 P1 하나"이지 "TS 탐색 2회"가 아니다), **재현 불가능한
     이중 실행이 조용히 최종 결과를 결정**한다. 패키지가 존재하는 이유(§R2-6: "S3 단가
     스프레드 8배를 3배로 줄이는 유일한 수단")인 바로 그 값이 이 방식으로 오염된다.
  2. **(드문 경우) 링크 0이 진짜로 24h에 잘린다** — HANDOFF §0/§R2-6 D-4가 약속한
     "self-chaining으로 사용자 개입 없이 이어서 완주한다"가 **성립하지 않는다.** 링크 1은
     CREST부터 다시 시작하므로, 링크 0이 이미 수렴시킨 NEB-TS/TSOpt 결과를 전부 버리고
     또 처음부터 최대 24h를 쓴다. 진짜로 24h를 넘겨야 하는 무거운 TS라면 **이 체인은
     영원히 완주하지 못하고 매번 0%에서 다시 시작**하며, 이는 무한 루프는 아니지만
     (링크 수가 `n_links`로 고정돼 있으므로) **정해진 링크 수를 다 써도 목표에 도달하지
     못한 채 core-h만 소진하고 실패로 끝난다.**
- **고쳐라 (coder에게)**: 최소 수정은 `common.sh`의 멱등성 검사가 **논리적 항목 키**
  (예: `SEI_LOGICAL_KEY="P1"`, 체인 인덱스와 무관)로 마커를 보게 하고, `sei_job_main`이
  "$@"의 반환값을 그대로 신뢰하지 말고 **payload 자신이 각 단계 완료 후 자체 마커를
  남기고 다음 실행 시 그 마커를 보고 단계를 건너뛰도록** `P1.sh`/`P1b.sh`/`P3.sh`에
  단계별 skip 로직을 추가해야 한다(`P2.sh`가 CP2K restart로 이미 보여준 패턴을
  ORCA/xtb 다단계 워크플로에 맞게 이식). 대안으로 `size_job`이 P1/P1b/P3처럼
  "체크포인트 불가능한 유계(bounded) 워크플로"에는 애초에 **체인을 걸지 않고**
  core-h 상한 대신 **단일 24h 링크 + 실패 시 사용자 재실행**으로 처리하는 방법도
  있다(다만 이러면 §R2-6 D-4 "사용자 2차 개입 금지"를 이 세 파일럿에서는 포기하게 됨 —
  lead 판정 필요).

---

## MAJOR

### M-1. 체인 제출이 도중에 실패해도 `failures[]`에 남지 않는다 — 조용히 잘린 채로 "정상"처럼 보고됨

- **근거**: `sei_pilot/scheduler.py:141-160`(`submit_chain`은 `jid is None`이면 `break`하고
  그때까지 모은 `ids`만 반환), `sei_pilot/cli.py:210-235`(`submit_entry`는
  `if not ids: mark_failed(...)` 만 검사한다. **`ids`가 비어있지 않고 일부만 있는 경우는
  체크하지 않는다.** `payload = {"job_ids": ids, ..., "chain_links": links}`에서
  `chain_links`는 **원래 계획된 링크 수**(예: 3)를 그대로 적지만 `job_ids`는 실제로
  제출된 것(예: 2개)만 들어간다.)
- **[확인]** 이 불일치(`chain_links=3` vs `len(job_ids)=2`)가 기록되긴 하지만, 이걸 보고
  "체인이 잘렸다"고 해석하는 코드가 `collect.py`/`report.py` 어디에도 없다. `failures[]`는
  `store.all_failures()`가 `*.failed.json` 파일을 모으는 것인데, 이 경로에서는
  `mark_failed`가 호출되지 않는다.
- **어떻게 틀리는가**: 사이트 QoS가 "동시 제출 가능 잡 수"를 제한해 체인의 3번째 링크
  제출이 거부되면(실제로 `test_submit_failure_is_isolated`가 이런 케이스를 다루지만
  **단일 잡 제출 실패**만 테스트하지 **체인 중간 실패**는 테스트하지 않는다),
  collector는 이미 제출된 2개 링크의 `afterany`만 기다리다가 그게 끝나면 즉시 실행되고,
  P1/P2 등은 **의도한 core-h의 2/3만 쓰고 중단됐는데도** 회신 JSON에는 이 사실이
  어디에도 나타나지 않는다(마커가 없으면 `job_status`는 그냥 "incomplete"로 보일 뿐,
  "왜 중단됐는지"는 안 남는다).
- **고쳐라**: `submit_entry`에서 `len(ids) < links`(요청한 체인 항목에 한해)일 때
  `store.mark_failed(key, "chain_partial_submit", "%d/%d links only" % (len(ids), links),
  severity="warning")`를 추가.

### M-2. 체인 마커가 **링크별로 분리**돼 있어, `job_status()`가 보고하는 "done/failed"가
전체 체인이 아니라 **첫 링크 하나**의 결과일 수 있다

- **근거**: `sei_pilot/collect.py:50-60`(`job_status`)가 `store.read_marker(key, "done")`/
  `"failed"`만 본다. `key`는 항상 논리적 이름(`"P2"`)이고, 링크 1 이상이 쓰는 마커
  (`P2_c1.done.json` 등)는 **절대 읽히지 않는다.**
- **[확인] P2/P2ext는 실질적 피해가 제한적**이다 — CP2K가 같은 `job_dir`의 결과 파일
  (`.ener`, `.restart`, `p2_meta.json`)을 계속 갱신하므로 **과학적 데이터 자체는 최신
  링크 것을 읽는다.** 하지만 `status` 필드(pass/fail)는 **링크 0의 결과에 고정**된다.
  예: 링크 0이 파일시스템 hiccup으로 rc≠0 종료 → `P2.failed.json` 기록. 링크 1이 정상
  이어받아 완주(`P2_c1.done.json`) → **`state/P2.failed.json`은 아무도 지우지 않으므로**
  `collect_p2`는 영구히 `job_status="failed"`를 반환하고 `res["status"]="fail"`이 박힌다
  (`collect.py:180-182`). 데이터는 있는데 상태만 "실패"로 영구 오분류되는 경우다.
  (`Store.mark_done`은 성공 시 `failed` 마커를 지우는 로직이 있지만 — `state.py:73-74` —
  이건 **python 쪽 `mark_done` 호출 경로**이고, 셸 쪽 `sei_write_marker`는 그런 정리를
  하지 않는다. 게다가 애초에 python은 이 항목에 대해 `mark_done`을 호출하지 않는다 —
  완료 판정은 셸이 쓴 마커 파일의 존재로만 이뤄진다.)
- **고쳐라**: 링크가 여러 개인 항목은 **모든 링크의 마커를 훑어서** "마지막으로 실행된
  링크(가장 늦은 epoch)"의 상태를 대표값으로 쓰거나, 최소한 "이전 링크 실패 후 이후
  링크 성공"인 이력을 `warnings[]`에 남겨야 한다.

---

## MINOR

### N-1. P4(GPU4PySCF 대조) 항목의 CPU 참조 계산이 `ResourceGuard`의 core-h 집계에서 완전히 빠진다

- **근거**: `sei_pilot/plan.py:64-68`(`Item("P4", ..., core_hours_budget=0.0, gpu_hours=1.0,
  gpus=1, nodes=1, ...)`), `payload/P4.sh:22-37`(pyscf `UKS` SP+gradient를
  `SEI_TOTAL_CORES` 코어로 실제 실행 — 공짜 연산이 아니다).
- **영향은 작다** — `size_job(0.0, ...)`이 `floor`(0.25h) 하나로 wall을 고정하므로 총
  소비 자체가 크게 튈 수는 없다. 다만 "가드가 모든 소비를 강제한다"는 설계 원칙
  (`budget.py:1-19` 서두)에 이 항목만 예외로 남아 있다는 점은 문서화라도 필요하다.
  BLOCKER/MAJOR와 달리 즉시 고칠 필요는 없다고 판단해 MINOR로 내림.

### N-2. `payload/P1.sh`의 IRC 판정에서 "이온성 배위(Li 등)를 결합에서 제외"하는 기본값이
바꿀 수 있는 반응 유형 (lead 요청 항목, 버그 아님 — 위험 서술)

- **근거**: `sei_pilot/criteria/xyzgraph.py:63-77, 205-234`.
- **[확인] 코드 자체는 책임 있게 짜여 있다** — 기본값(`include_ionic=False`)과
  대안(`True`) 양쪽을 전부 계산해 JSON에 같이 싣고 `[UNRESOLVED: IRC-CONV]`로 명시했다.
  버그로 지적하는 게 아니라, 이 기본값이 **어떤 반응에서 오판정을 만들 수 있는지**를
  lead가 명시적으로 요청했으므로 기록한다: 만약 P1이 실제로 잡아낸 saddle point가
  "공유결합 변화 없이 Li⁺가 다른 카르보닐 산소로 옮겨가는" 낮은 장벽의 이온 재배위
  천이상태라면(SSIP↔CIP 종류의 전이), `include_ionic=False`(기본) 하에서는 양끝의
  공유결합 그래프가 동일해 보여 `irc_endpoints_distinct=False`로 **판정되어 P1 전체가
  "fail"** 처리된다 — 실제로는 물리적으로 존재하는 낮은 장벽의 TS인데도 "TS가 아니다"로
  잘못 버려질 수 있다. 반대 방향(고리 열림처럼 진짜 공유결합이 끊어지는 경우)은 이
  선택이 판정을 흐리지 않는다. 이 위험은 P1 자체보다, 향후 S3에서 같은 판정 로직을
  재사용할 때 "Li 재배위 전용 TS"를 network에서 자동으로 걸러내 버릴 위험으로 이어진다.
  proposer 판정을 꼭 받아야 한다.

---

## 확인하지 못한 것

- ORCA/CP2K/xtb의 실제 출력 형식([UNVERIFIED] 표기된 부분: NEB-TS 출력 파일명,
  Mulliken 스핀 열 위치, `xtb --path` 문법, ORCA VIBRATIONAL FREQUENCIES 블록 형식) —
  실행 환경이 없어 검증 불가. coder가 표시한 대로 "1차 검증은 사용자 클러스터"로 남는다.
  단, `units.py`/`criteria/p2.py`/`criteria/p4.py`의 **단위 처리 자체**(Hartree vs eV,
  meV/atom/ps 산식, CP2K `.ener` 컬럼 인덱스)는 정적으로 검토했고 문제를 찾지 못했다.
- `sei_pilot/enumerate_gen1.py`(P3 열거기), `sei_pilot/probes.py`(처리량·큐대기 통계),
  `sei_pilot/sysprobe.py`(lscpu/df/network 파서) 상세 검토는 시간 제약으로 생략했다 —
  P0 최우선 항목(가드/멱등/체인/부분실패/dry-run)과 P1 물리 항목(단위, P1/P2 판정)에
  집중했다.
- `02_METHOD_SPEC.md` §11 참고문헌(R8/R10/R11/R12 `[FULLTEXT-UNVERIFIED]`) 1차 문헌
  확정 — 코드 리뷰를 우선하라는 지시에 따라 이번 라운드에서는 손대지 못했다.
- `run.sh --dry-run`을 실제로 실행해 "5분 내 완료 + 무제출"을 내 손으로 확인하지는
  못했다(이 박스에도 스케줄러가 없어 `LocalAdapter`로 빠지는데, 그 경로가 실제로
  아무것도 "제출"하지 않는지는 코드 추적으로만 확인했고 실행 검증은 하지 않았다 —
  coder의 HANDOFF §3에 실행 로그가 있으나 "다른 agent의 말을 근거로 삼지 말라"는
  원칙에 따라 이 항목은 미검증으로 남긴다).

---

## 2026-08-17 (추가) — lead 피드백 반영 + 신규 BLOCKER 발견 (s(t) 시간축 정렬 오류)

lead가 이미 판정된 2건(가드 기본값 4,000 승인/전파 확인됨 — 문제 없음 확인. IRC 이온배위
제외 기본값은 proposer가 이미 오판정으로 결론 내고 §12 2층 그래프 방식으로 교체 지시함)을
공유하며 중복 보고를 피하라고 했다. **위 N-2는 이 정정으로 supersede된다** — proposer의
§12 교체안이 이미 코드 문제로 확정됐으므로 내가 "위험 시나리오"로만 남겨둔 서술은
참고용으로만 남기고 별도 지적으로 세지 않는다. 가드 기본값 4,000 전파는 이미 위 리뷰에서
직접 확인했고 이상 없다(N-1/B-1과 무관, 이 항목은 "판정 완료"일 뿐 내가 새로 찾은 문제가
아니었다).

lead가 지목한 "단위·스케일 인자 누락과 같은 유형의 버그가 더 있는지"를 `criteria/p2.py`의
s(t) 판정 코드에 집중해 다시 훑었고, **동일 유형의 신규 BLOCKER를 찾았다.**

### B-2. `spin_localization_from_mulliken`이 Mulliken 프레임 인덱스를 **`.ener`의 매 스텝
시간 배열에 그대로 인덱싱**한다 — 두 출력의 기록 주기가 다른데 맞추지 않는다.
ADR-005/§11.5 G-AIMD 판정(s(t))의 **시간축이 계통적으로 약 10배 압축**된다.

- **근거 파일**: `inputs/cp2k_aimd.inp.tmpl:24-34, 76-83`
  (`&PRINT/&TRAJECTORY/&EACH MD 20`, `&RESTART/&EACH MD 50`, **`&DFT/&PRINT/&MULLIKEN/&EACH
  MD 10`** — Mulliken population analysis는 **10 MD step마다** 출력된다.
  TIMESTEP=0.5 fs이므로 Mulliken은 물리적으로 **5 fs 간격**이다.
  `.ener` 파일 출력 주기는 이 템플릿에 별도 `&PRINT/&ENERGY` 오버라이드가 없으므로
  CP2K 기본값(**매 스텝**, 0.5 fs 간격)을 그대로 쓴다),
  `sei_pilot/criteria/p2.py:201-219`(`spin_localization_from_mulliken`).
- **[확인]** 함수 본문:
  ```python
  for k, frame in enumerate(frames):        # frames = Mulliken 프레임 (10 step마다 1개)
      ...
      t = time_fs[k] if time_fs and k < len(time_fs) else float(k)
      series.append((t, tgt / total))
  ```
  `time_fs`는 `parse_cp2k_ener()`가 만든, **매 스텝(0.5 fs 간격)** 시간 배열이다.
  `frames`는 Mulliken 블록 리스트로 **10 스텝(5 fs)마다 1개**만 존재한다. 그런데 이
  함수는 Mulliken 프레임의 순번 `k`(0, 1, 2, ...)를 **그대로** `time_fs`의 인덱스로
  써서 시각을 가져온다. 올바른 시각은 `time_fs[k * 10]`(Mulliken 출력 주기만큼
  건너뛴 스텝)이어야 하는데, 코드는 `time_fs[k]`(매 스텝 배열의 k번째, 즉 0.5·k fs)를
  쓴다. **주기 비(10)만큼 시간축이 압축된다.**
  `payload/cp2k_common.sh:47-73`(`sei_spin_series`)가 이 함수를 **1차 경로로도** 호출하므로
  (`s_of_t.dat`를 직접 만드는 그 경로), "이중화"로 방어되는 파서 실패 케이스가 아니라
  **주 경로 자체가 이 버그를 갖고 있다.**
- **[확인] 테스트가 이 케이스를 구조적으로 가릴 수 없다**: 유일한 테스트
  (`tests/test_criteria.py:429 test_mulliken_parsing_and_localization`)는 **Mulliken
  프레임 1개 + `time_fs=[0.0]` 1개짜리** 입력만 쓴다. 프레임 수와 time_fs 길이가 둘 다
  1이라 `k=0`밖에 없고, 인덱스 오정렬이 드러날 수가 없는 입력이다. 다중 프레임·다중
  스텝 케이스를 다루는 테스트는 없다.
- **어떤 입력에서 어떻게 틀리는가**: P2ext까지 성공해 **실제로 3 ps(6000 step, 0.5 fs)를
  다 돌렸다고 하자.** Mulliken은 10 step마다 찍히므로 프레임 수 = 600개(0~599). 함수는
  `time_fs[0], time_fs[1], ..., time_fs[599]`를 시각으로 쓰는데 이건 실제로는
  **0, 0.5, 1.0, ..., 299.5 fs = 0~0.2995 ps 구간의 시각**이다(진짜 프레임 599의 물리적
  시각은 599×10×0.5fs = 2995 fs = 2.995 ps인데, 계산된 값은 299.5 fs). **약 10배
  압축.** `evaluate_spin()`의 `trajectory_ps = (series[-1][0]-series[0][0])*FS_TO_PS`는
  진짜 3 ps 대신 **~0.3 ps**로 계산된다.
  - `SPIN_VERDICT_WINDOW_PS = 3.0` 판정에서 `window_satisfied = trajectory_ps >= 3.0`이
    **항상 거짓**이 된다 — **실제로 P2ext(+800 core-h)까지 성공시켜 진짜 3 ps를 확보해도
    코드는 "0.3 ps밖에 없다"고 보고**하고, `⟨s⟩>0.85`인 경우도 절대 `provisional_pass`로
    승격하지 못하고 영원히 `undetermined`에 머문다. §11.5가 "800 core-h로 사는 것은
    core-h가 아니라 달력(왕복 1회=3.5일)"이라고 명시한 그 왕복을, **이 버그가 도로 만들어
    낸다** — lead가 3ps 데이터를 받고도 "창이 부족하다"고 오판해 재확장을 요청하게 될
    가능성이 높다.
  - `slope_per_ps`(표류 판정, `SPIN_DRIFT_SLOPE_PER_PS = -0.05`)도 압축된 시간축으로
    계산되므로 **진짜 기울기의 약 10배 크기로 보고된다.** 완만한 진짜 표류(-0.005/ps,
    통과해야 정상)가 겉보기 -0.05/ps 근처로 부풀려져 `drifting=True`로 **거짓 양성**
    판정될 수 있다 — reject 방향으로 편향된 오판정.
  - 종합: 이 버그는 **판정을 항상 보수적(거부/미결정) 방향으로만** 틀리게 하므로 "위험한
    반응을 통과시키는" 실패는 아니다. 그러나 **ADR-005 S1 방법 분기(비구속 PBE 유지 vs
    cDFT 강제)를 결정하는 유일한 실측값이 구조적으로 신뢰 불가**해진다는 점에서, 그리고
    "800 core-h + 왕복 3.5일을 들여도 코드가 그 값을 못 알아본다"는 점에서 **B-1과
    동급의 BLOCKER**로 매긴다. `s_of_t.dat`(payload가 직접 쓰는 파일)와 CP2K 출력
    재파싱 경로가 **둘 다 같은 함수를 거치므로** 이중화가 이 버그를 방어하지 못한다.
- **고쳐라**: `spin_localization_from_mulliken`에 Mulliken 출력 주기(또는 직접 스텝 번호)를
  넘겨서 `time_fs[k]` 대신 `time_fs[k * mulliken_stride]`(또는 Mulliken 블록에서 직접
  스텝 번호를 파싱)로 고쳐야 한다. 가장 안전한 방법은 CP2K `.out`의 Mulliken 블록
  근처에서 스텝 번호를 함께 추출하는 것(현재 `parse_cp2k_mulliken_spin`은 스텝 번호를
  전혀 기록하지 않는다 — 프레임 순번만 반환). 그게 어려우면 최소한
  `cp2k_aimd.inp.tmpl`의 `MULLIKEN &EACH MD 10`과 `.ener` 출력 주기를 **일치**시키고
  (예: 둘 다 MD 10로 맞추거나, 최소공배수로 정렬), `sei_spin_series` 호출부에서
  stride를 명시적으로 넘기는 방식으로 고쳐야 한다. 여러 프레임·정수 배 아닌 stride를
  포함하는 회귀 테스트를 반드시 추가해달라(현재 테스트는 이 클래스의 버그를 원리적으로
  못 잡는 입력만 쓴다).

## 판정 갱신
**FIX-THEN-RUN 유지.** BLOCKER가 1건 → **2건**(B-1 체인 재실행 중복, B-2 s(t) 시간축
정렬 오류)으로 늘었다. 둘 다 국소 수정(B-1: payload 셸 3개 + collect.py, B-2: p2.py
1개 함수 + 입력 템플릿 주기 정렬)이라 왕복 1회 안에 고칠 수 있다고 본다.
**"지금 보내도 되는가": 아니오.**

---

## 2026-08-17 (추가) — lead 채택 확인, 재리뷰 대기 (standby)

lead가 FIX-THEN-RUN 판정을 전면 채택하고 패키지 인도를 보류했다는 응답을 받았다
(SendMessage가 이 세션에서 비활성이라 lead의 지시가 teammate-message로만 전달됨 —
나는 여전히 회신을 보낼 수 없어 이 로그로만 확인을 남긴다).

lead 결정 요약(내 기록용):
- B-1 대안 중 "P1/P1b/P3는 단일 24h + 사용자 재실행"은 **채택 안 됨**
  (ADR-008 "사용자 2차 개입 금지" 원칙 유지). 대신 coder에게
  **① 논리 키 기준 멱등성 + ② payload 단계별 체크포인트(P2 EXT_RESTART 패턴 이식)**
  둘 다 지시함.
- B-2, IRC 2층 그래프(§12), 가드 4,000 정합성도 coder 수정 대상에 포함.
- coder 수정 완료 시 **재리뷰 요청 예정** — 범위는 "수정된 부분 + 인접 영역"으로
  한정(전체 재리뷰 아님). 신규 회귀 테스트가 **원래 버그를 실제로 재현하는 입력을
  쓰는지**를 최우선으로 확인할 것(예: B-1 재현 테스트는 실제 payload 셸을 실행하거나
  그에 준하는 시뮬레이션으로 "링크1이 링크0 완료를 인지하고 스킵/재개하는지"를 검증해야
  하고, B-2 재현 테스트는 Mulliken stride ≠ 1인 다중 프레임 입력을 써야 한다 — 둘 다
  현재 테스트가 원리적으로 못 잡던 바로 그 형태).
- MINOR(N-1, N-2)는 이번 라운드 처리 대상 아님. 목록은 위에 보존.

현재 상태: **coder 수정 대기 중(standby).** 수정 완료 통지가 오면 위 기준으로 국소
재리뷰를 수행한다.

---

## 2026-08-17 (신규 과업) — Blind Test 정답지: EC:EMC 3:7 + 1M LiPF6 문헌 기반 SEI 화학 인벤토리

**목적**: ADR-014/R-17 대응. proposer의 탐색 엔진(S2-A)이 **목표종 보호를 끈 상태에서**
알려진 SEI 성분을 스스로 재발견하는지 시험하는 blind test의 정답지. 방법 설계자(proposer)가
아닌 독립적 리뷰어가 작성한다는 것이 이 문서의 성립 조건이다.

### 🔴 방법론적 한계 — 반드시 먼저 읽어라

**이 세션에는 웹 검색/문헌 조회 도구가 없다(Read/Bash/Write만 가용, 인터넷 접근 불가).**
따라서 이 인벤토리는 **내 사전학습 지식에서 복원한 것**이며, `02_METHOD_SPEC.md`가 표기하는
`[FULLTEXT-UNVERIFIED]`(초록이라도 이번 세션에 실제로 확인함)보다 **더 낮은 확인 수준**이다.
아래 확인 수준 태그를 엄격히 구분해서 읽어라:

| 태그 | 의미 |
|---|---|
| `[RECALL-강]` | 이 분야(Li-ion 전해질 분해/SEI) 표준 개론서·리뷰(Xu *Chem. Rev.* 비수계 전해질 리뷰류,
  Aurbach 계열 SEI 리뷰류, Peled/Menkin SEI 개념 논문류)에서 반복적으로 재확인된, 커뮤니티
  합의 수준이 높다고 기억하는 항목. 그래도 **이번 세션에 원문 대조는 못 했다.** |
| `[RECALL-약]` | 특정 계산 논문 하나(저자/연도까지 기억하지만 세부 수치는 불확실)에서 본
  기억에 의존. **저자명·연도·정확한 barrier 값은 틀렸을 수 있다** — 인용이 아니라
  "이런 계산이 있었다는 기억"으로 취급하라. |
| `[추정-화학]` | 문헌을 특정하지 못하나, EC/EMC/PF6⁻ 화학의 일반 원리(라디칼 짝지음,
  탄산에스터 가수분해 등)로부터 **내가 추론한 것.** 정답지에 넣을 게 아니라 "찾아봐야 할
  후보"로만 써라. |
| `[미상]` | 기억이 없다. "얇다"로 정직하게 보고. |

**⟹ lead/proposer에게: 이 문서를 blind test 정답지로 그대로 채택하지 말고, 최소한
`[RECALL-강]` 항목만이라도 실제 1차 문헌(Xu *Chem. Rev.* 2004/2014, Aurbach *J. Power
Sources* 리뷰, Peled & Menkin *J. Electrochem. Soc.* 2017 SEI 개념 논문, Balbuena/Wang
EC 환원 DFT 논문들, Leung & Budzien *PCCP* 2010, Ushirogata/Sodeyama/Tateyama *JACS*
2013, Blau/Persson HiPRGen 논문(이미 R2로 확인됨))으로 **인터넷 접근이 되는 agent(사용자
또는 웹 도구가 있는 세션)가 대조 확인**해야 blind test가 성립한다. 이번 산출물은
"무엇을 찾아야 하는지의 초안"이지 "확정된 정답지"가 아니다.**

---

### A. 생성물 인벤토리 — ADR-003의 7종을 넘어서

`02_METHOD_SPEC.md` §8.3/§8.4에 이미 LIBE pool에 존재하는 것으로 확인된 종
(LEDC, LEMC, ROCO2Li, LiF, Li2CO3, C2H4, CO, CO2, PF6⁻/PF5/POF3, LiOCH3, LiOC2H5,
CH3OCO2Li, C2H5OCO2Li, DMDC, DEDC)은 **표에서 제외**한다 — 이미 알고 있으므로 blind test
정답지에서 새로운 정보가 아니다. 아래는 **우리 문서에 아직 명시적으로 없는 것들.**

| 항목 | 분류 | 확인 수준 | 비고 |
|---|---|---|---|
| **LiPO2F2** (lithium difluorophosphate) | 무기 SEI/CEI 성분 | `[RECALL-강]` | PF6⁻ 가수분해/환원 부산물로 LiPF6계 전해질 SEI·CEI에서 **널리 보고**됨. 우리 목록의 PF6⁻ 분해 채널(→PF5→POF3→LiF)에 **P가 남는 유기/무기 인산염 갈래**가 통째로 빠져 있다. |
| **알킬 플루오로인산 에스터** (예: ROP(O)F2, (RO)2P(O)F류) | 유기인 SEI 성분 | `[RECALL-약]` | POF3가 용매(EC/EMC)의 OH·O 원자와 반응해 만드는 것으로 기억. 정확한 구조·명명은 불확실. |
| **HF** (불산, 가스/미량 용존) | 반응 매개체·부식종 | `[RECALL-강]` | LiPF6 + 미량 H2O → LiF + POF3 + 2HF. **직접 목표종은 아니지만, 아래 HF-매개 이차반응들의 필수 반응물.** |
| **H2O** (미량 수분) | 반응 매개체 | `[RECALL-강]` | 사실상 모든 PF6⁻ 분해/HF 생성 화학의 **트리거**로 문헌에서 취급됨. ADR-001 조성 정의에 **명시적으로 포함되지 않음**(첨가제 없음, 무수 가정으로 보임) — 이게 문제다(아래 D-3). |
| **Li2C2O4** (리튬 옥살산) | 응축상 유기 SEI 성분 | `[RECALL-약]` | carbonate 전해질 SEI에서 **소수 성분으로 보고된 기억**이 있으나 EC/EMC계에서의 비중은 불확실. |
| **HCOOLi** (리튬 포름산), **CH3COOLi** (리튬 아세트산) | 응축상 유기 SEI 성분 | `[RECALL-약]` | CO2 재환원·재결합 경로의 하류 생성물로 일부 XPS/NMR 연구에서 언급된 기억. 비중 낮음. |
| **폴리(에틸렌 옥사이드/카보네이트) 유사 올리고머** (개환 EC의 사슬성장 중합체) | 응축상 유기 SEI 성분 | `[RECALL-약]`, **논쟁 항목으로 분류(§C)** | EC 개환 라디칼음이온이 다른 EC 분자를 공격해 사슬을 늘려가는 음이온성 개환중합 메커니즘이 제안된 바 있다는 기억. LEDC(이량체) 수준에서 멈추는지, 더 긴 사슬까지 가는지는 **문헌에서도 갈리는 것으로 기억**(XPS 해상도 한계로 실측이 어려운 영역). |
| **Li2O** | 무기 SEI 성분 | `[추정-화학]` | Li2CO3의 추가 환원/분해 하류 생성물로 화학적으로는 그럴듯하나, EC/EMC계 SEI 조성 보고에서 **주성분으로 본 기억은 약함**(주로 산화물 전극 표면이나 극단적 환원 조건에서 논의되는 경향). |
| **C3H6 (프로펜)**, **C2H6 (에탄)** 등 미량 탄화수소 가스 | 가스 부산물 | `[RECALL-약]` | DEMS 연구에서 C2H4/CO/CO2 대비 **미량 성분**으로 보고된 기억. 정량 비중 낮음. |
| **Li 금속 자체와의 직접 반응(anode side) 생성물** | — | 해당 없음 | ADR-002로 표면 배제 확정이므로 인벤토리에서 제외. |

**요약**: 생성물 후보 **≈ 9종 신규 제안**(위 표, LiO2 제외 시 확신도 낮은 항목 다수).
그중 확신도가 상대적으로 높은 것은 **LiPO2F2, HF/H2O 매개 이차화학** 두 갈래뿐이다.
나머지는 스스로 "약함"으로 표시했다.

---

### B. 반응 단계 — 문헌에서 반복적으로 등장하는 경로(barrier 수치는 대부분 미상)

| 반응 | 확인 수준 | barrier/ΔG | 비고 |
|---|---|---|---|
| EC + e⁻ → EC•⁻ (고리형 라디칼음이온) | `[RECALL-강]` | 미상 | 이미 §8.6에서 우리 문서가 다룸(닫힌고리 EC⁻ 극소 확인, ADR-006 P0). |
| EC•⁻ → 개환 라디칼음이온 (C-O 결합 절단, acyl-O vs alkyl-O 두 자리 논쟁) | `[RECALL-강]` | ADR-006에 "문헌 barrier ≈0.48 eV" 언급 있음(우리 문서 자체 인용, 출처 재확인 못 함) | **어느 C-O 결합이 끊어지는지가 논쟁 항목**(§C) |
| 개환 라디칼음이온 + 개환 라디칼음이온 (2몸 짝지음) + 2Li⁺ → LEDC | `[RECALL-강]` | 미상 | 이미 LIBE에 LEDC로 확인됨 — S2-A가 원리적으로 도달 가능한 **2체 반응**(아래 D-1에서 "도달 가능"으로 분류) |
| EC•⁻ 2차 환원(2e⁻ 경로) → 개환 후 C2H4 + CO3²⁻(→Li2CO3) 분해 | `[RECALL-강]` | 미상 | ADR-003 축(a)의 1e⁻/2e⁻ 분기 본체. 우리 문서가 이미 이 분기를 인지(ADR-005 Consequences). |
| EMC + e⁻ → EMC•⁻ → C-O 절단 → CH3• + CH3OCO2⁻(또는 C2H5O• + CH3OCO2⁻ 등 자리 이성질) | `[추정-화학]`(EC 화학의 유추이며 EMC 전용 문헌 기억은 약함) | 미상 | LIBE에 관련 라디칼/생성물이 이미 존재(§8.3 EMC 계열 0/13 결손) — **생성물은 확인되나 elementary step의 문헌 근거는 내가 못 댄다.** |
| LiPF6 + H2O → LiF + POF3 + 2HF | `[RECALL-강]` | 미상 | 널리 인용되는 반응. 정확한 1차 출처(Sloop 계열로 기억하나 불확실)는 대조 필요. |
| POF3 + H2O(또는 미량 알코올/카르보닐) → 인산 에스터류 + HF | `[RECALL-약]` | 미상 | |
| HF + Li2CO3(고체, 표면) → LiF + H2O + CO2 | `[RECALL-강]` | 미상 | **응축상 고체가 반응물** — 아래 D-2 구조적 맹점의 핵심 사례. Aurbach 계열이 "SEI가 사이클링에 따라 유기물→LiF-rich로 진화한다"는 설명에 이 반응을 든 것으로 기억. |
| LEDC(또는 유기 카보네이트 SEI) + HF/H2O → LiF + 유기 분해물(가스 방출 동반) | `[RECALL-약]` | 미상 | 위와 같은 부류의 이차 화학. SEI "숙성(ripening)" 설명에 흔히 등장하는 서사로 기억하나 정확한 화학종은 불확실. |
| 개환 EC 라디칼음이온의 사슬 성장(음이온성 개환중합) | `[RECALL-약]`, 논쟁 | 미상 | §A 폴리머 항목과 동일 근거. |

---

### C. 논쟁 항목 (정답으로 넣지 말 것)

1. **EC 개환 시 끊어지는 C-O 결합 자리** (acyl-O vs alkyl-O) — 어느 쪽이 우세한지,
   그리고 그것이 1e⁻/2e⁻ 경로 선택과 어떻게 얽히는지는 **계산 방법·용매 모델에 따라
   결론이 갈리는 것으로 기억**한다. `[RECALL-약]`.
2. **LEDC vs LEMC 우세** — 어느 쪽이 SEI의 주성분인지는 실험 조건(전위 스캔 속도,
   온도, 첨가제 유무)에 따라 문헌 보고가 갈리는 것으로 기억한다. lead의 지시문에도
   이미 "쟁점"으로 명시돼 있다.
3. **1e⁻ vs 2e⁻ 경로의 상대 비중** — ADR-003 축(a)이 이미 이것을 정량 목표로 삼고
   있다는 것 자체가 이게 **미해결/논쟁 상태**라는 증거다. 정답지에 "이 비율이 X:Y다"라고
   넣으면 안 된다 — 우리가 **계산으로 알아내야 할 대상**이지 이미 아는 정답이 아니다.
4. **개환 EC의 중합/올리고머화 여부와 사슬 길이 분포** — §A/§B에서 이미 "논쟁"으로 표시.
5. **PF6⁻ 분해가 EC 환원과 독립적으로(순수 가수분해) 일어나는가, 아니면 환원 과정과
   결합된 경로(예: 환원된 EC 라디�일종이 PF6⁻를 공격)가 있는가** — `[추정-화학]` 수준의
   내 추측이며 문헌 근거를 대지 못한다. **정답지가 아니라 "확인이 필요한 질문"으로만
   남긴다.**

---

### D. 🔴 우리 방법(S2-A: fragment-recombine + 화학양론 균형 반응 열거)이 구조적으로
못 찾는 항목 — 이 작업의 최고 가치 산출물

**D-1. (대조군) 원리적으로 도달 가능한 것**: LEDC(2체 라디칼 짝지음), ROCO2Li계
(1체 분해 + Li⁺ 결합), PF6⁻ 단계적 분해(PF6⁻→PF5→POF3→LiF, 순차 이분자/일분자 단계) —
전부 **이분자 이하의 균형 반응**으로 표현 가능하므로 S2-A의 설계 범위 안에 있다.
이미 LIBE pool에 이 종들이 존재한다는 사실(§8.3)이 이를 뒷받침한다. **이것들이 blind
test의 "쉬운 성공 기준"이다 — 이것조차 못 찾으면 엔진 자체가 고장난 것.**

**D-2. 응축상/결정 격자가 반응물·생성물인 단계 — 구조적으로 못 찾는다 (R-07과 동일 근거,
재확인)**: `HF + Li2CO3(고체) → LiF(고체) + H2O + CO2`, `LEDC(고체) + HF → LiF(고체) + ...`
류의 "SEI 숙성" 반응은 **한쪽 항이 분자가 아니라 결정성 고체(주기적 격자)**다. S2-A는
분자 CRN이므로 이런 반응의 반응물/생성물 자체를 표현할 문법이 없다. **찾지 못하는 게
아니라 애초에 물을 수 없는 질문이다.** — R-07이 이미 지적한 것과 **동일한 구조적 한계가
"생성물 형성"뿐 아니라 "생성물의 이차 진화"에도 그대로 적용된다는 것**이 이번에 추가로
확인한 지점이다.

**D-3. 🔴 트리거 분자가 principal species 목록에 없으면 그 화학 전체가 원천 배제된다**:
LiPF6 가수분해·HF 매개 화학(§A/§B의 상당수)은 **H2O를 반응물로 요구**한다. S2-A는
"principal molecule 목록 → fragment 분해 → 재조합"으로 pool을 만드는데, **ADR-001의
대상 조성 정의(EC:EMC 3:7 + 1M LiPF6, 첨가제 없음)에 H2O가 principal species로 명시돼
있지 않다.** fragment-recombine 엔진은 자기가 아는 원자 조각의 조합만 만들 수 있으므로,
H2O(또는 그로부터 오는 H, OH 조각)가 pool에 안 들어가면 **HF/POF3/인산에스터/이차
숙성 화학 전부가 원리적으로 생성될 수 없다.** 그런데 §A/§B에서 확인 수준이 가장 높은
(`[RECALL-강]`) 항목들이 하필 이 갈래에 몰려 있다(LiPF6+H2O→LiF+POF3+2HF, HF+Li2CO3
반응). **이건 엔진의 결함이 아니라 입력 정의의 문제이지만, 결과는 같다 — 문헌에서 가장
확실하다고 알려진 반응 갈래 하나가 통째로 사각지대가 될 위험이 있다.** 대응은 간단하다
(H2O를 미량 principal species로 pool에 명시 추가). **하지만 지금 이 문서를 작성하기
전까지 어느 문서에도 이 갈래가 언급되지 않았다** — 그 자체가 이 작업의 성과다.

**D-4. 사슬 성장/중합** — 이미 §8.4 결손표에 "C5+ 올리고머 희박"으로 나와 있어
proposer도 인지하고 있으나, **원리적 이유를 명시해 둔다**: N_pool 상한(ADR-011,
≤6,000 species)과 generation depth 제약이 있는 한, **개환 EC 사슬중합처럼 원리상 사슬
길이가 무한히 늘어날 수 있는 반응 계열은 어느 지점에서든 인위적으로 절단된다.** 이건
"버그를 고치면 해결"이 아니라 **유계(bounded) 탐색과 무계(unbounded) 화학 사이의 근본
불일치**다. 실측(LIBE)에서 C5+가 희박한 게 "그 화학이 안 중요해서"인지 "애초에
carbonate 계산 커뮤니티도 잘 안 다뤄서"인지 구분이 안 된다는 점도 §C의 논쟁 4번과 얽힌다.

**D-5. 3체 이상 협동 단계** — lead가 예시로 든 항목. 문헌에서 "2개의 Li⁺과 1개의 용매
분자가 동시에 관여하는 concerted 단계"류의 서술을 본 기억은 있으나(`[추정-화학]`) 구체
반응을 못 댄다. **화학종 수준(예: Li⁺(EC)₃(PF6⁻) 같은 다성분 착물)은 우리 tier-2가 이미
다루지만, 그 착물 "안에서" 일어나는 진짜 3체 concerted TS는 S2-A의 이분자 반응 열거
문법으로 표현 불가**하다는 점만은 구조적으로 확실하다.

**D-6. 표면 촉매 필요 반응** — ADR-002로 이미 배제 확정. 신규 지적 아님, 재확인만.

---

### 요약 (lead 회신용)

- **생성물**: 신규 제안 ≈9종(표 A). 확신도 높은 것은 **LiPO2F2, HF, H2O** 3종뿐 — 나머지는
  스스로 "약함"으로 표시.
- **반응**: 신규 서술 ≈9건(표 B). 대부분 barrier/ΔG 수치 미상(내가 낼 수 없음).
- **🔴 구조적으로 못 찾는 항목**(최고 가치 산출물, §D): (1) 응축상/격자 관여 이차반응
  (HF-Li2CO3류) — 반응 자체를 표현 불가. (2) **H2O가 principal species에 없으면
  PF6⁻/HF 관련 화학 전체가 원천 배제**될 위험 — 이게 가장 확실하다고 알려진 화학 갈래와
  겹친다는 게 심각도를 높인다. (3) 사슬 중합/올리고머 — 유계 탐색과 무계 화학의 근본
  불일치. (4) 3체 이상 concerted 단계 — 문법적으로 표현 불가.
- **논쟁 항목**(정답 아님, §C): EC 개환 자리, LEDC vs LEMC 우세, 1e⁻/2e⁻ 비중, 중합
  여부, PF6⁻ 분해의 환원 결합 여부.
- **문헌이 얇은 영역**: EMC 단독 환원 경로의 elementary step 근거(생성물은 LIBE에 이미
  있으나 그리로 가는 반응 경로의 문헌 확신도는 낮음), 올리고머 SEI 성분 정량.
- **🔴 최우선 권고**: 이 문서는 **정답지 초안이지 확정본이 아니다.** 인터넷 접근이 되는
  주체(사용자 또는 웹 도구 있는 세션)가 최소 `[RECALL-강]` 항목만이라도 1차 문헌 대조를
  해야 blind test가 성립한다. 그 전까지 이 표를 "확인됨"으로 인용하지 마라.

---

## 2026-08-17 — 재리뷰: BLOCKER 2건 + IRC §12 + 가드 4,000 수정분

**범위**: lead 지시대로 수정분과 인접 영역만(전체 재리뷰 아님). B-1/B-2 수정 코드,
M-1/M-2 부수 수정, IRC 2층 그래프(§12) 구현, 가드 4,000 전파, 신규 회귀 테스트.
**직접 실행**: `python3 -m unittest discover -s tests` → **192 tests, OK** (기존 162 →
+30, 전부 통과. coder의 "통과했다"는 말이 아니라 내가 직접 돌린 결과).

### B-1 (체인 재실행 중복) — **해소 확인**

- `payload/common.sh`: `SEI_LOGICAL_KEY` 도입, `sei_job_main`의 멱등성 검사가 **논리 키**
  기준으로 바뀜(`common.sh:94-97`). `sei_stage`가 **단계별 체크포인트**를 갖게 됨
  (`stages/<name>.json`에 rc=0 있으면 skip, `common.sh:56-79`) — P2.sh의 EXT_RESTART
  패턴을 P1/P1b/P3에 이식하라는 요구를 **P1.sh/P1b.sh/P3.sh 자체는 한 글자도 안 고치고**
  `sei_stage`의 내부 동작만 바꿔 달성했다(각 단계가 이미 `sei_stage`를 통해 호출되고
  있었으므로) — 우아한 최소 수정.
- **[확인] `sei_pilot/scheduler.py`**: `JobSpec.logical_key` 신설, `submit_chain`이 모든
  링크에 **동일 logical_key**를 부여(`scheduler.py:156-160`). 템플릿 3종(`slurm/pbs/local.
  sh.tmpl`)에 `SEI_LOGICAL_KEY` export 라인 추가 확인.
- **[확인] 신규 테스트 `tests/test_payload_shell.py`**: **실제 bash를 subprocess로 실행**해
  두 체인 링크를 순서대로 돌리는 방식으로 검증한다 — 내가 요구한 "실제 payload 셸을
  실행하거나 그에 준하는 시뮬레이션" 기준을 정확히 만족한다. 특히:
  - `test_link1_does_not_recompute_after_link0_success` — **B-1의 가장 흔한 실패 모드를
    직접 재현**: 링크 0 정상 종료 후 링크 1을 실행해도 단계 A/B가 **다시 실행되지 않음**을
    카운터 파일로 확인.
  - `test_link1_resumes_from_checkpoint_when_link0_died` — 링크 0이 중간 단계에서 죽는
    경우, 링크 1이 **완료된 단계는 건너뛰고 실패한 단계만 재실행**함을 확인.
  - `test_double_execution_is_recorded_when_it_happens` — 감사 메커니즘 자체가 진짜
    이중실행을 놓치지 않는지 **양성 대조군**으로 확인(좋은 습관).
  기존 `test_chain_links_recorded`(python 제출 로직만 검증하던 것)는 그대로 남아 있고
  새 테스트가 **payload 실행 계층**을 추가로 덮는 구조 — 계층이 명확히 분리됐다.

### B-2 (s(t) 시간축 정렬) — **해소 확인, 방어가 이중**

- **[확인] 근본 수정**: `criteria/p2.py`의 `parse_cp2k_mulliken_spin`이 이제 Mulliken
  블록 직전의 CP2K MD 진행 배너에서 **스텝 번호/시각을 직접 파싱**해 프레임에 붙인다
  (`p2.py:154-218`). `resolve_frame_times()`가 신뢰도 순으로 5단계 폴백
  (블록 자체 시각 → 스텝×dt → 명시 stride → 추정 stride(경고) → 프레임 순번(불신 표시))을
  제공하고, `time_axis_reliable()`이 신뢰 가능한 출처만 화이트리스트한다.
- **[확인] 판정 게이트**: `evaluate_spin()`이 `time_axis_reliable`이 `False`면
  **`provisional_pass`로 승격하지 않고 `undetermined`로 떨어뜨린다**(`p2.py:396-401`) —
  "시간축을 못 믿으면 창 길이 자체가 무의미"라는 내 지적을 정확히 코드화했다.
- **[확인] 근본 원인도 같이 제거**: `inputs/cp2k_aimd.inp.tmpl`에서 `.ener` 출력 주기
  (`&ENERGY &EACH`)를 Mulliken 주기(`{{MULLIKEN_EVERY}}`)와 **동일 변수로 통일**했고,
  `TIMESTEP`/`MULLIKEN_EVERY`를 `payload/cp2k_common.sh` 한 곳(`SEI_TIMESTEP_FS`,
  `SEI_MULLIKEN_EVERY`)에서만 정의해 입력 렌더링과 파서가 **같은 값을 공유**하게
  했다 — "값이 두 곳에 따로 있어서 어긋난다"는 이 버그 계열의 재발을 구조적으로 막았다.
- **[확인] 신규 테스트가 정확히 원래 버그를 재현한다**:
  `test_time_axis_uses_step_numbers_not_frame_index`가 **6000 step × 0.5 fs = 3 ps,
  Mulliken 10 step마다 → 600 프레임**이라는 실제 시나리오 그대로 데이터를 만들고,
  "옛 버그 값(299.5 fs)이 아니라 진짜 값(2995.0 fs)이 나온다"를 **명시적으로 대조
  단언**한다(`assertNotAlmostEqual(..., 299.5, ...)`). `test_full_3ps_window_is_
  recognized_end_to_end`는 그 값으로 `provisional_pass`가 실제로 나오는지까지
  끝까지 검증한다. `test_unreliable_axis_never_grants_provisional_pass`는 "그럴듯해
  보이는 데이터라도 축이 불확실하면 승격 안 됨"을 별도로 확인한다. **이건 "테스트를
  추가했다"가 아니라 "그 테스트가 원래 버그를 재현하는가"라는 lead의 기준을 통과한다.**

### IRC §12 2층 그래프 — **proposer 판정과 일치, barrier 미지 시 처리 확인**

- **[확인]** `criteria/endpoints.py`가 R1(Layer C 차이)/R2a(entity 수 변화)/
  R2b(Layer I만 차이, τ=0.1eV 속도론 병합)/R3(둘 다 동일) 순서 판정을 구현. τ 기본값
  0.1 eV, `cfg`로 오버라이드 가능.
- **[확인] 요청사항 그대로 반영됨**: `R2b`에서 `barrier_fwd_eV`/`barrier_rev_eV` 중
  하나라도 `None`이면 `UNDETERMINED`(`"R2b-unknown_barrier"`)를 반환하고, `_explain()`이
  "P1 파일럿은 이 barrier를 계산하지 않으므로 여기 걸리는 것이 정상"이라고 명시한다.
  `p1.py::evaluate_p1`이 이 경우를 **`fail`이 아니라 `undetermined` status**로 올바르게
  분기하는 것도 확인(`p1.py:189-194`). 회신 JSON에 `merge_rule_applied`(R1/R2a/R2b-*/R3)가
  그대로 실린다 — lead가 요구한 "어느 규칙으로 판정했는지 기록"을 만족한다.
- **[확인]** 옛 방식(공유결합만 비교)의 결과도 `legacy_covalent_only_distinct`로 남겨
  과거 회신과 비교 가능하게 했고, Layer I 임계 민감도(±delta) 스캔도 함께 계산해
  `threshold_sensitivity.flips`로 판정이 임계값에 종속되는지 드러낸다 — 이건 요청 범위
  밖의 추가 안전장치이나 해로울 게 없어 문제 삼지 않는다.
- **테스트**: `test_R2b_without_barrier_is_undetermined_not_rejected`가 이 경로를 직접
  확인한다.

### 가드 4,000 — **전파 확인**

`budget.py:DEFAULT_MAX_CORE_HOURS=4000.0`, `HANDOFF_TO_LEAD.md` §6 사용자 문구·
`run.sh` 헤더·`README_USER.md` 전부 4,000으로 일관. 회귀 테스트
`test_default_guard_runs_the_whole_approved_package`(예약 3,610.7 core-h — 내가 직접
돌린 `--dry-run` 출력과 일치 — / 상한 4,000) 확인.

### 잔여 확인 사항 (BLOCKER/MAJOR 아님, 기록만)

- **M-1(체인 부분 제출 실패 기록) 자체는 고쳐져 있다** — `cli.py:226-232`에
  `len(ids) < links`일 때 `mark_failed(..., "chain_partial_submit", ..., severity=
  "warning")` 추가 확인. **다만 이 경로를 직접 때리는 회귀 테스트는 못 찾았다**
  (`grep`으로 `chain_partial_submit`/관련 테스트명 검색 — 0건). 코드는 정확해 보이나
  테스트로 고정돼 있지 않아 향후 리팩터링에서 조용히 깨질 수 있다. **MAJOR로도 안
  올린다** — 로직 자체가 단순하고 내가 직접 코드를 읽어 정확함을 확인했기 때문. 다음
  라운드에 여유 있으면 테스트 추가를 권한다.
- **M-2(링크별 실패 마커 잔존)도 함께 고쳐졌다** — `common.sh:114-125`에서 성공 시
  `${SEI_LOGICAL_KEY}.failed.json`을 지운다. `test_failed_marker_is_cleared_when_a_
  later_link_succeeds`로 직접 검증됨(확인).
- **N-1/N-2(MINOR)**: 이번 라운드 대상 아님 — 지시대로 건드리지 않음.

## 판정
**BLOCKER 0건.** **OK — 지금 사용자에게 보내도 된다.**
남은 것은 MINOR 수준(M-1의 테스트 부재, N-1/N-2)뿐이며 전부 "알고 보내도 되는" 수준이다.

---

## 2026-08-17 (대기 중 보강) — Blind Test 정답지 §A/§B 보강 (ADR-016 이후)

**맥락**: coder가 CPU/GPU 패키지 분리 + P5를 작업 중이라 lead 지시대로 착수하지 않고
대기한다. 그동안 ADR-020으로 상시 유지 항목이 된 blind test 정답지를 보강한다.
ADR-016(미량 H2O를 principal species에 추가)으로 §D-3에서 지적한 "원천 배제" 위험은
**입력 정의 차원에서는 해소**됐다. 그런데 H2O가 pool에 들어온다는 것은 §A/§B에서
이미 "확신도 높음"으로 표시했던 HF/PF6⁻ 가수분해 갈래가 **이제 실제로 도달 가능한
목표가 됐다**는 뜻이다 — 그 갈래에 딸린 하위 생성물을 더 촘촘히 채워 넣는 것이
지금 시점에 가장 가치가 크다고 판단했다. 여전히 웹 도구 없이 사전학습 지식에서
복원한 것이므로 확인 수준 태그(`[RECALL-강/약]`/`[추정-화학]`)는 그대로 엄격 적용한다.

### A 보강 — H2O 도입으로 새로 사정권에 들어온 생성물

| 항목 | 분류 | 확인 수준 | 비고 |
|---|---|---|---|
| **H2** (수소 가스) | 가스 부산물 | `[RECALL-강]` | 미량 수분·HF의 **직접 환원**(2H2O + 2e⁻ → H2 + 2OH⁻, 또는 2HF + 2e⁻ → H2 + 2F⁻) 산물. DEMS 초기사이클 가스 분석에서 **C2H4/CO/CO2와 나란히 보고되는 대표 성분 중 하나**로 기억한다 — ADR-003의 3종 가스 목표 자체가 이미 불완전 목록일 수 있다는 뜻이다. H2O가 원천 배제됐던 이전 상태에서는 이 경로 자체가 안 보였다. |
| **LiOH** | 무기 SEI 성분(수분 오염 지표) | `[RECALL-약]` | H2O 환원의 OH⁻ + Li⁺ 직접 결합 산물. 화학적으로 자명하고 XPS 문헌에서 수분 오염 지표로 언급되는 것으로 기억하나, EC/EMC 정상 조성에서 **주성분으로 다뤄지는지는 확신 못 한다.** |
| **LiPO2F2 형성의 대안 경로**: LiPF6 + Li2CO3 → LiPO2F2 + LiF + CO2 | 반응(§B와 중복 게재) | `[RECALL-약]` | PF6⁻ 가수분해(POF3 경유) 말고, **이미 형성된 Li2CO3와 LiPF6/POF3가 직접 반응**해 LiPO2F2를 내놓는 경로도 문헌에서 본 기억이 있다(주로 CEI/양극 표면 논의에서였을 수 있어 SEI/음극 맥락 확신도는 낮다). **이게 사실이면 D-2(응축상이 반응물)와 동일한 구조적 문제**를 하나 더 만든다 — Li2CO3(고체)가 반응물이라 S2-A 분자 CRN이 표현 못 한다. |
| **HPO2F2 / H2PO3F 류 인산 중간체** | PF6⁻ 가수분해 캐스케이드 중간종 | `[추정-화학]` | POF3의 P-F 결합이 순차적으로 가수분해된다면 화학적으로 중간에 이런 종들이 있어야 하는데, 구체 문헌을 못 댄다. "찾아봐야 할 후보"로만 남긴다. |

### B 보강 — 반응

| 반응 | 확인 수준 | 비고 |
|---|---|---|
| 2 H2O + 2e⁻ → H2 + 2 OH⁻ (그리고 2 HF + 2e⁻ → H2 + 2 F⁻) | `[RECALL-강]` | 위 H2 생성물의 근거. 전기화학적으로 표준적인 양성자성 환원 반응이며 확신도가 상대적으로 높다. |
| OH⁻ + Li⁺ → LiOH | `[추정-화학]` | 자명한 결합 반응이나 SEI 문헌에서의 비중은 확신 못 함. |
| LiPF6(또는 POF3) + Li2CO3(고체) → LiPO2F2 + LiF + CO2 | `[RECALL-약]` | 위 표와 동일 근거. **D-2 구조적 맹점의 사례가 하나 더 늘어난 것으로 취급한다.** |
| PF5(Lewis 산)가 EC/EMC 개환·중합을 촉매 | `[추정-화학]`, §C 논쟁 6 신설 | 전해질 저장 안정성/가스 발생 문헌에서 "PF5가 carbonate 중합을 촉진한다"류 서술을 본 기억이 있으나 구체 근거를 못 댄다. §C 논쟁 항목(중합 여부)과 **연결되는 촉발 메커니즘 후보**로만 취급하라 — 정답으로 넣지 마라. |

### C 추가 — 논쟁 항목 6번(신설)
6. **PF5가 EC 개환/중합의 촉매로 작용하는가** — `[추정-화학]`. §A/B의 중합 항목과 얽혀
   있으며, 이게 사실이면 PF6⁻ 화학(무기)과 EC 중합(유기 사슬성장) 두 논쟁이 **하나의
   기구로 묶인다는 뜻**이라 검증 가치가 크다. 그러나 내가 낼 수 있는 근거 수준이 낮아
   정답지가 아니라 "확인이 필요한 가설"로만 분류한다.

### D 갱신 — D-3 상태 정정
**D-3(H2O 부재로 HF 화학 전체 원천 배제)은 ADR-016으로 입력 정의 차원에서 해소됐다.**
단, 위 "LiPF6+Li2CO3→LiPO2F2" 경로처럼 **고체 Li2CO3가 반응물인 하위 갈래는 여전히
D-2(응축상 격자가 반응물)에 걸린다** — H2O를 넣었다고 모든 하위 갈래가 뚫리는 것은
아니라는 점을 분명히 해 둔다. D-2는 그대로 유효한 구조적 맹점이다.

### 이번 보강에서 확신도를 낮게 유지한 이유 (정직성 기록)
이번 보강분은 이전 라운드보다 **평균 확신도가 낮다**(`[RECALL-약]`/`[추정-화학]`이 다수).
H2O 도입 이전에는 없었던 갈래라 내 기억에서 자연히 더 주변부(CEI/양극 논의, 저장
안정성 논의 등 SEI 본류가 아닌 문헌)에서 끌어온 것들이기 때문이다. **이 갈래일수록
proposer의 1차 문헌 대조가 더 중요하다** — 확신도가 낮은 상태로 blind test 정답지에
잘못 들어가면 "못 찾았다"는 오판정을 만든다.

## 재리뷰 대기 상태
coder의 CPU/GPU 분리 + P5 작업 완료 통지를 기다린다. 완료되면 lead가 예고한 4개
신규 실패 모드(프로파일 오염 / 머지 손실 / P4 CPU 기준값 소재 명시 / P5 레벨 라벨)를
최우선으로 검토한다.

---

## 2026-08-17 — 재리뷰: CPU/GPU 프로파일 분리 + P5 + 실행 결함 수정 3건

**범위**: 수정분 + 인접 영역만. **직접 실행**: `python3 -m unittest discover -s tests` →
**375 tests, OK (skipped=8)**(기존 192 → +183. skip 8건은 이 박스에 pyscf 미설치 관련
7건 + df 관련 1건 — 전부 정상적인 환경 부재 skip이지 실패 은폐가 아님을 직접 확인).

### 1. XC 이름 오류 클래스 — **P4(pyscf)는 해소, ORCA(P1/P1b/P5)는 부분 방어**

- **[확인] `sei_pilot/qcnames.py` 신설**: `libxc.parse_xc()`로 **실제 확인된** 이름만
  화이트리스트(`KNOWN_GOOD_XC`)에 넣었고, 실패 시 유효 후보 + 흔한 오타 별칭
  (`XC_ALIASES`, `"wb97x-d3"` → 안내 문구 포함)을 함께 낸다. `preflight_pyscf()`가
  SCF 시작 **전에** 예외를 던진다. **pyscf 부재 시 `(None, ...)`을 돌려줘 "모르는 것을
  통과로 처리하지 않는다"**는 원칙도 지켰다.
- **[확인] ORCA 쪽(`payload/qc_adapter.sh`)**: `sei_qc_smoke()`가 **`sei_orca_header()`
  자체를 두 레벨 다 호출**해 H2 SP를 돌린다 — production 입력을 만드는 함수와 smoke가
  **동일 코드 경로**이므로 범함수·기저·SMD 줄이 어긋날 수가 없는 구조(B-1/B-2와 같은
  "진실을 한 곳에" 패턴). 실패 시 `SEI_ORCA_XC_CANDIDATES`/`SEI_ORCA_BASIS_CANDIDATES`
  후보와 ORCA 원문 로그 25줄을 함께 낸다. **lead가 찾은 클래스(그럴듯하지만 틀린 이름)에
  대해서는 P1/P1b/P5 전부 방어된다.**
- **🟡 잔여 갭(신규 발견, MINOR)**: smoke는 `sei_orca_header`가 만드는 **공통 헤더**
  (범함수/기저/SMD)만 검증한다. `NEB-TS`/`OptTS NumFreq`/`IRC`처럼 **P1.sh에서만 쓰는
  run-type 키워드와 `%neb`/`%geom`/`%irc` 블록**은 smoke 대상이 아니다 — 여전히
  `[UNVERIFIED]`로 남아 있다(원래 설계에서도 이미 인정한 위험이며 이번 라운드가 새로
  만든 갭은 아니다). ORCA는 통상 문법 오류를 파싱 단계에서 빠르게 실패하는 편이라
  피해가 자체적으로 제한되는 경향이 있고, B-1의 단계별 체크포인트 덕에 이미 끝난
  단계(crest 등)는 재과금되지 않는다. **BLOCKER로 올리지 않는다** — 원래도 인정된
  잔여 위험의 연장선이라 이번 라운드 결함이 아니다.

### 2. 프로파일 오염 — **정확 집합(set) 단언 테스트로 해소 확인**

`plan.default_items(profile)`가 `Item.profiles` 태그로 분기(`plan.py:57-141`).
`tests/test_profiles_merge.py::TestProfileSeparation`가 CPU/GPU 항목 집합을 **정확히**
(`assertEqual`, 부분집합이 아니라 등호) 검증한다 — lead가 우려한 "dry-run의 graceful
skip에 가려 안 보이는" 문제를 원천적으로 피하는 가장 강한 형태의 테스트다. 추가로
`test_every_item_declares_at_least_one_profile`/`test_all_items_are_covered_by_the_
two_profiles`가 "**어느 프로파일에도 안 들어가 영원히 안 도는 항목**"이라는, 내가
미처 생각 못 한 실패 모드까지 막는다. `test_payload_file_exists_for_every_item`도
좋은 보험. **직접 확인**: `plan.default_items("cpu")` 키 집합과 `("gpu")` 키 집합이
lead가 적은 리스트와 정확히 일치함을 코드 읽고 대조함.

### 3. 머지 손실 — **무손실 설계 + 충돌 시 "둘 다 보존 + 경고" 확인**

`report.merge_reports()`가 pilots/failures/unresolved를 **전부 이어붙이고** 프로파일을
태깅한다. 같은 파일럿 id가 두 프로파일에 있으면 **덮어쓰지 않고 둘 다 남기며
`merge_warnings`에 올린다** — 이게 프로파일 오염의 **2차 방어선**도 겸한다(머지 시점에
"P4가 cpu.json에도 있다" 같은 충돌이 나면 바로 드러남). `TestMergeLossless`가
카운트 보존·payload 보존(잘리지 않음)·프로파일 태깅·중복 시 경고(양성 대조군
`test_duplicate_pilot_across_profiles_is_kept_and_warned`)까지 확인한다. 머지본 전용
스키마(`validate_merged_report`)도 분리돼 있어 "빈 필드를 채워 억지로 통과"하는 꼼수를
막는다. **문제 없음.**

### 4. P4 CPU 기준값 출처 — **명시 확인**

`plan.py:97-98`(P4 rationale에 "CPU 기준값은 같은 GPU 머신의 CPU로 잰다" 명시) +
`TestP4SpeedRatioReference`가 `cpu_reference.machine == "gpu_host_cpu"`,
`cpu_reference.caveat`에 "HPC" 경고 문구 포함, `ratio_gpu_per_cpu_reference`로 키 이름
자체를 개명(과거 `ratio_gpu_per_node`처럼 분모가 모호한 이름이 아님), `hpc_normalization.
required=True` + `how`에 재정규화 방법 명시를 확인. **분모가 HPC 노드가 아니라 GPU
머신 CPU라는 사실이 JSON 안에 자체 설명적으로 남는다.** 문제 없음.

### 5. P5 레벨 라벨 — **명시 확인**

`criteria/p5.py::verdict()`가 `threshold_basis` 필드에 **값싼 레벨 문자열
("wB97X-D3/def2-TZVP/SMD")을 그대로** 싣고, `caveat`에 "고수준 값에 그대로 적용하지
마라"를 명시한다. `test_threshold_basis_is_cheap_level_not_primary`가 `threshold_basis`에
"TZVPPD"(고수준 표식)가 **없음**을 직접 검증 — 라벨이 빠지는 것도, 라벨이 틀린 것도
둘 다 막는 좋은 음성 대조군이다. **문제 없음.**

### 6. P5 대표종 커버리지

`inputs/p5_species/manifest.json` 14종 직접 대조: 원자수 {3,3,5,5,6,7,10,10,11,11,15,
15,20,21}, 전하 {−1,0,+1} **전부 등장**(hco3_anion/pf6_anion/ec_radical_anion/emc_
radical_anion=−1, 대부분=0, li_ec_cation/li_ec2_cation=+1), 개각(mult=2) 4종
(ch3o_radical·ec_radical_anion·li_ec_radical·emc_radical_anion, 원자수 5/10/11/15에
분포) — **개각이 빠지지 않았다**는 lead의 필수 요구를 만족. `p5.py`가 종별 원자료를
그대로 반환(`test_raw_rows_are_returned_not_averaged`)함도 확인.
- **🟡 사소한 불일치(MINOR)**: `plan.py`의 P5 rationale 텍스트는 "5~25원자 구간"이라
  쓰는데 실제 manifest 범위는 **3~21원자**다(h2o/co2가 3원자로 5 미만, 최대가 21로 25
  미만). 계산 자체나 곡선 적합 가능성에는 영향 없음 — 그냥 서술과 실측 범위가 살짝
  어긋난다. 다음 라운드에 문구만 고치면 된다.

### 7. tarball 신선도 — **직접 확인, 통과**

`test_build_stamp.py::test_real_repo_dist_is_fresh`를 포함한 전체 스위트를 내가 직접
돌려 **지금 `src/dist/`에 있는 실제 tarball 2개가 현재 소스와 내용 해시로 일치함**을
확인했다(스킵이 아니라 `ok`로 실행됨 — dist가 비어 있으면 스킵되는 구조라 실제로 검증
대상이 있었다는 뜻). mtime이 아니라 **콘텐츠 해시** 기준이라 `touch`만으로는 오탐하지
않음(`test_touch_without_content_change_does_not_warn`)도 확인. lead가 우연히 잡았던
사고 유형이 이제 자동화돼 있다.

### 🔴 신규 발견 (MAJOR, 이번 라운드가 만든 것) — `budget.py`의 `guard_source` 서술이
**하드코딩된 채 갱신 안 됨**

- **근거**: `sei_pilot/budget.py:144-150` (`ResourceGuard.to_dict()`). `guard_source`
  필드가 여전히 문자열 리터럴로 **"4,000 core-h / 24 h wall. 패키지 계획 총량
  ~3,150 core-h."** 를 반환한다. 그런데 이번 라운드에서 실제 가드값은
  `PROFILE_GUARDS = {"cpu": max_core_hours=5000, "gpu": max_core_hours=60, ...}`로
  **프로파일마다 다르게 바뀌었다**(`budget.py:36-39`). `grep`으로 `guard_source`를
  전 코드베이스에서 찾아보면 **정의된 곳이 이 한 곳뿐**이고 프로파일별로 갈라지지
  않으며, 이 필드의 내용을 검증하는 테스트도 없다.
- **왜 문제인가**: 회신 JSON의 `guard` 블록 안에서 `max_core_hours`(정확, 5000 또는
  60)와 `guard_source`(부정확, "4,000... 3,150"이라고 서술)가 **같은 객체 안에서 서로
  모순**된다. 예: GPU 리포트를 읽는 사람이 `guard.max_core_hours=60`을 보고도
  `guard.guard_source`가 "4,000... 3,150"이라고 말하면 어느 쪽을 믿어야 할지 헷갈리고,
  최악의 경우 "가드가 4,000으로 잘못 설정된 게 아닌가"라는 불필요한 왕복 질문을 만들
  수 있다. **실행 안전에는 영향이 없다** — 실제 상한 강제는 `self.max_core_hours`가
  정확히 하고 있으므로 계산이 폭주하거나 잘못 승인되는 일은 없다. 순수하게 **서술
  필드의 자기모순**이다. B-1(SEI_KEY 불일치)·B-2(stride 불일치)·XC 이름 문제와 **같은
  계열**(진실이 두 곳에 있다가 한쪽만 갱신됨)이지만 **파급력은 훨씬 작다**(안전에
  안 걸리고, 사람이 읽는 서술 텍스트 하나에 그친다).
- **고쳐라(제안)**: `guard_source`를 `self.max_core_hours`/`self.max_wall_h`/전달받은
  `profile`로부터 **동적으로 생성**하거나, 최소한 프로파일별 문자열을
  `PROFILE_GUARDS`에 같이 정의해 `guard_for_profile()`이 채워 넣게 하라.
- **판정에 대한 영향**: **MAJOR로 기록하되 BLOCKER로 올리지 않는다.** 이유: (1) 실제
  가드 강제력은 정확하다 — 이건 안전장치가 아니라 안내문이다. (2) 옆에 있는
  `max_core_hours`/`max_wall_h`/`max_gpu_hours` 필드가 전부 정확하므로 신중히 읽으면
  틀린 서술을 무시하고 정확한 값을 쓸 수 있다. (3) 고치는 데 코드 몇 줄이면 되고,
  당장 사용자에게 인도해도 **계산 결과나 안전성에는 영향이 없다.** "알고 보낸다"로
  분류한다.

## 판정
**BLOCKER 0건.** **OK — 지금 사용자에게 보내도 된다.**
남은 것: MAJOR 1건(guard_source 서술 불일치 — 안전에 영향 없음, 알고 보낸다) +
MINOR 2건(ORCA smoke가 NEB-TS/IRC 전용 키워드는 검증 못함 — 원래도 인정된 위험 /
P5 원자수 범위 서술 3~21 vs 문서상 5~25). 지난 두 라운드 기준(원래 버그를 재현하는
테스트인가) 그대로 적용해 확인했고, 이번에 coder가 추가한 375−192=183개 테스트는
전부 구체적 실패 시나리오를 겨냥하고 있었다(트리비얼하지 않음).

---

## 2026-08-17 — 재리뷰 예고 수신 (사전 준비 메모, 착수는 아직 안 함)

lead가 "coder 재작성이 곧 끝난다. 그때 정식 요청을 보내겠다"며 **RT-1b 누락 방지**를
미리 당부했다. 정식 재리뷰 요청 전이므로 코드를 아직 건드리지 않는다(코드가 아직
바뀌는 중일 수 있음). ADR-032/033을 읽고 체크리스트만 만들어 둔다 — 실제 검증은
정식 요청 수신 후 수행한다.

### 🔴 최우선 확인 항목 — RT-1b 5수 (engineer 정지 선언의 유일한 요구)
회신 JSON(아마 P1b 확장분)에 다음 5개 값이 **실제로** 나오는지 확인한다:
① 값싼 레벨(`ωB97X-D/def2-SVPD`) 단가 ② 고수준 배수 ③ 🔴 **composite 배수
(`r_composite`, 정의: 기하·진동수 SVPD // 에너지 SP TZVPPD, 예상 ≈1.25) — 이게 빠지면
ADR-032의 사전 확약 판정 규칙(`|ΔG|<0.05` 채택 / `0.05~0.1` 채택+σ_r 상향 / `≥0.1` 불가)을
**적용할 방법이 없다** ④ `gen`(외부 기저) 페널티 ⑤ SCF 실패율.

### 병행 확인 목록 (lead 예고, 착수 시 순서대로)
1. **P2 계열 처분**(ADR-033): P2ext·p2_scaling **삭제**, P2 → **P2f**(CP2K FIST 스모크,
   <50 core-h)로 교체. **죽은 참조**(cp2k_common.sh, criteria/p2.py, cp2k_aimd.inp.tmpl 중
   AIMD 전용 부분) 잔존 여부 + 삭제 사유가 `HANDOFF_TO_LEAD.md`에 기록됐는지.
   ⚠ **B-2에서 내가 검증한 s(t) 시간축 코드가 이번에 죽은 코드가 될 수 있다** — 삭제가
   맞다면 문제없지만, **부분 삭제로 죽은 참조만 남기는 것**이 새 실패 패턴일 수 있다.
2. **QC 코드 전환(ORCA → Gaussian16)**: 어댑터 분리 여부(한 파일에 두 문법 혼재 금지).
   `gen` 외부 기저(def2-TZVPPD/def2-TZVPD, C/H/O/Li/P/F) 동봉 여부. preflight가
   "키워드 유효성"이 아니라 **"동봉 기저가 계에 등장하는 원소를 전부 덮는가"**로
   바뀌었는지 — 이건 지난 라운드 qcnames.py 패턴과 다른 성격의 검증이라 새로 봐야 한다.
3. **이기종 노드 sizing — fail-loud 요구**: `compute_nodes`가 비었을 때 **조용히
   `login_cpu`로 폴백하면 안 된다**(engineer가 지목한 사고 기구). 폴백 잔존 여부가
   최우선 확인 대상 — 이건 지금까지의 "값이 두 곳에 있어 한쪽만 갱신" 패턴과 달리
   **"에러가 나야 할 곳에서 조용히 대체값을 쓰는"** 새로운 실패 유형이다.
4. 항목별 계정(`-A`) 매핑 + dry-run 표시.
5. xtb 동봉(`vendor/xtb/`) — 라이선스·체크섬·glibc 실패 시 조용히 안 죽는지.
6. PBS 3중 방어(로컬 검증기 + canary + `qsub -h`) — **"사전검사 통과"를 거짓 표시하지
   않는지**가 핵심(값싼 검사를 비싼 검사인 것처럼 표시하는 것도 이 프로젝트에서 반복된
   신뢰성 문제의 한 형태로 취급해서 본다).
7. P5 독립 시드 2회(`σ_protocol`, ADR-031).
8. **composite 도입에 따른 M2(허수진동수 크기 cm⁻¹) 임계 재보정** — proposer가 명시
   요구(존재/개수는 기저 둔감, 크기는 민감). `criteria/p1.py`의 `IMAG_WINDOW_CM1 =
   (-2000, -100)`이 지금 값싼 기저(SVPD) 기준으로 다시 산정됐는지, 아니면 예전
   고수준 기준 숫자가 그대로 남아 있는지가 핵심 — **이게 바로 "같은 사실이 두 곳에
   있고 한쪽만 갱신됨"의 여섯 번째 반복일 가능성이 가장 높은 지점이다.**

### 대기 상태
정식 재리뷰 요청 수신 시 위 체크리스트 순서로 착수한다. 지난 세 라운드 기준 유지:
"테스트를 추가했다"가 아니라 "그 테스트가 원래 버그(또는 이번 요구사항 위반)를
잡는가."

---

## 2026-08-17 — 재리뷰: RT-1b/M2/Gaussian16 전환 + P2 처분 — **BLOCKER 2건 발견**

**범위**: 수정분 + 인접 영역. **직접 실행**: `python3 -m unittest discover -s tests` →
**520 tests, OK (skipped=8)**. ⚠ **테스트 전부 통과했지만 아래 두 BLOCKER는 실제 실행/
코드 추적으로만 드러났다 — "테스트 통과"가 이번에도 정확성의 근거가 아니었다.**

## BLOCKER

### B-3. 🔴 **P1의 진동수 판정이 Gaussian16 로그를 파싱하지 못한다 — 모든 실제 P1 결과가
"fail"로 나온다**

- **근거**: `sei_pilot/criteria/p1.py::parse_frequencies()`(및 그걸 부르는
  `evaluate_freq`/`evaluate_p1`)가 여전히 **자기 내부의 ORCA 전용 파서
  (`parse_orca_frequencies`, `"VIBRATIONAL FREQUENCIES"` 블록 탐색) +
  제네릭 폴백("450.1i" 또는 "Frequency:" 줄)만** 쓴다. 반면 QC 코드는 Gaussian16으로
  전환됐고, `collect_p1()`(`collect.py:150-186`)은 `code.startswith("gaussian")`일 때
  IRC 끝점은 `_g16_last_geometry_xyz()`로 **올바르게** g16 형식을 XYZ로 변환해 넘기지만,
  **주파수 텍스트(`freq_text`)는 변환 없이 Gaussian 로그 원문을 그대로
  `p1.evaluate_p1(freq_text=...)`에 넘긴다.** `evaluate_p1` 내부는 이 텍스트를
  `g16.parse_frequencies()`(별도 신설 모듈, `Frequencies --` 형식을 정확히 파싱함)로
  보내지 않고 여전히 자신의 ORCA 파서를 부른다.
- **[확인] 직접 실행으로 재현**: 실제 Gaussian16 형식 텍스트
  (`Frequencies --   -450.1234    112.4000    331.0000`)를 만들어
  `g16.parse_frequencies()`와 `p1.parse_frequencies()`에 각각 먹였다.
  - `g16.parse_frequencies(sample)` → `[-450.1234, 112.4, 331.0, 450.1234, 600.0, 720.0]`
    (정확)
  - `p1.parse_frequencies(sample)` → `([], 'none')` (**완전 실패**)
  - `p1.evaluate_p1(freq_text=sample, ...)` → `status='fail'`,
    `criteria={'imag_freq_count': 0, ...}`, `fail_reasons=['no_frequencies_parsed', ...]`
- **왜 테스트가 못 잡았는가**: `g16.py`는 `tests/test_g16_adapter.py`에서 **단위
  테스트로는 철저히 검증**돼 있다(주파수 파싱 포함). 그러나 `tests/test_criteria.py`의
  `p1.evaluate_p1` 관련 테스트는 전부 `ORCA_FREQ_GOOD`(ORCA 형식) 픽스처만 쓴다
  (`grep`으로 확인, Gaussian 형식 입력을 쓰는 테스트 0건). **두 모듈이 각각 단위
  테스트는 통과하지만, "Gaussian 로그 → evaluate_p1"이라는 통합 경로 자체가 한 번도
  실행된 적이 없다.** IRC 쪽은 `_g16_last_geometry_xyz`로 다리를 놓았는데 **주파수
  쪽만 그 다리를 놓는 걸 빠뜨렸다** — IRC는 고쳤고 freq는 안 고친, 부분 이식의 전형.
- **영향**: **사용자 클러스터에서 P1(약 1,000 core-h)이 완주해도, 진짜 TS를 찾았어도,
  회신 JSON은 무조건 `status: fail`, `imag_freq_count: 0`을 보고한다.** 이 패키지의
  핵심 존재 이유(S3 TS 단가 스프레드 8배→3배 축소 실측)가 산출물 자체에서 무너진다.
  스모크 테스트도 이 경로를 검증하지 않는다(스모크는 `sei_orca_header`/`sei_qc_smoke`
  가 아니라 Gaussian 쪽 다른 함수를 쓸 텐데, 어느 쪽이든 판정 로직 자체를 실행하지
  않으므로 이 버그를 잡을 수 없다).
- **고쳐라**: `evaluate_p1`(또는 그 호출부 `collect_p1`)이 QC 코드를 알고
  `g16.parse_frequencies()` 결과(이미 파싱된 float 리스트)를 직접 받아들이도록
  바꿔야 한다. 가장 안전한 방법: `p1.parse_frequencies()`가 ORCA 포맷을 못 찾으면
  `g16.parse_frequencies()`도 시도하도록 레이어를 추가하거나(이번 리뷰에서
  B-2가 취했던 "우선순위 폴백" 패턴과 동일), `collect_p1`이 Gaussian 분기에서
  이미 파싱된 진동수 리스트를 `evaluate_p1`에 직접 넘기도록 인터페이스를 바꿔라.

### B-4. 🔴 **P2f가 CP2K를 절대 찾지 못한다 — 변수 이름 불일치**

- **근거**: `payload/cp2k_common.sh::sei_cp2k_detect()`는 **`SEI_CP2K`**를 설정한다
  (`SEI_CP2K="$(command -v $c)"; export SEI_CP2K`). 그런데 `payload/P2f.sh:18,19,34`는
  **`SEI_CP2K_BIN`**을 검사·사용한다(`[ -z "${SEI_CP2K_BIN:-}" ] && ... exit 3`,
  `"${SEI_CP2K_BIN}" -i p2f.inp ...`). **`SEI_CP2K_BIN`은 코드 어디에서도 설정되지
  않는다**(`grep -rn "SEI_CP2K_BIN" payload/*.sh` → P2f.sh의 3곳뿐, 정의하는 곳 없음).
  `set -u` 환경에서 `${SEI_CP2K_BIN:-}`는 항상 빈 문자열로 평가되므로, **CP2K가
  실제로 설치돼 있고 `sei_cp2k_detect`가 정확히 찾아내도, P2f.sh는 항상 "CP2K 없음 →
  생략"으로 즉시 종료(`exit 3`)한다.**
- **왜 테스트가 못 잡았는가**: `tests/test_plan_report_e2e.py:153-154`의
  `test_missing_software_skips_with_reason_not_failure`류 테스트는 **이 개발 박스에
  CP2K가 실제로 없는 상태**에서 "P2f가 skip 상태고 사유에 cp2k가 들어간다"만
  확인한다 — 이건 **버그가 있어도 없어도 똑같이 통과하는 테스트**다(우연히 정답과
  같은 결과가 나오는 경우). "CP2K가 있을 때 P2f가 실제로 도는가"를 목(mock) CP2K
  바이너리로 검증하는 테스트가 없다.
- **영향**: `<50 core-h`짜리 저비용 스모크라 core-h 낭비는 미미하지만, **P2f의
  존재 이유(이 클러스터에서 CP2K FIST를 쓸 수 있는지 확인 — ADR-012의 λ_out 고전
  MD 경로의 전제조건)가 원천적으로 달성되지 않는다.** 실제로 CP2K가 있는 클러스터
  에서도 회신 JSON은 "CP2K 없음"이라고 거짓 보고하며, 이는 향후 λ_out 작업 착수
  여부 판단을 오도한다.
- **고쳐라**: `P2f.sh`의 `SEI_CP2K_BIN`을 `SEI_CP2K`로 통일하거나(가장 간단),
  `sei_cp2k_detect()`가 `SEI_CP2K_BIN`이라는 별칭도 함께 export하게 하라.

### 부수 발견 (MINOR) — cp2k_common.sh의 죽은 참조 (도달 불가, 당장 위험하진 않음)

`cp2k_common.sh`의 `sei_cp2k_input()`은 여전히 존재하지 않는
`${SEI_PKG_ROOT}/inputs/cp2k_aimd.inp.tmpl`(P2/P2ext와 함께 삭제됨)을 참조하고,
`sei_spin_series()`는 존재하지 않는 `sei_pilot.criteria.p2` 모듈을 import한다.
**[확인] 다행히 이 두 함수는 이제 아무 payload에서도 호출되지 않는다**
(`grep -rln "sei_spin_series\|sei_cp2k_input\|sei_cp2k_smoke" payload/*.sh` →
정의부인 `cp2k_common.sh` 자신만 걸림). 즉 **현재는 도달 불가능한 죽은 코드**라 당장
크래시는 안 나지만, 나중에 누군가 "CP2K 어댑터에 이미 있는 함수"로 착각하고 재사용하면
그 순간 깨진다. lead가 요구한 "삭제 사유가 HANDOFF에 기록됐는가"는 확인했다
(`HANDOFF_TO_LEAD.md`에 ADR-033 처분 내역 기록 있음) — 문서화는 됐으나 **코드 정리는
안 됐다.** 다음 라운드에 `sei_cp2k_input`/`sei_qc_smoke`/`sei_spin_series`와 주석의
"P2 / P2ext / p2_scaling 공유" 문구를 함께 지우기를 권한다.

## MAJOR — fail-loud 요구가 문자 그대로 구현되지 않음 (완화책은 있음)

engineer 정지 선언의 문구는 **"실패시켜라"**(하드 실패)였다. `tests/test_
heterogeneous_sizing.py`와 실제 코드(`cli.build_env`)를 대조한 결과, coder는
**"조용히 폴백하지 않는다"는 조용히(silent) 쪽만 없앴을 뿐, 폴백 자체(그리고 그 값으로
계속 진행하는 것)는 유지**했다 — `compute_nodes`가 없으면 `login_cpu` 값을 쓰되
`cores_per_node_is_login_fallback=True` + 출처 문자열에 `🔴` + dry-run 텍스트에
`--cores-per-node` 수정 힌트를 띄운다(`test_falls_back_to_login_with_a_loud_marker`,
`test_plan_text_shouts_about_the_fallback`로 확인). **하드 실패(예외/exit)는 아니다.**
- **[확인] 완화 요인**: `cmd_submit`이 `cmd_preflight`를 먼저 호출해 계획 텍스트를
  출력하고, 원래 설계(§R2-6 D-2)상 15초 중단 기회를 준 뒤에 실제 제출로 넘어간다 —
  즉 이 경고는 `--dry-run`뿐 아니라 **실제 제출 경로에서도 사용자 눈에 보인다.**
  원래 사고("dry-run이 24를 정상값처럼 보고해서 사용자가 그대로 승인")의 핵심
  실패 조건(**경고가 안 보임**)은 실제로 제거됐다.
- **판정**: **BLOCKER로 올리지 않는다.** 그러나 이건 lead/engineer가 명시적으로
  요구한 동작과 **다른** 것을 구현한 것이므로, "coder가 독자 판단으로 요구사항을
  약화했다"는 사실 자체는 lead가 알고 재승인해야 한다고 본다 — 내가 대신 판정할
  사안이 아니다.

## 확인했으나 문제 없음 (요약)
- **RT-1b 5수**: `payload/P1b.sh`에 [A]값싼레벨 [B]고수준 [C]composite(A+C 조합)
  [D]gen 페널티(같은 기저로 gen vs 내장 분리, engineer 원 요청의 "혼입" 문제를
  올바르게 피함) + SCF 실패율 구조를 직접 코드로 확인. `r_composite` 계산에 필요한
  A/C 단계가 모두 존재.
- **P5 Gaussian 전환**: `g16.summarize()`를 통해 완전히, 깨끗하게 마이그레이션됨
  (ORCA 잔재 없음). dual-seed(σ_protocol) 구조도 확인.
- **P1b의 SCF/termination 파싱**: `.log` 확장자 분기로 `g16.parse_scf`/
  `g16.parse_termination`을 올바르게 사용(`collect_p1b`).
- **M2 provenance**: `imag_window_provenance()`가 `_basis_from_route(freq_text)`로
  로그 route를 직접 파싱해 매 판정에 어느 기저였는지 싣는다(하드코딩 아님). 다만
  **freq_text 자체가 위 B-3 버그로 실제 생산 로그에서는 애초에 파싱 실패 상태이므로,
  이 provenance 필드는 정확해도 그 위에 얹힌 판정 자체가 잘못돼 있다는 점이 더
  근본적인 문제다.**
- **M2 (b) 논거의 논리적 빈틈**(lead가 의심한 지점, "경계까지 거리 vs 창 폭"):
  **[의심 유지, 미해결]** — coder의 주석은 "창 폭 1,900이 변동을 덮는다"고만 쓰고
  하한(−100) 근처의 얕은 TS가 경계 밖으로 밀릴 위험은 별도로 다루지 않는다. 다만
  이 문제는 **proposer 판정 대상으로 이미 명시적으로 위임**돼 있고
  (`IMAG_WINDOW_PROVENANCE.who_can_change`), coder가 임의로 숫자를 정하지 않은 것
  자체는 올바른 태도다. **lead의 의심이 옳다고 본다** — 재보정이 필요할 가능성이
  있으나, 이건 코드 버그가 아니라 **아직 답이 나지 않은 과학적 판단**이므로 critic
  판정 범위(코드 정확성) 밖에 둔다. proposer에게 넘겨야 한다.
- **`guard_source`(직전 라운드 MAJOR)**: 이번 라운드에 `self.describe()`로 동적
  생성되게 고쳐졌음을 확인.
- **테스트 스위트**: 520 tests, OK.

## 확인하지 못한 것 (시간 제약)
- **PBS 3중 방어**(로컬 검증기+canary+`qsub -h`)의 "사전검사 통과를 거짓 표시하지
  않는가" — 코드 존재는 확인했으나 표시 문구까지 정밀 대조하지 못했다.
- **xtb 동봉**(`vendor/xtb/`)의 라이선스·체크섬·glibc 실패 처리 — 미확인.
- **gen 기저 preflight**(`basisset.py::check_coverage`)의 세부 로직 — 함수 존재만
  확인, 원소 목록 C/H/O/Li/P/F 커버리지 산식까지 검증 못함.
- **패키지 무결성 재확인**(타르볼 mtime, `.pyc` 0건, provenance 3건) — lead가 이미
  확인했다고 했으나 나는 이번 라운드에서 직접 tar 압축을 풀어 대조하지 못했다.
  단, `test_real_repo_dist_is_fresh`가 전체 테스트 스위트 실행에 포함돼 통과했으므로
  **최소한 소스-tarball 해시 일치는 자동으로 검증됨**.

## 판정
**FIX-THEN-RUN. BLOCKER 2건 — 지금 사용자에게 보내면 안 된다.**
B-3(P1 판정이 항상 fail로 나옴)이 가장 심각하다 — 실제 HPC의 core-h(약 1,000)가
소모돼도 산출물이 무의미해진다. B-4는 저비용이지만 P2f의 존재 이유를 무효화한다.
둘 다 국소 수정(각각 함수 하나~변수 이름 하나)이라 왕복 1회 안에 고칠 수 있는
규모이나, **반드시 "Gaussian 로그를 실제로 먹이는" 통합 테스트를 회귀 테스트로
추가하도록 요구해야 한다** — 이번에도 컴포넌트 단위 테스트는 전부 통과했지만
통합 경로 자체가 한 번도 실행되지 않아 놓친 것이기 때문이다.

---

## 2026-08-17 — 재재리뷰: B-3/B-4 수정 검증 + MAJOR(null cores_per_node) 판정

**원칙**: lead의 지적을 그대로 받는다 — **존재 확인이 아니라 실행 확인**을 한다.
아래는 전부 내가 **직접 실행**한 결과다(grep이 아니라 subprocess/함수 호출).

## B-3 수정 검증 — **진짜 고쳐졌다, 그리고 회귀 테스트가 진짜로 버그를 잡는다는 것도 확인**

1. **직접 실행**: `p1.parse_frequencies(gaussian_sample)` →
   `([-450.1234, 112.4, 331.0, 450.1234, 600.0, 720.0], 'gaussian')`. 정확.
   `evaluate_p1(freq_text=gaussian_sample, ...)` → `imag_freq_count: 1`,
   `imag_freq_cm: -450.1` — 정확히 파싱되고 판정에 반영된다.
2. **`tests/test_integration_paths.py` 19개 직접 실행** → 전부 OK. 실제 G16 TS 로그
   전문(route 줄 + SCF + `Frequencies --` 2줄 + 정상종료 문구)을 만들어
   `collect_mod.collect_p1()`을 처음부터 끝까지 돌리는 진짜 통합 테스트임을 코드로
   확인했다.
3. **🔴 lead 요청 2번 — "이 테스트가 수정 전 코드에서 실제로 실패하는가"를 직접
   재현했다.** `p1.parse_frequencies`를 **원래 버그 버전**(ORCA+generic만, gaussian
   디스패치 제거)으로 몽키패치하고 `TestGaussianLogReachesP1Verdict`를 다시 돌렸다:
   → **7개 중 3개 FAIL** (`test_frequencies_are_parsed_from_the_gaussian_log`,
   `test_parser_used_is_reported_as_gaussian`, `test_status_is_not_a_false_fail` —
   후자의 실패 메시지에 실제로 `"status": "fail"`, `"reasons": ["no_frequencies_parsed"]`
   가 그대로 찍혔다). **이 회귀 테스트는 진짜로 원래 버그를 잡는다.** 존재 확인이
   아니라 실행 확인으로 검증 완료.

## B-4 수정 검증 — **진짜 고쳐졌다, 양성 대조군도 진짜로 작동한다**

1. **직접 확인**: `cp2k_common.sh`가 `SEI_CP2K`만 export하고, `P2f.sh`도
   `SEI_CP2K`만 참조한다(`SEI_CP2K_BIN`은 주석의 사고 기록에만 남음). **죽은 함수
   3개(`sei_cp2k_input`/`sei_spin_series`/`sei_cp2k_smoke`)도 실제로 삭제됨**을
   직접 파일을 읽어 확인했다(`sei_cp2k_detect`/`sei_cp2k_launcher` 둘만 남음) —
   내가 이전 라운드에 지적한 MINOR(죽은 참조)도 함께 해소됐다.
2. **`TestP2fActuallyRunsWithAMockCp2k` 5개 직접 실행** → 전부 OK. 목(mock) cp2k를
   `PATH`에 올리고 `P2f.sh`를 실제 `bash` subprocess로 실행해 진짜로 도는지 확인하는
   양성 대조군이 실재함을 코드로 확인.
3. **🔴 이 양성 대조군도 실제로 버그를 잡는지 직접 재현했다.** 패키지 사본을 떠서
   `P2f.sh`만 `SEI_CP2K` → `SEI_CP2K_BIN`으로 되돌리고(옛 버그 재현), 목 cp2k를
   PATH에 올려 실행: → **`returncode: 3`, `"[P2f] CP2K 없음 → 생략"`** — 목 cp2k가
   버젓이 PATH에 있는데도 없다고 보고하는 **정확히 원래 버그를 재현**했다. 즉 이
   테스트는 진짜 버그를 잡는 진짜 양성 대조군이다.

## MAJOR — cores_per_node null 판정과 실제 잡 사이징의 관계 (lead의 자기 의심 검증)

- **[확인] lead가 우려한 사실관계는 맞다**: `cli.py::build_env()`의 `env["cores_per_node"]`
  는 계산 노드 사양을 모르면 여전히 `cores_login`(폴백값)을 담고(`cli.py:118-123`),
  이 값이 그대로 `submit_entry`/`JobSpec.cores_per_node`(`cli.py:478` 등)로 흘러가
  **실제 제출되는 잡의 자원 요청(SLURM `--ntasks-per-node`/PBS `ncpus=`)에 쓰인다.**
  반면 회신 JSON의 `cluster.cores_per_node`는 `report.py`에서 **완전히 별도 경로로,
  실측 probe_node/partition 값에서만** 계산되므로 실제로 `null`이 된다
  (`report.py:58-71`). **즉 "회신은 모른다고 정직하게 말하면서, 실제 제출은 여전히
  추정값으로 나간다"는 lead의 우려는 사실관계로 정확하다.**
- **[분석] 그러나 이게 새로운 위험을 만드는지 추적했다 — 아니다, 자기일관적이다.**
  `size_job()`의 wall·링크·예약 계산과 실제 제출 스펙(nodes/cores_per_node)이
  **동일한 `env["cores_per_node"]` 값 하나**에서 함께 파생된다. 즉 가정이 틀려도
  가드 예약과 실제 제출 요청이 **서로 어긋나지 않는다** — 폭주(가드를 회피해 더 많이
  쓰는 경로)는 없다. 틀렸을 때 벌어지는 일은 둘 중 하나뿐이다:
  - 계산 노드가 로그인보다 **코어가 많은** 경우(가장 흔함, 실제 사고 사례도 이 방향
    24 vs 64): 요청 코어 수가 실제보다 **적게** 나간다 → 노드의 일부만 씀 → **비효율
    적이지만 안전**(제출 자체는 대개 수락됨). wall이 보수적으로 길게 잡히므로 오히려
    24h 캡을 못 채우고 끝날 위험이 크다(성능 손실이지 안전 문제 아님).
  - 계산 노드가 로그인보다 **코어가 적은** 드문 경우: 요청이 거부될 수 있으나, 이는
    `adapter.submit()`이 `None`을 돌려 `mark_failed(..., "submit_rejected", ...)`로
    **이미 있는 부분실패 격리 경로**가 그대로 잡는다(조용히 사라지지 않음).
  - 둘 다 **회신 JSON에서 `cores_per_node`가 null임을 보고 사람이 알아챌 수 있는 것**이지,
    코드가 잘못된 숫자를 "측정값"으로 자동 소비해 **잘못된 결론(예: 단가 재계산)을
    내리는 것은 아니다** — 그리고 그게 바로 lead가 막으려던 사고(ADR-034, engineer가
    24를 신뢰해 한 라운드를 날림)의 정확한 재발 방지 대상이었다. **그 사고는
    막혔다.**
- **판정**: **BLOCKER로 올리지 않는다.** 이건 "probe 결과를 알기 전에 잡을 미리
  사이징해야 하는" 이 패키지 구조 자체의 근본적 제약(닭과 달걀)이며, 완전히
  없애려면 "probe_node 완료를 기다렸다가 나머지를 사이징하는 2단계 제출"이라는
  더 큰 설계 변경이 필요하다 — 이번 라운드의 요구사항(진짜 계산 노드 값이 없을 때
  거짓으로 "측정됐다"고 말하지 않는 것)은 정확히 달성됐다. 다만 **다음 라운드에
  고려할 개선 후보**로 남긴다: dry-run 요약에 "이 계획은 폴백값 24로 사이징됐다"는
  경고가 있으나(`format_plan_text`, 이미 확인), 이 경고가 전역 1회성이 아니라 실제
  영향받는 항목별로도 보이면 더 좋다(현재는 모든 항목이 동일 폴백값을 쓰므로 전역
  경고 1회로 충분하다고 판단 — 이것도 문제 삼지 않는다).

## 나머지 확인
- **P1b/P3/P5에 같은 유형(부분 이식)의 잔여 결함 없음**: `p1b.py`의 판정 함수들은
  원문 텍스트를 직접 파싱하지 않고 이미 추출된 값만 받는다(collect_p1b가 `.log`
  분기로 g16 파서를 올바르게 부름, 이전 라운드에 이미 확인). `p1b.parse_orca_scf_
  cycles`는 `.log`가 아닌 파일에 대한 **도달은 하나 실제로 호출될 일 없는** 관성
  코드(Gaussian 전용 체제이므로) — 위험하진 않으나 다음 정리 라운드 후보.
  P3는 xtb(애초에 ORCA/Gaussian과 무관)라 이 클래스의 버그 대상이 아니다.
  `grep`으로 `p1.parse_frequencies`/`parse_orca_frequencies`/`parse_generic_
  frequencies`를 부르는 곳이 `p1.py` 자신 외에 없음을 확인 — 다른 곳에 같은 함정이
  없다.
- **테스트 스위트**: 539 tests 직접 실행 → OK (skipped=8, 이전과 동일한 환경 부재
  skip). B-3/B-4 관련 19개는 위에서 개별 확인.

## 판정
**BLOCKER 0건. OK — 지금 사용자에게 보내도 된다.**

두 BLOCKER(B-3, B-4) 모두 (a) 코드가 실제로 고쳐졌음을 직접 실행으로 확인했고,
(b) 회귀 테스트가 존재할 뿐 아니라 몽키패치/사본 조작으로 **원래 버그를 재현해
그 테스트가 실제로 실패하는지까지 검증**했다. MAJOR 1건(계산 노드 미확정 시 잡
사이징에 여전히 로그인 폴백값이 쓰이는 것)은 추적 결과 **가드와 제출 스펙이
자기일관적이라 폭주·오판정 위험이 없고**, 애초에 이번 라운드가 막으려던 사고
(잘못된 숫자가 "측정값"으로 소비되는 것)는 정확히 막혔음을 확인했다 — 남은 것은
성능/효율 문제이지 안전 문제가 아니므로 다음 라운드 개선 후보로 남기고 지금
인도를 막지 않는다.

---

## 2026-08-17 — 최종 재리뷰: CP2K 전면 제거 + U-27 NonEq 스모크

**범위**: 변경 2건(CP2K 제거, P1b의 U-27 스모크)만. **직접 실행**: 전체 스위트
542 tests, OK (skipped=8) + `tests/test_u27_noneq.py` 16개 단독 실행 OK.

## 1. CP2K 전면 제거 — **깨진 곳 없음, 잔존은 의도된 인벤토리**

- **[확인]** `payload/cp2k_common.sh`, `payload/P2f.sh` **파일 자체가 삭제**됨
  (`ls` → No such file). `sei_pilot/plan.py`에 `P2f`/`cp2k` 항목 0건. 아무 payload도
  `cp2k_common`을 source하지 않음(`grep` 0건). `accounts.json`에서 `cp2k` 키 제거
  + `_removed`에 복원 절차 기록.
- **[확인] 남은 4곳(payload/probe_node.sh, sysprobe.py, report.py, units.py)의
  "cp2k" 문자열을 각각 대조**:
  - `probe_node.sh:59`, `sysprobe.py:18,26,320` — **소프트웨어 인벤토리 탐지
    목록**의 원소 하나일 뿐(orca/g16/vasp_std/qchem/xtb와 나란히). 삭제된 함수를
    부르지 않는다 — 단지 "이 바이너리가 PATH에 있는가"를 확인하는 문자열 리스트에
    남아 있을 뿐이라 **삭제해도 안 해도 실행에 영향 없다.** lead 주장(가용성
    인벤토리, 축 3 DFT MD 폴백용)과 일치 — **내가 코드로 직접 확인**했다(lead
    말을 근거로 삼지 않음).
  - `report.py:41` — docstring 예시 문자열(`{"cp2k": {"path":...}}`). 순수 설명.
  - `units.py:91` — `drift_mev_per_atom_per_ps()` docstring의 "CP2K의 .ener 파일은..."
    이라는 **일반 단위환산 설명**. 이 함수 자체는 여전히 유효한 범용 유틸이며
    CP2K 전용 코드에 묶여 있지 않다.
  **판정**: 죽은 참조 0건. 지난 라운드 지적(MINOR)했던 죽은 함수 3개도 파일째
  삭제로 완전히 해소.

## 2. U-27 NonEq 스모크 — **격리·폴백·실패 처리 모두 확인**

- **[확인, 코드 추적] RT-1b 5수와 완전히 분리된 데이터 경로**: RT-1b의 [A]/[B]/[C]/[D]
  단계는 `$D/steps/<tag>/job.log`에서, U-27은 `$D/u27${sfx}/stepN.log`에서 각각
  읽힌다(`collect.py`의 `steps_dir` 순회는 `stagewise_`로 시작하는 것만 제외할 뿐
  `u27` 디렉터리는 애초에 다른 경로라 순회 대상에 들지도 않는다). `res["status"]`는
  U-27 처리 **이전에** `p1b.evaluate_p1b()`로 이미 확정되고, U-27 결과는 별도 키
  `res["u27_noneq"]`로만 붙는다. **구조적으로 U-27이 5수·status를 오염시킬 수
  없다.**
- **[확인, 직접 실행] `tests/test_u27_noneq.py` 16개** — mock g16을 세 가지 모드
  (accepting/rejecting/hostile)로 만들어 **실제 `payload/P1b.sh`를 bash subprocess로
  끝까지 실행**하는 진짜 통합 테스트임을 실행해 확인했다:
  - `TestSmdRejectedIefpcmFallback`: SMD+NonEq만 거부하는 mock에서 실제로 IEFPCM
    폴백이 시도되고 `solvent_model_used: "iefpcm"`, `iefpcm_fallback_needed: true`가
    회신에 남는다 — **폴백이 진짜로 동작하고 진짜로 기록된다.**
  - `TestAllNonEqRejected`: 모든 NonEq가 거부되는 최악의 mock에서도
    `test_p1b_does_not_die`(returncode 0) +
    `test_rt1b_measurements_survive_the_u27_failure`(steps/ 디렉터리에 A/D 단계
    산출물 존재)가 **동시에** 통과 — U-27 완전 실패가 나머지 5수를 죽이지 않음을
    실행으로 확인.
  - 실패 사유(`failed_at_step`, `g16_excerpt`)도 정확히 채워짐 — 실패가 데이터로
    남는다.
- **[확인, 코드 추적] `.chk` 복사 실패 시 조용히 틀린 답이 나오는가** — lead가
  가장 우려한 지점. `cp -f "$w/step1.chk" "$w/step${st}.chk" 2>/dev/null || true`
  자체는 복사 실패를 삼킨다(스타일상 느슨함, 인정). **그러나 그 다음 줄이 안전판
  이다**: `sei_stage`로 step2/step3를 실제로 돌린 뒤
  `grep -q "Normal termination" "$w/step2.log" ... || return 1`로 검사한다.
  `.chk`가 없으면 G16의 `NonEq=read`가 읽을 반응장이 없어 **G16 자신이 오류
  종료**하고(`Error termination`), 이 grep이 그 실패를 정확히 잡아 `u27_try`가
  1을 반환 → IEFPCM 폴백 시도 → 그것도 실패하면 `route_accepted: false`로 정직하게
  보고된다. **"조용히 틀린 답"이 아니라 "정직하게 실패"로 귀결된다.** 다만
  `cp` 실패 시점에 바로 `return 1`(명시적 존재 확인)했다면 더 빠르고 명확한
  진단이 됐을 것 — **MINOR 스타일 개선 후보**로만 남긴다(기능적 결함 아님).
- **[확인] 값 자체는 판정에 안 쓰인다**: `lambda_out_hartree_indicative`에
  `_value_caveat`로 "이 값은 루트가 돌았다는 증거일 뿐, 물리적 타당성은 proposer
  몫"이 명시돼 있다 — 값을 실수로 신뢰하게 만들 여지를 스스로 차단했다.

## 판정
**BLOCKER 0건. OK — 지금 사용자에게 보내도 된다.**

이번 라운드는 지난 두 라운드보다 변경 폭이 좁았고(CP2K 제거는 순수 삭제, U-27은
독립적으로 부가된 진단 1건), 직접 실행한 542개 전체 테스트 + U-27 16개 단독
실행 + 코드 추적(RT-1b/U-27 데이터 경로 분리, cp2k 잔존 문자열 4곳 개별 대조)
전부에서 새 BLOCKER를 찾지 못했다. 세 라운드 누적으로 확인된 패턴 — "테스트
통과는 정확성의 증거가 아니다" — 에 대해 이번엔 실제로 **위험해 보였던 지점
(`.chk` 조용한 실패)까지 끝까지 추적해 안전판이 있음을 코드로 확인**했다는 점을
분명히 해 둔다(추측으로 "괜찮을 것 같다"고 넘기지 않았다).

---

## 2026-08-17 — 🔴 직전 판정 보류 통지 수신 (lead 순서 오류)

lead가 **직전 재리뷰 요청을 보류**한다고 알려왔다. coder가 아직 작업 중(③V1 실행이
패키지 밖에서 진행 중)인데 완료 확인 없이 리뷰가 개시됐다는 것이다.

**⟹ 바로 위 항목("최종 재리뷰: CP2K 전면 제거 + U-27 NonEq 스모크", `OK` 판정)은
무효로 간주한다.** 그 판정 자체는 취소하지 않고(과거 기록은 보존한다는 이 문서의
원칙대로) **삭제하지 않되**, 이 메모로 무효화를 명시한다:

- 그때 읽은 코드·실행한 테스트 결과는 **그 시점의 트리에서는 사실**이었으나,
  **그 트리가 인도될 최종 트리라는 보장이 없었다.** 특히 `dist/` 관련 확인(있었다면)은
  전부 무효.
- **재개 신호("패키지 동결" + 해시)를 받기 전까지 아무 것도 하지 않는다.**
  코드 파일을 다시 읽거나 테스트를 다시 돌리지 않는다 — 지금 보는 트리도 최종이
  아닐 수 있으므로 지금 하는 확인은 낭비이거나 오도할 수 있다.
- **재개 시 범위**(lead가 재확인): CP2K 삭제 부작용 / U-27 실패 시 P1b 생존 /
  `.chk` 복사 실패가 조용한가 시끄러운가 / 회귀 테스트가 진짜 버그를 잡는가.
  이번 대기 전 라운드에서 이미 이 네 가지를 전부 확인했었지만, **동결된 트리에서
  처음부터 다시 확인한다** — 이전 확인 결과를 근거로 삼지 않는다.

## 현재 상태: **대기 (idle). "패키지 동결" 통지 수신 시까지 착수하지 않는다.**

---

## 2026-08-17 — 긴급 리뷰: 실클러스터 dry-run 실패 대응 (PBS 거부 4/4 + Gaussian 미탐지) 수정판

대상: `sei_pilot/templates/pbs.sh.tmpl`, `sei_pilot/scheduler.py`(PBS 부분),
`sei_pilot/cli.py`(`--emit-script`, `format_feasibility`), `sei_pilot/envpaths.py`,
`config/sizing.json`, `tests/test_pbs_script_shape.py`
(참조: `01_DECISION_LOG.md` 진행 로그 2026-08-17 하단 6건, `src/HANDOFF_TO_LEAD.md` §20)

🔴 **우리 박스에는 PBS·Gaussian이 없다. 아래 판정은 전부 "생성되는 텍스트의 형태"와
"틀렸을 때 진단 가능한가"에 대한 것이며, PBS가 실제로 수용하는가는 검증 불가능하다.**

### 치명적

- **`cli.py:447` (`SubmissionCheck.to_dict`) — `[확인, 직접 실행]` 거부 메시지가
  여전히 잘린다. coder의 "이제 자르지 않고 접는다"는 주장은 반만 사실이다.**
  `to_dict()`가 `"message": self.message[:400]`로 **400자 하드 컷**을 하고 있고,
  `submission_feasibility()`(`cli.py:286`)가 사전검사 결과를 만들 때 정확히
  `adapter.test_submit(spec).to_dict()`를 거쳐 `format_feasibility()`로 넘긴다 —
  **이것이 실제 파이프라인 경로다.**
  ```
  check = SubmissionCheck('probe_node', False, 'qsub -h + qdel', <535자 메시지>)
  d = check.to_dict()
  len(d['message']) == 400   # 뒤쪽 135자(꼬리, 원인이 있을 수 있는 자리) 소실
  ```
  직접 실행해 확인했다(위 재현 스니펫 그대로 동작). **`tests/test_pbs_script_shape.py`의
  `TestRejectionMessageIsNotTruncated` 3건은 전부 `feas` 딕셔너리를 손으로 만들어
  `format_feasibility()`에 바로 넣는다 — `SubmissionCheck.to_dict()`를 단 한 번도
  통과하지 않는다.** 즉 **실제 실행 경로는 회귀 테스트가 커버하지 않고, 그 경로에
  정확히 예전과 같은 종류의(폭만 66→400로 커진) 절단이 남아 있다.**
  → 이 입력이면 이렇게 틀린다: PBS filter hook의 실제 실패 메시지(특히 Python
  traceback을 포함하는 hook 오류는 흔히 수백~천 자)가 400자를 넘으면, 이번에도
  원인이 잘려나간 뒷부분에 있을 수 있고 우리는 또 "왜 거부됐는지 모르는 채" 사용자
  회신을 기다리게 된다 — **이번 수정 라운드 전체의 존재 이유(왕복 낭비 방지)가
  무너지는 지점.**
  → 이렇게 고쳐라: `to_dict()`의 `[:400]` 슬라이스를 제거하거나(가장 간단),
  최소한 잘렸을 때 `"...[truncated, N chars total]"` 같은 표시를 남겨 **잘렸다는
  사실 자체를 삼키지 않게** 하라. 그리고 `TestRejectionMessageIsNotTruncated`에
  `SubmissionCheck(...).to_dict()`를 실제로 거치는 테스트를 최소 1건 추가하라
  (현재는 이 경로가 테스트에서 원천적으로 빠져 있다).

- **`cli.py:389-391` vs `cli.py:451-458` — `[확인, 직접 실행]` `--emit-script`와
  실제 제출이 "같은 `build_spec()`"을 쓰는 건 맞지만, 그 함수에 넘기는 `common_env`가
  서로 다르다.** `cmd_submit`의 `common_env`는 `SEI_QC_LEVEL`(계산 레벨, `--level`에서
  파생)을 포함하는데, `cmd_emit_script`의 `common_env`는 **`SEI_QC_LEVEL`을 아예
  빼놓는다.** `build_spec` 함수 자체가 같다는 coder의 주장은 사실이지만, **"같은 함수 +
  다른 입력 = 다른 출력"** 이라 실질적으로는 갈라진 경로다. 직접 실행해 diff로 확인:
  ```
  common_env_submit = {..., 'SEI_QC_LEVEL': qc_level_slot('g2')}   # → "1"
  common_env_emit   = {...}                                        # SEI_QC_LEVEL 없음
  spec_submit.env['SEI_QC_LEVEL'] -> '1'
  spec_emit.env.get('SEI_QC_LEVEL') -> None
  diff(제출용 .qsub, --emit-script 출력) :
    -export SEI_QC_LEVEL="1"
  ```
  → 이 입력이면 이렇게 틀린다: 사용자가 `--level g2`로 제출한 뒤(P1이 G-2 레벨로
  돌아감) 뭔가 이상해서 `--emit-script P1 --level g2`로 "우리가 실제로 뭘 보냈는지"
  확인하면, **`export SEI_QC_LEVEL=...` 줄 자체가 없는 스크립트**를 보게 된다.
  `P1.sh:21`이 `${SEI_QC_LEVEL:-2}`로 기본값 2(G-1, 더 비싼 레벨)로 떨어지므로,
  이 출력을 그대로 손으로 재실행하면 **실제 제출된 것과 다른 레벨로 돈다.**
  PBS 헤더 자체(거부 원인 후보)는 `{{ENV_EXPORTS}}`가 지시어 블록보다 훨씬 뒤에
  있어 이번 4/4 거부 진단에는 영향이 없지만, **"제출과 --emit-script가 다르면
  디버깅 자체가 거짓말이 된다"는 것은 handoff §20.1이 스스로 세운 기준이고, 그
  기준을 정확히 어긴 사례를 실행으로 찾았다.** 이 경로를 검사하는 테스트는
  `tests/` 전체에 0건이다(`grep -rl emit_script tests/*.py` 결과 없음).
  → 이렇게 고쳐라: `cmd_emit_script`가 `cmd_submit`과 **동일한 `common_env` 조립
  로직**(최소한 `SEI_QC_LEVEL` 계산)을 공유하도록 하라. 이상적으로는 `common_env`
  조립 자체를 헬퍼 함수 하나로 뽑아 두 커맨드가 호출하게 만들어, "다음에 또
  새 env 키가 추가될 때 한쪽에만 붙는" 재발을 구조적으로 막아라.

### 중대

- **`config/sizing.json:17-18` — `[확인]` `pbs.ncpus_per_node`는 **코드 어디에서도
  읽히지 않는 죽은 설정값**이다. JSON 주석(`_ncpus_note`)은 "여기에 그 값을 넣거나
  `--ncpus-per-node`로 덮어라"고 사용자에게 **둘 다 유효한 방법인 것처럼** 안내하지만,
  `grep -n "sizing.json" sei_pilot/cli.py`로 확인한 실제 소비처는 `usable_cores`와
  `pbs.max_probe_nodes` 둘뿐이다(`cli.py:106, 552`). `ncpus_per_node`를 읽는 코드는
  전무하다(`--ncpus-per-node` CLI 플래그, `args.ncpus_per_node`만 `build_spec`에서
  쓰인다, `cli.py:529-531`). handoff §20.2 표의 "ncpus | config/sizing.json +
  --ncpus-per-node"라는 서술도 **정확하지 않다** — sizing.json 쪽은 아무 효과가 없다.
  → 이 입력이면 이렇게 틀린다: 사이트가 `ncpus`를 제한해서(예: 정본 스크립트처럼
  32) 다시 거부당했을 때, 사용자나 우리가 JSON 주석을 따라 `sizing.json`의
  `pbs.ncpus_per_node`를 32로 고쳐 넣고 재제출하면 **아무 일도 일어나지 않고
  그대로 감지값(예: 64)으로 다시 제출되어 또 거부된다** — 이 프로젝트가 그토록
  경계해 온 "고쳤다고 믿었는데 안 고쳐진 왕복" 패턴 그 자체다.
  → 이렇게 고쳐라: `build_spec`의 `ncpus_override`가 `args.ncpus_per_node`뿐 아니라
  `sizing.json`의 `pbs.ncpus_per_node`도 폴백으로 읽게 하거나, 그게 아니면
  `_ncpus_note`에서 "JSON 값은 현재 사용되지 않는다. `--ncpus-per-node`만 쓰라"고
  정정하라. (같은 파일의 `pbs.emit_stdio_lines`도 동일하게 죽은 키다 — 실제로는
  `JobSpec.emit_stdio_lines` 생성자 기본값 `False`가 전권을 쥔다.)

- **`tests/test_pbs_script_shape.py:10-21` vs `scheduler.py:59-72` (`pbs.sh.tmpl`
  줄 3-5) — `[확인]` 지시어 순서가 자기모순이다.** 테스트 파일이 인용하는 "정본"(사용자가
  실제로 돌려온 스크립트, docstring에 그대로 붙여넣어짐)은 `-V, -q, -N, -A, select,
  walltime` 순인데, `handoff §20.2` 표는 "정본 순서"를 `-V, -N, -q, -A, select,
  walltime`이라 적었고 **실제 구현(`pbs.sh.tmpl` 3~5행: `-N` → `PARTITION_LINE(-q)`
  → `ACCOUNT_LINE(-A)`)도 후자(-N이 -q보다 먼저)를 따른다.** 즉 코드는 handoff
  요약과는 일치하지만, **같은 테스트 파일이 그 위에서 인용한 사용자 원문과는
  다르다.** `test_directive_order_matches_canonical`은 이 `-N`↔`-q` 상대 순서를
  검사하지 않는다(idx(-V)<idx(-q), idx(-q)<idx(select), idx(-A)<idx(select)만 검사).
  → PBS가 `#PBS` 줄들 사이의 상대 순서에 무관하다는 것이 일반적 통념이라 이 자체가
  4/4 거부의 원인일 가능성은 낮다고 본다(`[의심]`, 검증 불가). 그러나 "사용자
  정본과 정확히 같은 형태로 맞췄다"는 이번 수정의 핵심 주장 중 하나가, **같은 문서
  안에서 인용한 원문과 실제로 다르다**는 것은 사실이며 테스트도 이를 가려주지
  못한다. → 원문과 정확히 일치시키거나(안전한 선택), 왜 순서를 바꿨는지 사유를
  남기고 테스트로 그 순서를 명시적으로 고정하라.

### 사소

- `cli.py:326-328` (`_wrap`) — 66자 폭 하드 랩이 단어 중간을 자른다(예:
  `TAIL_END` / `_MARKER`로 분리). 직접 확인했으나 **정보 손실은 없다**(전체가
  두 줄에 걸쳐 보존됨) — 위 400자 절단과는 성격이 다르다. grep으로 원인을 찾는
  사람이 살짝 불편할 뿐이므로 사소로만 남긴다.

### 확인 및 실행으로 검증된 것 (`[확인, 직접 실행]`) — 문제 없음

- `squeeze_directive_blanks` — partition/account/emit_stdio/qos/array/gpus 6개
  선택 지시어의 **64개 조합 전수**를 직접 렌더링해 지시어 블록 안에 빈 줄이 남는
  조합이 0건임을 확인했다.
- `module_block()` — `module load %s 2>/dev/null || echo ...`로 실패해도 `||`가
  있어 잡을 죽이지 않음을 코드로 확인, 회귀 테스트(`test_module_failure_does_not_kill_the_job`)도
  통과.
- 로그인 노드 module 탐지(`envpaths.resolve_qc_via_module`) → `env["qc_module"]` →
  `build_spec`의 `job_modules` → `JobSpec.modules` → 템플릿 `MODULE_LINES`까지
  코드 추적으로 연결을 확인했다. `cmd_submit`과 `cmd_emit_script`가 **같은 `env`
  객체**를 쓰므로 이 경로는 두 커맨드 사이에 갈라지지 않는다(SEI_QC_LEVEL과 달리).
- `probe_queuewait` 노드 상한(`config/sizing.json: pbs.max_probe_nodes = 16`) —
  축소가 발생하면 `store.mark_failed("probe_qw_capped", "node_count_capped", ...)`가
  기록되고, `all_failures()` → `report_mod.build_report(..., failures=...)` 경로로
  최종 회신 JSON에 실제로 실린다(코드 추적 확인). 조용히 축소되지 않는다.
- `--ncpus-per-node` 기본값 — `argparse` 기본 `None`, `sizing.json`의
  `pbs.ncpus_per_node` 기본 `null`. **감지값 고정 동작이 그대로 유지됨**을 확인했다
  (단, 위 "중대" 항목대로 JSON 쪽 오버라이드는 애초에 배선이 안 돼 있다).
- `tests/test_pbs_script_shape.py` 15건 전부 직접 실행 → 통과. 단 위에서 지적한
  대로 **실제 파이프라인 경로(to_dict 절단, emit-script env 분기)를 커버하지
  못하는 얕은 테스트**임을 확인했다 — "통과"가 이번에도 근거가 아니었다.

## 판정
**FIX-THEN-RUN**

실제 `.qsub` 생성(헤더 형태·빈 줄 제거·module 배선·노드 상한 로깅)은 6개 대상 중
직접 실행으로 검증 가능한 범위에서 전부 정상이었고, 이 부분이 실클러스터 제출
자체를 막을 이유는 찾지 못했다. **그러나 이번 라운드가 존재하는 이유 자체인
두 가지 안전장치 — "거부 메시지는 이제 안 잘린다" / "--emit-script는 실제
제출본과 같다" — 가 각각 실제 실행 경로에서 깨져 있음을 직접 실행으로 확인했다.**
둘 다 지금 당장 제출을 막을 결함은 아니지만(전자는 다음 거부가 400자를 넘을 때만,
후자는 `--level`을 비기본값으로 쓸 때만 발현), 다음 왕복(3.5일)에서 정확히 같은
방식으로 다시 눈이 멀 수 있는 자리이므로 **제출 전에 고치기를 권한다.** 사용자가
그 사이 제출을 강행하는 것 자체를 막을 근거는 아니다(BLOCK 아님) — 스크립트
자체는 정상으로 보인다.

---

---

## 2026-08-17 — 재리뷰: §21 대응(4건 수정 + coder 자발 발견 5번째) — **새 치명 1건 발견**

대상: 동일(§21 diff) + `build_common_env`/`submission_feasibility`/`cmd_emit_script`
(참조: `HANDOFF_TO_LEAD.md` §21, `01_DECISION_LOG.md` ADR-041, sha256 cpu `8b231ede06f3`)

### 이전 라운드 4건 — 전부 실행으로 재확인, 정상 (좋은 소식)

- **#1 400자 컷** — `SubmissionCheck.to_dict()`가 이제 자르지 않고 `message_bytes`를
  별도로 낸다(`scheduler.py:445-457`). `TestFullPathFromFeasibilityToScreen`이
  535자(>400) 메시지로 `submission_feasibility()` → `to_dict()` → `format_feasibility()`
  **전 구간**을 실제로 태우는 것을 코드로 확인했고, 직접 재실행해 통과를 확인했다.
- **#2 `--emit-script` vs `--level`** — `build_common_env(args, store, part)`로
  일원화됐고, 소스에서 `build_common_env(args, store, part)` 호출이 정확히 3곳
  (제출/사전검사/emit-script)임을 `inspect.getsource`로 스스로 세는 테스트까지
  붙었다. `--level g2`로 실행 재현: emit-script 출력에 `export SEI_QC_LEVEL="1"` 확인.
- **coder 자발 발견(사전검사가 다른 스크립트를 검사)** — `submission_feasibility()`가
  이제 `build_spec()`을 직접 쓴다(`cli.py:285`). `TestPrecheckUsesTheSameSpecBuilder`류
  테스트가 `sched_mod.JobSpec(` 리터럴이 `submission_feasibility` 소스에 없음을
  확인한다. 소스 직접 읽어 확인: 맞다.
- **#4 죽은 설정 키** — `build_spec()`이 이제 `pbs_cfg.get("ncpus_per_node")` /
  `pbs_cfg.get("emit_stdio_lines")`를 실제로 읽는다. **CLI 플래그 > JSON > 감지값**
  우선순위를 직접 실행으로 3가지 케이스(JSON만/CLI가 JSON을 이김/둘 다 없을 때
  감지값 64 유지) 전부 재현해 확인했다. 기본값(감지값, 보통 64)은 그대로다.
- **#5 지시어 순서** — 템플릿이 `-V, -q, -N, -A, select, walltime`(정본과 동일)로
  바뀌었고, `test_directive_order_matches_canonical`이 이제 6개 지시어의 **전체
  상대순서**를 `sorted(got) == got`로 못박는다. 직접 실행해 통과 확인.

### 🔴🔴 치명 — 새로 발견: **`submission_feasibility()`가 쓰는 파티션과 `--emit-script`가
쓰는 파티션이 여전히 다른 경로에서 나온다. 그리고 실제 PBS 전용 클러스터에서는 그 결과가
`None`이 되어 — 실제 제출본에서 `#PBS -q` 지시어 자체가 통째로 빠질 수 있다.**

**근거 (entry point 수준에서 직접 확인, `[확인, 직접 실행]`)**:
`sysprobe.collect_login()`의 `env["partitions"]`는 **오직 `sinfo`(SLURM 전용 명령)**로만
채워진다(`sysprobe.py:432-433`). `default_partition(env, args)`(`cli.py:238-249`,
`cmd_submit`·`submission_feasibility`가 실제로 쓰는 함수)는 `--partition`/`--queue`가
없으면 이 `env["partitions"]`에서 기본값을 찾는다. **PBS 전용 클러스터에는 `sinfo`가
없다** — 이 프로젝트의 실제 대상 환경이 정확히 그것이다(ADR-004/008, SLURM이 아니라
PBS/Torque). `sinfo`가 없으면 `env["partitions"] = []`이고, `default_partition`은
**`None`을 반환한다.**

반면 `cmd_emit_script`는 여전히(§21에서 안 고쳐짐) 자기만의 폴백을 쓴다:
```python
part = (getattr(args, "queue", None) or args.partition
        or accounts_mod.default_queue())   # config/accounts.json: "normal"
```

**FakeShell로 `sinfo`는 없고 `qsub`/`qstat`/`pbsnodes`는 있는 실제 PBS 환경을 흉내 내
두 실제 진입점 함수(`cmd_preflight`→`submission_feasibility`, `cmd_emit_script`)를
직접 호출해 대조했다** (내부 함수를 손으로 짜맞추지 않음 — ADR-041 §3 규율 그대로):
```
[cmd_preflight] submission_feasibility()의 partition_used: None
[cmd_emit_script] 실제 출력:
  #PBS -q normal
  ...
```
`partition=None`이 `build_spec`→`JobSpec.partition`→`PbsAdapter.write_script`로
흘러가면 `if spec.partition:`이 거짓이라 `PARTITION_LINE`이 빈 문자열로 남고,
**`#PBS -q` 줄 자체가 스크립트에서 사라진다**(직접 렌더링해 확인 — `#PBS -q` 문자열이
결과에 0회 등장).

**⟹ 이 입력이면 이렇게 틀린다**: `./run.sh`(기본 진입점, `--partition`/`--queue`
없이 호출)로 실제 제출하면, **사용자의 작동하는 정본 스크립트에는 있는 `#PBS -q normal`이
우리가 보내는 실제 `.qsub`에는 아예 없다.** 반면 `./run.sh --emit-script <항목>`으로
"우리가 뭘 보내는지" 확인하면 **`#PBS -q normal`이 버젓이 보인다** — 실제로는 없는데
있다고 보여주는, **§20.1이 스스로 "최악의 형태"라 부른 바로 그 실패**가 지금 이
수정판에도 남아 있다.

**왜 이게 이번 라운드에서 가장 중요할 수 있는가**: lead가 데이터에서 찾은 "거부된 4건이
전부 `-A etc`"라는 패턴은 `-A`뿐 아니라 **"probe 계열 진단 잡은 대개 `--queue`/
`--partition`을 명시적으로 안 준다"는 사실과도 완전히 들어맞는다** — 즉 그 4건은
`-A etc`인 동시에 `-q` 자체가 빠져 있었을 가능성이 있다. **두 가설(계정값 / 큐 누락)이
지금까지 한 번도 분리되지 않았다.** 헤더 빈 줄 제거·지시어 순서 교정 등 지난 두 라운드의
수정이 전부 **`-q`가 있다고 가정한 스크립트** 위에서 이루어졌다면, 그 수정들의 유효성
자체가 재검토 대상이 된다. (이것 역시 `[의심]`이다 — 실제로 4건이 `-q` 없이 나갔는지는
그 잡들의 원본 스크립트를 봐야 확정된다. 그러나 **코드가 그럴 수 있다는 것은 확인된
사실이다.**)

**왜 지금까지의 테스트가 이걸 놓쳤는가 (ADR-041의 네 번째 반복)**: §21에서 추가된
`TestEmitScriptIsByteIdenticalToSubmission._scripts()`(`test_pbs_script_shape.py:392-421`)는
"제출본 ≡ emit 출력"을 검증한다고 주장하지만, **`for _ in range(2): build_spec(..., "normal", ...)`
로 같은 리터럴 `"normal"`을 두 번 하드코딩해 넣고 같은 함수를 두 번 호출할 뿐이다.**
`default_partition()`도, `cmd_emit_script`의 실제 폴백 로직도 이 테스트 경로에
**한 번도 등장하지 않는다.** ADR-041이 세 번째 반복까지 잡아낸 바로 그 패턴("부품은
같은데 조립선의 한 단계가 빠졌다")이 **그 규약을 명문화한 바로 다음 라운드에 네 번째로
재발했다.** 구조적 원인도 짚어둔다: **`cmd_emit_script(args)`는 `cmd_preflight`/
`cmd_submit`과 달리 `shell`/`store`/`env` 인자를 주입받지 못하고 내부에서 `Shell()`을
직접 생성한다**(`cli.py:367`). 그래서 FakeShell로 이 진입점을 정상적으로 테스트할 수
없고(모듈 전역 `cli.Shell`을 몽키패치해야만 가능 — 실제로 그렇게 해서 이번에 확인했다),
결과적으로 "진입점에서 테스트하라"는 새 규약을 **지키고 싶어도 지킬 수 없는 구조**였다.

→ **이렇게 고쳐라**:
1. `default_partition(env, args)`와 `cmd_emit_script`의 파티션 결정 로직을 **하나로
   합쳐라**(가장 간단: `cmd_emit_script`가 `default_partition(env, args)`를 그대로
   쓰게 하라). 이번에도 "같은 함수를 쓴다"가 아니라 **호출부가 실제로 하나인지** 재확인하라.
2. `default_partition`이 `None`을 반환하는 상황 자체를 없애라 — 최소한 PBS에서는
   `accounts_mod.default_queue()`를 최종 폴백으로 두거나, `None`이면 사전검사·제출
   단계에서 **경고를 크게 띄워라**(현재는 조용히 `-q` 없는 스크립트가 나간다 — 이
   프로젝트가 가장 경계하는 "조용히 틀림"의 정석적인 사례다).
3. `cmd_emit_script(args)`에 `shell=None, store=None, env=None` 주입 인자를 추가해
   `cmd_preflight`/`cmd_submit`과 같은 방식으로 테스트 가능하게 만들어라. 그 뒤
   `TestEmitScriptIsByteIdenticalToSubmission`을 **진짜 진입점 호출**(FakeShell 주입)로
   다시 짜라 — 지금처럼 파라미터를 손으로 맞춘 내부 함수 호출 두 번으로는 이 라운드가
   놓친 것과 같은 종류의 결함을 구조적으로 못 잡는다.
4. 사용자에게 회신 요청 시, 계정(`-A etc` vs `-A vasp`) 비교와 **함께** 거부된 4건의
   원본 스크립트에 `#PBS -q` 줄이 있었는지도 물어봐 달라고 lead에게 요청한다(critic
   범위 밖이므로 요청만 함).

### 계정(`-A`) 경로 — lead 요청대로 별도 확인, 문제 없음
`resolve_account(args, env, verbose=...)`가 세 진입점(`cmd_submit`/
`submission_feasibility`/`cmd_emit_script`) 모두에서 동일하게 호출되고, `build_spec`의
`account=(entry.get("account") or getattr(args, "_resolved_account", None))`도 단일
경로다. 실제 entry-point 호출로 대조한 두 스크립트 모두 `#PBS -A etc`로 일치함을
확인했다(위 재현 로그 참조). **`-A`는 갈라지지 않는다.**

## 판정
**BLOCK** — 단 `submit` 경로에 한정한다.

이유: 이번에 발견한 결함은 (a) 실제 대상 환경(PBS 전용, `sinfo` 없음)에서 (b) 사용자가
그대로 쓰는 기본 진입점(`./run.sh`, 옵션 없이)에서 (c) **정본에 있는 `#PBS -q` 지시어를
조용히 빠뜨릴 수 있고**, (d) 그 사실을 **우리 자신의 진단 도구(`--emit-script`)조차
숨긴다** — 이는 지난 라운드에 고쳤다고 보고한 바로 그 실패 유형(디버깅이 거짓말이 되는
것)의 재발이며, 동시에 지금까지의 4/4 거부 원인 분석(빈 줄, `-A` 값)이 **분리되지 않은
두 번째 변수(`-q` 누락) 위에서 이루어졌을 가능성**을 새로 열었다. 이 상태로 다시 제출하면
또 한 번의 맹목적 3.5일 왕복을 태울 위험이 실질적이다.
단, lead가 알려준 대로 **현재 진행 중인 계정 진단은 우리 패키지를 거치지 않는 수동
경로**이므로 이 BLOCK이 그 진단을 막지는 않는다 — 그 경로는 이 결함과 무관하다.

---

---

## 2026-08-17 — 재재리뷰: §23 `#PBS -q` BLOCK 대응 — sha256 cpu `acd51c64359b`

대상: `resolve_partition`/`default_partition`/`partition_warning`(신설),
`cmd_emit_script`(주입 가능화), `TestEmitScriptIsByteIdenticalToSubmission`(재작성),
`config/accounts.json`, `config/sizing.json` (동결 확인)

### 1. `-q` 가 실제 제출 경로에 나오는가 — `[확인, 직접 실행]` **5개 조합 전수, 정상**

FakeShell을 실제 `cmd_submit`(→`default_partition`)과 실제 `cmd_emit_script`
**두 진입점 모두에 직접 주입**해(손으로 함수 짜맞추지 않음) 아래 5개 조합에서
`#PBS -q` 줄과 그 값을 대조했다:

| 조합 | submit 경로 | emit-script 경로 | 일치 |
|---|---|---|---|
| 옵션 없음, PBS 전용(`sinfo` 없음) | `#PBS -q normal` | `#PBS -q normal` | ✅ |
| `--queue myq` | `#PBS -q myq` | `#PBS -q myq` | ✅ |
| `--partition mypart` | `#PBS -q mypart` | `#PBS -q mypart` | ✅ |
| `sinfo` 있음, 기본 파티션 있음 | `#PBS -q cpu` | `#PBS -q cpu` | ✅ |
| `sinfo` 있음, 기본 파티션 없음(첫 항목) | `#PBS -q gpuq` | `#PBS -q gpuq` | ✅ |

가장 중요한 첫 행(옵션 없이 기본 `./run.sh` — 실제 PBS 클러스터의 정상적인 사용 형태)에서
더 이상 `-q`가 빠지지 않는다. **`config/accounts.json`의 `queue_default`("normal",
사용자 확인값)로 정확히 떨어진다.**

### 2. 세 경로(제출·사전검사·emit) 동일성 — 항등식으로 되돌아가지 않았다 `[확인]`

`TestEmitScriptIsByteIdenticalToSubmission`을 코드로 직접 읽었다. 이전 판의 결함
(`_scripts()`가 `"normal"`을 두 "경로" 모두에 하드코딩 — 실질적으로 같은 함수를 같은
인자로 두 번 부른 항등식)을 테스트 자신의 docstring이 자백하고 있고, 새 판은:
- `args`를 **`cli.build_parser().parse_args(argv)`** (진짜 argparse)로 만든다.
- **`cli.cmd_emit_script(args, shell=FakeShell(), store=..., env=...)`** /
  **`cli.cmd_submit(args, shell=FakeShell(), store=..., env=...)`** — **진짜 진입점**을
  직접 호출한다(더는 내부 함수를 손으로 짜맞추지 않는다).
- 픽스처 `ENV`가 `partitions: []`로 명시돼 있고, `test_fixture_really_has_no_sinfo_partitions`가
  이 픽스처 자체가 "PBS 현실"을 재현하는지 별도로 지킨다(픽스처 드리프트 방지).
직접 실행해 7건 전부 통과 확인했다.

### 3. 경고 경로 — `[확인, 직접 실행]` **정상, 단 구현이 이원화돼 있다**

큐를 config 폴백까지 실패시켜(강제로 `accounts_mod.default_queue()`가 `None`을 돌려주게
만듦) `submission_feasibility()` → `format_feasibility()`를 직접 실행했다:
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 🔴 큐(파티션)를 정하지 못했습니다 — 제출 스크립트에 `-q` 가 없습니다.
!   큐 지정을 요구하는 사이트에서는 **전 항목이 거부**됩니다.
!   → ./run.sh --queue <큐이름>
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```
**조용히 넘어가지 않는다.** 다만 이 경고가 실제로 화면에 뜨는 코드는
`format_feasibility()`에 **인라인으로 따로** 구현돼 있고(`cli.py:353-359`), lead가
언급한 신설 함수 `partition_warning()`(`cli.py:272-283`)은 — 거의 동일한 문구를
만들지만 — **소스 전체에서 정의된 곳 말고는 한 번도 호출되지 않는 죽은 함수다**
(`grep -rn "partition_warning" src/ tests/` → 정의 1건 외 0건). 지금 당장 위험하지는
않다(실제로 화면에 뜨는 것은 인라인 버전이고, 그게 작동한다는 것을 확인했다). 그러나
이건 이 프로젝트가 `envpaths.py` 주석에서 스스로 "같은 유형 5번째"라 부른 바로 그
패턴("같은 진실이 두 곳에")의 재발이다 — **나중에 누군가 `partition_warning()`을
고치면 아무 일도 안 일어난다.** → 죽은 함수를 지우거나, `format_feasibility()`의
인라인 블록을 `partition_warning()` 호출로 교체하라(둘 중 하나로 통일).

추가로, `--no-precheck`가 켜지면 `submission_feasibility()`가 `checked=False`로 조기
반환해 이 경고 자체가 안 뜬다(큐가 실제로 못 정해졌어도). 다만 `--no-precheck`
자체의 경고 문구("계정·큐 문제가 있으면 실제 제출에서야 드러난다")가 이미 이 상황을
포괄적으로 고지하고 있어 **숨겨진 공백은 아니다** — 사소로만 남긴다.

### 4. `-A` 매핑 / `ncpus` 64 기본값 — `[확인]` **동결 그대로**
`config/accounts.json`: `probe`/`xtb`→`etc`, `gaussian`→`gaussian`, `vasp`→`vasp`,
`queue_default`→`normal` — 전부 이전 라운드와 동일. `config/sizing.json`의
`pbs.ncpus_per_node`는 여전히 `null`(감지값 사용, 보통 64). 세 진입점 모두
`resolve_account()` 단일 소스인 것도 재확인. **손대지 않았다는 lead 지시가 지켜졌다.**

### 5. 🔴 lead 요청 — "되돌리면 깨지는가" 직접 검증 + "같은 유형이 다른 곳에 없는가" 수색

**되돌리기 실험 (`[확인, 직접 실행]`, 파일은 건드리지 않고 메모리에서만 함수를
예전 동작으로 교체)**: `resolve_partition`을 config 폴백이 없던 예전 형태로 되돌려
`TestEmitScriptIsByteIdenticalToSubmission` 7건을 재실행했다. **`test_queue_directive_is_present_in_the_submitted_script`,
`test_queue_directive_is_present_in_the_emitted_script`** 정확히 2건이 즉시
실패했다(`assertTrue(...#PBS -q...)`가 `[-V, -N, -A, -l select, -l walltime]`을 보여주며
깨짐). 나머지 5건(agree/identical 등)은 두 경로가 "똑같이 틀려서" 여전히 통과했다 —
**이것도 정상이다**(동일성 검사와 정확성 검사는 서로 다른 축이라는 뜻). coder가 보고한
숫자(3건)와 정확히 같지는 않지만(내 되돌리기 범위가 더 넓어서 — `resolve_partition`
자체를 되돌렸다), **핵심 주장("회귀 테스트가 장식이 아니라 실제로 잡는다")은 내
독립적인 방법으로도 동일하게 확인됐다.**

🔴🔴 **"같은 유형이 다른 곳에도 없는지 훑어봐라" — 있었다. 바로 그 파일에.**
`tests/test_pbs_script_shape.py`에 **`class TestFullPathFromFeasibilityToScreen`이
두 번 정의돼 있다**(301행, 530행 — 내용은 바이트 단위로 동일). Python은 모듈 최상위에서
같은 이름의 클래스를 다시 정의하면 **뒤의 것이 앞의 것을 조용히 덮어쓴다.**
`python3 -m unittest test_pbs_script_shape -v`로 직접 실행해 확인: **총 35건만 수집되고
실행된다**(두 클래스의 메서드 이름이 완전히 같아 8건이 아니라 4건만 살아남음).
`ast`로 `tests/*.py` 전체(클래스·최상위 함수)를 스캔해 이 파일 외에는 중복이 없음도
확인했다. **다행히 두 정의가 내용까지 동일해 지금 당장 커버리지 손실은 없다** — 그러나
이건 정확히 coder가 이번 라운드에서 자기 발견으로 보고한 그 사고("새 클래스가 기존
클래스와 같은 이름으로 낡은 정의에 덮였다")의 **잔해가 정리되지 않고 그대로 파일에
남아 있는 것**이다. 다음에 누가 둘 중 하나만 고치면 그 즉시 예전과 똑같은 사고가
재발한다. → 중복 클래스 정의 하나를 지워라(둘이 동일하므로 어느 쪽을 지워도 무방).

## 판정
**FIX-THEN-RUN**

`-q` 누락이라는 이번 라운드의 핵심 결함은 **entry-point 수준에서 5개 조합 전수 검증 +
독립적인 되돌리기 실험**으로 실제로 고쳐졌음을 확인했다. **submit을 막을 이유는 이제
없다** — 지난 재리뷰의 BLOCK 근거는 해소됐다. 다만 이번 라운드에서 새로 찾은 두 가지
(죽은 `partition_warning()` 함수, 중복 정의된 `TestFullPathFromFeasibilityToScreen`
클래스)는 **지금 당장 결과를 틀리게 만들지는 않지만, 둘 다 이 프로젝트가 이미 다섯 번
넘게 겪은 것과 정확히 같은 실패 유형의 잔해**이므로 제출 전에 치우고 가는 것을 권한다.
사용자가 지금 막혀 있지 않다는 lead의 확인대로, 서두를 이유는 없다.

---

---

## 2026-08-17 — 최종 확인: §24 잔해 정리 + 구조적 중복가드 — sha256 cpu `e4b0504cd0f8`

대상: `units.py`(`core_hours` 중복 의혹), `plan.py`(우회 계산 여부),
`TestNoDuplicateTestClassNames`(신설 가드), `cli.py`(`partition_warning_lines`)

### 🔴🔴 최우선 — `units.py`의 `core_hours` 중복: **lead의 프레이밍을 정정한다**

**결론부터**: 현재까지 확보 가능한 모든 증거로 볼 때 이것은 **제품 코드에 실제로 살아
있던 사고가 아니라, coder가 신설 가드를 검증하려고 의도적으로 만든 양성 대조(positive
control) 표본이었을 가능성이 매우 높다.** `[확인]`/`[의심]`을 아래에 정확히 구분해 적는다.

`[확인, 직접 실행]`:
- 현재 `units.py`에는 `core_hours(n_cores, wall_seconds)` 정의가 **정확히 1개**뿐이다
  (`grep -n "^def core_hours("` → 67행 1건. 이전의 느슨한 grep이 `core_hours_to_node_hours`를
  잘못 집계해 2건으로 보였을 뿐이었다 — 내 실수를 스스로 잡았다).
- 공식이 수치적으로 옳다: `core_hours(64,3600)=64.0`, `core_hours(32,7200)=64.0`,
  `node_hours`↔`core_hours` 왕복 변환이 정확히 원상복귀된다(64.0→2.0 node-h→64.0 core-h).
- `S_TO_H = 1/3600`, `H_TO_S = 3600` 상호 역수 확인.

`[의심 — 그러나 근거 있음]` 중복이 "실제 사고"가 아니라 "의도된 시험"이었다는 판단의 근거:
1. coder의 §24.3 원문이 이 사례를 **"양성 대조로 셋 다 실제로 잡는 것을 확인했다"**는
   문장 아래, `tests/`에서 만든 **다른 두 개의 명백히 의도적인 표본**(클래스 중복,
   메서드 중복)과 **같은 목록에 나란히** 놓았다. `sei_pilot/`(제품 코드) 쪽 표본이
   하나는 있어야 `test_scan_covers_both_trees`의 "두 트리 다 덮는다"는 주장이 실증되므로,
   `units.py`가 그 역할로 선택됐을 개연성이 높다.
2. 만약 이것이 **진짜로 우연히 발견된 사고**였다면, 이번 세션 내내 coder가 보여 온
   습관(예: `-q` 누락, `SEI_QC_LEVEL` 누락 때 "이전 값 vs 이후 값"을 정확히 대조해
   보고)에 비춰 볼 때 **"두 정의가 어떻게 달랐는지"를 반드시 함께 적었을 것**이다.
   §24 어디에도 그 비교가 없다.
3. `core_hours`가 **정말로 두 개의 서로 다른 정의**로 오랫동안 존재했다면, `import`
   시점에 뒤 정의가 앞을 덮으므로 **한쪽 정의는 이번 세션 이전부터 한 번도 실행된 적이
   없었다는 뜻**이 되고, 그 경우 지금 남은 단 하나의 정의(옳음을 확인함)가 애초에
   **줄곧 쓰이고 있던 그 정의**다 — 즉 중복이 있었더라도 **살아 있던 쪽은 지금 보는
   이 옳은 공식**이었을 것이므로, 과거 core-h 숫자에 영향이 없다는 결론은 이 경로로도 같다.

**남는 것**: 버전 관리(git)가 없어 "그 순간 실제로 트래킹되던 파일에 두 정의가 동시에
존재했는지, 존재했다면 그 창 동안 tarball이 빌드됐는지"는 **나로서는 포렌식하게 증명할
수 없다.** 이것은 coder에게 직접, 구체적으로 물어야 답이 나온다(추측 금지 원칙에 따라
내가 대신 단정하지 않는다): *"양성 대조 때 `units.py` 실제 파일을 일시적으로 편집했는가,
아니면 스크래치 사본/문자열로만 시험했는가? 실제 파일을 편집했다면 그 상태로 빌드/스탬프가
찍힌 적이 있는가?"*

**⟹ lead의 "네가 시킨 중복 스캔이 제품 코드에서 진짜를 찾았다"는 표현은 현재까지의
증거로는 과장이다.** 값에 영향이 있었다는 근거는 없고, 오히려 반대 방향의 근거(위 1~3)가
있다. 다만 100% 반증은 VCS 부재로 불가능하므로 위 한 문장짜리 확인 질문으로 닫기를 권한다.

### 🔴 새로 발견 — lead 질문 #3("우회 계산")에 대한 답: **있다, `plan.py`에**

`[확인, 직접 실행]` `units.py`의 주석("이 정의를 다른 데서 다시 쓰지 마라")에도 불구하고,
**이 파일럿의 실제 core-h 예약·가드 판정 값을 만드는 두 곳이 `units.core_hours()`를
전혀 부르지 않고 자체 산술을 쓴다**:

- `plan.py:259-272` `size_job()` — `reserved = total_cores * wall * links` (일반 항목 전부)
- `plan.py:322-329` array 항목 특례 — `reserved = round(n_tasks * 1 * wall, 2)`

이 두 값은 그대로 `guard.reserve(item.key, core_hours=reserved, ...)`로 들어가
**5,000 core-h 하드가드 판정과 사용자에게 보이는 "예약 core-h" 숫자 전부의 근원**이 된다
(반면 `budget.py`의 `record_measured()`, 즉 **사후 실측** 경로는 정확히 `units.core_hours()`를
부른다 — 계획값과 실측값이 서로 다른 경로로 계산되고 있다는 뜻이다).

직접 대조해 **현재는 수치가 일치함을 확인했다**(`size_job` 단일 링크 500.0=500.0,
63링크 체인 1008.0=1008.0, array 200태스크 5.0=5.0 — 전부 `units.core_hours()`로 계산한
값과 소수점까지 일치). **⟹ 지금 당장 core-h 숫자가 틀렸다는 증거는 없다.** 그러나
이 프로젝트가 여러 번 겪은 정확히 그 패턴("같은 진실이 두 곳에", 이번엔 "계획값과
실측값이 서로 다른 공식")이 형태로는 이미 존재한다 — `S_TO_H`가 언젠가 바뀌거나(예:
duty-cycle 보정 추가) `core_hours()`에 로직이 추가되면 `plan.py`의 두 자리는 **조용히
따라가지 못한다.** → `size_job()`과 array 특례가 `units.core_hours()`/
`node_hours_to_core_hours()`를 호출하도록 바꿀 것을 권한다.

### 잔해 ① (중복 클래스) — `[확인, 직접 실행]` 제거됨
`ast`로 재스캔: `test_pbs_script_shape.py`에 중복 클래스 0건. 전체 스위트
`python3 -m unittest discover` **585 tests OK (skipped 8)** 재실행해 확인. 해당 파일
단독 실행도 35→**39건**으로 정상 증가(가려졌던 4건 + 신설 가드 4건).

### 잔해 ② (partition 경고 이원화) — `[확인]` 하나로 통합됨
`def partition_warning_lines()` 단 1개만 존재하고(`grep`으로 확인), `format_feasibility()`가
`L.extend(partition_warning_lines())`로 그것만 호출한다. 남은 문구는 `-q 가 없습니다`
쪽이다. 🔴 **이건 coder의 주장을 그대로 받은 게 아니라, 지난 재리뷰에서 내가 직접
`format_feasibility()`를 실행해 화면에 찍힌 텍스트를 캡처했을 때 이미 `-q 가 없습니다`가
나왔던 것과 정확히 일치한다** — 즉 "실제로 사용자에게 보이던 쪽이 어느 것인가"라는
lead의 질문에 **내 이전 라운드의 독립적인 실측**으로 답할 수 있다: 맞다, 살아 있던
인라인 쪽이었고 그게 지금 유일하게 남은 쪽이다.

### 가드 자체의 자기지시적 맹점 — `[확인, 직접 실행, 파일 미변경]` 살아남는다
lead가 지목한 시나리오(가드 클래스 자신을 중복시키면 가드가 사라지는가)를 **스크래치
메모리 사본**(실제 파일은 건드리지 않음)으로 직접 재현했다: `test_pbs_script_shape.py`의
텍스트를 읽어 `TestNoDuplicateTestClassNames` 블록을 통째로 한 번 더 이어붙인 뒤,
가드와 동일한 AST 스캔 로직을 그 문자열에 그대로 돌렸다. **`TestNoDuplicateTestClassNames`
자신이 중복 클래스로 정확히 검출됐다.** 이유: 가드는 **파일의 원문 텍스트를 `ast.parse`로
정적 분석**하지, 파이썬 런타임에 임포트된 객체(어느 한쪽이 이미 조용히 덮인 상태)를
보지 않는다. **런타임 도입부에서 하나가 사라지는 것과, 소스 텍스트 안에 두 정의가 있다는
사실은 서로 다른 층이라 가드가 자기 자신의 중복에도 눈멀지 않는다.** coder가 처음에
"가드가 사라졌다"고 밟은 실패는(별도 확인은 못 했으나 정황상) 아마 다른 방식(런타임
기반 카운팅 등)으로 첫 시도를 했을 때의 일이었을 것이고, 지금 남은 구현은 그 함정을
구조적으로 피해 간다.

### `-A` / `ncpus` 64 / V1b — `[확인]` 동결 유지
`config/accounts.json`(`queue_default: normal`, `probe/xtb→etc`, `gaussian→gaussian`,
`vasp→vasp`) · `config/sizing.json`(`pbs.ncpus_per_node: null`) 전부 이전 라운드와
바이트 단위로 동일. V1b 관련 파일은 이번 diff 범위에 없다(안 건드림 확인).

## 판정
**FIX-THEN-RUN**

제출을 막을 근거는 없다 — `-q`/동일성/경고/가드 자기지시성 등 이번 대상의 핵심 항목은
전부 직접 실행으로 재확인했고, lead가 가장 걱정한 "core-h 값이 실제로 바뀌었는가"에도
**바뀌었다는 증거를 찾지 못했다**(오히려 반대 방향 정황이 있다). 다만 두 가지는 제출
전에 마저 닫기를 권한다: ① `plan.py`의 core-h 우회 계산 2곳을 `units.py` 호출로
바꿀 것(지금은 우연히 일치하지만 구조적으로는 정확히 이 프로젝트가 반복해서 데인
패턴이다) ② coder에게 `units.py` 양성 대조가 실제 트래킹 파일을 일시 편집한 것이었는지
스크래치본이었는지 한 줄로 확인해 이번 항목을 완전히 닫을 것. 둘 다 사용자 제출을
지연시킬 이유는 아니라고 본다.

---

### 후기 — lead의 자진 정정 수신

lead가 "units.py core_hours 중복 = 제품 코드의 실제 결함"이라는 자신의 프레이밍을
**자진 철회**했다(§24.3의 세 줄이 발견 목록이 아니라 coder가 스캐너를 시험하려 주입한
양성 대조군 목록이었다는 것을 재확인). 이 문서의 바로 위 항목에서 **critic도 독립적으로
동일한 결론(양성 대조일 가능성이 높다, 값 영향 없음)에 이미 도달해 lead에게 전달했었다**
— 이번엔 서로 다른 방향에서 같은 결론에 도달했으므로 재조사는 불필요하다. 나머지 확인
항목(②~⑦)은 이미 위 라운드에서 전부 직접 실행으로 확인 완료했다.

---

---

## 2026-08-17 — lead 가설 검증: `probe_queuewait` 사전검사 ≠ 실제 제출

lead가 판단을 혼자 확정하지 않겠다며 검증을 요청함(직전 5회 자기 오판 인지). entry-point
레벨(FakeShell 주입, `cmd_preflight`/`cmd_submit` 실제 호출)로 직접 검증했다.

### 1. 사전검사가 정말 `select=85`를 만드는가 — `[확인, 직접 실행]` **그렇다, 그리고 더 나쁘다**

`cmd_preflight`가 실제로 만드는 `check_probe_queuewait` 사전검사 스펙을 어댑터에서
가로채 직접 찍었다:
```
precheck: key=check_probe_queuewait  nodes=85  cores_per_node=32
```
lead의 가설이 맞다. **그리고 `cores_per_node`도 갈린다** — 아래 참조.

### 2. `cap=16` 적용 후 실제 제출과의 차이 — `[확인, 직접 실행]` **수치로**

같은 방식으로 `cmd_submit`이 실제로 제출하는 스펙을 가로챘다:
```
submit: probe_qw_n1   nodes=1   cores_per_node=1
submit: probe_qw_n4   nodes=4   cores_per_node=1
submit: probe_qw_n16  nodes=16  cores_per_node=1
        (64는 max_probe_nodes=16 에 걸려 생략됨 — 화면에도 남음)
```
| | 사전검사가 시험하는 것 | 실제로 제출되는 것 |
|---|---|---|
| 잡 개수 | 1개 | 3개(64는 생략) |
| 노드 수 | **85** | 1 / 4 / 16 |
| 노드당 코어 | **32** | **1** |
| 총 요청 코어 | **2,720** | 1+4+16 = **21** |

**사전검사가 시험하는 형태(`select=85:ncpus=32:mpiprocs=32`)는 실제 운영에서
단 한 번도 제출되지 않는다.** 반대로 **실제로 제출되는 3개 잡 형태는 사전검사가
단 하나도 시험하지 않는다.** 노드 수도 코어 수도 둘 다 갈린다 — lead가 지목한 것보다
divergence가 더 크다.

🔴 **왜 특히 나쁜가**: `config/sizing.json`의 `_max_probe_note`가 스스로 밝히듯
**"probe_queuewait가 85노드를 요청해 거부됐다"** 는 것이 `max_probe_nodes=16` 상한을
만든 실측 사건이다. 즉 **사전검사가 지금, 과거에 실제로 거부당했던 바로 그 형태(85노드
단일 요청)를 다시 그대로 재현해서 시험하고 있다.** 큐 상한을 넘는 사이트라면 사전검사가
`probe_queuewait`를 "거부됨"으로 보고할 것이고, 사용자는 **실제로는 문제없을 3개 잡을
포함해 전체를 의심하게 된다** — 정확히 lead가 우려한 시나리오다. 반대 방향(사전검사는
통과하는데 이 시험은 실제 제출본과 무관하므로 정보가 0)도 마찬가지로 나쁘다 — **이
항목의 사전검사는 현재 어느 쪽으로 나와도 의미가 없다.**

### 3. 다른 항목에도 같은 유형이 있는가 — `[확인, 직접 실행]` **없다. `probe_queuewait` 유일**

`submit_entry()` 전체를 읽어 특례 분기가 `if key == "probe_queuewait":` **단 한 곳**뿐임을
확인했다(`grep -n "if key ==" cli.py` → 1건). 의심했던 array 항목(`probe_throughput`,
`-J 1-200`)도 직접 대조했다:
```
probe_throughput  precheck: nodes=1 array=(1,200) cores_per_node=1
probe_throughput  submit  : nodes=1 array=(1,200) cores_per_node=1   ← 완전 일치
P3(일반 항목)      precheck: nodes=1 cores_per_node=32
P3(일반 항목)      submit  : nodes=1 cores_per_node=32               ← 완전 일치
```
`probe_throughput`은 PBS job array(`-J`)로 **하나의 qsub 호출**로 나가므로 애초에
분해되지 않는다 — `probe_queuewait`처럼 "합계 노드 수를 여러 개의 진짜 잡으로 쪼개는"
패턴은 이 파일럿 전체에서 이 항목 하나뿐이다. **"같은 유형이 다른 데도 있는가"에 대한
답은 없다, 이다.**

### 4. 고치는 방향 — 의견을 요청받았으므로 판단을 낸다

두 선택지 중, **"사전검사도 `submit_entry`와 같은 분해를 재사용하되, 대표로 가장 큰
실제 잡(현재 상한 반영 16노드)만 시험"** 을 권한다. 이유:
- 사이트가 잡을 거부하는 축은 대개 **노드 수 상한**이므로, 셋(1/4/16) 중 통과 여부를
  가르는 것은 사실상 가장 큰 것뿐이다. 1·4는 16이 통과하면 거의 항상 통과한다.
- 셋 다 시험하면 PBS의 사전검사는 **부작용이 있는 방식**(`qsub -h`+`qdel`, 이미 문서화된
  한계)이므로 **왕복 부담(held job 3개, 삭제 실패 시 잔류 위험도 3배)** 이 불필요하게 는다.
- 🔴 **반드시 지켜야 할 것**: 대표를 고를 때 **`submit_entry`가 실제로 쓰는 것과 동일한
  분해 함수를 호출**해서 뽑아야 한다(이번 사고가 "같은 계산을 두 곳에 따로 적어서"
  난 것과 같은 유형이므로). `entry["nodes"]=85`를 그대로 쓰거나 사전검사 쪽에 `16`을
  하드코딩하는 방식은 **다음에 `max_probe_nodes`가 바뀌면 또 조용히 갈린다.**
  가장 안전한 형태는 `submit_entry`의 분해 로직 자체를 함수로 뽑아 `submission_feasibility`와
  공유하는 것이다(이번 세션에 `build_common_env`/`build_spec`에서 이미 쓴 것과 같은 패턴).

### lead의 직전 오판(coder에게 보낸 "85가 그대로 나가면 또 거부") — `[확인]` 정정 확인

**맞다, 그 문장은 틀렸다.** 실제 제출 경로는 이미 1/4/16으로 분해·상한 적용돼 있고
(위 §2에서 직접 확인), 85가 그대로 제출되는 경로는 없다. 문제는 **제출이 아니라
사전검사**라는 lead의 자기 정정이 옳다.

## 판정
**FIX-THEN-RUN**

실제 제출(core-h를 태우는 경로)은 정상이므로 지금 제출을 막을 이유는 없다. 그러나
`probe_queuewait`의 사전검사는 **현재 상태로는 없느니만 못하다** — 실제로 나가지 않는
형태(85×32)를 시험하고, 실제로 나가는 형태(1/4/16×1)는 전혀 시험하지 않는다. 다음
사용자 왕복에서 사전검사가 이 항목을 "거부"로 잘못 보고해 불필요한 혼란(다른 3개 정상
잡까지 의심)을 일으킬 실측 위험이 있다(과거에 정확히 이 85노드 형태가 거부된 전례가
있다는 것이 `config/sizing.json` 자체에 기록돼 있다). 제출 전에 고치는 것을 권하되,
사용자가 지금 막혀 있지는 않다.

---

---

## 2026-08-17 — 최종 확인: §25~27 (core-h 일원화 + probe_queuewait 4곳 정합) — sha256 cpu `8050a1d211be`

lead가 "OK면 이 해시로 사용자에게 나간다"고 명시한 최종 게이트. 4개 항목 전부
entry-point 레벨(FakeShell 주입, 진짜 `cmd_preflight`/`cmd_submit` 호출)로 **독립
재현**했다 — coder의 표를 그대로 믿지 않고 내가 직접 다른 방식으로 다시 만들었다.

### 1. 값 변화가 정확한가 — `[확인, 직접 실행]` **정확하다. lead의 564.8도 옳다**

64 core/node를 반환하는 `pbsnodes -a` 응답으로 FakeShell을 구성해 `build_plan()`을
직접 돌렸다:
```
probe_node        nodes=1   reserved=15.0
probe_throughput  nodes=1   reserved=5.0
probe_queuewait   nodes=21  reserved=44.8   note="[64] node 생략(상한 16)"
P3                nodes=1   reserved=500.0
TOTAL = 564.8
```
`21 = 1+4+16`(64는 cap 16에 걸려 제외) 확인. `564.8`은 lead가 언급한 숫자와 **정확히
일치**한다. coder의 §27.3 `"270.0 → 64.8"`과도 모순이 아니다 — 그건 P3를 뺀 프로브
3항목만의 부분합(15+5+44.8=64.8)이었고, 거기에 P3의 500을 더하면 564.8이 나온다.
**lead와 coder의 숫자가 서로 다른 부분집합을 가리켰을 뿐, 실제로는 일치한다** —
모순처럼 보였던 것은 모순이 아니었다.

**③(plan.py core-h 일원화)이 ①(probe_queuewait 실측값 변경)과 섞이지 않았는가**도
직접 재확인했다: 지난 라운드에 감사했던 값(`size_job` 500.0 / 63링크 체인 1008.0 /
array 5.0)을 `core_hours_h` 리팩터 이후 코드로 다시 계산해 **완전히 동일**함을
확인했다(정확한 소수점까지). ③은 경로만 바뀌고 값은 안 바뀐다는 요구가 지켜졌다.

### 2. `units.core_hours_h` — `[확인]` **중복이 아니라 단일 정의 + 단위 래퍼다**

`grep -n "^def core_hours"` 재확인: `core_hours_h(n_cores, wall_hours)` 정의 1개 +
`core_hours(n_cores, wall_seconds)`가 `core_hours_h(n, wall_seconds*S_TO_H)`를
**호출**(위임)하는 래퍼 1개. 직접 실행: `core_hours_h(64,1.0) == core_hours(64,3600)`
= `True`. 이건 같은 파일에 이미 있던 `node_hours_to_core_hours`/`core_hours_to_node_hours`
쌍과 같은 패턴(단일 정의 + 단위 변환)이라 **일관적이다.** coder의 부동소수 왕복 논거는
내 표본에서는 비트까지 동일하게 나와(`44.8`, `44.7552` 등 여러 값에서 시험) 극적으로
입증되진 않았지만, **핵심은 그 논거의 진위가 아니라 결과**다 — `plan.py`의 3개 호출부
(259/312, 365/382, 397/403행)가 지금 실제로 `units.core_hours_h()`를 부르고 있음을
직접 확인했으므로 critic이 요구한 "우회 계산 제거"는 **형식과 무관하게 달성됐다.**
우회를 정당화하는 논리가 아니라 우회 자체가 없어졌다.

### 3. 네 곳이 한 소스에서 나오는가 — `[확인, 직접 실행]` **cap 16/4/1 전수 독립 재현**

coder의 표를 그대로 쓰지 않고 `config.load`를 가로채 cap만 바꿔가며 실제 `cmd_preflight`
(표시+예약+사전검사)와 실제 `cmd_submit --no-precheck`(실제 제출)를 각각 새로 돌려
직접 대조했다:
```
cap=16: 표시=21  예약=44.8   사전검사=(16,1)  실제제출=[n1,n4,n16]  ← precheck는 최대실잡(16)과 일치
cap=4 : 표시=5   예약=10.67  사전검사=(4,1)   실제제출=[n1,n4]      ← precheck는 최대실잡(4)과 일치
cap=1 : 표시=1   예약=2.13   사전검사=(1,1)   실제제출=[n1]         ← precheck는 최대실잡(1)과 일치
```
세 경우 모두 **사전검사 스펙이 정확히 그 cap에서 실제로 제출되는 것 중 가장 큰 잡과
일치**한다. 16을 하드코딩하지 않았다는 coder의 주장이 독립 재현으로 확인됐다.

### 4. 생략 사실이 회신 JSON에 실리는가 — `[확인, 직접 실행]` **실린다**

`cmd_preflight` 실행 후 실제로 디스크에 쓰인 `results/sei_probe_report.cpu.json`을
직접 열어 확인했다(화면 문구가 아니라 파일):
```json
"queue_wait_decomposition": {
  "node_counts_submitted": [1, 4, 16],
  "dropped_by_cap": [64],
  "cap": 16,
  "_reservation_basis": "노드합 21 × 64 core/node × 0.0333 h. ... 코어 단위 과금이면 실제 소비는 이보다 64배 작다."
}
```
engineer가 소비할 그 파일에 축소 사실과 과금 가정(노드 단위 보수적 가정, §27.3에서
lead에게 판단을 미룬 그 항목)까지 명시돼 있다. 화면에만 있고 JSON엔 없는 상황이 아니다.

### 부수 확인 — `[확인]`
- 전체 스위트 재실행: `609 tests OK (skipped 8)`.
- `ast` 전수 재스캔(`tests/` + `sei_pilot/`, 클래스·함수 양쪽): 중복 0건.
- `config/accounts.json`(`queue_default: normal`, 매핑 4종) · `config/sizing.json`
  (`ncpus_per_node: null`, `max_probe_nodes: 16`) — 전부 이전 라운드와 바이트 단위 동일.
  `-A`/`ncpus`/V1b 동결 유지.

## 판정
**OK**

이번 라운드는 이전 다섯 라운드와 달리 **독립 재현에서 결함을 찾지 못했다.** lead가
요청한 4개 항목 전부 entry-point 레벨에서 coder의 주장과 다른 방식으로 다시 만들어
대조했고, 전부 일치했다. 특히 lead와 coder의 숫자가 다르게 보였던 부분(564.8 vs 64.8)도
직접 계산해 "서로 다른 부분집합을 가리켰을 뿐 모순이 아니다"로 해소했다. **이 해시
(`8050a1d211be`)를 인도판으로 승인한다.**

---

## critic3 리뷰 — 2026-08-18 — 재실행 패키지 최종 (§28~§34, 대상 build 당시 sha `4623019f0e11`)

**대상**: coder2 인도판, coder2 지목 4항목(§31 되돌리기 재현 / ADR-048 P6 3중 방어 / §33.1
wall·link 가드 / collect.py 전 함수×payload 필드 대조) + lead 지정 그 외 항목.
**방법**: 전부 `python3 -m unittest`, `bash`, 직접 patch+revert 로 **경로 실행**해 확인했다
(ADR-036/041/043 규율). 클러스터가 없으므로 PBS/G16 자체의 수용 여부는 판정 불가 — 그 영역은
코드 형태·진단 가능성만 확인했다.

## 판정
**FIX-THEN-RUN**

## 치명적

- `sei_pilot/plan.py:resolve_wall_limit()` (698행) + `sei_pilot/cli.py:resolve_partition()`
  (249행) — **[확인, 경로 실행+코드 대조]** §34.3 이 주장하는 "`long` 큐가 있으면 비용 0 으로
  wall 문제가 사라진다"는 **거짓이다.** `resolve_wall_limit()` 은 `qstat -Qf`(인자 없음)로
  **모든 큐**를 읽어 walltime 최장의 사용 가능한 큐를 찾고(`longest_wall_queue`), 그 값을
  `max_wall_h_used`(태스크 wall·링크·천장 산정에 쓰는 값)로 승격시킨다. 그런데 이 함수가
  고른 큐 이름(`queue_selected`)은 **`sei_pilot/*.py` 전체에서 이 한 줄 말고 아무 곳에서도
  읽히지 않는다**(`grep -rn queue_selected` 확인). 실제 제출 스크립트의 `#PBS -q` 는
  `cli.resolve_partition()` 이 별도로 정하는데, 이 함수는 `--partition`/`--queue` 인자 →
  `sinfo`(PBS 에선 항상 빈 목록) → `config/accounts.json` 의 **정적** `queue_default`
  (="normal") 순으로만 본다 — `resolve_wall_limit` 의 결과와 **완전히 무관하다.**
  `tests/test_wall_limit_source.py` 전 케이스가 `env["queue_info"]`(단일 큐) 만 쓰고
  `env["queues"]`(다중 큐)·`-q` 연동은 **한 건도 테스트하지 않는다**(확인).
  → **이 입력이면 이렇게 틀린다**: 실클러스터의 `normal` 큐가 실제로 24 h 이고(ADR-048/049
  가 명시적으로 대비한 시나리오), `long` 같은 더 긴 큐가 실제로 존재한다면 —
  `resolve_wall_limit` 은 `long` 을 찾아 `max_wall_h_used` 를 24 보다 크게 올리고, P1b(22원자,
  예산 3,072)는 링크 분할 없이 통과해 **§R26.4 게이트 (b) 가 조용히 PASS 한다.** 그런데 실제
  제출은 여전히 `-q normal` 로 나간다 — PBS 는 요청 walltime(48 h) 이 `normal` 의 상한(24 h)
  을 넘는 잡을 **`qsub` 시점에 거부**하거나(사이트에 따라) 24 h 에서 wall-kill 한다.
  **§34.5 가 "게이트가 24 h 시나리오에서 제출을 막고 설계대로 동작한다"고 적은 바로 그 안전
  장치가, `long` 큐가 실존하는 순간 무력화된다** — 그리고 그 순간은 이 세션 문서가 "1 순위
  해법"이라 부르며 가장 기대를 걸고 있는 바로 그 상황이다. ADR-048 이 P6 에 대해 쓴 문장이
  그대로 적용된다: *"신뢰받는 안전장치가 실제로는 작동하지 않는 것은 없느니만 못하다."*
  → **고쳐라**: `resolve_wall_limit` 이 스캔한 큐 중 실제로 **선택된 것**(`queue_selected`)을
  `cli.resolve_partition`/`build_spec` 에 실제로 전달해 `-q` 를 거기로 보내거나, 반대로
  `resolve_wall_limit` 이 **`resolve_partition` 이 이미 고른 큐 하나만** 보고 계산하게 해서
  "gate 가 보는 큐"와 "제출이 가는 큐"를 강제로 같게 만들어라. 최소한 회귀 테스트 하나
  (제출 스크립트의 `-q` == `queue_selected`, 또는 `queue_selected`≠기본 큐일 때 gate 가 경고)
  를 추가해야 한다.

- `sei_pilot/collect.py:collect_p5()`(506행) → `criteria/p5.py:normalize_rows()`(39행) —
  **[확인, 직접 실행으로 재현]** P5.sh 가 `p5_results.json` 에 담아 보내는 최상위 필드
  `dual_seed_species` / `seed_pairs` / `_sigma_note` 는 `collect_p5` 가 **`rows` 와
  `n_requested` 만 꺼내고 나머지는 통째로 버린다.** 게다가 `species_rows` 그 자체(정본이라
  주석에 적힌 그 배열)를 만드는 `normalize_rows()` 도 원본 행의 `seed` / `seed_provenance` /
  `qc_code` / `route` / `level_label` / `failure_reason` / `g16_cpu_seconds` 를 **복사하지
  않는다.** 합성 dual-seed 행 2개(같은 id, seed=0/1)를 `evaluate_p5()` 에 직접 넣어 재현:
  ```
  seed 필드가 있는가: False
  ```
  두 행은 `core_hours`/`wall_h`/`scf_cycles_*` 말고는 완전히 동일한 모양으로 나온다.
  → **이 입력이면 이렇게 틀린다**: P5.sh 의 `_sigma_note` 는 정확히 *"같은 id·같은 level 의
  seed 0/1 두 행을 비교하면 σ_protocol 을 낼 수 있다"*고 약속하는데, 받는 쪽이 실제로 받는
  `sei_probe_report.*.json` 에는 (a) 어느 종이 dual-seed 대상이었는지(`dual_seed_species`),
  (b) 짝이 완결됐는지(`seed_pairs`), (c) 개별 행이 seed 0 인지 1 인지가 **전부 없다.**
  dual-seed 종은 core-h 를 2 배 써서 만든 데이터인데 그 데이터로 하려던 유일한 비교
  (perturbation 재현성)가 회신만으로는 **원리적으로 복원 불가능**하다 — 사용자는 회신 JSON
  1개만 보낸다(README, "결과 요약" 절). `failure_reason` 유실도 별도로 심각하다: 미수렴 종의
  **원인**이 최종 리포트에서 사라진다. `tests/test_profiles_merge.py` 는 `species_rows` 의
  개수·`converged` 여부만 검사하고 `seed`/`seed_pairs` 존재를 검사하는 테스트는 **0 건**
  (확인: `grep -n dual_seed\|seed_pairs\|"seed"` 전체 tests/ 대조).
  → 이것이 lead 가 지목한 **"측정해 놓고 안 쓰는 값" 여섯 번째 사례**다(B-3 / 400자 컷 /
  `host` / CREST / P6 오버서브스크립션 다음).
  → **고쳐라**: `normalize_rows` 에 `seed`, `seed_provenance`, `qc_code`, `route`,
  `level_label`, `failure_reason`, `g16_cpu_seconds` 추가, `collect_p5` 가
  `dual_seed_species`/`seed_pairs`/`_sigma_note` 를 결과에 그대로 실어라. 회귀 테스트:
  dual-seed 합성 입력 → 최종 report 에서 seed 쌍을 실제로 식별 가능한지.

## 중대

- `sei_pilot/plan.py:sizing_gates()` 게이트 (a)(536행) — **[확인, 코드 실행으로 재현]**
  ADR-048 이 "3중 방어"라 부르는 것 중 plan-time 게이트는 `entry["cores_per_node"]`
  (=`item.cores_per_task`, override 반영 전)를 보는데, 실제 제출 코어 수는
  `cli.build_spec()`(667행)에서 `--ncpus-per-node`/`config/sizing.json:pbs.ncpus_per_node`
  로 **한 번 더 덮어써진다.** 이 덮어쓰기는 P6 의 세 항목(`P6_t1/t16/t64`)에도 **똑같이,
  차별 없이** 적용된다. 직접 재현(`build_spec` 에 `ncpus_per_node=32` 를 흉내):
  ```
  gate(a) 통과 여부(override 적용 전 plan 기준): True   ← 게이트가 통과로 본다
  P6_t1  실제 제출 ncpus=32   P6_t16 실제 제출 ncpus=32   P6_t64 실제 제출 ncpus=32
  ```
  즉 **`sizing_gates` 게이트 (a) 는 이 경로를 전혀 보지 못한다** — 셋 다 32 로 나가도
  plan-time 검사는 "통과"라고 말한다. 다행히 **런타임 방어(`collect_p6`)는 살아 있다**:
  `declared`(항목 키에서 옴, override 영향 없음)와 `requested`(`SEI_TOTAL_CORES`, override
  반영됨)가 어긋나 셋 다 `[INVALID]` 로 버려진다 — κ 가 틀린 값으로 나가지는 **않는다.**
  그러나 이 경로를 타면 **P6 예산(1,944 core-h) 전체가 헛돈다**는 점, 그리고 §34.2 가 말하는
  "게이트가 제출 전에 막는다"는 이 시나리오에서 **거짓**이라는 점은 남는다.
  🟡 **현재 기본 설정에서는 발동하지 않는다** — `config/sizing.json` 의 `ncpus_per_node`
  는 지금 `null` 이고 `run.sh` 는 기본으로 `--ncpus-per-node` 를 넘기지 않는다. 다만
  `config/sizing.json` 의 주석과 `HANDOFF §0.1` 이 **정확히 이 값을 32 로 바꾸라고 사용자/
  lead 에게 권유**하고 있어(사용자 정본 스크립트가 ncpus=32) 다음 라운드에 이 스위치가
  켜질 개연성이 낮지 않다. → **고쳐라**: gate (a) 가 override 반영 후의 실제 값(즉
  `build_spec` 이 최종적으로 쓸 `cpn`)을 보게 하거나, override 가 P6 처럼 `cores_per_task`
  가 명시된 항목에는 적용되지 않게 막아라.

## 사소

- `dist/sei_pilot_cpu.tar.gz` 가 **재현 불가능하다** — **[확인]** 소스 변경 없이
  `make_package.sh` 를 두 번 돌려 tarball sha256 이 매번 바뀌는 것을 직접 확인했다
  (`7dd91d57cc0c...` → `2b03cbbf0773...`, 둘 다 lead 가 인용한 `4623019f0e11` 과도 다름).
  원인은 `cp -r` 이 mtime 을 보존하지 않아 tar 헤더가 매 빌드 달라지는 것으로 보인다
  (`build_stamp.py` 의 `source_digest`/`per_file` 해시는 내용 기준이라 안정적이다 — 이번
  `check` 는 두 번 다 통과했다). **`인도판 sha256 XXXX` 라는 표현 자체가, 같은 소스로
  재빌드해도 검증 불가능한 식별자**라는 뜻이다. 내용 무결성은 `source_digest`/`per_file`
  로 이미 보장되므로 치명적이진 않지만, HANDOFF·리뷰 메시지 전체가 tarball sha 를 "이
  정확한 빌드"의 증표로 반복 인용하는 관행은 오도 소지가 있다. 회귀는 아니라고 판단해
  사소로 둔다.
- `sei_pilot/collect.py` / `payload/P1.sh:53,63` — **[확인]** `crest_status.json` 의
  `crest_path`(어느 CREST 바이너리를 썼는지) 필드가 어디서도 읽히지 않는다. 진단용이고
  `crest_skipped` 축이 이미 핵심 신호를 옮기므로 영향은 작다.
- 문서 정합성 — `HANDOFF_TO_LEAD.md §34.2` 는 "게이트 하나라도 실패하면 `cmd_submit` 이
  빈 목록을 반환한다"고 적었지만, **[확인]** 실제 코드(`plan.py:627` 부근 주석 "위반
  항목만 막는다. 전량 차단은 틀린 실패 모드다")는 gate (c)(총 천장 초과)만 전체를 막고
  gate (a)/(b) 위반은 **해당 항목만** `skipped` 처리한다(더 나은 설계로 보이지만, §34.2
  서술과 다르다 — 후속 세션이 "게이트=전량차단"으로 오독할 자리다).
- 테스트 개수 불일치 — **[확인]** 현재 소스로 `python3 -m unittest discover -s tests -q`
  실행 시 `684 tests OK (skipped=8)`. HANDOFF 최종 상태 줄은 `679 tests OK` 다. 전부
  통과하므로 결함은 아니지만, §34 이후 `test_accounts.py` 등 몇 파일이 그 뒤에도 수정된
  흔적(mtime)이 있다 — HANDOFF 의 마지막 "679" 라인이 이미 그 수정 전 스냅샷일 가능성이
  높다. 판단 근거로 `679`를 그대로 믿지 마라(ADR-041/043 규율 그대로).

## 확인한 것 (coder2 4항목 — 전부 경로 실행으로 재현, 문제 없음)

1. **§31 되돌리기 재현** — `collect.py` 의 `m.update(probes.host_metrics(...))` 를 제거하고
   `__pycache__` 를 지운 뒤 재실행: `FAILED (failures=1, errors=4)` — HANDOFF 서술과 정확히
   일치. `TestHostMetricsUnitBehaviour`(부품, 2건)와 `test_payload_writes_host_into_task_json`
   (payload 단위, 1건) 은 되돌린 상태에서도 **계속 통과**했다 — "부품 테스트로는 정의상 못
   잡는다"는 coder2 의 주장을 직접 재현해 확인했다. 복원 후 9건 OK.
2. **ADR-048 P6 3중 방어** — `payload/P6.sh` 가 declared/requested/observed(nproc)/
   actual_nprocshared 를 전부 기록하고, `collect_p6()` 가 `declared==requested==nprocshared`
   불일치 시 `[INVALID]` 로 버리며 κ·S 산출에서 제외하는 것을 코드로 확인. array 1코어
   하드코딩(§33.1 원 버그)에 대해서는 이 방어가 **정확히 설계대로** 작동한다. (plan-time
   게이트의 override 관련 사각지대는 위 "중대" 항목 참조 — 원래 버그에 대한 방어는 유효하다.)
3. **§33.1 wall/link 가드** — `plan.py` 의 array 코어 산식(`per_task_cores = ...`)을
   `1` 로 되돌려 재현: `test_pilot_arrays_get_whole_node_not_one_core`,
   `test_pilot_walls_stay_inside_the_queue_limit` 둘 다 즉시 FAIL — `budget_guard` 를
   우회하는 결함을 wall/링크를 직접 보는 검사가 잡는 것을 확인. 복원 후 684 tests OK.
4. **collect.py 전 함수 × payload 필드 대조** — P1/P1b/P3/P4/P6/probe_* payload 를 collect.py
   와 대조했고 대부분 정합(특히 u27_noneq.json 은 통째로 실려 손실 없음, P6 세 값 전부
   보존). **P5 만 위 "치명적" 항목처럼 심각한 유실**이 있었다 — 이것이 여섯 번째 사례다.

## 확인하지 못한 것
- 실클러스터의 `normal` 큐가 실제로 24 h 인지 48 h 인지, `long` 같은 더 긴 큐가 실제로
  존재하는지는 이 박스에서 확인 불가하다(PBS 없음). 위 "치명적" 항목의 실제 발동 여부는
  다음 회신에서만 확정된다 — 그러나 **코드가 그 상황을 안전하게 처리하지 못한다는 것
  자체는 클러스터 없이도 확인됐다.**
- `--ncpus-per-node`/`config/sizing.json:pbs.ncpus_per_node` 를 이번 라운드에 실제로 쓸
  계획인지는 lead/사용자 판단 영역이라 확인 대상이 아니었다.

## critic3 후속 — 2026-08-18 (같은 날, 이어서) — 대상 정정 반영 + coder2 수정 재검증 → **OK**

**경위**: 최초 리뷰 후 대상 해시가 두 번 더 갱신됐다(`4623019f0e11`(§34) →
`7dd91d57cc0c`(§35, ADR-050) → §36(게이트 항목단위 차단) → §37(critic3 대응)).
리뷰 도중 coder2 가 실시간으로 수정하는 것을 직접 목격했다(트리가 일시적으로
FAIL 상태였던 것도 확인 — mtime 기준 편집 중이었다). **각 수정을 독립적으로
재현·되돌리기 실험으로 재검증했다.** coder2 의 "고쳤다"는 말을 근거로 삼지 않았다.

### 재검증한 것 (전부 직접 실행)

1. **P5 dual-seed 유실 (치명적-1)** — `criteria/p5.py::normalize_rows()` 에 7개 필드
   (`seed`/`seed_provenance`/`failure_reason`/`g16_cpu_seconds`/`qc_code`/`route`/
   `level_label`) 복사가 추가됐고 `collect_p5` 가 `dual_seed_species`/`seed_pairs`/
   `_sigma_note` 를 싣는 것을 확인. **되돌리기**: 7개 필드 추가분을 지우고 재실행 →
   `tests/test_critic3_fixes.py` 4건 중 관련 2건 FAIL(존재 단언 우선이라 KeyError 아님).
   복원 후 통과 확인.
2. **`long` 큐 무연동 (치명적-2)** — `resolve_wall_limit(env, guard, max_wall_h, submit_queue)`
   에 `submit_queue` 인자가 추가돼, **명시적으로 그 큐를 찾은 경우에만** 그 큐의 wall 을
   쓰고, 못 찾으면 기존 단일 큐 probe(`queue_info`)로 폴백한다(예전처럼 "가장 긴 큐"를
   자동 채택하지 않음). `cli.py` 가 `submit_queue=default_partition(env, args)` 를
   실제로 넘기는 것 확인(제출 시 큐를 정하는 **바로 그 함수**). 더 긴 큐는
   `longer_queue_available` 로 **알리기만** 하고 자동 전환하지 않음. 직접 되돌리기: 새로
   추가된 override 블록을 지우고 재실행 → `test_submitting_to_long_uses_longs_wall` 등
   3건 FAIL(48.0 대신 None/틀린 값). 복원 후 9건 OK.
   🟢 통합 테스트(`test_24h_submit_queue_blocks_p1b_even_though_long_exists`)로
   "long 이 있어도 submit_queue=normal 이면 P1b 가 게이트에 걸린다"까지 확인됨 — 정확히
   내가 우려했던 시나리오가 이제 올바르게 차단된다.
3. **P6 게이트 override 사각지대 (중대)** — `plan.ncpus_override_from_config(args)` 로
   override 계산을 한 곳으로 모으고, `item_cores_are_the_measurement(key)` 가 `P6_t*`
   항목엔 override 를 면제하는 것 확인. 직접 재현: `--ncpus-per-node 32` 시뮬레이션 →
   `P1`/`P5` 는 32 로 덮이지만 **`P6_t1=1 P6_t16=16 P6_t64=64` 는 그대로**임을
   `build_spec()` 실행으로 직접 확인(내가 처음 재현했던 것과 같은 스크립트, 결과만 반대).

### 그 외 확인
- ADR-050 관련 4항목(모두 lead 가 §35 리뷰범위로 지정) — `tests/test_accounts.py`
  `TestEngineePolicyADR050`(mopac 프로브 유지+정책배제 / lammps≠reaxff / cp2k 조건부)
  + `tests/test_integration_paths.py::test_cp2k_layer_is_not_wired_into_the_package`
  (payload/*.sh 전체를 실제로 스캔해 CP2K 참조 0건 확인) — **전부 직접 실행, 통과.**
  `sysprobe.py` 의 `ALLOWED_ENGINES`/`CONDITIONAL_ENGINES`/`EXCLUDED_ENGINES` 는
  실제 판정 로직(`engine_policy()`)이고 스텁이 아님을 코드로 확인.
- **§30 재실행 로직(lead 최우선 지목, 미리뷰 이력)** — `inspect.getsource` 기반 텍스트
  검사(기존 테스트)로는 부족하다고 판단해 **직접 진짜 end-to-end 스크립트를 작성해
  실행**: `cmd_submit` 1차 제출 → `store.mark_failed("P1", ...)` → `cmd_submit` 2차
  호출 → 실제로 `P1` 에 새 `sbatch` 호출이 나가고(`+ P1 job=... x3 links`), 나머지
  이미 제출된 항목은 스킵되고, `is_failed` 가 clear 되는 것을 **런타임으로** 확인했다.
  (source-order 검사만 있던 기존 커버리지의 빈틈을 이번에 직접 메웠다 — 결과는 정상.)
- 최종 상태: `700 tests OK (skipped=8)`, `python3 src/build_stamp.py check --root .
  --dist src/dist` → `[stamp] ✅`, **`source_digest ecdba8a324e2157a`**(coder2 §37.6 과
  독립적으로 재계산해 일치 확인). tarball sha256 은 여전히 재빌드마다 바뀌는 것을
  재확인했고, 이번엔 `source_digest` 를 정본으로 쓰는 것이 규약으로 명문화됐다
  (byte-reproducible build 자체는 별도 사양, lead 승인 대기 — 이건 이번 라운드 범위 밖).

## 판정 (최종)
**OK** — 대상 `source_digest ecdba8a324e2157a` (`700 tests OK`, `[stamp] ✅`).
치명적 2건 + 중대 1건 + 사소 3건 전부 coder2 가 고쳤고, **전부 내가 독립적으로
재현·되돌리기 실험으로 재검증**했다(coder2 의 보고를 근거로 삼지 않았다). 새로
발견된 결함 없음. 19,000 core-h 규모 제출을 진행해도 된다고 판단한다.

**남는 것 (차단 사유 아님, 기록만)**: tarball byte-reproducibility 는 정책 결정
대기 상태로 남아 있다 — `source_digest` 를 정본으로 삼는 규약이 이미 이번 세션에
정착했으므로 급하지 않다.

### 추기 — `ecdba8a324e2157a` 이후 추가 변경 예고 (같은 날)

위 "OK" 판정은 `source_digest ecdba8a324e2157a` 시점 기준으로 유효하다(coder2 도 동일 시점을
"안정 체크포인트"로 확인). **그 직후 사용자 답변**(*"`long` 은 존재하지만 `normal` 이 이미
48 h 다. `long` 은 안 쓴다"*)에 따라 lead 가 **치명적-2 의 처방을 재판정**했다:
*"게이트가 제출 큐를 보게 배선"(§37, 내가 검증한 것) 대신* **"발동 조건이 사라졌으니 배선하지
말고 선택 로직 자체를 지워라"**(*"가장 안전한 코드는 없는 코드다"*). lead 는 동시에
*"`queue_selected` 미배선이 무해해진 것은 운이 좋았던 것이지 우리가 잘한 게 아니다 — critic 이
찾지 않았으면 24h 사이트에서 그대로 터졌을 것"*이라고 적어, **내 지적 자체는 유효하게 유지된다는
것**과 **처방만 바뀐다는 것**을 분리했다. 또한 이번 라운드에서 드러난 네 사례(host 유실 / wall
상한 미소비 / P5 dual-seed / queue_selected 미소비)가 **같은 병**(생산자→소비자 경계에서
값이 조용히 버려짐)이라는 점에서, lead 가 **경계 검사를 일회성 감사가 아니라 상설 회귀
테스트로 넣으라고 지시**했다.

⟹ **다음 재재리뷰는 새 `source_digest` 로 다시 한다.** `ecdba8a324e2157a` 자체에 대한 위 OK
판정을 철회하지 않는다(그 시점 코드는 실제로 정상이었다) — 다만 **그 코드가 최종 인도판이
아니게 됐으므로**, 새 체크포인트가 나오기 전까지는 **판정을 보류(대기)** 상태로 둔다.
coder2 요청대로 지금은 재검증하지 않고 다음 호출을 기다린다.

## critic3 재재리뷰 — 2026-08-18 (같은 날, 세 번째) — 대상 `source_digest 308884324b43a963` → **OK 유지**

**대상**: ADR-052(큐=normal 고정, 선택로직 삭제) + 생산자→소비자 경계 검사 신설 반영판.
`710 tests OK (skipped=8)`, `[stamp] ✅`. 전부 직접 재검증(되돌리기 실험 포함), coder2 보고를
근거로 삼지 않았다.

### 재검증한 것 (직접 실행)

1. **치명적-2 재처방(ADR-052)** — `resolve_wall_limit()` 에서 `longest_wall_queue` 자동 선택
   블록이 완전히 제거되고 `longer_available = None` 으로 고정된 것, 그리고 `EXPECTED_QUEUE_WALL_H
   = 48.0` 대비 실측이 다르면 `queue_wall_surprise` 경고가 뜨는 것을 코드로 확인.
   **되돌리기**: 지운 자동 선택 로직을 복원해 재실행 → `test_no_queue_selection_happens_at_all`
   FAIL 확인(`longer_queue_available` 가 다시 채워짐). 복원 후 `test_critic3_fixes.py` 11건 OK.
2. **`tests/test_producer_consumer.py`(신설, 8건)** — sysprobe 수집 필드 전수 소비 검사 +
   payload 아티팩트 전수 소비 검사 + "이미 샜던 값 4건" 이름 고정 검사. **되돌리기**:
   `report.py` 에서 `"engine_policy": login.get("engine_policy"),` 한 줄 제거 →
   `test_engine_policy_and_raw_modules_reach_the_report` FAIL 확인(coder2 가 이번 라운드에
   자기가 만든 ADR-050/043 필드를 자기가 새게 할 뻔했다는 보고와 일치). 복원 후 8건 OK.
3. **P3/GPU 휴면 유실 3건 화이트리스트** — `p3_attempt_quality.json`/`xtb_source.json` 은
   `payload/P3.sh` 에서만 쓰이는데 `plan.py::default_items()` 에 `Item("P3", ...)` 자체가
   없음을 확인(ADR-049 로 계획에서 실제로 빠짐). `pystack.json` 은 `probe_gpu_node.sh` 전용인데
   **ADR-037 확인**: *"GPU tarball 을 인도하지 않는다"* — 코드는 남아 있지만 이번 라운드엔
   실행될 기회가 없다. **셋 다 화이트리스트 사유가 정확하다.**

### 새로 확인한 것 — `collect_p1b`/`collect_p4` 확장 대조 (coder2 요청)
- `collect_p1b` — `u27_noneq.json` 은 통째로 실려 손실 없음(재확인). `geom_source.txt`
  (TS 기하 출처 텍스트)만 안 읽힘 — 진단 텍스트라 영향 작음.
- 🟡 **`collect_p4`** — `payload/P4.sh` 가 쓰는 `gpu_error` / `cpu_error` / `fatal` /
  `gpu_failure_class` / **`gpu_fix_hint`**(`symptom`/`pip`/`why`/`ld_library_path` 4필드) /
  `memscan_error` / `memscan_stopped` / `oom_error` / `n_basis_functions` / `gpu_count` /
  `cpu_reference_machine` 이 `collect_p4`/`p4.evaluate_p4` 어디에서도 읽히지 않는다(코드
  대조로 확인, `criteria/p4.py` 전체에 해당 이름 0건). 특히 `gpu_fix_hint` 는 GPU import 실패의
  **구체적 pip 처방**을 담은 값진 진단인데 최종 회신에서 사라진다. `test_producer_consumer.py`
  의 아티팩트 검사는 **파일 단위**(`p4_result.json` 을 여는지)만 보고 **필드 단위**는 보지
  않아 이 결함을 못 잡는다(coder2 본인이 이 한계를 자인한 그대로).
  **다만 ADR-037 에 따라 GPU tarball 이 이번 라운드에 인도되지 않으므로, 지금 당장의 19,000
  core-h 제출에는 영향이 없다.** P3 휴면 유실과 같은 성격(고쳐서 무해한 게 아니라 안 돌아서
  무해)이므로 **`WHOLE_DICT_PASSTHROUGH`/화이트리스트에 사유와 함께 등록하거나, GPU 패키지를
  다음에 되살릴 때 함께 고치라고 표시해 두는 것을 권한다.** 이번 라운드 차단 사유는 아니다.

### 그 외 의견 (coder2 질의 응답)
- **`item_cores_are_the_measurement()` 의 `P6_t` 접두사 의존** — 여전히 약한 지점이라는 데
  동의한다. 지금 당장 고칠 만큼 급하지는 않다(Item 객체에 명시적 플래그를 두는 것이 더 나은
  방향이라는 데는 동의하지만 이번 라운드 차단 사유로 보지 않는다).
- **시드 쌍 미완성 경고 승격** — 과하지 않다고 판단한다. 안 읽는 소비자가 생기면 그 자체가
  같은 병의 재발이다.
- **ADR-052(배선 대신 삭제)** — 지지한다. lead 의 *"가장 안전한 코드는 없는 코드다"*
  판단에 동의하며, `queue_wall_surprise` 로 "사용자 진술과 실측이 다르면 알린다"는 안전판이
  남아 있어 ADR-036 원칙과도 정합한다.

### 최종 확인
`710 tests OK (skipped=8)`, `python3 src/build_stamp.py check --root . --dist src/dist` →
`[stamp] ✅`, `source_digest 308884324b43a963`(coder2 보고와 독립적으로 재계산해 일치 확인,
빠른 표적 재실행으로도 재확인 — 동시에 여러 세션이 전체 스위트를 돌려 한 차례 시간이 오래
걸렸으나 결과 자체는 안정적이었다).

## 판정 (유지)
**OK.** 새로 발견한 `collect_p4` 필드 유실은 **이번 제출(CPU 19,000 core-h)을 막을 사유가
아니다**(GPU 패키지 미인도, ADR-037). 나머지는 전부 재검증 통과. 진행해도 된다.

## critic3 부분 재확인 — 2026-08-18 (네 번째) — `source_digest ecf8c7272aa15615` (714 tests)

**요청 범위**: `make_package.sh` 출력 문구, `criteria/cost.py::longest_stage()` 신설 +
`collect_p1` 적재, `collect_p4` 화이트리스트 등록(내가 앞서 찾은 것). 전부 직접 검증했다.

### 검증한 것
1. **`make_package.sh` 출력** — `pilot_package/` 밖 파일이라 `source_digest` 대상이 아님을
   재확인(diff 로 plan.py/p5.py/report.py 무변경도 함께 재확인). 문구만 바뀌었고 `sha256` 을
   "전송 무결성용, 동일성 비교에 쓰지 마라"로 명확히 구분한 것 확인 — 내가 처음 지적한
   tarball 비재현성 문제의 "값싼 절반"(문서화)을 제대로 닫았다.
2. **`longest_stage()` 트립와이어** — `cost.py` 에 신설, `LONGEST_STAGE_TRIPWIRE_H=40.0`,
   기록 없으면 `exceeds_tripwire: null`(ADR-036 — "안전"이 아니라 미판정)인 것 확인.
   **되돌리기**: `exceeds_tripwire` 를 `False` 로 강제 → `test_tripwire_fires_above_40h` FAIL
   확인, 복원 후 15건 OK(coder2 의 "[되돌리기 L]" 재현).
3. **`collect_p4` 화이트리스트 등록** — `test_producer_consumer.py` 에 `p4_result.json`/
   `pystack.json` 상호참조 사유가 실제로 적힌 것 확인.

### 🔴🔴 새로 찾은 것 — **트립와이어 자신이 자신의 존재 이유를 어겼다**
`collect_p1()` 에 `res["longest_stage"] = cost.longest_stage(recs)` 를 지웠더니 —
**714건 중 단 한 건도 실패하지 않았다**(dist 신선도 무관 실패 2건 제외). **`longest_stage()`
자체의 단위 테스트 4건은 전부 `cost.longest_stage()` 를 직접 부르고, `collect_p1()` 을 거쳐
최종 결과에 도달하는지 보는 테스트는 0건이다.** ADR-041("경계가 아니라 진입점에서 테스트하라")
이 정확히 겨냥한 그 구멍이, **"측정해놓고 안 쓰는 값을 막으려고 만든 안전장치" 자신에게서
재발했다.**

🔴 **더 심각한 것**: `collect_p1()` 같은 함수, 세 줄 아래(219행)에서 `degraded_reasons` 는
`res.setdefault("warnings", []).extend(...)` 로 **사람이 읽는 채널에도** 싣는다(주석: *"필드는
코드가 읽고 warnings 는 사람이 읽는다 — 둘 다 필요하다"*). **`longest_stage` 는 그 패턴을
따르지 않는다** — `exceeds_tripwire: true` 가 나와도 `res["warnings"]` 에 아무것도 안 남는다.
`report.py::summarize_for_user()` 콘솔 요약도 `longest_stage`/`warnings` 를 보지 않는다
(코드 확인, 참조 0곳).

**왜 이게 이번 제출에 특히 중요한가**: `ADR-052` 자신이 적어둔 대로, **P1 최장 스테이지
`[ESTIMATE]` 최악 칸이 47.8 h 로 트립와이어(40 h)에 여유 0.2 h 뿐이다.** 즉 이 트립와이어는
가상의 엣지 케이스가 아니라 **이번 제출에서 실제로 발동할 가능성이 낮지 않은 안전장치**다.
발동해도 `res["warnings"]` 에 안 실리면, JSON 을 받는 사람이 `pilots[].longest_stage` 를
따로 찾아 봐야 한다 — **바로 그 "사람이 뒤져야 하는 안전장치"를 이 필드 자신이 없애려고
만들어졌는데, 구현이 그 목적을 절반만 이뤘다.**

## 판정
**FIX-THEN-RUN** (이 항목 하나 때문에). 나머지 3건(빌드 출력/트립와이어 계산 자체/`collect_p4`
화이트리스트)은 전부 확인 통과.

**요청**: (a) `longest_stage()["exceeds_tripwire"]` 가 True 면 `collect_p1` 이
`res["warnings"]` 에도 싣는다(기존 `degraded_reasons` 패턴 그대로). (b) **진입점 테스트 하나**
추가 — 진짜 `stages/*.json` 을 디스크에 놓고 `collect_p1()` 을 호출해 최종 결과에
`longest_stage` 와 (트립와이어 발동 시) 해당 경고가 도달하는지 확인(ADR-041). 되돌리기 실험은
`res["longest_stage"] = ...` 줄과 새 warnings 확장 줄을 각각 지워서 이 새 테스트가 깨지는지로.

## critic3 재확인 — 2026-08-18 (다섯 번째) — `source_digest ca757f4cfac0d30c` (718 tests) → **OK**

**요청 범위**: `collect.py` 의 트립와이어 `warnings[]` 확장 2줄 + `test_critic3_fixes.py` 의
`TestTripwireReachesTheFinalResult` 4건. `diff` 로 그 외 파일(plan.py/p5.py/report.py/cost.py)
무변경도 재확인했다.

### 검증한 것
- **`warnings[]` 확장** — `collect_p1()` 에 `exceeds_tripwire` 시
  `res.setdefault("warnings", []).append(...)` 가 정확히 추가된 것을 diff 로 확인.
- **4건 신설 테스트** — 전부 **디스크에 진짜 `stages/*.json` 을 놓고 `store`/`collect_p1()` 을
  실제로 호출**하며, 마지막 1건은 `cmd_collect()` 까지 통과해 **디스크에 쓰인 회신 JSON**
  안의 `pilots[].longest_stage.exceeds_tripwire` 를 확인한다(ADR-041 끝까지).
- **되돌리기 [M] 독립 재현** — `res["longest_stage"] = …` 줄 제거 → **`FAILED (failures=1,
  errors=3)`** — coder2 의 자진신고("존재 단언이 1건뿐이라 나머지 3건은 ERROR")와 정확히
  일치함을 직접 확인했다. (ADR-042(a) 기준 미달이라는 coder2 의 자평에 동의하지만, FAIL 1건이
  이미 증거로 충분해 이번 라운드에 추가 수정을 요구하지 않는다 — 사소.)
- **되돌리기 [N] 독립 재현** — `warnings` 확장 2줄만 제거 → **`FAILED (failures=2)`**
  (경고 도달 테스트 2건만 정확히 깨짐, 필드 자체는 살아있는 나머지 2건은 통과) — coder2 보고와
  일치.
- 복원 후 `python3 src/build_stamp.py check` → `[stamp] ✅`, `source_digest ca757f4cfac0d30c`
  독립 재계산 일치.

### ⚠ 범위 밖에서 발견한 것 (기록만, 판정에 반영 안 함)
전체 스위트 실행 중 `tests/test_session_digest.py::TestAgainstRealDocs::test_real_docs_parse_sanely`
가 재현 가능하게 FAIL 한다(`AssertionError: 'Current phase 를 읽지 못했다'`). 원인:
`src/session_digest/docparse.py::parse_header()` 가 `docs/05_STATE.md` 의 **첫 12줄만** 스캔해
`**Current phase**:` 를 찾는데, 그 줄이 지금 **135행**에 있다 — 문서가 성장하며 헤더 필드가
윈도 밖으로 밀려난 것으로 보인다. **`session_digest` 는 이번 라운드에 아무도 건드리지 않았고
(coder2 의 diff 에도 없다), pilot_package 리뷰 범위 밖이다.** 판정에 반영하지 않았으나
lead 에게 별도로 알린다.

## 판정
**OK.** `source_digest ca757f4cfac0d30c`. 트립와이어 안전장치가 이제 필드·경고·회신 JSON
세 층 전부에서 확인됐다. 새로 발견한 결함(범위 밖 session_digest 제외) 없음.
19,000 core-h 제출 진행 가능.

## critic3 리뷰 — §41 README 정합성 — 2026-08-18 (여섯 번째, 대상 `source_digest 79624c4f182e8c14`)

**대상**: 코드가 아니라 **사용자가 읽는 면** — `README_USER.cpu.md` 재작성,
`tests/test_readme_matches_code.py`(8건), `test_account_submission.py` 임시 디렉터리 누수 수정.
`726 tests OK`, `[stamp] ✅`. 전부 직접 실행·되돌리기·인도본(tarball) 추출로 확인했다.

### ① README 수치가 코드에서 파생됐는가 — **[확인, 코드 실행]**
README 를 보지 않고 **독립적으로** `plan.build_plan()` 을 직접 호출해 재계산했다(64 core/node,
`normal` 48h, g16+xtb 만 있는 환경):
```
guard 21,000 / 48h · reserved 19,091.4 · expected 16,679.0
probe 65.8 · P1 9,216 · P1b 4,738 · P5 3,127.6(≈3,128) · P6_t1/16/64 = 24/384/1,536
```
**README 의 모든 수치와 정확히 일치했다.** 손으로 옮겨 적은 자리는 찾지 못했다.
`tests/test_readme_matches_code.py::code_truth()` 도 같은 방식(진짜 `plan.build_plan()` 호출)
으로 산출해 SPEC-BLOCK 과 대조하는 것을 코드로 확인 — 하드코딩된 "정답"과의 대조가 아니다.

### ② 되돌리기 [O]/[P] — **양쪽 다 직접 재현**
```
[O] budget.py 의 cpu guard 21000→17000 (코드만 변경) → FAILED (failures=3)
    (guard 불일치·항목목록 변경·합계 불일치 — README 는 그대로인데 코드가 바뀌어 어긋남)
[P] README 의 SPEC-BLOCK 삭제(정규식으로 블록 통째 제거) → FAILED (failures=5)
    (test_spec_block_is_actually_parsed 포함 — 검사 자신이 사라진 검증 대상을 알아채는지)
복원 후 각각 8건 OK
```
lead 가 요청한 "검사가 검사망 안에 있는가"를 [P] 로 직접 확인했다 — **블록이 사라지면 조용히
통과하는 대신 명시적 `AssertionError`(FAIL, ERROR 아님)로 RED 가 된다.**

### ③ 🔴 lead 의 필수 질문 — "검사는 소스를 지키는데 인도물은 복사본이다" 판정
**결론: 실재하는 구조적 구멍이 맞다. 다만 오늘 산출물은 무결하고, 지금 당장 위험도는
lead 의 우려보다 낮다 — `make_package.sh` 가 `set -eu` 로 돌아 `cp -r` 실패 시 스크립트
자체가 죽어서 `tar czf` 까지 못 간다(이번 세션의 실제 사고도 "빌드가 죽었다"였지 "깨진
tarball 이 스탬프를 통과했다"가 아니었다). `build_stamp.py check` 의 tarball sha256 검증도
빌드 직후 값과 지금 값을 대조하므로, **빌드 자체가 성공한 뒤에 tarball 이 손상되는 경로**는
잡는다.**

**그럼에도 진짜 구멍**: (a) `cp -r` 이 disk-full 이 아닌 다른 이유로 **부분 실패했는데 exit
code 는 0인 경우**(예: 권한 문제로 일부 파일만 건너뛰는 cp 구현, 향후 리팩터로 `set -e` 가
깨지는 경우, `cp` 를 파이프에 넣어 exit code 가 가려지는 경우)는 오늘의 방어선을 그대로
통과한다. (b) **`build_stamp.py check` 는 소스 트리와 tarball 의 "동일성"을 직접 비교하지
않는다** — 소스는 `source_digest`(내용 해시)로, tarball 은 "빌드 시점 자기 자신과 같은가"로
따로 검증한다. **한 번도 "tarball 을 열어서 source_digest 와 대조"하는 코드 경로가 없다.**
직접 확인: `grep -rn "tarfile\|tar.*open\|extractall" src/build_stamp.py` → **0건.**

**차단 사유가 아니다.** 이유:
1. 오늘 인도본은 내가 **직접 tarball 을 추출해** `README_USER.md` 를 소스와 `diff` 했고
   **바이트 단위로 동일**했다 — 무결하다는 lead 의 결론을 독립적으로 재확인했다.
2. `set -eu` 방어선이 이미 오늘의 구체적 사고(disk-full) 유형을 실제로 막았다(빌드가 죽었지
   나쁜 tarball 이 나가지 않았다) — **완전 무방비는 아니다.**

**그래도 이번 판에 고칠 값어치가 있다고 판단한다(다음 판으로 미루지 말라):**
- 비용이 작다 — `test_readme_matches_code.py` 의 `spec_block()`/`code_truth()` 를 재사용해
  **tarball 을 임시로 풀어 그 안의 `README_USER.md` 로 같은 단언을 반복**하는 테스트 클래스
  하나만 추가하면 된다(`tarfile.open` + `extractall` + 경로만 바꿔 기존 함수 재사용).
- 이 프로젝트가 **같은 유형의 사고를 이미 여섯 번 이상** 냈다("검사 대상과 실제 산출물이
  다른 사본" — dry-run≠제출본, README 소스≠tarball 사본, tarball sha256≠source_digest 등)
  — **패턴이 반복될 때마다 "다음 판"으로 미루는 관성 자체가 이 프로젝트의 반복된 실패
  원인**이었다(ADR-041/042/043 전부 "왜 진작 안 잡았나"의 기록이다).
- `make_package.sh` 가 이미 각 프로파일을 dry-run 스모크(2/5 단계)로 검증하고 있으므로,
  **같은 자리에 "tarball 추출 → README 대조"를 한 단계 추가하는 구조적 비용은 낮다.**

### ④ P6 경고·wall 불일치 지침의 위치·강도 — **[확인]**
- **"P6 를 빼지 마세요"** — P6 표 행 바로 아래(36행), 독립된 굵은 문장, 🔴 이모지로 시작.
  표를 훑다 항목을 지우려는 사람이 **바로 다음 줄에서** 마주친다. 위치·강도 모두 적절하다고
  판단한다.
- **wall 불일치 지침** — 별도 `## 🔴 제출 전에 멈춰야 하는 경우` **소제목**으로 분리돼 있어
  훑어보기(skimming)만 해도 걸린다. dry-run 이 실제로 찍는 문구의 핵심 어구("walltime 상한이
  X h 다 — 확인해 준 값 Y h 와 다르다", `[UNVERIFIED]`)를 그대로 인용해 화면 경고와 문서를
  사람이 패턴매칭할 수 있게 연결했다(완전한 축자 인용은 아니지만 — ADR-052/조항 번호 등은
  생략 — 핵심 수치·구조는 일치해 인식에는 지장 없다).
- 둘 다 **"문구 존재 여부"** 를 넘어 **사용자가 실제로 멈추게 만드는 배치**로 판단한다.

### ⑤ 임시 디렉터리 누수 수정 — **[확인, 실행]**
`test_account_submission.py::tearDown`/`addCleanup` 이 **자신이 만든 경로(`self.d`/지역 변수
`d`)만 정확히 추적해 지운다** — 와일드카드(`sei_acct_*` 글롭)로 **다른 세션의 살아있는 임시
디렉터리까지 쓸어버릴 위험은 없다**(코드에 glob/패턴 삭제 0건, 직접 grep 확인).
실행 확인: 이 파일만 단독 실행 전후 `/tmp/sei_acct_*` **0→0**(신규 누수 없음),
`/tmp/sei_feas_*` **6→6**(기존 잔재는 이 세션 이전 것으로 보이며 이 실행이 늘리지 않았다).

## 판정
**FIX-THEN-RUN — 단, 오늘 인도본 자체는 무결하다(BLOCK 아님, 낮은 비용의 개선 요청).**
README·되돌리기·임시디렉터리 수정 전부 통과. ③의 "소스 vs tarball 사본" 구멍만 이번 판에
닫을 것을 권고한다(비용이 낮고 같은 유형의 사고가 반복돼 온 프로젝트라는 근거로).
이 항목 때문에 19,000 core-h 제출을 막을 필요는 없다고 본다 — **오늘 인도본은 내가 직접
tarball 을 열어 무결성을 확인했다.** 다음 빌드부터 이 검사가 있으면 같은 확인을 사람이
반복하지 않아도 된다.

## critic3 — §41 보강 질문 (A)(B)(C) 답변 — 2026-08-18 (같은 리뷰, 이어서)

**직접 재현**: `dist/sei_pilot_*.tar.gz` 를 임시로 다른 곳에 옮기고(‑`make_package.sh` 의
"낡은 산출물을 `.stale` 로 치운" 직후·"테스트 실행" 직전과 같은 상태) 그 상태에서
`test_build_stamp.py` 를 돌렸다:
```
test_account_column_is_in_the_packaged_plan  ... skipped 'tarball 이 없다'
test_bundled_bases_are_in_the_tarball        ... skipped 'tarball 이 없다'
test_m2_provenance_is_in_the_packaged_p1     ... skipped 'tarball 이 없다'
test_rt1b_is_in_the_packaged_p1b             ... skipped 'tarball 이 없다'
```
tarball 을 되돌린 뒤 같은 파일을 다시 돌리면 **4건 전부 `ok`**(진짜로 tarball 을 열어 내용을
확인)로 바뀐다. `make_package.sh` 를 라인 단위로 다시 읽어 **`[1/5] 테스트 실행`(23행)이
`[3/5] tarball 생성`(36~54행)보다 먼저** 실행됨을 확인했다 — **lead 의 주장과 완전히 일치한다.
`_member()` 기반 검사군은 `make_package.sh` 실행 중 100% skip 된다.**

### (A) 빌드가 자기 산출물을 못 보는 구조가 허용 가능한가 — **아니오, 그리고 교착과 무관하게 고칠 수 있다**
`:12-13` 주석이 말하는 교착은 **"낡은(이전 빌드) tarball 을 새 빌드 전에 검사해서 막힌다"**
는 것이다. 그 해법(치우고 skip)은 **그 문제만** 푼다. **내가 요구하는 것은 그것과 다른
질문이다: "방금 이 실행에서 새로 만든 tarball 을 검사하라."** 이건 순환이 아니다 —
새 tarball 이 새 소스에서 갓 나온 것이므로, 검사가 실패하면 원인은 **패키징 단계 자체의
버그**이고, 사람이 그걸 고치고 다시 빌드하면 된다. **다른 빌드 단계(테스트 실패 시
`.stale` 복원 후 `exit 1`)와 완전히 같은 패턴**이라 새 위험을 안 만든다.
⟹ **`[3/5]` 뒤, `[4/6]`(지문 기록)과 나란히 `[3.5/6] 패키지 산출물 검증`** 을 추가해
**그 tarball 대상 검사군만**(`test_build_stamp.py` 의 tarball 계열, 빠르다 — 1초) 다시 돌리고,
실패하면 다른 단계와 똑같이 `exit 1` 로 막는다. **답: 허용 불가하고, 고치는 비용도 낮다.**

### (B) coder2 의 `~5줄` 이 실질 보호인가, 초록 불빛인가 — **지금 그대로면 초록 불빛뿐이다**
`_member("README_USER.md")` 를 **기존 `TestM2DecisionReachesTheTarball` 클래스에 얹기만** 하면
그 클래스 전체가 (A) 에서 확인한 대로 `make_package.sh` 안에서 **항상 skip** 된다 — 즉
**빌드 파이프라인 안에서는 이 assertion 이 단 한 번도 실행되지 않는다.** 사람이 빌드 후
스위트를 **따로** 돌릴 때만(오늘 나와 lead 가 그랬던 것처럼) 실행된다. **이건 정확히 이
프로젝트가 아홉 번째로 반복하는 형태다 — "검사는 있는데 정작 필요한 순간엔 안 돈다."**
⟹ **coder2 의 5줄 자체는 옳고 필요하지만, (A) 의 파이프라인 배선 없이 단독으로는 실질
보호가 아니다.** 둘을 함께 넣어야 한다.

### (C) 지금 고칠 값어치가 있는가 — **있다. 지금 고쳐라.**
- 비용: `make_package.sh` 에 5~8줄(테스트 하위집합 재호출 + 실패 시 `exit 1`) + coder2 의
  README assertion ~5줄. **총 10~15줄, 실행 시간 +1초 미만**(tarball 계열만 도니까).
- 이득: **오늘 인도본이 무결했던 것은 사람이 습관적으로 다시 돌렸기 때문**이라고 lead 가 이미
  실측으로 못박았다. 습관은 다음 빌드에서, 또는 다른 세션(coder2/lead 가 바뀌거나 바빠서
  건너뛸 때)에서 실패할 수 있다. **구조로 만들어 두면 그 확률이 0 이 된다.**
- 이 프로젝트 자체의 규율(ADR-041/042/043, "검사 자신이 검사망 안에 있는가")과 정확히
  같은 결의 문제라, **다음 판으로 미루면 그 규율을 스스로 어기는 셈이다.**

## 판정 (§41, 확정)
**§41 자체(README 재작성/`test_readme_matches_code.py`/누수 수정)는 통과.**
**추가로 발견된 "빌드 파이프라인이 자기 산출물을 검사 못 하는" 구조적 결함은 이번 판에
고치는 것을 권고한다** — (A)(B)(C) 답변 전부 "지금, 저비용, 구조로" 를 가리킨다.
오늘 이미 인도된 tarball 자체는 (사람이 직접 tarball 을 열어 확인했으므로) 무결하다 —
**차단 사유는 아니고, 습관에 기대지 않는 재발 방지 조치로 권고한다.**

## critic3 review — §42/§43 build gate partial re-verification — 2026-08-18 (seventh, `source_digest 79624c4f182e8c14`, unchanged since §41)

**Note**: from this entry on, output is in English per user instruction relayed by lead.

**Target**: `tests/packaged_gate.py` (new), `tests/test_readme_matches_code.py` (new `TestBuildGate`
class), `src/make_package.sh`, `src/build_stamp.py`. All four requested items (a)-(d) verified by
direct execution and revert experiments, independent of lead's or coder2's own measurements.

### Baseline
```
standalone: Ran 735 tests OK (skipped=8)                         -- confirmed, matches lead's report
gate alone: cd tests && python3 -m unittest -q packaged_gate
            -> Ran 8 tests OK (TestM2DecisionReachesTheTarball x4
               + TestPackagedReadmeMatchesCode x4)                -- confirmed
source_digest 79624c4f182e8c14, stamp check -> [OK]               -- confirmed, unchanged since §41
```

### (a) New tarball-opening class, wired nowhere by name -> must be auto-discovered
Created a throwaway file `tests/test_critic3_gate_probe.py` with a new class
`TestCriticProbeOpensTarball` (calls `tarfile.open(` on the real dist tarball), registered nowhere
in `packaged_gate.py`. Ran `python3 -m unittest packaged_gate` from `tests/`:
```
first pass (assertion true):  Ran 9 tests ... OK              <- discovered and ran
second pass (assertion false, deliberately wrong): Ran 9 tests ... FAILED (failures=1), exit code 1
```
Confirmed both directions: a brand-new class is picked up without any registration, and when it
fails, the whole gate process exits non-zero (the shape `make_package.sh`'s `if (...)` branch
depends on). Cleaned up the probe file afterward; gate back to 8/OK.

### (b) Remove the `[6/7]` gate invocation from `make_package.sh` -> must go RED
Located and stripped the entire gate block (the comment header through the closing `fi`) from a
copy of `make_package.sh`; `bash -n` confirmed the result still parses. Ran the meta-test suite:
```
FAILED (failures=1)
FAIL: test_gate_exists_and_runs_after_packaging (test_readme_matches_code.TestBuildGate...)
AssertionError: 'packaged_gate' not found in '<script text>' : gate missing after packaging step
```
This is exactly the meta-test I looked for on my own before finding it: it inspects
`make_package.sh`'s own text for the literal string `"packaged_gate"` and asserts it appears after
`"tar czf"`. It is discovered by the default `test*.py` pattern, so it **is** part of the 735-test
standalone run -- deleting the gate's invocation line is caught without anyone needing to run a
full build. Restored the file; `diff` confirmed byte-identical to the pre-edit checkpoint; suite
back to green, stamp still ✅.

### (c) `VERIFICATION_FAILED.json` present -> `build_stamp.py check` must not report OK
Did this independently, not just re-running the shipped `test_marker_makes_stamp_check_fail`: copied
the real `dist/` (tarballs, sha256, BUILD_STAMP.json) into a scratch directory, hand-wrote a
`VERIFICATION_FAILED.json` with an arbitrary reason string, and ran
`python3 src/build_stamp.py check --root . --dist <scratch>` directly:
```
[stdout] "This dist/ has FAILED artifact verification -- do not ship it."
         reason: critic3 injected marker for independent verification
         (exact injected string echoed back)
exit code: 1
```
Confirms the marker is checked first and unconditionally blocks the OK report, even though every
other file in the scratch dir (tarballs, hashes, stamp) was otherwise internally consistent.

### (d) Is `tarfile.open(` (paren-anchored) fragile, and does discovery match the real set?
Wrote a third, independent AST scanner from scratch (not copied from either
`packaged_gate.tarball_test_classes()` or the test file's own duplicate check), scanning every
`test_*.py` for class bodies containing the literal substring `"tarfile.open("`:
```
independently recomputed: [('test_build_stamp', 'TestM2DecisionReachesTheTarball'),
                            ('test_readme_matches_code', 'TestPackagedReadmeMatchesCode')]
packaged_gate's own set:  <identical>
MATCH: True
```
Also checked directly whether `TestBuildGate` (the meta-test class itself, which references
`packaged_gate.OPENS_TARBALL` by attribute, not by inlining the string) trips the paren-anchored
scan: it does not (`tarfile.open(` does not appear literally in its source). The self-match
history in the docstring refers to an earlier, bare-substring version of the criterion; the
paren-anchored version in the current source does not reproduce it. Also directly triggered the
"zero classes found" fail-safe by monkeypatching `tarball_test_classes` to return `[]` and calling
`load_tests` -- it raises `AssertionError` (fails loud), not a silent pass.

## Verdict
**PASS.** All four items (a)-(d) verified by direct execution and revert experiments, independent
of the measurements reported by lead and coder2. No new gaps found within the requested scope.
Per lead's explicit instruction, `per_file` full-tarball comparison and re-deriving `source_digest`
from the deliverable are out of scope for this round and are not evaluated here.

## Status — shipped, standing down

Lead accepted the PASS verdict from the §42/§43 build-gate re-verification and is shipping:
`source_digest 79624c4f182e8c14 · 735 tests OK · stamp check OK · gate 8/OK · no VERIFICATION_FAILED marker`.

No further review action until the user returns `sei_probe_report.cpu.json`. Per lead's instruction,
first task on return will be checking the P6 numbers (kappa and the thread-count knee S) against
their stated purpose and measurement conditions (ADR-048 invalidation rules, same-system/same-job-type
comparability to the RT-1c reference value) -- that is now the variable the five-month schedule
depends on. Standing by.

## critic3 review — RT-1 module-name incident (D1-D4) — 2026-08-18 (eighth, full re-verification, `source_digest b8375e9d18326553`)

**Target**: `sei_pilot/sysprobe.py`, `config/env_paths.json`, `payload/qc_adapter.sh`, 4 changed
test files. Full re-verification (source_digest changed from `79624c4f182e8c14`). All items
verified by direct execution, independent construction, and revert experiments.

### Baseline
```
source_digest b8375e9d18326553 -- confirmed, stamp check OK
gate (packaged_gate, from tests/): Ran 8 tests OK               -- confirmed, matches lead's report
standalone: Ran 743 tests OK (skipped=8)                        -- MEASURED DIFFERENT FROM LEAD'S "740"
```
🔴 **Discrepancy found on the standalone count** (see "Fact-check" section below). Everything else
matches lead's measurements exactly.

### (a) Audit count of `strip/rstrip/lstrip(<arg>)` call sites -- verified independently, found a miscount
Grepped every `.py` file under `pilot_package/` (not just `sysprobe.py`) for the pattern
`\.(strip|rstrip|lstrip)\(["'][^"')]`, then hand-classified each hit as live code vs. docstring:
```
sysprobe.py:232   name.rstrip("*")        -- live, single-char, safe
sysprobe.py:254   name.rstrip("*")        -- live, single-char, safe
sysprobe.py:472   tok.rstrip("(default)") -- INSIDE THE DOCSTRING (illustrates the old bug), not live
sysprobe.py:501   tok.strip(":,")         -- live, part of strip_module_markers's own cleanup step
plan.py:1021      .strip(" /")            -- live, "genuine char set" per HANDOFF, matches
g16.py:185        line.strip().lstrip("#")-- live, single-char, safe -- NOT MENTIONED IN THE AUDIT
```
🔴 **The claimed count is off by one.** HANDOFF §44.2 states "4 call sites, only this one was
wrong" and lists exactly `rstrip("*")` x2 + `plan.py .strip(" /")` + the fixed bug = 4. That
enumeration omits `criteria/g16.py:185`, a fifth live call site with an argument. **The safety
conclusion still holds** -- the omitted site strips a single character (`#`), which is
unambiguous (a one-character charset is identical to suffix removal, same reasoning already
applied to the two `rstrip("*")` sites) -- but the audit's own stated count (4) does not match
what is actually in the tree (5). This is exactly the failure mode lead asked me to check for:
an audit that sounds exhaustive but has an uncounted blind spot, which in this instance happens
not to matter, but the counting process itself was not as thorough as claimed.

### (b) Regression fixture -- verbatim check and pre-fix failure count -- verified, found a bigger gap than claimed
Confirmed every line-group in `tests/test_module_name_truncation.py::CLUSTER_MODULE_TEXT` is a
byte-exact substring of `src/dist/sei_probe_report.cpu.json`'s `cluster.modules_raw` (checked all
13 tokens individually, then the full gaussian block as one contiguous excerpt -- it matches the
real file byte-for-byte; the 7 other lines are real lines pulled from elsewhere in the same
`modules_raw` dump, not fabricated, though not contiguous with each other -- "verbatim" holds at
the line level, not as a single contiguous block, which the docstring does not actually claim).
Then reverted `strip_module_markers` to the exact original line quoted in HANDOFF
(`tok.rstrip("(default)").strip(":,")`, no more, no less) and ran the file:
```
FAILED (failures=5)
FAIL: test_linda_suffix_survives
FAIL: test_all_linda_variants_survive
FAIL: test_helper_removes_suffix_not_character_set
FAIL: test_only_documented_markers_are_removed
FAIL: test_arbitrary_suffixes_built_from_the_old_charset_survive
```
🔴 **Not 2 failures -- 5.** HANDOFF §44.5 says "fails on the pre-fix code (2 failures, exactly the
`.linda` assertions)." Only 2 of the 5 failures are `.linda` assertions
(`test_linda_suffix_survives`, `test_all_linda_variants_survive`); the other 3 come from
`TestFixIsNotLindaSpecific` and the direct-unit `test_helper_removes_suffix_not_character_set`,
which test `strip_module_markers` directly rather than through `parse_module_avail`. Most likely
explanation (not verified, offered as the plausible account): the "2 failures" revert was run
before `TestFixIsNotLindaSpecific` was added (that class's docstring explicitly says it was added
*after* lead's feedback: *"A fixture with only `c01.linda` would pass with a fix that
special-cases `linda`"*), and the revert experiment was never re-run against the expanded test
file. This is the same shape as ADR-042(b)/(c) -- a revert result reported once and not
re-checked after the test file grew -- just at the level of "which count is reported" rather than
"pycache masks the real state." Restored the file afterward; confirmed clean (`diff` against my
pre-edit checkpoint, 8/8 OK).

### (c) D3 -- constructed the real scenario end to end, in bash, not mocked
Built PATH shims for `module` and `g16` that reproduce the actual site behavior: `module load
gaussian/g16.c01.linda` (and the other two `.linda`/`.linda` candidates) prints `ERROR:105` to
stderr and **exits 0**; only `module load gaussian/g16.a03` actually makes a `g16` binary appear
on PATH. Ran `sei_qc_detect` for real (`source payload/qc_adapter.sh; sei_qc_detect`) with no
Python-level mocking:
```
SEI_QC=gaussian16
SEI_QC_MODULE=gaussian/g16.a03
SEI_QC_MODULE_TRIED=gaussian/g16.c01.linda gaussian/g16.b01.linda gaussian/g16.a03.linda gaussian/g16.a03
```
Confirms: the loop walked all four candidates in order, none of the three exit-0-but-broken
attempts were accepted as success (because success is gated on `command -v g16`, not `module
load`'s exit status), and the working candidate at the end of the fallback chain was correctly
selected and recorded in `modules_tried`. This is exactly the incident shape, reproduced and
shown to now resolve correctly.

### (d) Shipped tarball config -- verified independently
Extracted the actual `dist/sei_pilot_cpu.tar.gz`, read `config/env_paths.json` inside it: default
`gaussian/g16.c01.linda`, fallbacks `g16.b01.linda / g16.a03.linda / g16.a03` -- matches lead's
report exactly. Grepped the full extracted tree for `g16.c01.lin`, `g16.b01.lin`, `g16.a03.lin`
(the truncated, non-existent names) excluding `.linda` matches: found exactly 3 hits, all inside
Python/bash comments explaining the historical bug (`sysprobe.py:481,484`,
`payload/qc_adapter.sh:30`), none in active code or config. Confirms lead's claim.

### D4 -- other tests whose expected values may have been derived from our own code (named, not fixed)
Per lead's explicit request, named without fixing:
1. **`tests/test_g16_adapter.py`'s `LOG_OK`/`LOG_ROUTE_ERROR`/`LOG_MEMORY_ERROR` fixtures** --
   structurally the same risk shape as D4: we do not have a Gaussian16 instance to check parser
   output against, so the fixtures are hand-typed to what we believe the real format looks like,
   and the "expected" parsed values (SCF energy, imaginary-frequency count, convergence flags)
   are checked against our own understanding rather than an independently obtained real log. The
   file's own docstring already flags this residual risk and names the mitigation (the route
   smoke test on the real cluster) -- so this is a known, tracked risk, not an undiscovered one,
   but it is the closest structural match to D4's failure shape in the current suite.
2. **Documentation staleness, not a live-assertion bug, but the same "say only what is true"
   class of issue lead has flagged three times this round**: `tests/test_gaussian_module_priority.py`
   still has two docstrings quoting the truncated (non-existent) module name after the fix:
   line 7 (`계산 노드 모듈: gaussian/g16.a03, .a03.lin, .b01.lin, .c01.lin`, part of an unrelated
   earlier incident's historical record, so arguably intentional as a record of that incident --
   but it sits directly above the *new* correction note about the `.linda` fix, which risks
   conflating the two incidents) and line 286 (`TestConfiguredGaussianModule`'s class docstring:
   `"gaussian/g16.c01.lin"`, while the actual assertions three lines below correctly test
   `"gaussian/g16.c01.linda"`). Named only, not changed, per instruction.

I did not find a third instance beyond these two. This is not an exhaustive audit -- doing that
properly would require authorship history (no `.git` in this checkout), so absence of further
findings here should be read as "not found by structural inspection," not "proven absent."

### The "user-confirmed" laundering check -- other config fields
Checked every config field carrying `confirmed`/`사용자 확인`/`사용자 확정`/`_source` across
`config/*.json`:
```
sizing.json   usable_cores.map {"68":64}   -- "user confirmed: 'compute node is a 68-core system,
                                               only 64 cores used'" -- this quotes the user's own
                                               direct statement about their hardware, not
                                               something we parsed and asked them to rubber-stamp.
accounts.json probe/gaussian/xtb/vasp      -- account-per-software mapping, the user's own naming
              (all "confirmed": true)         scheme; not derived from our parsing.
env_paths.json gaussian_modules.default    -- THIS WAS THE LAUNDERED ONE (already the subject of
                                               D2, fixed this round). Historically labelled
                                               "사용자 확정" while the value had in fact been
                                               produced by our own buggy parser and merely shown
                                               back to the user for a yes/no.
qc_levels.json "_status": "lead 확정"       -- methodology decisions (which functional/basis to
                                               use), not values parsed from the cluster environment
                                               -- a different category, not subject to this risk
                                               (lead is the source of the decision, not confirming
                                               our derived output).
```
Found no second instance of the laundering pattern beyond the one already being fixed this round.
Named per instruction, not changed.

### Temp-dir leak fix -- verified beyond the 3 named files
Ran each of the three files lead named individually with a leaked-dir census before/after
(`test_pbs_script_shape.py` including its module-level `_script` helper used across all 58 tests,
`test_gaussian_module_priority.py`, `test_g16_adapter.py`): all three showed 0 -> 0 for their
respective temp-dir prefixes. Then ran the **entire** standalone suite (743 tests) with a
whole-`/tmp` census of every `sei_*`-prefixed entry before and after: **5 -> 5, net zero.**
Confirms the fix holds at both the targeted-file level and the whole-suite level, not just the
three files named in the report.

### Fact-check -- standalone test count does not match what was reported
```
lead reported: "740 tests OK (skipped=8)"
I measured:    Ran 743 tests OK (skipped=8)          -- reproduced twice, stable, no leftover
                                                          files from my own experiments
gate (8/OK) and source_digest (b8375e9d18326553) both match lead's report exactly.
```
Since `tests/` is outside `pilot_package/` and therefore outside `source_digest`'s scope, the
tree can grow test count without changing the digest -- so this is not evidence that the
delivered artifact differs from what was reviewed, only that the dev-side test count reported
does not match what is currently on disk. Noting the fact plainly per this round's standing
instruction to verify counts rather than repeat them; not treating it as a defect in its own
right absent further explanation.

## Verdict
**PASS**, with two precision corrections to record (per this round's own stated priority --
*"a precise statement of what is and is not true matters more than the finding itself"*):
- the strip/rstrip/lstrip audit count is 5 live call sites, not 4 (conclusion -- only 1 was ever
  wrong -- still holds; the count itself does not),
- the pre-fix revert of the regression test fails 5 assertions, not 2 (the fixture is a stronger
  regression guard than reported, not a weaker one; still a "does not pass" finding to correct in
  the written record).

Neither correction changes the shipping decision: D1-D4 are genuinely fixed, D3's fallback walk
was verified end to end with a real bash reproduction of the site's exit-0-on-failure behavior,
the shipped config matches what was measured, the temp-dir leak fix holds suite-wide, and no
second instance of the "confirmation laundered our own bug into ground truth" pattern was found.
The standalone test-count mismatch (743 vs. 740) is noted as an open fact-check item, not a
blocker.

## critic3 review — follow-up on the RT-1 incident: the "invalid revert that passed" trap — 2026-08-18 (ninth, same `source_digest b8375e9d18326553`, tests/ widened to 743)

**Target**: same source_digest as the previous entry (unchanged -- the additions are test-only,
outside `pilot_package/`). Verified: 743-test count now matches lead's re-measurement; the
`TestFixIsNotLindaSpecific` synthetic names are non-vacuous; both of coder2's revert experiments
(the invalid one and the faithful one) reproduced independently; `strip_module_markers`'s live
body contains no reference to "linda"; the job-side candidate walk re-confirmed with a fresh real
bash reproduction; the login-node/compute-node residual reasoned through and confirmed covered.

### Fixture and synthetic-name check
Confirmed (again, on the current file) that the 13-line `CLUSTER_MODULE_TEXT` fixture contains all
4 gaussian tokens and all 10 legitimate `(default)` tokens matching `cluster.modules_raw`
(re-verified against `src/dist/sei_probe_report.cpu.json` directly, same result as last time).

Checked lead's specific concern -- do any of `TestFixIsNotLindaSpecific`'s 8 synthetic names
(`tool.linda`, `tool.default`, `tool.ault`, `tool.fated`, `tool.deft`, `tool.ude`, `x.lua`, `x.el`)
terminate on the first character under the old bug, making the assertion vacuous? Ran the actual
old-buggy `.rstrip("(default)")` against all 8 directly:
```
vendor/tool.linda   -> vendor/tool.lin   (2 chars stripped)
vendor/tool.default -> vendor/tool.      (7 chars stripped)
vendor/tool.ault    -> vendor/tool.      (4 chars stripped)
vendor/tool.fated   -> vendor/tool.      (5 chars stripped)
vendor/tool.deft    -> vendor/tool.      (4 chars stripped)
vendor/tool.ude     -> vendor/tool.      (3 chars stripped)
vendor/x.lua        -> vendor/x.         (3 chars stripped)
vendor/x.el         -> vendor/x.         (2 chars stripped)
```
None are vacuous -- every one strips 2 or more characters under the old code, so each genuinely
exercises the charset-collision class, not just a coincidental single-character match.

### The "invalid revert that passed" trap -- reproduced both versions myself

**Invalid version** (early `return` for names ending in `"linda"` layered on top of the still-intact
correct marker-loop, exactly as coder2 described self-diagnosing):
```python
tok = (token or "").strip()
if tok.endswith("linda"):
    return tok
changed = True
while changed:
    ...                       # the correct general logic, still present underneath
```
Ran `test_module_name_truncation.py`: **`Ran 8 tests ... OK`.** Confirmed the false negative --
this "revert" proves nothing, because the general logic it was supposed to be replacing was still
doing the real work for every case except the ones that hit the shortcut.

**Faithful version** (the general fix *replaced* with the old buggy `rstrip` plus a naive
`linda`-specific patch -- the shape of a fix someone might actually ship without understanding the
root cause):
```python
tok = (token or "").strip()
if tok.endswith("linda"):
    return tok.strip().strip(":,")
tok = tok.rstrip("(default)")
return tok.strip().strip(":,")
```
Ran the same file: **`FAILED (failures=3)`** -- matches coder2's corrected count exactly:
```
FAIL: test_arbitrary_suffixes_built_from_the_old_charset_survive  (TestFixIsNotLindaSpecific)
FAIL: test_only_documented_markers_are_removed                    (TestFixIsNotLindaSpecific)
FAIL: test_helper_removes_suffix_not_character_set                (TestModuleNameIsNotTruncated)
```
This confirms the general-property tests do their job: a naive `linda`-only patch is caught, and
the earlier "it passed" result was specifically because that first experiment did not construct
the hypothesis it claimed to test, not because the suite is weak. Restored the file after each
attempt; `diff` against a pre-edit checkpoint confirmed byte-identical; suite green again both
times.

### `strip_module_markers` -- confirmed no "linda" reference in the live body
Parsed the function with `ast`, stripped the docstring node, and printed only the executable body:
it iterates `MODULE_MARKERS = ("(default)", "(D)", "(L)")` and nothing else. `"linda"` appears
nowhere in the executable statements (the two textual matches in the file are both inside the
docstring, illustrating the historical bug).

### Job-side candidate walk -- re-confirmed with a fresh, independent bash reproduction
Rebuilt the PATH-shim scenario from scratch (new shim scripts, new temp dirs) and re-ran
`source payload/qc_adapter.sh; sei_qc_detect` for real:
```
SEI_QC=gaussian16
SEI_QC_MODULE=gaussian/g16.a03
SEI_QC_MODULE_TRIED=gaussian/g16.c01.linda gaussian/g16.b01.linda gaussian/g16.a03.linda gaussian/g16.a03
```
Same result as before -- the walk is real and correctly falls through to the working candidate.

### The login-node/compute-node residual -- confirmed covered, not treated as a finding
Traced where each check actually executes: `sysprobe.collect_login()` (software/module inventory,
including whatever `module avail` reports) runs wherever `./run.sh` itself is invoked -- the login
node, per the README's own instruction. `sei_qc_detect`'s candidate walk lives inside
`payload/qc_adapter.sh`, which is sourced *by the submitted job itself* and therefore executes on
the compute node, independently of and without trusting the login-node inventory. Because the
job-side walk re-probes from scratch (checking `command -v g16` after each `module load` attempt,
never the login-node's earlier assessment), a module that looked fine on the login node but isn't
actually usable on a compute node still gets discovered and, if a working fallback exists, routed
around -- at the cost of one ~6s job rather than a silently-wrong plan. This matches lead's
framing exactly: named as an accepted residual, not something requiring a fix, and the job-side
walk does structurally cover it.

## Verdict
**PASS.** Both revert-experiment traps (the earlier count corrections and this "invalid revert
that passed" one) are now on record with faithful reproductions attached. No new gaps found within
this round's scope.

## Status — reconciled, shipping, standing down

Lead reconciled the 740/743 discrepancy: 740 was lead's own stale figure (sent from coder2's first
self-report, before `TestFixIsNotLindaSpecific` was added at lead's request; 743 is correct and
confirmed independently by lead as well as by me). Both count corrections from the previous entry
accepted. `test_gaussian_module_priority.py:286`'s stale docstring (still names the truncated
module name plus the "user-confirmed" framing that motivated D2) is being fixed doc-only by lead
directly; `test_g16_adapter.py`'s `LOG_*` fixtures accepted as a named, already-tracked risk for
next round, not this one's finding.

Standing down until the cluster re-run returns `sei_probe_report.cpu.json`. First task on return:
the P6 numbers (kappa, thread-knee S) -- validate `declared == requested == nprocshared`
(ADR-048's hard gate) and same-system/same-job-type comparability to the RT-1c reference value
before taking either number at face value.

## critic3 flush — end of session, handoff to successor reviewer — 2026-08-18

**Purpose**: this entry is not a verdict recap. It is what exists only in my context and would be
lost otherwise. Read this before the P6 numbers arrive.

### 1. The P6 validation, written as an executable checklist (not carried as intention)

**Why this matters more than any other single check**: P6 is the only item in this package whose
purpose is to measure a unit conversion factor (κ = wall-time ratio vs. the RT-1c reference
machine) and a scaling knee (S = w16/w64). Every other item's core-h number is denominated in that
unit. If κ is wrong, it is not "one wrong number" -- it is the wrong ruler for every other number
in the report, silently. And P6 is specifically the one item that does **not** fail loudly when
its sizing is wrong: P5/P1b hit a 1-core allocation and blow their wall limit (747h/3072h),
dying fast and visibly; P6 hits a 1-core allocation and G16 *oversubscribes* `%nprocshared`
threads onto that one core, runs to completion, and returns a plausible-looking wall time. The
result is data-shaped garbage, not a crash. That asymmetry is the entire reason ADR-048 exists.

**The check, precisely** (`collect_p6()`, `sei_pilot/collect.py:261-300` as of `b8375e9d18326553`):
```python
agree = (declared is not None and declared == requested == nprocshared)
```
This is presented as the invalidation gate. **It is weaker than it looks.** `declared` comes from
the item key (`P6_t16` -> `16`), fixed at plan time, independent of anything that happens on the
cluster. `requested` is `SEI_TOTAL_CORES`, an environment variable **our own submission script
sets**. `nprocshared` is parsed out of the `.gjf` file that our own input generator wrote **using
that same `SEI_TOTAL_CORES` value**. `requested` and `nprocshared` are not two independent
measurements agreeing with each other -- they are the same number, written twice from the same
source. **The only field in the record that is an actual, independent, OS-level measurement is
`cores_observed`** (from `nproc` inside the job, reflecting real cgroup/affinity allocation), and
`collect_p6`'s own `entry` dict carries it (`"cores_observed": rec.get("cores_observed")`,
line 289) -- **but `agree` never reads it.** It is measured and not used. It is the ninth instance
of that exact shape this session has spent the whole round chasing in other files, and it is
sitting in the one function that exists specifically because of that failure class.

⟹ **When the reply comes back, do not accept `valid: true` at face value.** For every P6_t*
entry, independently check `cores_observed == declared_threads` as well. If PBS silently grants
fewer cores than requested (a scheduler quirk, a queue policy, contention) while our own script
still faithfully sets `SEI_TOTAL_CORES` and writes it into `%nprocshared`, `agree` will read
`True`, `valid` will read `True`, and the wall time will be wrong by however many-fold the real
core count differs from the declared one -- exactly the ~16x failure mode ADR-048 was written to
catch, slipping through the specific gate built to catch it, via the one field that gate does not
check.

**The rest of the checklist, in priority order**:
1. `cores_observed == declared_threads` for each of P6_t1/t16/t64 (above -- not enforced by code).
2. `declared == requested == nprocshared`, the check that *is* enforced -- confirm it actually
   ran (i.e. `p6_anchor.json` exists per task, not silently absent -- an absent file makes
   `declared` `None`, which correctly fails `agree`, but confirm you can see *why* it's absent if
   it is, rather than assuming absence itself is fine).
3. `rc == 0` and `status == "done"` for the task feeding κ (t16) -- `valid` already requires this,
   but re-check it yourself; do not trust the `valid` boolean without having looked at `rc` and
   `status` directly.
4. Same-system, same-job-type comparability to the RT-1c reference
   (`P6_REFERENCE_WALL_S = 177.3`, `sei_pilot/collect.py:17`; "[MEASURED] dev box, Ryzen 7800X3D,
   16 threads"). `kappa = by_thread[16] / P6_REFERENCE_WALL_S` is only meaningful if the t16 task
   ran the same system (`li_ec_radical_reactant.xyz`, charge 0, mult 2), same job type (`sp`), and
   same QC level as the reference run. `payload/P6.sh` hardcodes the system/charge/mult/job_type
   (`§R22.10(a)(b)`) specifically so this can't drift -- confirm the reply's `p6_anchor.json`
   actually shows those same values, not just that the code intends to hold them fixed.
5. `S = w16/w64` -- if `S < 1` (64 threads slower than 16), that is a valid, informative result,
   not an error to explain away. Do not let anyone round it toward "must be a measurement
   artifact" without cause.
6. Whether `--ncpus-per-node` or `config/sizing.json`'s `pbs.ncpus_per_node` was used for this
   submission. If it was, confirm `item_cores_are_the_measurement()` (`plan.py`) actually
   exempted the P6 items from the override -- I verified this mechanism works (§37 round), but
   verify it actually fired for *this* submission rather than assuming the mechanism I tested in
   isolation ran the same way in the real submission.

### 2. Checked clean this session -- and what would make each one stop being clean

| # | What I checked | Clean because | Stops being clean if |
|---|---|---|---|
| 1 | `normal` queue = 48h assumption (ADR-052) | User-stated AND `qstat -Qf`-measured, both agree | The site's queue config changes, or a submission implicitly lands in a different queue than `normal` |
| 2 | Tarball round-trip integrity (`packaged_gate`) | `make_package.sh` always runs it before shipping, wired via a meta-test that's in the standard 743-test suite | Someone tars `pilot_package/` by hand, bypassing `make_package.sh` entirely -- nothing catches a manually-built tarball that never went through the gate |
| 3 | `tarfile.open(` discovery criterion | Verified non-fragile, verified `TestBuildGate` doesn't self-match, verified via a third independent scanner | Someone refactors a tarball-opening test to use `tarfile.TarFile(path).__enter__()` or similar instead of `tarfile.open(`, or wraps it in a helper function one level removed -- the literal-substring-in-class-body scan would miss it silently, and there is no test for *that* |
| 4 | Temp-dir leak fix (0->0, suite-wide) | Measured directly, twice, at whole-suite granularity | **Nothing prevents a newly-added test file from introducing a fresh `mkdtemp()` without `addCleanup`.** There is no meta-test enforcing "every `mkdtemp` call site has a matching cleanup" the way `TestBuildGate` enforces "the gate exists and runs after packaging." This fix closed the leaks that existed; it did not close the class of bug. It cost two builds already. |
| 5 | strip/rstrip/lstrip audit (5 sites, 1 historically wrong, now fixed) | Recounted independently across the whole `pilot_package/` tree | **Same shape as #4** -- nothing stops a sixth call site from being added elsewhere with a multi-character charset argument and no audit ever looking at it again. The audit was a point-in-time sweep, not a standing check. |
| 6 | "User-confirmed" config fields not laundering our own output (sizing.json, accounts.json) | Traced provenance of each value; both quote direct user statements about their own systems | If any of these values is ever "refreshed" by re-running our own probe and silently overwriting the config with what we measured, re-labeled as still "confirmed" -- the label would no longer mean what it currently means, and nothing would flag the change of meaning |

**The general pattern in this table**: this round built strong protection for the *specific*
instances of each bug class (module names, README/tarball drift, temp-dir leaks in 3 named
files). It did not, in most cases, build protection against the *next* instance of the same
class appearing somewhere new. That gap is structural, not a specific finding, and it is the
same gap ADR-041/042/043 already named for a different bug class (values getting dropped between
producer and consumer) before `test_producer_consumer.py` closed it generically. The temp-dir
leak and the strip-audit have not received that generic treatment yet.

### 3. Accepted as out-of-scope, not verified

- **`config/env_paths.json`'s vendored xtb version, and every other "we control this ourselves"
  config value** -- not independently checked this session (out of scope; also lower risk, since
  we author these directly rather than deriving them from parsing something external).
- **GPU profile / `collect_p4` field loss** -- flagged the gap (§37 round), accepted "not blocking
  because ADR-037 says the GPU tarball isn't delivered." **I verified ADR-037's text says this. I
  did not verify there is a mechanism that actually prevents `dist/sei_pilot_gpu.tar.gz` from
  being sent** -- it is still built, still exists in `dist/`, still passes its own dry-run smoke
  test in `make_package.sh`. Nothing stops a future session from shipping it by habit. If GPU is
  ever revived, `collect_p4`'s missing fields (`gpu_fix_hint` etc., named in the §37 round, not
  fixed) become live again -- this was already flagged as a "fix together" pair with `pystack.json`
  in the whitelist, so it is at least named in code, not just in my head.
- **`per_file` full-tarball comparison, `source_digest` re-derivation from the deliverable** --
  explicitly out of scope in every round since it was first raised (§41 onward). Never verified
  end-to-end by me. Lead's position (record `source_digest` as the identity, treat
  byte-reproducible builds as a separate future spec) is reasonable but rests on the packaging
  step being trustworthy, which is exactly item #2 in the "P6 validation" section above and item
  #2 in the "checked clean" table above -- both about that same trust boundary from different
  angles.
- **`criteria/p1.py`'s `p1_cost_bias()` magnitude estimates** (`crest_skipped`: -5 to -15%,
  `hessian_recomputed_per_irc`: +10 to +25%) -- I confirmed the *mechanism* delivers these labels
  and warnings correctly (labeled `[ESTIMATE]`, with rationale text). I did not independently
  check whether -5/-15/10/25 are themselves defensible numbers -- that is a chemistry/costing
  judgment call, proposer's or engineer's territory, not something I verified.
- **`qc_levels.json`'s functional/basis choices** ("lead 확정": wB97XD/def2-TZVPPD/SMD etc.) --
  explicitly classified this round as a different risk category from parsed-environment values
  (see the laundering-check section of the previous log entry) and did not audit the chemistry
  itself.
- **Axis 3, LAMMPS, λ_out** -- explicitly told not to touch (proposer's territory this round).
  Untouched.
- **ADR-053's inode-vs-byte finding** -- noticed in passing while reading ADR-052's neighborhood,
  not investigated; it is a real cluster-measurement claim (`files 778,249 / limit 1,000,000`,
  78% consumed) that I have not independently verified and that is outside every scope I was
  given this session.
- **HANDOFF §44.7's "200/200 jobs on 200 distinct hosts, 0 rejected"** -- read and accepted, not
  independently re-derived from raw data this session (I did independently verify the *n_nodes ≥
  200* / `host_metrics` *mechanism* itself much earlier in the session, in the §31 round -- but
  that was checking that the collector doesn't drop the `host` field, not re-deriving this
  specific round's 200/200 figure from the actual reply JSON).

### 4. Technique notes, for reuse (method, not anecdote)

- **Real PATH shims over Python-level mocks, for bash-level behavior.** Where the defect lives in
  a shell script's control flow (D3: does the candidate loop actually continue past a
  `module load` that exits 0 but didn't work?), a Python mock of the *intended* behavior cannot
  expose a bug in the *actual* bash logic. Write real executable shims on `PATH`, `source` the
  real script, run it as a real subprocess, and read the environment variables it sets. This
  caught nothing extra this round (D3 held up), but it is the only way that check would have been
  worth anything if D3 hadn't held up.
- **Run reverts in both polarities.** A revert that goes red proves the wiring exists. It does not
  prove discovery-without-registration, self-containment, or any other *positive* property someone
  claims. Where the claim is "X happens automatically, without needing to register it anywhere,"
  construct a brand-new instance of X, register it nowhere, and confirm it fires in *both* the
  passing and failing case -- passing proves discovery works, failing proves the discovered thing's
  own failure propagates. One polarity alone proves half of what's being claimed.
- **Distinguish a faithful revert from a layered one.** This round's central trap: reconstructing
  "what the old buggy code did" by adding old behavior *on top of* still-correct code, rather than
  *replacing* the fix with the old behavior, produces a revert that changes nothing about the
  cases under test and therefore "proves" the tests are weak when it has proven nothing. Before
  trusting any revert-experiment result, read the diff and confirm the new code path is
  the *only* path reachable for the cases being asserted on -- not an early-exit sitting in front
  of an otherwise-intact correct implementation.
- **AST-parse and strip the docstring before searching for a token.** Grepping raw text for a
  bug's signature (a module name, a function call) will match both live code and the comment/
  docstring that documents the historical bug -- producing false positives in exactly the files
  most likely to discuss the bug in prose. Parse with `ast`, exclude the first `Expr`/`Constant`
  statement of a function/class body, then search only what remains.
- **Recompute claimed counts independently, from scratch, across the whole tree -- not the file
  where the bug was found.** Both count corrections this session (5 vs. 4 strip sites, 5 vs. 2
  pre-fix failures) came from writing an independent script rather than re-running or re-reading
  the existing one. An audit that only looked in the file where the bug lived will not find a
  fifth site in a different file that happens to share the same risky pattern.
- **Before relying on any "already checked, don't re-measure" instruction, spot-check the current
  state anyway.** `source_digest` and the stamp check take seconds to run and caught a live mid-
  edit state at least twice this session (once during the §36-era queue-logic churn, once
  implicitly via the 740/743 count drift). The cost of checking is near zero; the cost of
  reviewing a moving target is a wasted round.
- **Census before/after at the file level *and* the whole-suite level.** A leak fix verified only
  against the specific files named in the report can miss leaks elsewhere; a leak fix verified
  only at the whole-suite level (net zero) can miss a leak in one file that happens to be offset
  by a cleanup surplus in another. Do both.

## Flush complete.

**One-line answer to "what is the most likely way the next reply fools us into accepting a bad
number": P6's `declared == requested == nprocshared` gate will read `True` even when PBS silently
grants fewer cores than requested, because `requested` and `nprocshared` are both written from the
same `SEI_TOTAL_CORES` variable by our own script rather than being independent measurements --
the one field that *would* catch it, `cores_observed` (real, OS-level, from `nproc`), is recorded
in the reply but never checked by the gate that decides `valid`.**

---

## critic8 review — B0 execution package, post-restart verification — 2026-08-19 (`source_digest 4a484eb71ef2b36d`, tarball `src/dist/sei_pilot_cpu.tar.gz` built `2026-08-19T04:22:45Z`)

**Scope**: verification per STATE §0-f (critic7's brief, unconsumed, used verbatim as critic8).
**Artefact verified**: the SHIPPED TARBALL, extracted to `~/.critic8_verify/sei_pilot_cpu/`
(outside `/tmp`, per the standing warning that `/tmp` is reaped mid-session). `BUILD_STAMP.json`
inside the tarball confirms `source_digest 4a484eb71ef2b36d`, matching the freeze point recorded in
STATE §0-i/§0-k. **`src/` was NOT touched, `make_package.sh` was NOT run** (ADR-086 — `src/dist/`
is frozen while `coder8` works; the red suite in `src/` right now is expected mid-refactor drift
from `coder7`'s stopped B-1 edit to `criteria/g16.py`/`criteria/p5.py` and is not reported here).

Method: rather than running the repo's `unittest` suite (which imports from `src/`, currently red
for reasons unrelated to what I was asked to check), I imported each shipped module directly from
the extracted tarball and exercised it with targeted inputs — including constructing the specific
adversarial/degenerate cases the brief and `HANDOFF_CODER6.md` named as unverified. This is
verification of the artefact users actually receive (ADR-057), not of `src/`.

## 판정
FIX-THEN-RUN

## 치명적 (결과가 틀림)
없음 — no item found in this session rises to "a shipped number is silently wrong." The one MAJOR
below is a reporting-layer risk (a correct number sits next to a misleading one), not yet a wrong
number, because B0 unit costs are still unpriced (`b0_plan.size()` returns null, correctly — see
below) and nothing has consumed the pooled field yet.

## 중대 (재현/신뢰성 문제)

- `sei_pilot/bound.py:126-160` `partition()` — **[확인]**. The function returns BOTH a correct
  `per_stratum` breakdown AND a POOLED top-level `convergence_rate` / `n_converged` /
  `convergence_denominator` computed over `in_stats` across every stratum combined, with no
  caveat on the top-level fields themselves (`_denominator_note` explains what's excluded, not
  that the included set spans two populations). I constructed the exact scenario STATE §0-f warns
  about — 19 closed-shell species converging and 4 open-shell species all failing (a plausible
  real B0-D outcome, since B0-D went 19→23 species specifically to add the open-shell stratum
  because open-shell SCF is harder) — and measured:
  ```
  out['convergence_rate']                 = 0.826   (looks fine)
  out['per_stratum']['closed_shell']['convergence_rate'] = 1.0
  out['per_stratum']['open_shell']['convergence_rate']   = 0.0   (complete open-shell failure)
  ```
  → If B0-D's entire open-shell stratum fails to converge, the prominent top-level field a reader
  reaches for first reports "83% converged" and hides that the stratum added specifically to
  measure open-shell cost/convergence produced zero data. I traced the call site
  (`sei_pilot/orbitals.py:405`, inside the function that builds `b0_species_panel`) and confirmed
  `partition()`'s full return dict — including the pooled fields — is embedded verbatim as
  `bound_partition` in the final report output, so this is not a dead intermediate; it reaches the
  artefact (Rule 13). **Fix**: either drop the top-level pooled `convergence_rate` /
  `n_converged` / `convergence_denominator` (per_stratum already carries the correct numbers, per
  the file's own docstring rule "reported PER STRATUM and NEVER POOLED"), or rename them with the
  same field-name-carries-the-caveat convention the rest of this codebase uses consistently
  elsewhere (`dissociation_events_at_uncontrolled_effective_temperature`, etc.) so a downstream
  consumer cannot reach for the unqualified name by accident.
  🔒 Not a Tier-1 finding today only because nothing downstream reads this field yet (B0-D has not
  run) — but it is the exact "silent failure" shape §10 already lists eight instances of, and it
  would become one the moment `bound_partition.convergence_rate` is quoted anywhere.

## 사소
없음.

## 검증 완료 — 요청받은 항목별 결과 (all against the shipped tarball, all `[확인]` unless noted)

- **THE GUARD, unit check (§0-f's 🔴🔴 item)** — `sei_pilot/budget.py:79-119`. Single authority
  `B0_APPROVED_REFERENCE_CORE_HOURS = 15000.0`; KNL figure derived in exactly one function
  (`reference_to_local_core_hours`); `b0_plan.check_against_guard()` calls `budget.b0_guard_spec()`
  with no override parameter, so B0's own guard path cannot have a KNL number typed into it
  directly. I did find a generic `--max-core-hours` CLI override (`cli.py:1031`) that lets a raw
  KNL number be typed for the `cpu`/`gpu` profiles — but `PROFILES = (cpu, gpu)` (`plan.py:41`)
  does not include `"b0"`, and B0 is not wired to submission at all yet (confirmed: no `JobSpec`/
  `wall_h` reference anywhere in `b0_plan.py`), so this override cannot reach B0's guard. Not
  reported as a finding — it predates this session's work and does not apply to the item the brief
  asked about. **36,000 KNL vs RT-1's 21,000 KNL is confirmed the SAME ceiling in different units,
  not a raise** (8,750 reference < 15,000 reference approved) — I did not repeat the lead's earlier
  error here.
- **`b0_plan.size()` / `check_against_guard()` DELIBERATE nulls** — confirmed by direct call:
  `size({})` returns `reserved_core_hours_knl: None`, `complete: False`, all 6 stages listed in
  `unpriced_stages`; `check_against_guard()` on that returns `fits: None`. Matches
  `HANDOFF_CODER6.md`'s DELIBERATELY-ABSENT table exactly. Not reported as a defect.
- **Orbital parser's four traps (ADR-084/085)** — ran the real fixture
  (`tests/fixtures/g16_eigenvalues_p1_ts.txt`, src-side, read-only) through the SHIPPED
  `orbitals.py`: reproduced `n_alpha_occ 25 / n_beta_occ 24 / alpha_homo -0.30464 /
  beta_homo -0.34581 / homo_hartree -0.30464 / somo_hartree -0.30464 / n_singly_occupied 1`
  exactly as ADR-085 records. Then constructed a synthetic RESTRICTED (RKS, no `Beta` block)
  fixture and confirmed `is_unrestricted: False`, `somo_hartree: None`, with the
  no-SOMO-in-a-restricted-log note — the second (RKS) bug ADR-085 describes is fixed in the
  shipped code, not just described in prose.
- **Route truncation (§B-1) / `nosymm` (§B-2)** — confirmed the defect IS present in the shipped
  tarball as documented: `criteria/g16.py:parse_route` (`RE_ROUTE.match`, single-line) reads only
  the line matching `^\s*#[pPnNtT]?\s+`, never a continuation line, which is why the stored route
  is always cut where G16 wraps its echo — consistent with the "always exactly 70 chars" finding.
  No `truncated: true` marker anywhere in `summarize()`'s output. `nosymm` does not appear
  anywhere in the shipped `sei_pilot/` tree (`grep -rn nosymm` = empty) — nothing asserts it is
  absent, nothing asserts it is present; it is simply not built yet. This matches the "MERELY
  UNFINISHED" classification and `coder8`'s current task; **not reported as a new finding** per
  the brief's explicit instruction not to chase the in-flight edit.
- **C-9 / `symmetric_placement_flags` + `coplanarity` (Jacobi degeneracy, §0-f item 3 + ADR-078)**
  — ran both functions against all 5 real shipped geometry files
  (`li_ec_cation`, `li_ec_radical`, `li_ec_radical_reactant`, `li_ec_radical_product`,
  `li_ec2_cation`). All 5 return `flagged: True` with the exact degenerate distance sets recorded
  in ADR-078/`HANDOFF_CODER6.md` C-4 (`2x C@5.2497`, `4x H@5.8456`, `2x O@4.0341` for the four
  180°-axis files; a 6-set fingerprint for the 90.27°-mirror file). Separately fed
  `linalg.jacobi_eigen` a synthetic exactly-degenerate covariance matrix (`diag(5,0,0)`, the
  collinear-molecule case coder6 flagged as untested) — it returns exact eigenvalues `[5,0,0]`
  with an orthonormal eigenvector set and does not fail or return NaN. The collinear case is
  correctly caught by `symmetric_placement_flags` (the axis fingerprint), not by `coplanarity`
  (which correctly reports `is_coplanar: True, max_out_of_plane: 0.0` for a line — a true but
  incomplete statement, and STATE §0-g already documents point-group/collinearity detection as
  explicitly DEFERRED TO PRODUCTION, not claimed done here).
- **`readiness.evaluate`'s single `elif` (§0-f item 1)** — reproduced both polarities directly:
  current code with binary+data `True`/`True` and smoke `None` (unchecked) → `ready = None`
  (correct, matches the brief's concern about `test_binary_and_data_alone_are_never_ready`).
  Simulated the "simplified" collapse a successor might make (`ready = not negative`) on the same
  inputs → `ready = True` — confirms the test surface is load-bearing exactly as described; did
  not need to construct an actual revert since the current code already demonstrates both branches
  are reachable and distinct.
- **`arm2` unwired extended path** — confirmed `b0_plan.py:105` calls `arm2.build_all(species)`
  with `shipped_only` left at its default `True`; the 20-species extended/naive builder is present,
  tested-reachable, but not invoked from the B0 pipeline. Not reported as a defect (deliberate,
  per ADR-078/`HANDOFF_CODER6.md`).
- **`solvent.DESCRIPTORS = {}` / `solvent_line()` raises** — confirmed by reading
  `solvent.py:14-121`: explicit raise (`SolventDescriptorsMissing`), no acetonitrile fallback.
  Matches the DELIBERATELY-ABSENT table; not reported as a defect.
- **Pre-registration (ADR-083) / `n_soft` role (ADR-083)** — confirmed in
  `curvature.py`: `PRE_REGISTRATION["date"] = "2026-08-19"`, `registered_before_any_data: True`,
  the 6,000×-is-synthetic caveat is present verbatim (`"🔴 not_chosen_from_data"`); the panel
  output hard-codes `"primary_verdict": None` and `"🔒 primary_verdict_is_a_judgement_for":
  "proposer"` as literals (not computed), so a revert collapsing it to a boolean would have to
  touch this exact line; `N_SOFT_CURVE_ROLE["role"] = "CALIBRATION ONLY"` with the
  may-not-be-quoted-as-evidence caveat attached. Did not additionally run a revert experiment
  (tests are src-side and src is mid-refactor); structural presence in the shipped artefact is
  confirmed directly.
- **6h tripwire — detection half (C-13)** — `guards.py:591-634` `detect_tripwire_aborts()` reads
  `executions.jsonl`-style records for a `run` append with no matching `finish`/`skip_done`,
  computes a LOWER-BOUND core-h from `now_epoch - started`, and explicitly warns when `cores` is
  missing from the `run` record (pre-R31.2a payloads cannot be accounted for). Matches the
  brief's description. **Prevention half is NOT wired**: confirmed no `JobSpec`/wall-request code
  exists anywhere in `b0_plan.py`, consistent with `HANDOFF_CODER6.md`'s own "NOT STARTED:
  composite route strings · B0 collector wiring · payload/PBS" line — not a new finding, already
  tracked, restated here only because the brief asked me to verify both halves explicitly.

## 확인하지 못한 것
- The three revert-failure families (§F in `HANDOFF_CODER6.md`) — I did not locate the ~90 revert
  harness runs or their outputs to re-audit specific instances (the harness was `/tmp/revert_harness.py`,
  explicitly noted as destroyed by `/tmp` reaping). I instead independently re-derived two of the
  claimed properties from scratch (readiness `elif`, orbital RKS/SOMO) by direct construction,
  which is a different but equally strong form of verification for those two; I did not attempt to
  re-verify the other ~88 reverts and cannot rule out a fourth false-green case existing among them.
- `sei_pilot/guards.py`'s C-10 `cost_probe_violations` and C-12 `fallback_decision` — read but not
  exercised with adversarial inputs this session; out of the time budget for this pass.
- Whether `execution_audit` is the right host for the integrity block (§0-f item 4) — this is
  explicitly marked in the brief as "lead decides after," not a critic judgement call; not
  evaluated.
- `sei_pilot/execlog.py`'s PFL size-trigger / JSON-parseability / host+cores integrity checks —
  read the module docstring only, did not construct a malformed `executions.jsonl` to test it.

## Status
Reporting to lead now, per each-stage-not-batched. Standing by for the next stage (e.g. once
`coder8` reports a green suite and the lead releases a rebuild) or for direction on the bound.py
finding.


---

## critic8 review — STAGE 2, lead-directed re-check of `guards.derived_or_null` against the real cluster report — 2026-08-19 (same tarball, `source_digest 4a484eb71ef2b36d`)

**Instruction**: lead asked me to RE-RUN `guards.derived_or_null` through the real reply
`cpu_machine_pilot_results/sei_probe_report.cpu.json`, not re-argue the earlier closure. I did —
and it surfaces a defect one level up from the question asked.

## 판정 (재개정)
BLOCK on the composite-ratio computation path specifically (see below); FIX-THEN-RUN otherwise
unchanged from stage 1.

## 치명적 (결과가 틀림) — NEW, supersedes stage-1's "없음"

- `sei_pilot/criteria/p1b.py:119-149` `cost_ratios()` — **[확인, reproduced on the real cluster
  reply]**. `guards.derived_or_null` / `guards.unconverged_inputs` (C-1) are never imported by
  `criteria/p1b.py` or by `collect.py`. `cost_ratios()` independently decides which stages are
  "missing" by `v is None` on `core_hours` — **the exact "presence of a cost field, not the
  `converged` field" bug `guards.py`'s own docstring names ADR-065 as the incident that made C-1
  necessary.** The guard exists, is well-documented, and is DEAD CODE with respect to the actual
  r_composite/r_high computation.

  Reproduced directly against `cpu_machine_pilot_results/sei_probe_report.cpu.json`'s real
  `pilots[P1b].rt1b.raw_steps`:
  ```
  li_ec2_cation_A_cheap_optfreq   core_h=282.7378   converged=False
  li_ec2_cation_C_high_sp_on_cheap core_h=10.3289   converged=True
  → rt1b.per_species[li_ec2_cation].r_composite = 1.0365   PUBLISHED, non-null
    (hand-recomputed: (282.7378+10.3289)/282.7378 = 1.0365 — exact match)

  li_ec_cation_A_cheap_optfreq    core_h=5.0311    converged=True
  li_ec_cation_B_high_optfreq     core_h=1.92      converged=False
  → rt1b.per_species[li_ec_cation].r_high = 0.3816   PUBLISHED, non-null
    (hand-recomputed: 1.92/5.0311 = 0.3816 — exact match)
  ```
  → **`r_composite = 1.0365` is the SAME NUMBER ADR-065 named as the incident**: *"r_composite =
  1.0365 was published over a 283 core-h non-convergence."* ADR-065 corrected the narrative
  (removed it from the reported range, `1.14–1.30 (n=2)` instead of including it) but **the code
  path that produces this number was never fixed** — it will reproduce the identical error on the
  next report, and it does not know it did anything wrong: no warning, no null, no `missing` entry
  for the unconverged step (`missing` only flags *absent* core-h, and both A and B here HAD a
  core-h value despite not converging).
  → A second, independently-discovered instance on `li_ec_cation`/`r_high` shows this is not a
  one-off — it is the shape of `cost_ratios()`, not a single bad input.

  I confirmed the guard machinery, if it HAD been wired in, gives the right answer:
  ```
  guards.unconverged_inputs({li_ec2_cation's 3 steps}) = ['..._A_cheap_optfreq', '..._B_high_optfreq']
  guards.derived_or_null(same, compute) = (None, {"null_reason": "...ADR-065, where r_composite =
    1.0365 was published over a 283 core-h non-convergence."})
  ```
  The fix exists, is correct, and is simply never called from the function that would need it.

  **Consequence going forward**: B0-F is explicitly "TS bake-off ... AT COMPOSITE (C-11)" — it
  reuses this composite methodology. Whatever species in B0-F fails to converge at the cheap level
  but produces SOME core-h before failing will get an `r_composite`/`r_high` published as if it
  were a real measurement, with nothing in the output flagging it. This is precisely Tier-1
  ("단위/판정 조용히 틀리게 만드는 것") — a reported ratio silently built on a non-convergent
  input, indistinguishable downstream from a real measurement.

  **Fix**: `cost_ratios()` must check `entry.get("converged") is True` for every stage a ratio
  depends on (A for `u_cheap_core_h`/`r_composite`'s denominator, A+C for `r_composite`'s
  numerator components, A+B for `r_high`), route it through `guards.unconverged_inputs`/
  `derived_or_null` (already built, already tested against exactly this incident), and populate
  `missing`/`note` from non-convergence, not merely absence.

## Status of stage-1's MAJOR (bound.py pooled convergence_rate)
Unchanged, already sent to coder8 directly.

## 검증 완료 — remaining lead-directed items (coder6's five nominations)

- **Item 1 — `readiness.evaluate`'s single `elif`**: already covered in stage 1 (both polarities
  reproduced directly). Restated per lead's instruction to make the category explicit: `ready`
  falls to `None` when smoke is unchecked even with binary+data both `True`; a naive
  `ready = not negative` collapse (the shape a "simplification" would take) flips it to `True` on
  the same input. Confirmed connected, not merely present.
- **Item 2 — `guards.derived_or_null` re-run against the real report**: done above. Result: the
  earlier closure ("ran the real cluster report through it") appears to have exercised the
  function directly/in isolation and found it correct in isolation — which it is. **What was not
  checked, and what I found, is that the real computation path (`criteria/p1b.py`) never calls it
  at all.** Re-running the guard in isolation against real data cannot surface a wiring gap; only
  tracing the actual call graph from `collect_p1b` → `p1b.rt1b_summary` → `cost_ratios` does.
- **Item 3 — Jacobi on a degenerate covariance**: already covered in stage 1 (`diag(5,0,0)`
  synthetic case, exact eigenvalues, orthonormal degenerate eigenvectors, no NaN/crash; confirmed
  `symmetric_placement_flags` — not `coplanarity` — is the mechanism that actually catches the
  collinear/axis case on all 5 real shipped geometries).
- **Item 4 — `execution_audit` as host for the integrity block**: reading only, no ruling (lead's
  call per the brief). `collect.py:82-124`: `execution_audit()` is the pre-existing per-collector
  double-execution auditor (duplicate `stage_events.jsonl` runs), called identically from every
  one of the 4 collectors I found calling it (`collect.py:240,491,522,560`) with its `warnings`
  already flowing into `pilots[].warnings[]`. The `executions.jsonl` integrity block
  (`execlog.audit`) is attached to it via one call (`integrity = execlog.audit(...)`) with the
  stated rationale that piggybacking avoids a second wiring path that could drift from the first
  (the same reasoning R31.2a used for `host`/`cores`). Tradeoff for the lead to weigh: the
  integrity block is reachable uniformly and free of a second mechanism, at the cost that its name
  (`execution_audit`, about duplicate execution) does not obviously advertise that it also carries
  `executions.jsonl` line-format integrity — a reader specifically looking for "where is the PFL
  size-trigger / JSON-parseability check" would not find it by name.
- **Item 5 — the three constants, declared once**: `SIZE_TRIGGER_FRACTION = 0.75`
  (`execlog.py:48`, referenced twice more by name, never re-literalled) and
  `COPLANAR_TOL_ANG = 0.10` (`guards.py:62`, referenced by name at both its two call sites,
  `guards.py:306,353`) are each declared exactly once with no duplicate literal found anywhere
  else in the shipped `sei_pilot/` tree. `OUT_OF_PLANE_KICK_ANG = 0.25` is also declared exactly
  once (`guards.py:71`) — noted for completeness only; per the lead's instruction this one is
  routed to a proposer and I am not adjudicating whether 0.25 Å clears an optimiser step.

source_digest: 4a484eb71ef2b36d (unchanged from stage 1)


---

## critic8 review — STAGE 2 (continued): sharpened bound.py framing, execlog.py adversarial test, guards.fallback_decision adversarial test — 2026-08-19 (`source_digest 4a484eb71ef2b36d`)

## 판정
BLOCK — a second, more severe instance of the same defect CLASS as stage 2's r_composite finding,
found in the SHIPPED, ALREADY-EXECUTED payload script, reproducing the project's own named C-12
incident verbatim in code that will run again.

### Correction to stage-1's `bound.py` MAJOR, per lead's sharpening (both points accepted)
Lead re-derived the finding independently and is right that I under-stated it:
1. **It is not a missing caveat — the function contradicts its own declared contract in the same
   return dict.** `partition()`'s own `_per_stratum_note` says verbatim *"u_cheap and the
   convergence rate are reported PER STRATUM and NEVER POOLED,"* and the docstring opens with
   *"the three groups that must never be averaged together"* — and the SAME dict, ten lines later,
   ships `"convergence_rate": n_conv / len(in_stats)`, pooled. This is the SAME SHAPE as the
   route-truncation defect (`"freq"` absent from a route whose log yielded 27 frequencies — "the
   report refutes its own field"). **Third instance of this exact class now on record**, and the
   class — not the instance — is what should travel forward: a field's own neighbouring text can
   contradict the field, and nothing currently checks a report against its own stated contract.
2. **The adjacent `_denominator_note` makes it worse, not better.** It sits directly on the pooled
   field and correctly explains a DIFFERENT axis (unbound/tripwire exclusion), so a reader sees a
   red-flagged note attached to the number and reads "this has been thought about" — §0-h's
   ①-then-② pattern exactly, where the eye stops at the caveat that exists rather than checking
   for the one that is missing. An uncaveated pooled number would have been safer than this one.

## 치명적 (결과가 틀림) — NEW

- **`payload/P1.sh:78-84` — the C-12 incident, still live in the shipped, already-executed
  script.** `[확인]`. `guards.fallback_decision()` (C-12) exists, is correctly built, and — I
  tested it adversarially — reproduces the historically-named incident exactly: `exit_ok=True`
  with one failed acceptance check still gives `fallback_fires=True`; `exit_ok=False` with all
  acceptance checks passing gives `fallback_fires=False` ("exit status was not used to decide,"
  confirmed); an unevaluated (`None`) acceptance check falls toward firing, not toward accepting;
  an empty acceptance dict fires with the exact "conditioned on nothing" warning. **The guard
  itself is correct.**

  🔴 **It is never called from anywhere.** `grep -rn "fallback_decision" sei_pilot/*.py` outside
  `guards.py` itself returns nothing. And the actual decision of whether QST2's TS search falls
  back to a single-ended `opt=(ts,calcfc)` search is made in `payload/P1.sh:79`:
  ```bash
  if ! grep -q "Normal termination" "$TS_LOG" 2>/dev/null; then
    echo "[P1] QST2 가 정상 종료하지 않았다 → 단끝단 opt=(ts,calcfc) 로 폴백"
    ...
  ```
  This is **exactly** the pre-C-12 logic `guards.py`'s own docstring names as the incident C-12
  exists to fix, word for word: *"the QST2 → single-ended fallback fired only if QST2 FAILED TO
  CONVERGE. QST2 converged — to a saddle of the wrong coordinate — so the fallback never fired and
  302 core-h bought a wrong answer."* `P1.sh`'s fallback is STILL keyed on Gaussian's termination
  string alone — not on imaginary-mode count, not on IRC endpoints, not on any acceptance test.
  There is no bridge anywhere from `guards.fallback_decision` (Python, correct) into the bash
  script that actually runs the job and decides whether to spend more core-h on a fallback.
  I checked the two other `"Normal termination"` greps in the shipped payload
  (`P1b.sh:145,169` SMD→IEFPCM solvent fallback; `qc_adapter.sh:277` smoke-level G1→G2 fallback) —
  both are legitimately status-only decisions with no acceptance-test concept attached to them;
  neither is the C-12 incident. Only `P1.sh:79` is.

  → **This is not hypothetical**: `P1.sh` is the script that already ran RT-1's real
  `ts_qst2.log` — the same log this team spent a full session validating the orbital/eigenvalue
  parser against. If it is resubmitted (RT-2, or reused for B0-F's "TS bake-off, 6 attempts AT
  COMPOSITE, 2 production-sized"), a QST2 run that terminates normally but lands on the wrong
  saddle will pass this `if` silently — precisely as before — and core-h will again buy a wrong
  answer with nothing in the submission-time logic flagging it. Downstream Python analysis
  (C-2's IRC verdict) can still catch it AFTER the fact, but that is a `report`, not a `prevent`,
  and the C-12 constraint was written specifically because catching it after spending the core-h
  is the failure mode, not the fix.

  **Fix**: either (a) have `payload/P1.sh` write enough of an acceptance signal (imaginary
  frequency count from the route's own `freq`, or a cheap post-hoc geometry check) into a file a
  Python step reads before deciding whether the fallback fires, replacing the `grep "Normal
  termination"` gate with a call through `guards.fallback_decision`'s logic; or (b) if a
  submission-time acceptance test is judged too expensive for the shell stage, say so explicitly
  next to the `grep` line and route the fallback DECISION (not just the diagnosis) into whatever
  collector step already reads the log — right now nothing does either.

  🔒 **This is the THIRD instance this session of the same defect class**: a correct, tested
  guard function exists in `guards.py`, cites the specific historical incident it fixes in its own
  docstring, and is never called from the code that actually produces the number/decision it was
  built to protect (stage 1: `bound.py`'s pooled `convergence_rate`, not import-related but same
  "declares a rule, doesn't enforce it" shape; stage 2 first BLOCK: `criteria/p1b.py`'s
  `cost_ratios()` never imports `guards`; this one: `payload/P1.sh` is bash and was never
  connected to the Python guard at all). **The pattern is not "one function forgot to import
  `guards`" — it is that building the guard was treated as equivalent to applying it, three times
  in the same codebase.**

## execlog.py against a malformed `executions.jsonl` (lead-directed, C-10 clause)

`[확인]`, constructed 4 test files (kept outside `/tmp`, in `~/.critic8_verify/execlog_test/`):
```
1 bad JSON line among 3 valid `run` lines   -> fallback_trigger_fired=True, unparseable_count=1,
                                                unparseable_line_numbers=[3] (correct 1-based index),
                                                reason text names "no severity threshold"
0 bad lines, file well under the size trigger -> fallback_trigger_fired=False   (negative polarity)
file forced past size_trigger_bytes() (4,948,780 B > 3,145,728 B) with 0 bad lines
                                             -> fallback_trigger_fired=True, correct byte counts
                                                and percentage in the reason text
```
**One bad line is confirmed sufficient** — no severity threshold, as pre-registered. Both trigger
conditions (size, unparseable line) fire independently and correctly, and the negative case does
not fire. This satisfies the specific ask.

⚠ **Secondary observation, not by itself a defect given current scope**: `grep -rn
"fallback_trigger_fired\|FALLBACK_REMEDY" payload/*.sh sei_pilot/*.py` outside `execlog.py` finds
nothing — nothing in the shipped tree currently reads the fired flag to actually switch
host-recording to per-task files; the field is detection/reporting only. Given `payload/PBS`
submission wiring for anything that would need to make this switch is itself `NOT STARTED`
(`HANDOFF_CODER6.md`), I read this as scope, not defect — flagging so it is not silently assumed
"and also enforced" the way `derived_or_null` was.

## `guards.fallback_decision` and `guards.cost_probe_violations` adversarially

`fallback_decision`: 5 constructed cases (the actual historical incident replayed —
`exit_ok=True` + one failed acceptance check; `exit_ok=False` + all acceptance passing; one
unevaluated/`None` check; empty acceptance dict; `acceptance=None`) — **all 5 behave exactly per
the C-12 rule as documented.** The function itself is correct; see the BLOCKER above for where
that correctness fails to reach the artefact.

`cost_probe_violations`: **not reached this stage** — ran out of budget after the `P1.sh` finding,
which took priority. Listed under "not verified" below, not silently dropped.

## 확인하지 못한 것 (재확인, stage 2 종료 시점)
- `guards.cost_probe_violations` — read but not adversarially exercised.
- The ~90 hand-run reverts from `HANDOFF_CODER6.md` §F — lead directed NOT to rebuild these for
  stage 2; still unaudited beyond the 3 self-reported families.

source_digest: 4a484eb71ef2b36d (unchanged)


---

## critic8 review — STAGE 3: scope correction, 4-collector reach-by-execution, `cost_probe_violations` — 2026-08-19 (`source_digest 4a484eb71ef2b36d`)

## 판정
BLOCK — unchanged from stage 2, now WIDER in scope than stage 2 stated (see correction below),
plus one further confirmed-live instance of the same class (`cost_probe_violations` / P1).

### (a) SCOPE CORRECTION to the STAGE 2 `r_composite`/`r_high` BLOCKER — lead is right, I was wrong
My stage-2 report said B0-D "doesn't touch this code." **That was true only because B0 collector
wiring is currently unwired, and it is on `coder8`'s own task list.** `b0_plan.py:128-130` names
arm 3 explicitly: `{"stage": STAGE_DFT_HIGH, "arm": 3, "note": "r_high, from ARM 1's conformer"}`,
and STATE's own arm list reads *"(generated conformers / idealised control / r_high)"* —
**B0-D's arm 3 IS `r_high`.** The moment collector wiring lands, arm 3's output flows through the
same unguarded `cost_ratios()`/`_ratio()` path already shown to publish a ratio over a
non-converged input. **The BLOCK covers B0-D arm 3 and B0-F equally, not "the composite path
only."** Correcting this entry so it is not read as "B0-D is clear."

### 🟢 Additional confirmation (lead's, adopted): ADR-065's own numbers ARE the unguarded ones
`rt1b.per_species` publishes `r_composite ∈ {1.0365, 1.142, 1.3004}` and
`r_high ∈ {0.3816, 1.5284}`. ADR-065's hand-derived VALID sets are `r_composite = 1.14–1.30 (n=2)`
and `r_high = 1.5284 only (n=1)`. **The two values ADR-065 excluded by hand-derivation are
precisely the two values the code publishes unguarded** (`1.0365` and `0.3816`). ADR-065 was a
human doing C-10/C-1's job manually, once, by inspection, on one report. Nobody will repeat that
by hand for B0-F's larger batch — which is the entire reason a guard was built, and the entire
reason it mattering whether the guard is wired is not academic.

### 🔒 THE CLASS (lead's framing, recorded because the class outlasts the instance)
```
check that ran     : "guards.derived_or_null exists, is correct, and is well-tested in isolation"
property claimed   : "derived quantities are guarded against non-convergence"
```
Same shape as RT-1's Rule 20 loss (*"a gaussian-ish string exists in `modules[]`"* ⟹ *"G16 will
run"*) — applied here to a GUARD instead of a CAPABILITY. A guard's existence and its reach are
different properties. This project has now paid for that distinction twice, and (see below) I
found a fourth live instance of the same shape while completing stage 3.

### Why it survived undetected until now (lead's finding, adopted)
`li_ec2_cation_B_high_optfreq` has `core_hours=None` **and** `converged=False` — its `r_high` came
out `None` via the `missing` path, for the WRONG reason (absence, not non-convergence). **The
existing mechanism catches non-convergence by accident whenever the failed step also failed to
record cost, and misses it whenever the step burned cost and still did not converge.** A partial
guard that fires often enough to look like it works is why nobody noticed — and it means "extend
`missing` to be more careful" is the wrong prescription; `missing` is answering a different
question (presence) than the one that matters (convergence), and conflating them is what caused
this in the first place.

## (b) `execution_audit` reach, proved by EXECUTION not by reading call sites (lead's condition on accepting item 4)
`[확인]`. Built a `Store` fixture (`state.py`) with `mark_done()` on each of the 4 keys and a
malformed `executions.jsonl` (one bad JSON line) written into each collector's real `job_dir`, then
called `collect_p1`, `collect_p1b`, `collect_p3`, `collect_p5` **directly, end to end** — not by
reading the call sites:
```
P1  -> log_integrity.fallback_trigger_fired=True, unparseable_count=1,
       reached execution_audit.warnings[]=True, reached res.warnings[]=True
P1b -> same
P3  -> same
P5  -> same
```
All 4 collectors independently execute the audit and correctly surface the fired flag into both
the field consumed by code and `warnings[]` consumed by a human (Rule 13, both required). This is
a REAL reach proof, not a proxy claim — the earlier "called identically from 4 collectors" was a
call-site reading and the lead correctly flagged that as the same shape of claim the BLOCKER just
punished; this supersedes it with an executed one.
⚠ Noted for completeness, not a defect: `collect_p6` and `collect_p4` do **not** call
`execution_audit` at all (confirmed absent from both function bodies). Not investigated further
this stage — P6/P4 may have a different telemetry shape (single job vs. array) that makes the
per-task integrity audit inapplicable, but I did not verify that; flagging as unconfirmed rather
than asserting it is fine.

## (c) `execlog.py` malformed-line test — already completed and logged in the prior "STAGE 2
(continued)" entry (one bad line sufficient, both trigger conditions independently confirmed,
negative polarity confirmed). Not repeated here; referenced per the lead's numbering so it is not
read as skipped.

## (d) `guards.cost_probe_violations` adversarially — 🔴 A FOURTH LIVE INSTANCE OF THE SAME CLASS

`[확인]`. 7 constructed cases (clean probe, the literal RT-1 incident replayed —
`status='fail'` — chemical-verdict-key smuggling, non-empty `criteria`/`fail_reasons` each alone,
empty dict, `None`, and a combined multi-violation case) — **all 7 behave exactly as C-10
specifies.** The function itself is correct, same as `fallback_decision` and `derived_or_null`
before it.

🔴 **`grep -rn "cost_probe_violations" sei_pilot/*.py sei_pilot/criteria/*.py` outside `guards.py`
returns nothing — never called.** And `criteria/p1.py:265` still does exactly the thing C-10's own
docstring names P1 as one of its four founding instances of: `status = "pass" if passed else
("undetermined" if undetermined else "fail")` — a binary/ternary chemical verdict assigned
directly inside what the constraint calls a cost/convergence probe.

**Ran the guard, as built, against the REAL shipped P1 pilot result** —
`cpu_machine_pilot_results/sei_probe_report.cpu.json`'s `pilots[P1]`, the same report this whole
review has been drawing from:
```
P1.status = "fail"          (non-cost-probe status)
P1.criteria = {...}         (non-empty)
P1.fail_reasons = [...]     (non-empty)
guards.cost_probe_violations(pilots[P1])  ->  3 violations, all three of C-10's named categories
  fired at once, on the CURRENT shipped artefact, today.
```
This is not a constructed edge case — it is the live state of the report already in the repo.
`ADR-066` already tells readers not to trust P1's verdict for a *different* reason (the QST2
geometry precondition violation), which has been masking the fact that the CODE still manufactures
one. The two problems are independent: ADR-066 is about the verdict being wrong; this is about a
cost probe being architected to render a verdict — chemically right or wrong — at all.

**Severity call, left to the lead**: I am not marking this a third BLOCKER outright, because
`ADR-066` already instructs the team not to read P1's verdict as chemistry, which mitigates
today's actual harm — but the CODE-level conflation C-10 was written to eliminate is still fully
present and will reproduce in any future P1-shaped probe (a re-run, or a differently-named S3
probe built the same way) with nothing catching it. Recording as a fourth confirmed instance of
"guard built citing the exact incident, never wired to the code that produces it," alongside
`bound.py` (stage 1), `criteria/p1b.py` (stage 2), and `payload/P1.sh` (stage 2 continued).

## 🔒 Systemic pattern across all four, worth a single fix rather than four
Every instance is a `guards.py` function that (1) exists, (2) is correct under adversarial testing,
(3) cites the specific historical incident it fixes in its own docstring, and (4) has zero callers
outside `guards.py`. A single audit pass — grep every `guards.py` public function name across
`sei_pilot/*.py`, `sei_pilot/criteria/*.py`, and `payload/*.sh`, and require at least one caller
outside `guards.py` for every C-N-labelled function — would have caught all four at once and would
catch the next one before it ships. Suggesting this to `coder8` as the actual fix, not four
separate patches.

source_digest: 4a484eb71ef2b36d (unchanged)


---

## critic8 review — STAGE 3b: THE REACH INVENTORY, all 13 (+1 corrected) unwired guards, by execution — 2026-08-19 (`source_digest 4a484eb71ef2b36d`, `src/` now at `d0cd2778b031a214` per lead — dist/ still frozen, this review is against dist/ throughout)

## 판정
BLOCK — unchanged, now with a THIRD confirmed-live instance, and it is the most severe of the
three: it corrects ADR-090's own reach sweep and shows C-2 unenforced on the P1 pipeline.

## 🔴🔴 CORRECTION TO ADR-090's WIRED(3) LIST — `irc_verdict` is NOT wired

`[확인, by execution]`. ADR-090 lists `irc_verdict` as one of 3 WIRED guards. **It is not.**
`grep -rn "irc_verdict" --include="*.py" .` (both the tarball and the current `src/`, digest
`d0cd2778b031a214`) matches exactly two lines: the function's own `def` in `guards.py`, and
`criteria/p1.py:283`:
```python
"irc_verdict": ir.get("verdict"),
```
This is a **dict key literally spelled `"irc_verdict"`**, whose value is `ir.get("verdict")` —
`ir` is the return of `criteria/p1.py`'s OWN, separate `evaluate_irc()` function (graph-based
endpoint-distinctness classification, vocabulary `same`/`undetermined`/`distinct`), **not**
`guards.irc_verdict`'s return (vocabulary `ok`/`indeterminate`, built specifically so `fail` is
never emitted for an IRC that didn't run properly, per C-2). **The grep that produced ADR-090's
WIRED(3) matched a same-spelled dict key, not a call.** This is Rule 19 (*"a checker that names
its targets by a token it must itself contain will match itself"*) landing on the audit that was
built to catch exactly that class of error.

### The consequence, demonstrated by execution, not asserted
`evaluate_irc()` never checks `normal_termination`, `IRC_MIN_POINTS` (5), or `IRC_MIN_DESCENT_EV`
(0.05 eV) — the three explicit clauses of C-2. It only compares the LAST frame of whatever
trajectory it is given. Constructed a synthetic IRC pair, 2 frames each direction (`n_points=2`,
**below** `IRC_MIN_POINTS=5`), forward ending intact (CO2) and reverse ending fully dissociated
(3 separate atoms):
```
ir = criteria.p1.evaluate_irc(fwd_2frames, rev_2frames)
-> irc_endpoints_distinct: True, verdict: "distinct", passed: True, n_frames_forward: 2
```
**A 2-point trajectory with no termination or descent check produces `passed: True`.** Fed into
`evaluate_p1`, this directly drives `status = "pass"` — **a full chemical TS verdict, from an IRC
that would fail all three of C-2's clauses**, with `guards.irc_verdict`/`irc_direction_ok` never
consulted anywhere in the call chain. C-2 exists specifically to prevent an under-run IRC from
producing a verdict at all (*"the TS is wrong" and "the IRC did not run" must not share an exit
code* — ADR-066). **It is not enforced in the code that computes P1's actual `status` field.**

**On the real data**: RT-1's actual `pilots[P1].detail.irc` has `n_frames_forward=1,
n_frames_reverse=1` — also far below 5 — and happened to classify as `verdict: "same"` /
`passed: False`, so the missing point-count check did not change THAT run's outcome (it failed
for the unrelated, already-documented reason of comparing the TS with itself, ADR-065). **That is
coincidence, not protection** — my synthetic case shows the same code path returns `True` the
moment the truncated endpoints happen to look different, which a genuinely short-but-real IRC can
do easily (e.g. two directions heading toward visibly different fragments after only 2-3 steps).

🔒 This is the most severe of the three confirmed-live instances this session: **it is the guard
built in direct response to the P1/ADR-066 incident, in the script that already produced the real
`ts_qst2.log`/`irc_forward.log`/`irc_reverse.log` this whole review has been drawing from, and it
is not reached** — masked from a grep-based reach sweep by a coincidentally-matching field name.

## THE REACH INVENTORY — all 16 `guards.py` public functions, classified by EXECUTION

```
FUNCTION                    STATUS   EVIDENCE
------------------------------------------------------------------------------------------------
derived_or_null             (A)      criteria/p1b.py:119-149 cost_ratios() exists, computes
  + unconverged_inputs                r_composite/r_high from core_hours presence only, never
  (internal helper of                 imports guards. CONFIRMED by execution against the real
  derived_or_null, same fate)         report (STAGE 2). Consumes: RT-1 historical AND B0-D arm 3
                                       (b0_plan.py:128-130) AND B0-F once collector wiring lands.

irc_verdict                 (A)      🔴 CORRECTED FROM ADR-090's "WIRED". criteria/p1.py's
  + irc_direction_ok                  evaluate_irc()/evaluate_p1() exists, computes P1's actual
  (internal helper,                   `status` field, and never calls guards.irc_verdict. CONFIRMED
  same fate)                          by execution: synthetic 2-frame (below IRC_MIN_POINTS=5)
                                       trajectory yields passed=True. See correction above.

fallback_decision            (A)      payload/P1.sh:78-84's QST2 fallback exists, decides purely
                                       from `grep "Normal termination"`. CONFIRMED by reading +
                                       adversarial test of the guard showing the guard itself is
                                       correct and unused (STAGE 2 continued).

cost_probe_violations        (A)      criteria/p1.py:265 exists, assigns `status =
                                       "pass"/"undetermined"/"fail"` directly -- the literal
                                       conflation C-10 names P1 as one of its four founding
                                       instances of. CONFIRMED by execution against the real
                                       shipped P1 pilot result: fires all 3 violation categories
                                       today (STAGE 3).

require_ts_precondition      (A)      payload/P1.sh launches `ts_qst2` (lines 67-72) with NO
  + ts_precondition                    precondition check of any kind immediately before it --
  + endpoint_report                    confirmed by reading lines 55-72 directly: the block
  (internal helpers,                   between the CREST stage and the QST2 submission contains
  same fate as their only              no imaginary-frequency-of-endpoints check, no optimisation-
  entry point)                         status check. The consumer (P1.sh's TS launch) EXISTS and
                                       skips the precondition entirely. C-8 (lead's finding,
                                       independently confirmed here by reading the exact lines).

symmetric_placement_flags    WIRED    conformers.py:640, `guards.symmetric_placement_flags(atoms,
                                       centre=centre)`. Confirmed present; detection only (see
                                       perturb_out_of_plane below for why that is not itself a gap).

coplanarity                  WIRED    called from perturb_out_of_plane (internal) AND from
  + heavy_atoms                        ts_precondition (internal, itself unwired -- see above).
  (internal helper)                    Directly exercised in STAGE 1 against all 5 real shipped
                                       geometry files; confirmed reachable independent of
                                       ts_precondition's own wiring status because
                                       perturb_out_of_plane is a plain function, callable directly.

perturb_out_of_plane         (B)      Zero callers, internal or external. NOT a new defect:
                                       matches STATE §0-g's own declared status --
                                       "NOTHING IS PERTURBED... instrumentation only," and C-9's
                                       corrective action is explicitly DEFERRED TO PRODUCTION
                                       (point-group detection + perturbation). Must not be wired
                                       without: the production geometry-perturbation step for arm 1
                                       conformer generation, not yet started.

tripwire_record               (B)      Zero callers. `bound.py:121` already reads a
  + detect_tripwire_aborts             `"TRIPWIRE-ABORTED"` status as one of `partition()`'s three
  + spend_core_hours                   groups -- a ready CONSUMER for the status -- but nothing
                                       PRODUCES that status: `B0_TRIPWIRE_WALL_H` (budget.py:93) is
                                       confirmed not wired to any wall_h request anywhere (no
                                       JobSpec in b0_plan.py, already reported STAGE 1), and no
                                       collector calls `detect_tripwire_aborts` against
                                       `executions.jsonl`. Legitimate (B): must not be written
                                       without B0's collector wiring (`HANDOFF_CODER6.md`'s own
                                       "NOT STARTED: ... B0 collector wiring · payload/PBS").
                                       Distinct from `criteria/cost.py`'s UNRELATED
                                       `LONGEST_STAGE_TRIPWIRE_H=40.0` (the pre-existing, already-
                                       wired P1 longest-stage tripwire) -- confirmed these are two
                                       different mechanisms sharing only the word "tripwire".
```

**Corrected count**: not 13 unwired / 3 wired. **14 unwired (top-level entries: `derived_or_null`,
`irc_verdict`, `fallback_decision`, `cost_probe_violations`, `require_ts_precondition`) / 2 wired
(`symmetric_placement_flags`, `coplanarity`)**, when internal helpers are folded into the fate of
their sole entry point rather than counted separately. Of the 5 unwired top-level entries: **4 are
(A) — a consumer exists today and gets it wrong** (`derived_or_null`, `irc_verdict`,
`fallback_decision`, `cost_probe_violations`, plus `require_ts_precondition`'s consumer,
`payload/P1.sh`, also exists — that makes it 5 of 5 unwired top-level guards are (A), zero are
pure-(B) at the top level). Only the two INTERNAL-ONLY helpers with no consumer anywhere
(`perturb_out_of_plane`, and the `tripwire_record`/`detect_tripwire_aborts`/`spend_core_hours`
trio) are genuinely (B).

🔒 **Every top-level guard this session actually traced to a real consumer turned out to be a
live (A).** The (B) cases are exactly the ones with NO consumer anywhere, existing or not-yet-
built -- consistent with the lead's warning that a (B) today is how an (A) gets created tomorrow
when the wiring is written and the guard is forgotten (`perturb_out_of_plane`'s sibling
`symmetric_placement_flags` already made the jump from B to WIRED once conformers.py needed
detection; nothing yet forces the same jump for the correction step).

source_digest: 4a484eb71ef2b36d (dist/, unchanged and still the artefact under review)


---

## critic8 review — STAGE 4: the 5 uncovered collectors, by execution — 2026-08-19 (`source_digest 4a484eb71ef2b36d`)

## 판정
BLOCK — unchanged, now with a FOURTH confirmed-live instance, and it is the highest-stakes one
found this session: κ, the single dominant variable of the 5-month schedule, has no
double-execution audit and no `executions.jsonl` integrity check, despite the underlying job
producing exactly the telemetry the audit would need.

Note on process: item 1 of this stage (re-classify all 13/14 unwired `guards.py` functions) was
already delivered in full, by execution, in the prior "STAGE 3b: THE REACH INVENTORY" entry —
not repeated here. This entry is items 2–3: the 5 collectors `execution_audit` does not reach.

## 치명적 (결과가 틀림) — NEW, the session's highest-stakes instance

### `collect_p6` — (A). Consumer EXISTS, telemetry EXISTS, audit is simply never called.

`[확인, by execution]`. `payload/P6.sh:51` calls `sei_stage "anchor_t${NP}" sei_qc_run ...` — **the
identical shared mechanism** `payload/common.sh` gives P1/P1b/P3/P5, which writes both
`stage_events.jsonl` (double-execution detection) and `executions.jsonl` (R31.2a host/cores
telemetry) into P6's own job_dir. **The data `execution_audit()` needs is produced. `collect_p6`
never reads it.**

Constructed the adversarial case directly in a real `Store`/job_dir for `P6_t16`:
```
stage_events.jsonl   TWO "run" events for stage "anchor_t16"   (a double execution)
executions.jsonl     one valid "run" line + one malformed line  (a C-10 integrity trigger)
p6_anchor.json        the SECOND (overwritten) run's numbers, wall_s=999999.0 (a corrupted/
                       absurd value standing in for "whatever the last, possibly-bad, run wrote")
```
`collect.collect_p6(store, keys=['P6_t16'])` returns:
```
status: "pass" · tasks[0].valid: True · n_invalid: 0
kappa: 5640.152, kappa_label: "[MEASURED — 이 계·이 잡타입]"
"execution_audit" key: ABSENT from the result entirely
```
**No `duplicate_execution` flag. No `execlog_fallback_trigger` warning. No hint anywhere in the
output that the stage ran twice or that its log has a malformed line.** The ONLY validation P6
performs is `declared == requested == nprocshared` (ADR-048's core-count sanity check), which is a
DIFFERENT property (thread-count agreement) and says nothing about whether the number it validated
came from a clean, single, complete execution.

**Why this is the highest-stakes instance found this session, not an incremental one**: κ is not
one number among many — `05_STATE.md` names it *"단일 임계 경로"* (the single critical path) for
the whole 5-month feasibility judgement, the one figure every other schedule number in
`03_COMPUTE_PLAN.md` is scaled by. A double-executed or corrupted `anchor_t16` measurement moves κ
directly and silently, and every week-count downstream inherits the error with a `[MEASURED]`
label attached, indistinguishable from a clean run.

**Fix**: `collect_p6` should call `execution_audit(store.job_dir(key))` for each of its 3 task
keys (or once with an appropriate `expected_run_lines`) exactly as the other 4 collectors do, and
fold its `duplicate_execution`/integrity warnings into `out["warnings"]` before `valid` is decided
— not merely appended after the fact the way P1 does today (see the pattern note below).

## 검증 완료 — the remaining 4 uncovered collectors, classified by reading their payload's own
telemetry mechanism (execution-level: does the mechanism `execution_audit` reads even EXIST for
this collector's job_dir, checked directly against the payload script, not inferred)

```
collect_p4            (B), legitimately exempt FROM THIS SPECIFIC GAP. `payload/P4.sh` sources
                       only `env_common.sh`, never `common.sh`; contains no `sei_stage` call.
                       Confirmed: no `executions.jsonl`/`stage_events.jsonl` is ever produced in
                       P4's job_dir, so `execution_audit` would have nothing to read even if
                       called. ⚠ Separate, lower-priority observation (not this gap, not
                       investigated further): P4 is a real GPU pilot burning real compute hours on
                       a real G16/GPU job, structurally similar in stakes to P1/P1b, and whether it
                       SHOULD participate in the same double-execution telemetry system used by the
                       CPU-side pilots is a design question outside "does the existing guard reach
                       it" — flagging so it is not silently read as fully resolved.
collect_node_probe    (B), legitimately exempt. `payload/probe_node.sh` reads raw sysprobe text
                       (lscpu/free/df/network/nvidia-smi) from ONE job run; no `common.sh`, no
                       `sei_stage`, no stage-based duplicate-execution concept applies to a single
                       system-inventory dump.
collect_throughput     (B), legitimately exempt, AND already covered by its OWN dedicated
                       mechanism. `payload/probe_throughput.sh` does not use `common.sh`/
                       `sei_stage`; it writes per-task `starts/task_${TID}.json` files instead —
                       this is not a gap, it is precisely the pattern `execlog.py`'s
                       `FALLBACK_REMEDY` text names as the model to switch TO under C-10's
                       pre-registered fallback ("the pattern `probe_throughput.sh` already uses").
collect_queue_wait     (B), legitimately exempt, as the lead's hypothesis suggested. Reads a single
                       `started.json` per queue-wait probe key; no `common.sh`/`sei_stage`; the
                       queue-wait measurement is inherently a one-shot timestamp comparison with no
                       "stage that could re-run" concept.
```

## 🔒 Item 3 — "wired but reached on only SOME paths is (A) too": `collect_p1`'s OWN partial pattern, found while checking this
Not a new function, a note on an existing one already read in stage 3: `collect_p1` (`collect.py`,
line ~240) calls `execution_audit` correctly, but its `duplicate_execution`/integrity warnings
reach `res["warnings"]` only via `res.setdefault("warnings", []).extend(res["execution_audit"]
["warnings"])` — a step AFTER several other fields (`degraded_reasons`, `longest_stage`) are
already folded in, and AFTER `res["status"]` may already have been set to `"fail"` by the trailing
`if st == "failed"` block. The ORDER means `execution_audit`'s warnings arrive, but nothing in
`collect_p1` currently makes a double-execution or a malformed-log finding CHANGE `status` or
`valid` the way P6's ADR-048 cross-check does for thread-count disagreement — `execution_audit`'s
finding is reported, never gated on. Not re-verifying this by a fresh execution run (already
executed in stage 3's 4-collector proof, which confirmed the warning DOES reach `res["warnings"]`
for P1); noting only that "reaches warnings[]" and "affects the verdict" are, once again, two
different properties, and only the first is confirmed for any of the 4 collectors that do call it.
🔒 **Flagging per the lead's instruction to assume there are others, rather than closing the
book on this ADR-090 audit at exactly 5 collectors and 5 (soon 6, with `irc_verdict`) guard
functions.**

source_digest: 4a484eb71ef2b36d (unchanged)


---

## critic8 review — FINAL PASS: confirm the four wirings in the rebuilt tarball, plus the ADR-057/tests-do-not-ship observation — 2026-08-19

**Artefact verified**: `src/dist/sei_pilot_cpu.tar.gz`, extracted fresh.
`source_digest 2042753e1537ee64 · built_at_utc 2026-08-19T06:22:01Z · n_files 91`. Superseded
`4a484eb71ef2b36d`, the digest this entire review was against through all four prior stages.

## 판정
**OK to release the four wirings covered by this pass.** Not a full re-review — scoped exactly to
the lead's four lines, per instruction. The tarball previously reviewed under `4a484eb71ef2b36d`
carried 4 confirmed BLOCKERs; this pass confirms all 4 are fixed in `2042753e1537ee64` by direct
execution against the shipped code, not by reading the diff or trusting the commit message.

## Pass/fail, per line

```
1  criteria/p1.py calls guards.irc_verdict (C-2)                                          PASS
2  criteria/p1b.py calls guards.unconverged_inputs (C-1); 1.0365/0.3816 not producible     PASS
3  collect.py calls execution_audit from collect_p6 (κ); `valid` is GATED                  PASS
4  payload/P1.sh reaches guards.fallback_decision through the heredoc bridge (C-12)        PASS
```

### 1. `criteria/p1.py` → `guards.irc_verdict` — PASS, by AST + execution
AST call-detection (not grep, per ADR-092's own lesson) finds `guards.irc_verdict(...)` at
`criteria/p1.py:309`, inside `evaluate_p1`. The misleading same-spelled dict key is renamed to
`irc_topology_verdict`; the real guard's output is `irc_c2_verdict`, and `c2_ok =
bool(c2["may_render_chemical_verdict"])` is folded into `passed` and into the `undetermined`
branch (never `fail`, per C-2's own rule).

Re-ran the EXACT adversarial case from stage 3b (2-frame IRC trajectory, below `IRC_MIN_POINTS=5`,
forward intact / reverse dissociated — previously yielded `status: "pass"`):
```
status: "undetermined"   (was "pass")
irc_c2_may_render_chemical_verdict: False
irc_c2_verdict.forward_failures: ["normal_termination is None, not True",
                                  "n_points = 2, below the required 5",
                                  "endpoint or TS energy missing -- descent cannot be evaluated"]
```
C-2's three clauses are now checked and all three correctly fail the synthetic case; the verdict
falls to `undetermined`, never `fail`, exactly as C-2 requires.

### 2. `criteria/p1b.py` → `guards.unconverged_inputs` — PASS, by execution against the REAL historical incident data
`from .. import guards` at the top of the file; `_guarded_ratio()` routes every ratio through
`guards.unconverged_inputs(steps_for_guard)` before computing, with "missing" (data-absence) and
"non_converged" (C-1) kept as two distinct, never-conflated reasons for a `None`.

Ran `p1b.cost_ratios()` on the SAME `raw_steps` dict from
`cpu_machine_pilot_results/sei_probe_report.cpu.json` that produced the two incident numbers:
```
li_ec2_cation.r_composite = None   (was 1.0365)   non_converged=['A']
li_ec_cation.r_high       = None   (was 0.3816)   non_converged=['B']
li_ec_cation.r_composite  = 1.3004  (unchanged -- A and C both converged; only B failed, and only
                                     the ratio that actually depends on B nulled, not both)
hco3_anion.r_composite = 1.142, r_high = 1.5284   (unchanged -- fully converged species, matches
                                                    ADR-065's independently hand-derived valid set)
```
**Both named incident numbers are confirmed gone, and the fix is precise** — it nulls only the
ratio whose own numerator/denominator touches an unconverged step, not every ratio for that
species.

### 3. `collect.py` → `execution_audit` from `collect_p6`, `valid` GATED — PASS, by execution against the exact stage-4 adversarial case
Re-ran the identical fixture from stage 4 (`P6_t16` job_dir: `anchor_t16` run twice in
`stage_events.jsonl`, one malformed line in `executions.jsonl`, `p6_anchor.json` reporting
`wall_s=999999.0`):
```
BEFORE (4a484eb71ef2b36d)   status="pass", valid=True,  kappa=5640.152 [MEASURED], no warning
AFTER  (2042753e1537ee64)   status="fail", valid=False, kappa=None,
                             invalid_reason: "[INVALID] execution_audit 가 이 앵커 태스크의
                             무결성을 문제 삼았다 (duplicate_execution=True,
                             unparseable_lines=1)... ADR-091/ADR-092."
```
`valid` now reads `bool(agree and st == "done" and rec.get("rc") == 0 and not integrity_bad)` —
gated, not merely reported (the code comment explicitly contrasts this with `collect_p1`'s
report-only pattern flagged in stage 4 as a still-open, lower-priority item).

### 4. `payload/P1.sh` → `guards.fallback_decision` via heredoc bridge — PASS, by executing the actual bridge script
The `grep "Normal termination"` line is replaced by a `python3 - <<'PY'` block (the same bridge
pattern the script already uses four other times) that parses the log with `criteria.g16`,
constructs an `acceptance` dict (`normal_termination`, `opt_converged`,
`exactly_one_imaginary_mode`), and calls `guards.fallback_decision`; the shell branches on
`fires`/`accepted` printed by the bridge.

Extracted and ran the bridge's own Python verbatim against two constructed logs:
```
log terminates normally, 2 imaginary modes (wrong-coordinate saddle -- the 302 core-h incident
  shape exactly)             -> normal_termination=True, VERDICT: fires    (old code: accepted)
log terminates normally, exactly 1 imaginary mode (genuine TS)
                              -> VERDICT: accepted                          (unchanged, correct)
```
Both polarities confirmed: the fallback now fires on the specific failure mode C-12 exists for,
and does not fire on a genuine TS, using the SAME script file that ships in the tarball.

## 🔴 ADR-057 observation — the one new question, as asked

`tar tzf src/dist/sei_pilot_cpu.tar.gz | grep -c '/tests/'` → **0**, independently confirmed
(matching `coder8` and the lead). This is not new information about this build specifically —
**no build has ever shipped `tests/`, and none should**: it is dev/CI tooling, structurally
distinct from the runtime `sei_pilot/`/`payload/` package the cluster executes. What is new is
that **this round's headline deliverable — the AST-based reach test that is supposed to prevent a
guard-wiring regression from shipping silently again — belongs to exactly that non-shipping
category**, and this is the first round where a critic has been asked to confirm a *test's*
existence/correctness as the primary object of review, rather than confirming runtime behaviour.

**What this means concretely**: I verified all 4 wirings above by re-deriving them independently —
AST call-detection plus direct execution against the shipped `criteria/p1.py`, `p1b.py`,
`collect.py`, and `payload/P1.sh`, which ARE in the tarball. That is a full, ADR-057-compliant
verification of *"is the wiring present in what ships today."* **It is not, and cannot be, a
verification of *"does a regression test exist that will catch it if the wiring is later
reverted."*** That second claim is exactly what the reach test is FOR, and its own file is
structurally guaranteed to never be inside anything I am permitted to inspect under ADR-057,
because ADR-057's mandate is scoped to the artefact a user/cluster receives, and a test is by
definition not that.

**The gap, stated precisely**: `BUILD_STAMP.json` records `source_digest`/`n_files`/`per_file`
hashes — a claim about WHAT was built — and nothing about WHICH TESTS PASSED as a property of that
digest, even though the suite does run as a build gate (per this round's `Ran 1204, OK
(skipped=8) — 0 failures, 0 errors`). A critic reviewing only the shipped artefact of some FUTURE
round has no artefact-level signal that a reach test for these four properties exists at all, let
alone that it is green — they would have to trust a report, which is precisely the practice R21 /
ADR-041 exist to prevent ("a confirmation is independent only if the value did not originate with
us"). If the four wirings above are ever silently reverted while "the suite stays green for every
other reason" (this session's own recurring phrase for exactly this risk shape), the next critic's
only recourse is to re-derive all four by hand from first principles — which is possible, and is
what I just did, but is not what a regression test is supposed to make unnecessary.

**Not proposing a fix** (out of scope for a stand-down pass) — naming the gap as requested:
*artefact-level verification (ADR-057) and dev-time regression-test verification are two different
acts with two different objects, and this project's process has so far only had documents for the
first. A future ADR might record, in the shipped `BUILD_STAMP.json` or an adjacent provenance
file, WHICH NAMED TESTS passed as of a given `source_digest` — not the test files themselves, just
their identity and result — so a critic can at least see the claim even without the content, the
same asymmetry `execlog.py`'s own `fallback_remedy` text already accepts (a field for code, a
warning for a human) applied one level up, to the build itself.*

source_digest of this pass's artefact: `2042753e1537ee64`.
source_digest this entire review was conducted against before this pass: `4a484eb71ef2b36d`.

## Status
All four requested wirings PASS. Standing down for good, per instruction.


---

## critic9 review — ADR-107 독립검증: 클러스터 회신 raw log 대 lead 진단 대조 — 2026-08-20

**대상**: `cpu_machine_pilot_results/sei_pilot_work/{jobs,state,results}/` (읽기 전용, 수정/삭제 없음)
**방법**: `results/sei_probe_report.cpu.json` 파싱 + `jobs/*/executions.jsonl`,
`stage_events.jsonl`, `stages/*.json`, `steps/*/job.log`, `module_load.log`, `state/*.json` 직접 열람.
전부 raw 파일에서 재도출, ADR-107 본문(§ line 8557-8630) 대조.

## 판정
**BLOCK 아님 — ADR-107 의 5개 증상은 raw log 로 전부 재확인됨. 다만 회계 항목(증상4) 의
"≥944 core-h" 하한이 그 자체로 과소평가로 보이며, 이는 별도로 lead 에게 보고할 사안이다.**

### ADR-107 5개 증상 대조

1. **P1b 동시성 — 확인됨.** `jobs/P1b/executions.jsonl`: run×3 (host node2660/2661/2662, 각 cores=64),
   finish 0건. `stage_events.jsonl` 39줄 중 다수 stage 가 "run" 이벤트 2~3회. `steps/li_ec2_cation_B_high_optfreq/`
   에 `Gau-13681/48768/52931.rwf` 3세트가 공유 `job.chk`/`job.log` 에 41,599줄 기록,
   `grep -c "Normal termination"` = **0**. 추가로 `l9999.exe.80s-11909,node2662.btr` /
   `l401.exe.80s-8665,node2661.btr` 존재 — `li_ec2_cation_A_cheap_optfreq` 단계도 최소 2개 호스트가
   건드렸다는 저수준 증거. ADR-107 이 언급한 것보다 오염 범위가 조금 더 넓다(사소, 결론 불변).

2. **P1b 순서 붕괴 — 확인됨, 그것도 정확히.** `stages/p1b_hco3_anion_A_cheap_optfreq.json`:
   `start_epoch 1787127512, end_epoch 1787127681`. `stages/p1b_hco3_anion_C_high_sp_on_cheap.json`:
   `start_epoch 1787127643, end_epoch 1787127670`. ADR-107 의 "512-681" / "643-670" 은 절대 epoch 의
   마지막 3자리였다 — 표기가 불친절하지만 숫자 자체는 정확히 일치. C 가 A 완료 전에 시작해 먼저 끝남 ⟹
   rc=0 stage 도 입력 출처를 특정 못한다는 결론 유효.

3. **P5 전손 — 확인됨.** `jobs/P5/executions.jsonl`: 22 run epoch~1787127429-472, 22 finish
   epoch~1787127466-511 (경과 34~38초), rc=1 21건 rc=0 1건. `jobs/P5/species/` 는 항목 0개.
   `module_load.log` 를 `cat -A` 로 보면 같은 줄 안에 두 메시지가 줄바꿈 없이 이어붙어 있다
   (`...as follows:   Please add PBS option...as follows:`) — 단순 반복이 아니라 진짜 fd 경합의
   증거. `state/P5.done.json`(epoch 1787127510) 과 `state/P5.failed.json`(epoch 1787127511) 이 1초
   간격으로 공존. `tasks.tsv` 는 공유 고정 경로, 최종본 18줄 존재(마지막 쓰기 승자), 그러나
   `species/` 가 비어 있으므로 22개 태스크 중 어느 것도 그 최종본을 온전히 읽지 못했다는 결론과 정합.

4. **회계 322.1 vs 944 — 322.1 은 재도출되나(👇), 944 자체가 과소평가로 보인다.**
   `jobs/P1b/stages/*.json` 12개 파일(13번째 `li_ec2_cation_B_high_optfreq` 는 rc 기록 자체가 없어
   파일 부재)의 `wall_s × 64 cores / 3600` 합계 = **322.08 core-h** — ADR-107 의 322.1 과 일치.
   이건 "최종 승자가 쓴 stage json" 집계이므로 **가장 비싼 중복 단계(끝내 Normal termination 0건으로
   죽은 B_high_optfreq)의 비용이 통째로 빠져 있다** — 322.1 은 심지어 "3배 중복분"도 아니고
   "죽은 채로 끝난 가장 긴 단계"가 안 잡힌 부분합이다.
   🔴 **944 core-h 자체도 직접 측정한 하한보다 낮아 보인다.** `executions.jsonl` 최초 run epoch
   1787127429, `steps/*/job.log` 의 최종 mtime 이 1787176578~1787176678 사이(12개 파일이 ~100초
   구간에 몰려 있음 — 동시 kill 의 흔적)이므로 경과 시간 ≈ 1787176678−1787127429 = **49,249초 ≈
   13.68시간**. finish 이벤트가 0건(=qdel 로 죽을 때까지 계속 점유)이었다는 ADR-107 자신의 서술과
   합치면, 3 노드 × 64 코어 × 13.68 h ≈ **2,626 core-h** 가 mtime 근거의 하한이지, 944 가 아니다.
   ⚠ 이 계산은 "세 노드가 kill 시점까지 계속 점유했다"는 가정에 기대며, PBS 자체 회계 로그(qstat/pbsacct)
   는 이 트리에 없어 완전히 독립적으로는 확인 못 한다 — 그래서 [의심]에 가깝지만, 근거가 파일
   mtime 이라 추측이 아니라 측정이다. **"≥944" 라는 표현 자체(하한이라고 명시)와는 모순되지 않는다
   (2,626 도 944 이상이니 "≥944" 는 여전히 참) — 다만 다음 라운드에 이 숫자를 인용할 때 "944" 를
   중심값처럼 쓰면 실제보다 2.8배 낮게 잡는 것이다.**

5. **감사 사각 — 확인됨.** P5 pilot 항목의 `execution_audit.duplicate_execution` = `false`,
   `stage_run_counts` = `{}`(비어 있음 — sei_stage 도달 전에 죽어서), `links_executed` 에 `"P5"` 가
   정확히 22회. ADR-107 의 서술과 정확히 일치.

### κ = 1.218 (P6) — lead 진단 확인, ADR-048 실패모드 배제됨

`jobs/P6_t1|t16|t64/p6_anchor.json` 3개 전부 `declared_threads == requested_threads == cores_observed
== actual_nprocshared`(1/16/64 각각), `executions.jsonl` 각 1 run + 1 finish, **서로 다른 호스트**
(node2657/2658/2659), `stage_events.jsonl` 각 1줄. 회신 JSON 의 `P6.tasks[*].execution_audit`:
`duplicate_execution: false`, `n_distinct_hosts: 1`, `valid: True` 셋 다. **ADR-091/092 가 지적한
"collect_p6 가 execution_audit 를 안 부른다"는 결함이 이번 아티팩트에서는 이미 고쳐져 있다** — FINAL
PASS 항목 3의 확인과 정합. κ = 216s / 177.3s = 1.2181... → 1.218, 산수도 맞다.
**결론: κ 는 안전하다. array 오염과 무관한 개별 항목 3개이고, 게이트가 실제로 작동했다.**

### P1 (527.822 core-h, wall 8.2614h) — array 아님, 회신 그대로 사용 가능(비용만)

`jobs/P1/executions.jsonl`: run 1(host node3238, cores 64) + finish 1(rc=0) + `P1_c1`/`P1_c2`
skip_done 2건(다른 epoch, 다른 link 이름 — B-1 체인 재실행 가드가 이미 끝난 항목을 다시 실행하지
않고 넘어간 흔적이지 중복 실행이 아니다). `stage_events.jsonl` 3줄 각 1회(ts_qst2/irc_forward/
irc_reverse). breakdown 합 125.7067+134.2933+267.8222 = 527.822, core_hours_total 과 일치, host 1개.
**비용 숫자는 쓸 수 있다.** 화학적 판정(imag −48.4 cm⁻¹, IRC 양끝 동일)은 acetonitrile 이라 어느
방향으로도 U-56 에 계상 불가라는 lead 판단에 **동의** — ADR-106 이 ε 민감도를 `[USER-DOMAIN]` 으로
확정한 이상, 이 배치는 조건이 다른 배치이지 "TS 탐색이 실패한 사례"가 아니다. c10 위반
(`status:"fail"` 이 비용 프로브에 화학적 사유를 얹음)은 회신이 스스로 기록했고 "NOT acted on here"
로 남긴 것도 정확하다 — 지금 처리하면 스코프를 넘는다.

### C-5 거부(`endpoint_prep_reactant`) — 진짜 가드 작동, 다른 이유로 죽은 것 아님

`jobs/endpoint_prep_reactant/solvent_precheck.err` 에 사람이 읽을 수 있는 사유가 그대로 있다:
"5 of 7 SMD descriptors are absent" + 어떤 2개는 구조적으로 0, 어떤 5개는 문헌 추출 실패로
`[UNVERIFIED]`. `terminal_status.json`: `status: solvent_descriptors_missing`, `budget_core_h: 384.0`
인데 `core_hours_total: 0.0` — 예산은 잡혔지만 실제 소비는 0. `module_state: loaded`(G16 자체는
정상 로드됨 — 모듈/바이너리 문제로 죽은 게 아니다). **가드가 의도대로 작동한 사례, 확인됨.**

## 쓸 수 있는 숫자
```
κ = 1.218                         [MEASURED — 이 계·이 잡타입]  P6, array 무관, 감사 클린
speedup_16_to_64 = 1.588           같은 근거
P1 core_hours_total = 527.822 core-h, wall 8.2614 h   [MEASURED, 비용만] — array 아님, 단일 호스트
P1 breakdown (ts_qst2 267.82 / irc_fwd 125.71 / irc_rev 134.29)   같은 근거
endpoint_prep_reactant core_hours_total = 0.0          [MEASURED] — 가드가 정상 작동해 0 소비
```

## 쓰면 안 되는 숫자
```
P1b 의 모든 수 (r/r_composite/r_high, 322.1 core-h 포함) — VOID. 322.1 은 그나마도 죽은 최장
   단계 비용이 빠진 부분합이라 실비용의 하한도 아니다.
P5 의 모든 수 (species_converged=0, level_cost_ratio, budget_verdict 등) — 0/22 태스크가 tasks.tsv
   를 온전히 읽었다는 증거가 없다.
P1 의 화학적 판정 전부 (imag_freq_cm=-48.4, irc_topology_verdict="same", status="fail" 자체를
   "TS 실패"로 읽는 것) — acetonitrile 배치, U-56 어느 방향으로도 계상 금지 (ADR-106).
"≥944 core-h"를 P1b 손실의 중심값처럼 인용하는 것 — 아래 참조. 하한이라는 표현 자체는 참이지만
   raw mtime 근거로는 실측 하한이 ~2,626 core-h 에 더 가깝다.
```

## BLOCKER
없음. 이번 회신을 근거로 P1b/P5 를 VOID 로 두고 P6/κ 를 그대로 쓰는 lead 의 판정 방향에 반박
근거 없음.

## MAJOR
- `docs/01_DECISION_LOG.md:8599` ADR-107 증상4 — **"3 tasks × 64 cores × 4.92h = 944 core-h"의
  4.92h 출처를 이 문서에서도 raw 트리에서도 찾지 못했다.** `jobs/P1b/executions.jsonl` 최초 run
  epoch(1787127429)과 `steps/*/job.log` 최종 mtime(1787176578~678, ~100초 폭으로 군집 — 동시 kill
  정황) 로 직접 재는 경과시간은 **13.68시간**이며, finish 이벤트가 0건(끝까지 점유)이라는 ADR-107
  자신의 서술과 결합하면 3×64×13.68 ≈ **2,626 core-h** 가 mtime 근거의 실측 하한이다. PBS 자체
  회계(qstat/pbsacct) 가 이 트리에 없어 완전 독립 확인은 못 했지만 [의심]이 아니라 파일 mtime
  기반 [확인]에 가깝다. → **다음 라운드에 "944"를 인용할 때 근거가 무엇인지 lead 에게 물어야
  하고, 아니라면 2,626 core-h 로 정정을 제안한다.** ("≥944"라는 하한 표현 자체는 여전히 참이라
  BLOCK 사유는 아니다.)

## 사소
- ADR-107 증상1 이 언급한 삼중 오염은 `li_ec2_cation_B_high_optfreq` 뿐 아니라
  `li_ec2_cation_A_cheap_optfreq` 도 최소 2개 호스트(`.btr` 파일 증거)가 건드렸다 — 결론(P1b 전체
  VOID)에는 영향 없음, 오염 범위 서술만 더 넓혀도 됨.

## 확인하지 못한 것
- P1b/P5 를 죽인 것이 정말 "사용자의 qdel"인지 — 관련 파일(.e*/.o* PBS 로그, epilogue)이 이
  트리에 없어 walltime 킬인지 수동 kill 인지 구분 못 했다(둘 다 13.68h < 요청 walltime 이라 큰
  차이는 아니지만, 사유가 다르면 다음 제출 설계가 달라질 수 있다).
- 4.92h 의 실제 출처(다른 계산식이었을 가능성) — lead 에게 직접 물어야 함.

---

## critic9 정정 — MAJOR("944 core-h 과소평가") 철회, lead 반박 채택 — 2026-08-20

**lead 의 반박을 직접 재확인함**: `state/P5.done.json` mtime = 1787176572, 그러나 파일 내용의
`epoch` = 1787127510(rc=0 시점) — 두 값의 차이가 13.6시간. **파일 내용이 만들어진 실제 시각과
mtime 이 13.6시간 벌어져 있는데, 그 파일은 애초에 38초짜리 P5 태스크가 만든 것**이므로 mtime 은
계산이 끝난 시각일 수 없다. `jobs/P1b/stages/p1b_hco3_anion_A_cheap_optfreq.json` 도 동일 패턴
(mtime 1787176577, 내용의 `end_epoch` 1787127681, 차이 13.6h). `results/sei_probe_report.cpu.json`
(mtime 1787176690)까지 포함해 P5/P1b/P6/최종 리포트가 전부 mtime 1787176572~690 (2분 폭) 안에
몰려 있다 — **이 트리 전체가 한 번의 `cp`/`rsync -a`(타임스탬프 미보존) 로 옮겨진 결과이지,
동시 kill 의 증거가 아니다.**

**철회**: 내가 직접측정이라 믿었던 "13.68시간 / 2,626 core-h" 는 **잘못된 시간 소스(mtime)에서
나온 오염된 계산**이었다. 앞선 리뷰의 MAJOR 항목을 철회한다.

**lead 가 제시한 4.92h 는 재계산으로 확인됨**: `executions.jsonl` 의 `run` epoch(node2660/node2662,
1787127473) ~ `stages/p1b_li_ec2_cation_A_cheap_optfreq.json` 의 `end_epoch`(1787145212, rc=1) =
17,739초 = **4.9275h ≈ 4.92h.** 정확히 일치. 3×64×4.92 = 944 core-h 는 **"stage 마커로 복원 가능한
구간만의 하한"**이라는 lead 의 성격 규정에 동의한다 — `li_ec2_cation_B_high_optfreq`(끝내 정상
종료 못 하고 qdel 로 죽은 단계)는 마커 파일 자체가 없어 그 구간의 실비용은 **이 트리의 어떤
파일로도 복원 불가**(`[UNRECOVERABLE FROM THIS TREE]`, lead 표현 채택)하다는 데도 동의한다.

## 갱신된 판정
- κ=1.218 · P1 527.822 core-h · C-5 0.0 core-h — 그대로 사용 가능(변동 없음)
- P1b/P5 전부 VOID — 그대로(변동 없음)
- 🔴 **"944 core-h" 를 인용할 때는 반드시 "stage 마커 구간만의 하한, 실제 총 소모는 이 트리에서
  복원 불가"라는 단서를 붙여야 한다.** 중심값으로도, 상한 근사치로도 쓰지 말 것.
- 🔒 **프로세스 규칙 추가 제안**: 이 회신 트리(`cpu_machine_pilot_results/sei_pilot_work/`)에서는
  파일 mtime 을 사건 시각 증거로 쓰지 마라 — 전송 과정에서 타임스탬프가 보존되지 않았다. 시각
  증거는 파일 *내용* 안의 epoch 필드에서만 취하라. coder9 패치 리뷰에서도 이 함정을 볼 것
  (lead 지시대로).

## BLOCKER / MAJOR
없음(정정 후). 이전 MAJOR 는 철회됨.

---

## critic9 — 다음 인스턴스 사전조사(임무2 대기 중, coder9 체크리스트용) — 2026-08-20

**방법**: `sei_pilot/plan.py::_all_items()` 전 항목 열거 + `templates/pbs.sh.tmpl` + `payload/*.sh` 각각의
`SEI_JOB_DIR` 사용·`sei_stage` 호출·array-index 참조 여부 grep, 코드 수정 없음.

### 근본 결함의 정확한 모양 (재확인)
`templates/pbs.sh.tmpl:26` — `export SEI_JOB_DIR="{{JOB_DIR}}"` 는 렌더링 시점에 값이 박히고
array 확장 이후에도 모든 task 가 같은 값을 받는다. `payload/common.sh:76` —
`marker="${SEI_JOB_DIR}/stages/${stage}.json"` 는 **stage 이름으로만** 키가 잡히고 task/array-index
로는 안 잡힌다. `payload/probe_throughput.sh:8-9` 만 `PBS_ARRAY_INDEX` 를 읽어 `starts/task_${TID}.json`
으로 경로를 쪼갠다 — 이게 유일하게 안전한 패턴.

### 현재 array 인 항목 (2/3 이 이미 터짐)
```
probe_throughput  array(1,200) cores_per_task=1   payload/probe_throughput.sh:8-9 PBS_ARRAY_INDEX 읽음
                  → 🟢 SAFE (유일하게 올바른 패턴)
P5                array(1,22)                      payload/P5.sh:28,73 — tasks.tsv 고정경로 생성+순회,
                  인덱스 미참조                     → 🔴 BROKEN (ADR-107 확인됨)
P1b               array(1,3)                       payload/P1b.sh:40,108 — targets.tsv 고정경로
                  (3종 결정론적으로 동일 재생성)     생성+전량 순회, 인덱스 미참조 → 🔴 BROKEN (확인됨)
```

### array 아닌 항목 — 같은 관례(`D="${SEI_JOB_DIR}"` + `sei_stage <고정이름>`)를 쓰므로
### **array 로 바뀌는 순간 즉시 같은 결함을 물려받는다**
```
P1                  payload/P1.sh:19          sei_stage 이름: ts_qst2/irc_forward/irc_reverse (고정)
                    지금은 단일잡이라 안전. 여러 TS 시도(다른 초기 추정)를 array 로 병렬화하면
                    3개 task 가 같은 ts_qst2.json 마커·같은 job.chk 를 공유 — P1b 와 동일 결함.

endpoint_prep_reactant   payload/endpoint_prep.sh:46,133,186   sei_stage 이름: endpoint_rough/
                    endpoint_tight (역할별 접미사 없음). SEI_ENDPOINT_ROLE 은 지금 Item 단위로
                    고정 주입(extra_env)돼서 안전하지만, 🔴 **STATE §0-o.5 항목2/§0-m 이 이미
                    "product 끝단"을 다음 스코프로 명시했다.** reactant+product 를 각각 별도
                    Item(P6_t1/t16/t64 패턴)으로 내면 안전하고, **array(1,2)로 합쳐 role 을
                    array-index 로 매핑하면 즉시 12번째 인스턴스가 된다** — endpoint_rough.json
                    마커가 role 구분 없이 하나뿐이라 두 role 이 같은 마커/같은 job.gjf 를 공유한다.
```

### array 로 못 바뀌는(=구조적으로 보호되는) 항목 — "우연"이 아니라 PBS 제약
```
P6_t1/t16/t64    plan.py:317-323 이 이유를 명시: select= 를 task 마다 못 바꾼다(ncpus 1/16/64
                 가 서로 다름). 🟢 이건 **의도가 아니라 우연도 아니다** — array 로 합치려면
                 셋 다 같은 ncpus 를 요청해야 하는데 그러면 P6 존재 이유(스레드 스케일링 S)가
                 없어진다. 즉 이 항목이 array 가 되는 미래 자체가 자기모순이라 이 경로로는
                 안 터진다. (다만 payload/P6.sh 내부에 스레드별 loop 를 넣는 실수는 별개 결함이고
                 이번 조사 범위 밖이다 — 코드 확인 결과 P6.sh 는 단일 anchor 실행만 함, 문제 없음.)

probe_queuewait  plan.py:214, queue_wait_decomposition() — 1/4/16/64 노드를 array 가 아니라
                 submit_entry() 특례로 개별 잡 3개(각 다른 노드 수)로 쪼갠다. 이유가 P6 와 같다
                 (노드 수가 task 마다 다름 = array 불가). 구조적으로 보호됨.

P4 (GPU)         단일 species, manifest 순회 없음(내부 rep=2/3/4/6 크기 스캔은 같은 잡 안에서
                 순차 실행, task 분할이 아님). 지금은 array 아니고 array 로 바뀔 조짐도 코드에
                 없음. 🔴 다만 **GPU profile 이 여러 species 스크리닝으로 커지면(엔지니어링
                 로드맵에 있는 방향) 가장 유력한 다음 array 후보**다 — 지금은 사전조사 대상일
                 뿐 결함 아님.
```

### 결론 — coder9 패치 체크리스트 (임무2 시 대조)
```
[ ] P5.sh, P1b.sh 가 PBS_ARRAY_INDEX/SLURM_ARRAY_TASK_ID 를 읽어 자기 몫만 처리하는가
[ ] 고친 뒤에도 tasks.tsv/targets.tsv 는 "생성 1회 + 각 task 읽기"인가, 아니면 각 task 가
    여전히 매번 재생성(">")하는가 — 후자면 생성 경합은 없어져도(결정론적 동일 내용이라
    운 좋게 안 터졌을 뿐) 다른 입력이면 다시 터질 수 있는 잠복 결함
[ ] sei_stage 마커 이름에 task/array-index 가 들어가는가, 아니면 여전히 종/스테이지 이름만인가
    (이름만이면 "각 task 가 자기 몫만 처리"가 깨지는 순간 다시 충돌)
[ ] SEI_JOB_DIR 자체가 task 별로 갈리는가(예: `${SEI_JOB_DIR}/${TID}`), 아니면 파일명에만
    index 를 넣어 같은 디렉터리를 계속 공유하는가 — 후자면 `stages/`, `steps/` 개수가
    늘어날 뿐 디렉터리 오염 가능성은 남는다
[ ] endpoint_prep_reactant 에 product 를 추가할 때 array(1,2) 로 합치지 않고 별도 Item 으로
    내는지 (합치면 endpoint_rough/tight 마커 role 접미사 필수)
```

---

## critic9 — ADR-107 문서 자체 리뷰 + c10 미조치 건 판단 — 2026-08-20

### 1. ADR-107 리뷰

**file:line 인용 전수 검증 — 전부 정확함.** `templates/pbs.sh.tmpl:26`, `payload/common.sh:76`,
`payload/P5.sh:73`, `payload/P1b.sh:108`, `payload/P1.sh:52,72,124,161`,
`payload/endpoint_prep.sh:133,186`, `sei_pilot/cli.py:588,596,599`, `sei_pilot/plan.py:274,303,317`,
`payload/P6.sh:51`, `payload/probe_throughput.sh:8-9` — 전부 직접 열어 grep 으로 재확인, 오차 0건.

**R-1("모든 P1b 숫자는 VOID") — 결론은 옳고, 근거는 준 것보다 더 세다.**
`stage_events.jsonl` 을 직접 세어보면 13개 stage 중 **정확히 7개가 3회씩** run(문서와 일치),
나머지 6개(hco3_anion 의 C/D_gen/D_builtin, li_ec_cation 의 C/D_gen, li_ec2_cation 의 C)는
run 1회 + skip_done N회 — `sei_stage` 의 "마커 있으면 건너뛴다"가 **이번엔 우연히 작동했다**
(SP 계산이 짧아서 다른 두 task 가 도착하기 전에 끝남). 문서가 인용한 근거(symptom 2, "순서
붕괴로 provenance 를 잃는다")는 **C/D 처럼 A 를 입력으로 쓰는 stage 에는 정확히 맞지만, A·B
자체(직접 3중 오염, `li_ec2_cation_B_high_optfreq` 확인됨)에는 다른 이유(symptom 1, 직접
동시쓰기 파괴)가 적용된다.** `hco3_anion_A_cheap_optfreq` 는 직접 확인해보니 Gau 임시파일이
1세트뿐이고 job.chk/log 도 하나뿐이라 겉보기엔 "깨끗한 단일 실행"처럼 보인다 — **그러나 이건
운이 좋아서 corruption 의 흔적이 안 남았을 뿐, "이 3개 프로세스 중 정확히 어느 것이 이 mol.xyz/
job.gjf 를 마지막으로 덮어썼는지" 는 로그로 증명 불가능하다**(TOCTOU: 마커는 계산이 끝난
후에야 쓰인다). ⟹ **"증명된 오염" 이 아니라 "청정함을 증명 못 함"이 VOID 의 진짜 근거**이고, 이
쪽이 R-1 이 실제로 인용한 근거보다 강하고 포괄적이다. **문서를 고칠 필요는 없다(결론 불변) —
다만 다음에 누가 "B 는 A 에 의존 안 하니 살릴 수 있지 않나"라고 물으면 이 문단을 참고하라고
적어 둔다.**

**R-4("P1 cost 는 사용 가능") — critic9 확인으로 이미 격상됨.** 뒤쪽 "critic9 INDEPENDENT
VERIFICATION" 절이 사실상 🟡→🟢 갱신인데 R-4 라인 자체의 이모지는 그대로다. **오류 아님**(이
문서는 append-only 판정 로그라 뒤 절이 앞 절을 갱신하는 방식이 프로젝트 관례) — 사소, 언급만.

**라벨 — `[MEASURED, FLOOR]` / `[UNRECOVERABLE FROM THIS TREE]` 가 `docs/06_GLOSSARY.md` 의
라벨 규약(§117줄, `[MEASURED]/[ESTIMATE]/[LITERATURE]/[UNVERIFIED PROVENANCE]/[FIXTURE]`)에
없다.** ADR-106 이 만든 `[USER-DOMAIN]` 도 아직 그 목록에 없다 — **이번이 처음이 아니라 이미
한 번 밀려 있던 것**이다. "같은 진실이 두 곳에 있으면 한쪽만 갱신된다"는 이 프로젝트가 여섯 번
넘게 겪은 그 패턴 그대로다. **MINOR — GLOSSARY 갱신 제안**(코드 변경 아님, coder9 담당 아니어도
됨. 문서만).

**빠진 결과 — P3 는 괜찮고, `probe_qw_n64` 는 별건이지만 라벨이 하나 걸린다.**
P3 는 ADR-049 로 이미 계획에서 제거됐다(`skip_reason: "잡이 not_submitted 상태"`, 의도된 상태)
— ADR-107 이 다룰 필요 없음, 동의. `probe_qw_n64` 는 **ADR-107 의 array 결함과 무관한 별개
메커니즘**(config/sizing.json 의 `max_probe_nodes` 캡이 64→16 으로 축소, `state/
probe_qw_capped.failed.json` 에 `reason: "node_count_capped"` 로 깔끔히 기록됨 — 확인함) — 다뤄야
할 이유 없음, 동의. **다만** `results.queue_wait_probe` 의 4번째 항목(`nodes:64`)이
`"status": "still_queued"` 로 나온다 — 실제로는 "영영 제출 안 됐다"(cap 때문에 삭제)인데 표현이
"곧 온다"처럼 읽힌다. **ADR-107 소관 아니고 MINOR**지만, 다음에 누가 이 필드를 보고 64-node
데이터가 나중에라도 채워질 거라 기대하면 안 되므로 어딘가에 적어 둘 가치는 있다.

### 🟢 신규 — U-76(P5 22 vs 18) 원인을 직접 특정함
`PYTHONPATH=. python3 -c "from sei_pilot import plan; print(len(plan._p5_runs()))"` → **22**,
`p5_task_budgets()` 도 22(둘 다 같은 `_p5_runs()` 리스트에서 나옴 — 서로 안 어긋남). 반면
`payload/P5.sh:28` 이 만드는 `tasks.tsv` 는 **종×시드만** 나열해 **18줄**이고(14종+dual-seed
4종), `cheap_level_too` 4종(co2/ec/emc/li_ec2_cation)은 **별도 줄이 아니라 `run_one()` 안에서
같은 줄 처리 중 조건부로 끼워 실행된다**(`P5.sh:69-71`). ⟹ **원인 확정**: `plan.py` 의 array
크기(22, `#PBS -J 1-22`)는 "main/seed2/cheap 을 각각 독립 단위로 센 것"을 전제하는데, `P5.sh` 의
실제 loop 단위(18)는 "cheap 을 별도 단위로 안 센다." **두 표현의 세는 단위 자체가 다르다** — 어느
쪽이 "옳은지"는 스코프 결정(cheap 을 독립 array task 로 쪼갤지 vs 예산표를 18단위로 다시 짤지)
이고 그건 lead 몫이다(coder9 에게 판정 미루라는 ADR-107 자신의 지시에 동의). 다만 **원인은 확정
가능했다** — coder9 브리핑에 이 두 함수/파일 위치를 그대로 건네면 새로 찾을 필요가 없다.

### 2. `c10_cost_probe_violations` — 미조치 건에 대한 판단

**세 선택지 평가**
```
A) 그대로 내보내되 표시만(현재)   장점: 데이터 손실 0, 값싸다. `criteria/p1.py:363-372` 의 주석이
   스스로 "이건 lead 의 스코프 결정이지 구현 결정이 아니다"라고 명시 — coder8 이 이미 신중하게
   내린 판단이고 재고할 필요 없다고 본다.
   단점: `status` 필드가 여전히 이중 의미(비용측정 실패/화학판정 실패)를 진다.

B) status 를 중립값으로 강제 교정 + chemical 필드 분리   장점: 구조적으로 오독을 막는다.
   단점: 이게 바로 그 "구현이 아니라 스코프 결정"이다 — P1 자체가 "TS 완주"를 목적으로 선언된
   항목(plan.py:237 rationale)이라 "cost probe 다"라는 전제 자체가 스코프 논쟁거리다. 코더가
   임의로 하면 방법론 변경을 코더가 대신 내리는 것(이 프로젝트가 금지하는 패턴).

C) 회신 생성 거부   단점: P1b/P5 진단 전체를 함께 날린다(collector 는 리포트 하나를 만든다).
   ADR-092 가 보여줬듯 guard 자체가 67% 오탐 이력이 있다 — guard 오탐 하나로 회신 전체를 막으면
   §0-o.2("raw log 도 같이 받아라")가 성공시킨 바로 그 진단가능성을 잃는다. 기각.
```

**판단: A(현행 유지)가 맞는 선택이었다 — 그러나 배선이 하나 빠져 있다.**
`sei_pilot/cli.py:923 collect_unresolved()` 를 전문 확인했다 — P1 의 IRC 판정 관련 4가지 항목은
`unresolved_for_lead` 로 올라가지만 (line 927-987 전체 확인, `return out` 까지), **c10 관련 체크는
단 한 줄도 없다.** `report.py:176` 의 `unresolved_for_lead` 자체 주석은 *"스크립트가 끝내 측정하지
못한 것 + 판정 대기 중인 규약 = lead 가 여전히 눈이 먼 항목"* 이라고 정확히 c10 이 해당하는
정의를 스스로 내려놓고 있다. **이번 회신에서 실측**: `unresolved_for_lead == []` — c10 위반이
살아 있는데도(criteria/p1.py 자신의 주석이 "lead 의 스코프 결정 대기 중"이라고 써놨는데도) **lead
전용 채널에는 도달하지 못했다.**

🔴 **이게 실제 비용이다**: `c10_note` 는 `pilots[0].c10_note` 안에 중첩돼 있어, lead 가 최상위
요약(`unresolved_for_lead`, `summarize_for_user()`)만 훑으면 못 본다. 이번 라운드는 critic 이 직접
파고들어 잡았지만, **다음 critic 이 없거나 바쁘면 놓친다** — 그리고 그게 정확히 lead 가 물은
질문("다음 사람이 P1 실패를 화학적 실패로 읽는다")의 실제 경로다.

**제안 (코드 변경은 coder9 담당, 여기선 판단만)**:
```
1  A(현행 유지)를 계속한다 — B 는 스코프 결정이라 지금 하면 안 된다.
2  🔴 그러나 `cli.py::collect_unresolved()` 에 c10 체크 한 줄을 추가한다:
     pilots[*].c10_cost_probe_violations 가 비어있지 않으면 unresolved_for_lead 에 항목 추가
     (item="cost probe가 화학 판정을 달고 있다", severity="major",
      action="P1 을 cost-only 로 재설계할지 스코프 결정 필요").
   이건 A 를 B 로 바꾸는 게 아니라 — **이미 존재하는 "lead 대기" 신호를 이미 존재하는 "lead 채널"에
   연결하는 배선 문제**이며, 지금까지 이 프로젝트가 반복해서 찾아낸 그 결함류(존재하지만 안 닿음)와
   정확히 같은 모양이다.
3  이건 ADR-090 §5 canonical order 밖의 항목이라 별도 줄로 다뤄야 한다 — §5 를 다시 쓰지 말고
   lead 가 새 항목으로 등록할 것.
```

### 판정
BLOCKER 없음. 위 세 발견(R-1 근거 보강, U-76 원인, unresolved_for_lead 배선 누락)은 전부 MAJOR/제안
수준이며 지금 당장 아무것도 막지 않는다.

---

## critic9 — 임무2 부분 착수: A-1 안정 파일 4개 리뷰 (`common.sh`/`P5.sh`/`P1b.sh`/`plan.py`) — 2026-08-20

**범위**: `payload/common.sh` · `payload/P5.sh` · `payload/P1b.sh` · `sei_pilot/plan.py` 전문 통독.
**부분 리뷰임을 명시한다** — `config/qc_levels.json`, `payload/qc_adapter.sh`, `sei_pilot/solvent.py`,
`sei_pilot/collect.py`, `sei_pilot/state.py` 는 coder9 가 작업 중이라 안 봤다(lead 지시).
**단, `qc_adapter.sh` 의 딱 두 줄**(module_load.log:50, adapter.json:110 이 `SEI_TASK_FILE_SUFFIX` 를
쓰는지)은 `P5.sh`/`P1b.sh` 가 그 두 파일의 존재를 가정하고 있어서 교차확인 목적으로만 grep 했다 —
그 파일의 다른 로직은 안 봤다.

### 🟢 판정: 이 4개 파일은 설계로서 옳다. BLOCKER 없음. MAJOR 2건은 지금 막을 필요 없지만 lead 판단
### 전에 다음 단계(재제출/제출)로 넘어가면 안 된다.

### 경로 충돌표 (체크리스트 1번)
```
경로                                suffix?           안전한 이유
started.json                        YES (.t<N>)       common.sh:156
state/<key>.done|failed.json        YES (SEI_LOGICAL_KEY 자체가 .t<N>)   common.sh:36-58
executions.jsonl, stage_events.jsonl NO(공유파일)      append-only, host/link 필드로 사후분리 가능
                                                        (R31.2a 주석, 이번 라운드 이전부터 이미 안전)
stages/<stage>.json (sei_stage 마커) NO(공유 dir 안)   🔴 suffix 로 보호 안 됨 — stage 이름 인자
                                                        자체가 유일해야만 안전. P5/P1b 종별 stage는
                                                        태스크당 종 1개만 처리해서 유일 — 간접보호.
tasks.tsv/targets*.tsv               YES (.t<N>)       P5.sh:41, P1b.sh:50,69,71
geom/, geom.t<N>/                    YES               P5.sh:62
species/<tag>/, steps/<tag>/         NO(직접), 간접보호  tag=species id 기반이고 태스크당 종 1개뿐
p5_seeds.json / p5_task_results.json YES(TID 있을 때)   P5.sh:75,177 — TID 없으면(수동) 기존 이름 유지
adapter.json / module_load.log       YES                qc_adapter.sh:50,110 — 교차확인함(로직은 안 봄)
```
`SEI_JOB_DIR` 자체는 **여전히 공유**다(체크리스트 4번 질문 그대로였는데, coder9 는 템플릿이 아니라
`common.sh:49-57` 에서 SEI_KEY/SEI_LOGICAL_KEY 접미사로 풀었다 — 두 스케줄러(PBS/SLURM)에 동시에
걸리므로 템플릿 두 벌을 고치는 것보다 낫다. **구현 형태가 내 예상과 다르다는 이유로는 지적하지
않는다** — lead 지시대로 "성질"로만 판정: 위 표의 모든 경로가 실제로 안 겹치는지 하나씩
확인했고, `stages/*.json` 한 항목만 **suffix 가 아니라 태스크당-종-1개라는 간접 보장**에 기대고
있다 — 이 자체는 지금 유효하지만 아래 MAJOR #1 이 바로 그 간접보장이 흔들리는 지점이다.

### 체크리스트 2-5 결과
```
2  SEI_TASK_KEYS_APPLIED 재진입     안전 — 값 비교라 같은 TID 로 재-source 될 때만 스킵한다.
   (체인+array 동시 사용 경로가 지금 코드베이스에 없음 — P1 만 체인이고 array 아님, P1b/P5 는
   array 이고 체인 아님). 🔒 잠복 취약점: TID 가 프로세스 도중 바뀌는 미래 경로가 생기면
   값비교 가드가 접미사를 중첩 적용(.t3.t5)할 수 있다 — 지금은 발생 안 함, 메모만.
3  P1(non-array) 영향 없음         확인 — SEI_ARRAY_TASK_ID 가 빈 문자열이면 common.sh:50 의
   `[ -n ... ]` 이 거짓이라 SEI_KEY/SEI_LOGICAL_KEY 완전히 예전과 동일.
4  off-by-one/범위밖 TID           둘 다 올바름. P5.sh:53 `1<=idx<=len(runs)`, 벗어나면 exit 2
   →bash exit 5(조용한 0실행 아님). P1b.sh:63 `$TID -lt 1 || -gt N_TARGETS` → exit 5. 둘 다
   1-base→0-base 변환도 정확(P5: runs[idx-1], P1b: sed -n "${TID}p").
5  A-1g(tasks.tsv 여전히 `>` 재생성) 여전히 `>` 다 — 그러나 이제 경로가 태스크별이라 **경합
   자체가 사라졌다.** "매 태스크 재생성"이 문제가 아니라 "고정경로에 재생성"이 문제였다 —
   해소됨.
```

### 🔴 U-76 lead 판정(run 단위=22) 반영 확인
`P5.sh:45` 가 `from sei_pilot.plan import _p5_runs` 로 직접 import, 조건부 cheap 실행(구판의
"같은 줄 안에서 처리")이 사라지고 **실행 1건 = tasks.tsv 1줄**로 통일됨(주석 P5.sh:93-94 가
스스로 이 수정을 설명). `_p5_runs()` 가 유일한 열거원 — 확인.

### 🔴 MAJOR #1 — P1b "마지막 태스크만 stagewise+U-27 을 한다"가 예산 여유 0%인 자리에 얹힌다
`P1b.sh:132-141`: TID != N_TARGETS 인 태스크는 종별 측정만 하고 종료, **TID == N_TARGETS(=3, 즉
22원자 종을 맡은 태스크)만** §11.5 단계별 측정(2 레벨×4 잡타입=8 회 G16 실행, L150-154)과 U-27
스모크(최대 6회 G16 실행 — SMD 3 + IEFPCM 폴백 3, L169-233)를 **추가로** 떠맡는다. 코드 주석
자체가 "[코더 결정, lead 확인 요망]"이라 명시했다 — **그 결정에 동의하되, 구체적 위험을
수치로 짚는다**: `plan.py` 주석(§R26.1/§R27, 이번 라운드 이전부터)이 `P1B_TASK_CORE_HOURS[2] =
3,072 = 64 cores × 48h`, 즉 **정확히 1.00× — 여유 0%** 라고 스스로 적어 놨다. 여기에 8+6=최대
14회의 추가 G16 실행을 얹으면, 22원자 종의 opt+freq/SP 들이 이미 그 예산을 다 쓴 뒤 stagewise/
U-27 이 시작되는 순간 **wall 48h 상한에 걸려 죽을 위험**이 실측 없이 존재한다 — 이게 실제로
터지면 이번 라운드와 똑같은 모양(태스크가 조용히 wall-kill 로 끝나고 부분 데이터만 남음)이
재발한다. **테스트로 잡으려면**: stagewise 8회 + U-27 최대 6회의 예상 core-h 합을
`P1B_TASK_CORE_HOURS[-1]` 에서 종별 측정분을 뺀 나머지와 비교하는 사전검사(dry-run 성격, 실행
전에 계산 가능) 하나면 충분하다. **coder9 가 이미 이슈로 인지했으니 새 지적이 아니라 위험의
크기를 구체화한 것 — MAJOR, lead 확인 후 진행.**

### 🔴 MAJOR #2 — 이번 라운드가 남긴 오염된 `stages/*.json` 위에 재제출하면 새 코드가 낡은 결과를 그대로 승계한다
`sei_stage`(common.sh:95-118)의 마커 판정은 `stages/<stage>.json` 에 `"rc": 0` 이 있으면 무조건
건너뛴다 — **이번 판·다음 판 구분이 마커에 없다.** 이번 라운드가 실제로 남긴 오염 흔적
(`cpu_machine_pilot_results/sei_pilot_work/jobs/P1b/stages/p1b_hco3_anion_A_cheap_optfreq.json` 등,
critic9 가 이미 확인한 rc=0 마커 — 그런데 그 stage 는 3중 동시실행 중 하나가 우연히 rc=0 을 냈을
뿐 provenance 는 못 믿는다, 이번 리뷰 앞부분 참조)이 **동일 경로 `jobs/P1b/` 에 남아 있는 채로
고쳐진 payload 를 재제출하면**, 새 코드가 `stages/p1b_hco3_anion_A_cheap_optfreq.json` 을 보고
"이미 완료" 로 읽어 **재실행 없이 오염된 값을 그대로 승계한다.** ADR-107 R-9 가 이미 P5 의 거짓
`done` 마커 문제(state/ 수준)를 지적했는데, **이건 그보다 한 단계 아래(stages/ 수준)에서 같은
모양이 또 있다는 것**이다. `--force` 도 이 마커엔 안 닿는다(`sei_stage` 는 `args.force` 를 아예
모른다 — force 는 `cli.py` 수준 개념이다). 재제출 전에 (a) `jobs/P1b/`, `jobs/P5/` 를 새 경로로
옮기거나(사용자의 "삭제 금지"는 지키면서 이름만 바꾸는 방법 있음) (b) `sei_invalidate_stage` 를
재제출 스크립트가 오염된 항목에 자동으로 돌리는 절차가 필요하다 — **coder9 담당인지 lead 가
직접 처리할 재제출 절차인지만 정해지면 된다, 코드 결함은 아니다.**

### 사소
- `sei_stage` 마커 경로(common.sh:98)가 suffix 로 안 보호된다는 사실 자체는 지금 위험하지 않지만
  (P5/P1b 는 tag 유일성으로, P1b stagewise/U-27 은 게이트로 각각 보호), **보호 메커니즘이
  경로마다 다르다** — 나중에 세 번째 payload 가 추가되면 또 처음부터 판단해야 한다. 코드 변경
  요구 아님, 메모.
- "3"(P1b 대상 종 수)이 `plan.py` 의 `P1B_TASK_CORE_HOURS` 튜플 길이와 `P1b.sh:54`
  `for want in (5, 12, 22)` 양쪽에 각각 하드코딩돼 있다 — 지금은 일치하지만 "같은 진실 두 곳"
  패턴. U-76 급은 아님(둘 다 3으로 이미 안정적), 메모만.

### 테스트 없음에 대해 — BLOCKER 로 올리지 않음(lead 지시). 대신 입력 명세만
```
- P5/P1b 오프바이원: TID=0, TID=len+1 을 주고 exit code != 0 && "실행 0건" 로그가 없는지 확인
- 경합 재현(ADR-107 R-7 이 요구하는 그 테스트): 같은 SEI_JOB_DIR 로 TID=1..N 을 병렬로 띄우고
  모든 산출 파일 경로가 서로 겹치지 않는지 확인 — "task 1이 자기 몫만 돈다"는 걸론 부족하다
  (이번 결함은 동시성 결함이었지, 단일 태스크 로직 결함이 아니었다).
- MAJOR #1: stagewise(8)+U-27(≤6) 예상 core-h 합을 P1B_TASK_CORE_HOURS[-1] 잔여 예산과 비교하는
  사전검사(dry-run, 실행 없이 계산 가능).
- MAJOR #2: jobs/<key>/stages/ 에 미리 rc=0 마커를 심어두고 새 payload 를 그 위에 돌려 마커를
  무비판 승계하는지 확인하는 회귀 테스트.
```

---

## critic9 — 임무2 본리뷰: coder9 의 A-1~A-4 구현 (6개 중점 항목) — 2026-08-20

**🔴 ADR-057 예외 명시(lead 지시)**: 원래 검증 대상은 shipped tarball 이나, `dist/` 는 ADR-086 으로
동결돼 있고 이번 라운드는 tarball 이 없다. **이 리뷰는 source tree 검증이며, 다음은 검증 불가다**:
(1) `make_package.sh` 패키징이 이 소스를 있는 그대로 옮기는지(과거 README 어긋남 사고 ADR-057 이
바로 이 지점), (2) `tests/` 제외가 여전히 맞는지, (3) `BUILD_STAMP.json`/digest 가 이 코드와
합치하는지, (4) tarball 추출 후 바이트 단위 재현. `test_build_stamp.py` 의 2건 FAIL 은 정확히
"tarball 이 소스보다 낡다"는 ADR-086 의 기대 신호이고, 변경 파일 목록(10개)이 coder9 가 보고한
목록과 정확히 일치함을 직접 확인했다 — 그 외에는 아무것도 tarball 기준으로 보장 못 한다.

**직접 실행한 것**: `python3 -m unittest discover -s tests -p "test_*.py" -t tests` 전체
(Ran 1275, failures=2, errors=4, skipped=14 — coder9 보고와 정확히 일치, 직접 재현함).
`test_array_task_split.py` 26건 단독 재실행(전부 OK, subprocess 로 실제 bash 스크립트 실행,
mock 아님). `common.sh` 를 `/tmp` 사본에서 수정 전 형태로 뮤테이션해 실제로 task 2 가 침묵하는지
직접 재현(아래 참조) — **저장소 파일은 건드리지 않았다**(임시 디렉터리에서만 작업, 정리 완료).

### 1. task 키 접미사 경계 사례 — 뮤테이션 테스트로 직접 검증, PASS
`/tmp` 사본에서 `common.sh` 의 `SEI_ARRAY_TASK_ID` 블록(577 바이트)을 제거해 **수정 전 형태**를
재현한 뒤, `sei_job_main` 을 거쳐 같은 논리 키로 태스크 1/2 를 순차 실행:
```
뮤테이션(수정 전 형태)  → task2 "논리 키 P5 완료 마커 존재 → 건너뜀" — 침묵. ran.txt 1줄.
원본(수정 후)          → task1=P5.t1, task2=P5.t2, 둘 다 실행. ran.txt 2줄. state/ 에 각각 done.
```
**결론: 회귀 테스트가 실제로 원래 버그를 재현하는 입력을 쓰고 있고, 수정이 그 정확한 버그를
고쳤다는 것을 직접 실행으로 확인함(coder9 의 주장을 신뢰한 게 아니라 내가 돌렸다).**
PBS 전용 경로(`#PBS -J` 렌더 + 실제 PBS 가 `PBS_ARRAY_INDEX` 를 설정하는 것)는 이 박스에서
검증 불가라는 coder9 의 한계 인정에 동의한다 — 그런데 `common.sh` 가 읽는 메커니즘 자체는
스케줄러 불가지론적(env var 만 본다)이고, 내 테스트가 `local.sh.tmpl` 과 동일한 셸 구조로 그
메커니즘을 직접 실행했다. **잔여 미검증분은 "PBS 가 실제로 이 env var 를 정확히 설정하는가"
뿐이며, 이건 우리 코드가 아니라 PBS 자체의 책임이고, 이번 회신의 raw log 가 이미 그것을 증명했다**
(P5.qsub 에 `#PBS -J 1-22` 가 실제로 렌더됐고 22개 서로 다른 host 에서 실행됐다 — PBS 는 자기
몫을 했다, payload 가 안 읽은 게 사고였다). **잔여 위험 없음으로 판단.**

### 2. P1b 마지막 태스크 배치 — wall 산식으로 반박, MAJOR (직전 부분리뷰에서 이미 지적한 것의 강화)
plan.py 자신의 주석이 `P1B_TASK_CORE_HOURS[2] = 3,072 = 64 cores × 48h wall`, **여유 0%**라고
적어 놨다. 여기에 stagewise(8회 G16) + U-27(최대 6회)을 얹으면 위험하다는 게 직전 부분리뷰의
지적이었는데, **이번에 실제 회신 데이터로 훨씬 강한 근거를 찾았다**: task 3 이 맡는 22원자
종은 `li_ec2_cation`(21원자, manifest 확인)이고, **이 종은 실제로 이번 라운드에
`A_cheap_optfreq` 만으로 15,952초(4.43h, 64코어=283.6 core-h)를 쓰고도 rc=1(미수렴)이었으며,
`B_high_optfreq` 는 qdel 까지 끝내 완료하지 못했다.** 즉 **종 자체의 계산비용이 이미 예산
경계에 근접하거나 넘을 조짐을 실측으로 보였는데, 그 위에 stagewise+U-27 을 더 얹는 설계다.**
coder9 는 이미 이슈로 인지했다("[코더 결정, lead 확인 요망]") — **동의, lead 판정 전 진행 금지
권고.**

### 3. A-3 문턱 (`CORE_HOURS_UNDERCOUNT_RATIO=1.2`) — 직접 계산으로 오탐 재현, MAJOR
`collect.core_hours_accounting_warnings()` 를 파이썬에서 직접 호출해 문턱의 수학적 거동을
확인했다:
```
total= 0.50  overhead=0.5core-h(관대한 상한: smoke 2xH2 SP + glue @ 64코어)  ratio=2.000  경고=True(정상)
total= 1.00  같은 overhead                                                  ratio=1.500  경고=True(정상)
total= 2.00  같은 overhead                                                  ratio=1.250  경고=True(정상, 문턱 바로 위)
total= 5.00  같은 overhead                                                  ratio=1.100  경고=False
total= 9.00  같은 overhead                                                  ratio=1.056  경고=False
```
**비율만 보고 절대값 하한이 없다**(`+0.01` 은 사실상 무의미하게 작다). 실측 P1(총 527.822,
overhead 0.9 core-h)은 안전하게 오탐 없음을 직접 계산해 확인했다 — **큰 항목은 안전**하지만,
P5 의 가장 싼 종(h2o, co2 같은 소분자, 총 core-h 가 한 자릿수일 가능성이 있는)이나 P1b 의
`hco3_anion`(5원자, 실측 부분합 ~9 core-h 대) 처럼 **총량이 작은 태스크에서는 정상적인
smoke/glue 오버헤드만으로도 오탐이 날 수 있는 게 수학적으로 증명된다.** `sei_qc_smoke` 자체는
H2 2원자 SP 2회라 실비용은 크지 않을 가능성이 높지만(정확한 실측치 없음, [의심]으로 표시),
**절대값 하한을 함께 걸면(예: "비율 1.2 초과 AND 절대 갭 > N core-h") 문턱이 훨씬 안전해진다** —
coder9 에게 제안.

### 4. A-2 경고 방향 — 직접 재현으로 오탐 확인, MAJOR
합성 executions.jsonl 로 직접 확인: P1 이 nodeA 에서 epoch 100-200 에 실패하고, **13.9시간 뒤**
nodeB 에서 `P1_c1` 으로 재개(epoch 50000-50100, 완전히 순차적·비중첩)하는 **정당한 케이스**를
`execution_audit()` 에 넣었더니:
```
concurrent_logical_runs: {'P1': {'n_run_lines': 2, 'hosts': ['nodeA', 'nodeB']}}
warnings: ['🔴 concurrent_execution: ... 2회@nodeA,nodeB ...']
```
**경고가 발화한다 — 시간적으로 전혀 겹치지 않는데도.** 현재 로직(common.sh 코드 아니라
`collect.py` 의 `execution_audit`)은 `len(entries)>=2 and len(hosts)>=2` 만 보고 **run/finish
epoch 의 시간 중첩 여부를 전혀 안 본다.** `test_sequential_chain_resume_on_one_host_does_not_warn`
이라는 이름의 테스트가 이미 있는데 **정확히 "on_one_host"만 테스트하고 있어 — 위험한 경우(다른
host)를 의도적으로 피해간 이름이다.** coder9 자신이 이 위험을 알고 있었다는 뜻으로 읽힌다(테스트
이름이 정직하다). **판정: 이 형태는 ADR-091 이 이미 경고한 "오탐이 진짜를 가리는" 패턴과
정확히 같다.** 제안: `entries` 를 epoch 로 정렬하고 인접 run 사이에 **먼저 온 것의 대응 finish
epoch 가 다음 run epoch 보다 늦을 때만**(진짜 시간 중첩) 경고하도록 좁힐 것. 게이트가 아니라
경고이므로 지금 당장 막을 이유는 없지만(coder9 의 프레이밍에 동의), 이 소음이 실측으로 자주
나면(이 클러스터는 체인 재개가 다른 host 로 흔히 감) "경고 피로" 로 흐른다 — MAJOR, coder9
차기 항목 제안.

### 5. `SEI_SOLVENT_POLICY_JSON` 우회 표면 — 적대적으로 봄, 실질 위험 낮음이나 게이팅 없음은 사실
`load_policy()` 가 env var 를 config 보다 **무조건 우선**한다(테스트 모드 플래그로 안 잠겨
있음) — coder9 의 "우회 표면이 늘었다"는 말 그대로 맞다. 다만:
- `pcm_numeric` 경로는 epsilon 값과 무관하게 **항상** `raise`(미구현) — 이 경로로는 어떤 입력을
  줘도 덱이 안 나온다. 안전.
- `solvent_line()` 이 `"scrf=(smd,solvent=generic,read) %s"` 를 **하드코딩된 리터럴**로 만들고
  `descriptors` 딕셔너리 값은 `Eps=%s` 형태로만 스플라이스된다 — 이름 있는 용매를 그 경로로
  넣을 방법은 없다(구조적으로 막힘, coder9 말대로).
- 🔴 **그러나 `descriptors` 값 자체에 타입 검증이 없다.** `have[n]` 을 `%s` 로 그대로
  스플라이스하므로, 이론상 `descriptors={"Eps": "18.5) scrf=(smd,solvent=acetonitrile"}` 같은
  악의적 문자열이 주어지면 G16 route 문자열 자체가 깨질 수 있다. **실질 위험은 낮다** — 이
  채널에 접근하려면 이미 잡 실행 환경변수를 조작할 권한이 필요하고, 그 권한이면 스크립트 자체를
  바꾸는 것과 별 차이가 없다. **그래도 숫자 타입 검증(`float(v)`) 한 줄이면 이 경로 자체가
  사라진다** — 코드 변경 아님, 제안만.
- 더 실질적인 위험은 보안이 아니라 **설계 위반**이다: env var 가 **테스트 전용이라는 문서
  주석만 있고 코드로 강제되지 않는다.** 잡 제출 환경(`#PBS -V`)에 우연히 이 이름의 변수가
  섞여 들어가면(사이트 프로파일 등) config 파일의 결정을 조용히 무시한다 — ADR-105 가 원한
  "한 곳에서 결정" 이 깨진다. 제안: `SEI_SOLVENT_POLICY_JSON` 을 실제 잡 템플릿(`pbs.sh.tmpl`
  등)에서 명시적으로 `unset` 하거나, 이름에 `_TEST_` 를 박아 혼입 가능성을 낮출 것.

### 6. 거부의 전면성 — collect 경로 확인, **coder9 의 "4항목"이 아니라 5항목이고 그 중 하나가 κ 다**
🔴🔴 **가장 중요한 발견**: `payload/P6.sh` 는 `sei_qc_smoke` 를 호출하지 않지만, `sei_qc_input`
을 직접 호출하고(`JOB_TYPE="sp"`), `config/qc_levels.json` 의 `job_types.sp` 템플릿이
`"#p {functional}/{basis} {solvent} sp"` — **`{solvent}` 자리가 있다.** 즉 P6 도
`resolve_solvent_line()` 을 반드시 통과한다. **실제 config(뮤테이션 아니고 현재 그대로)로 직접
실행해 확인**:
```python
solvent_mod.resolve_solvent_line(solvent_mod.load_policy(), None)
→ RAISED SolventUndecided: "C-5: 이 덱에 도달한 용매 결정이 없다 (solvent_policy.model=None)..."
```
**P6(κ 앵커) 도 지금 config 그대로 제출하면 exit 4 로 거부된다.** coder9 의 메시지는 "다음
배치의 QC 4항목"(P1/P1b/P5/endpoint_prep_reactant)이라고 했는데, **P6 이 빠져 있다 — 그런데
P6 도 같은 이유로 막힌다.** 그리고 더 심각한 것: `solvent_policy.model` 이 가질 수 있는 세 값
전부 지금 막혀 있다 — `null`→거부, `smd_descriptors`→테이블이 `{}` 라 거부,
`pcm_numeric`→**epsilon 값과 무관하게 미구현이라 무조건 거부**(코드에 하드코딩된 raise, `epsilon`
값을 검사하기도 전에 도달). **즉 지금 이 코드베이스에서 `solvent_policy.model` 을 어떤 값으로
설정해도 어떤 화학 항목도 덱을 못 낸다** — pcm_numeric 방출 경로(scrf `read` 섹션 배선)가
실제로 구현되기 전까지는. 이건 STATE §0-o.5 항목1/ADR-105 가 "이번 라운드는 배선만, 값 결정은
다음"이라고 명시적으로 예정한 것과 합치하지만(버그 아님, 설계대로), **P6 이 이 일반 거부에
포함된다는 것 자체는 이 리뷰에서 처음 확인됐다** — decision log/state 어디에도 "P6+solvent"
언급이 없다(전수 grep 확인).
**거부의 전면성(coder9 질문 원래 취지) 자체는 확인**: exit 4 는 `sei_job_main` 의 일반
`rc!=0` 처리를 타서 `state/<key>.tN.failed.json` 에 `reason: "payload_nonzero_exit"` 로 잡히고,
`collect_p5`/(추정)`collect_p1b`(611번째 줄, 시간상 전체는 안 읽었으나 collect_p5 와 대칭 구조로
보임)는 `st=="failed"` 면 `status="fail", fail_reasons=["job_marker=failed"]` 로 표면화한다 —
**조용한 skip 으로 뭉개지지는 않는다(status 는 확실히 fail 로 보인다).** 다만 **이유가 일반
문자열("job_marker=failed")이라 "C-5 거부"인지 "G16 이 진짜 죽었다"인지 최상위 필드만 보고는
구분이 안 된다** — `endpoint_prep_reactant` 는 자체 collector(`collect_endpoint_prep`)가
`"solvent_descriptors_missing"` 이라는 구체적 status 를 붙이는데, P1/P1b/P5 는 그 대우를 못
받는다. 실제 사유(`SolventUndecided` 메시지 전문)는 `smoke_result${SFX}.txt` 안에는 있다 —
**유실은 아니지만 최상위에서 안 보인다.** 이건 이번 리뷰 앞부분에서 지적한 c10/`unresolved_for_lead`
배선 누락과 **같은 모양**(정보는 어딘가에 있는데 요약 채널에 안 닿음) — MAJOR, 다음 항목 제안.

### 판정
**BLOCKER 급 정보 하나(P6 도 막힌다) — 코드 결함은 아니고 설계대로지만, 제출 시점 판단에
직접 영향을 준다. lead 에게 별도로 알린다(팀 프로토콜: BLOCK 급이면 lead 에게도 반드시).**
나머지는 MAJOR(A-2/A-3 임계값 오탐 가능성, P1b 마지막태스크 예산 위험 강화 근거,
smoke-refusal 사유 미표면화) — 지금 코드를 막을 사유는 아니나 coder9 차기 항목으로 제안.
common.sh/P5.sh/P1b.sh 의 핵심 동시성 수정 자체는 뮤테이션 테스트로 직접 검증했고 옳다.

---

## critic9 — P-0(pcm 방출+deck_verified 게이트) + MAJOR#1(P1b 4번째 태스크) 좁힌 리뷰 — 2026-08-20

**범위**: lead 지시대로 이 둘만. R-13/A-5/§5(env unset)/§6(P6) 등 coder9 가 함께 보고한 나머지는
다음 라운드로 넘김, 안 봄(단 payload/P1.sh 가 리뷰 중 out-of-band 로 바뀐 것을 인지함 — C-8
게이트 추가로 보이며 이번 스코프 밖이라 내용 검토는 안 함, 존재만 기록).

## 판정: BLOCKER 1건. 나머지 4개 체크리스트 전부 직접 실행으로 확인, 결함 없음.

### 🔴 BLOCKER — `SEI_QC_PURPOSE` 가 잡 템플릿에서 unset 안 됨 (deck_verified 게이트 우회로)
`qc_adapter.sh:161` 이 `purpose = os.environ.get("SEI_QC_PURPOSE") or "production"` 로 읽는다.
`sei_qc_smoke()` 는 `SEI_QC_PURPOSE=smoke sei_qc_input ...`(단일 명령 스코프, `export` 아님 —
안전한 패턴, 전수 grep 으로 다른 세팅 경로 없음 확인)로만 쓴다. 그런데 `templates/*.tmpl` 3종은
`SEI_SOLVENT_POLICY_JSON` 만 `unset` 하고 **`SEI_QC_PURPOSE` 는 안 지운다**(coder9 도 메시지에서
인지). `pbs.sh.tmpl` 에 `#PBS -V`(제출 환경 전체 상속)가 있으므로, 사용자 쪽 환경에 우연히
`SEI_QC_PURPOSE=smoke` 가 잡혀 있으면(과거 디버깅 잔재 등) **P1/P1b/P5/endpoint_prep 의 모든
본계산 호출이 smoke 로 위장돼 `deck_verified=false` 게이트를 통과한다** — lead 가 지목한 "유일한
진짜 안전장치"가 뚫리는 정확한 경로다. coder9 가 한 줄이라고 이미 말했다 — **템플릿 3종에
`unset SEI_QC_PURPOSE` 추가를 재제출 전 요구한다.**

### 나머지 4개 — 직접 실행/실제 config 로 확인, 결함 없음
```
1(부분) deck_verified=false 에서 정말 막히는가
        실제(뮤테이션 아닌) config/qc_levels.json 정책으로 resolve_solvent_deck() 을 직접 호출:
        purpose="production" → RAISED SolventUndecided (막힘, 확인)
        purpose="smoke"      → deck 반환, label=[UNVERIFIED...] (통과, 확인)
        의도한 방향대로다. 위 BLOCKER 가 유일하게 찾은 우회로.
2       smoke 경로만 통과 — 위와 같은 실행으로 확인(반대로 걸리지도, 너무 열리지도 않음)
3       ε 숫자전용 — route_fragment="scrf=(pcm,solvent=generic,read)"(하드코딩 리터럴),
        extra_input_lines=["eps=18.5"](float 검증됨). 이름 있는 용매 경로 없음, 확인.
4       P1b 4번째 태스크가 1-3 을 안 건드림 — P1b.sh:65-80 직접 확인:
        EXTRAS_TID=N_TARGETS+1(=4), 그 태스크는 targets 파일을 **빈 파일로**(`:>`) 만들어
        종별 루프가 0회 실행. plan.py: P1B_TASK_CORE_HOURS=(476,1190,3072,**590**) — 1-3 값
        불변 확인(기존 §R26.1/§R27 그대로). test_species_task3_has_no_extras_either /
        test_dedicated_task4_carries_the_stagewise_and_u27_extras_only 직접 재실행, PASS.
5       590 이 가드 21,000 안에 드는가 — `plan.build_plan()` 을 실제 env(PBS/64core/48h/
        gaussian16 module)로 직접 호출: P1b reserved=**5328.0**(=476+1190+3072+590, 정확히
        일치), 전체 CPU 항목 총 reserved=**20,065.39**(주석의 "20,065.4" 와 일치, 반올림
        차이만), guard.max_core_hours=21,000.0, `sizing_gates.blocked_items=[]`(아무것도
        안 막힘). 확인.
```

## MINOR (다음 라운드 목록용, 지금 안 막음)
- `descriptors` 값 float 검증은 됐지만(critic9 §5 반영 확인) `SEI_SOLVENT_POLICY_JSON` 자체도
  env 우선이라 같은 `#PBS -V` 유입 계열 위험이 구조적으로 남아 있음(이미 unset 됨, 잔여 위험
  낮음, 기록만).
- P1.sh 가 이번 리뷰 도중 바뀜(C-8 게이트로 보임) — 이번 스코프 밖, 내용 미검토.

## 확인하지 못한 것
- R-13(frozen fixture 2벌), A-5(collect_unresolved 분리), §5 템플릿 3종 전체 diff — lead 지시로
  스코프 제외, 다음 라운드에.

---

## critic9 — P-0/MAJOR#1/C-8 재검증: 이전 BLOCKER 철회 + 6항목 확인 — 2026-08-20

### 🟢 이전 BLOCKER 철회 — SEI_QC_PURPOSE 는 실제로는 우회 불가였다
**직접 재현으로 확인.** `/tmp` 하네스에서 `SEI_QC_PURPOSE=smoke` 를 **영속 export**(#PBS -V
유입 시뮬레이션)한 뒤 실제 `qc_adapter.sh` 를 소싱해 `sei_qc_smoke()` 를 호출:
```
smoke_L1=ok, smoke_L2=ok  (H2 스모크 자체는 통과 — 의도대로)
sei_qc_smoke rc=1         ← "smoke=ok_but_production_deck_refused" 발동, 거부 사유 출력됨
```
원인: `qc_adapter.sh:379-388` 의 production-gate 가 `resolve_solvent_deck(..., "production")` 을
**리터럴 문자열**로 호출한다(환경변수를 안 읽음) — env leak 에 면역이다. 이 호출이
`deck_verified=false` 에서 반드시 실패하고 `rc_all=1` 을 만들어 `sei_qc_smoke` 자체가 비정상
종료한다. P1/P1b/P5/endpoint_prep 전부 `sei_qc_smoke ... || exit 4` 패턴이 **가장 먼저**
실행되므로(4개 payload 헤더 직접 확인), leak 이 있어도 **본계산 `run_step`/`sei_qc_input`
호출에 도달하기 전에 스크립트가 죽는다.**
⚠ **다만 `sei_qc_input` 자체는 leak 에 취약함을 별도로 확인**(같은 하네스에서 smoke 이후 수동으로
production `sei_qc_input` 을 호출하니 실제로 미검증 덱이 나왔다) — 그러나 이 호출은 정상 실행
경로에서는 **도달 불가**(스크립트가 이미 exit 4 로 죽어 있으므로)이다. 결론: **현재 스크립트
구조에서는 우회 불가.** `SEI_QC_PURPOSE` 를 템플릿에서 unset 하는 것은 여전히 권한다 — 방어
심층화용(스크립트 구조가 나중에 바뀌면 이 면역이 깨질 수 있음) — 그러나 **재제출을 막을
BLOCKER 는 아니다.** 이전 리뷰의 BLOCKER 판정을 여기서 철회한다.

### 2. `SEI_C8_ENDPOINTS_JSON` — 우회 아님, 확인
`local.sh.tmpl:7-8` 에 `unset SEI_SOLVENT_POLICY_JSON`/`unset SEI_C8_ENDPOINTS_JSON` 이
`{{ENV_EXPORTS}}` **앞에** 있음을 직접 읽어 확인(순서 중요 — 늦으면 무의미). 그리고 이 채널은
**데이터만 주입**하고 판정은 여전히 `guards.require_ts_precondition` 이 한다(P1.sh:104-107 확인)
— 이름 있는 용매 채널과 달리 "무엇을 넣어도 통과"가 구조적으로 아니다. 안전.

### 3. 예산 590 의 N — P1b 종 집합이 아니라 태스크4 실기하, 확인
`inputs/li_ec_radical_reactant.xyz` 첫 줄 = `11`(원자수 헤더), `manifest.json` 의 `ec`
(`u27_reference: true`) `n_atoms=10` — 둘 다 직접 파일 열람으로 확인. `plan._p5_runs()` 로
b(N) 실행: `b(11)=71.3, b(10)=53.6, 2×71.3+53.6=196.3, ×3=588.9≈590` — 주석 전문과 정확히
일치.

### 4. C-8 거부 노출 — 확인, 노출은 됨(승격은 의도적으로 다음 라운드)
`collect.py:441-449` 직접 확인: `c8_precondition` 전체 기록 + `warnings` 에 "c8_refused ...
이 거부는 C-8 이 작동한 결과이지 화학적 실패가 아니다"를 명시적으로 붙인다 — endpoint_prep 의
`solvent_descriptors_missing` 과 같은 지위 부여, 잘 라벨링됨. `unresolved_for_lead` 미승격은
coder9 가 이미 인지·이번 범위 밖으로 명시 — 동의, 다음 라운드 목록에.

### 5. 128-core fixture 테스트 분할 — 약화 아님, 오히려 "진실 하나" 원칙 강화
`test_plan_report_e2e.py:204-236` 확인: 원래 성질("가드가 조용히 안 뺀다")이 이제 **두
테스트로 상호보완**한다 — `code_truth()`(승인된 실제 형태: 64core/48h/PBS/normal, ADR-057
검증에 쓰던 바로 그 harness) 기준 "전부 돈다" + 128-core/24h 가상 fixture 기준 "안 맞으면
시끄럽게 빠진다"(`budget_guard` 사유 확인). `code_truth()` 가 조작된 값이 아님을 직접
`build_plan()` 재실행으로 교차검증(아래 6번과 동일 실행에서 나온 값). **약화 아니라 보완.**

### 6. README 총계 — coder9 가 인용한 숫자가 실제와 다르다, 코드/README 자체는 일치
직접 확인: `README_USER.cpu.md:88-89` = `expected_total_core_hours=17653`,
`reserved_total_core_hours=20065`. `code_truth()` 직접 재실행: `expected=17653.01,
reserved=20065.39` — **정확히 일치**(README/코드 정합 확인, ADR-057 성질 유지). 🔴 **coder9 가
메시지에서 인용한 "18,037/20,449" 는 실제 값과 다르다**(둘 다 정확히 +384 — endpoint_prep_reactant
의 예산 384.0 과 우연히 같은 차이, 원인은 모름 — stale 값이거나 오기로 보인다). **README/코드
자체는 문제 없으니 재제출을 막을 사유는 아니다** — coder9 에게 그 숫자 출처만 확인 요청.

## 판정
**BLOCKER 없음.** 이전 판정(SEI_QC_PURPOSE)은 재현 실험으로 철회했다. 나머지 5항목 전부 직접
파일 열람·직접 실행으로 확인, 결함 없음. MINOR 1건(SEI_QC_PURPOSE 여전히 방어심층화로 unset
권장) + 사실확인 요청 1건(coder9 의 README 숫자 인용 오류, 코드 자체는 정상).

---

## critic9 — lead 질문 선답변: deck_verified=true 시 무엇이 8,432 core-h 를 지키는가 — 2026-08-20

**아직 config 는 `deck_verified:false` 다(item 1 미착지) — 그러나 코드에 이미 S-1/S-2 런타임
검증 메커니즘이 들어와 있어(`solvent.py:194-297`, `qc_adapter.sh:385-425`) 그 메커니즘 자체를
지금 읽고 답한다. item 2(collector `applied_dielectric_evidence`)는 아직 `collect.py` 에
없음(전수 grep 확인) — 도착하면 별도로 본다.**

### 발견: S-1 의 `eps_matched` 는 순환증거에 취약하고, `deck_verified=true` 가 되는 순간 그마저
### 게이트에서 빠진다 — lead 의 우려가 정확하다

`solvent.py:280-291`: `run_verified = runtime_verification_ok(runtime_verification, eps_f)`,
게이트는 `config_verified or run_verified`. **`config_verified=true` 가 되면 `or` 의 왼쪽이
참이라 `run_verified` 값과 무관하게 즉시 통과한다** — S-1 검증 자체가 라벨(`label=None`)에도
반영 안 되고 완전히 무의미해진다. 즉 `deck_verified=true` 이후 **레이블/게이트 관점에서는
정확히 lead 말대로 `sei_qc_smoke` 의 성패(=route 문법이 G16 에 받아들여지는가) 하나만 남는다.**

**그리고 그 남은 하나(S-1 의 `eps_matched`)조차, config_verified 가 false 였을 때도 완전하지
않았다.** `criteria/g16.py:472-499` `parse_scrf_dielectric()` 의 자체 docstring이 이미 실토한다:
```
"G16 이 `read` 추가 입력 섹션을 에코하면 입력의 eps=18.5 줄 자체가 매치될 수 있다 —
 에코는 '적용됐다'의 증거가 아니다."
```
`RE_DIELECTRIC_CANDIDATES` 의 패턴(`r"(?i)\beps\s*=?\s*([0-9]+\.[0-9]+)"` 등)은 **문맥 무관
텍스트 매치**다 — G16 이 입력 파일을 그대로 에코하는 것은 (성공/실패와 무관하게) 흔한
동작이므로, **`read` 섹션 문법이 틀려서 G16 이 그 섹션을 조용히 무시해도, 에코된 입력 줄
자체가 `eps_matched=True` 를 만들 가능성이 높다.** 즉 S-1 은 "G16 이 우리가 뭘 요청했는지
받아 적었다"를 증명하지, "G16 이 그 값을 실제로 SCRF 계산에 넣었다"를 증명하지 못한다 —
정확히 lead 가 예로 든 시나리오("eps 섹션이 무시되는데 route 는 멀쩡한 경우")다.

### 판정
🔴 **`deck_verified=true` 로 전환한 뒤에는, "덱이 틀렸는데 G16 이 받아들이는" 시나리오를 막는
코드 장치가 전혀 없다** — S-1 은 config_verified 가 참이면 아예 안 물어보고, 물어봤어도 순환
증거에 취약해서 신뢰도가 낮았다. **유일한 보호는 사람이 첫 실 로그의 `deck_verification.json`
(계속 기록은 됨, 게이트에서만 빠짐)/`applied_dielectric_evidence`(도착 예정)를 읽고 판단하는
것 — 그리고 그건 사후(core-h 를 이미 쓴 뒤)다.**

🟢 **이번 라운드가 잃는 것에 대한 lead 판단(비용은 살아남는다)에 동의, 근거를 더 붙인다**:
SCRF/PCM 오버헤드는 **PCM 이 켜져 있다는 사실 자체**(추가 반복·추가 적분)에서 오지, 정확한
ε 값 자체에서 오지 않는다(이건 계산화학 일반론이고 이 프로젝트가 직접 측정한 값은 아니다 —
[의심]으로 표시, ADR-106 의 "ε sensitivity 는 화학적 결과에 민감하다"는 진술과는 다른 축이다:
ADR-106 은 **결과값**이 ε 에 민감하다는 것이었지 **비용**이 민감하다는 게 아니었다). ⟹
core_hours_total/wall_h/κ 관련 숫자는 ε 가 틀려도 유효할 가능성이 높다는 lead 판단에 동의.
**화학적 결과(barrier, IRC, ΔG 등)는 못 지킨다** — deck 형식이 틀렸는데 G16 이 받아들였다면
그 계산 자체가 EC:EMC 3:7 이 아닌 다른(혹은 정의되지 않은) 유전상수 위에서 돈 것이라 U-56/
S3 판정에 못 쓴다. 이건 이번 라운드가 어차피 acetonitrile 배치 취급을 받았던 것과 **같은
급의 손실**이다 — 화학은 잃고 비용은 남는다.

### 제안 (코드 변경 요구 아님, coder9/lead 판단용)
`applied_dielectric_evidence` 필드가 오면 최소 다음이 있는지 볼 것: (1) `eps_matched` 값
자체 뿐 아니라 **evidence_lines 원문이 통째로** 실리는가(사람이 에코/진짜를 구분할 유일한
방법), (2) 못 찾았을 때(`n_matches=0`) 조용히 빈 리스트만 두는 게 아니라 "찾지 못했다"는
사유 문자열이 남는가, (3) `deck_verified=true` 상태에서도 이 필드가 계속 채워지는가(게이트와
무관하게 — 위에서 확인한 대로 smoke 코드 자체는 조건 없이 도는 것으로 보이나, collector 가
그 결과를 무조건 옮기는지는 미확인, 도착 후 확인).

---

## critic9 — 조건 명시 정정 + lead 최종질문 답변(반박 없음) — 2026-08-20

**정정**: 위 "BLOCKER 철회" 절의 근거는 **`solvent_policy.deck_verified=false` 전제 위에서만
성립한다.** `qc_adapter.sh:379-388` 의 production-gate 가 `resolve_solvent_deck(...,
"production")` 을 리터럴 호출해 SEI_QC_PURPOSE leak 을 무력화하는 것은 **그 호출이
`deck_verified=false` 라서 무조건 실패하기 때문**이다 — `deck_verified=true` 가 되면 그 호출은
**설계상 성공**하고(승인된 상태이므로), production-gate 자체가 막을 이유가 없어진다.
🔒 **다음에 `deck_verified` 가 다시 false 로 돌아갈 때(새 덱/재사양) 위 철회 문단을 조건 없이
인용하지 마라.** 다만 결론(BLOCKER 아님)은 두 상태 모두에서 유지된다 — `deck_verified=true`
에서는 production 이 설계상 허용이라 애초에 "우회할 게이트"가 없고, `SEI_QC_PURPOSE` 는
`deck_verified=false` 일 때만 의미 있는 변수이기 때문이다(lead 판단, 동의).

**lead 최종질문("deck_verified=true 에서 무엇이 8,432 core-h 를 지키나") — 반박 없음, PASS.**
이전 절에서 이미 답한 내용과 동일: `sei_qc_smoke` 실패 경로 하나뿐이고, deck 형식은 맞는데
`read` 섹션 값이 무시되는 경우 아무것도 안 막는다는 lead 판정에 동의. cost 생존 판정에도
동의하되 **방향성 하나만 보탠다**: `scrf=(pcm,solvent=generic,read)` 에서 `read` 섹션 값만
무시되고 `pcm` 키워드 자체는 G16 이 인식하는 경우(가능성 높음 — route 키워드와 read 섹션은
문법적으로 별개 파싱 단계) PCM 오버헤드는 여전히 걸리므로 cost 는 그대로 산다. **더 나쁜
경로(문법 전체를 G16 이 거부해 조용히 gas-phase 로 도는 경우)라면 cost 가 과소평가될 수
있는데, 이건 [UNVERIFIED]다 — 실 G16 로그가 없어 어느 경로인지 판정 불가.** 이 구분이 통과를
막을 사유는 아니다(둘 다 이미 알려진 리스크 범주 안이고, 첫 실 로그의 `deck_verification.json`
이 사후에 이걸 가릴 증거를 남긴다). **rebuild/제출에 반박 없음.**

---

## critic9 — 재제출 차단요소 마감분 리뷰: unset+S-1+C-8-2 revert — 2026-08-20

**직접 실행**: `python3 -m unittest discover ...` 전체(Ran 1307, failures=4, errors=0, skipped=14
— coder9 보고와 정확히 일치, FAIL 4건 전부 build_stamp×2/packaged README×2 확인함).
`test_solvent_wiring.TestPurposeSmugglingIsCutAtTheJobTemplate` 단독 재실행(2/2 OK).
`test_endpoint_prep` 전체 재실행(7/7 OK). `code_truth()` 재실행.

## 판정: BLOCKER 없음. 6항목 전부 직접 확인.

```
1  unset SEI_QC_PURPOSE 3종 템플릿      grep 로 3파일 전부 확인. 재현테스트
   (test_the_bypass_input_itself_...)를 직접 재실행 — sch.LocalAdapter 로 실제
   local.sh.tmpl 을 렌더해 subprocess 실행, 부모env에 SEI_QC_PURPOSE=smoke +
   미검증 PCM policy 를 심어도 leaked.txt 없음 + meta.err 에 "solvent_refused
   (C-5)" 확인. 템플릿 렌더 경로 그대로를 검증한다(직접 함수호출 아님). PASS.
2  순환증거(에코 vs 실증) 처리          현재 설계(원문 동봉 + 사람판단 필요 +
   패턴 자체를 [UNVERIFIED] 후보로 표시)가 맞다고 본다. 실 G16 로그가 없는
   상태에서 에코-제외 휴리스틱을 짜면 **G16 출력 형식을 추측으로 지어내는
   것**이고, 그건 이 프로젝트가 반복해서 피해온 바로 그 실패류다("메모리로
   형식을 지어내지 않는다"). 지금처럼 두는 게 옳다 — 첫 실 로그가 오면 그때
   evidence_lines 를 fixture 로 캡처해 정밀 규칙을 짜라(다음 라운드).
3  runtime 기록 위조표면              `grep -rn deck_verification` 전수 확인:
   쓰는 곳 `qc_adapter.sh:416`(sei_qc_smoke 안) **단 하나**.
   `endpoint_prep.sh:107`/`qc_adapter.sh:166` 은 읽기만. `w` 모드로 매 smoke
   호출마다 새로 쓰므로(조건부 스킵 없음) 이전 잡의 낡은 파일이 남아있어도
   최신 smoke 가 항상 덮어씀 — staleness 위험 없음(이전에 내가 지적한 stages/
   마커의 "존재하면 스킵" 문제와 다른 모양). 안전.
4  endpoint_prep smoke 부작용         `endpoint_prep.sh` 직접 열람: sei_qc_detect
   (QC없음 exit 3) → **smoke(신설, exit 4)** → C-5 precheck 순서 확인, QC 없음이
   smoke 보다 먼저 걸리는 순서 유지됨. `TestNoQcEngineBlocksFirst` 직접 재실행
   (2/2 OK, "아무 G16 산출물도 없음"까지 확인하는 테스트). smoke 의 H2 2회는
   `sei_qc_run` 직접호출(sei_stage 미경유) — **이건 신규 결함이 아니라 P1/P1b/
   P5 전부에 이미 있던 기존 관례를 endpoint_prep 에도 그대로 적용한 것**(직접
   코드 확인, 전 payload 공통 패턴). stage 합계 밖인 것도 종전과 동일.
5  array 접미사 정합                  쓰기(`qc_adapter.sh` 내 smoke 블록)와 읽기
   (`qc_adapter.sh:163-166`, `endpoint_prep.sh:107`) 양쪽 다 **같은 env var**
   `SEI_TASK_FILE_SUFFIX` 를 `or ""` 로 직접 읽는다 — 파이썬 로컬변수로 각자
   재계산하지 않는다. 드리프트 불가능한 구조. 확인.
6  C-8-2 revert 완전성                `grep -rln endpoint_prep_product` 전 소스+
   테스트: `plan.py` 한 줄만(취소 기록 주석, 의도적 잔존 — coder9 말대로).
   `code_truth()` 재실행: expected=17653.01/reserved=20065.39, items 10개
   (product 없음) — README(17653/20065)와 정확히 일치. 확인.
```

MINOR 없음(이번 배치). 재제출을 막을 사유 없음.

---

## critic9 — FINAL PASS: ADR-107(array 분기) + ADR-108(solvent P-0/S-1) 라운드 종결 — 2026-08-20

**🔴 ADR-057 예외 유지**: `dist/` 는 ADR-086 동결, 이번 라운드 tarball 없음 — 이 FINAL PASS 는
**source tree** 기준이다. tarball 패키징 자체(README 인도본 정합, `make_package.sh` 변환 정확성,
`tests/` 제외 여부)는 **검증 못 했다** — 그건 lead 가 rebuild 후 별도로 확인해야 한다.
`test_real_repo_dist_is_fresh` 가 지금 FAIL(변경 19파일, tarball 낡음)인 것은 ADR-086 이 예정한
정상 신호다.

**동결 상태 재확인**: 전체 스위트 재실행 — `Ran 1307, failures=4(build_stamp×2 +
packaged README×2, 전부 동결신호), errors=0, skipped=14` — **직전 리뷰와 완전히 동일**, 트리가
실제로 편집 동결 중임을 확인.

### 이번 라운드(ADR-107 → ADR-108) 전체를 관통한 critic9 의 판정 이력 요약
```
1  ADR-107 5개 증상(P1b/P5 array 미배선) 전부 raw log 직접 재확인 — 확인, lead 진단과 일치
2  mtime 을 시간증거로 쓴 MAJOR 1건 — 자기철회(lead 반박이 맞았음, 근거와 함께 로그에 남김)
3  다음 인스턴스 사전조사 — endpoint_prep product 가 12번째 후보임을 사전에 지목(적중,
   실제로 C-8-2 에서 그 형태로 들어왔다가 사용자 판정으로 되돌아감)
4  common.sh/P5.sh/P1b.sh/plan.py 부분리뷰 — MAJOR 2건(P1b 4번째 작업 예산 위험,
   재제출시 낡은 stages/ 마커 승계 위험) → 둘 다 이후 라운드에서 실제로 조치됨
   (전자는 4번째 태스크 분리+590 core-h, 후자는 lead 의 재제출 절차 판단으로 이관)
5  A-1~A-4 전체 리뷰 — MAJOR 4건 전부 뮤테이션/직접실행으로 재현·검증, 전부 반영 확인
   (마지막 확인 라운드에서 4건 전부 실제 수정+회귀테스트로 재검증 완료)
6  🔴🔴 가장 중요한 발견 — P6(κ) 도 solvent 게이트에 걸린다는 것을 실제 config 로 직접
   실행해 최초로 확인, lead 에게 즉시 별도 통지 (설계대로였지만 결정 전 필수 정보였음)
7  P-0/MAJOR#1 좁힌 리뷰 — BLOCKER 1건(SEI_QC_PURPOSE 템플릿 unset 누락) 제기
8  같은 BLOCKER 를 coder9 요청으로 **직접 재현실험**(뮤테이션 아닌 실제 하네스)해 우회
   불가임을 확인하고 스스로 철회 — 단 그 철회의 전제(deck_verified=false)를 lead 가
   짚어 로그에 조건 명시로 정정
9  lead 의 핵심 질문("deck_verified=true 에서 무엇이 지키나") 에 코드 근거로 선답변 —
   S-1 의 eps_matched 가 순환증거(G16 입력 에코)에 취약함을 코드 자체 docstring 인용으로
   확인, cost 생존 판단에 동의+근거 보강, 반박 없이 PASS
10 마감분(unset 3종+재현테스트/S-1/위조표면/endpoint_prep smoke/array접미사/C-8-2 revert
   완전성) 6항목 전부 직접 실행·열람으로 확인, BLOCKER 없음
```

### 최종 판정
**OK — critic9 관점에서 이 source tree 를 rebuild 해 제출해도 된다.** 남은 항목:
- 🔒 lead/coder9: rebuild 후 tarball 자체의 ADR-057 정합(README 인도본, BUILD_STAMP)은
  **아직 아무도 이 라운드에서 확인 안 했다** — critic9 는 tarball 이 없어서 못 봤다.
  다음 critic(또는 이번 lead)가 rebuild 직후 반드시 한 번은 봐야 한다.
- 다음 라운드로 이관된 항목(코드 변경 아님, 목록만): A-2 경고 오탐 완화(구간겹침판정은
  이미 반영됨— 확인함), A-3 절대값 하한(이미 반영됨—확인함), c10/`unresolved_for_lead`
  배선, C-8 거부의 lead-채널 승격, `SEI_SOLVENT_POLICY_JSON`/`SEI_QC_PURPOSE` 의 구조적
  방어심층화(이미 unset 됨—확인함, 스크립트 구조 변경 시 재점검 필요라는 점만 남김),
  S-1 에코-제외 정밀화(첫 실 로그 확보 후).

이 라운드에서 critic9 가 제기한 BLOCKER 는 1건(SEI_QC_PURPOSE)이었고, 재현실험으로 스스로
철회했다. 결함을 지어내지 않았고, 지적한 것은 전부 파일 열람·직접 실행·재현 테스트로 뒷받침했다.

---

## critic9 — lead 요청 3항목 최종확인 — 2026-08-20

1. S-1 우회여부: `runtime_verification_ok()` 직접 실행 — 다른 eps 기록(20.0) 재사용 시도 시
   `False`(현재요청 18.5 와 불일치 시 거부, 직접 검증). `deck_verified` 쓰기 스캔 테스트
   (`test_solvent_wiring.py:357-368`)로 코드가 그 값을 올리지 않음 확인. 우회 없음.
2. C-8-2 revert: `grep -rln endpoint_prep_product` 재실행 — `plan.py` 주석 1줄만(의도적
   기록). `code_truth()` 재실행 — reserved=20065.39(20,065 원복 확인), 10항목, product 없음.
3. `route_smoke_failed`: `endpoint_prep.sh:92` 가 쓰고 `collect.py:1038-1039` 가
   `terminal_status.json` 에서 그대로 읽어 `out["status"]` 에 반영, 같은 whitelist(1064-1068)
   에 `solvent_descriptors_missing`/`solvent_refused` 와 나란히 들어감 — 패턴 일치, 실제로
   와이어링됨(장식 아님).

## 판정: PASS

---

## 2026-08-20 — critic10 리뷰: U56-2 (ADR-109) 배선 — `sei_pilot/plan.py::u56_2_items()`, `sei_pilot/guards.py`(single-ended C-8), `sei_pilot/b0f_deck.py`(신규), `payload/U56.sh`(신규), `config/b0_reactions.json`, `config/qc_levels.json`, `tests/test_u56_plan_items.py`·`test_u56_deck_builder.py`·`test_c8_gate.py`·`test_endpoint_route_parity.py`

**대상**: `src/pilot_package/` — 이것은 SOURCE REVIEW다(ADR-057 예외를 서면으로 명시한다).
`dist/`는 ADR-086으로 얼어 있고 이번 라운드에는 U56-2 자체가 아직 릴리스되지 않았으므로(§0-p,
`u56_2.released=false`) `dist/`를 대상으로 삼지 않았다.

**방법**: `docs/05_STATE.md` §0-p 전체, `01_DECISION_LOG.md` ADR-107/108/109,
`02_METHOD_SPEC.md` §39.32(Candidate B)·§39.39·§39.41·§39.42·§39.43 통독 후 소스 통독
(`plan.py`, `guards.py`, `b0f_deck.py`, `U56.sh`, `endpoint_prep.sh`, `qc_adapter.sh`,
`qc_levels.json`, `b0_reactions.json`). `tests/test_u56_plan_items.py`·`test_u56_deck_builder.py`·
`test_c8_gate.py`·`test_endpoint_prep.py`를 `python3 -m unittest`로 **직접 실행**했다(RED/GREEN
모두 [확인]). ⚠ 리뷰 도중 `plan.py`/`config/b0_reactions.json`가 **살아있는 편집 중**이었다 —
동일 파일을 두 번 읽었을 때 내용이 달랐다(첫 읽기: U56_RC_scan 포함/wall_h 미배선, 두 번째
읽기: 제거됨/배선됨). 아래는 **마지막으로 읽고 직접 실행까지 확인한 상태** 기준이다. lead는
coder10의 편집이 안정된 뒤 전체 스위트를 한 번 더 돌리는 것을 권한다.

### 판정: FIX-THEN-RUN
컴퓨트 리스크는 없다(released=false 이므로 이번 라운드 batch에 아무것도 안 들어간다,
`test_default_items_do_not_carry_u56_items_while_unreleased` [확인, GREEN]). 그러나 이 모듈이
스스로 지정한 테스트 두 파일이 **현재 RED**다 — 이 프로젝트가 dist/ 동결의 근거로 쓰는 바로 그
규율(빌드 전 스위트 GREEN)을 이 모듈 스스로 어기고 있다. released=true로 스위치가 올라가기
전에 반드시 고쳐야 하지만, 지금 당장 잡을 막을 필요는 없다.

### 브리핑 항목별 1차 판정
```
(1) release 게이트 R-11/S-2 패턴 정합성      🟢 PASS. u56_2_released()는 코드가 절대 쓰지
    않고(test_code_never_flips_the_release_flag, GREEN), default_items()는 released=false
    동안 U56 항목을 안 싣는다(GREEN). deck_verified의 S-2 패턴과 구조적으로 동일 — coder10의
    주장은 맞다. 단, 게이트 뒤의 **내용물**은 아래 (5)/치명적 항목 참조.
(2) 단끝단 C-8 완화가 §39.32 Candidate B 에 맞는지   🟢 PASS. guards.single_ended_ts_precondition
    은 product=None 을 명시적으로 기록하고("output of the IRC, not an input") 가짜 product 를
    합성하지 않는다. reactant 쪽 C-8/C-9 조건은 그대로 유지된다 — "halves the exposure, it does
    not remove it"(스펙 원문)과 정확히 일치. 완화가 아니라 스펙이 요구한 대로의 분리다.
(3) f1_observables → optimised/converged 매핑이 과대 해석인지   🟡 매핑 자체는 과대 해석이
    아니다(optimised = normal_termination AND opt_converged, 둘 다 실제 G16 로그 파싱값이라
    RT-1급 "주장된 optimised" 재발 여지가 없다) — 그러나 이 매핑을 쓰는 실제 코드 경로
    (U56.sh:82-128 의 resolve())는 test_c8_gate.py 어디에서도 실행되지 않는다: 모든 U56 C-8
    테스트가 `SEI_C8_ENDPOINTS_JSON` 주입 채널로 guard 를 우회해서 부른다. 브리핑이 지목한
    "인증을 소비하는 지점" 자체가 커버리지 0 이다 — 아래 중대 참조.
(4) ModRedundant 섹션 위치/[UNVERIFIED] 라벨   🟢 PASS. qc_adapter.sh: 좌표 → ModRedundant →
    gen 기저 → scrf read 순서는 G16 문서의 추가 입력 섹션 순서와 일치하고, 기존 solvent 섹션과
    같은 방식으로 정직하게 [UNVERIFIED — cluster route smoke required] 라벨이 붙어 있다.
(5) grid 불일치 판단 / 자기신고 갭   🟢 grid: 실측 결과 endpoint_opt_rough/freq, ts_opt,
    ts_qst2, ts_opt_from_guess, irc_forward/reverse, relaxed_scan **전부** `Int(Grid=UltraFine)`
    를 갖고 있다(qc_levels.json 직접 grep [확인]) — coder10 의 "TS 체인을 맞췄다"는 판단은
    맞다, proposer 감으로 미룰 필요 없었다. Ω/endpoint_rmsd 미계산은 U56.sh 안에
    `_omega_status`/`_endpoint_rmsd_status` 로 정직하게 자기신고돼 있다 — 문제 없음. 그러나
    §39.42(a)가 요구한 **⟨S²⟩ emission 은 자기신고조차 없이 그냥 없다** — 치명적 항목 참조.
```

### 치명적 (released=true 전에 반드시 고칠 것 — 결과가 조용히 틀리거나 스위트가 깨짐)

- `tests/test_u56_plan_items.py` — **[확인, RED, 직접 실행]** `python3 -m unittest
  test_u56_plan_items` → `Ran 12 tests ... FAILED (failures=3, errors=2)`. 원인: 이 테스트는
  U56-2 가 **6개** 항목(`U56_RC_scan` 포함)이라고 기대하는데, `plan.py::u56_2_items()`는 현재
  **5개**만 반환한다(`U56_RC_scan`/T21-se가 없다) — 이것은 §39.41(d)의 컷 판정("U56-2 is now 3
  attempts... T21-se... MOVED to S3 wave 1")과 정확히 일치하는 **올바른** 소스코드 변화다.
  즉 **소스는 맞고 테스트가 낡았다.** 실패 5건: `test_the_six_items_exist`,
  `test_dependencies_wire_attempts_to_their_endpoint_certs`(KeyError),
  `test_attempt_env_declares_reaction_method_and_endpoint_keys`(KeyError),
  `test_budgets_are_positive_and_marked_estimate_where_unpriced`([ESTIMATE] 마커 카운트가 4→2로
  줄어 임계값 미달 — 상수 블록에서 wall_h/새 필드로 대체되며 마커 수가 바뀐 부작용으로 보인다),
  `test_endpoint_items_declare_role_and_rc_declares_its_missing_input`(R-C reactant 기하가 이제
  트리에 **존재해서** 실패 — 이것도 Q1 해소(§0-p "RESOLVED — it exists... package as
  inputs/li_ec2_radical_reactant.xyz")를 반영한 **올바른** 소스 변화고 테스트만 낡았다).
  → 이 프로젝트 자체가 "RED 테스트를 되돌려서 GREEN으로 만들지 마라, 새 이벤트로 보고하라"는
  규율을 명시적으로 갖고 있다(§0-p.6) — 같은 규율을 여기 적용해 coder10 에게 넘긴다: 테스트를
  §39.41(d)/Q1 해소에 맞춰 갱신할 것, 소스를 되돌리지 말 것.
- `tests/test_u56_deck_builder.py` — **[확인, RED, 직접 실행]** `Ran 15 tests ...
  FAILED (failures=2, errors=1)`. `TestScanWindowIsEnforcedAgainstConfig`가 §39.39(d)의 옛
  스캔 스키마(`cfg["u56_2"]["scan"]["n_steps"]/["step_ang"]`, `b0f_deck.SCAN_STEPS_MIN/MAX`)를
  참조하는데, `b0f_deck.scan_params()`는 이미 §39.42(b)의 개정 스키마(coarse/refine 분리,
  `COARSE_STEPS_REGISTERED` 등)로 바뀌어 5-tuple을 반환한다 — `test_defaults_are_inside_the_window`
  는 `ValueError: too many values to unpack (expected 2, got 5)`로 **에러**(실패조차 아니고 API
  형태 자체가 다르다). 같은 이유로 나머지 2건도 실패. 이 모듈 역시 소스는 §39.42(b)를 정확히
  반영했고(`config/b0_reactions.json`의 `u56_2.scan` 블록도 새 스키마로 갱신돼 있음 [확인]),
  테스트만 옛 스키마를 겨눈다.
- `sei_pilot/criteria/g16.py::parse_s2` (⟨S²⟩ 파서, §39.42(a) 요구) — **[확인] 호출자 0곳,
  테스트 0곳.** `payload/endpoint_prep.sh`의 f1_observables 방출 블록(그리고
  `config/f1_required_observables.json`의 바인딩 emit-list)에 ⟨S²⟩ before/after 가 전혀 없다
  — grep 으로 `spin`/`S\*\*2`/`annihilat` 전부 0 hits(파서 정의 파일 자신 제외). §39.42(a)는
  이것을 "REQUIRED EMISSION at both endpoint stages"라고 못박았고, 05_STATE.md 는 이것을
  coder10 작업 목록에 올려놨다. 더 나쁜 부분: U56.sh 의 Ω/endpoint_rmsd 는 각각
  `_omega_status`/`_endpoint_rmsd_status` 로 "[NOT IMPLEMENTED]"를 **자기신고**하는데, ⟨S²⟩는
  그 자기신고조차 없다 — f1_required_observables.json 자신의 규율("a missing observable ...
  must be reported as absent rather than inferred")을 어긴다. 이것은 §39.39(h)가 발견한
  "roles.mapping_for 는 있는데 호출자가 0곳"과 같은 SCOPE 결함이 `parse_s2`에서 재발한 것이다.
  → 이 입력이면 이렇게 틀린다: R-C reactant(환원 EC 라디칼 음이온, doublet UKS)처럼 스핀 오염이
  현실적인 종에서 endpoint_prep 가 "converged, n_imag==0"을 찍어도, 그 UKS 기준이 심하게 오염돼
  있었는지 아무도 모른다 — "우리가 인증했다고 생각한 종이 아닐 수 있다"(스펙 원문)는 경고가
  코드에 반영되지 않았다.
- `config/b0_reactions.json`의 `u56_2.irc_hessian_source` 주석 — **[확인] 과대 해석/미배선.**
  주석은 "`.chk 이관 배관은 스위치와 무관하게 항상 동작한다`"고 적혀 있지만, `payload/U56.sh`
  (irc 생성부, `for dir in forward reverse; do sei_qc_input ... irc_${dir} ...`)에는 **어떤
  `%chk` 이관도 없다** — `qc_adapter.sh`가 job마다 `%chk=<basename>.chk`를 자동으로 쓰므로
  `ts_opt.chk`와 `irc_forward.chk`/`irc_reverse.chk`는 이름부터 다른 별개 파일이고, 아무도
  복사/링크하지 않는다. `irc_forward_rcfc`/`irc_reverse_rcfc`(qc_levels.json에 이미 존재)도
  U56.sh 어디서도 선택되지 않는다. → 이 입력이면 이렇게 틀린다: 나중에 lead/사용자가 이
  주석을 믿고 `irc_hessian_source: "readfc"`로 스위치를 올리면, 존재하지 않는(또는 이름이 안
  맞는) chk 를 rcfc 가 기대하게 되어 job 이 죽거나 — 최악의 경우 같은 디렉터리에 우연히 남은
  이전 스테이지의 chk 를 rcfc 가 읽어 **엉뚱한 곡률의 IRC 를 조용히 완주**시킬 수 있다(ADR-107
  류의 "고정 경로가 조용히 틀린 파일을 읽는다" 패턴과 같은 모양). 현재 상태(항상 calcfc, 항상
  스위치 무시)는 화학적으로는 안전하지만(P1 앵커와 동일 관례), 절감(§R39.15 4a, ~510–1,630
  core-h/attempt)은 실현되지 않았고 그 사실이 코드에 반영되지 않았다.

### 중대

- `tests/test_endpoint_route_parity.py` — **[확인] §39.41(b)가 명시적으로 요구한 폭 넓히기가
  안 됐다.** 스펙 원문: "extend the same `_surface_tokens` comparison to `ts_opt` / `ts_qst2` /
  `ts_opt_from_guess` / `irc_forward` / `irc_reverse` against the endpoint routes. That is the
  executable form of C-8.1(ii) and it would have caught this." 현재 테스트는 여전히
  `endpoint_opt_rough` ↔ `endpoint_opt_freq` 비교(C-8.1 clause (i))만 한다. 지금 데이터는
  우연히 맞다(grid 실측 [확인], 위 (5) 참조) — 하지만 이 프로젝트가 같은 자리에서 **두 번**
  당한 결함(grid 누락)을 세 번째로 잡을 회귀 테스트가 여전히 없다. 이번 라운드에서 가장
  명시적으로 지시된 가드 확장인데 누락됐다.
- `config/b0_reactions.json`의 최상위 `u56_2._doc` 문자열이 낡았다 — "4 single-/double-ended
  TS attempts... R-A x {QST2, relaxed_scan} + R-B x relaxed_scan + R-C x relaxed_scan"이라고
  적혀 있는데, 바로 아래 `_endpoint_items` 필드와 `plan.py`(현재 3 attempts, T21-se 없음)와
  모순된다. 05_STATE.md 자신이 "SUPERSEDED — quote only the last" 규율을 두 번 적용한 바로
  다음날 같은 모양의 실수다. 기능에는 영향 없지만(코드는 `_doc`를 안 읽는다) 다음 리더가 이
  줄만 보고 U56-2를 "4 attempts"로 오독할 수 있다.
- `payload/U56.sh` 의 인증서 해석 경로(`resolve()`, endpoint_prep 산출물 → cert dict)가
  `test_c8_gate.py`의 어떤 테스트에서도 실행되지 않는다 — 전부 `SEI_C8_ENDPOINTS_JSON` 주입
  경로만 탄다. 매핑 자체는 검토 결과 문제없어 보이지만(위 (3)), 실제 프로덕션 경로가 통합
  테스트 커버리지 0인 채로 released=true 후보에 들어가는 것은 이 항목 리스트에서 가장 위험한
  단일 코드 경로다.

### 확인한 것 (문제 없음 — 근거를 남긴다)
- `Int(Grid=UltraFine)`가 `qc_levels.json`의 관련 8개 job_type 전부(endpoint_opt_rough/freq,
  ts_opt, ts_qst2, ts_opt_from_guess, irc_forward/reverse, relaxed_scan)에 있다 — §39.41(b) 수정
  완료 [확인, grep].
- `tests/test_c8_gate.py` 22개 전부 GREEN — subprocess 수준으로 U56.sh 전체 체인(relaxed_scan
  단끝단, qst2 양끝단, mapping emit, exit 6/8 구분, R-12 fingerprint)이 실제로 돈다 [확인,
  직접 실행].
- `b0f_deck.py`의 d(Li–O_break) covariate(§39.42(a) 요구 ①) 구현 확인, C-3 스타일(판정 없이
  데이터만) 정확히 준수.
- array 충돌(ADR-107류) 패턴 없음: U56-2 항목 전부 `array=None`, 별도 Item — 공유 job dir 문제가
  구조적으로 발생할 수 없다 [확인, `test_no_item_is_an_array` GREEN + 소스 직접 읽음].
- release 게이트 자체(코드가 flag를 안 올림, released=false 동안 default_items()가 U56 항목을
  안 실음)는 deck_verified의 S-2 패턴과 구조적으로 동일 — R-11/ADR-109 요구를 만족한다.

### 확인하지 못한 것
- `payload/U56.sh`의 `resolve()`(실제 endpoint_prep 산출물 소비 경로)를 직접 실행하는 통합
  테스트가 없어서, f1_observables → cert 매핑이 **실전에서** 옳게 동작하는지는 코드 읽기로만
  판단했다(위 (3), 정적으로는 문제 없어 보인다). 실제 G16 로그로 한 번 태워보기 전까지는
  [UNVERIFIED]로 남겨야 한다.
- 리뷰 도중 소스가 라이브로 편집되고 있었다 — 이 리뷰가 가리키는 "5개 항목/wall_h 배선" 상태가
  lead 가 다음에 열어볼 때도 최종 상태인지는 재확인이 필요하다. 특히 위에 적은 두 테스트
  파일의 RED 여부는 coder10 의 다음 커밋 이후 다시 돌려봐야 한다.

---

## 2026-08-20 (같은 날, 추가 요청) — critic10 리뷰: P6 κ-anchor gate — `sei_pilot/collect.py::collect_p6` (lead 요청, coder11 발견 followup)

**대상**: `sei_pilot/collect.py:499-580`(`collect_p6`), `payload/P6.sh`(anchor 산출물 필드),
`tests/test_producer_consumer.py`(생산자/소비자 경계 검사, 관련성 확인용). U56-2 스코프 밖 —
lead 요청으로 별도 판정.

### 판정: 중대 결함 확인, 이번 라운드 κ=1.218 수치 자체는 위험하지 않음(별도 채널로 확인 요함)

**게이트 결함 — [확인].** `collect_p6`의 `agree`(collect.py:529)는
`declared == requested == nprocshared` 세 값만 비교한다:
```
declared          job KEY 이름에서 파싱(P6_t16 -> 16)               -- 우리가 지은 이름
requested         SEI_TOTAL_CORES 환경변수                          -- 우리가 스케줄러에 요청한 값
actual_nprocshared  P6.sh:64 `grep '^%nprocshared' anchor.gjf`      -- **우리가 그 값으로 직접 쓴**
                    anchor.gjf 파일을 도로 읽은 것 (Gaussian 실행 로그가 아니다)
```
세 값 모두 **같은 상류(우리 자신의 제출 파이프라인이 믿는 코어 수)에서 파생**된다 — 서로 다른
독립 소스가 아니다. 반면 `cores_observed`(P6.sh:66, `nproc` — **cgroup/affinity 를 통과한 뒤
커널이 실제로 보여준 값**, 이 넷 중 유일하게 독립적인 실측)는 `collect_p6`가 딕셔너리에
싣기는 하지만(collect.py:548) **`agree`/`valid` 게이트 어디에도 안 들어간다.**

→ 이 입력이면 이렇게 틀린다: 스케줄러/cgroup 결함으로 실제 1코어만 배정됐는데 제출 파이프라인이
(ADR-107 류의 템플릿 버그로) `SEI_TOTAL_CORES`를 여전히 16으로 내보내면, `declared=16`,
`requested=16`, `actual_nprocshared=16`(우리가 그 값으로 **직접 쓴** anchor.gjf 를 도로 읽은 것)
**셋 다 일치**하고 `valid=True`로 κ 산출에 들어간다 — `cores_observed=1`인데도. 이건 이 함수
자신의 docstring(collect.py:502-506)이 "이번 라운드 내내 싸운 실패 부류의 정점"이라고 명시한
바로 그 16배 오차 시나리오이고, 이 게이트가 막는다고 주장하는 바로 그 것이다. ADR-107(P1b/P5
가 서로 자기선언끼리만 일치하고 실제 배정과 대조 안 함)과 같은 모양.

**`cores_observed_all` — [확인] 순수 사장 데이터.** `grep -rn "cores_observed_all"` 결과
`payload/P6.sh:87`(쓰는 곳) 단 한 곳 — Python 소스 어디에도 이 문자열이 없다. `nproc --all`은
cgroup 을 무시하고 노드 총 논리 코어 수를 읽으므로, 이 값 **단독으로는** 배정 불일치를 못
잡는다(오버서브스크립션이든 정상이든 노드가 68코어면 항상 68). **`cores_observed`와 짝지어야만
의미가 생긴다**: `cores_observed == cores_observed_all`(cgroup 미적용 — 이 job 이 노드 전체를
본다, 다른 job 과 격리 안 됐을 위험) vs `cores_observed < cores_observed_all`(cgroup 이 정상
작동, N 코어로 격리됨) — 이 비교가 코드 어디에도 없다. 🔴 coder11 의 질문("cgroup 미적용 노드
오탐 방지 의도인지, 그냥 빠진 건지")에 대한 내 1차 판정: **소스만으로는 원래 의도를 확정할 수
없다** — 필드 이름 자체(`_all`)와 `cores_observed`와의 자연스러운 짝짓기는 "cgroup 미적용
탐지용으로 설계됐다"는 가설을 지지하지만, 실제로 그 비교 코드가 존재한 적이 없다(git 이력
확인은 이 리뷰 범위 밖). 의도가 무엇이었든 **현재 상태는 동일하다: 쓰기만 하고 아무도 안
읽는다.**

**메타 테스트가 왜 이걸 놓쳤는지 — [확인].** `tests/test_producer_consumer.py`는 정확히 이
결함 계열("만들어 놓고 아무도 안 읽는 값")을 잡으려고 만든 테스트다. 그런데 `p6_anchor.json`이
`WHOLE_DICT_PASSTHROUGH`(파일 단위 면제 목록)에 "collect_p6 가 필드를 개별로 읽는다"는 사유로
올라가 있다 — `cores_observed`엔 절반만 맞고(읽긴 하지만 검증엔 안 씀), `cores_observed_all`엔
아예 틀리다(읽지도 않음). 이 테스트 자신의 docstring(98번째 줄)이 "이 검사는 파일 단위만
본다 — 필드 단위 유실은 못 잡는다"고 이미 자기 한계를 적어놨다 — 그 한계가 정확히 여기서
발동했다.

**심각도**: 이번 라운드 결과를 조용히 틀리게 만들지는 않았다(lead 가 `cpu_machine_pilot_results/`
의 실측 3개 앵커에서 declared=requested=cores_observed=nprocshared 전부 일치한다고 직접
확인함 — 나는 원 브리프의 "사용자 결과 트리 접근 금지" 지시를 지키기 위해 그 파일을 직접 다시
열지 않았다, 아래 "확인하지 못한 것" 참조). 하지만 **게이트 자체는 5개월 일정의 단일 임계
변수(κ)를 지킨다고 주장하면서 그 변수의 유일한 독립 실측값을 제외한다** — 다음 라운드에
κ를 다시 재는 잡이 다른 큐/노드 설정에서 돌면 이 구멍이 조용히 열린다.

### 치명적 (κ 재측정 전에 고칠 것)
- `collect_p6`의 `agree`(collect.py:529)가 `cores_observed`를 비교에서 뺀다 — `declared`,
  `requested`, `actual_nprocshared` 셋 다 우리 자신의 제출 파이프라인에서 파생된 값이고,
  커널이 실제로 준 코어 수(`cores_observed`)와 대조하는 게 하나도 없다. `agree = (declared
  is not None and declared == requested == nprocshared == cores_observed)`로 넓히고, 불일치
  시 기존 `invalid_reason` 메시지에 `cores_observed` 값을 함께 실어야 한다.

### 중대
- `cores_observed_all`이 payload 에서 쓰이고 Python 어디에서도 안 읽힌다 — 순수 사장 데이터.
  `test_producer_consumer.py`의 파일 단위 면제(`WHOLE_DICT_PASSTHROUGH["p6_anchor.json"]`)가
  이 필드 단위 유실을 가렸다. 최소한 `cores_observed_all`을 entry dict 에 실어 사람이 읽을 수
  있게 하거나(cgroup 미적용 진단용), 정말 불필요하면 payload 에서 지우고 그 이유를 적어라 —
  "지어놓고 안 읽는 값"으로 방치하지 마라(§39.0 종결 규율).

### 확인하지 못한 것
- 이번 라운드 실측 κ=1.218 이 실제로 안전한지는 `cpu_machine_pilot_results/`의
  `p6_anchor.json` 3건을 내가 직접 다시 읽지 않아서 [확인] 표시를 못 한다 — 원래 브리프의
  "사용자 결과 트리 접근 금지" 지시를 이번 파생 요청에도 그대로 적용했다. lead 의 직접 확인을
  근거로 삼지 않는다는 원칙과 충돌하지만, 접근 금지 지시가 더 상위라고 판단했다 — lead 가
  내게 그 트리를 직접 열어도 된다고 명시하면 그때 재확인하겠다.
- `cores_observed_all`의 원래 설계 의도(cgroup 미적용 탐지용으로 처음부터 기획됐는지, 필드를
  일단 다 찍어두고 나중에 정하기로 했다가 잊힌 것인지)는 소스만으로는 판별 불가 — 이 리뷰
  범위에서 커밋 이력/HANDOFF 문서까지는 보지 않았다.

### 추가 (같은 날) — lead 보고로 판정 강화, coder11 의 "의도적 면제" 가설 반증됨

🔴 **[lead 직접 보고, critic10 미확인 — 접근 제한 유지]** lead 가 `cpu_machine_pilot_results/`의
`p6_anchor.json` 실측을 직접 읽어 전달: **t1 의 `cores_observed`=1, t64 의 `cores_observed`=64**.
만약 이 클러스터에서 `nproc`이 cgroup/affinity 를 무시하고 노드 총 코어(예: 68)를 그대로
반환했다면 t1/t16/t64 셋 다 같은 값(68)이 나왔어야 한다 — 그런데 **셋이 서로 다르고 요청한
코어 수와 정확히 일치**했다. ⟹ **이 클러스터에서 `nproc`은 cgroup/affinity 를 정확히
반영한다**는 것이 측정으로 확인됐다(coder11의 "cgroup 미적용 노드에서 오탐 방지를 위해
일부러 뺐을 것"이라는 선의 가설을 반증하는 방향).

**판정 갱신**: "왜 `cores_observed`를 `agree`에서 뺐는지 소스만으론 모른다"에서 → **"이
클러스터에서는 뺄 정당한 이유가 없었다는 것이 측정으로 확인됐다"로 강화한다.** `cores_observed`
는 이 데이터셋에서 노이즈도 상수도 아니라 정확히 요청값을 반영하는 신뢰 가능한 신호였고,
그런데도 게이트가 그것을 무시했다 — 위에 적은 "치명적" 항목의 우선순위를 유지·강화한다(설계
누락이 아니라 실측으로 정당화되지 않는 누락).

⚠ 위 t1=1/t64=64 수치 자체는 critic10 이 직접 읽은 것이 아니라 lead 의 보고에 의존한다 —
"다른 agent 의 말을 근거로 삼지 마라"는 critic 원칙과 "사용자 결과 트리 접근 금지" 지시가
충돌하는 지점이며, 이번에는 후자를 우선했다. lead 가 직접 접근을 승인하면 재확인하겠다.

### 재확인 (같은 날) — [critic10 직접 확인] lead 승인 받아 `cpu_machine_pilot_results/` 진단 목적 1회성 열람

lead 승인(R-13은 "테스트가 사용자 트리를 읽지 않는다"는 규율이지 critic 의 진단 목적 1회성
읽기를 막는 게 아니라는 판단)에 따라
`cpu_machine_pilot_results/sei_pilot_work/jobs/P6_t{1,16,64}/p6_anchor.json` 세 파일을
직접 열었다(읽기만, 수정/삭제 없음). **[확인]**:

```
        declared  requested  cores_observed  cores_observed_all  actual_nprocshared  wall_s
P6_t1          1          1               1                  68                 "1"    1831
P6_t16        16         16              16                  68                "16"     216
P6_t64        64         64              64                  68                "64"     136
```

세 태스크 전부 `declared == requested == cores_observed == actual_nprocshared`(넷 다) 완전
일치, `cores_observed_all`은 세 태스크 모두 68로 **상수**(cgroup 을 무시하고 노드 총 코어를
그대로 반환한다는 앞선 판단과 일치). ⟹ **lead 가 보고한 t1=1/t64=64 수치가 정확했다** — 앞
단락의 "판정 강화"가 이제 [lead 보고] 가 아니라 **[critic10 직접 확인]** 으로 격상된다.

**결론 재확인**:
1. 이번 라운드 κ=1.218 산출에 쓰인 t1/t16/t64 세 앵커는 **넷째 값(cores_observed)까지 포함해
   전부 일치** — 지금 수치는 오염되지 않았다. 게이트의 구멍(`cores_observed` 미비교)은 이번
   라운드에는 발동하지 않았다.
2. `cores_observed_all=68`이 세 태스크에서 동일한 것은 이 필드가 (예상대로) cgroup 과 무관한
   노드 상수라는 것을 실측으로 재확인한다 — `cores_observed`와 짝지어야만(1/16/64 vs 68) 의미가
   생기는데 그 비교 코드가 없다는 앞선 판정도 그대로 선다.
3. `p6_anchor.json` 자체가 이미 `_gate_note` 필드로 "declared == requested == nprocshared 가
   아니면 [INVALID]"라고 ADR-048 규칙을 그대로 박아 놓았다 — `cores_observed`는 규칙 문면에도
   없다. 게이트의 누락이 코드 한 곳의 실수가 아니라 규칙 정의 자체(ADR-048)에서부터
   `cores_observed`를 빼놓은 것임을 확인한다. 넷째 실측값을 규칙에 넣는 결정은 coder10/coder11
   수정 시 `_gate_note` 문구도 함께 갱신해야 한다(코드와 산출물 주석이 다시 갈리지 않도록).

**판정 최종**: 중대(치명적 항목 유지) — 이번 라운드 κ 수치는 안전, 게이트 자체는 넷째 실측값
없이 5개월 일정의 단일 임계 변수를 지킨다고 주장하는 구조적 결함. 다음 κ 재측정 전에 고쳐야
한다.

---

## 2026-08-20 — critic10: 다음 리뷰 예정 항목 (coder10 배치 완료, lead 전달, 접수만)

lead 전달: coder10 이 지시 7건 배치를 완료(suite 1379, failures 2 — freeze-signal 뿐, skipped 14).
P1 route 검증(tarball 대비 live 소스 UltraFine 일치)·E21 cap·T21-se 제거는 lead 가 소스에서
직접 확인 완료. **급하지 않음(released=true 전이면 됨)** — 아직 착수하지 않았고, coder10 이
idle 확인되면 다음 라운드에서 본다. coder10 이 스스로 요청한 리뷰 항목 5건, 기록만 해둔다:

```
1. R-C ≥3 seed 프로토콜 — payload 런타임 자동화 안 됨(지금은 provenance 로만 전달, 새 입력
   기하는 수동). §39.42(a) Q1 요구사항.
2. "두 basin 이 다르면 GFN2 양쪽 다 scan" — 기록만, 자동화 안 됨.
3. dual-start 에너지 비교(같은 route stage-1 SCF)가 basin 선택 근거로 충분한지 — 화학적 타당성
   판단 필요(critic 영역 아닐 수도, proposer 라우팅 검토).
4. refine 시작점 선택(최댓값 앞 coarse 점 ±0.075 Å 커버)의 타당성.
5. IRC %chk 이관 — per-task 격리(SEI_TASK_FILE_SUFFIX)와 freq-단계-출처 둘 다 구현됐다고
   주장. rcfc 스위치는 꺼진 채 출하(다음 route smoke 까지). 🔴 **이전 리뷰(오늘, 위 항목)에서
   critic10 이 지적한 "config 의 irc_hessian_source 주석이 존재하지 않는 chk 이관 배관을
   있다고 과대해석했다"는 정확히 이 항목과 겹친다 — 다음 리뷰에서 U56.sh 의 IRC 생성부를
   재읽어 실제로 %chk 복사/재사용 코드가 생겼는지, SEI_TASK_FILE_SUFFIX 가 ADR-107 류의
   공유경로 충돌을 정말 막는지 직접 확인할 것. 지금은 접수만 하고 검증하지 않았다.
```

---

## 2026-08-20 — critic10: 최종 트리 재검증 (coder10 응답에 대한 독립 확인, U56-2)

coder10 이 오늘자 리뷰 5개 치명적/중대 항목에 대해 "네가 본 것은 편집 경합 중간 스냅샷"이라고
답하며 최종 트리 상태를 주장했다. **다른 agent 의 말을 근거로 삼지 않는다는 원칙에 따라 전부
직접 재실행·재확인했다** (coder10 의 설명을 읽고 믿은 게 아니라 아래 명령/코드를 내가 직접
실행·읽었다):

```
$ python3 -m unittest test_u56_plan_items test_u56_deck_builder test_endpoint_route_parity \
                       test_endpoint_prep      → Ran 60 tests, OK          [확인]
$ python3 -m unittest test_c8_gate             → Ran 25 tests, OK          [확인]
$ python3 -m unittest discover -p "test_*.py"  → Ran 1379 tests,
                                                  FAILED (failures=2, skipped=14)  [확인]
```
전체 스위트의 실패 2건은 `test_build_stamp.py`의 `test_real_repo_dist_is_fresh` /
`test_correct_root_still_verifies` — tarball 이 오늘 바뀐 소스 파일 목록(정확히 이번 라운드에
손댄 config/b0_reactions.json, f1_required_observables.json, qc_levels.json, U56.sh,
endpoint_prep.sh, qc_adapter.sh, b0f_deck.py 등)보다 낡았다는 **의도된 ADR-086 동결 신호**다
— §0-p.6 규율과 정확히 일치, 새 결함 아님 [확인, 실패 메시지 직접 읽음].

### 항목별 재확인 (소스 직접 읽음)
```
1. test_u56_plan_items    GREEN [확인]. test_the_six_items_exist 가
   test_exactly_the_post_cut_items_exist 로 교체된 것, 5개 항목 확인.
2. test_u56_deck_builder  GREEN [확인]. TestScanRegistrationIsEnforcedAgainstConfig +
   TestRefineDecision(4 case) 존재 확인, 다 통과.
3. ⟨S²⟩                   배선 확인 [확인, 소스 직접 읽음].
     - config/f1_required_observables.json: "s2_both_stages" 항목 존재, wired_as 필드가
       "f1_observables.json fields s2_stage1_rough / s2_stage2_tight (payload/endpoint_prep.sh,
       criteria/g16.py::parse_s2)" 로 정확히 가리킨다.
     - payload/endpoint_prep.sh:366-367 — `g16.parse_s2(rough_text)["last"]` /
       `g16.parse_s2(text)["last"]` 실제 호출 확인(문자열 존재가 아니라 호출 확인).
4. chk 이관                U56.sh:427-464 직접 읽음 [확인]. TS_CHK/IRC_CHK 이름이
   `${SEI_TASK_FILE_SUFFIX:-}`를 물고, qc_adapter.sh:292-293 의 `%chk=` 생성 규칙과
   **정확히 같은 접미사 규칙**을 쓴다(둘이 따로 놀면 이름이 어긋나 조용히 실패하는데,
   직접 대조해 일치함을 확인했다). 출처 주석("freq block of the TS job (final chk state),
   NOT the CalcFC guess Hessian")이 코드 배치(TS_LOG 는 opt=(ts,calcfc) freq 잡의 로그,
   그 잡의 chk 는 freq 가 마지막에 덮어쓴다)와 실제로 맞는다. rcfc 스위치는
   `config.load("b0_reactions.json").u56_2.irc_hessian_source` 가 "readfc"일 때만
   `_rcfc` job_type 을 선택하고 기본은 calcfc — 이전에 내가 지적한 "존재하지 않는 배관을
   과대해석했다"는 더 이상 사실이 아니다. **철회한다.**
5. route parity 확장       test_endpoint_route_parity.py::TestTsIrcFamilySitsOnTheSameSurfaceAs
   TheEndpoints 존재 확인, ts_opt/ts_opt_from_guess/ts_qst2/irc_forward/irc_reverse/rcfc
   변형/relaxed_scan 전부 커버, 직접 실행 GREEN.
```

### 판정 갱신: 치명적 4건 전부 해소 확인(직접 검증) — U56-2 소스에 대한 이전 FIX-THEN-RUN 의
**RED-test 사유는 소멸했다.**

### 아직 남은 것 (오늘 지적한 "중대" 항목 중 coder10 응답이 다루지 않은 것 — [확인, 여전히 존재)
```
A. config/b0_reactions.json 의 최상위 u56_2._doc 문자열이 여전히 낡았다 — "4 single-/double-
   ended TS attempts... R-A x {QST2, relaxed_scan} + R-B x relaxed_scan + R-C x relaxed_scan"
   [재확인, python3 로 직접 읽음, 그대로다]. 기능 영향 없음(코드가 _doc 를 안 읽는다), 다음
   리더가 오독할 수 있는 주석 불일치. 사소하지만 미해결로 기록한다.
B. payload/U56.sh 의 resolve()(endpoint_prep 실제 산출물 -> cert dict, f1_observables.json
   소비 지점)를 직접 태우는 테스트가 여전히 없다 [재확인, test_c8_gate.py 에
   "f1_observables"/"endpoint_tight.meta.json"/"SEI_U56_REACTANT_ENDPOINT_KEY" 문자열
   0 hits]. 모든 C-8 게이트 테스트가 SEI_C8_ENDPOINTS_JSON 주입 채널만 탄다 — 프로덕션에서
   실제로 쓰이는 인증서 해석 경로 자체는 여전히 통합 테스트 커버리지 0.
```
released=true 전에 B 는 한 번은 닫는 게 좋다(released 이후 첫 실행이 이 경로의 첫 실전 테스트가
되는 셈이라 — U-74 교훈과 같은 모양). A 는 사소, 편할 때 고치면 됨.

**최종 판정(U56-2 소스, 이 라운드): OK(중대 2건 B/A 는 released 전 처리 권고, 급하지 않음)**.
BLOCK/치명적 사유 없음.

---

## 2026-08-20 — critic10 review: coder11's accumulated batch (G-SCAN-2 v3, Ω/spectator/bracket, C-2.1/C-2.2/condition-7 (B+), CHEMICAL/BUDGET/UNKNOWN/MIXED classification, GFN2 bidirectional scan producer, rcfc chk-handoff refusal, test_guard_reach.py heredoc fix)

**Note**: from this entry on, review notes are in English per the user's language-policy directive
(lead, 2026-08-20).

**Scope**: `sei_pilot/b0f_deck.py` (`gscan2_decision`, `scan_barrier_ev`), `sei_pilot/guards.py`
(`irc_verdict`, `irc_direction_ok`, `classify_indeterminate`, `bracket_check`),
`sei_pilot/gfn2_scan.py`, `sei_pilot/curvature.py` (Ω), `payload/U56.sh` (chk handoff / rcfc
refusal / IRC completion emission), `tests/test_u56_deck_builder.py`,
`tests/test_irc_truncation_c2.py`, `tests/test_bracket_check.py`, `tests/test_omega_mode_character.py`,
`tests/test_gfn2_scan.py`, `tests/test_guard_reach.py`, `tests/test_c8_gate.py`. This is a SOURCE
review (`dist/` frozen, ADR-086/057; nothing here has been packaged).

**Method**: read `05_STATE.md` §1–3 and the relevant `02_METHOD_SPEC.md` sections (§39.48, §39.50,
§39.55, §39.59, §39.63–65) for the claimed physics/design, then read the source directly, then ran
the tests myself rather than trusting the lead's or coder11's summary.

### Verdict: OK for this round, ONE real defect found — not yet reachable in production, must be
### fixed before B+ (the terminal-optimisation piece) is wired to real IRC data

### Confirmed correct (5 items lead asked about)

1. **G-SCAN-2 barrier-agreement fix (clause ii) — CORRECT.** [confirmed by source read + test
   execution] `b0f_deck.py:216` `BARRIER_REFERENCE_FRAME = {"forward": 0, "reverse": -1}`.
   Traced the physical setup in `gfn2_scan.py::bidirectional_plan`: forward scans reactant→product
   (`d0→d1`), reverse scans product→reactant (`d1→d0`), so `reverse[-1]` genuinely is the reactant
   end — the reference-frame choice is consistent with the actual scan geometry, not just asserted.
   `test_u56_deck_builder.py::TestGScan2V3` (11 cases, all pass, including
   `test_the_measured_r_a_pair_passes_end_to_end` against a REAL xtb log fixture pair, not just
   synthetic numbers) — ran directly: 34/34 OK.
2. **`test_guard_reach.py` heredoc regex widening — CORRECT.** `_HEREDOC_PY_RE =
   re.compile(r"<<'(PY[A-Z0-9_]*)'\n(.*?)\n\1\n", re.S)` uses a backreference to the captured
   delimiter name, so it cannot cross-match an unrelated heredoc sharing only the `PY` prefix — a
   naive `PY[A-Z0-9_]*` without the backreference would have been a weaker, more error-prone fix.
   ⚠ Caveat: the first run I did showed a spurious failure
   (`test_deferred_guards_have_no_external_caller_yet` for `gscan2_decision`) that vanished after
   clearing `tests/__pycache__/*.pyc` — a stale bytecode cache from before the dict entry was moved
   from `DEFERRED_NO_CONSUMER_YET` to `EXPECTED_REACHED`, not a real defect. Recommend `coder11`/
   whoever runs the suite next clear `__pycache__` first when checkpoints land close together in
   time — I nearly reported a false BLOCKER from this.
3. **rcfc chk-handoff refusal — CORRECT, and honestly scoped.** `U56.sh:774` refuses an IRC
   direction (writes `irc_<dir>.refusal.json`, `cause_class: "unknown"`, no silent fallback to
   `calcfc`) iff `HESS_SRC == "readfc"` and `CHK_COPIED != "true"`. Read the full block: no mid-run
   method switch, refusal is per-direction (not a whole-attempt abort), correctly excluded from
   both the chemical and budget denominators. `TestU56RcfcRefusesWithoutItsHessian`'s own docstring
   states plainly that this is a SOURCE-level check only (no env-override channel exists without
   touching the shape-locked PBS template) — an honest scope statement, not a concealed gap.
4. **Ω / spectator test / bracket check — CORRECT**, `test_omega_mode_character.py` (18 tests) and
   `test_bracket_check.py` (11 tests) both green, including the mass-weighted-vs-unweighted Ω
   regression (the unweighted shortcut is pinned as an explicit NEGATIVE case, not just deleted)
   and the bracket check's `awaiting_calibration` accounting for R-B/R-C's missing product side
   (counted, never silently read as "never fires" — matches §39.65's own caveat).
5. **C-2.1/C-2.2/condition-7 (IRC truncation gate, branch a/b) — CORRECT for what's built.**
   `test_irc_truncation_c2.py` (14 tests) green; `irc_direction_ok` correctly refuses a truncated
   path with no B+ record (`"B+ was not run"`) and correctly accepts branch (b) only when
   `completion.truncated` AND `bplus.agreement is True`. Matches STATE's own disclosure that B+
   itself is not built yet and today's behaviour is "the arm does not run," not "the gate quietly
   passes" — verified true from source, not just asserted in prose.

### Critical (new finding, not previously logged) — `classify_indeterminate` mis-tags a B+
### bifurcation disagreement as `budget`, not `chemical`

**[confirmed by direct execution, not just reading]**:
```python
>>> guards.irc_verdict(direction(agreement=False), direction(agreement=True), E_TS)["cause_class"]
'budget'
```
where `direction(agreement=False)` is exactly `test_irc_truncation_c2.py`'s own
`test_bplus_disagreement_is_a_bifurcation_and_stays_indeterminate` fixture — the case the project's
own comments describe as "a bifurcation between its two start points," which is a CHEMICAL finding
(the IRC found evidence of a genuine branch, not a budget/plumbing artefact).

**Root cause**: `classify_indeterminate` (`guards.py:339`) classifies by substring-matching the
*prose* failure message against `INDETERMINATE_BUDGET_MARKERS = ("truncated", "maxpoints", "wall",
"budget", "timeout", "maxcycles", "step budget", "cap")`. Every truncated-path failure message
(`irc_direction_ok`, line ~190) starts with `"IRC was TRUNCATED (%s) %s"` regardless of whether the
`%s %s` that follows says `"B+ DISAGREED (a bifurcation...)"` or `"B+ was not run"` — so the
`"truncated"` marker fires and classifies BOTH as `budget`, before the classifier ever gets to look
at the B+-specific text. There is no `"chemical"` marker list at all; `"chemical"` is only the
fallback when neither `unknown` nor `budget` markers match, and `"truncated"` always matches first.

**Why this matters, in the project's own terms** (`guards.py:314-324`, unedited): *"A large BUDGET
class is itself a diagnostic: the caps are wrong (spend more per attempt). A large CHEMICAL class
means the method is wrong (stop and fix it). OPPOSITE responses."* and *"`1/p` may ONLY be computed
over the CHEMICAL-class denominator."* If a real B+ bifurcation lands in the `budget` bucket: (1)
it is silently excluded from the `1/p` chemical denominator that wave-1 sizing depends on, and (2)
it feeds the diagnostic that says "the caps are wrong, spend more" — the wrong remedy for a genuine
path bifurcation, which no larger `maxpoints` cap fixes.

**Why it hasn't bitten yet**: B+ itself ("two terminal optimisations per direction") is not wired
to real IRC data — `bplus.agreement` is currently only ever set by test fixtures, never by a real
payload run (confirmed: no `"bplus"` key writer exists in `U56.sh` today, only `"bplus": {}`
implicitly absent, matching STATE's own "B+ terminal-opt piece itself not yet built"). So this is
dormant, not currently producing a wrong number in any round's reply. **It WILL bite the moment B+
is wired**, silently, because the existing test for this exact scenario
(`test_bplus_disagreement_is_a_bifurcation_and_stays_indeterminate`) only asserts
`status == "indeterminate"` and that the message contains `"B+ DISAGREED"` — it never asserts
`cause_class`, which is exactly the gap that let this ship unnoticed.

**Recommended fix**: derive `cause_class` from the STRUCTURED fields already available
(`completion.get("truncated")`, `bplus.get("agreement")`) rather than string-mining the prose the
same function just generated one line earlier — e.g. `bplus.get("agreement") is False` ⟹
`"chemical"` (a positive bifurcation measurement) BEFORE the generic `"truncated"` budget check,
`completion.get("truncated") and bplus is empty` ⟹ `"budget"` (unchanged). This also removes a
second latent hazard: the current design means classification silently depends on the EXACT wording
of a human-readable message, so a future rewording of "B+ DISAGREED" for clarity (this project has
done exactly that kind of edit before) would silently change classification with no test failure
pointing at the cause.

### Confirmed clean, no notes
GFN2 bidirectional scan producer (`gfn2_scan.py`) — `test_gfn2_scan.py` (10 tests) green, including
a fixture pair (`.inp`/`.log`) the test's own docstring states is a real xtb-produced input/output
match, not synthetic. Full suite: `Ran 1467 tests`, `failures=2` (both `test_build_stamp`'s
dist-freshness freeze signal — expected, ADR-086, not a new defect), `skipped=14` — ran directly,
not inherited from either report.

### Not verified in this pass (time-boxed, flagging rather than silently skipping)
- Δ_shell shell-averaging arithmetic (§3's non-saturating 0.366/0.190 eV figures) — not re-derived
  from raw data this pass; out of this batch's stated scope (lead's message did not list it).
- The GFN2 producer's own xtb `$scan` syntax correctness against a live xtb binary — accepted on
  the fixture's own claim of having been run for real; did not re-invoke xtb myself.

---

## 2026-08-20 — critic10 adversarial follow-up: `classify_indeterminate` fix verified, `bracket_check` §39.66 direction-aware version verified, plus THREE new findings from the two areas coder11 asked for adversarial attention on

**Scope**: verifying coder11's fix + §39.66 landing, then adversarial review of (a)
`gfn2_scan.parse_scan_log`'s frame-advance loop and (b) the four rcfc source-level-only assertions,
per coder11's explicit request.

### Verified: the `classify_indeterminate` fix is correct
`guards.py`'s `irc_direction_ok` now attaches a structured `cause_tags` list per clause instead of
substring-mining prose; `irc_verdict` derives `cause_class` from the union of tags via
`_class_from_tags`. Ran it directly on the exact reproduction from my last review:
```
irc_verdict(direction(agreement=False), direction(agreement=True), E_TS)["cause_class"] == "chemical"
```
Confirmed. `test_a_bplus_disagreement_is_CHEMICAL_not_budget` and
`test_classification_does_not_depend_on_message_wording` both exist and pass. Good root-fix, not a
patch — agreed with coder11's framing that a targeted reorder would have left every OTHER clause
still classified by substring.

### Verified: §39.66 direction-aware `bracket_check` is correctly implemented
`direction == "form"` refuses on `saddle > reactant`, `direction == "break"` refuses on
`saddle < reactant`, `direction is None` → `applicable: false, non_monotonic`, counted not dropped.
`derive_direction` (`gfn2_scan.py`) correctly measures monotonicity from the actual scan trajectory
rather than accepting a declared field, returns `None` on non-monotonic or <2 points — matches
§39.66(b)'s design exactly. `test_the_breaking_bond_half_alone_does_NOT_catch_p1` (the test coder11
flagged as the sharpest one to attack) ran directly: PASS, and it is doing what it claims — a
positive control that keeps credit attached to the mechanism/form coordinate, not the breaking bond.

### NEW FINDING 1 (answers coder11's item (a)) — `parse_scan_log`'s frame-advance loop silently
### drops an entire subsequent well-formed frame when a preceding frame's declared atom count
### doesn't match its actual body length. Reproduced by direct execution, not hypothetical.

```python
text = ("3\n energy: -1.0 xtb: 6.7.1\nH 0 0 0\nH 0 0 1\n"      # frame 1: declares 3 atoms, only 2 present
        "2\n energy: -2.0 xtb: 6.7.1\nH 0 0 0\nH 0 0 1\n")     # frame 2: complete and well-formed
gfn2_scan.parse_scan_log(text)
# -> n_points = 1  (frame 2 is GONE)
# -> warnings = ['frame 1 declared 3 atoms but 2 were readable']   -- says nothing about frame 2
```
**Mechanism**: the geometry-reading loop breaks early when a line fails `len(f) >= 4` (here, frame
2's own header line `"2"` gets consumed as if it were one of frame 1's coordinate lines, since the
range `i+2 : min(i+2+n, len(lines))` is built from the DECLARED `n`, not from how many lines were
actually read). The advance step `i = i + 2 + n` then ALSO uses the declared `n` unconditionally,
landing `i` on frame 2's COMMENT line (not its header) — `head.isdigit()` fails, the loop
skip-scans one line at a time through the rest of frame 2's own content, and reaches EOF having
silently consumed it. **No warning at all is emitted for the lost frame** — the only warning
present describes frame 1's mismatch, which does not communicate that a full frame vanished after
it.

**Why this is not a contrived edge case for this codebase specifically**: this project has been
bitten repeatedly by exactly this shape of defect (a truncated/partial write that looks complete —
C-2.2/condition-7's entire IRC-truncation gate exists for the DFT-log version of this same problem;
C-13 treats a wall-clock-killed run's partial output as data, never silently discarded). A
`xtbscan.log` cut short by a wall-clock kill mid-frame, or corrupted by a partial disk write, is a
realistic way to get a declared/actual atom-count mismatch in production, and this producer feeds
`gscan2_decision` — the gate that decides whether to fund a ~660–6,400 core-h DFT attempt. A
silently truncated profile could be missing its true energy maximum and pass a hysteretic path that
should have fired, or (less likely but possible) drop the frame that would have kept a clean path
under the tolerance and cause a false FIRE.

**Test coverage as it stands**: one fixture (a real, complete log) plus one synthetic case that only
tests a missing ENERGY line on an otherwise correctly-sized frame — never a declared/actual LENGTH
mismatch, which is the case that triggers the frame-loss. Coder11's own uncertainty about this loop
was well-placed.

**Suggested fix**: advance `i` by `2 + len(geometry)` (what was ACTUALLY consumed) rather than
`2 + n` (what was DECLARED) when they differ, and/or verify the line at the computed next-frame
position `.isdigit()` before committing to the jump, falling back to a resync scan if not. At
minimum, emit a warning that explicitly says trajectory parsing may have desynchronised from this
point forward, so a corrupted log cannot look identical to a slightly-short one to any consumer
that only checks `n_points` and `warnings` are non-empty.

### NEW FINDING 2 (found while answering coder11's item (b)) — `collect_u56` captures
### `irc_refusals` (the rcfc chk-handoff refusal) but never promotes it to `warnings[]`, unlike
### every sibling refusal type in the same function

`collect.py:1166-1168` reads `irc_<dir>.refusal.json` into `out["irc_refusals"]`. Read the rest of
`collect_u56`: `mapping_refusal` (line 1187-1190) and `c8_refused` (line 1181-1186) both get an
explicit `warnings.append(...)` line right after being read. `irc_refusals` gets none. This
violates the project's own stated rule, quoted verbatim in `guards.py`'s `irc_verdict` docstring one
function away: *"Rule 13: the field is read by code, warnings[] is read by a human. Both are
required."* If both IRC directions refuse under `readfc` (e.g. the chk copy silently failed for
both), `u56_attempt.json`'s `STATUS` is untouched by the per-direction `continue` branch and stays
whatever it was set to before the IRC loop (`"ts_candidate_produced"`) — so a human skimming
`warnings[]` for this attempt would see nothing flagging that neither IRC actually ran, and would
have to know to check `irc_refusals` specifically. Dormant today (refusal can only fire under
`readfc`, which ships off), but — like the `classify_indeterminate` bug — this should be closed
before the `rcfc` switch is ever flipped, for the same reason: the first real activation is the
first time this silently-missing surfacing would matter.

### NEW FINDING 3 (found while re-reading the §39.66 caller wiring in `U56.sh`) — the bracket
### check's direction lookup silently defaults an UNKNOWN direction to `"break"`, not to the
### documented `non_monotonic`/`None` handling, if `gscan_verdict.json`'s direction derivation
### raises for any reason

`guards.bracket_check`: `direction = (directions or {}).get(key, "break")` — the default for a
KEY NOT PRESENT in `directions` is the string `"break"`, not `None`. `U56.sh`'s caller
(`PYBRACKET` heredoc) wraps the whole per-bond `derive_direction` loop in one
`try/except (OSError, ValueError, KeyError, IndexError): directions = {}` — if reading
`gscan_verdict.json`'s `profiles`/`forward` structure fails for ANY reason partway through
(missing key, wrong shape, etc.), `directions` resets to an EMPTY dict for EVERY bond, not just the
one that failed. Every `form`/`mechanism` coordinate (the ones §39.66 exists to widen coverage to)
then silently gets `"break"` semantics instead of the correct `"form"` inequality — or the correctly
documented `applicable: false, non_monotonic` path §39.66(b) specifies for an undeterminable
direction. Using P1's own numbers as the concrete failure case: Li–O2 forms (reactant 2.489, saddle
3.980); under the WRONG default "break" rule (`refuse if saddle < reactant`) 3.980 is NOT less than
2.489, so the check would silently **pass** exactly the coordinate §39.66 was built to catch P1
with, instead of refusing OR reporting `non_monotonic`.

**Why this is not firing today**: the same code path that reads `gscan_verdict.json` for direction
derivation is written by the SAME run that must have already passed an earlier, stricter gate
(`GSCAN_FIRED` check, `U56.sh:396-414`) that exits before ordering `ts_opt` at all if the verdict
file is missing or unreadable — and the writer unconditionally sets `profiles` alongside `fired` in
one JSON dump. So in practice the invariant "if `gscan_verdict.json` says pass, `profiles` is also
well-formed" holds today, and I could not construct a currently-reachable input that trips this.
Flagging it as a robustness gap, not a live defect: the invariant is implicit across two separate
code blocks in two different places in the file, unenforced by any shared check — the same "one
truth, two places, one drifts" shape this project has been bitten by before (ADR-107's `tasks.tsv`,
the P5 species-count mismatch). A future refactor of either the writer or `derive_direction`'s
return contract would not be caught by any existing test before it silently degraded a form/
mechanism-coordinate bracket check into an always-passing no-op.

### Suite
`Ran 1477+ tests` (matches coder11's report), cleared `__pycache__` before this pass per the
procedure change coder11 adopted.

---

## 2026-08-20 — critic10: verified coder11's R-5/R-6/R-7/R-8 fixes (all correct), plus ONE new
## finding surfaced by re-running the full suite — `docparse.parse_risks` silently drops every
## closed risk, because the doc's own documented format and the parser's regex disagree

### R-5 through R-8 fixes — all verified correct by direct execution, not by reading the summary

- **R-5** (`classify_indeterminate`): re-ran the exact prior reproduction, confirms `cause_class`
  now comes out `"chemical"` for a B+ disagreement. Structured `cause_tags` implementation read in
  full — correctly derives from clause-level tags, not prose. [confirmed]
- **R-6** (`parse_scan_log` frame loss): re-ran my exact adversarial reproduction —
  `n_points` is now 2, not 1; the recovered second frame's data is correct
  (`energy_hartree=-2.0`, 2/2 geometry entries). Read the fix: advances by `2 + len(geometry)`
  (actual) rather than `2 + n` (declared) when they differ, and warns explicitly when the landing
  line after that isn't a header (`"parsing may have DESYNCHRONISED"`). `test_gfn2_scan.py` 17/17,
  including the two new tests, run directly. [confirmed]
- **R-7** (`irc_refusals` → `warnings[]`): read `collect.py:1184-1189` — now loops
  `out["irc_refusals"]` and appends one `warnings[]` entry per refusal with its `cause_class`.
  `U56.sh:924-929` sets `STATUS="irc_refused_no_direction_ran"` gated on an `IRC_RAN` counter that
  only increments after `sei_qc_input` actually succeeds — correctly distinguishes "every direction
  refused" from "at least one ran." [confirmed]
- **R-8** (`bracket_check` direction default): read `guards.py:303-315` — `direction =
  supplied.get(key)` (no `"break"` fallback string; Python's implicit `None` for an absent key now
  coincides with the same `None` a genuinely non-monotonic coordinate already produced), and
  `U56.sh`'s `PYBRACKET` heredoc no longer wraps the whole per-bond derivation loop in one swallow-
  everything `except`; a `gscan_verdict.json` read failure or an empty forward profile is now
  reported into `out["reasons"]` individually rather than silently emptying the whole `directions`
  map. **Agreed with coder11's counter-point that I under-scoped this originally**: I had reasoned
  the broad `except` was protected by the earlier `GSCAN_FIRED` gate refusing on a missing/unreadable
  verdict file, but that gate only checks the FILE'S existence and `fired`/`cause_class` keys — it
  never validates the `profiles.forward` structure the direction-derivation loop actually needs, so
  a healthy, readable `gscan_verdict.json` with a malformed or missing `profiles` block would have
  hit the broad `except` too, on a run the earlier gate would have waved through. Correct catch;
  updating my own record. [confirmed]

### One more finding, found while re-verifying suite health, not part of coder11's batch

**`docparse.parse_risks` silently drops every CLOSED risk from `05_STATE.md`'s Known-Risks
section**, because the section's own header instruction and the parser's regex specify two
different formats for the same thing:
```
STATE.md header (line 395-396): "keep bold **R-NN** ids and - [ ] open / - [x] ~~R-NN~~ ... closed
                                  format"
docparse.py RE_R (line 17):      re.compile(r"\*\*(R-\d+)\*\*")   -- requires **R-NN**, NOT ~~R-NN~~
```
R-5 through R-8 were closed today exactly per the doc's own documented convention
(`- [x] ~~R-6~~ **FIXED**: ...`), and `RE_R.search()` does not match `~~R-6~~` at all (nor does it
match `**FIXED**`, since the captured group must literally be `R-\d+`) — so these four lines are
invisible to `parse_risks` entirely, not merely mis-flagged as open. **Reproduced directly**:
```python
docparse.parse_risks(open("docs/05_STATE.md").read())
# -> 4 entries (R-1..R-4 only). R-5..R-8 do not appear at all, open OR closed.
```
This is exactly what caused the third (previously unexplained) failure in the full suite:
`test_session_digest.py::TestAgainstRealDocs::test_real_docs_have_adrs_and_items` —
`assertGreaterEqual(len(self.state["risks"]), 5)` now fails with 4, because the test counts ALL
risk entries (open + closed) and 4 of the real 8 are silently missing. **Not a freeze-signal
failure** — full suite is `1480 / failures=3 / skipped=14`, not `1480 / failures=2` as reported;
the third failure is this one, newly surfaced by today's closures, not by any source change.

**Why this matters beyond one red test**: `session_digest` is the module that parses these docs for
the packaged report the user receives (`docparse.py`'s whole purpose, per its own module
docstring-adjacent comments referenced earlier this session). A closed risk silently vanishing from
that parse means a future round's summary could under-report how many risks exist AND how many were
resolved, with no visible gap — this is the exact "written down and not read" failure shape this
project has named as its own signature defect, now found in the tooling that exists to prevent it.

**Whose fix this is**: ambiguous — either `docparse.RE_R` should also accept `~~R-NN~~`, or the
`05_STATE.md` header instruction is wrong and closed risks should be written `**R-NN**` (not
strikethrough) to match the existing regex. Not picking one; flagging both the mismatch and the
currently-red test it causes. Low urgency (does not affect any chemistry or budget number), but it
is a real regression from a clean baseline and should not be quietly absorbed, per this project's
own §0-p.6 rule ("if the failure count changes, that is a new event to report, not silently
absorb") — applied here by analogy even though this isn't the `dist/` freeze signal.

### Suite, exactly as run
`Ran 1480 tests`, `failures=3` (`test_build_stamp` ×2, expected; `test_session_digest` ×1, new —
see above), `skipped=14`.

---

## 2026-08-20 — critic10: `docparse.parse_risks` fix verified

Lead's fix (`~~**R-NN**~~` — strikethrough AND bold together, satisfying both the visual marker
and `RE_R`) verified directly, not taken on report: `docparse.parse_risks(open("docs/05_STATE.md")
.read())` returns 8 entries (R-1..R-4 open, R-5..R-8 closed) [confirmed]. `test_session_digest.py`
60/60 [confirmed]. Full suite re-run clean: `Ran 1491 tests`, `failures=2` (both `test_build_stamp`
freeze-signal, expected), `skipped=14` — back to the clean baseline. `test_bplus.py` has appeared
(not reviewed yet — noting its existence for the next pass, not evaluating it now).

---

## 2026-08-20 — critic10 incident investigation (lead-directed, real cluster return): P6 solvent
## refusal explained, P5 t21/t22 silent gap explained — both traced to source + real artefacts
## in `cpu_machine_pilot_results/` (read-only, lead-authorized per §4's R-13 note)

**Scope**: not a code review of new work — a diagnostic trace requested by lead against the actual
returned cluster round. Read-only throughout; nothing under `cpu_machine_pilot_results/` was
modified or deleted.

### 1. Why P6 refused (`solvent_refused (C-5)`, all 3 sub-jobs) while P1b/P5 ran real decks

**Not a doc/config contradiction, and not a divergence in the solvent-decision logic itself** —
`sei_pilot/solvent.py::resolve_solvent_deck` is the single decision point and every payload calls
the same function through `qc_adapter.sh`. **The divergence is that `payload/P6.sh` never calls
`sei_qc_smoke` at all** [confirmed, grep: zero matches for "smoke" in P6.sh], while
`payload/P1b.sh:42` and `payload/P5.sh:35` both call `sei_qc_smoke` before their first production
`sei_qc_input`, and `sei_qc_smoke` is what writes `deck_verification<suffix>.json` — the file
`resolve_solvent_deck`'s `runtime_verification` argument is read from (`qc_adapter.sh:166`).
Without that file, `run_verified` is `False`; `config_verified` is also `False`
(`solvent_policy.deck_verified` is `false` in `config/qc_levels.json`, correctly — flipping it is
the lead's call, not the code's); with `purpose` defaulting to `"production"` (P6 never sets
`SEI_QC_PURPOSE=smoke` either), `resolve_solvent_deck` raises `SolventUndecided`.
**Verified directly against the real return**: `cpu_machine_pilot_results/.../jobs/P6_t1/anchor.meta.err`
contains the EXACT `SolventUndecided` message text from `solvent.py`'s `pcm_numeric` branch, word
for word, rc=4 in `executions.jsonl`. This is not a guess — the returned artefact's error string
and the source code's raise statement match verbatim.

**Why this matters, and why it's cheap to fix**: P6 measures machine timing (κ, thread scaling),
not chemistry — it does not need the real PCM deck to answer its own question, but it is routed
through the SAME shared adapter that enforces the full chemistry-grade C-5 gate regardless of
purpose. `payload/P6.sh` was never retrofitted with the `sei_qc_smoke`-then-production two-step
pattern that `P1b.sh`/`P5.sh`/`endpoint_prep.sh`/`U56.sh` all picked up under ADR-105/108's S-1/S-2
wiring — it looks like an old payload nobody revisited when the rest of the fleet was updated.
Core-h cost of the incident is trivial (~8s × 3, rc=4 fails fast) but it cost a full round's worth
of κ re-measurement turnaround (~3.5 days, RT-1) for nothing. **Fix**: add a `sei_qc_smoke` call to
`P6.sh` before its `sei_qc_input`, matching the other payloads — one line, same pattern already
proven elsewhere.

### 2. Why P5.t21/t22 vanished with no result AND no failure record

**Both are the same species, `li_ec2_cation`** — t20 (seed 0, level 2/main), t21 (seed 1, level 2),
t22 (seed 0, level 1/cheap fallback) all involve this one species; t20 is the one that
SUCCEEDED-AT-THE-TASK-LEVEL (state has `P5.t20.done.json`), t21/t22 did not.

**Read t20's own job.log first, as the control case**: it hit a genuine, self-terminated G16
failure — `"Error in internal coordinate system. Error termination via Lnk1e in .../l103.exe"`,
followed by a SIGSEGV backtrace in G16's own error-handling code (`l103.exe:13626 terminated with
signal 11`) — but G16 itself reports its own elapsed time as **6h 37m 47s**, under the array's
declared `walltime=07:45:24` (`P5.qsub`). `sei_stage` correctly wrapped this (rc=1 recorded in
`stages/p5_li_ec2_cation_s0_L2.json`), `executions.jsonl` shows BOTH a `"run"` and a `"finish"`
event (`epoch 1787211133, rc: 0` — the TASK script itself exited cleanly; the chemistry inside it
did not, and is honestly recorded as `converged: false, failure_reason: "error_termination"` in
`p5_task_results.t20.json`). **This is the system working as designed** — a chemistry failure,
correctly captured, correctly distinguished from an execution failure (C-2's own principle).

**t21 (`li_ec2_cation_s1_L2`) and t22 (`li_ec2_cation_s0_L1`) show a DIFFERENT shape entirely**:
both job.logs stop mid-SCF-cycle with NO termination message of any kind — no `Normal
termination`, no `Error termination`, nothing — mid-DIIS-iteration, still printing ordinary SCF
cycle output right up to the last line. Neither has a `stages/p5_*.json` marker at all. Neither has
a `"finish"` entry in `executions.jsonl` — only `"run"`. ⚠ **I initially reasoned from file mtimes
and nearly drew a wrong conclusion — caught myself and re-derived from real epoch data instead**
(this project's own §0-p.5 "MTIME TRAP" warning: mtimes in this tree are transfer times, not write
times; every file in a batch is stamped within the same narrow transfer window regardless of when
it actually stopped executing). **The reliable evidence is the absence of a `"finish"` event and
the absence of a stage marker for exactly these two tasks and no others** — `sei_stage`'s
marker-write happens only AFTER its wrapped command (`sei_qc_run`, running G16 synchronously)
returns; if the whole process tree is killed while G16 is still running (the shape a PBS
wall-clock enforcement kill takes — no graceful shutdown, no trap), neither the marker nor the
`"finish"` event is ever written, and the payload's own results-aggregation Python block (further
down `P5.sh`, which writes `p5_task_results.t<N>.json`) is never reached either — because the
whole script died with its child.

**Conclusion, appropriately caveated**: this is consistent with a wall-clock kill of both tasks
(t20's sibling attempt on the same species needed 6.72h of the 7.76h budget just to crash; t21/t22
did not crash early and evidently kept running past the point t20 stopped) — but I cannot rule out
an independent node/OOM failure from what's in the returned tree alone, since there is no PBS
accounting record here (`qstat -x -f 23673266[]` or the site accounting log would settle it, and
this project has already flagged that exact ask to the user once before, unanswered, for a
different incident — bundling this with that ask is cheap). **What IS certain, independent of which
exact mechanism killed the process**: `payload/P5.sh` has **no tripwire / wall-clock-aware
protection** at all — no per-species budget check between species (unlike `endpoint_prep.sh`,
which explicitly checks cumulative core-h against budget between its two stages and writes
distinct `stage1_budget_exhausted`/`stage2_budget_exhausted` markers for precisely this shape of
event), no trap/signal handler, nothing. A species slow enough to approach the wall limit is
completely unrecoverable — not even a partial/aborted-run record survives, in direct violation of
this project's own C-13 principle (*"an aborted run's core-h is DATA about convergence risk, never
discard it"*) and this round's own standing rule #7 (*"report success/completion rates with their
real denominator, never pool survivors with a silently-shrunk attempt count"*).

**Practical consequence for reading "P5: 20/22"**: it is not "20 succeeded, 2 unlucky" — it is "20
tasks either finished OR crashed loudly enough to leave a record, and exactly the 2 tasks running
the one species independently already flagged as anomalously expensive/hard-to-converge
(`li_ec2_cation`, 282.7 core-h without converging in an earlier, unrelated measurement) hit the one
gap in the payload that has no floor under it." **`u_cheap` and any P5-derived per-species cost
figure should not silently treat 22 as the denominator** — it should be reported as 20 measured / 2
unrecoverable-cause-unknown, with `li_ec2_cation` flagged as the species responsible for both, not
folded into an aggregate rate as though it were 2 ordinary missing data points.

**Suggested fix, same shape as `endpoint_prep.sh`'s existing pattern**: `P5.sh`'s `run_one` (or its
caller) should check elapsed wall time against a declared per-task budget before/between species
inside a task (today's array split is already 1 species per task after ADR-107, so this reduces to:
before launching `sei_qc_run`, check remaining wall budget; if a species is already known to be a
repeat offender like `li_ec2_cation`, this is the cheapest place to catch it) — and, more
generally, wrap the `sei_qc_run` call so that a `SIGTERM` from an approaching PBS wall-clock limit
(PBS typically sends `SIGTERM` some seconds before the hard `SIGKILL`) can be trapped and used to
write a `wall_exhausted` marker before the process actually dies, the same shape C-13 already uses
elsewhere in this project.

---

## 2026-08-20 — critic10: proposer7's two P5 data-hygiene items, both confirmed, both UNRELATED
## to the P6/deck_verified trace above

### 1. Stale `level` label — confirmed, source located

`criteria/p5.py:28-29`:
```python
LEVEL_PRIMARY = "wB97X-V/def2-TZVPPD/SMD"      # ADR-029 기본값
LEVEL_CHEAP = "wB97X-D3/def2-TZVP/SMD"
```
Hardcoded string constants, never derived from the actual route or `config/qc_levels.json`. Real
data confirms the mismatch is worse than a formatting drift: `p5_task_results.t1.json`'s h2o row
carries `"level": "wB97X-V/def2-TZVPPD/SMD"` while `"route_echoed"` on the SAME row reads
`"#p wB97XD/gen scrf=(pcm,solvent=generic,read) opt freq"` — **wB97X-V and wB97XD are different
functionals** (both Head-Gordon-group, but wB97X-V adds VV10 nonlocal dispersion; wB97XD is the
older empirically-dispersion-corrected one — not interchangeable), not just a naming variant, and
the solvent term (SMD vs the real PCM) is wrong too. These constants are also used as DICTIONARY
KEYS for the cheap/primary cost-ratio computation (`p5.py:172-177`) — the ratio arithmetic is
internally self-consistent (same wrong key both times) so it is not itself corrupted, but any
report or downstream document that quotes the `level` field as what actually ran is wrong. Agreed
with proposer7: this must be regenerated from `route_echoed` (already captured correctly on every
row) before any of this feeds B1 sizing.

### 2. `rc` not usable as a health signal on this batch — confirmed, explained

`sei_qc_run()` (`qc_adapter.sh:345-347`) is literally `g16 < job.gjf > job.log 2>&1` in a subshell —
`rc` is G16's OWN process exit status, not a chemistry verdict computed by this codebase. Confirmed
directly: `p5_task_results.t1.json`'s h2o row has `rc: 1` AND `converged: true` simultaneously
(h2o, a trivial closed-shell case — genuinely converged, log parser independently confirms `Normal
termination` + `opt.converged`). `rc` on this cluster's G16 build (`g16.linda.c01`, the Linda
parallel wrapper) evidently does not reliably return 0 on a successful run — a known real-world
property of Linda-wrapped Gaussian on some cluster configurations (worker-process cleanup can set a
non-zero exit at the wrapper level even after the calculation itself completes and prints Normal
termination), not something this codebase's logic controls. **Checked whether this is dangerous**:
`rc` is only ever passed through (`criteria/p5.py:81: "rc": r.get("rc")`), never used as a gate or
filter anywhere in the P5 pipeline — `converged` is computed independently from the actual log
content, not from `rc`. So this is a genuine data-hygiene/labelling hazard for a HUMAN or a FUTURE
piece of code that assumes `rc==0` means success (exactly proposer7's own framing — "if read
naively, the whole batch would look failed") — not a currently-active silent corruption of any
number already in use.

### Relation to the P6/deck_verified trace: NONE — different code paths entirely

The P6 divergence traced earlier is `payload/P6.sh` missing a `sei_qc_smoke` call, in
`qc_adapter.sh`'s solvent-resolution path. Both items above are in `criteria/p5.py` (a label
constant never wired to the real route) and the raw `sei_qc_run`/G16-Linda exit-code behaviour —
neither touches solvent resolution or smoke verification at all. Three independent bugs, not one
root cause wearing three faces; sequencing them separately is correct.

---

## 2026-08-20 — critic10: proposer7's third P5 item (`converged` means opt-only) — confirmed
## from a real log, mechanism located

Quick verification (lead flagged non-blocking; checked anyway since it was cheap and on-brand).
`sei_pilot/criteria/p5.py`'s `"converged": bool(s["normal_termination"] and s["opt"]["converged"])`
uses `g16.summarize()`'s `normal_termination`, which is a presence check on the string `"Normal
termination"` anywhere in the log — **confirmed directly against `jobs/P5/species/h2o_s0_L2/job.log`**:
```
1458: Normal termination of Gaussian 16 at Thu Aug 20 09:50:32 2026.      <- the OPT phase's own link
1738: NEqPCM: ... EpsInf=0.0000
1739: EpsInf not defined for this solvent.
1740: Error termination via Lnk1e in .../l1110.exe                        <- the FREQ phase, right after
```
The `opt freq` route runs as two chained Link1 sub-jobs; the opt phase prints its own "Normal
termination" before the freq phase starts and immediately fails on the same EpsInf-not-defined
issue proposer7 traced to the endpoint certification. `normal_termination` doesn't distinguish
"the whole requested route completed" from "one sub-link inside it printed the string once" — so
`converged: true` is accurate about the OPTIMIZATION and silently absent about the FREQUENCY, for
every row in this batch. Confirms proposer7's framing exactly: a wrong label (the `level` string)
is visibly wrong the moment someone compares it to the route; a field that's silently narrower than
its name looks correct indefinitely, which is why this is worth fixing even though nothing
downstream currently reads `converged` as "opt+freq both converged." Root cause (EpsInf) is
proposer7's finding, already routed to coder11 — not re-investigating it here, just confirming the
labelling mechanism from source + a real log, per lead's request.

---

## 2026-08-20 — critic10: rebuild-readiness inventory (lead asked for an explicit call on the
## whole accumulated batch, not a per-piece rubber stamp)

**Verdict: NOT YET rebuild-ready.** Reviewed-and-confirmed-OK pieces do not cover the whole
accumulated batch — several are landing right now or have never been opened by me. Itemised so the
gap is concrete, not a vague "not done yet":

```
CONFIRMED, by direct execution/source read (today, this critic)
  U56-2 (ADR-109)                          OK, 2 minor cosmetic items open, non-blocking
  G-SCAN-2 v3 / Ω / spectator / bracket    OK
  C-2.1/C-2.2/condition-7 (branch a/b)     OK
  CHEMICAL/BUDGET/UNKNOWN/MIXED (R-5)      FIXED, verified
  parse_scan_log frame-drop (R-6)          FIXED, verified
  irc_refusals -> warnings[] (R-7)         FIXED, verified
  bracket_check direction default (R-8)    FIXED, verified
  docparse.parse_risks / RE_R              FIXED, RE-verified just now after its second widening
                                            (still 8/8 correct)
  P6 solvent_refused root cause            diagnosed, NOT YET fixed in source (one-line fix
                                            identified, not landed)
  P5 t21/t22 silent gap                    diagnosed, NOT YET fixed in source (tripwire proposal
                                            sent, not landed)
  P5 level-label / rc / converged fields   diagnosed (3 items), coder11's fix NOT LANDED YET
                                            per lead's own message ("once coder11's fix lands")

NEVER OPENED BY ME, present in the suite right now
  test_bplus.py            B+ decision half + §39.70/71 -- lead separately said HOLD this one
                            until the "verdict flip" wiring question with proposer7 settles;
                            do not read my silence on it as review, it is an explicit pause
  test_epsinf_bracket.py   presumably the EpsInf fix's own test -- exists, unread
  test_sp_ladder.py        SP ladder (§39.47(c) DFT single-point ladder) -- unread entirely
  test_p1_excluded_sizing.py   the P1 resize -- unread; this is the change that MOVED the
                            freeze-signal baseline from 2 to 4 failures TODAY and I have not
                            verified the two new README-parity failures are the expected kind
                            of red rather than a real drift
  "engine class"           lead's own term from the request -- I do not have a confirmed
                            referent for this (no `class Engine`/`EngineClass` in source);
                            asking directly rather than guessing at what to review
```

Four items are outstanding P6/P5 fixes that are diagnosed but not yet in source at all — reviewing
a fix that does not exist yet is not possible, so those alone push rebuild past "not yet" on their
own. The four never-opened test files are the larger gap: two (`test_sp_ladder.py`,
`test_p1_excluded_sizing.py`) are plausibly small and can be picked up next; `test_bplus.py` is
explicitly paused by lead's own instruction, not by me stalling.

**Recommendation**: rebuild waits until at minimum (a) the P6/P5/level-label/rc/converged fixes
land and get verified, (b) SP ladder and the P1 resize get a pass, (c) "engine class" is identified
and reviewed or ruled out of scope. B+ can plausibly stay outside the rebuild gate if it is
release-gated the same way U56-2 was (behind a flag nothing flips automatically) — worth lead
confirming that shape holds for B+ too before treating its pause as a non-blocker.

---

## 2026-08-20 — critic10: B+ gate shape confirmed, SP ladder reviewed (one real gap found), P1
## resize reviewed (confirmed correct)

### B+ gate shape — NOT the same `released:false` config pattern as U56-2/sp_ladder, and that's fine
`bplus_agreement`/`bplus_sample_points` (`guards.py:256,353`) are in `test_guard_reach.py`'s
`DEFERRED_NO_CONSUMER_YET` bucket — zero external callers, enforced structurally (the reach test
fails the moment a payload calls them, same mechanism that caught `gscan2_decision` correctly
before its GFN2 producer existed, verified as sound reasoning earlier this session). No payload
wires B+ into a submittable job at all today, so there is no config flag to check — the gate is
"cannot be reached," which is at least as safe as "reachable but flagged off." Confirmed rather
than assumed, per lead's request.

### SP ladder — confirmed release-gate mechanism correct (matches S-2/U56-2 pattern exactly:
### `sp_ladder_released()`, config-driven, code never sets the flag, `sp_ladder_items()` built
### and tested unconditionally). ONE real gap found:

**`payload/SP_LADDER.sh` does not exist on disk** — `sp_ladder_items()` declares
`payload="payload/SP_LADDER.sh"` for all three rungs (n=1,2,3) and the file is simply absent
[confirmed, `ls` → No such file]. **Not caught by either existing check**, for two different
reasons: `test_profiles_merge.py::TestProfileSeparation::test_payload_file_exists_for_every_item`
only scans `plan._all_items()`, which correctly excludes `sp_ladder_n*` while
`sp_ladder_released()` is False — the exact same reason the general check couldn't have caught
U56-2 either before it was released; and `test_sp_ladder.py` DOES call `sp_ladder_items()` directly
(bypassing the gate, confirmed correct by its own `test_the_items_are_still_built_and_therefore
_still_tested`) but never asserts the payload file exists — unlike U56-2's own sibling test
(`test_u56_plan_items.py::test_every_payload_file_exists_and_sources_common`), which does. Same
shape as `test_producer_consumer.py`'s file-level-only blind spot found earlier this session: a
check exists, is correct for what it checks, and still misses this because nobody added the
specific assertion to the specific test file the gate applies to. Not a submission risk today
(`released=false`, item is unreachable), but **must be closed before `sp_ladder.released` is ever
set to true** — add a payload-existence assertion to `test_sp_ladder.py`, same shape as U56-2's.

### P1 resize — confirmed correct, measured, well-tested

Reconciled the full-suite README-parity failure numbers directly: `reserved_total_core_hours`
20065 (packaged/frozen) vs 10913-10917 (source) — a **9,148-9,152 core-h drop**, matching the plan.py
comment's own claimed "~9,150 core-h of headroom recovered" almost exactly. Read the reasoning: P1
was **actually submitted this round on real hardware** (not simulated) — C-8 correctly refused it 3
times, measured cost **0.0103 core-h (37 s) total**, against the old budget of 6,800 core-h /48 h/
whole-node (reserving ~9,216 core-h of guard ceiling for a job that structurally cannot spend more
than a few core-h, since `endpoint_prep_product` was removed and `ts_precondition` is never True on
a missing endpoint). New sizing: `P1_EXCLUDED_REFUSAL_CORE_H = 64.0`,
`P1_EXCLUDED_REFUSAL_WALL_H = 1.0` — ~6,200x the measured refusal cost, a deliberate margin so a
guard failure (if C-8 ever stopped firing) would be "short and cheap" rather than a 48h whole-node
burn, not a zero margin. `P1` Item itself is correctly KEPT (not deleted) purely because `P1b`
(the round's largest item, 5,328 core-h) `depends_on=["P1"]`, and the missing-dependency check
would silently drop `P1b` if `P1` were removed — a subtler, worse failure than the one being fixed.
`tests/test_p1_excluded_sizing.py` (8 tests) run directly: OK, covers exactly this reasoning
(dependency retained, sizing generous-not-zero, refusal reported not silent, C-8 never passes on a
missing product). **Confirmed correct — this is real, hardware-measured evidence, not an estimate,
and the margin philosophy matches the project's own established pattern (E21 cap, P1_EXCLUDED
refusal cap: "cap too small" is fixed by generosity, never by shrinking toward the measured value).**

### Updated rebuild-readiness checklist
```
CONFIRMED OK, added this pass    B+ gate shape (unreachable, structurally safe)
                                  SP ladder release-gate mechanism
                                  P1 resize
NEW, non-blocking-today          SP_LADDER.sh missing payload file + its own test's missing
                                  existence check -- close before sp_ladder.released=true
STILL OUTSTANDING                4 diagnosed-not-landed fixes (P6 smoke call, P5 tripwire,
                                  level-label/rc/converged-field trio -- coder11 in progress)
                                  test_epsinf_bracket.py -- exists on disk, not yet reported
                                  landed by coder11, unread
                                  test_bplus.py -- explicitly paused by lead pending proposer7
```

---

## 2026-08-20 — critic10: `stages_completed` + EpsInf bracket fix verified (both correct,
## independently reproduced), checklist updated

### `stages_completed` — verified correct, against the real defect log, not coder11's claim alone

`g16.stages_completed(text, route)` (`criteria/g16.py:291`) read in full: `completed` from output
evidence only (`SCF Done`/`Optimization completed`/`Frequencies --`/`Thermochemistry` string
presence), `requested` from the route text (never treated as evidence of completion),
`missing = requested - completed`. **Reproduced independently against the real artefact**
(`cpu_machine_pilot_results/.../P5/species/ec_s0_L2/job.log`, not taken from coder11's message):
```python
g16.stages_completed(open(".../ec_s0_L2/job.log").read())
-> {"completed": ["opt", "scf"], "requested": ["freq", "opt", "thermo"],
    "missing": ["freq", "thermo"], ...}
```
Matches coder11's report exactly. `criteria/p5.py:66-73` carries the `[critic10]`-tagged comment
explaining `converged` stays opt-only by name (historical-comparison stability) with
`stages_completed` as the field that carries the real answer — read directly, present as
described. **The cost-statistic filter (`diagnostics()`'s `ok = [r for r in rows if
r["converged"] ...]`, line 133) is confirmed UNCHANGED** — still includes freq-crashed species'
partial core-h in the "converged" cost denominator, with the documented reasoning (line 71-73)
that changing the filter is a methodology call, not silently made here. Matches coder11's own
framing exactly — a real, live open question, correctly not resolved unilaterally in code.
`test_stages_completed.py` (8 tests, including the "trap" test pinning that both `converged`
inputs are `True` on a zero-frequency log) ran directly: OK.

### EpsInf fix — verified correct, bracket design (not a single hardcoded value)

`solvent.py:299` `resolve_solvent_deck(..., eps_inf=None)` — genuinely NOT defaulted; `qc_adapter.sh:182`
reads `SEI_QC_EPSINF` per run with no fallback (`eps_inf=(float(_epsinf) if _epsinf else None)`).
Deck emission (`solvent.py:390-404`) adds `EpsInf=<value>` to the extra input lines only when
supplied, and otherwise honestly states `_eps_inf_status: "ABSENT -- G16's freq stage will read
EpsInf=0.0000 and abort in L1110"` rather than silently omitting the field. This is a genuine
two-endpoint invariance BRACKET (`epsinf_bracket` module, read separately: two admissible EpsInf
endpoints for a given static eps, comparing whether C-8's own read (`n_imag`, low-frequency modes)
moves between them) — not a single chosen-and-hoped value, matching coder11's own framing that
"choosing a value would pre-decide the experiment." `test_epsinf_bracket.py` (9 tests) ran
directly: OK, including a refusal test for an impossible eps and a no-verdict-on-missing-run case
(Rule 18 applied correctly here too).

### Suite, reconfirmed directly
`Ran 1549 tests`, `failures=4` (`test_build_stamp` x2 + `test_readme_matches_code` x2, same known
set as before — no new failures), `skipped=14`. Matches coder11's report.

### Checklist update
```
LANDED AND VERIFIED TODAY        stages_completed / converged documentation (not a silent fix)
                                  EpsInf root-cause fix (bracket design)
STILL NOT LANDED                 level-label (LEVEL_PRIMARY/LEVEL_CHEAP still the stale ADR-029
                                  strings, confirmed unchanged -- grep, line 28-29)
                                  P6.sh missing sei_qc_smoke call (confirmed unchanged)
                                  P5.sh wall-clock tripwire (confirmed unchanged, no trap/
                                  SIGTERM/wall-budget code present anywhere in the file)
                                  SP_LADDER.sh payload file + its test's existence assertion
NOT A FIX NEEDED                 rc (Linda-wrapper quirk, informational-only, already established
                                  as never gated on)
STILL PAUSED / UNKNOWN           test_bplus.py (lead: hold pending proposer7)
```

---

## 2026-08-20 — critic10: level-label fix, P6 smoke fix + general regression test, P5 tripwire,
## SP ladder's payload-existence invariant — ALL independently verified correct

Thorough pass; one claim ("a general test asserts every production payload smokes") took real
searching to substantiate rather than being visible on the obvious first grep — recorded so the
next person does not repeat the same dead-end search.

### Level labels — verified correct against real config, not just read as code
```python
p5.LEVEL_PRIMARY -> "wB97XD/def2-TZVPPD/PCM(eps=18.5)"     [reproduced, matches config exactly]
p5.LEVEL_CHEAP   -> "wB97XD/def2-TZVPD/PCM(eps=18.5)"       [reproduced]
p5.LEVEL_PRIMARY != p5.LEVEL_CHEAP                          -> True [confirmed distinct]
p5.level_label("level9")                                    -> raises KeyError, does NOT
                                                                 render "?/?/PCM(eps=18.5)"
```
`level_label()` (`criteria/p5.py:56`) derives every field from `qc_levels.json`'s level blocks and
`solvent_policy` — the same policy the deck itself reads — rather than restating a literal.
`_safe_label` only catches at IMPORT time (config unreadable), tagging `[LABEL-UNRESOLVED]`;
`level_label()` itself refuses a placeholder-filled string rather than emit one. `test_level_labels.py`
(9 tests) run directly: OK, including a test pinning the OLD literal strings **by value**
specifically so they cannot silently return via someone "restoring a constant."

### P6 smoke fix — verified, AND the general regression test genuinely exists (took real
### searching to find, misfiled by name)
`payload/P6.sh:47` now calls `sei_qc_smoke` before its production input, confirmed by direct read.
**The claimed general test — `test_every_production_payload_smokes` — does exist**, in
`tests/test_p5_wall_tripwire.py` (class `TestP6NowSmokesBeforeProduction`, despite the file's name
being about something else entirely) — checks all six payloads that use the shared adapter
(`P1.sh`, `P1b.sh`, `P5.sh`, `P6.sh`, `endpoint_prep.sh`, `U56.sh`) for `sei_qc_smoke` presence.
⚠ **Scope note, not a defect**: it is a fixed enumeration of six names, not a dynamic scan of
`payload/*.sh` — a future seventh payload needing the pattern would need to be added to this list
by hand, the same shape as `WHOLE_DICT_PASSTHROUGH`'s manual-registration pattern found earlier
this session. Acceptable (the list is short and the test's own docstring states its purpose), but
worth knowing it is not self-extending.

### P5 wall-clock tripwire — verified correct and complete
`payload/P5.sh` now has: a pre-launch budget check (checked BEFORE launching a species, not after
— confirmed by reading the code, matches the docstring's own framing "checking after the fact
cannot help"), a `trap ... TERM` handler (PBS sends `SIGTERM` before `SIGKILL`, giving one chance
to write `wall_exhausted<suffix>.json` naming the species that was running and why), and
`collect_p5` reads the marker and promotes it to `warnings[]` (Rule 13, same shape as the
`irc_refusals` fix). `test_p5_wall_tripwire.py` (9 tests, including the two smoke tests above) run
directly: OK.

### SP ladder's payload-existence check — closed as an INVARIANT, not a bare assertion; the
### payload itself is still honestly missing, exactly as coder11 disclosed
`test_sp_ladder.py::TestThePayloadExistsBeforeTheGateCanOpen` (2 new tests) encodes `released =>
payload exists` rather than a bare `assertTrue(os.path.exists(...))` — deliberately so the test
stays GREEN while `sp_ladder.released` is `false` (so it is not a permanently-red test people learn
to ignore) and would fail at the exact moment someone sets `released=true` without the payload
present. Read the design rationale in the test's own docstring: this is the right shape for a gap
that is currently safe but must not be forgotten. **`payload/SP_LADDER.sh` itself is confirmed
still absent** — `ls` → no such file — exactly as coder11 stated (theirs to write, not closed).

### Suite, reconfirmed directly
`Ran 1570 tests`, `failures=4` (same known set: `test_build_stamp` x2, `test_readme_matches_code`
x2), `skipped=14`. Matches coder11's report exactly.

### Checklist, updated
```
CLOSED AND VERIFIED TODAY   level labels, P6 smoke (+ its general regression test), P5 tripwire,
                            SP ladder's payload-existence test (the INVARIANT, not the payload)
STILL OPEN, coder11's own   payload/SP_LADDER.sh itself does not exist
NOT MINE OR CODER11'S TO    P5 diagnostics() cost filter still pools freq-crashed species under
DECIDE                      `converged` -- lead is tracking, will revisit with proposer7/engineer8
                            once real freq re-runs land (per lead's own note)
STILL PAUSED                test_bplus.py -- lead's hold, pending proposer7
```
Nothing outstanding on my checklist is a correctness risk to today's plan — everything reachable
today (`released=false` on both U56-2 and sp_ladder) is confirmed safe; what remains is either
"write the payload" (coder11's own open item) or "decide a methodology question" (not a bug).

---

## 2026-08-20 — critic10: EXPLICIT REBUILD-READY CALL

**Verdict: YES, rebuild-ready.** Re-ran the full suite fresh one more time before answering:
`Ran 1574 tests`, `failures=4` (same known set — `test_build_stamp` x2, `test_readme_matches_code`
x2), `skipped=14`. No new failures since the last check; the four are exactly the expected
freeze-signal (source has moved, `dist/` correctly has not — clearing them IS what a rebuild does).

**On `payload/SP_LADDER.sh`, the one thing lead asked me to weigh explicitly**: it does NOT block.
Reasoning:
```
1. sp_ladder_released() defaults false, no code path anywhere sets it (confirmed, tested), and
   `default_items()`/`_all_items()` exclude sp_ladder_n1..n3 while it is false -- the missing
   payload is inert in the shipped source today, not merely untested.
2. The gap is not silent: test_sp_ladder.py::TestThePayloadExistsBeforeTheGateCanOpen encodes
   `released => payload exists` as an invariant. If anyone ever sets released=true without the
   payload, THAT test goes red immediately -- the failure mode is caught by construction, not by
   hoping someone remembers.
3. Same shape, same precedent as U56-2 earlier this session, which I already reviewed and called
   OK for rebuild purposes with comparable open items (an untested resolve() path, a stale _doc
   string) explicitly marked "close before released=true, not before rebuild." Consistency: a
   missing payload behind a code-immutable, test-guarded false flag is a "finish the feature"
   item, not a "the shipped source is unsafe" item -- and rebuild ships SOURCE, not roadmap
   completeness.
4. test_bplus.py is the same shape one level further out: zero external callers at all (confirmed
   earlier), so it cannot affect a shipped package's behaviour regardless of its own internal
   state.
```
**What WOULD have changed this answer**: if either gated item's release flag could be set by code,
or by a config default other than explicit human action, or if the guarding test itself were
missing or unverified. None of those hold — checked, not assumed.

Rebuild-ready. `dist/` freeze may lift.

---

## 2026-08-20 — critic10: smoke-check generalization verified; B+ wiring reviewed for the first
## time (landed via proper §39.70/71 process, not a rogue change) — ONE new cost-efficiency
## finding: B+ runs unconditionally, not gated on whether the IRC actually needed it

### Smoke-check fix — verified correct, dynamic scan + its own reach test

Moved to `test_payload_shell.py::TestEveryQcPayloadSmokesFirst`, confirmed: scans `payload/*.sh`
dynamically (not a fixed list), excludes the definer (`qc_adapter.sh`, detected by the presence of
`"sei_qc_smoke() {"` — i.e. by DEFINITION, not filename, closing the same class of loophole one
level down), asserts smoke precedes the first `sei_qc_input` (not merely present), and carries its
own reach test (`test_the_scan_actually_sees_the_payloads`, checking the scan finds >= 6 files
including `P6.sh`) so a scan that silently matched nothing could not pass forever — explicitly the
same failure shape as the heredoc regex earlier this session. 3/3 ran directly: OK. Old P6-specific
pin stayed at its original site with a pointer comment to where the general form now lives — no
duplicate, no silent coverage drop.

### B+ wiring — reviewed for the first time; landed through proper process, not ahead of review

Read `05_STATE.md`'s full §39.70/§39.71 trail before touching the payload: the "verdict flip" issue
lead mentioned was DISSOLVED by proposer7 redesigning the comparator (graph-isomorphism + the
optimizer's own energy-convergence criterion, replacing a threshold-sensitive Li-contact cutoff),
ruled and priced (engineer8, §R39.38/41) before coder11 wired it. This was NOT wired ahead of or
around my hold — it went through the team's normal process while I was reviewing other things.
Confirmed the three non-obvious properties the team's own notes call out as easy to silently get
wrong: start points are the LAST path point + arc-length MIDPOINT (never by index, verified against
a real 30-point P1 IRC fixture with non-uniform index-to-arc spacing), level is the TS chain's own
DFT level via `endpoint_opt_rough` (not GFN2 — GFN2 is documented to merge exactly the
Li-coordination basins B+ exists to distinguish), and an unavailable start point yields NO verdict
rather than a default. All three read directly from `U56.sh` and match the STATE.md description.

### NEW finding — B+ terminal optimizations run UNCONDITIONALLY on every IRC direction, not
### gated on whether the IRC actually needed branch (b)

Read `U56.sh`'s B+ block (`payload/U56.sh:947-995`) in full: after `sei_stage "u56_irc_${dir}"`
succeeds, the B+ pick-and-submit sequence runs immediately with **no conditional anywhere in the
block** — no check on `completion.truncated`, no check on which reaction (`$RXN`) is running.
Confirmed with `grep`: the only `if` in the entire block is `if [ "$BPLUS_PTS" = "ok" ]` (did the
IRC log actually have enough path points to pick from) — nothing gates on whether B+'s answer would
even be CONSULTED. Verified directly against `guards.irc_direction_ok` that this is a cost problem,
not a correctness one:
```python
irc_direction_ok({..., "completion": {"truncated": False, ...}, "bplus": {"agreement": False}}, E_TS)
irc_direction_ok({..., "completion": {"truncated": False, ...}}, E_TS)                    # no bplus
# -> BOTH give ok=True, connection_established_via="a" -- bplus is silently IGNORED once branch
#    (a) already applies, even a DISAGREEING bplus verdict changes nothing.
```
So a converged IRC (branch a) still verdicts correctly regardless of what B+ says — **no wrong
answer results**. But B+'s cost (engineer8: 97 core-h/attempt at T11-se, T21-se currently
unpriced/retracted) is spent on EVERY IRC direction that produces enough path points, including
every one that already converged and did not need branch (b) at all. **The design intent for this,
as I read it in STATE.md, is R-A-specific**: "R-A additionally gets ONE real converged IRC... in
the SAME run, calibrating B+ against ground truth for the one reaction where BOTH exist" — implying
B+ is otherwise meant for the branch-(b)/truncated case, with R-A's always-on B+ being a deliberate
EXTRA measurement for calibration, not the general rule. **The payload does not distinguish R-A
from R-B/R-C, or a converged direction from a truncated one** — it spends the same ~97 core-h/
direction everywhere, with no calibration purpose outside R-A. I did not find this ruled either way
in `05_STATE.md`'s extensive §39.70/71 trail — it reads as a genuine gap, not a documented tradeoff.
**Not currently spending anything for real** (`u56_2_released` confirmed still `False`) — but it
inflates the true per-attempt cost of a released U56-2 beyond what the `core_hours_budget` constants
(`U56_ATTEMPT_11ATOM_CORE_H=700` etc., unchanged since before B+ was wired) currently assume, on
every attempt whose IRC simply converges cleanly — exactly this project's own "gate-before-you-pay"
principle (§4 standing rule 5), just not applied here yet. Worth a conditional (`completion.truncated`
for R-B/R-C, or however the team wants to scope R-A's calibration exception) before release, and
worth flagging to engineer8 since the per-attempt budget constants don't yet reflect ANY B+ cost,
gated or not.

---

## 2026-08-20 — critic10: two more findings — B+ unconditional cost (new), SP_LADDER.sh landed
## with one uncaught artifact (`sp_points.json`)

### B+ cost-efficiency finding — see full writeup above (already logged in this file). Summary:
B+ terminal optimizations run unconditionally on every IRC direction (`payload/U56.sh:947-995`),
never gated on `completion.truncated`. Confirmed via direct guard testing that this is a cost
issue, not a correctness one — `irc_direction_ok` ignores `bplus` entirely once branch (a) already
applies. Not currently spending real core-h (`u56_2_released=False`), but the per-attempt budget
constants don't reflect any B+ cost either way. Worth a conditional before release.

### `payload/SP_LADDER.sh` now exists — landed while I was mid-review of B+, confirmed directly
`test_sp_ladder.py` (18 tests, including 4 new payload-shape tests) run directly: OK. One new gap
surfaced by the full-suite run, unrelated to B+: `test_producer_consumer.py::
test_every_payload_artifact_is_read_by_the_collector` now fails — `SP_LADDER.sh` writes
`sp_points.json`, which `collect.py` does not read and which is not in the
`WHOLE_DICT_PASSTHROUGH` exemption list. This is the exact defect class that test exists to catch,
catching it correctly on the first real check. Not urgent (`sp_ladder.released=False`, unreachable
today) but should close alongside the rest of the ladder before release.

### Full-suite count anomaly — investigating, not yet resolved, flagging rather than reporting a
### number I have not pinned down
A `discover` run right after `SP_LADDER.sh` landed showed only 1 failure (the `sp_points.json` one
above) and `skipped=28` (up from the stable `skipped=14` all session) — the 4 expected freeze-signal
failures (`test_build_stamp` x2, `test_readme_matches_code` x2) did not appear at all in that run.
**Checked `dist/BUILD_STAMP.json` directly: no rebuild has happened** (`source_digest` unchanged,
tarball mtimes unchanged since the start of this session) — so the freeze-signal tests going quiet
is NOT explained by an actual rebuild. Running `test_build_stamp`/`test_readme_matches_code` in
isolation immediately afterward reproduced the expected 4 failures correctly. Most likely
explanation: test-run noise from concurrent file edits landing mid-`discover` (coder11 is actively
working), not a real change in suite health — but I have not yet reproduced the anomaly a second
time to confirm that read, and am not reporting a "1579/1" headline number until I have. Re-running
`discover` clean; will report once confirmed either way rather than passing along an unverified
count.

### Anomaly resolved: confirmed transient (concurrent edits mid-run), and `sp_points.json` is
### now fixed too

Re-ran `discover` clean: `Ran 1579 tests`, `failures=4` (the expected known set), `skipped=14` —
back to the stable baseline, confirming the earlier `1/28` reading was test-run noise from files
changing mid-`discover`, not a real suite-health change. **`sp_points.json` gap is also already
closed**: `collect.py:1201` now reads it (`"sp_points": _read_json(...)`) — landed between my two
runs. Nothing outstanding from this pass.

### coder11's follow-up on the B+ finding — agreed, and noting an operational constraint

coder11 confirmed the mechanism reading and identified the fix is two-part: gating B+ on
`completion.truncated` alone would be wrong for R-A's deliberate calibration case (a converged IRC
is exactly the condition that calibration needs), so the exemption shape is a methodology question
correctly routed to proposer7 rather than decided in code. Agreed — this is the right call, and the
same shape as the `diagnostics()` cost-filter question already routed there. Also correctly flagged
downstream: once conditional, B+'s cost is no longer a flat per-attempt constant but bounded by the
IRC's own (not-yet-known) outcome — told to engineer8 directly.

**Operational note for this log**: coder11 reports `dist/` is mid-rebuild and has committed to not
touching `src/`/`tests/` until it reports, since a stray suite run writes `__pycache__` into the
tree being packaged (this is what broke a previous rebuild attempt). Holding my own test-running
activity for the same reason until the rebuild is confirmed complete — no further `unittest`
invocations from this session until then.

---

## 2026-08-20 — critic10: rebuild verified independently — clean, source_digest matches, suite
## fully green

Verified lead's rebuild report directly, not taken on trust:
```
dist/BUILD_STAMP.json source_digest = c0280111f00cd8e4      [confirmed, matches lead's report]
n_files = 103 (up from 94 pre-rebuild — matches the session's new files: SP_LADDER.sh, etc.)
test_build_stamp + test_readme_matches_code (37 tests)       OK — freeze-signal cleared
full suite (`discover`)                                       Ran 1579 tests, OK (skipped=14)
                                                               ZERO failures, not just the
                                                               expected-4-down-to-0 pattern
```
This is the first fully-green full-suite run all session. Rebuild is clean. Resuming test-running
activity now that the tree is confirmed free (coder11's hold lifted with the rebuild's success).

---

## 2026-08-21 — critic11 인수: EpsInf 브래킷 라운드 stale-done 의혹 검증 + coder12 `spec_digest` 수정 리뷰

**대상**: `cpu_machine_pilot_results/sei_pilot_work/` 원본 결과 (직접 읽음, lead 요약 아님) +
`src/pilot_package/sei_pilot/state.py`(`spec_digest`, `Store.done_spec_status`), `cli.py:599-641`
(`cmd_submit` 스킵 분기), `tests/test_done_spec_digest.py`.
**방법**: 원본 로그/마커 파일 직접 diff·grep·epoch 변환, `spec_digest`/`done_spec_status`를 실제
returned workdir에 대해 직접 실행, 전체 테스트 스위트 재실행(reproduce by execution).

## 판정
**FIX-THEN-RUN** — 코드 수정 자체는 맞고 테스트도 통과하지만, **이번에 이미 반환된 라운드의
`endpoint_prep_reactant` 항목은 이 수정으로도 저절로 고쳐지지 않는다.** 다음 라운드 제출 전에
`--rerun endpoint_prep_reactant`를 명시적으로 돌리지 않으면 정확히 같은 결함이 반복된다.

## 치명적 (결과가 틀림)

- `cpu_machine_pilot_results/sei_pilot_work/jobs/endpoint_prep_reactant/endpoint_tight.log:37-43`
  — **[확인] staleness 주장 사실로 확인.** `endpoint_tight.gjf`에 `EpsInf=` 줄이 아예 없음
  (`endpoint_tight.gjf:100-104`, `eps=18.5`만 있고 `EpsInf` 없음 — epsinf_full 쪽 gjf에는
  `EpsInf=18.5`가 있음, 대조 확인). 로그는 `Thu Aug 20 10:28:35 2026`에 정확히 예전과 같은
  `EpsInf not defined for this solvent` / `Error termination ... l1110.exe` 로 죽음.
  → `state/endpoint_prep_reactant.submitted.json`의 `submit_epoch=1787186817`
  (`date -d @1787186817` → **Thu Aug 20 09:46:57 KST**)은 EpsInf 수정이 코드에 반영되고
  리빌드된 시각(`results/sei_probe_report.cpu.json`의 `generated_at: 2026-08-20T19:21:27Z`,
  리빌드 시각)보다 **훨씬 이르다** — 즉 이 잡은 진짜로 "새 제출인데 옛날 버그가 재현된 것"이
  아니라 **애초에 새로 제출조차 되지 않은, 수정 이전 잡의 산출물**이다.
  → `results/plan.json`(및 `sei_probe_report.cpu.json`의 `plan`)에는 이 항목의
  `extra_env.SEI_QC_EPSINF = "1.0"`이 올바르게 박혀 있다 (플랜은 맞다) — 즉 **계획은 옳았고
  실행이 그 계획을 반영하지 못했다**, lead의 원래 가설과 정확히 일치.
  → 근본 원인 코드: `src/pilot_package/sei_pilot/state.py::Store.is_done` (당시 버전)이 마커
  존재 여부만 보고 `entry`의 `extra_env` 변경 여부를 전혀 비교하지 않았음 — coder12가
  `spec_digest`/`done_spec_status`로 고침, 코드 자체는 올바르고 회귀 없음(아래 참고).

- `state/endpoint_prep_reactant.submitted.json` (원본, 아직 리셋 안 됨) — **[확인, 직접
  실행으로 재현]** 수정된 `state.py`를 이 실제 workdir에 대해 그대로 돌려보면:
  ```
  is_done("endpoint_prep_reactant") -> True
  done_spec_status(key, spec_digest(현재_계획_entry)) -> ("unknown", None)
  ```
  `done_spec_status`는 저장된 `submitted` 마커에 `spec_digest` 필드가 없으면(이 마커는 수정
  이전에 쓰인 것이라 필드가 없음) `"stale"`이 아니라 `"unknown"`을 반환하도록 **의도적으로**
  설계돼 있다(과거 마커 전체를 오탐으로 몰아 대량 재실행시키지 않기 위한 보수적 선택,
  `state.py` 주석에 명시). `cli.py:610-615`의 `unknown` 분기는 경고만 출력하고 `continue` —
  **건너뛴다.** → 다음 `./run.sh`를 그냥 다시 돌리면 `endpoint_prep_reactant`는 **또 스킵되고
  EpsInf=1.0 쪽 브래킷 끝점은 이번에도 측정되지 않는다.** 브래킷 실험의 절반(`no_fast_response`,
  n²=1)이 여전히 미확보 상태로 남는다 — `endpoint_prep_reactant_epsinf_full`(n²=18.5) 하나만
  가지고는 §39.73이 요구하는 불변성 비교(두 끝점 비교)를 할 수 없다.
  **조치 필요**: 다음 라운드 제출 전에 `--rerun endpoint_prep_reactant` 실행 (또는 동등하게
  `state/endpoint_prep_reactant.{done,submitted}.json`을 수동으로 치움) — 자동으로는 안 된다.

## 중대 (낭비/재현불가)

- `src/pilot_package/sei_pilot/cli.py:781-806`(`submit_entry`의 `probe_queuewait` 서브키 루프)
  — **[확인]** 이 루프의 `store.is_done(sub_key)` 체크는 상위 루프(599행)의 `spec_digest`
  staleness 검사를 거치지 않고 독립적으로 스킵을 결정한다 — 같은 결함 형태(설정이 바뀌어도
  옛 done 마커에 막힘)가 이 경로에도 구조적으로 남아 있다. 지금 당장은 `probe_qw_n<N>`의
  구성이 `entry`의 `extra_env`에 의존하지 않아(보이는 범위에서는) 실제로 안 터진 것으로
  보이지만, 이 서브키가 나중에 `extra_env` 등 가변 설정을 갖게 되면 같은 사고가 반복된다.
  Blocking 아님 — 지금 이 라운드와 무관.

- `tests/test_done_spec_digest.py:59-77`(`test_submit_loop_reruns_stale_done`) — **[확인]**
  이 테스트는 실제 `cli.cmd_submit`의 반복문을 호출하지 않고, 그 반복문이 하는 두 번의
  호출(`done_spec_status` → `reset_item`)만 손으로 재현한다(주석에 스스로 인정:
  "Drive just the decision the loop makes, through the same two calls it uses"). `cli.py`
  실제 반복문(599-641행)은 내가 직접 읽어 `stale` 분기 뒤에 `continue`가 없고 아래
  `is_failed`/`is_submitted` 체크를 거쳐 `submit_entry`까지 자연스럽게 흘러가는 것을 확인했다
  (지금은 맞다) — 그러나 이 테스트는 그 흐름 자체(예: 나중에 실수로 `continue`가 추가되는
  회귀)를 잡아내지 못한다. 실제 `cmd_submit`을 (스케줄러 mock으로) 끝까지 구동하는 테스트가
  아니라서, "review로 확인, 실행으로 재현"은 내가 직접 코드를 읽고 fallthrough를 확인하는
  선에서 그쳤다 — 완전한 end-to-end 재현은 아님.

## 사소
없음.

## 확인하지 못한 것
- `endpoint_prep.sh` 페이로드가 `SEI_QC_EPSINF`를 실제로 어떻게 소비해 `solvent.py`
  `resolve_solvent_deck`을 호출하는지는 유닛 테스트(`test_epsinf_bracket.py`) 수준에서만
  확인했고, 쉘 스크립트 자체를 통독하지는 않았다 — `epsinf_full` 잡이 실제로 성공한 것으로
  보아 배관은 맞는 것으로 보이나, 별도 리뷰 대상으로 남겨둠.
- P5의 t21/t22, P6 등 이번 리뷰 범위 밖의 다른 항목들에도 동일한 "unknown 마커라 스킵" 문제가
  잠재하는지는 개별 확인하지 않았다 (해당 마커들도 `spec_digest` 필드가 없어 전부 `unknown`
  판정을 받을 것이나, 이번 라운드에서 그 항목들의 `extra_env`가 실제로 바뀌었는지는 별도
  확인 필요).

### 추가 (같은 날, coder12의 구체 질문 4개 응답)

**Q1 — `SPEC_DIGEST_FIELDS`에 스퓨리어스 재실행을 일으킬 필드가 섞여 있는가: 예, `cores_per_node`.**
- **[확인, 코드 추적]** `plan.py:1293` — `cpn = cores_per_node or env.get("cores_per_node") or 32`.
  `env["cores_per_node"]`는 `sysprobe.py:316`에서 **매 `./run.sh` 실행마다 클러스터를 라이브로
  probe해서 나온 노드별 코어수의 최빈값(mode)**이다 — 아이템의 속성이 아니라 "그 순간
  보이는 노드 풀의 통계"다.
- `endpoint_prep_reactant`는 `plan.py:674`에서 `cores_per_task=None`으로 명시(P1과 같은
  "노드 전체" 컨벤션) — 즉 `entry["cores_per_node"]`는 override 없이 그대로 `cpn`이 들어간다
  (`plan.py:1315`, 그리고 1401행의 override 조건 `item.cores_per_task is not None`이 이 항목엔
  안 걸림). ADR-110 자체가 "DFT/G16 Item은 whole-node라 work≈charged, `cores_per_task` 강제
  대상이 아니다"라고 명시하므로, DFT 항목 대부분이 이 경로를 탄다.
- **[확인, 직접 실행]** 계산 내용이 완전히 같은 entry라도 `cores_per_node`만 64→48로 바뀌면
  digest가 달라짐을 직접 재현:
  ```
  same computation, cpn 64 vs 48 -> digest equal? False
  ```
  이질적 노드 풀(일부 노드 점검으로 드레인, 최빈값 이동)이나 다른 로그인 노드에서 probe한
  결과가 다르면, **이미 정상적으로 끝난 384 core-h짜리 whole-node DFT 항목이 다음 라운드에
  "stale"로 오판돼 자동으로 다시 돈다** — 과학적으로 아무것도 안 바뀌었는데 core-h만 태움.
  이건 `spec_digest`의 자기 docstring이 말하는 구분("account/partition/wall 반올림처럼
  WHERE/HOW를 바꾸는 것은 제외")과 정확히 같은 카테고리인데 빠뜨린 것으로 보임.
- **권고**: `cores_per_node`(및 `nodes`, 다만 이건 대부분 Item에 고정값이라 위험도 낮음)를
  `SPEC_DIGEST_FIELDS`에서 빼거나, `item.cores_per_task`가 명시적으로 설정된 경우에만
  digest에 포함하고 whole-node 기본값(cpn)은 제외할 것. `payload`/`extra_env`/`array`/
  `chain_links`/`gpus`만으로도 원래 잡았던 EpsInf 사례(`extra_env` 변경)는 그대로 잡힌다.

**Q2 — stale에서 자동 재제출이 "done은 --force로도 안 뚫린다" 원칙에 반하는 방향인가:
아니다, 방향 자체는 맞다** — 정말 계산 내용(WHAT)이 바뀌었다면 그 done은 다른 계산의
것이므로 재실행이 옳다(그게 원래 버그였다). 다만 Q1에서 확인한 대로 필드 선정에
HOW 성격의 라이브 프로브 값이 섞여 있으면, 그 안전판을 "가짜 stale" 경유로 몰래 우회해
core-h를 태우는 구멍이 생긴다 — Q1을 고치면 Q2의 정책 방향은 그대로 둬도 안전하다.

**Q3 — array 경로에서 `done_spec_status`가 base `submitted` 마커를 읽는 게 맞는가: 맞다,
[확인].** `submit_entry`(`cli.py:826-838`)는 array 여부와 무관하게 `payload["spec_digest"]
= spec_digest(entry)`를 항상 base submitted 마커에 넣고, array면 그 위에 `n_tasks`/
`accepted`만 얹는다(별도 digest 없음) — `done_spec_status`가 base marker만 보는 것과
정확히 일치한다.

**Q4 — `reset_item`이 옆으로 치운 `.reset.<epoch>` 파일을 나중에 뭔가 마커처럼 읽는가:
아니다, [확인 + 직접 실행으로 재현].** `collect.py`는애초에 `state_dir`를 전혀 안 읽는다
(job_dir/steps_dir/starts_dir만 listdir). `state.py`의 `all_failures()`(`endswith
(".failed.json")`), `task_marker_states`/`is_done`/`is_failed`(정규식 `...\.json$`로
끝을 앵커), `cli.py:1102`의 `cmd_status`(`endswith(".json")`) 모두 정확한 접미사 매칭이라
`X.done.json.reset.<epoch>`(".json"으로 끝나지 않음)는 구조적으로 걸러진다. 직접 재현:
`mark_submitted`+`mark_done`+태스크 마커 하나 만든 뒤 `reset_item` 호출 → `is_done`/
`is_failed`/`all_failures` 전부 리셋 이전 상태로 안전하게 돌아가는 것 확인.

**요약**: 2, 3, 4는 그대로 둬도 됨. 1은 고쳐야 함 — 지금 상태로 배포하면 EpsInf 버그는
잡지만, 이질적/변동하는 클러스터 노드 풀에서 whole-node DFT 항목들이 스퓨리어스하게
재실행되는 새로운 낭비 벡터를 만든다 (Tier 2, core-h 낭비 — 결과가 틀리는 건 아님).

### 추가 (같은 날, engineer9 제보 — `SEI_QC_LEVEL`이 `spec_digest`에서 빠짐, 오답 위험)

**판정 (이 항목 단독): BLOCK** — `--level` 이 다른 값으로 같은 workdir에 대해 다시 돌려질 수
있는 한, 이 결함이 고쳐지기 전까지는 `--level`을 바꿔 재제출하면 안 됨.

- **[확인, 메커니즘 추적]** `cli.py:730` — `SEI_QC_LEVEL`은 `build_common_env(args, ...)`가
  만드는 `common_env` 딕셔너리에서만 설정된다. `common_env`는 `entry`(plan 딕셔너리)와
  완전히 별개 객체이고(`build_spec`이 `job_env = dict(common_env)`로 시작해서 그 위에
  `qc_env_for_jobs`, 마지막에 `entry["extra_env"]`를 덮어씀, `cli.py:763-771`), `entry` 자체는
  `plan.py`의 `build_plan()`에서 만들어질 때 레벨 정보를 전혀 담지 않는다(`qc_level`은
  요약 프린트용 `summary` dict에만 들어감, `plan.py:1445`, per-item `entry`엔 없음).
  `spec_digest(entry)`(`state.py:39-56`)는 `entry`만 해싱하므로 **`SEI_QC_LEVEL`은 애초에
  digest에 들어갈 방법이 없다.**
- **[확인, 실제 사용처]** `P1.sh:21`, `P1b.sh:240`, `P6.sh:29` 모두 `LVL="${SEI_QC_LEVEL:-2}"`로
  직접 읽어 **어느 이론 레벨(주 레벨 vs g2 폴백)로 계산할지**를 결정한다 — 순수한 스케줄링
  파라미터가 아니라 **계산 내용 그 자체(WHAT)**.
- **[확인, 직접 실행]** entry 자체가 레벨을 담지 않으므로, `--level g1`로 만든 entry와
  `--level g2`로 만든 entry가 (다른 CLI 인자에도 불구하고) **완전히 동일한 딕셔너리**가
  되고 digest도 같다:
  ```
  g1 vs g2 digest, same entry object: True
  ```
  즉 `g1`으로 완료된 항목에 대해 `--level g2`로 다시 돌리면 `done_spec_status`는 `"unknown"`도
  아니고 곧바로 **`"match"`**를 반환 — `cli.py:614`의 "이미 완료 → 건너뜀 (멱등 재개, spec
  일치 ...)" 메시지까지 찍으며 **확신을 갖고 건너뛴다.** g1 결과를 g2 결과인 것처럼 회신에
  담아 보고하게 됨 — engineer9 말대로 "절약처럼 보이는" 오답 사고.
- **같은 함수 안의 나머지 두 변수도 동일 결함**: `SEI_QC_MODULE`/`SEI_QC_LOGIN_PATH`
  (`qc_env_for_jobs`, `cli.py:734-751`)도 `env`(사전검사 결과)에서만 오고 `entry`엔 없음 —
  다른 module/경로로 다시 돌려도 digest는 무관.
- **세 번째 사례 탐색 (lead 요청)**: `cli.py` 안에서 `"SEI_..."` 로 설정되는 env 키를 전부
  나열해 확인 — `SEI_PKG_ROOT`/`SEI_WORKDIR`/`SEI_PARTITION`/`SEI_ITEM`/`SEI_WALL_H`는
  전부 WHERE/HOW 성격(경로·파티션·잡 식별자·유도된 wall)이라 제외가 맞다. **이 함수
  범위 안에서는 추가 사례를 못 찾음.** 단, 구조적으로 더 넓은 문제가 하나 있음(별도
  트래킹 제안, 지금 당장 fix 대상은 아님): `spec_digest`는 `entry`의 얕은 필드만 보고,
  `config/qc_levels.json` 같은 **설정 파일 내용 자체**(레벨별 functional/basis 정의)가
  라운드 사이에 바뀌어도 `entry`의 문자열 키(`extra_env` 등)가 그대로면 잡히지 않는다 —
  `payload/common.sh`의 스테이지 레벨 `pkg_fingerprint`는 이걸 잡지만 그건 **잡 내부
  재개**용이고, 최상위 `is_done` 스킵 판단에는 안 쓰인다.
- **결과에 미치는 영향**: `cores_per_node` 건(과소비, Tier 2)과 달리 이건 **결과가 조용히
  틀려서 보고되는** Tier 1 사고. coder12에게 fold `common_env`(최소한 `SEI_QC_LEVEL`)를
  digest에 포함하라고 이미 lead가 전달함 — 랜딩되면 재확인 예정.

---

## 2026-08-21 (2차 배치) — critic11: `outcome.py` cause-class 재시도 정책 + terminal_status 배선 리뷰

**대상**: `sei_pilot/outcome.py`(신규), `payload/common.sh`(`sei_terminal*`, `sei_write_marker`),
`payload/endpoint_prep.sh`, `payload/P5.sh`, `payload/P1b.sh`, `payload/P6.sh`, `cli.py`(재시도
정책 + `spec_digest(entry, physics)`), `state.py`(`physics_env`, `reset_item(archive_job_dir=)`).
**방법**: 각 payload 전문 통독(특히 `_write_terminal`/`sei_terminal` 호출부의 실제 `exit` 코드),
`status_from_g16_logs`를 실제 반환된 P5 로그 22개 전부에 직접 실행, array 항목의 재시도 판정
경로를 임시 Store로 직접 재현, `test_outcome_retry.py` 통독(어떤 케이스가 실제로 커버되고
어떤 케이스가 안 되는지 확인).

## 먼저: 이전 두 건 재확인 — [확인] 둘 다 고쳐짐
- `SPEC_DIGEST_FIELDS`에서 `cores_per_node`/`chain_links` 빠짐, `SEI_QC_LEVEL`/`SEI_QC_MODULE`/
  `SEI_QC_LOGIN_PATH`는 `physics_env()`로 별도 접어서 `spec_digest(entry, physics)`에 포함됨.
  직접 실행으로 재확인: `g1 vs g2 (physics-aware): False`(이제 다르게 나옴, 이전엔 True였던
  버그), `cores_per_node 64 vs 48: True`(이제 같게 나옴, 더 이상 스퓨리어스 재실행 안 남).

## 판정 (이번 배치)
**FIX-THEN-RUN** — `outcome.py`/재시도 정책 자체의 설계(taxonomy, `should_retry`)는 맞지만,
**배선이 절반만 됐다.** 구체적으로 두 가지가 정책의 목적 자체를 무력화한다:
(A) `endpoint_prep.sh`의 예산-소진 상태가 `exit 7`(비영)로 끝나 `is_failed` 무조건 재시도
경로로 새서 "budget은 재시도 안 함" 규칙을 실제로는 안 지킨다.
(B) **array 항목(P5 등)은 이 재시도 메커니즘이 아예 동작하지 않는다** — item-level 판정이
읽는 base done 마커가 array 항목엔 존재하지 않아 `cause`가 항상 `"absent"`로 나온다.
(B)가 더 근본적: 지난 라운드 P5의 20/22 freq가 몰살한 바로 그 상황에서도 이 메커니즘은
발동하지 않았을 것.

## 치명적

### Q4 관련 — array 항목은 outcome 기반 재시도가 구조적으로 발동하지 않음 (coder12의 전제 자체가 틀림)
- **[확인, 직접 실행]** 코더는 "array는 whole-array가 resubmit될 것"이라 가정했는데,
  실제로는 **whole-array가 절대 resubmit되지 않는다** (19개 멀쩡한 태스크를 다시 도는
  게 아니라, 아무것도 재시도되지 않음). 재현:
  ```
  is_done(P5): True
  base done marker payload (what cli.py reads): {}
  outcome: None cause: absent should_retry: False
  ```
  근거: `cli.py:610-612`의 `done_payload = store.read_marker(key, "done")`은 **base**
  `<key>.done.json`만 읽는다. array 항목은 `sei_write_marker`가 태스크별
  `<key>.t<N>.done.json`만 쓰고(`common.sh`의 `SEI_LOGICAL_KEY`가 `P5.t3`처럼 태스크
  접미사를 달기 때문), base `P5.done.json`을 쓰는 코드는 어디에도 없다(python
  `Store.mark_done`은 정의만 있고 아무도 호출 안 함 — 실제 마커는 전부 bash
  `sei_write_marker`가 씀). `is_done()`은 태스크 마커를 집계해 True를 정확히 내지만,
  `outcome`/`cause_class` 판정은 그 집계를 안 거치고 존재하지 않는 base 마커를 읽어
  항상 `absent`가 된다.
  **결과**: 22개 태스크 전부 `engine_failure`로 죽어도(지난 라운드 EpsInf 사고가 정확히
  이 모양이었다) 이 새 메커니즘은 **조용히 아무것도 하지 않는다** — `should_retry("absent")
  = False`이므로 그냥 "이미 완료 → 건너뜀"으로 처리됨. `test_outcome_retry.py`의
  `SubmitLoopRetryPolicyTest`는 이걸 검증하지 않는다 — `P6_t1`/`P6_t16`/`P6_t64`를 예로
  쓰는데 이것들은 P6가 **서로 다른 Item**(스레드 1/16/64, array 아님)이라 각자 정상적인
  base marker를 갖는다 — 진짜 array(`.tN` 태스크 마커 공유) 케이스는 테스트에 없다.
- **권고**: item-level `outcome`/`cause_class` 판정을, array일 땐 태스크 마커들을 집계해서
  내려야 함(예: 하나라도 plumbing-class면 재시도, 전부 success/chemical/budget이면 스킵 —
  `is_done`의 집계 로직과 대칭으로). 지금 상태로 배포하면 P5/P1b 같은 array 항목엔
  "auto-retry plumbing failures" 기능이 **이름만 있고 작동을 안 함**.

### Q2/Q5 관련 — `endpoint_prep.sh`의 budget-exhausted가 정책을 우회해 무조건 재시도됨
- **[확인, 코드 추적]** `endpoint_prep.sh:242,327`의 `stage1_budget_exhausted`/
  `stage2_budget_exhausted`는 `_write_terminal` 직후 **`exit 7`**(비영 종료)한다.
  `common.sh:sei_job_main`(238-247행)은 `rc != 0`이면 `sei_write_marker failed`를 쓴다 —
  `done`이 아니다. `cli.py`의 새 outcome/cause_class 게이트(610행 이하)는 **`is_done()`이
  True인 경우에만** 도는 코드라서, `failed` 마커로 끝난 이 케이스는 그 게이트를 아예 건너
  뛰고 곧장 `is_failed(key) and not args.force: ... store.clear_failed(key)`(무조건 재시도,
  cause_class 무관)로 간다. **결과: "budget은 재시도 안 한다"는 lead ruling이 바로 이
  케이스(예산 캡에 진짜로 걸린 경우)에서 지켜지지 않는다** — 다음 `./run.sh`마다 같은
  384 core-h 예산을 처음부터 다시 태우고 또 같은 캡에 걸려서 또 실패하고 또 재시도되는
  걸 영원히 반복한다(입력이 안 바뀌니 결과도 안 바뀜 — 딱 이 정책이 막으려던 그 사고).
  대조로 `P5.sh`는 `wall_exhausted`/`wall_budget_exhausted` 이후 **항상 `exit 0`**로 끝나서
  (마지막 줄) 올바르게 `done`+cause_class 게이트를 탄다 — `endpoint_prep.sh`만 이 비대칭이
  있다.
- Q2가 물은 "unknown이라서 영원히 재시도되는 상태 문자열"도 4개 발견함(`input_missing`,
  `skipped`, `route_smoke_failed`, `solvent_descriptors_missing` — 전부 `CAUSE_BY_STATUS`에
  없음, `route_smoke_failed`는 비슷한 이름의 `smoke_failed` 키가 이미 있어서 커버된 것처럼
  보이지만 실제 문자열이 달라 안 잡히는 오탈자성 드리프트). 다만 이 넷은 전부 같은 이유로
  `exit`가 비영이라 `is_failed` 경로로 새서, **cause_class 매핑 여부와 무관하게 이미
  무조건 재시도되고 있었다**(이 배치 이전부터 있던 동작) — 그래서 "unknown이라 새로
  retry-forever가 생긴다"는 아니고, "cause_class에 공들여 적어 넣은 정보가 이 네 상태에선
  전부 읽히지 않는 죽은 코드"라는 문제다(프로젝트에 반복되는 "measured but unread" 모양).
  실제로 정책을 어기는 건 위의 budget 케이스뿐.

## 중대

### Q3 — P1b extras task의 "completed" 무조건 기록이 진짜 실패를 가릴 수 있음
- **[확인]** `P1b.sh:280-284` — `u27_try` SMD 시도와 IEFPCM 폴백이 **둘 다** 실패해도
  (`U27_OK=0`, `route_accepted: false`) extras task는 `sei_terminal "completed" ...`를
  무조건 쓴다(313행). opt5의 "설계상 에러"는 별도 단계라 문제없지만, 이 코드는 opt5의
  기대된 실패와 **SP/grad/Hessian 단계나 U-27 자체의 진짜 플러밍 실패**를 구분하지 않고
  전부 "completed"로 뭉갠다 — `first_bad`/`g16_excerpt`로 어느 스텝이 실패했는지는
  `u27_noneq.json`에 기록되지만, 그 정보가 `terminal_status.json`(재시도 판단이 실제로
  보는 파일)엔 전혀 안 들어간다. **U-27 양쪽 변형이 진짜 engine/protocol 이유로 실패해도
  "completed"(성공)로 보고돼 재시도 대상이 안 됨** — Q3에서 물은 그 위험이 맞다.
- 권고: extras task의 상태를, "opt5는 항상 무시" + "그 외 스텝/‐U-27 자체는 로그로
  판정"으로 나눠서 쓸 것(예: 나머지 스텝들의 termination을 `status_from_g16_logs`로 따로
  평가해서, opt5 로그만 제외하고 합성).

## 사소
없음 (Q1의 "requested stage missing" 분기 자체는 route 파싱 기반이라 별도 결함 못 찾음 —
기존에 이미 8개 테스트로 핀돼 있음).

## 확인하지 못한 것
- P1b.sh의 stagewise(SP/grad/Hessian/opt5) 단계들이 각각 정확히 몇 번째 줄에서 어떤
  exit 코드로 끝나는지는 extras task 부분만 봤고 전체를 다 훑지는 않았다 — Q3의 권고를
  실제로 구현할 때 opt5 로그를 어떻게 골라낼지는 payload 쪽 세부 구조를 더 봐야 함.

---

## 2026-08-21 (3차 배치) — critic11: physics_env 배선 + P5/P1b EpsInf=1.93 실제 채택 확인

**방법**: 3개 항목 전부 직접 실행으로 재검증(리뷰가 아니라 재현).

1. **[확인, 직접 실행]** `g1 vs g2 digest, same entry object: False` — 새 코드로 재현, 이전
   버그(True) 고쳐짐. `spec_digest(` 호출부는 `cli.py`에 정확히 2곳(610행, 869행)뿐이고
   둘 다 `physics_env(...)`를 통해 physics를 넘긴다 — 세 번째 호출부 없음. 다만
   `submit_entry`(869행)의 `probe_queuewait` 서브키 분기(838행, `mark_submitted`)는 여전히
   **digest 자체를 아예 안 씀**(physics 누락이 아니라 digest 필드 자체가 없음) — 전에
   지적한 그 갭 그대로, 이번 배치에서 손 안 댐, 여전히 비차단(그 서브키들은 `extra_env`에
   안 걸림).
2. **[확인, 직접 실행]** `cpn 64 vs 48 equal? True` — `cores_per_node`가 `SPEC_DIGEST_FIELDS`
   (이제 `key,payload,extra_env,nodes,array,gpus`)에서 빠진 것 재확인.
3. **[확인, 직접 실행]** `payload/qc_adapter.sh::sei_qc_input`을 실제로 돌려서 확인 —
   `SEI_QC_EPSINF=1.93`, `SEI_QC_PURPOSE=smoke`, opt_freq 잡타입으로 생성한 `.gjf`에
   `EpsInf=1.93` 줄이 정확히 들어감(`eps=18.5`와 함께). `plan.py:728,753` — P5와 P1b
   Item 둘 다 `extra_env={"SEI_QC_EPSINF": repr(solvent.EPSINF_PHYSICAL_EC_EMC)}`
   (=`"1.93"`)를 갖는 것도 직접 읽어 확인 (728행 P5, 753행 P1b, `depends_on=["P1"]`로
   식별). 배선 끝에서 끝까지 확인됨 — coder12가 추론만 하고 직접 안 돌려봤다던 그 부분.

## 판정
**OK** (이 3개 항목 한정). 지난 배치에서 지적한 (A) budget-exhausted가 정책 우회,
(B) array 항목 auto-retry 무력화는 이번 배치의 범위 밖 — 아직 미해결로 남아있음, 별도 확인
필요.

---

## 2026-08-21 (4차 배치) — critic11: input_defect(deterministic) 클래스 + pkg_fingerprint 재시도 게이트

**방법**: fingerprint 두 계산부(cli.py/common.sh)를 각각 실제 절대경로로 독립 실행해 직접
비교, `INPUT_DEFECT_SENTINELS`의 원래 출처(`criteria/g16.py::ROUTE_ERROR_HINTS`)를 찾아
사용 맥락 대조, 반례 로그를 직접 만들어 `status_from_g16_logs`에 통과시켜 재현,
`test_outcome_retry.py` 직접 실행(14 tests, OK), 전체 스위트 2회 재실행.

## 판정
**FIX-THEN-RUN** — Q1(fingerprint 일치)은 문제없음. Q2가 실제 위험 맞음, 재현됨.

## 치명적

### Q2 — `INPUT_DEFECT_SENTINELS` 체크가 정상 종료 여부보다 먼저 돌아서, 수렴한 로그를 오분류할 수 있음
- **[확인, 직접 실행으로 재현]** 이 6개 단어 리스트는 `criteria/g16.py:57-58`의
  `ROUTE_ERROR_HINTS`에서 그대로 복사됐다. **원래 용법**(`g16.py:80`, `parse_termination`)은
  `elif any(h.lower() in text.lower() for h in ROUTE_ERROR_HINTS)`을 **`if not normal:`
  분기 안에서만** 검사한다 — 이미 비정상 종료로 판정된 로그 안에서만 원인을 세분화하는
  용도. `outcome.py:113-117`의 새 사용은 **이 가드 없이, `s["normal_termination"]`을
  확인하기도 전에** 무조건 검사한다.
- 실제 반례를 만들어 통과시켜 재현: `Normal termination of Gaussian 16`으로 정상 종료하는
  로그에 흔한 G16 진단 문구 한 줄("Illegal symmetry operation ignored (harmless, standard
  G16 note).")만 섞었더니:
  ```
  status: input_defect | note: deterministic: 'Illegal' in log -- same deck, same crash
  ```
  **수렴한 계산이 "결정론적 deck 결함"으로 잘못 기록된다.** `input_defect`는
  `cause_class="deterministic"`, 재시도 대상에서 빠지는데(그 자체는 이 경우 무해 —
  이미 성공했으니 재시도가 필요없다), 문제는 **기록 자체가 거짓**이라는 것 — 사람이
  나중에 `outcome=input_defect`를 보고 "이 deck이 고장났다"고 잘못 판단해 멀쩡한 결과를
  버리거나 불필요하게 "고칠" 위험이 있다. `n²`(굴절률)처럼 물리량이 아니라 라벨의
  문제지만, 이 프로젝트가 반복해서 강조해온 "라벨이 틀리면 결과 자체가 오염된 것처럼
  읽힌다"는 그 패턴 그대로다.
  🟡 이번 라운드의 실제 로그 148개 전체를 6개 단어로 grep했을 때는 전부 0건 — 즉 지금까지
  실측 데이터에서 발생한 적은 없다(운이 좋았을 뿐일 수도). 구조적 위험(체크 순서)은 실제
  데이터 발생 여부와 무관하게 존재.
- **권고**: `parse_termination`이 하는 것과 같은 순서로 바꿀 것 — 먼저
  `s["normal_termination"]`을 확인하고, **그것이 False일 때만** `INPUT_DEFECT_SENTINELS`로
  세분화. (또는 최소한 `"Normal termination of Gaussian" in t`이면 sentinel 검사를
  건너뛴다.)

## 확인, 문제없음
- **Q1 — fingerprint 계산 일치**: `cli.py`의 `current_fp`와 `common.sh::sei_pkg_fingerprint`가
  같은 문자열을 낸다는 걸 두 계산을 완전히 독립적으로(하나는 파이썬에서 `args.pkg_root`
  스타일, 하나는 bash+환경변수로 `common.sh`를 그대로 흉내) 실제 이 프로젝트의 절대경로로
  돌려서 직접 비교: 둘 다 `1c5bf7982ebd94d8`로 동일. `args.pkg_root`는 `cli.py:1250`에서
  한 번 `os.path.abspath`되고 `store.workdir`도 `Store.__init__`에서 항상 절대경로라, 두
  계산이 같은 두 절대경로 쌍 위에서 도는 것도 코드로 확인 — 우연이 아니라 구조적으로
  같음. engineer9가 걱정한 "매 라운드 한 번씩 영원히 재시도" 루프는 발생 안 함.
- `SPEC_DIGEST_FIELDS`에 추가된 `cores_per_task`는 `plan.py:1332`에서 `item.cores_per_task`
  (Item이 코드에 선언한 고정값, xtb는 명시적 정수, whole-node DFT는 `None`)를 그대로 담고,
  나중에 `cores_per_node`를 덮어쓰는 것과 별개 키라 라이브 클러스터 probe에 영향받지
  않음(지난 배치의 `cores_per_node` 문제와 같은 함정이 아님) — 안전.
- array 항목 auto-resubmit 금지(`not entry.get("array")`)는 지난 배치에서 지적한 구조적
  무력화(항상 발동 안 함)를 대체하는 "명시적으로 절대 안 함 + `--rerun` 안내"로 바뀜 —
  `test_outcome_retry.py`의 `SubmitLoopRetryPolicyTest`를 직접 돌려 실제 출력에서
  `P5`가 `outcome=input_defect`로 끝나도 "array 항목은 자동 재제출하지 않는다... `--rerun
  P5`" 메시지만 내고 건너뛰는 것 확인(14 tests, OK). 이전 배치의 "아무 말 없이 조용히
  스킵"보다 나음 — 최소한 사람에게 알림.

## 사소
- 전체 스위트 첫 실행에서 `test_g16_adapter.TestQcLevelsConfig.
  test_every_route_that_relies_on_the_c9_perturbation_carries_nosymm`가 딱 한 번
  실패했다가 재실행하니 통과, 단독 실행도 통과 — 순서/전역상태 의존 플레이키로 보임.
  이 배치 변경과 관련 있어 보이지 않고 재현 안 됨(2번째·3번째 실행 모두 알려진 4건만).
  기록만 해둠, 조치 불필요.

## 확인하지 못한 것
없음(질문 2개 다 직접 실행으로 답함).

---

## 2026-08-21 (5차 배치) — critic11: array aggregate + failed-경로 게이트 + P1b 조건부 + nosymm 재현

**방법**: 4개 항목 전부 직접 실행/재현.

1. **[확인, 직접 실행]** `outcome_payload`을 22-태스크 P5에 대해(이번엔 태스크 마커에
   `outcome`/`cause_class`까지 채워서) 재현: `aggregate cause_class: deterministic`,
   `pkg_fingerprint: fp1`(단일 fp면 보존, 여럿이면 `None`으로 안전하게 접힘 — 확인).
   지난 배치에서 지적한 "array는 항상 absent" 문제 해결됨.
2. **[확인, 직접 실행, 진짜 프로덕션 호출 방식으로 재현]** `sei_job_main bash <script>`로
   실제와 동일하게 서브프로세스로 페이로드를 띄우고, 그 안에서
   `sei_terminal stage1_budget_exhausted ...; exit 7`을 실행 — 결과 `.failed.json`:
   `"outcome": "stage1_budget_exhausted", "cause_class": "budget"`. `common.sh::
   sei_write_marker`가 kind(done/failed) 무관하게 `terminal_status.json`을 읽어 넣는 것
   확인. (처음엔 bash 함수 안에서 `exit`를 써서 전체 스크립트가 죽는 내 테스트 하네스
   실수를 했었고, 실제 프로덕션 방식(별도 서브프로세스)으로 다시 돌려 정정함.) 이제
   `cli.py`의 `is_failed` 분기가 `fcause in (chemical,budget,deterministic)`이면
   `skipped_failed`로 막아 지난 배치에서 지적한 예산-소진 무한재시도가 실제로 막힘 —
   근거 파일까지 열어 확인.
3. **[확인]** `P1b.sh:312-318` — `U27_OK=1`일 때만 `"completed"`, 아니면
   `sei_terminal_from_logs -- "$D"/u27*/step*.log`로 실제 로그 기반 판정. 지난 배치
   지적사항 반영됨.
4. **[확인]** `nosymm` 추가(`opt/opt_freq/freq/opt5`)로 route 문자열에 새 토큰이 앞쪽에
   끼어들었는데, 이 프로젝트의 route 파싱은 전부 `keyword_in_route`(대소문자무시
   substring `in` 검사, `criteria/g16.py:768-783`)나 `route_tmpl.format(**fields)`(이름
   기반 템플릿, `qc_adapter.sh`)를 쓰고, `.split()[N]` 류 위치 기반 파싱은 route/functional/
   basis 관련 코드 전체에서 검색해도 하나도 없음 — 그래서 nosymm 삽입으로 깨질 payload가
   없음. `test_endpoint_route_parity.py`(8 tests) 그대로 통과.

## 판정
**OK.** 지난 두 배치의 (A)(B) 둘 다 이번에 실제로 고쳐진 것을 프로덕션과 동일한 호출
경로로 재현해 확인했다. 전체 스위트 1613/4(알려진 build_stamp×2 + README parity×2), 회귀
없음.

---

## 2026-08-21 (6차 배치) — critic11: acetone carrier + EpsInf 브래킷 취소 + freq smoke

**방법**: 5개 항목 전부 직접 실행/코드추적으로 확인.

1. **[확인, 직접 실행]** `sei_qc_input`을 실제로 돌려서(옛 호출자처럼 `SEI_QC_EPSINF=1.93`을
   여전히 넘긴 채로) 확인: route는 `scrf=(pcm,solvent=acetone,read)`, extra_input_lines는
   `eps=18.5` 하나뿐, **EpsInf 줄 없음** — 넘긴 값이 실제로 무시됨. `solvent.py:407-415`
   코드 확인과 일치.
   `runtime_verification_ok`/`eps_matched` 재확인: `qc_adapter.sh:490`의
   `matched = any(abs(v - eps_req) < 1e-6 for v in found_values)` — **순서 무관, 정확한
   수치 일치만 본다.** 아세톤 기본 유전상수(≈20.7)가 로그 어딘가에 따로 찍혀도 `found_values`
   리스트에 그냥 추가 원소로 섞일 뿐, 요청값 18.5와 다른 숫자이므로 `matched`에 영향
   없음(우연히 일치할 값이 아님) — 코더가 걱정한 "다른 곳에 찍힌 아세톤 기본값에 매치"는
   구조적으로 발생 안 함(any-match가 특정 수치를 정확히 요구하기 때문).
2. **[확인, grep 전수]** `grep -rn "SEI_QC_EPSINF|epsinf_full|epsinf_bracket_items"
   src/pilot_package/`는 `state.py:63`의 과거 기록 한 줄만 나옴. `test_readme_matches_code`
   직접 돌려서 소스 코드가 만드는 항목 목록에서 `endpoint_prep_reactant_epsinf_full`이
   실제로 빠진 것 확인(패키지된 README만 아직 그 이름을 담고 있어 그 2개 테스트가
   실패 — 리빌드 대기 중인 알려진 신호, 새로운 게 아님). README 총액 9135/9131도
   README_USER.cpu.md에서 직접 확인.
3. **[확인, 실제 로그로 재현]** `endpoint_prep_reactant_epsinf_full/endpoint_tight.log:393`의
   실제 " Solvent              : Generic," 블록에 정규식 `\s*Solvent\s*:`이 매치되는 것과
   `Eps(infinity)`가 슬라이스 2번째 줄(잘릴 위험 전혀 없음)에 들어오는 것 확인.
   🟡 **사소한 부정확 발견**: 이 블록은 실제로 헤더+12개 파라미터 줄 = 13줄인데
   (`Solvent`부터 `Electronegative halogenicity`까지, 그다음 `----` 구분선), 코드의
   `lines[i:i+12]`는 12개만 담아 **마지막 한 줄("Electronegative halogenicity")이 잘림**.
   핵심 진단값(`Eps`/`Eps(infinity)`)은 앞쪽이라 전혀 영향 없고, 지금 아무 로직도 이
   필드의 완전성에 의존하지 않음 — 차단 아님, 나중에 "전체 표를 담는다"고 오해할 사람을
   위해 기록만.
4. **[확인, 직접 실행]** `test_changed_detection_set_is_unknown_never_stale` 포함
   `test_done_spec_digest.py` 8개 전부 통과. 코드 확인: `physics_keys` 집합이 이전과
   다르면(예: `g16` 모듈이 로그인 PATH에서 일시적으로 안 잡혀 `SEI_QC_MODULE`이 이번엔
   없음) `unknown`을 내고 `stale`로는 절대 안 감 — engineer9가 우려한 "감지 실패 하나가
   워크디렉터리 전체를 동시에 재제출시키는" 사고를 원천 차단.
5. **[확인]** `plan.py:378-397`(`endpoint_prep_product`, `explicit_wall_h=
   U56_ENDPOINT_11ATOM_WALL_H`=3.0), `plan.py:624-635`(`endpoint_prep_reactant`,
   `explicit_wall_h=6.0` 그대로), 21-atom(`endpoint_prep_rc_reactant`,
   `U56_ENDPOINT_21ATOM_WALL_H`=24.0) — 셋 다 코드에서 직접 확인, 코더 진술과 정확히 일치.

## 판정
**OK.** 전체 스위트 1618/4(알려진 신호만), 회귀 없음.

---

## 2026-08-21 (7차 배치) — critic11: sentinel 순서 수정 재검증 + C-8 solvent-config guard + freq smoke 3-deck

**방법**: 4개 항목 직접 실행/추적.

1. **[확인, 직접 실행]** `outcome.py:117-124` — sentinel 체크가 이제 `"Error termination" in t
   or not normal_termination` 분기 **안**으로 들어감(코드 확인). 지난 배치의 반례("Illegal
   symmetry operation ignored" + Normal termination)를 다시 통과시킴:
   `counterexample status: converged`(고쳐짐). 실제 `P5/species/ec_s0_L2/job.log`(진짜
   EpsInf 사고 로그)는 여전히 `input_defect`로 나옴 — 진짜 실패는 그대로 잡히는 것도 확인.
2. **[확인, 코드 추적 + 직접 실행]** `guards.endpoint_report`(`guards.py:1036-1039`)를
   소스에서 직접 읽음 — `if n_imag is None: blocking.append(...)`이 "Unknown is not
   permission"이라는 문구로 명시적으로 막는다(코더 말대로 정확함, 다시 읽어 확인). 추가로
   `optimised is not True`도 독립적으로 블록하므로 이중 방어. `cert["refused"]` 문자열이
   다른 어디서도 읽히지 않는 것 확인(`grep -rn '\.get("refused")'` — U56.sh 868행의
   `refused`는 완전히 다른 서브시스템(bracket-check)의 별도 필드, cert의 것과 무관).
   `cert`(n_imag=None 포함)가 `endpoint_certs.json`에 그대로 저장돼(`U56.sh:154-157`)
   `require_ts_precondition`으로 그대로 흘러가는 파이프라인도 소스로 확인. 직접 실행으로
   전체 체인 재현: `guards.ts_precondition({"optimised": None, "n_imag": None, "refused":
   "solvent_config_mismatch:..."}, {...})` → `may_start: False`, blocking_reasons에
   optimised/n_imag 둘 다 등장 — "측정 안 됐으니 체크를 건너뛴다"로 읽히는 경로 없음.
3. **[확인, bash 정독]** `qc_adapter.sh:404-425`의 `for tag in production legacy` 루프 —
   입력생성 실패(`[ "$tag" = production ] && rc_all=1`)와 종료판정 실패
   (`if [ "$tag" = production ]; then rc_all=1 ... else (legacy는 정보성) fi`) 둘 다
   `tag=production`에서만 `rc_all`을 건드림, `legacy`는 절대 안 건드림 — 요구사항과 정확히
   일치. `lvl`/`tag`/`jt` 전부 `local` 선언, 앞쪽 sp smoke 루프(`for lvl in 1 2`)와 이
   블록이 각자 `lvl`을 새로 순회해 셰도잉 문제 없음.
4. **[확인, grep]** `tests/`에서 `sp`/`force` job_type의 route 문자열을 직접 핀하는
   테스트/픽스처를 찾지 못함(`test_criteria.py`의 `"sp"` 매치는 cost-ratio 딕셔너리 키일
   뿐 route 텍스트와 무관) — 코더 진술과 일치.

## 판정
**OK.**

전체 스위트 직접 재실행: **1620 tests, OK (skipped=14), 실패 0건** — 코더가 말한 "1620/4"
(알려진 4개 freeze 신호)보다 더 좋은 결과(전부 그린). 아마 그 사이 리빌드가 있었던 것으로
보임 — 나쁜 방향의 불일치가 아니라서 추가 조사 안 함.

---

## 2026-08-21 (8차 배치) — critic11: method-signature C-8 guard (level/functional/basis/grid/solvent)

**방법**: 소스 추적 + 실제 테스트 실행(real-data 케이스 포함).

1. **[확인, 코드 추적]**
   (a) `certificate_matches_production`(`solvent.py:301`)는 `meta.get("route")`를 쓴다
   — `qc_adapter.sh:333`의 `out = {"route": route, ...}`에서 `route`는 우리가
   `route_tmpl.format(**fields)`로 직접 만든 문자열이지 G16의 echo(`route_echoed`)가 아님.
   G16 출력 줄바꿈/서식 변주에 노출될 일이 없음 — 우리가 항상 같은 정규 형태로 쓰니까
   `int(grid=...)` 정규식이 안전함, 코더 추측이 맞음.
   (b) **"level3가 놀랍다"는 의문은 버그 아님, 의도된 설계임 — 끝까지 추적해 확인.**
   `U56.sh:74`의 `level`은 argv[4] = `$LVL`, `LVL`은 `U56.sh:42-46`에서
   `config/b0_reactions.json`의 `level.geometry_and_hessian`을 읽는다 —
   **그 값이 정확히 `"level3"`**(`b0_reactions.json:6`, C-11 코멘트: "COMPOSITE: geometry +
   Hessian at def2-SVPD (level3)... P1은 level2로 돌아 production protocol을 한 번도
   안 거쳤다"). `endpoint_prep.sh`의 `TIGHT_LEVEL="${SEI_ENDPOINT_TIGHT_LEVEL:-3}"`도
   같은 값(레벨 슬롯 "3")으로 기본 설정돼 있어 둘이 같은 값으로 맞아떨어지는 게 우연이
   아니라 설계다. 옛 qsub의 `SEI_QC_LEVEL` 잔재가 아니라, U56과 endpoint_prep 양쪽이
   **같은 config 단일 출처를 보고 같은 "production geometry+Hessian 레벨"을 쓰도록
   ADR-099/§39.32(c)에서 이미 정한 값**. 실제 반환 인증서(18.5 arm, level3)가 새 가드에
   REFUSED(아세톤 전환 이전 덱)로 나오는 것도 `test_real_returned_certificate_is_refused`
   실행으로 확인 — 이건 가드가 제대로 작동하는 증거이지 level 불일치 버그가 아님.
2. **[확인]** `collect.py:1092-1099` — `if status == "converged": out["reading_rule"] = ...`
   그대로.
3. **[확인]** `criteria/p5.py:403-413` — `GEOMETRY_REFUSED_TAGS` 4개 행(`ec_radical_anion_s0_L2`,
   `li_ec2_cation_s0_L2`, `li_ec_cation_s0_L2`, `li_ec_radical_s0_L2` — 마지막 것은 nosymm
   노트에서 "정확히 평면으로 수렴, C-9/ADR-066 병리"로 이미 지목된 그 행과 일치, 근거
   있음), `geometry_refused()` 소비자는 `criteria/p5.py` 자신과 테스트뿐 — grep으로 확인.

`TestCertificateMustMatchProductionMethod`(4) + `TestP5GeometryRefusalList`(1) 직접 실행,
전부 통과. 전체 스위트 재실행: **1621 tests, OK (skipped=14), 실패 0건** — 리빌드
`a0b7da68f6be7b8d` 이후 그린 상태 재확인.

## 판정
**OK.**

### 8차 배치 1(b) 보충 — coder12 요청, LVL→level_key→refusal 전체 체인을 실제 데이터로 재확인

**[확인, 직접 실행, 실데이터]** U56.sh:42-46의 LVL 추출 스니펫을 그대로 떼어내 실행:
`level3` 나옴(추정 아니라 실행). 이 값을 그대로 라이브 경로처럼 사용:

```
production_method_signature("level3") →
  functional=wB97XD, basis_real_name=def2-SVPD, grid=ultrafine,
  route_fragment='scrf=(pcm,solvent=acetone,read)'

certificate_matches_production(실제 반환된 18.5-arm meta, level_key="level3") →
  ok: False
  why: "method_mismatch: solvent route '...scrf=(pcm,solvent=generic,read)...' lacks
        'scrf=(pcm,solvent=acetone,read)'; solvent read block ['eps=18.5','epsinf=18.5']
        != ['eps=18.5']"
```

`meta`의 실제 값(`level=level3`, `basis_real_name=def2-SVPD`, route에 `wB97XD` 포함, grid
`UltraFine`)이 `production_method_signature("level3")`와 level/functional/basis/grid
네 축 전부 일치해 `mism` 리스트에 안 들어가고, **오직 solvent 축(route fragment + read
block)만 거부 사유로 나옴** — coder12가 물은 "level3에서 비교하면 solvent 축만 걸린다"가
실제 데이터로 확인됨. 유닛테스트가 level2로 비교해 level/basis까지 같이 걸리는 것과는
다른, 라이브 경로 그대로의 결과.

---

## 2026-08-21 (9차 배치) — critic (critic11 후속): P5_freq_recovery 신규 항목 리뷰

**대상**: Round B에서 새로 추가된 `P5_freq_recovery` 항목 일체 —
`config/p5_freq_recovery.json`, `payload/P5_FREQ.sh`, `sei_pilot/plan.py`의
`p5_freq_recovery_items`/`p5_freq_recovery_released`, `sei_pilot/collect.py`의
`collect_p5_freq_recovery`, `criteria/g16.py`의 신규 파서(`parse_cartesian_forces`,
`parse_point_group`, `parse_zpe_and_thermal`), `tests/test_p5_freq_recovery.py`.
**방법**: 소스 직접 추적 + 실제 `cpu_machine_pilot_results/` 반환 트리에 대한 직접 실행
(설명이나 테스트 통과 보고를 그대로 믿지 않음).

### 치명적 — [확인, 직접 실행, 실데이터]

**`collect_p5_freq_recovery`(`collect.py:851-855`)의 라운드-1 `u_opt` 태그 생성이 실제
반환 데이터에서 L1/L2를 충돌시켜 3개 행의 데이터를 버리고 2개 행을 조용히 오염시킨다.**

```python
tag = "%s_s%s_L%s" % (r.get("id"), r.get("seed"),
                     "1" if r.get("level") == p5.LEVEL_CHEAP else "2")
```
이 코드는 라운드-1 `p5_task_results.t*.json`의 `"level"` 필드가 현재의
`p5.LEVEL_CHEAP`/`LEVEL_PRIMARY`(둘 다 `criteria/p5.py:89-90`에서 `qc_levels.json`으로부터
동적으로 파생된 문자열, 예: `"wB97XD/def2-TZVPD/PCM(eps=18.5)"`)와 일치한다고 가정한다.
그런데 실제 반환 트리를 직접 읽으면:

```
$ python3 -c "..." (jobs/P5/p5_task_results.t*.json 전수)
ec   seed=1 level='wB97X-V/def2-TZVPPD/SMD'   core_hours=38.73778
ec   seed=0 level='wB97X-D3/def2-TZVP/SMD'    core_hours=8.23111   (L1, cheap)
emc  seed=0 level='wB97X-V/def2-TZVPPD/SMD'   core_hours=16.05333  (L2, primary)
emc  seed=0 level='wB97X-D3/def2-TZVP/SMD'    core_hours=12.81778  (L1, cheap)
co2  seed=0 level='wB97X-V/def2-TZVPPD/SMD'   core_hours=1.58222   (L2, primary)
co2  seed=0 level='wB97X-D3/def2-TZVP/SMD'    core_hours=1.6       (L1, cheap)
ec   seed=0 level='wB97X-V/def2-TZVPPD/SMD'   core_hours=8.83556   (L2, primary)
```
이는 §1a finding 4에서 critic10이 지적하고 고친 바로 그 스테일 하드코딩 라벨이다(수정은
**앞으로의** 실행에만 적용되고, 이미 반환된 라운드-1 JSON은 스테일 라벨 그대로 디스크에
남아 있다 — 당연하다). 현재 `p5.LEVEL_CHEAP` = `"wB97XD/def2-TZVPD/PCM(eps=18.5)"`,
`p5.LEVEL_PRIMARY` = `"wB97XD/def2-TZVPPD/PCM(eps=18.5)"` — 둘 다 위 스테일 문자열
어느 쪽과도 일치하지 않는다. `collect.py`의 실제 코드 경로(`_merge_p5_task_results` 포함)를
그대로 실행해 확인:

```
COLLISION on emc_s0_L2 : overwritten 16.05333 -> 12.81778  (level 필드 'wB97X-D3/def2-TZVP/SMD')
COLLISION on co2_s0_L2 : overwritten 1.58222 -> 1.6         (level 필드 'wB97X-D3/def2-TZVP/SMD')
COLLISION on ec_s0_L2  : overwritten 8.23111 -> 8.83556      (충돌 후 마지막 값이 우연히 맞음)

ec_s0_L1  -> None   emc_s0_L1 -> None   co2_s0_L1 -> None
ec_s0_L2  -> 8.83556 (정답, 순전히 처리 순서 운)
emc_s0_L2 -> 12.81778 (오답 — 실제로는 L1/cheap 원가, L2/primary 원가 16.05333이 아님)
co2_s0_L2 -> 1.6      (오답 — 실제로는 L1/cheap 원가, L2/primary 원가 1.58222가 아님)
```

**결과 두 가지, 둘 다 실제 반환 데이터에서 재현됨:**
1. `ec_s0_L1`/`emc_s0_L1`/`co2_s0_L1` — `p5_freq_recovery.json`에 이 태그로 등록된 3개 행이
   (해당 opt 비용이 디스크에 멀쩡히 존재함에도) `u_opt`를 영원히 찾지 못해 freq가 끝난 뒤에도
   `"incomplete: missing u_opt or u_freq"`로만 남는다 — 경고 하나 없이 조용히 조립 실패.
2. `emc_s0_L2`/`co2_s0_L2` — freq 잡이 끝나면 `u_cheap_status="assembled"`로 표시되지만
   실제로는 **L1(cheap) 레벨의 opt 비용 + L2(primary) 레벨의 freq 비용**을 더한, 어느
   한 레벨도 아닌 잡종 숫자다. `_caveat`에도, `warnings[]`에도 이 사실이 전혀 드러나지 않음
   — 이번 세션 내내 반복된 "measured but unread"/"assembled 라벨이 실제로 보장하는 바가
   없음" 패턴과 정확히 같은 모양(§39.61(c)가 요구한 "두 반쪽의 provenance가 함께 실린다"는
   지켜지나, "같은 레벨인가"는 애초에 검사되지 않는다). `ec_s0_L2`만 우연히(딕셔너리
   처리 순서상 정답이 나중에 덮어써서) 맞다 — 이건 안전장치가 아니라 우연이다.

**왜 테스트가 못 잡았나**: `tests/test_p5_freq_recovery.py::CollectorAssemblyTest`의 mock이
`"level": p5.LEVEL_PRIMARY`(현재 파생 상수 그 자체)를 직접 써서 라운드-1 행을 만든다
(184줄, 152행) — 실제 반환 데이터가 들고 있는 스테일 문자열이 아니라 코드가 기대하는
정확한 문자열을 넣어준 것이라 이 충돌 경로를 전혀 밟지 않는다. `p5_results.json`(정규화된
병합 파일)은 반환 트리에 존재하지 않고 `_merge_p5_task_results`로 원본 태스크 파일을
그대로 병합하므로(직접 확인), 이 항목이 `released=true`가 되어 처음 돌아가는 순간 바로
이 경로를 탄다 — 가상의 위험이 아니라 다음 실제 실행에서 100% 재현되는 결함.

**도달성**: `collect_p5_freq_recovery`는 `cli.py:1002`에서 `pilots.append(...)`로 실제
회신 조립 경로에 연결돼 있다 — 죽은 코드 아님, `released=true`가 되는 순간 바로 소비된다.

**고쳐야 할 것**: `"level"` 문자열 동등 비교 대신 라운드-1 원본 raw 필드(예: functional/basis
조합, 혹은 `route_echoed`에서 직접 파싱한 basis) 나 P5 매니페스트의 `kind`
(`"main"`/`"cheap"`) 값으로 L1/L2를 구분하거나, 스테일 라벨 → 신규 라벨 매핑 테이블을 넣거나
(레거시 데이터가 이번이 마지막이 아닐 수 있으니 매핑을 남기는 편이 안전), 최소한 두 값이
충돌할 때 조용히 덮어쓰지 말고 예외/경고를 내야 한다 — 현재는 dict 키 충돌이 완전히
무음이다.

### 사소 — [확인, 재구성 검증]

`config/p5_freq_recovery.json:2`의 `_doc`는 각 행의 `task_budget_core_h` 산식을
"Hessian(NBasis, p=4.46) × 1.5 + 1.66 overhead, floor 6.4"로만 적는다. 17개 행 전부를
역산해 실제로 맞는 공식을 찾아보면(각주 없는 항 하나가 더 있음):

```
cost = 2.27 × (nbasis/173)^4.46 × (n_atoms/11)^1.0 × 1.5 + 1.66,  floor 6.4
```
이 식은 17개 행 전부를 소수점 둘째 자리까지 정확히 재현한다(직접 계산, 첨부 파이썬
스크립트로 확인). 즉 `_doc`가 적은 식에는 **`n_atoms` 선형 항이 통째로 빠져 있다** —
NBasis만으로 역산하면 emc_s0_L2는 151.25(실제 205.6과 36% 차이), pf6_anion_s0_L2는
34.72(실제 22.7과 53% 차이)가 나와 전혀 안 맞는다. 지금 당장 숫자가 틀린 건 아니다(테이블
안의 17개 값은 서로 내적으로 일관됨, 그 자체는 확인함) — 하지만 나중에 18번째 종을 이
공식 설명만 보고 추가하는 사람은 근사 40%씩 어긋난 예산을 만들게 된다. `_doc`에
`(n_atoms/11)` 항을 명시적으로 적어 넣을 것을 권고.

## 판정
**FIX-THEN-RUN** — `P5_freq_recovery`는 여전히 `released:false`로 게이트돼 있어 지금
당장 아무것도 잘못 돌지 않는다(Round A의 endpoint 재인증과는 무관, 그쪽은 영향 없음).
하지만 이 상태로 `released:true`가 되면 처음 실행되는 순간 바로 위 충돌이 재현된다 —
게이트를 올리기 전에 `collect_p5_freq_recovery`의 태그 생성 로직을 고치고, 실제 반환
트리(코드가 아니라 `p5_task_results.t*.json` 그 파일들)를 입력으로 한 회귀 테스트를
추가해야 한다. 그 외 항목(`plan.py`의 release-gate 패턴, `payload/P5_FREQ.sh`의 route
생성/nosymm/UltraFine, `criteria/g16.py`의 신규 파서 5개)은 실제 반환 로그로 직접
검증했고 문제 없음. 전체 스위트 직접 재실행: **1630 tests, 실패 2건(`test_build_stamp`
쌍, 리빌드 `a0b7da68f6be7b8d` 이후 소스가 움직여 생기는 예상된 신호 — 회귀 아님)**.

---

## 2026-08-21 (10차 배치) — critic (critic12): §39.108 P5_freq_recovery 보완 3건 리뷰

**대상**: coder13이 landed라고 보고한 §39.108(a)/(b)/(d) — `payload/P5_FREQ.sh`(readout
블록), `sei_pilot/collect.py`(`collect_p5_freq_recovery`), 신규 테스트
`PayloadReadoutOnRealLogTest`(5개). §39.108(c)(1)(SCF/Hessian 분리)은 engineer10에 라우팅된
채 미착수 — 보고대로 확인, 임의로 G16 내부를 추측하지 않고 넘긴 판단은 타당.
**방법**: 02_METHOD_SPEC.md §39.108 원문과 대조 + 실제 반환 트리/실제 payload 코드 직접
실행(설명/테스트 통과 보고를 그대로 믿지 않음).

### 확인된 것

1. **[확인, 직접 실행]** `u_opt_symmetry_biased`(§39.108(a))는 라운드-1 opt 로그에서 뽑은
   `stored_point_group`(회신 값, C1이면 False·비C1이면 True·파싱 실패면 None)으로 정확히
   계산됨. `geometry_refused`와 완전히 독립적으로 저장됨 — 두 플래그가 겹치는 행
   (`li_ec_radical_s0_L2` 패턴, C2V+refused)에서 **둘 다** 살아 있는 것을 실제 payload
   heredoc을 서브프로세스로 돌려 확인(`test_refused_row_still_reports_symmetry_bias_separately`
   재실행, 통과). 실제 17개 행의 점군을 전수 재계산해 §39.108(a)가 적은 표(non-C1 14개,
   C1 3개: ec_s1/ec_radical_anion_s1/ch3o_radical_s1)와 **정확히 일치**함을 직접 확인.
2. **[확인, 직접 실행]** `imaginary_frequencies_cm1`/`n_imag_interpretation_rule`(§39.108(b))
   — freq 데이터가 없으면(`freqs`가 빈 리스트) `n_imag=None`(0으로 거짓 단정 안 함),
   있으면 실측 음수 주파수 리스트 그대로 저장. 해석 규칙 문자열이 스펙 문구(큰 |ν|=트래핑,
   작은 |ν|=indeterminate, n_imag==0의 비대칭적 약한 증거력)를 그대로 담아 데이터와 함께
   이동. 실제 로그(`endpoint_tight.log`)로 재현, 통과.
3. **[확인, 직접 실행]** `nosymm_verified`(§39.108(d))는 **이번 회차 freq 잡 자신의**
   `Full point group`(코드 확인: `g16.parse_point_group(text)`를 이번 라운드 로그에
   다시 적용)로 계산되고, `stored_point_group`(라운드-1, 다른 로그)과 절대 비교되지
   않음을 소스로 확인 — 실제 C1 freq 로그로 재현해 `nosymm_verified=True` 확인.
4. §39.108(c)(2)(양쪽 raw force 모두 기록)는 이미 이전 배치에서 구현돼 있던
   `stored_final_forces`/`freq_forces` 그대로였음 — 이번 diff의 신규 작업 아님, 보고에
   과장 없음.
5. 전체 스위트 독립 재실행: **1635 tests, 실패 2건(`test_build_stamp` 쌍, 예상된 프리즈
   신호)** — 코더 보고와 정확히 일치.

### 사소 — [확인, 직접 실행, 현재 실데이터에서는 미발현]

`collect.py`의 집계 경고 문구(line ~921)가 `u_cheap_usable_for_sizing is False`인 행을
전부 묶어 **"carry `u_opt_symmetry_biased=True`"**라고 말하는데, 이 조건은
`sym_biased is False`의 부정이라 **`True`뿐 아니라 `None`(점군 파싱 실패, "unknown")도
포함**한다. 직접 구성해 재현:

```
row: stored_point_group=None, u_opt_symmetry_biased=None
→ u_cheap_usable_for_sizing = False  (보수적 방향으로는 맞음)
→ 경고: "1 assembled row(s) carry u_opt_symmetry_biased=True: ..." ← 실제 값은 True가
  아니라 None인데 문구가 True라고 단언함
```
**수치는 안 틀린다**(sizing 배제라는 보수적 결론 자체는 맞음) — 틀리는 건 사람이 읽는
경고 문구뿐이다: "확인된 대칭-편향 14개"와 "점군을 못 읽어서 모르는 행"을 같은 문장에서
`=True`라고 뭉뚱그리면, 나중에 그 경고를 근거로 "몇 개가 대칭 편향인지" 세는 사람이
틀린 수를 세게 된다 — 이번 세션 내내 잡아온 "라벨이 실제로 보장하는 바보다 더 강하게
읽힘" 패턴과 같은 모양. **현재 실반환 데이터(17행 전부)에서는 발현 안 함** — 전수 확인
결과 17개 로그 모두 `Full point group`이 정상 파싱되어 `None`이 나올 일이 없다(직접
재계산, §39.108(a) 표와 일치). 로그가 잘리거나 손상된 미래의 행에서만 실제로 발현하는
잠복 결함. 고치는 법: 카운트/문구를 `sym_biased is True`인 것과 `is None`인 것을 따로
세거나, 문구를 "carry u_opt_symmetry_biased in (True, None/unknown)"으로 정확히 적을 것.

**참고, 새 항목 아님**: 지난 배치(9차)에서 보고한 `collect.py:852-855`의 라운드-1
`u_opt` 태그 충돌 버그(스테일 level 라벨)는 이번 diff에 포함되지 않았고 여전히 그대로
있음 — coder13에게 이미 별도로 라우팅됨, 이번 §39.108 리뷰의 판정에는 포함하지 않음
(다른 티켓).

## 판정
**OK** (§39.108(a)/(b)/(d) 세 항목, 실행으로 확인). 위 경고-문구 부정확은 사소하고
지금 실데이터에서 발현하지 않으므로 막을 이유 없음 — 다만 9차 배치의 `u_opt` 태그 충돌
버그는 여전히 미해결이라 `p5_freq_recovery.released`를 올리기 전에 반드시 함께 고쳐야
한다는 판정은 유지.

---

## 2026-08-21 (11차 배치) — critic (critic12): u_opt level-join 버그 수정 독립 재검증 (CLOSED)

**대상**: coder13의 9차/10차 배치 지적 두 건에 대한 수정 — `criteria/p5.py::level_key_from_g_label`
(신규), `collect.py`의 `collect_p5_freq_recovery` 조인/경고 로직, 신규 테스트
`CollectorRealTreeLevelJoinTest` + `CollectorAssemblyTest`의 sizing-경고 분리 테스트.
**방법**: 코드 신뢰하지 않고 직접 재현 — 실제 반환 트리로 버그 재현이 실제로 사라졌는지
독립적으로 다시 계산.

1. **[확인, 직접 실행, 실데이터]** `level_key_from_g_label`이 `cli.py::qc_level_slot`과 동일한
   조인 로직(G-라벨 대소문자/하이픈 무시 비교)을 씀을 소스 대조로 확인. 실제 반환 트리의
   모든 20개 라운드-1 행에 `level_label`(`"G-1"`/`"G-2"`) 필드가 실제로 존재함을 직접 읽어
   확인 — `level`(스테일 워디 문자열)과 별개로, 이 필드는 라벨 버그 이전부터 안 흔들렸다는
   coder13의 주장과 일치.
2. **[확인, 직접 실행, 실데이터]** 9차 배치에서 재현했던 것과 정확히 같은 스크립트를
   새 조인 로직으로 다시 돌림 — **충돌 0건, unmapped 0건, 20개 행 전부 20개의 서로 다른
   키로 정확히 분리됨**:
   `ec_s0_L1→8.23111, ec_s0_L2→8.83556, emc_s0_L1→12.81778, emc_s0_L2→16.05333,
   co2_s0_L1→1.6, co2_s0_L2→1.58222` — 9차 배치에서 지목했던 "emc_s0_L2가 실제로는
   L1(12.81778)로 오염된다"던 것이 이제 진짜 L2 값(16.05333)으로 정확히 나옴. co2도 동일.
3. **[확인, 직접 실행]** `CollectorRealTreeLevelJoinTest`가 목이 아니라 실제
   `jobs/P5/p5_task_results.t*.json` 파일을 그대로 복사해 쓰는 것을 소스로 확인, 재실행
   통과.
4. **[확인, 직접 실행]** 10차 배치의 사소한 지적(경고 문구가 `sym_biased=None`을
   `=True`로 뭉뚱그림)도 같은 패스에서 고쳐짐 — `biased_true`/`biased_unknown`을 별도
   리스트로 분리해 문구에 "confirmed ... =True"와 "UNKNOWN stored point group (...not
   confirmed biased)"를 따로 적음. 새 테스트가 한쪽 태그가 반대쪽 절에 안 새는 것까지
   확인(`unknown_clause`에 `confirmed_s0_L2` 없음을 assert). 코드 직접 대조, 정확히
   일치.
5. 전체 스위트 독립 재실행: **1637 tests, 실패 2건(`test_build_stamp` 쌍, 리빌드
   이후 소스 변경에 따른 예상된 신호, 회귀 아님)**.

## 판정
**OK — 9차/10차 배치에서 지적한 두 건 모두 CLOSED.** `P5_freq_recovery`는 여전히
`released:false`로 게이트돼 있고, 이제 release 전 반드시 고쳐야 한다고 판정했던 유일한
치명적 결함(u_opt 태그 충돌)이 실제로 사라진 것을 실데이터로 직접 확인했다. 추가로 발견된
결함 없음.

---

## 2026-08-21 (12차 배치) — critic (critic12): Round A `endpoint_prep_reactant` 인증서 독립 재검증 (§39.112)

**대상**: proposer9의 §39.112 주장(C-8.2/C-8.3 PASS) — 원본 파일에서 직접 재확인, 글을
근거로 삼지 않음. `jobs/endpoint_prep_reactant/{endpoint_rough.log, endpoint_tight.log,
endpoint_tight.gjf, endpoint_rough.gjf, f1_observables.json, deck_verification.json,
executions.jsonl}` 직접 열람.

1. **[확인, 직접 grep/read]** route: `endpoint_tight.gjf` 1-4행 —
   `#p nosymm wB97XD/gen scrf=(pcm,solvent=acetone,read) opt=(tight,calcfc,maxcycles=200)
   freq Int(Grid=UltraFine)`, 원자 11개(C,O,C,C,O,O,H,H,H,H,Li), `0 2`(전하 0, 다중도 2) —
   R-A/R-B 공유 reactant(Li(EC)•) 맞음, R-C 것 아님. `endpoint_rough.gjf`도 같은 functional/
   basis/solvent/grid, `opt=(loose,maxcycles=100)`만 다름 — stage 간 일관성 주장과 일치.
2. **[확인, 직접 grep]** `endpoint_tight.log`에서 `Full point group` 5회 전수 위치 확인:
   265/1482/1945/2387(최적화 스텝들, 2280행 "Stationary point found" 전) → **2692행
   "Link1: Proceeding to internal job step number 2"**(freq로의 내부 재시작) → **2865행에
   다시 "Full point group C1"** → 3446행 "Harmonic frequencies" 헤더. 즉 nosymm이 지오메트리
   최적화뿐 아니라 **freq Link1 스텝 진입 직후에도** C1로 확인됨 — proposer9 주장 그대로,
   직접 재현.
3. **[확인, 직접 실행, 우리 코드로]** `sei_pilot.criteria.g16.parse_frequencies`를 실제 로그에
   그대로 돌려 27개 진동수 전부 파싱, 최솟값 77.0255, **음수 0개** 확인 — proposer9의 수치와
   정확히 일치. `RE_FREQ = r"^\s*Frequencies\s*--\s*(.+)$"`(대문자 F로 시작, 앞에 공백만
   허용)를 직접 읽어 " Low frequencies ---  -21.5938 ..." 줄(소문자 f, "Low " 접두)이
   구조적으로 매치될 수 없음을 정규식 자체로 확인 — proposer9가 "같은 방식으로 읽었는지
   확인해달라"고 한 부분, 우리 파서 코드 자체가 그렇게 배제하고 있음을 직접 검증.
4. `f1_observables.json`: `n_imag_at_convergence: 0`, `opt_converged: true`,
   `angle_li_o_c.angle_deg = 129.44`(180° 평면-함정 아님), 5개 ring 결합 1.4083–1.5371 Å
   (전부 살아있음, degenerate 값 1.399/1.4에 안 걸림), `<S**2>` rough/tight 둘 다
   0.7533→0.75 — 전부 원본 JSON 직접 열람으로 대조, 일치.
5. `deck_verification.json`: `eps_matched: true`(직접 열람). `executions.jsonl`:
   run epoch 1787268094 → finish 1787271372, rc=0, cores=64 → wall 3278s=0.91056h →
   **58.28 core-h**, 재계산해 일치.
6. **[확인, epoch 직접 변환]** 잔여 크래시 파일(`l1110.exe.80s-66142,node4884.btr`) —
   run epoch를 로컬시간(+09:00)으로 직접 변환하면 이번 잡은 08:21:34~09:16:12(현지),
   해당 btr 파일 mtime은 06:43:24(현지, `ls --time-style=full-iso`로 직접 확인) — 이번
   실행 창보다 명백히 이전, proposer9의 "무해한 잔재" 판단과 일치.

### 추가 확인 — proposer9의 열린 질문 (3)에 대한 답

**"Harmonic frequencies" 헤더만으로 해석(analytic) Hessian이라고 볼 근거가 충분한가,
더 강한 마커가 있는가**: 있음, 직접 확인함. `endpoint_tight.log`의 freq Link1 스텝
내부 링크 순서 `Link 1101→1102→1110→**1002**→601→701→702→703→716`에서 **Link 1002**가
찍힘(`cpu: 2345.8 elap: 56.3`, 이 잡에서 가장 비싼 단일 링크) — Link 1002는 G16의
CPHF(coupled-perturbed HF/KS) 모듈로, **해석적 2차 미분(analytic Hessian) 전용**이다.
수치미분(freq=numer) 경로였다면 대신 변위된 각 지오메트리마다 힘 계산(Link 701/716류)이
반복되는 형태로 나타나야 하고 CPHF 링크가 이 자리에 오지 않는다. "Harmonic frequencies"
헤더 문구 자체는 analytic/numerical 양쪽에서 동일하게 찍히므로 그것만으로는 구분이 안
되는게 맞고, **Link 1002의 존재가 이 로그에서 확인 가능한 더 강한 마커**다 — proposer9의
직관("헤더만으로 충분한가")이 맞았고, 실제로 더 강한 증거가 로그 안에 있었다.

## 판정
**OK — §39.112의 인증(C-8.1/8.2/8.3 PASS)을 원본 파일에서 독립적으로 재확인, proposer9의
수치·해석 전부와 일치.** 추가로 찾은 결함 없음. Round A의 endpoint_prep_reactant 인증은
그대로 두면 됨. 열린 질문 (3)에 대한 답(Link 1002 = CPHF = analytic Hessian)을
proposer9에게 회신.

---

## 2026-08-21 (13차 배치) — critic (critic12): `u56_2.released` true 플립 + 리빌드 독립 검증

**대상**: coder13이 보고한 `config/b0_reactions.json`의 `u56_2.released` false→true 플립
(lead 경유 사용자 승인), 그에 따른 13개 테스트 수정, `tests/test_p1_excluded_sizing.py`의
가드 재정의, `make_package.sh` 리빌드. 특히 P1 영구 배제가 실제로 유지되는지가 최우선
순위.
**방법**: 전부 원본 소스/원본 config/원본 dist 파일을 직접 읽고 실행 — 코더 보고 문구
그대로 믿지 않음.

### 최우선 확인 — P1 영구 배제가 U56-2 release로 다시 열리지 않는가

1. **[확인, 직접 grep]** `payload/P1.sh`/`sei_pilot/criteria/p1.py` 전문에
   `endpoint_prep_product`/`endpoint_prep_reactant` 문자열이 **단 한 번도** 등장하지 않음
   — 직접 grep으로 확인, 두 파일 모두 0건.
2. **[확인, 직접 read]** `payload/P1.sh`의 C-8 heredoc(76-115행)이 실제로
   `reactant = {"source": r_path}` / `product = {"source": p_path}`만 만듦 — `optimised`/
   `converged`/`n_imag`/`level` 키가 어디서도 채워지지 않음. 테스트 주입 채널
   `SEI_C8_ENDPOINTS_JSON`은 `pbs.sh.tmpl`/`local.sh.tmpl`/`slurm.sh.tmpl` **셋 다에서
   `unset`**됨을 직접 확인 — 실제 클러스터 잡에는 절대 닿지 않는다.
3. **[확인, 소스 대조]** `guards.endpoint_report`(1015-1044행)를 직접 읽어
   `converged is not True`/`optimised is not True`/`n_imag is None` 셋 다 무조건 block함을
   확인 — reactant/product 어느 쪽이든 저 하드코딩된 `{"source": ...}` dict를 받으면
   반드시 세 이유로 동시에 막힌다. **U56-2가 릴리즈됐는지와 완전히 무관** — P1.sh가 그
   잡들의 산출물을 읽는 배선 자체가 없기 때문.
4. **[확인, 직접 실행]** `tests/test_p1_excluded_sizing.py` 9개 전부 재실행 통과. 특히
   `test_c8_never_passes_on_a_missing_product`를 손으로도 재현: 완전한 reactant + 빈
   product(`{}`)를 줘도 `may_start=False`.
5. **[확인, 직접 실행]** `plan.default_items('cpu')`를 직접 호출 — 15개 항목, U56-2의 5개
   (`endpoint_prep_product`, `endpoint_prep_rc_reactant`, `U56_RA_scan`, `U56_RA_qst2`,
   `U56_RB_scan`) 전부 계획에 들어와 있음. `P1`의 `core_hours_budget=64.0`,
   `min_wall_h=1.0` — U56-2 플립과 무관하게 그대로 (재무장 안 됨).

**결론: 실제로 P1을 막는 것은 `endpoint_prep_product`의 부재가 아니라 P1.sh 자신이 어떤
endpoint_prep 산출물도 읽지 않는다는 사실이며, 이는 U56-2의 release 여부와 완전히
독립적으로 성립함을 원본 코드에서 직접 확인했다.**

### 중대 — [확인, 직접 grep] P1 Item 자신의 `rationale`이 이제 거짓말을 한다

`sei_pilot/plan.py:657-663`, P1 Item의 `rationale` 문자열:
```
"...It cannot proceed: C-8 needs a certified PRODUCT endpoint and `endpoint_prep_product`
was removed, so the precondition can never pass..."
```
이 문장은 **더 이상 사실이 아니다** — `endpoint_prep_product`는 U56-2를 통해 계획에
다시 들어와 있다(위 5번에서 직접 확인). 실제로 P1을 막는 이유는 coder13이 새로
문서화한 것(P1.sh가 그 산출물을 아예 읽지 않음)인데, **바로 그 Item 자신의 rationale
문자열은 옛 이유("항목이 없어서 막힌다")를 그대로 들고 있다.** `grep`으로 이 문자열이
이번 diff에서 갱신 안 됐음을 확인, `test_the_exclusion_is_stated_where_a_reader_meets_
the_item`은 "PERMANENTLY EXCLUDED"/"P1b" 부분 문자열만 검사해 이 특정 주장은 테스트
대상이 아님(직접 확인, 실패 없이 통과하는 이유). 이 프로젝트가 이번 세션 내내 잡아온
바로 그 결함 모양("코드가 실제로 강제하는 것과 사람이 읽는 산문이 따로 논다")이,
**이번 diff가 정확히 그 문제를 고치려고 새 테스트 파일까지 쓴 바로 그 항목의 rationale
필드 안에서** 재발했다 — 위험하지는 않다(실제 가드는 맞고 테스트됨), 하지만 이 Item을
직접 읽는 사람(설계 원칙상 바로 이 자리가 "계획자·리뷰어가 실제로 읽는 곳"이라고
`test_p1_excluded_sizing.py` 자신의 독스트링이 명시)은 틀린 이유를 믿게 된다.
**권고**: rationale을 "C-8 requires certified optimised/converged/n_imag=0 endpoints;
P1.sh never reads any endpoint_prep_* output (hardcoded source-only dicts), so both
endpoints always fail C-8 regardless of what else is in the plan"로 갱신.

### 나머지 확인

6. 리빌드 무결성 — `source_digest`(BUILD_STAMP.json) `4953dce25d98f9b3` 확인 일치.
   `package_fingerprint` — BUILD_STAMP.json 자체에는 없는 필드(빌드 스크립트가 콘솔에만
   찍음)임을 grep으로 확인한 뒤, `version.package_fingerprint('.')`를 지금 이 소스
   트리에 직접 재실행 — **`ebc9c92f90026415`, 정확히 일치**(소스가 빌드 이후 안
   흔들렸다는 증거). `n_files=106` 일치.
7. `test_build_stamp.py` 20개 전부 재실행 통과, **`test_real_repo_dist_is_fresh`/
   `test_correct_root_still_verifies` 둘 다 이제 초록**(리빌드 전 계속 빨간불이던
   두 freeze 신호) — 리빌드가 실제로 최신임을 별도 경로로 재확인.
8. `test_readme_matches_code.py` 17개 재실행 통과 — README의 `expected=12905.01` /
   `reserved=12709.39` / `guard=21000`이 소스에서 새로 빌드한 값과 실제로 일치함을
   (숫자를 손으로 대조한 게 아니라) 이 테스트 자체가 소스→README 재생성·대조로
   확인하는 것이므로 신뢰 가능. GPU 프로필도 직접 호출해 2개 항목(`probe_gpu_node`,
   `P4`) 확인, 코더 주장과 일치.
9. `test_u56_plan_items.py`를 직접 읽어 `test_code_never_flips_the_release_flag`가
   `sei_pilot/` 소스 전체를 정규식으로 훑어 `"released"] =` 패턴이 없음을 실제로
   검사하는 진짜 구조적 테스트임을 확인(주장이 아니라 grep 기반 테스트). off-branch
   보존 테스트(`test_gate_would_exclude_u56_items_if_it_were_unreleased`)도 실제
   monkeypatch로 `default_items()` 라이브 경로를 재검사함을 확인.
10. 전체 스위트 독립 재실행: **1639 tests, 전부 OK (exit 0)** — 코더 보고와 일치.

## 판정
**FIX-THEN-RUN(사소한 항목 하나)** — U56-2 릴리즈 자체와 P1 영구 배제는 실제로 안전함을
원본 코드로 직접 확인했다(치명적 결함 없음, 리빌드도 무결). 유일한 지적은 `plan.py:657-
663`의 P1 rationale 문자열이 이제 사실과 다른 것 — 위험하지 않지만(실제 가드는 맞고
테스트됨), "산문이 실제 강제와 따로 논다"는 이 세션의 핵심 교훈과 정확히 같은 모양이라
방치하면 다음 사람이 잘못된 이유로 안심하게 된다. 릴리즈/제출을 막을 이유는 아님 — 문구만
고치면 됨.

---

## 2026-08-21 (14차 배치) — critic (critic12): P1 rationale/margin 수정 독립 재검증

**대상**: coder13이 13차 배치 지적(P1 rationale 문구 stale) 수정 중 추가로 찾은 두 번째
버그 — 같은 rationale 문자열의 "0.0103 core-h"(실제로는 wall-hours가 core-h로 잘못
라벨된 값, 05_STATE.md engineer9 correction과 동일 결함) → 실제 측정값 0.658 core-h/
margin 97x로 수정, `test_p1_excluded_sizing.py`의 상수/threshold도 함께 수정
(*1000 → *50, engineer8 승인 범위 10-50x).

1. **[확인, 직접 read]** `plan.py:657-670` 새 rationale 직접 읽음 — "endpoint_prep_product
   was removed" 문구 제거되고 실제 메커니즘(P1.sh가 endpoint_prep_* 산출물을 안 읽음)으로
   교체됨. "0.658 core-h total, 37 s x 64 cores" / "~97x" 로 갱신됨. 계산 직접 검산:
   37×64/3600=0.6578≈0.658 ✓, 64.0/0.658=97.26≈97x ✓ — 둘 다 05_STATE.md의 engineer9
   정정과 일치.
2. **[확인, 직접 read]** `test_p1_excluded_sizing.py`의
   `test_the_budget_is_generous_against_the_measured_refusal_cost` — `measured_refusal_core_h
   = 0.658`로 바뀌고 threshold도 `*50`(engineer8 원 승인 범위 10-50x)으로 바뀜.
   `64.0 > 0.658*50=32.9` 성립.
3. **[확인, 직접 실행]** `test_p1_excluded_sizing.py` 9/9 통과.
4. **[확인, 직접 실행]** 전체 스위트 재실행: **1639 tests, 실패 2건
   (`test_build_stamp` 쌍) — 소스가 리빌드 이후 또 바뀌어서 나오는 예상된 신호**(코더가
   "리빌드는 확인 후 별도로 한다"고 말한 것과 일치, 회귀 아님).

## 판정
**OK — 13차 배치의 지적 CLOSED, 코더가 같은 패스에서 스스로 찾은 두 번째(margin 라벨)
버그도 CLOSED.** 추가 결함 없음. 리빌드는 아직 안 됨(코더가 확인 후 진행하겠다고 함) —
리빌드 후 한 번 더 `test_build_stamp`만 재확인하면 됨, 재검증 요청 필요.

---

## 2026-08-21 (15차 배치) — critic (critic12): 리빌드 최종 확인

**대상**: coder13의 프롱즈 수정 반영 리빌드(`package_fingerprint 8ae3630c2e100307`,
`source_digest 9d5d7117faf5ec89`).
**확인**: `version.package_fingerprint('.')` 직접 재계산 → `8ae3630c2e100307` 정확히
일치. `BUILD_STAMP.json`의 `source_digest 9d5d7117faf5ec89`/`n_files 106` 직접 열람
일치. `test_build_stamp.py` 20/20 통과(freeze 신호 없음). 전체 스위트 독립 재실행:
**1639 tests, exit 0, 전부 그린**.

## 판정
**OK.** 13-15차 배치에서 다룬 항목 전부(U56-2 release, P1 rationale/margin 수정,
리빌드) 최종 클린 상태로 확인, 이번 라운드 이 트랙에 대해 추가 지적 없음.

---

## 2026-08-21 (16차 배치) — critic (critic14): Track A item 1/3 독립 검증 + 반환된 IRC 로그 직접 판독

**대상**: coder14의 `terminal_status.json` fix (`payload/U56.sh` 18:42, `sei_pilot/outcome.py`
18:41, `tests/test_u56_terminal_status.py`/`test_outcome_retry.py` 18:43), 그리고
`/home/yanselmo/.claude/plans/linear-hopping-frog.md` Track A item 3(`U56_RB_scan` IRC 판독).
**방법**: 반환된 실제 잡 디렉터리(`cpu_machine_pilot_results/sei_pilot_work/jobs/{U56_RA_scan,
U56_RA_qst2,U56_RB_scan}`)의 raw `.log` 직접 판독 + collection/marker 로직 직접 재실행.
코더 보고를 근거로 삼지 않음(보고 수신 전에 검증 착수).

## 판정
**FIX-THEN-RUN** — fix 자체는 기계적으로 동작함(직접 실행으로 확인). 그러나 이 fix가
막으려던 바로 그 두 항목(RA_scan/RA_qst2)이 `cause_class: success`로 기록된다. 아래 1·2는
클러스터 지출 전에 고쳐야 하고, 3은 **지금 읽으면 안 되는 verdict**를 만든다.

### 치명적 (결과가 틀림)

1. `src/pilot_package/sei_pilot/criteria/g16.py:401` — **[확인]** `IRC_MINIMUM_MARK =
   "Minimum found on this side of the path"` 는 이 클러스터의 G16(`g16.linda.c01`)이 실제로
   찍는 문자열이 아니다. 실제 문자열은 **`PES minimum detected on this side of the pathway.`**
   (근거: `U56_RB_scan/irc_forward.log:2703`, `irc_reverse.log:2611`. 반환 트리 전체에서
   코드가 찾는 문자열은 **0회**, 실제 문자열은 이 2개 파일에만 존재).
   → 이 입력이면 이렇게 틀린다: RB_scan은 forward/reverse **둘 다 진짜로 minimum에 도달해
   `Reaction path calculation complete.` + `Normal termination`** 으로 끝났는데
   `irc_completion_{forward,reverse}.json`은 `minimum_found: false`,
   `termination_reason: "normal_termination_without_a_minimum_marker"` 로 기록됐다. 하류에서
   `guards.irc_direction_ok`는 `n_points`(=1) 미달을 **budget** 으로 태그하고
   (`guards.py:158-159`), `guards.py:568-580`의 교리대로 "caps가 틀렸다 = attempt당 더 써라"
   처방으로 읽히며, `1/p` 산정의 CHEMICAL 분모에서 빠진다. 실제로는 289 s만에 minimum에
   도달한, 돈을 더 쓸 이유가 전혀 없는 케이스다.
   → 고쳐라: 두 문자열 모두 허용(구 버전 호환), 그리고 실제 로그 슬라이스를 fixture로 추가.
   **[확인] 이 sentinel은 지금까지 실로그로 검증된 적이 한 번도 없다** —
   `tests/fixtures/`에 있는 IRC 실로그는 maxpoints 2건뿐이고(PROVENANCE 있음, 진짜),
   `minimum_found: True` 케이스는 `test_irc_truncation_c2.py:109,180,200`,
   `test_criteria.py:264`, `test_guards.py:443`에서 **전부 손으로 만든 dict**다. 파서를 통과한
   적이 없으므로 이 테스트들은 sentinel에 대해 아무것도 검증하지 않는다.

2. `src/pilot_package/sei_pilot/criteria/g16.py:437-438` — **[확인]** `normal is not True` 인
   모든 경우에 `termination_reason`을 `"no_marker (log ends without a G16 termination line --
   wall-clock or budget kill leaves exactly this shape)"` 로 단정한다. RA의 4개 IRC 로그는
   **G16 termination line이 있다**: `Error termination via Lnk1e in .../l123.exe`
   (`U56_RA_scan/irc_forward.log:30457`, `irc_reverse.log:15882`,
   `U56_RA_qst2/irc_forward.log:29082`, `irc_reverse.log:10066`), 그 직전에
   `Maximum number of corrector steps exceded.`
   → 이 입력이면 이렇게 틀린다: engine-class(§39.69) 실패가 문자열 자체로 BUDGET-class로
   서술된다. wall 사용량은 1.8–5.3 h(48 h cap 대비)인데 처방은 "cap을 늘려 재시도"가 되고,
   재실행 비용은 stages 기록 기준 **RA_scan 336 core-h / RA_qst2 113 core-h**(직접 합산:
   `jobs/*/stages/*.json`의 wall_s×total_cores)이며 결정론적으로 같은 지점에서 다시 죽는다.
   → 고쳐라: `Error termination`이 있는 로그와 그냥 끊긴 로그를 구분하고, 전자에 budget을
   단정하는 문장을 쓰지 마라(원인 문자열은 innermost frame에서 뽑는 `gfn2_scan.parse_failure`
   패턴이 이미 있다).

3. `src/pilot_package/sei_pilot/guards.py:200` — **[확인]** condition 7 branch (b)를
   `completion.get("truncated")` 로 연다. 그런데 같은 함수의 주석(:185)과 §39.55(d) 원문은
   branch (b)를 **`maxpoints` + B+ agreement** 로 규정한다. `truncated`는 maxpoints뿐 아니라
   wall kill **과 엔진 crash**에도 True다.
   → 이 입력이면 이렇게 틀린다: `U56_RA_scan`은 IRC 적분 도중 **Error termination**으로 죽었고
   (forward 20 points, reverse 5 points), `bplus_{forward,reverse}.json`은 둘 다
   `agreement: true`. 따라서 현재 코드로 C-2를 돌리면 **crash한 경로에 대해 "connection
   established via branch (b)"** 가 나온다. 게다가 reverse의 B+ 두 시작점은 `mid` = path point
   2 (arc 0.684), `last` = point 5 (arc 1.706) — saddle에서 1.0 arc 떨어진 두 점의 비교이고,
   §39.70(2)가 "saddle에 너무 가까운 점"을 피하라고 한 바로 그 영역이다. 5-point stub에서의
   agreement가 단독으로 connection을 성립시킨다.
   → 고쳐라(coder 단독 판단 금지, 룰 필요): branch (b)의 조건을 `maxpoints_reached`로 좁히든지,
   proposer가 "engine crash + B+ agreement"를 명시적으로 허용하든지 둘 중 하나. **그때까지
   RA_scan의 C-2 verdict를 '연결 성립'으로 읽지 마라.**

### 중대 (낭비/재현불가)

4. `payload/U56.sh:270` — **[확인, 직접 실행]** `STATUS="ts_candidate_produced"` 가 scan/TS
   opt/IRC **이전에** 기본값으로 설정되고, 열거된 실패 분기에서만 하향된다. IRC가 error
   termination으로 죽는 경로는 열거되어 있지 않다(:1093은 "모든 direction이 refuse된" 경우만).
   반환된 실제 3개 디렉터리에 대해 `common.sh`의 `sei_terminal` + `sei_write_marker`를 그대로
   실행한 결과(`/tmp` 사본, 원본 불변):
   ```
   U56_RA_scan  terminal_status: ts_candidate_produced / cause_class: success   ← IRC 2/2 crash
   U56_RA_qst2  terminal_status: ts_candidate_produced / cause_class: success   ← IRC 2/2 crash
   U56_RB_scan  terminal_status: ts_candidate_produced / cause_class: success
   marker payload: outcome=ts_candidate_produced cause_class=success (3/3)
   ```
   `outcome: absent` 는 확실히 사라졌다(fix의 1차 목적 달성). 그러나 `common.sh:76-79`가 이
   필드의 존재 이유로 못 박은 문장 — *"a `done` marker can never again hide a segfaulted/
   not_converged job behind rc=0"* — 은 **이 두 항목에 대해 달성되지 않았다.** 게다가
   `cli.py:668`은 `cause not in (SUCCESS, "absent")` 일 때만 ⚠ 경고줄을 찍으므로, 다음 라운드
   `run.sh`는 IRC가 두 번 crash한 잡을 **경고 한 줄 없이** "이미 완료 → 건너뜀"으로 지나간다.
   → 고쳐라: payload가 이미 같은 자리에서 `irc_completion_${dir}.json`(=`normal_termination`)을
   쓰고 있으므로, **실행된** direction 중 하나라도 `normal_termination != true`면 STATUS를
   하향하라. 단, cause class는 코더가 단독으로 정하지 마라 — `engine`은 retry class이고
   (`outcome.py:66`), `cli.py:628`은 **pkg_fingerprint가 바뀌면 plumbing outcome을 자동
   재제출**한다. 이번 수정으로 fingerprint는 반드시 바뀐다(`test_build_stamp` 이미 red,
   변경목록에 `payload/U56.sh`·`outcome.py` 포함) ⟹ `engine`으로 매핑하면 다음 `run.sh`에서
   **RA_scan 336 + RA_qst2 113 = 449 core-h**가 SCF/IRC 설정 변경 없이 자동 재지출되고 같은
   지점에서 다시 죽는다. lead/proposer 룰이 필요한 지점.
   (부수 확인: `ts_candidate_produced → SUCCESS` 매핑 덕분에 **현재 상태에서는** 자동 재제출이
   일어나지 않는다. 즉 지금 taxonomy는 "비용상 안전, 라벨상 거짓"이다.)

5. **[확인] 승인된 plan의 전제 1건이 사실과 다르다** (Track A item 3):
   plan은 RB_scan이 `truncated: true`로 라벨됐다고 쓰고 coder14에게 그 이유를 찾으라고 지시했다.
   실제 파일은 `truncated: false`(forward/reverse 둘 다)이다. 실제 이상 징후는 정반대 —
   1 point(arc 0.183/0.223)만에 PES minimum에 도달한 경로가 `minimum_found: false` +
   `truncated: false`로 기록되어 있다(위 1번). item 3은 이 방향으로 다시 써야 한다.

### 사소

6. plan Track A item 2의 기하 선택 지시("coefficient가 ~35를 넘기 직전 점")는 실데이터에서
   잘 정의되지 않는다. **[확인]** `U56_RA_scan/irc_forward.log`의 beta 계수 계열(SCF cycle 순):
   32.5, 34.9, 37.1, 37.0, 38.2, 38.2, 37.4, 33.4, 33.2, 32.9, 33.6, 32.2, **31.1**, ... 이후
   상승해 38.4–38.7에서 **약 30 cycle 동안 평탄**. 즉 3번째 cycle에서 이미 35를 넘고 13번째에
   31.1로 되돌아온다. 진단용 기하는 cycle 번호가 아니라 **path point 번호**로 지정해야 한다.

### 확인하지 못한 것 / proposer·lead에게 넘기는 것

7. **[의심] "SCF instability가 IRC corrector 실패를 유발한다"는 인과 주장은 반환 데이터로
   뒷받침되지 않는다.** 반증 방향의 사실들(전부 [확인]):
   - `U56_RA_scan/irc_forward.log`의 SCF는 **66회 전부 수렴**(`SCF Done` 66회,
     `Convergence failure` 0회). SCF 비수렴은 일어나지 않았다.
   - `NBasis=173`, `NBsUse=173`, `EigRej=-1.00D+00` — G16이 1.0D-06 컷오프에서 **basis
     function을 하나도 제거하지 않았다**. 통상적 의미의 linear dependence 발동 기록이 없다.
   - **certified endpoint**(`endpoint_prep_product/endpoint_tight.log`)의 같은 warning 값은
     34.4 / 35.8 로, RA가 실패한 구간의 평탄값(38.4–38.7)과 **같은 자릿수**다 ⟹ 이 계수는
     성공/실패를 가르지 못한다. RB_scan은 같은 warning이 ~20에서 정상 종료.
   - 실제 죽는 지점의 텍스트는 전자구조가 아니라 **적분기**다:
     `Angle between gradients (degrees)= 55.7131`, `Maximum DWI gradient std dev = 0.362`,
     corrector `New End-Old End Dist. = 0.062911` vs threshold `0.010000`, 20 step 소진.
     같은 점의 힘은 이미 작다(`Cartesian Forces: Max 0.004792 RMS 0.001534` Ha/Bohr) — 경로
     끝의 평탄한 계곡에서 corrector가 못 붙는 전형적 모양.
   ⟹ `stable=opt`가 무의미하다는 뜻은 아니지만, **그것은 두 번째로 유력한 가설을 테스트한다.**
   같은 chk(`irc_forward.chk` 존재)에서 `IRC(Recorrect=Never)`/StepSize 변경 재시작이 더 직접적인
   판별이고 비용도 비슷하다. Track A item 2를 지출하기 전에 proposer/lead가 어느 가설을 사는지
   정해야 한다. (재현성 자체는 실행해 보지 않았으므로 [의심]으로 남긴다.)

### 실행 기록 (주장 아님)
- `tests && python3 -m unittest test_session_digest` → **Ran 63, OK** (plan의 63/63 조건 충족).
- `python3 -m unittest test_u56_terminal_status test_outcome_retry` → **Ran 21, OK**.
- 전체 스위트 `discover` → **Ran 1646, failures=4**: `test_build_stamp` 2건 +
  `test_readme_matches_code` 2건. 전부 "tarball이 소스보다 낡음" freeze 신호이며 변경 목록은
  `README_USER.cpu.md, payload/U56.sh, sei_pilot/{budget,cli,criteria/g16,outcome}.py`.
  회귀 아님. (README 수치 차 12,709 vs 14,245 core-h = 1,536은 오늘 오전 변경분에서 온 것으로
  coder14의 이번 수정과 무관.)
- taxonomy 신규 status 9종이 실제로 `U56.sh`에서 할당되는지 grep으로 1:1 확인 — 전부 할당됨
  (dead vocabulary 없음).

### 16차 배치 — 추가 확인 (critic14, proposer10의 §39.113(e)[재번호 전 §39.110(e)] 자기정정 검증 후)

**[확인]** proposer10이 §39.113(e)에 새로 적은 수치 `endpoint_prep_rc_reactant ~71-79`를 보고로
받지 않고 직접 재현: `jobs/endpoint_prep_rc_reactant/endpoint_tight.log`의 alpha/beta 계수는
**71.0 / 67.0 / 78.9 / 71.3**, `Normal termination` 2회. 즉 반환 트리 전체에서 이 warning의
**최대값은 실패한 IRC가 아니라 C-8 인증을 통과한 endpoint**(E21/R-C reactant, 21원자,
n_imag=0)에 있고, RA가 죽은 구간의 평탄값(38.4–38.7)의 약 두 배다. §39.113(e)의 결론(이 계수는
성공/실패를 가르는 판별자가 될 수 없다)을 독립적으로 재확인한다.

🔴 **파생되는 별개의 질문 — plan Track B item 4가 이미 열어둔 "인증된 결과를 다시 봐야 하는가"의
방향을 이 수치가 뒤집는다.** 만약 이 warning이 파동함수에 대해 실제 의미가 있다면, 그 신호가
가장 큰 계산은 **C-8이 인증에 쓰는 Hessian을 낸 바로 그 잡**이다. 즉 진단이 필요한 최악 지점은
mid-IRC 기하가 아니라 `endpoint_prep_rc_reactant`의 기하일 수 있다. 다만 21원자
cation+open-shell의 실측 단가는 존재하지 않고(S₂₁ cube law는 engineer8이 RETRACT), 11원자
mid-IRC `stable=opt`은 값이 싸다 ⟹ **제안(강제 아님)**: Track A item 2는 계획대로 11원자에서
집행하되, `endpoint_prep_rc_reactant` 기하를 두 번째 후보로 engineer 가격 산정에 올려라.
`stable=opt`가 11원자에서 instability를 찾든 못 찾든, 인증 무결성 질문은 21원자 쪽에 남는다.

**[확인] §39.113(e) 본문 재검증**: (c) 정정(bounded oscillation, SCF Done 66/Convergence failure 0,
EigRej=-1.0), (b) 정정(`PES minimum detected...` 양방향, IRC는 완주였다, parser bug는 coder 몫),
falsifiability 진술 모두 문서에 실제로 기록돼 있음을 직접 열람 확인(20222-20297행). 지운 것 없이
정정 관행대로 병기됨. Li 44% mode-character 반론을 독립적으로 유지한 것도 타당 — IRC가 완주했다는
사실은 mode가 옳다는 근거가 아니다.

---

## 2026-08-21 (17차 배치) — critic (critic14): coder14의 Track A item 3 + item 2 산출물 검증

**대상**: `criteria/g16.py`(IRC minimum marker), 신규 fixture 2건,
`tools/build_u56_ra_stability_probe.py` + `config/qc_levels.json`의 `stability_test` job_type,
그리고 coder14가 명시적으로 재검토를 요청한 3개 항목((a) cause class 타당성, (b) 기존 status
불변 여부, (c) 하단 `_write_terminal`의 도달성).

## 판정
**FIX-THEN-RUN** — item 3 수정은 실데이터로 정확히 동작함(직접 실행 확인). 진단 deck도 기하·
route·용매·기저 전부 production과 동일함을 확인했다. 그러나 **진단 잡을 제출하기 전에 고쳐야 할
것 2건**(nosymm 누락, 샘플 지점)이 있고, terminal_status fix에는 아직 구멍이 하나 남아 있다.

### 확인된 것 (직접 실행, 보고 인용 아님)

1. **[확인] minimum marker 수정은 실로그 6개 전부에서 옳게 동작한다.** 수정된 파서를 반환된
   IRC 로그 6개에 직접 돌린 결과:
   ```
   U56_RB_scan forward/reverse  min=True  trunc=False reason=minimum_found      ← 고쳐짐
   U56_RA_scan forward/reverse  min=False trunc=True  reason=no_marker(...)
   U56_RA_qst2 forward/reverse  min=False trunc=True  reason=no_marker(...)
   ```
2. **[확인] 신규 fixture 2개는 실로그의 verbatim slice다.** Python으로 원본 로그 문자열에
   대한 substring 포함 여부 검사 — `g16_irc_forward_minimum_u56rb.log`(476줄),
   `g16_irc_forward_point1_u56ra.log`(1201줄) 둘 다 True. 합성 데이터 아님.
3. **[확인] coder14 질문 (b) — 기존 status의 cause class는 하나도 안 바뀌었다.** 수정 전
   내가 직접 읽어둔 16개 entry를 pre-image로 대조: 변경 0건, 총 키 16→28.
4. **[확인] coder14 질문 (c) — 조기 `exit` 10개 전부가 바로 앞 줄에서 `_write_terminal`을
   호출한다.** 행 단위 대조: 46←45, 51←50, 64←63, 71←70, 78←77, 189←188, 229←228,
   266←265, 322←321, 523←522, 하단 1139 → `exit 0` 1151. 도달성 자체는 성립.
5. **[확인] item 2 진단 deck은 production과 동일한 계산이다.** 실제로 빌드해서
   `jobs/U56_RA_scan/irc_forward.gjf`와 대조: functional/기저 블록(`****` 블록 문자열 동일),
   `eps=18.5`, charge/mult `0 2`, `Int(Grid=UltraFine)`, level3(def2-SVPD) 전부 일치.
   기하는 `parse_irc_path_frames`의 frame 0과 좌표까지 동일(1e-6 이내, 11원자) — placeholder
   아님. manifest에 `solvent_deck_label: [UNVERIFIED — cluster route smoke required]`와
   package_fingerprint/invocation provenance가 기록됨.
6. **[확인] `SEI_QC_PURPOSE=smoke` 우회는 덱 내용을 바꾸지 않는다** — coder14 주장 검증:
   `resolve_solvent_deck`를 smoke/production 두 번 직접 호출 → route fragment와
   `eps=18.5` 동일, 차이는 label과 production 쪽의 거부(이 out-dir에 deck_verification.json이
   없으므로) 뿐.
7. **[확인] `minimum_found` 소비자 재확인** (coder14 질문 (c)의 두 번째 절): `src/` 전체에서
   `criteria/g16.py` 밖의 소비자 0건. `summarize`의 IRC 판별 게이트(:865)에 ALT를 OR로 넣은
   것도 의미 변화 없음("이 로그가 IRC인가" 판별을 넓힐 뿐).
8. **실행 기록**: `test_session_digest` **63/63 OK**; `test_irc_truncation_c2`,
   `test_u56_terminal_status`, `test_u56_ra_stability_probe`, `test_outcome_retry` 합쳐
   **110/110 OK**; 전체 `discover` **Ran 1650, failures=4** — 전부 기존 freeze 신호
   (`test_build_stamp` ×2, `test_readme_matches_code` ×2), 회귀 아님.

### 중대 (진단 잡 제출 전에 고쳐야 함)

9. `config/qc_levels.json` — **[확인] 신규 `stability_test` job_type만 `nosymm`이 없다.**
   같은 파일의 다른 job_type은 전부 갖고 있다:
   ```
   ts_opt              "#p nosymm {functional}/{basis} ..."
   irc_forward         "#p nosymm {functional}/{basis} ..."
   endpoint_opt_rough  "#p nosymm {functional}/{basis} ..."
   stability_test      "#p {functional}/{basis} {solvent} stable=opt Int(Grid=UltraFine)"
   ```
   → 이 입력이면 이렇게 틀린다: G16이 standard orientation에서 대칭을 잡으면 stability 분석이
   대칭 허용 orbital rotation으로 제한될 수 있고, 그러면 **symmetry-breaking instability를
   못 보고 "stable"로 보고**한다. 이 오류의 방향이 하필 §39.113(e)의 falsifiability 진술이
   기대는 방향("instability 없음 ⟹ 파동함수 설명 기각")과 같다 — 즉 거짓 음성이 그대로 룰이
   된다. 진단의 대상 기하는 IRC가 `nosymm`으로 만든 것이므로 route도 같아야 한다.
   → 고쳐라: `stability_test` route에 `nosymm` 추가(한 단어).

10. `payload/U56.sh` — **[확인] SIGTERM trap도 wall tripwire도 없다.** `P5.sh:115`는
    `trap '_p5_write_marker wall_exhausted ...; exit 9' TERM`을 갖고 있고
    (05_STATE §1a에 "PBS가 SIGKILL 전에 SIGTERM을 보낸다, 한 번의 기회"로 기록됨),
    `endpoint_prep.sh`는 단계별 예산 검사를 갖고 있다. U56.sh는 **둘 다 없다** — 게다가
    :1125의 자기 주석이 "wall cap과 core-h 예산은 payload 안에서 보이지 않는다"고 적고 있어,
    trap이 남은 유일한 수단이다.
    → 이 입력이면 이렇게 틀린다: ADR-114의 48 h wall cap에 걸린 U56 시도는 SIGTERM으로
    :1139 이전에 죽는다 ⟹ `terminal_status.json` 없음 ⟹ `outcome: absent` — **이번 fix가
    없애려던 바로 그 상태가, 가장 비싼 실패 모드(48 h × 64 cores = 3,072 core-h)에서 그대로
    남는다.** 게다가 `absent`는 retry class가 아니므로 그 항목은 조용히 영구 정지한다.
    이번 라운드에 안 터진 이유는 RA_scan이 48 h 중 5.3 h만 썼기 때문이고, cap에 근접하도록
    sizing된 것은 21원자 R-C 시도다. → `P5.sh`의 한 줄을 복사하라.

11. **[확인] 진단이 경로의 건강한 끝만 샘플한다.** 선택된 지점은 `--point-index 0`
    = arc 0.34202 (전체 6.83462의 **5%**), 인접 warning 34.89, 계산이 정상적으로 성공한
    구간이다. 실제 죽는 지점은 Pt 21, arc≈6.8, warning≈38.6이다. → 여기서 "stable"이 나와도
    **죽는 지점의 파동함수에 대해서는 아무것도 falsify하지 못한다**(비대칭 추론). 이건 coder의
    실수라기보다 plan의 지시("~35를 넘기 직전")를 문자 그대로 구현한 결과이며, 그 지시가
    실데이터에서 잘 정의되지 않는다는 것은 16차 배치 6번에 이미 적었다.
    → 고쳐라: **코드 변경 0**. 같은 도구를 `--point-index 19`(arc 6.835)로 한 번 더 돌려 덱
    2개를 만들고 둘 다 제출하라. 11원자 single point 2개는 비용상 무의미한 수준이고, 그래야
    "onset이 있는가"라는 질문에 답이 된다.

### 사소

12. `criteria/g16.py:392-399`의 `[VERIFIED against ...]` 블록은 여전히 세 문자열을 함께
    나열하는데 그중 `Minimum found on this side of the path`는 이제 미검증으로 확인됐다.
    바로 아래 :402-413 주석이 정확히 그 사실을 적고 있어 실질 위험은 없지만, "산문이 실제
    검증 범위보다 넓게 말한다"는 이 프로젝트의 반복 결함과 같은 모양이다 — VERIFIED 라벨의
    적용 범위를 maxpoints 줄로 좁혀 적으면 끝난다.
13. **[확인]** 신규 fixture 2개가 `tests/fixtures/PROVENANCE.md`에 등재되지 않았고
    (파일 mtime 18:41 < fixture 생성 18:45+), 기존 IRC fixture가 갖고 있는 파일 내
    `[FIXTURE SLICE -- NOT A COMPLETE G16 LOG] / Provenance: ...` 헤더도 없다. 내용은 진짜임을
    내가 확인했지만(위 2번), 다음 사람은 그 확인을 다시 해야 한다.

### 여전히 열려 있음 (16차 배치에서 제기, 이번 배치에서 미처리)

14. `criteria/g16.py:437-438` — RA 로그 4개가 `Error termination via Lnk1e`를 갖고 있는데도
    `termination_reason`이 "log ends without a G16 termination line -- wall-clock or budget
    kill" 로 단정된다. engine-class가 BUDGET-class로 서술되는 문제, 미수정.
15. `guards.py:200` — condition 7 branch (b)가 `maxpoints_reached`가 아니라 `truncated`로
    열려, crash한 RA_scan에 대해 "connection established"가 나온다. lead 판정 대기.
16. `payload/U56.sh:270` — IRC error termination 시 STATUS 미하향 ⟹ `cause_class: success`.
    lead 판정 대기(engine으로 내리면 449 core-h 자동 재지출).
17. `minimum_found`를 읽는 코드가 아직 없다 — 이번 fix로 기록은 진실해졌지만 RB는 여전히
    `n_points=1`로 BUDGET 태그를 받는다("측정했으나 읽지 않는" 형태). guards/proposer 몫.

### 17차 배치 — 추가 (critic14): proposer10의 §39.111/§39.112 검증 — 내용 OK, 번호 충돌 3건

1. **[확인] §39.115(신규, 재번호 후; 당시 §39.112, 20430행) 내용 타당.** 21원자 비용을 지어내지 않았고(T21-se 미가격
   상태 명시), 인증서 취소 자체는 결과 이후로 미룸, 11원자 쌍과 분리 유지 — 내가 제기한 프레이밍
   그대로. 이의 없음.
2. **[확인] §39.114(신규, 재번호 후; 당시 §39.111, 20329행)의 arc-length 표는 내 측정과 일치한다** (TS 포함/제외 관례
   차이만): 내 `parse_irc_path_frames` 기준 forward 20 frames(arc 0.342…6.835), reverse 5
   (…1.706); B+ xyz 헤더는 `path point 10, arc 3.41808` / `point 20, arc 6.83462` /
   reverse `point 2, arc 0.68385` / `point 5, arc 1.70584`. proposer10의 "21 (idx 0-20)"은
   saddle(Point Number 0)을 포함한 계수다. **⚠ 이 게이트는 코드가 될 것이므로 관례를 하나로
   못박아야 한다** — `parse_irc_path_frames`는 saddle을 포함하지 않는다. "~10 IRC points"를
   G16 로그의 `Point Number`로 세면 off-by-one이 된다.
3. 🔴 **[확인] 구현 함정 — `low_confidence`를 guards가 읽는 필드 밖에 두면 아무 일도 안 일어난다.**
   `guards.py:200`은 `bplus.get("agreement") is True` 를 본다. §39.114(1)이 요구한 강등을
   `agreement: true` 는 그대로 두고 옆 필드에 적으면, 게이트는 **여전히 통과**시킨다 — 이
   프로젝트가 반복해서 찾아낸 "측정했으나 읽지 않는" 결함의 재생산이 된다(rcfc `copied`,
   `cores_observed`, `forward_rc`/`reverse_rc`와 같은 형태). 강등은 `agreement` **그 필드
   자체**가 `True`가 아니게 만들거나, guards가 분리 조건을 직접 읽게 해야 한다.
4. 🔴 **[확인] 섹션 번호 충돌 3건.** proposer10이 §39.110 / §39.111 / §39.112 를 새로 썼는데
   셋 다 proposer9가 이미 쓴 번호다:
   ```
   19787 §39.110 (proposer9, li_ec2_cation 자기정정)   ↔ 20067 §39.110 (proposer10, TS read-out)
   19881 §39.111 (proposer9, SCF/Hessian split 없음)   ↔ 20329 §39.111 (proposer10, branch (b) gate)
   19943 §39.112 (proposer9, Round A 인증)             ↔ 20430 §39.112 (proposer10, 3번째 stable=opt)
   ```
   이미 인용이 갈라져 있다: `04_REVIEW_LOG.md:6935`(critic12)와 `05_STATE.md:1560`의 "§39.112"는
   proposer9의 인증 항목을, `05_STATE.md:1352,1357`의 "§39.111"은 proposer10의 새 룰을 가리킨다.
   문서가 팀의 유일한 공유 기억인데 인용이 두 곳으로 풀린다. 다음 빈 번호는 **§39.113**이다.
   → proposer10에게 재번호 요청(02_METHOD_SPEC.md는 내 소유가 아니므로 수정하지 않음). 내
   16차 배치 항목의 "§39.110(e)" 인용도 재번호 후 함께 갱신되어야 한다.

### 17차 배치 — 추가 (critic14): lead의 `deterministic` 판정 검증 — 오늘은 안전, 다음 라운드에 지뢰

**대상**: lead 판정 — IRC가 error termination으로 죽은 U56 항목의 `cause_class`를 `engine`이
아니라 **`deterministic`**(never-retry)으로. 내가 제기한 449 core-h 자동 재지출 위험을 막으려는
선택. 비용 목적은 달성된다. 그러나 **레이블이 두 가지를 추가로 주장한다**.

1. 🔴 **[확인, 직접 실행] `deterministic`은 다음 라운드에 그 항목을 영구히 건너뛰게 만든다 —
   IRC 덱을 고쳐도 그렇다.**
   ```
   outcome.should_retry('deterministic') = False
   state.SPEC_DIGEST_FIELDS = ('key','payload','extra_env','nodes','array','gpus','cores_per_task')
   payload 내용만 바뀐 경우 digest: 54876cd4e8fb3086 → 54876cd4e8fb3086  (stale? False)
   같은 설정이 extra_env 에 있었다면:  54876cd4e8fb3086 → c32c78160f6d0b1d (stale? True)
   ```
   `payload` 필드는 **스크립트 이름**("U56.sh")이지 내용이 아니다. 따라서 coder가 U56.sh 안의
   IRC route에 `IRC(Recorrect=Never)`/StepSize를 넣어도 spec_digest는 그대로 →
   `cli.py`의 stale 분기 미발동 → `should_retry` False → `skipped_done`으로 영구 통과.
   사용자가 표준 절차대로 `./run.sh`를 쳐도 **아무 일도 일어나지 않고**, 출력되는 사유는
   "결정론적 입력 결함 — 같은 덱은 같은 crash, 재시도 금지 (§39.87)" 로, 덱이 바뀐 뒤에는
   **거짓인 문장**이다. `--rerun <key>`를 쳐야 하는데 그건 사용자가 알 수 없다.
   🔒 이건 이 프로젝트가 이미 한 번 당한 결함의 재발이다 — `state.py:59-68`의 주석이 그 사고를
   적고 있다(EpsInf 라운드: done 마커가 spec 변경보다 오래 살아남아 EpsInf=1.0 arm이 아예 안
   돌았다). spec_digest는 바로 그걸 막으려고 도입됐는데, **payload 내용은 digest 밖**이라 같은
   구멍이 payload-내부 덱 변경에 대해 그대로 남아 있다.
   → 값싼 고침(설계 아님, 기존 메커니즘 사용): IRC 적분기 설정을 U56 Item의 `extra_env`로
   올려라. 그러면 그 값을 바꾸는 순간 digest가 바뀌어 정당하게 stale이 되고, 재무장이 자동이
   된다. 위 실행 결과의 마지막 줄이 그 동작을 그대로 보여준다.
   ⚠ **오늘은 막히는 게 없다**: proposer10의 §39.114(2) 진단은 손으로 제출하는 standalone 덱
   (coder14의 probe와 같은 형태)이라 harness를 타지 않는다. 지뢰는 *수정이 끝난 다음 라운드*에
   R-A 시도를 다시 돌리려 할 때 밟는다.

2. **[의심] "same deck → same crash, forever"는 아직 측정된 적이 없다.** 이 실패는 한 번도
   재현 시도가 없었고, `deterministic`은 그 재현 시도를 영구히 억제하는 필드다. 이 프로젝트에는
   반대 방향의 선례가 있다 — GFN2 `rc=128`은 "명백히 결정론적"으로 읽혔지만 standalone에서
   3/3 재현되지 않았고(05_STATE §1: 환경 의존), 게다가 여기 로그의 segfault는 Linda 병렬 종료
   잔해다. 재현 비용은 한 방향 약 48 core-h(`u56_irc_forward` 실측 47.7)이며, 필요하다면
   `irc_forward.chk`에서 손으로 재시작할 수 있다(probe와 같은 경로).

3. **[확인] 클래스 경계 문제(작지만 기록해 둔다).** `deterministic`은 현재 `input_defect`
   하나에서만 온다. `outcome.py`의 정의(§39.87)는 "**덱**의 결함, G16이 한 줄로 원인을 말하고
   매번 같은 지점에서 죽는다"이다. 이번 실패는 덱 결함이 아니다 — 덱은 유효했고 20 point의
   실제 화학이 계산됐으며 실패 텍스트는 적분기 허용오차다. 여기에 `deterministic`을 붙이면
   그 클래스의 뜻이 "덱이 잘못됐다"에서 "재실행해도 같을 거라고 우리가 믿는다"로 넓어진다 —
   §39.69가 `engine`을 만들 때 세운 "처방으로 정의하고 경계를 결정 가능하게"라는 규율의 반대
   방향이다. 게다가 `deterministic`의 처방은 "할 게 없다"인데, 팀은 방금 §39.114(2)로 **할
   일(진단 2건)을 승인**했다. 라벨과 실제 계획이 어긋난다.
   → 근본 문제는 라벨이 아니라 **retry 규칙이 "무엇이 바뀌었나"가 아니라 "빌드가 바뀌었나"에
   걸려 있다는 것**이다(`cli.py:628`). 그래서 `engine`은 지금 낭비하고 `deterministic`은 나중에
   막는다 — 둘 다 한쪽 방향으로 틀린다. lead의 선택은 **오늘 비용 측면에서 옳다**; 위 1번의
   재무장 경로만 함께 박아두면 된다.

### 17차 배치 — 추가 (critic14): 재번호 검증 결과 — 02_METHOD_SPEC은 클린, 05_STATE 인용 1건 오배정

**[확인] 재번호 자체는 정확하다.** `02_METHOD_SPEC.md` 직접 확인:
```
19787 §39.110 (proposer9)  19881 §39.111 (proposer9)  19943 §39.112 (proposer9)   ← 원본 무손상
20067 §39.113 (proposer10, TS read-out — 구 §39.110)
20329 §39.114 (proposer10, branch (b) gate (1) + 진단 설계 (2) + 구현 요건 (3) — 구 §39.111)
20455 §39.115 (proposer10, 3번째 stable=opt — 구 §39.112)
```
proposer10 범위(20060-20480)에 옛 번호 잔재 0건. §39.114(3)에 내가 지적한 두 항목(강등은
`agreement` 필드 자체가 `True`가 아니어야 함 / 임계값은 `parse_irc_path_frames` 관례로 표기)이
**build-time requirement**로 명시돼 있음을 본문에서 직접 확인. 본인 로그의 인용도 갱신했다
(§39.110(e)→§39.113(e), §39.111(1)→§39.114(1), §39.111(2)→§39.114(2), §39.112→§39.115;
7423-7434의 충돌 기록 표는 사건 기록이므로 원문 유지).

🔴 **[확인] 그러나 `05_STATE.md:1365`의 인용이 틀렸다.** branch (b) gate 룰을 **§39.113**으로
적었는데, §39.113은 proposer10의 **preliminary TS read-out**이고 그 룰은 **§39.114(1)**이다
(구 §39.111의 (1)절). `05_STATE.md:1379`의 §39.114(진단 설계)는 맞다 — 다만 그것도 같은 §39.114의
(2)절이므로, 한 섹션이 두 bullet으로 갈라지면서 앞의 하나가 다른 섹션 번호로 옮겨 붙었다.
→ 이 입력이면 이렇게 틀린다: coder14가 state 문서를 따라 "§39.113을 구현"하러 가면 룰이 없는
섹션에 도착한다. `1365 → §39.114(1)`, `1379 → §39.114(2)`로 고쳐야 한다. `1592`의 §39.112
(proposer9 인증)는 정확 — 그대로 두는 게 맞다.

🔴 **[확인] 파생 문제 — 확정된 진단 기하가 coder14가 이미 빌드한 덱과 일치하지 않는다.**
`05_STATE.md:1379-1383`이 옮긴 §39.114(2)의 결정은 `stable=opt`를 **두 기하**(arc≈1.7, arc≈6.83)
에서 돌리는 것이다. 그런데 coder14가 빌드해 둔 덱은 `--point-index 0`, **arc 0.34202**로 둘 중
어느 것도 아니다(내 16차/17차 지적 "5%만 샘플한다"에 대한 응답으로 설계가 옮겨간 결과다).
실제 인덱스 매핑(`parse_irc_path_frames`, saddle 제외, 20 frames):
```
index 4  -> arc 1.70908   (§39.114(2)의 첫 번째 목표)
index 19 -> arc 6.83462   (§39.114(2)의 두 번째 목표, crash 직전 마지막 점)
index 0  -> arc 0.34202   (기존에 빌드된 덱 — 이제 어느 목표도 아님)
```
→ coder14에게 전달: `--point-index 4`와 `--point-index 19`로 두 개를 빌드하고, index 0 덱은
폐기하거나 "미채택 후보"로 명시하라. 그대로 두면 제출 단계에서 어느 덱이 룰에 해당하는지
사람이 판단해야 한다.

---

## 2026-08-21 (18차 배치) — critic (critic14): coder14의 수정 4건 재검증 + plan.py 부수 변경

**대상**: `parse_irc_completion`의 error_termination 분기, `INPUT_DEFECT_SENTINELS` 추가 +
U56.sh의 `sei_terminal_from_logs` 전환, 진단 도구 4덱, `plan.py`의 product-cert 추가.
coder14가 명시적으로 물은 (a)(b)(c) 포함.

## 판정
**FIX-THEN-RUN** — 지적했던 2·3번은 실데이터로 고쳐진 것을 확인했다. 그러나 **부수적으로 들어간
`plan.py` 변경이 lead가 방금 무장해제한 336 core-h 자동 재제출을 다시 무장시킨다**(다른 문으로).
그리고 (a)의 구멍은 실재한다.

### 확인된 것 (직접 실행)

1. **[확인] `no_marker` 오단정 수정됨.** 실로그 재실행:
   ```
   U56_RA_scan forward/reverse  trunc=True  reason=error_termination (Error termination via Lnk1e ... l123.exe)
   U56_RB_scan forward          trunc=False reason=minimum_found
   ```
2. **[확인] deterministic 분류가 실로그에서 의도대로 나온다** (`status_from_g16_logs` 직접 호출):
   ```
   U56_RA_scan -> input_defect / deterministic / retry=False
   U56_RA_qst2 -> input_defect / deterministic / retry=False
   U56_RB_scan -> converged    / success       / retry=False
   ```
   🟢 내가 우려했던 "정상 종료한 RB가 stages_missing으로 engine_failure가 되는" 오분류는
   **일어나지 않는다** — 확인했다.
3. **[확인] coder14 질문 (b) — sentinel 문자열은 실로그와 바이트 일치.** G16의 실제 오타
   ("exceded")까지 그대로, RA 로그에 1회 존재.
4. 🟢 **[확인] 내가 우려한 "화학 verdict가 IRC from-logs로 덮인다"는 일어나지 않는다.**
   `saddle_outside_endpoint_bracket`(:899)와 `spectator_mode_not_the_coordinate`(:919)는
   `if/elif/elif [ -f ts.xyz ]` 사슬 안에 있어 발동하면 IRC 분기 자체에 들어가지 않는다 ⟹
   `IRC_TERMINAL_WRITTEN`이 설정되지 않고 하단의 STATUS 기록이 살아난다. 설계 정확.
5. **실행 기록**: 전체 `discover` **Ran 1661, failures=4**(기존 freeze 신호 4건 그대로),
   `test_session_digest` **63/63 OK**.

### 치명적 (비용)

6. 🔴 **[확인] `plan.py`의 product-cert 추가가 `U56_RA_scan`을 `stale`로 만들어 자동 재제출시킨다
   — lead의 `deterministic` 판정을 우회한다.**
   - `U56_RA_scan`의 `extra_env`에 `SEI_U56_PRODUCT_ENDPOINT_KEY`가 추가됐다(`plan.py:492`).
   - `extra_env`는 `state.SPEC_DIGEST_FIELDS`에 들어 있다 ⟹ spec_digest가 바뀐다(내가 앞서 실행으로
     확인: extra_env 키 하나 추가 → digest 54876cd4e8fb3086 → c32c78160f6d0b1d).
   - 반환된 `state/U56_RA_scan.submitted.json`의 `spec_digest = fe26e965728368c0`와 달라지므로
     `Store.done_spec_status`는 **`stale`** 을 돌려준다(`state.py:153` "same key set, digest
     differs -> a DIFFERENT computation").
   - `cli.py`에서 `if status == "stale": reset_item(archive_job_dir=True)` 는 **cause_class
     검사보다 먼저** 실행되고 cause_class를 아예 보지 않는다 ⟹ `deterministic`은 조회되지 않는다.
   → 이 입력이면 이렇게 된다: 다음 `./run.sh`에서 `U56_RA_scan`이 통째로 재제출된다 —
   **336 core-h**(stages 실측 합), 그리고 IRC는 같은 덱이므로 같은 지점에서 다시 죽는다.
   lead가 `engine` 대신 `deterministic`을 고른 이유(자동 재지출 차단)가 무효화된다.
   ⚠ 이 재제출이 **무가치하지는 않다** — product cert가 붙으면 bracket check가 양방향이 되어
   R-A bake-off의 판별력이 실제로 올라간다(그게 §39.113(d) housekeeping의 목적). 문제는
   **보이지 않는다는 것**이다: env 키 하나 추가가 예산 판정을 뒤집는 경로를 아는 사람만 안다.
   → lead 결정 사항으로 올린다. 값싼 정렬: 이 plan.py 변경을 IRC 덱 수정과 **같은 판에 실어라** —
   그러면 한 번의 재제출이 두 가지를 다 산다. (`U56_RA_qst2`는 이미 그 키를 갖고 있어 영향 없음,
   `U56_RB_scan`은 `converged/success`라 재제출 대상 아님.)

### 중대

7. 🔴 **[확인] coder14 질문 (a)에 대한 답 — 구멍은 실재한다.** `payload/U56.sh:1109-1110`:
   ```
   sei_terminal_from_logs ... -- ${RAN_IRC_LOGS}
   IRC_TERMINAL_WRITTEN=1        ← 성공 여부와 무관하게 설정된다
   ```
   `from-logs`는 실패 시 **rc=1로 죽고 파일을 쓰지 않는다** — 직접 재현:
   `cd /tmp && PYTHONPATH=/nonexistent python3 -m sei_pilot.outcome from-logs /tmp/c14y.json -- ...`
   → `rc=1`, 파일 미생성. U56.sh는 `set -u`만 걸려 있어(`set -e` 없음) 계속 진행하고,
   하단 fallback은 플래그 때문에 건너뛴다 ⟹ `terminal_status.json` 없음 ⟹ **`outcome: absent`**,
   즉 이번 fix가 없애려던 상태로 되돌아간다. 고침은 한 글자: `... && IRC_TERMINAL_WRITTEN=1`
   (또는 파일 존재 확인 후 설정).
8. ❌ **미수정 — `config/qc_levels.json`의 `stability_test`에 여전히 `nosymm`이 없다.**
   `"#p {functional}/{basis} {solvent} stable=opt Int(Grid=UltraFine)"`. 게다가 이번에 새로 만든
   `build_u56_ra_irc_recorrect_probe.py:91`의 라우트는 `nosymm`을 **넣는다** ⟹ 같은 진단 묶음
   안에서 두 덱의 관례가 갈렸다. 17차 배치 9번의 근거(대칭이 stability 분석 범위를 좁혀 거짓
   "stable"을 만들 수 있고, 그 방향이 §39.113(e) falsifiability가 기대는 방향) 그대로 유효.
9. ❌ **미수정 — U56.sh에 SIGTERM trap 없음**(`grep -n "trap " payload/U56.sh` → 0건).
   17차 배치 10번 그대로: 48 h cap kill = `terminal_status` 없음 = 3,072 core-h 무판정.

### 사소

10. **[확인] coder14 질문 (c) — recorrect 덱의 caveat 자체는 정직하다. 그러나 비교 대상이 틀렸다.**
    주석은 "stability_test의 라우트는 이번 라운드의 모든 실제 production 잡이 같은
    functional/basis/solvent fragment를 써서 **암묵적으로 smoke됐다**"고 쓰며 recorrect 덱과
    대비시킨다. fragment는 사실이지만 **`stable=opt` 키워드 자체는 한 번도 smoke된 적이 없다** —
    `sei_qc_smoke`는 `sp`와 `freq`(+legacy freq) job type만 돌린다(`qc_adapter.sh:366,406`),
    `stability_test`는 목록에 없다. 두 덱 다 "새 키워드 미검증"이 정확한 상태이고, 둘 다 실패해도
    비용이 ~0이므로 드라마도 아니다. 한쪽만 [NEEDS VERIFICATION]을 달면 다음 사람이 어느 덱을
    신뢰할지 잘못 고른다.
11. **[확인] 분류 경계(낮은 우선순위지만 기록).** `INPUT_DEFECT_SENTINELS`의 문서 문장은
    "G16 says what is wrong with the **deck**"인데 새로 넣은 "Maximum number of corrector steps
    exceded"는 덱 결함이 아니라 적분기 소진이다. 오늘 동작은 옳다(같은 덱 → 같은 crash).
    다만 목록의 정의가 넓어졌으므로 문장을 함께 넓히거나 목록 이름을 바꿔라 — §39.69가 세운
    "클래스는 처방으로 정의하고 경계를 결정 가능하게"를 유지하려면 다음 사람이 무엇을 넣어도
    되는지 판단할 기준이 있어야 한다.

---

## 2026-08-21 (19차 배치) — critic (critic14): nosymm / wall trap / branch(b) gate / fixture provenance 재검증

## 판정
**OK (조건부)** — 이번 배치에서 지적했던 항목은 **전부 실제로 고쳐졌고 실행으로 확인했다.**
남은 것은 lead 결정 대기 1건(18차 6번, plan.py stale 재제출)과 아래 사소 2건뿐이다.

### 내 기록 정정 (먼저)
🔴 **17차 배치 말미에 보낸 "네가 만든 덱은 `--point-index 0`이다"는 내가 읽은 시점 기준으로는
맞았고, 보낸 시점에는 이미 낡은 정보였다.** 내가 그 파일을 읽었을 때 `--point-index`는
`default=0`이었고 help 문구가 "0 = the first point after the TS, arc~0.34 A ... picked because
the nearby MO-coefficient warning there is ~34.9"라고 그 선택을 정당화하고 있었다(당시 인용
그대로). coder14가 그 사이에 도구를 다시 썼고, 나는 다시 읽지 않고 보냈다. 현재 파일은
`default=None` + `ap.error("--point-index is required with --irc-log")`로 **인자 필수**이며
docstring이 4/19를 명시한다 — 직접 확인. index-0 산출물은 존재하지 않는다. 지적을 철회한다.

### 확인된 것 (직접 실행/판독)

1. **[확인] `nosymm` 추가됨**: `"stability_test": "#p nosymm {functional}/{basis} {solvent}
   stable=opt Int(Grid=UltraFine)"`. `_nosymm_required_job_types`(C-9 perturbation 전용 목록)에
   넣지 않고 route에만 넣은 판단도 타당 — 그 목록의 테스트는 "C-9 섭동에 의존하는 라우트"라는
   다른 성질을 exact-match로 고정하고 있다.
2. **[확인] SIGTERM trap 추가됨**: `U56.sh:53`에 `trap '_write_terminal "wall_exhausted" ...;
   exit 9' TERM`, `sei_stage` 호출 6곳 전부에 `U56_CURRENT_STAGE=` 선행(6/6), `1145`에서 해제.
   `test_u56_wall_tripwire.py`는 정적 검사이지만 **비어 있지 않다** — 모든 `sei_stage` 호출이
   3줄 이내에 stage 대입을 갖는지 프로그램적으로 검사하므로 다음 stage 추가가 빠뜨리면 red.
   🟢 우려했던 점 하나 **직접 측정 후 기각**: trap이 python(`sei_terminal`)을 부르는 반면
   P5는 순수 shell heredoc이라 SIGTERM~SIGKILL 유예 안에 못 끝날 수 있다고 의심했으나, 실측
   10-20 ms(3회) — PBS 유예(초 단위) 대비 무의미하다. 지적하지 않는다.
3. **[확인] `IRC_TERMINAL_WRITTEN`의 `&&` 게이트 적용됨**(`U56.sh:1132-1133`), 그리고
   `test_u56_terminal_status.py`에 무조건 대입을 금지하는 정적 테스트가 추가됨.
4. **[확인] branch (b) 게이트 구현이 내가 지적한 두 함정을 정확히 피한다**: 강등이
   `irc_direction_ok` **안에서 consult 시점에** 계산되어 실제 분기 조건이 쓰는
   `bplus_agreement_effective`로 들어가고(`guards.py:226-236`), 원본 `bplus_*.json`은
   변형되지 않는다(전용 테스트로 고정). 임계값 `BPLUS_LOW_CONFIDENCE_MIN_POINTS = 10`은
   **`parse_irc_path_frames` 관례(saddle 제외)로 표기**되어 있고 off-by-one이 두 실제 사례의
   판정을 바꾸지 않는다는 근거까지 주석에 있다.
5. **[확인] fixture provenance 보강됨**: 신규 5개 전부 파일 내 헤더 + `PROVENANCE.md` 항목.
   헤더 삽입 후에도 **본문은 여전히 원본의 verbatim 부분문자열**임을 5/5 재확인(프로그램 검사).
6. **실행 기록**: 전체 `discover` **Ran 1671, failures=4**(기존 freeze 신호 4건 그대로),
   대상 스위트(`test_u56_wall_tripwire`, `test_irc_truncation_c2`, `test_guards`,
   `test_u56_ra_stability_probe`, `test_session_digest`) **172 OK**.

### coder14의 질문에 대한 답 — `unknown` 태그는 옳다. 다만 인접한 구멍이 하나 보인다

7. **`unknown`을 지지한다.** 이 경우는 "측정을 안 했다"가 아니라 "측정했으나 그 무게를 못
   견딘다"인데, `budget`(caps를 늘려라)이나 `chemical`(방법이 틀렸다) 어느 처방도 맞지 않고,
   룰 자신의 표현("not disqualifying, not yet load-bearing")과 가장 가깝다. 새 태그를 만들면
   §39.69가 세운 "클래스는 처방으로 정의한다"를 만족시킬 처방이 없다 — 만들지 마라.
8. 🟡 **[확인] 다만 이번 변경이 기존 구멍 하나를 더 잘 보이게 만든다: crash한 IRC는 guards에서
   `engine` 태그를 절대 받지 않는다.** `irc_direction_ok`의 첫 절이 `normal_termination is not
   True` → `tags.append("unknown")` 이므로, **엔진이 죽은 arm과 정말로 모르는 arm이 태그에서
   구분되지 않는다** — §39.69가 `engine` 클래스를 만든 목적("caps를 늘려도, 방법을 바꿔도
   소용없다, SCF/수치 설정을 바꿔라")이 U-56b 집계에서 한 번도 나타나지 않는다.
   지금은 고칠 수 있다: `parse_irc_completion`이 이미 `Error termination` 여부를 계산하지만
   **prose(`termination_reason`)로만** 내보낸다. 같은 파일의 주석이 "cause class를 prose
   substring 매칭으로 유도하지 말라"고 못박고 있으므로, `error_terminated: bool` 필드를 함께
   내보내고 guards가 그 필드로 `engine`을 태그하면 된다. 작고, 근거가 있고, 새 개념이 없다.

### 사소

9. **[확인] 재번호 이후 코드/산출물의 § 인용이 절반만 마이그레이션됐다.** 새 번호를 쓰는 파일
   (`guards.py` §39.114, `plan.py` §39.113, `test_irc_truncation_c2.py` §39.114)과 옛 번호가
   남은 파일이 섞여 있다:
   ```
   tools/build_u56_ra_stability_probe.py     §39.110 / §39.111 / §39.112  → 39.113 / 39.114 / 39.115
   tools/build_u56_ra_irc_recorrect_probe.py §39.111 (4곳)                → 39.114
   config/qc_levels.json                     §39.110                      → 39.113(e)
   payload/U56.sh                            §39.110 (housekeeping)       → 39.113(d)
   tests/fixtures/PROVENANCE.md              §39.112 (1곳)                → 39.115
   ```
   🔴 이건 dangling reference보다 나쁘다 — **옛 번호가 전부 실재하고 다른 내용을 가리킨다**
   (§39.110=li_ec2_cation 정정, §39.111=SCF/Hessian split, §39.112=Round A 인증). 예: qc_levels의
   `nosymm` 근거를 따라가면 species 이름 정정 문서에 도착해 "근거 없음"으로 읽힌다.
   선택 사항(범위 밖이라 강제하지 않음): src/ 안의 모든 `§39.x` 인용이 02_METHOD_SPEC.md의
   heading과 **정확히 하나** 매칭되는지 검사하는 작은 테스트 하나면 이 부류가 영구히 닫힌다.
10. `tests/fixtures/g16_endpoint_tight_rc_reactant.log`는 **718 KB 전체 로그**인데 그 용도는
   beta MO 계수 4줄이다. 다른 fixture처럼 슬라이스면 ~10 KB다. 또 헤더가 "FULL G16 LOG,
   VERBATIM"이라고 적혀 있으나 그 헤더 10줄 자체가 원본에 없다(본문은 verbatim 확인됨).

### 19차 배치 — 추가 (critic14): `extra_env` 보류 조치 독립 확인

**[확인] lead의 보고를 받지 않고 `plan.py:473-497` 직접 재판독**: `U56_RA_scan`의 `extra_env`는
3키(`SEI_U56_REACTION`/`SEI_U56_METHOD`/`SEI_U56_REACTANT_ENDPOINT_KEY`)로 원복됐고
`SEI_U56_PRODUCT_ENDPOINT_KEY`는 없다. `depends_on`도 `["endpoint_prep_reactant"]`로 원복.
보류 사유가 주석에 §39.113(d) 인용과 함께(재번호된 새 번호로) 기록돼 있고, "IRC 적분기 설정도
`extra_env`에 속하므로 같이 실어라"까지 적혀 있다 — 내가 권고한 option (ii) 그대로. `U56_RA_qst2`는
키 유지(정상, `test_u56_plan_items.py:192`가 고정). **재제출 위험은 현재 살아 있지 않다.**

⚠ **확인의 한계(명시)**: 제출 마커는 `physics_keys`의 **이름만** 남기고 값은 남기지 않으므로
`fe26e965728368c0`을 로컬에서 재계산할 수는 없다. 내가 확인한 것은 `SPEC_DIGEST_FIELDS`에
해당하는 필드가 전부 변경 전 내용으로 돌아왔다는 것이다(`extra_env` 원복, `depends_on`은 애초에
digest 필드가 아님). 이것이 오프클러스터에서 가능한 최강의 검사이고, 결론에는 충분하다.

🟡 **[확인] 다만 이 보류는 주석에만 산다 — 테스트가 없다.** `SEI_U56_PRODUCT_ENDPOINT_KEY`를
검사하는 테스트는 qst2에 **있어야 한다**는 것(`test_u56_plan_items.py:192`)과 payload의
동작(`test_u56_ra_scan_product_cert.py`)뿐이고, `U56_RA_scan`에 **없어야 한다**를 고정하는 것은
없다. 이 프로젝트는 같은 모양의 "의도된 부재"에 대해 이미 핀을 만든 선례가 있다 —
`test_p1_excluded_sizing.py`(실패 메시지가 위험을 직접 호명). 3줄이면 된다: 부재를 단언하고,
메시지에 "지금 넣으면 336 core-h 재제출이 즉시 발동하며, IRC 적분기 수정과 같은 판에 실을 때만
해제하라"를 적어라. 없으면 다음 사람이 §39.113(d)를 읽고 선의로 다시 넣는다 — 그게 이 보류가
막으려는 바로 그 행동이다.

**사소 [확인]**: `payload/U56.sh:18`의 헤더 주석이 아직 `SEI_U56_PRODUCT_ENDPOINT_KEY (qst2 만)`
이라고 적혀 있다. :181은 이미 `method == "qst2" or os.environ.get(...)` 로 **선언되면 method와
무관하게** 해석한다 — 같은 파일 안에서 산문이 동작보다 좁게 말한다.

**실행 기록**: `test_u56_plan_items` + `test_u56_ra_scan_product_cert` + `test_session_digest`
합쳐 **82 OK**.

---

## 2026-08-21 (20차 배치) — critic (critic14): `&&` 수정·smoke 대칭·sentinel 문서 재검증 + `engine` 태그 확인

## 판정
**OK** — 이번에 확인 요청된 항목 전부 실제로 반영됐다. 새 지적 1건(아래 5번)만 남는다.

### 확인된 것 (직접 실행/판독)
1. **[확인] `error_terminated` bool이 실제로 `engine` 태그를 만든다** — 내가 19차에서 제안한 것이
   그대로 구현됐고, 실데이터로 end-to-end 확인:
   ```
   U56_RA_scan forward  tags=['engine']   (이전에는 'unknown')
   U56_RB_scan forward  tags=['budget']   bplus_agreement_effective='low_confidence'
   ```
   prose substring 매칭이 아니라 `parse_irc_completion`의 새 boolean 필드에서 유도된다
   (`g16.py:447,458`, `guards.py:185`). §39.69의 `engine` 클래스가 처음으로 U-56b 집계에 나타난다.
2. **[확인] § 인용 스윕 완료** — `tools/`, `config/`, `payload/U56.sh`, `fixtures/PROVENANCE.md`
   어디에도 옛 번호(39.110/111/112)가 남아 있지 않다(grep 0건).
3. **[확인] smoke 검증 대칭 처리됨**: `build_u56_ra_stability_probe.py`의 docstring(:30)과
   manifest 출력(:219) 둘 다에 `[NEEDS VERIFICATION]`이 붙었고 — 즉 산출물 자체가 그 말을
   달고 나온다 — recorrect 도구의 주석(:20-22)은 "`stable=opt`도 마찬가지로 route-smoke된 적이
   없다, fragment만 sp/freq 경유로 검증됐다"로 다시 쓰였다. 내가 지적한 비대칭 해소.
4. **[확인] `INPUT_DEFECT_SENTINELS` 문서가 결정 가능한 경계로 넓혀졌다**(`outcome.py:68-76`):
   "deck 결함"이 아니라 "**같은 입력을 다시 돌리면 동일하게 실패한다**"가 이 튜플이 실제로
   강제하는 경계라고 명시하고, corrector 항목이 그 시험은 통과하되 "덱이 틀렸다"는 아니라고
   적었다. 다음 사람이 무엇을 넣어도 되는지 판단할 기준이 생겼다.
   (단, 그 "동일하게 실패한다"가 아직 한 번도 측정되지 않았다는 18차 배치의 [의심]은 그대로다.)
5. **실행 기록**: 전체 `discover` **Ran 1672, failures=4**(기존 freeze 신호), coder 보고
   1668/1672와 일치.

### 새 지적 (중대 — 방금 만든 선례로 한 줄이면 닫힌다)

6. 🔴 **[확인] `minimum_found`는 이제 올바로 파싱되지만 여전히 소비자가 없고, 그 결과
   `U56_RB_scan`은 `budget`으로 태그된다.** 위 1번의 실행 결과가 그것이다: RB는 G16 자신이
   `PES minimum detected ... / Reaction path calculation complete.`로 **완주를 선언한** 경로인데,
   `n_points=1 < IRC_MIN_POINTS=5` 절이 무조건 `budget`을 붙인다 — 처방이 "caps가 틀렸다, attempt당
   더 써라"가 되고, `1/p` 산정의 CHEMICAL 분모에서 빠진다(`guards.py:568-580`이 경고하는 바로 그
   오염). 289 s 만에 minimum에 도달한 계산에 대해 "예산이 모자랐다"고 기록하는 셈이다.
   → 이 입력이면 이렇게 틀린다: proposer10이 판정 중인 R-B 후보(Li 44% mode)가 U-56b에서
   budget-class로 집계되어, 방법론 문제를 구매 결정 문제로 읽게 만든다.
   → 고쳐라(방금 `error_terminated`로 만든 선례와 동형, 같은 함수, 한 줄):
   `completion.minimum_found`가 True면 짧은 경로는 budget 실패가 아니다. **통과/불통과 판정은
   proposer 몫**이지만 **태그는 budget이면 안 된다**. 최소한 `chemical`(안장점이 한 스텝 만에
   minimum으로 붕괴한다 = 표면에 대한 사실)이나 별도 표기가 맞다.

### 20차 배치 — 추가 (critic14): `engine` 태그 구현·인용 스윕 마무리 확인

**[확인] 새로 들어온 부분만 재검증** (앞선 항목은 20차 본문에서 이미 실행 확인):
1. `completion = d.get("completion") or {}` 가 함수 상단(:173)으로 올라가고 하단 중복이
   제거됐으며 `detail["completion"]`(:212)은 그대로 — 의미 변화 없음.
2. 신규 테스트 2개가 **실제로 판별한다**: `test_a_real_error_terminated_log_tags_engine`는 실
   fixture로 `error_terminated=True` + `engine` 태그를 확인하고 `unknown`이 아님을 단언한다.
   음성 대조군 `test_a_genuinely_unmeasured_case_still_tags_unknown`은 `engine`이 아님을 단언 —
   새 클래스가 `normal_termination is not True` 전체를 삼키지 않음을 고정한다. 좋은 규율.
3. fixture 헤더 수정 확인: `[FIXTURE -- FULL G16 LOG]` + provenance를 별도 문장으로.
4. 전체 스위트 **Ran 1674, failures=4**(기존 freeze 신호), `test_session_digest` **63/63**.
   coder 보고 1670/1674와 일치.

**🟡 사소 [확인] — 인용 스윕이 `tests/`를 빠뜨렸다.** `tools/`·`config/`·`payload/`·
`fixtures/PROVENANCE.md`는 깨끗하지만 테스트 파일에 옛 번호가 남아 있다:
```
test_u56_ra_stability_probe.py:3,64,75,85   §39.111(2)/§39.112  → 39.114(2)/39.115
test_u56_ra_scan_product_cert.py:1          §39.110(d)          → 39.113(d)
test_u56_ra_irc_recorrect_probe.py:2        §39.110(e)/39.111(2)→ 39.113(e)/39.114(2)
```
앞서 적은 이유 그대로 — 옛 번호가 전부 실재하고 다른 내용을 가리키므로 dangling보다 나쁘다.

**🟡 사소 [확인] — 음성 대조군 테스트에 confound가 하나 있다.**
`test_a_genuinely_unmeasured_case_still_tags_unknown`은 `energy_hartree=None`을 넘기는데,
그러면 "endpoint or TS energy missing" 절이 **따로** `unknown`을 붙인다 ⟹ 첫 절이 무엇을 붙이든
`assertIn("unknown")`은 통과한다. 바로 위 형제 테스트는 이 confound를 피하려고 일부러 에너지를
넣어두고 주석까지 달아 놨다(같은 파일, 6줄 위). 부하를 지는 절반(`assertNotIn("engine")`)은
유효하므로 위험하지는 않으나, 같은 파일 안에서 규율이 갈렸다 — 에너지 하나 넣으면 끝난다.

**🟢 판단 기록 — 두 건은 coder14의 결정을 지지한다(지적 아님)**:
(a) "src/의 모든 §39.x가 heading과 1:1 매칭되는지" 검사 테스트를 만들지 않고 **건너뛰었다고
명시한 것**은 옳다. 내가 선택 사항으로 제안했고, 요청 범위 밖이었고, 무엇보다 조용히 넘기지
않고 알렸다. 이 부류가 **세 번째로** 재발하면 그때 만들어라.
(b) rc_reactant fixture를 718 KB 전체로 둔 판단도 근거가 구체적이다 — warning 두 곳(~897,
~9416)과 EOF 근처의 마지막 orientation 블록(`last_geometry()`가 읽는다)이 떨어져 있어 세 구간을
정확히 잘라내는 쪽이 위험이 크다. 저장공간 문제 아님. 이 항목 닫는다.

**여전히 열림(재촉 아님, 기록용)**: 20차 6번(`minimum_found`가 소비되지 않아 `U56_RB_scan`이
`budget` 태그) — 클래스 선택은 proposer10에게 넘겨 둔 상태. `U56_RA_scan`의 키 부재 고정 테스트,
`payload/U56.sh:18`의 `(qst2 만)` 주석.

---

## 2026-08-21 (21차 배치) — critic (critic14): proposer10의 §39.116 기하 주장 독립 검증 + 태그 권고

### 1. [확인] §39.116의 결론은 옳다 — 회전 불변 지표로 재확인

proposer10의 주장(RB의 "minimum"은 saddle과 사실상 같은 기하)을 **다른 지표로** 재계산했다.
`Input orientation` 블록만 사용(같은 좌표계), 병진 제거 + 회전 불변량(전체 원자쌍 거리):
```
forward  translation-removed RMSD 0.0112 A | 원자쌍 거리 변화 max 0.0203 A, mean 0.0018 A
reverse  translation-removed RMSD 0.0163 A | 원자쌍 거리 변화 max 0.0228 A, mean 0.0027 A
break O_ether-C_carbonyl: 4.1348 -> 4.1339 (fwd) / 4.1365 (rev)
```
⟹ **결론 지지**: 경로는 어느 방향으로도 화학적으로 유의한 거리를 가지 않았다.

🟡 **정밀도 정정 1건**: proposer10은 "다른 모든 원자도 비슷하게 작게(≈0.0009 A) 움직인다"고
적었으나 실제 최대 원자쌍 거리 변화는 **0.0203 A** — break 결합 변화의 20배다. 화학적으로는
여전히 무시할 수준이라 **결론은 바뀌지 않지만**, 기록에는 실제 숫자가 남아야 한다.

🔒 **내가 빠질 뻔한 함정, 다음 사람을 위해 기록**: `ts.xyz`(payload 추출)와 IRC 로그의
`Input orientation`을 직접 비교하면 최대 변위 **0.7056 A**, 평균 0.6825 A가 나온다 — 전부
**순수 병진**(좌표계 원점 차이)이다. 같은 로그의 두 orientation 블록끼리 비교하거나 회전
불변량을 쓰지 않으면, 아무 일도 일어나지 않은 경로가 0.7 A 움직인 것처럼 보인다.

### 2. 태그 권고 (proposer10이 나/coder14에게 넘긴 plumbing 결정): **`protocol`**

새 클래스를 만들지 마라. 기존 `protocol`이 정확히 맞는다:
- **처방이 일치한다.** §39.68(3)의 `protocol` 정의는 "이 실행은 **우리 절차**에 대해 말한다,
  화학이나 caps가 아니라"이고 처방은 "절차를 고치고 다시 돌려라". proposer10의 진단(IRC 자체의
  정지 기준이 평탄한 좌표에서 조기 발동)과 Track B item 7의 후속 질문(이 시스템 부류에서 IRC
  정지 기준을 조여야 하는가)이 바로 그것이다.
- **선례가 같은 모양이다.** `protocol`은 §39.68(3)에서 "게이트가 반응이 아니라 **자기 자신에
  대해** 보고할 때"를 위해 만들어졌다(frame-0 미수렴). 이건 한 단계 뒤의 같은 형태다.
- **proposer10의 배제 요구를 그대로 만족한다** — CHEMICAL도 BUDGET도 아니고 두 분모 어디에도
  들어가지 않는다.
- **retry 부작용 없음 [확인]**: guards의 `cause_tags`는 `_class_from_tags`(:692)를 거쳐 C-2
  판정문에만 들어간다. 재제출을 결정하는 것은 `outcome.py`의 terminal_status 계급이며 별개다.
  (`unknown`도 분모에서 빼주지만 처방이 없어, 조치 가능한 계통적 결함을 "안 쟀다"와 섞는다.)

🔴 **구현 주의 [확인]**: `_class_from_tags`는 **서로 다른 태그가 2개면 `mixed`** 를 돌려준다
(:695-698). 따라서 `minimum_found`가 true일 때는 `n_points < IRC_MIN_POINTS` 절이 `budget`을
**붙이지 않아야** 한다 — `budget` 위에 `protocol`을 더하면 결과는 `mixed`가 되어 아무것도
말하지 않는다.

### 3. 🔴 NEW — Track B item 6에 대한 **세 번째** 독립 문제, 이미 디스크에 있는 데이터에서

`bracket_check.json`(R-B) 직접 판독:
```
break:O_ether-C_carbonyl   reactant 1.4317 A -> saddle 4.1348 A   (+2.703 A)  one_sided_ok=true
mechanism:Li-O_ether       reactant 3.1133 A -> saddle 1.7880 A   (-1.325 A)  one_sided_ok=true
product_side: awaiting_calibration (R-B의 product 는 검증 대상이므로 인증서 없음, 설계대로)
```
⟹ **R-B의 "전이상태"에서 끊어야 할 결합은 이미 끊어져 있다** — 반응물보다 2.70 A 더 벌어져
있고(1.43 A는 결합, 4.13 A는 결합이 아니다), Li는 이미 ether 산소로 옮겨가 있다. 여기에
proposer10이 든 두 문제(허수모드의 44%가 Li, 그리고 §39.116의 평탄-경로)를 더하면 세 가지다.
🔒 **게이트는 정상 동작했다, 잡지 못한 것이 설계된 한계다**: 방향 인식 한쪽 bracket check는
break 좌표에 대해 "반응물보다 **짧으면**" 거부한다. 여기서는 **길다** ⟹ 구조적으로 못 잡는다.
`bracket_check.json`의 `reasons`가 이미 그 문장을 담고 있다("does not catch a saddle that
overshoots the product and must not be read as though it did (§39.65)"). ADR-112가 P1을 잡은 것은
**form 좌표**의 overshoot였기 때문이고(반응물 기준으로 잡히는 쪽), R-B는 같은 병리가 **못 잡는
쪽**에 있다. §39.65/§39.66이 예고한 커버리지 공백의 첫 실제 사례다.

### 21차 배치 — 추가 (critic14): RB 태그가 `chemical`로 들어갔다 — §39.116 룰과 어긋난다

**[확인, 직접 실행]** `guards.py:201`이 `tags.append("chemical" if completion.get("minimum_found")
else "budget")`으로 들어갔고, 실 로그로 확인한 결과:
```
U56_RB_scan forward  tags=['chemical']  ok=False  _class_from_tags -> 'chemical'
```
🔴 **이것은 proposer10의 §39.116 룰과 정면으로 어긋난다.** 그 룰의 문장: *"neither budget nor
plain CHEMICAL ... don't count this arm as CHEMICAL/connection-established evidence, and don't
count it as budget either — excluding it from both sides of the 1/p denominator."*
근거도 기하다(내가 회전 불변 지표로 재확인): "minimum"은 saddle과 0.02 Å 이내로 같다 ⟹ 표면에
대해 아무것도 확정되지 않았고, G16의 정지 기준이 평탄한 좌표에서 조기 발동한 것이다. `chemical`
태그는 "화학에 대한 사실을 쟀다"고 주장하는데, 재지 않았다.

→ 이 입력이면 이렇게 틀린다: `1/p`는 **CHEMICAL 분모에서만** 계산해야 한다(`guards.py:568-580`이
못박은 규칙). 알고리즘 artifact인 arm이 그 분모에 들어가면 p가 낮아지고 → `1/p`(wave-1 sizing
배수)가 부풀고 → S3가 실제보다 비싸게 읽히고 → 그 자연스러운 대응(caps 조이기)이 상황을 악화시킨다.
그 주석이 묘사하는 바로 그 루프에, 반대편 문에서 들어간다. **현재 코드가 `p`를 계산하지는 않지만**
(grep 확인), 회신 아티팩트에 CHEMICAL로 실려 나가고 나중에 engineer가 wave-1 sizing에서 그것을 읽는다.

🔒 **내 책임 몫**: 이 값은 내 **첫** 메시지의 제안("chemical이 정직한 읽기")에서 왔다. proposer10의
기하 판독 이후 나는 `protocol`로 정정해 보냈으나 메시지가 엇갈렸다. 잘못은 coder14가 아니라
내 초안에 있다 — 기록해 둔다.

→ 고쳐라(한 단어): `"chemical"` → `"protocol"`. 단일 태그이므로 `_class_from_tags`의 `mixed`
위험은 없다(이미 `budget`을 붙이지 않는 분기라 그 부분은 정확히 구현됐다). 근거는 21차 본문 2번
그대로. **함께 고칠 것**: 새로 추가된 테스트가 "chemical, not budget"을 고정하고 있으므로 폐기된
룰을 핀으로 박아 둔 상태다 — 태그와 같이 갱신해야 한다. 음성 대조군(minimum 없는 짧은 경로는
여전히 budget)은 그대로 유효하다.

### 21차 배치 — 마무리 (critic14): 룰은 문서에 반영됨, 코드는 아직

**[확인] 문서 쪽 완료**: `02_METHOD_SPEC.md:20502 §39.116`(d 절에 `protocol` 채택, 정밀도 정정
0.0203/0.0228 Å, ts.xyz-vs-로그 프레임 병진 함정, `_class_from_tags` 순서 요건이 build note로
기록), `:20604 §39.117`(R-B의 break 좌표 overshoot, ADR-112 비대칭 프레이밍). 본문 직접 열람 확인 —
proposer10의 보고와 일치하며 내가 넘긴 네 항목이 모두 실제로 들어가 있다.

**[확인] 코드 쪽 미반영**: `guards.py:201`은 여전히
`tags.append("chemical" if completion.get("minimum_found") else "budget")` 이고, 실 로그 재실행
결과 `U56_RB_scan forward tags=['chemical'] class='chemical'`. 결함이 새로 생긴 것은 아니고
coder14가 아직 처리하지 않은 상태다(메시지 엇갈림). **문서와 코드가 갈라져 있는 동안에는
회신 아티팩트의 `cause_class`를 wave-1 sizing에 쓰면 안 된다** — §39.116(c)가 배제하라고 한 arm이
CHEMICAL 분모에 들어 있다.

---

## 2026-08-21 (22차 배치) — critic (critic14): tests/ 스윕·confound·신규 인용 테스트 검증

## 판정
**FIX-THEN-RUN** — 이번에 보고된 3건은 확인됐다. 그러나 **`protocol` 태그 수정은 여전히
반영되지 않았고, coder14는 반영됐다고 믿고 있다**(폐기된 `chemical` 수정과 혼동).

### 🔴 치명적 — 룰이 코드에 없다, 그리고 있다고 보고됐다
**[확인, 직접 실행]** coder14의 이번 메시지는 "RB minimum_found->chemical fix ... already landed
and reported"라고 적었는데, `chemical`은 §39.116(d)가 **기각한** 값이다. 현재 소스:
```
guards.py:201  tags.append("chemical" if completion.get("minimum_found") else "budget")
실행:          U56_RB_scan forward  tags=['chemical']  class='chemical'
```
§39.116(d)의 채택값은 `protocol`이다(문서 직접 확인, 21차 마무리 참조). 즉 **문서는 룰을 담고
있고 코드는 기각된 값을 담고 있으며, 담당자는 반영됐다고 인지하고 있다** — 세 축이 어긋난
상태다. 이 상태로 회신 아티팩트를 읽으면 §39.116(c)가 배제하라고 한 arm이 CHEMICAL 분모에
들어가고, `1/p`(wave-1 sizing 배수)가 부풀어 S3가 실제보다 비싸게 읽힌다.
→ 한 단어(`"chemical"` → `"protocol"`) + 그 값을 고정하는 테스트를 `assertIn`이 아니라
**정확히 `protocol`**(=`mixed` 아님)로. 음성 대조군(minimum 없는 짧은 경로 → `budget`)은 유효.

### 확인된 것
1. **[확인] `tests/` 인용 스윕 완료** — 3개 파일 정리됨. 남은 `39.11[012]` 언급은
   `test_method_spec_citations.py`의 docstring뿐이고, 그건 사건을 **서술**하는 문장이라 정상.
2. **[확인] confound 수정 정확** — `test_a_genuinely_unmeasured_case_still_tags_unknown`이
   실제 `energy_hartree`를 넘기고 이유를 주석에 적었다. 이제 `assertIn("unknown")`이 첫 절에
   대해 부하를 진다.
3. **[확인] 신규 `test_method_spec_citations.py`는 자기 범위를 스스로 검사한다** — 인용을
   50개 이상 실제로 찾는지, `§R39.x`(03_COMPUTE_PLAN.md의 다른 계열)를 오인하지 않는지,
   `"Ca": 39.96259098` 같은 수치 리터럴을 오인하지 않는지까지 고정. `test_guard_reach.py`의
   heredoc 정규식 사고("가드가 자기 범위를 못 덮는다") 이후 이 프로젝트가 배운 형태 그대로다.

### 🟡 그 테스트의 한계 — coder14가 스스로 명시했고, 보완이 값싸다
존재 검사만 하므로 **이 정리 작업을 촉발한 바로 그 결함(옛 번호가 실재하는 다른 섹션을
가리키는 오배정)은 잡지 못한다**. coder14가 docstring에 그 한계를 적어 둔 것은 옳다 — green을
"이 부류가 닫혔다"로 오독하지 않게 한다.
→ 보완 제안(결정 가능하고 3줄): **02_METHOD_SPEC.md의 `§39.x` heading 번호가 유일한지** 검사.
그것이 오늘 사건의 절반(같은 번호 3개가 두 번씩 존재)을 직접 잡는다. **오늘 green으로 시작한다**
— 직접 확인: heading 118개, 진짜 중복 0건(유일한 겉보기 중복 `39.2` vs `39.2b`는 접미사
때문이며 서로 다른 절이다). 존재+유일성 두 절이 짝이다.

---

## 2026-08-21 (23차 배치) — critic (critic14): `protocol` 태그 반영 확인 + 라운드 마감

## 판정
**OK** — 이번 라운드에서 내가 제기한 항목은 **전부 닫혔다.** 남은 것은 아래 "제출 전 필수" 1건뿐이고
그건 결함이 아니라 lead의 리빌드 결정 사항이다.

### 확인된 것 (직접 실행)
1. **[확인] `protocol` 반영됨.** `guards.py:201`이 `"protocol" if completion.get("minimum_found")
   else "budget"`. 실 로그로 단일 방향과 **공개 경로** 둘 다 실행:
   ```
   irc_direction_ok(forward)  tags=['protocol']
   irc_verdict(fwd, rev)      cause_class='protocol'   may_render_chemical_verdict=False
   ```
   `_class_from_tags`의 `mixed` 위험이 실데이터에서 실현되지 않음을 **추론이 아니라 실행으로**
   확인했다(coder14도 같은 방식으로 확인했다고 보고했고, 독립 재현됨).
2. **[확인] `IRC_MIN_POINTS` 주석(:42-47)이 예외를 상수 옆에 적었다** — "5점 미만 = 예산 부족"을
   다음 사람이 무조건 규칙으로 재유도하지 않게 막는다. 상수 자체는 truncated 경우에 대해 그대로.
3. **[확인] 인용 테스트의 유일성 절이 추가됐다**(`test_method_spec_citations.py:106`), 내가 지정한
   접미사 처리(`39.2` vs `39.2b`)와 "heading을 실제로 100개 이상 찾는가" 자기검사까지 포함.
   존재+유일성 두 절이 짝을 이뤄 이 부류가 닫혔다.
4. **[확인] 22차에서 제기한 나머지 3건은 이미 확인·종결 상태**(tests/ 스윕, confound, extra_env
   핀 + U56.sh 주석) — 22차 본문에 "확인된 것"으로 기록돼 있다. coder14와 이견 없음, 메시지
   엇갈림뿐이었다.
5. **실행 기록**: 전체 `discover` **Ran 1682, failures=4**(기존 freeze 신호 4건), 대상 스위트
   (`test_session_digest`, `test_irc_truncation_c2`, `test_guards`, `test_method_spec_citations`)
   **173 OK**.

### 🔴 제출 전 필수 (결함 아님, lead 결정) — 이번 세션 작업물은 **어느 패키지에도 실려 있지 않다**
`test_build_stamp`가 소스와 `dist/` 타르볼(`8ae3630c2e100307`)의 차이로 붙잡고 있는 파일이 **11개**다:
```
README_USER.cpu.md, config/qc_levels.json, payload/U56.sh,
sei_pilot/{budget,cli,criteria/g16,guards,outcome,plan}.py,
tools/build_u56_ra_{irc_recorrect,stability}_probe.py
```
즉 `terminal_status` fix, `error_terminated`/`engine` 태그, §39.116(d)의 `protocol` 태그,
§39.114(1)의 B+ 분리 게이트, `nosymm`, SIGTERM trap, 인용 스윕 — **오늘 확정된 것 전부**가
패키지 밖에 있다. 05_STATE 첫머리의 ADR-114 경고와 정확히 같은 모양이다.
⟹ 다음 제출 전에 **리빌드 → 전체 스위트 → critic 재확인** 순서를 밟아야 하고, 리빌드 후에는
`test_build_stamp`/`test_readme_matches_code` 4건이 green으로 돌아와야 정상이다(지금 red인 것은
freeze 신호이지 회귀가 아니다).

### 23차 배치 — 추가 (critic14): 동기화 문제 감사 — 3건 중 내 오류는 1건

coder14가 "이번 세션에 세 번, critic 쪽 확인이 파일 실제 내용과 어긋났다"고 제기했다. 내 신뢰도에
대한 지적이므로 내 로그에 감사 결과를 남긴다. **fresh read로 현재 상태부터 확정**(coder14의 값과
바이트 단위로 일치):
```
mtime 2026-08-21 20:12:09  sha256 469e189a9c8ea803218915eeb54e2ebaeaad4268d9b7bceed482718419559acc
guards.py:214  tags.append("protocol" if completion.get("minimum_found") else "budget")
실행: tags=['protocol']  irc_verdict cause_class='protocol'
```
현재 상태에 대해 **이견 없음** — 그리고 이 값은 내가 **직전 메시지에서 이미 보고한 것**이다
(23차 본문 1번, 판정 OK).

**3건 감사:**
1. `--point-index 0` — **내 오류가 맞다.** 읽은 시점에는 `default=0`이었으나 보내기 전에 다시 읽지
   않았다. 이미 철회·기록(19차).
2. `nosymm`/SIGTERM trap — **내 오류가 아니다.** 18차 보고 시점에 실제로 없었고 coder14 본인이
   "100% correctly caught the first time"이라고 확인했다. 반복으로 보인 것은, 내 19차 확인
   메시지가 전달 중일 때 coder14가 18차에 답했기 때문이다.
3. `chemical`/`protocol` — **내 오류가 아니다.** 당시 `guards.py:201`은 문자 그대로
   `tags.append("chemical" if ...)` 였고 나는 그 줄을 인용했다. 그리고 **바로 다음 메시지에서**
   `protocol` 반영을 확인하고 라운드를 OK로 닫았다 — 이 지적이 도착하기 전에.
⟹ 3건 중 1건이 내 오류다. 나머지 둘은 **양쪽이 같은 파일을 분 단위로 주고받는 동안의 메시지
엇갈림**이며, 구조적 원인은 "coder가 내 읽기와 내 메시지 사이에 고친다"는 것이다.

🟢 **값싼 프로토콜 개선(이번 교환이 그 시연이다)**: 상태 주장에 **콘텐츠 주소**를 붙인다 —
"landed" 보고에는 `sha256sum <file>`(또는 mtime)을, "not landed" 보고에도 같은 것을. 그러면
불일치가 왕복 없이 sha 비교로 즉시 판별된다. coder14가 이번에 그렇게 했고, 그래서 이 건은
한 번에 끝났다. 앞으로 양방향으로 적용한다.

**[확인] `TestEveryHeadingNumberIsUnique`(:98) 실재하고 통과** — `test_method_spec_citations`
**7 tests OK**(존재 4 + 유일성 3, 후자에 `39.2`/`39.2b` 구분과 "heading을 실제로 찾는가" 자기검사
포함). 존재+유일성 짝 완성 확인.

---

## 2026-08-21 (24차 배치) — critic (critic14): 리빌드 독립 검증

**방법 선택**: `make_package.sh`를 다시 돌리지 **않았다**. 재빌드는 검증이 아니라 새 산출물을
만드는 행위이고(coder14의 산출물을 덮어쓴다), 확인해야 할 대상은 **실제로 나갈 바이트**다.
그래서 이미 만들어진 `dist/`를 대상으로 검증했다 — 더 강한 검사다.

### 확인된 것 (전부 직접 실행)
1. **`build_stamp.py check` → `✅ tarball 이 현재 소스와 일치한다`**, `BUILD_STAMP.json`의
   `source_digest 0fcb8c2bcb8f7bde`, `n_files 108`, `built_at_utc 2026-08-21T11:22:48Z`.
2. **tarball 체크섬이 사이드카와 일치**: `sha256sum -c sei_pilot_cpu.tar.gz.sha256` → `OK`,
   값 `4fb52b3af4f403a413df73de302dbe58e5cf853d735c4beea66f9bba72cf60a6` (coder14 보고와 일치).
3. **패키지 안의 바이트를 직접 비교** (tarball을 풀어 소스와 sha256 대조):
   ```
   payload/U56.sh            4c7bcbe3379e9cad  MATCH
   sei_pilot/guards.py       469e189a9c8ea803  MATCH   ← 내가 앞서 확인한 protocol 판본
   config/qc_levels.json     1f7ac36ac352a3a4  MATCH
   sei_pilot/outcome.py      aa8517fa2ee697a3  MATCH
   sei_pilot/criteria/g16.py e90e8373a96026fd  MATCH
   sei_pilot/plan.py         cfb17f091c85d382  MATCH
   ```
   그리고 **풀어낸 파일에서 직접 grep**: `guards.py:214`가 `"protocol" if ...`, `U56.sh`에
   SIGTERM trap 1건과 `&& IRC_TERMINAL_WRITTEN=1` 1건, `qc_levels.json`의 `stability_test`에
   `nosymm` 존재. 설명이 아니라 **나갈 바이트**에서 확인했다.
4. **package_fingerprint `a7b668127d052e33`를 독립 재계산 — 두 경로 모두 일치**:
   풀어낸 tarball에서 `version.package_fingerprint('.')`, 소스 트리에서
   `package_fingerprint('.', ['sei_pilot_work'])` — 둘 다 `a7b668127d052e33`.
   즉 계산 노드가 찍을 지문과 소스가 같다.
5. **전체 스위트 `Ran 1685, OK (skipped=14), 실패 0`** — 이전 4건(`test_build_stamp` ×2,
   `test_readme_matches_code` ×2)이 **사라졌다**. 내가 "리빌드 후 green으로 돌아와야 정상"이라고
   적어 둔 신호가 그대로 나왔다. `test_session_digest` **63/63**.
6. **패키지 오염 없음**: `sei_pilot_work/`, `dist/`, 중첩 tarball 어느 것도 들어 있지 않다.
   20 MB의 대부분은 `vendor/`(풀면 61 MB, xtb) — 정상.

### 🟢 지문 변경의 비용 영향 — 확인 결과 **놀랄 일 없음**
`8ae3630c2e100307` → `a7b668127d052e33`. `cli.py:628`은 plumbing 계급(`protocol|engine|unknown`)
done 마커를 **빌드가 바뀌면 자동 재제출**한다. 반환 트리의 done 마커 **39개 전수 조사**:
```
자동 재제출 대상: 0건   (absent 36, success 3 — 둘 다 재시도 대상 아님)
```
⟹ 리빌드가 유발하는 자동 재지출은 **없다**.
`failed` 마커 4건(`P1`, `P1_c1`, `P1_c2`, `probe_qw_capped`)은 재시도 분기로 간다(`cause=absent`는
skip 목록 `chemical|budget|deterministic`에 없다). 비용은 유계다 — P1은 64 core-h/1h로 축소된
항목이고 C-8이 구조적으로 거부한다(실측 0.658 core-h), 나머지도 같은 형태이거나 probe다.
**총 ~2-3 core-h 수준, 의도된 동작**(실패 항목은 재시도 대상).

🟡 **사소 [확인] — `absent`가 두 분기에서 반대로 취급된다.** `done` 분기에서 `absent`는 "판정이
없으므로 절대 재시도하지 않는다"(outcome.py 주석)인데, `failed` 분기(`cli.py:685`)에서는 skip
목록에 없어 **재시도로 떨어진다**. 두 동작 다 방어 가능하지만, `failed` 분기의 주석은 "Same
taxonomy, same rule"이라고 적혀 있어 사실과 다르다. 영향 범위가 작아(위 4건) 차단 사유는
아니지만, 산문이 동작보다 넓게 말하는 이 프로젝트의 반복 형태다.

## 판정
**OK — 리빌드는 무결하다.** 이번 세션에 확정된 모든 룰이 실제로 패키지 안에 들어 있음을 바이트
수준으로 확인했다. 제출을 막을 이유 없음.

### 24차 배치 — 추가 (critic14): `absent` 비대칭 주석 수정 검증 — 리빌드 **불필요**

**[확인, 직접 diff]** 패키지 안의 `cli.py`와 현재 소스를 비교한 결과 **차이는 주석 1개뿐**이다
(1줄 → 11줄, 실행문 변경 0):
```
diff /tmp/c14pkg/sei_pilot_cpu/sei_pilot/cli.py  src/pilot_package/sei_pilot/cli.py
682c682,692   (주석만: "Same taxonomy, same rule" 문장을 `absent`가 두 분기에서 반대로
               취급된다는 설명으로 교체 + "고치지 말고 done 분기를 먼저 보라"는 경고)
```
내용도 정확하다 — 내가 지적한 그대로이고, "이 비대칭을 `absent`를 튜플에 추가해서 '고치지'
말라"는 문장까지 들어가 있어 다음 사람이 동작을 바꾸는 것을 막는다. lead의 판정(동작이 아니라
주석을 고친다)과도 일치한다.

**[확인] freeze 신호는 2건으로 정확히 좁혀졌다**: 전체 스위트 `Ran 1685, failures=2`
(`test_build_stamp` ×2만; `test_readme_matches_code` 2건은 README가 안 바뀌어 green 유지).
드리프트 파일 목록도 `sei_pilot/cli.py` **한 개**뿐이다.

🟢 **판단: 이 주석 하나 때문에 리빌드하지 마라.** 출하 아티팩트
(`a7b668127d052e33` / `4fb52b3a…60a6`)와 소스의 유일한 차이가 실행되지 않는 주석임을 diff로
확인했다 ⟹ **패키지의 과학적 내용은 여전히 유효**하고, 24차 본문의 검증 결과가 그대로 선다.
리빌드는 다음 실제 코드 변경과 함께 묶는 것이 맞다(리빌드 자체가 fingerprint를 또 바꾸고,
그때마다 재제출 판정을 다시 확인해야 한다 — 24차 본문의 39개 마커 전수조사를 반복해야 한다는
뜻이다). 지금 상태에서 제출해도 잃는 것은 없다.

---

## 2026-08-22 (25차 배치) — critic (critic15, successor to critic14): ADR-115 / ADR-116 / ADR-117 independent verification before the user spends ~50 core-h

**Scope**: `01_DECISION_LOG.md` ADR-115/116/117 (appended today); `05_STATE.md` §1e (+ §1d/§2 for
context); `02_METHOD_SPEC.md` §39.118-123; `03_COMPUTE_PLAN.md` §R39.78/§R39.79; the raw returned tree
`cpu_machine_pilot_results/u56_diagnostics_2026-08-21/` and the source job trees under
`cpu_machine_pilot_results/sei_pilot_work/jobs/`. **Nothing under `cpu_machine_pilot_results/` was
written, moved or deleted — read-only, per the standing restriction.** No `src/` file was modified.
Abbreviations on first use: `ADR-NNN` = architecture decision record; `IRC` = intrinsic reaction
coordinate; `TS` = transition state; `PCM` = polarisable continuum model; `SCF` = self-consistent
field; `MO` = molecular orbital; `C-2` = the coder constraint governing IRC verdicts; `C-8` = the
endpoint-certification constraint; `U-56a` = the binary feasibility gate that blocks S3 production;
`B+` = the terminal-optimisation comparator of §39.55; `bf` = basis functions.

### 판정

**BLOCK** on ADR-116's U-56a note (a stage gate is declared passed on the wrong instrument).
**FIX-THEN-RUN** on ADR-117's resubmit recipe (3 concrete fixes; the compute itself is otherwise sound).
ADR-115's ruling stands, but one of its stated justifications is factually wrong.

### C1 — Re-derivation of every load-bearing number: **OK, all reproduce**

| figure | ADR/§ claim | measured, this review | file:line |
|---|---|---|---|
| stage 1 lowest instability eigenvalue | +0.1419360 | `Eigenvector 1: 2.051-?Sym Eigenvalue= 0.1419360` | `1_point4_arc1.71/stability_probe.log:1022` |
| stage 2 lowest instability eigenvalue | +0.1842609 | `Eigenvalue= 0.1842609` | `2_point19_arc6.83/stability_probe.log:1029` |
| both "stable" verdicts | stable / already stable | `The wavefunction is stable under the perturbations considered.` + `The wavefunction is already stable.` | `…1_…log:1030,1033` / `…2_…log:1034,1037` |
| `<S**2>` | 0.7549 / 0.7546 | 0.7549 / 0.7546, both annihilating to 0.7500 | `…1_…log:632,636` / `…2_…log:600,604` |
| `EigRej` | −1.00D+00 at all three | −1.00D+00 at 173 bf (×2) and at 334 bf | `…1_…log:341`, `…2_…log:341`, `3_…/stability_probe.log:397` |
| `EigKep` | 4.2-4.5e-5 → 1.06e-5 | 4.52D-05, 4.17D-05, 1.06D-05 | same lines |
| CPU times | 30m49.0s / 43m41.3s | identical; = 0.5136 + 0.7281 = **1.2417 core-h** | `…1_…log:1326`, `…2_…log:1331` |
| stage-3 kill point | Cycle 8, DIIS 1.19D-04 | `DIIS: error= 1.19D-04 at cycle 7`, then `Cycle 8 Pass 1` and the log ends | `3_…/stability_probe.log:544-546` + tail |
| wall kill | 7244 / 7200 | `=>> PBS: job killed: walltime 7244 exceeded limit 7200` | `sei_u56_diagnostics.e23731675:1` |
| stage 4 never started | yes | `.o` file ends after `=== 3_rc_reactant_21atom ===` | `sei_u56_diagnostics.o23731675` |
| MO coefficients | 33.38 / 38.87 (beta) | 33.376628 / 38.873404 | `…1_…log:919`, `…2_…log:887` |
| stage-4 `.chk` uncorrupted | copied at deck-build time | **byte-identical**, md5 `87a378633c55f4df0021f133943cfe97`, 10,342,400 B, to `U56_RA_scan/irc_forward.chk` | verified by `md5sum` |

**두 개는 내가 새로 재도출했다** (아무도 확인하지 않은 것):
- 20 corrector sub-iterations after point 20: exactly **20** `Delta-x Convergence NOT Met`, **20**
  `SCF Done`, **0** `Convergence failure`. Gradient angles 31.3866° … 59.3851°.
- The failing point-21 segment cost **15:40:03 → 15:52:37 = 754 s wall × 64 cores ≈ 13.4 core-h
  charged (~10.6 core-h CPU at the run's 79% parallel efficiency)**; the 20 good points cost
  ≈ 21 core-h CPU ⟹ **≈1.05 core-h/point**. This is the number stage 4's walltime should be checked
  against and it was never derived by anyone.

### C2 — ADR-115's falsification: **FINDING** (ruling survives; one stated justification is false)

**(a) Pre-registration: [확인] genuine.** `1_point4_arc1.71/manifest.json` `"falsifiability"` field,
`generated_at_utc 2026-08-21T11:44:36Z` (before submission), reads verbatim: *"NO instability (already
a genuine local minimum in orbital space) FALSIFIES 'unstable wavefunction' and points to the IRC
integrator/numerics instead"*. Identical text in stage 2's and stage 3's manifests. ADR-115's quote is
accurate and not read favourably after the fact.

**(b) Arc 6.83 is the last converged point: [확인] true.**
`U56_RA_scan/irc_forward.log:21784-21789` — `NET REACTION COORDINATE UP TO THIS POINT = 6.83462`,
`# OF POINTS ALONG THE PATH = 20`, then `Point Number 21 in FORWARD path direction.` The crash is at
`:30456` (`Maximum number of corrector steps exceded`). ADR-115's "~20 corrector sub-iterations later"
is exact.
🟡 **But §39.118(i) says the gradient angle rises "monotonically from 31.4° to 59.4°" — that is FALSE.**
The series is 31.39, 41.26, 41.36, 47.09, 48.00, 51.95, 52.00, 55.19, **54.13**, 57.13, **55.14**,
58.21, **55.57**, 58.82, **55.71**, 59.18, **55.74**, 59.39, **55.71** — it splits into two interleaved
sequences (~55.7 and ~59.2) after iteration 10. ADR-115's own softer wording ("escalating 31° → 59°")
is accurate; §39.118's is not. The oscillation is if anything *stronger* evidence for the integrator
reading (a corrector alternating between two trial states), so the conclusion is unharmed — but a
ruling should not assert monotonicity that its own log contradicts.

**(c) Internal-vs-external caveat: [확인] correctly scoped, not downplayed.** The log shows
`Stability analysis using <AA,BB:AA,BB> singles matrix` — the UHF-type internal test, which is exactly
what the pre-registered criterion asked for ("genuine local minimum in orbital space"). No external
(UHF→GHF) or real→complex test was run and the ADR says so. Not load-bearing against the criterion.

**(d) 🟢 A fourth loophole nobody checked — and it closes in ADR-115's favour.** §39.118 checked three.
The obvious fourth is: the probes ran from a **fresh guess** (no `guess=read` in
`stability_probe.gjf`), whereas the IRC propagated its wavefunction point-to-point. A fresh SCF can
land on a *different* solution, in which case the probe would not have tested the wavefunction the IRC
was actually carrying. I checked it directly:

```
probe stage 2  SCF Done: E(UwB97XD) = -349.656751068   (2_point19_arc6.83/stability_probe.log:598)
IRC   point 20 SCF Done: E(UwB97XD) = -349.656751070   (U56_RA_scan/irc_forward.log:21655)
                                        Δ = 2e-9 Hartree
probe stage 1  SCF Done: E(UwB97XD) = -349.624752564   (1_point4_arc1.71/stability_probe.log:630)
IRC   point 5  SCF Done: E(UwB97XD) = -349.624752538   (U56_RA_scan/irc_forward.log:4835)
                                        Δ = 2.6e-8 Hartree
```
Same SCF solution to well inside convergence. The loophole is closed, positively, by measurement.
Report it — it makes ADR-115 stronger than it currently claims to be.

🔴 **(e) FINDING — ADR-115's stated reason for leaving the residual gap open is factually wrong.**
ADR-115: *"the divergent trial geometries were never converged to anything that could be probed"* /
*"the untestable region is untestable by construction, not by omission"*. §39.118(i): *"The actual
failure point was never converged to any single well-defined geometry — it exists only as a diverging
sequence of rejected corrector trials — and therefore cannot be probed with `stable=opt` at all
without first inventing a geometry nobody has independently justified."*
**[확인] Both statements are false against the log.** `U56_RA_scan/irc_forward.log` contains, between
lines 21790 and 30456, **20 fully-specified `Input orientation:` coordinate blocks** (the last at
`:30018`), each followed by a **converged** `SCF Done` (20 of them, zero `Convergence failure`). Those
are the corrector's trial geometries. They are on disk, complete, at zero acquisition cost, and the
existing `tools/build_u56_ra_stability_probe.py` already extracts geometries from exactly this log.
→ **What breaks**: the ADR declares a gap unclosable that costs ~0.5-0.8 core-h to close (stage 1/2
measured 0.51/0.73 core-h for the same 11-atom system). The *falsification at the two probed points*
stands; the *argument for stopping there* does not. → **Direction**: does not cost core-h and does not
change today's numbers; it silently converts "we chose not to test the crash region" into "the crash
region cannot be tested", which is the kind of sentence that gets cited later as if it were a physical
fact. → **Fix**: strike the "untestable by construction" clause; either run the fifth probe
(≈0.7 core-h, see C6-3) or state plainly that the gap is closable and was deprioritised.

**Is the two-point sample too thin to carry the ruling?** No — but only because of (d). Two points on
one arm would be thin on their own; combined with the demonstrated solution-identity to the IRC's own
wavefunction, `EigRej = -1` at all three geometries, ideal spin contamination, all 66 IRC SCFs
converging, and the Bulirsch-Stoer-specific death text, the falsification is adequately supported.

### C3 — ADR-116's Track B rulings: **OK** (all three independent of the diagnostic, as claimed)

- **Item 5 (accept `U56_RA_scan`, reject `U56_RA_qst2`)**: independent, as claimed. The only genuine
  dependency was the "could a wavefunction pathology contaminate both" worry, and ADR-115 removes it.
  ADR-116 correctly says this *removes a doubt* rather than *supplies positive evidence*.
- **Item 6 (reject `U56_RB_scan`)**: [확인] the claim "R-B's IRC never crashed and was never a subject
  of this diagnostic" is **true**. `U56_RB_scan/irc_completion_forward.json` and
  `irc_completion_reverse.json`: `normal_termination: true`, `truncated: false`, both directions; the
  log shows `PES minimum detected on this side of the pathway.` at
  `U56_RB_scan/irc_forward.log:2703` after `# OF POINTS ALONG THE PATH = 1`. The three legs also
  reproduce against `02_METHOD_SPEC.md:20580` (0.0203 Å forward / 0.0228 Å reverse) and `:20613`
  (1.4317 Å → 4.1348 Å, +2.703 Å). "Untouched by today's data": true.
- **Item 7 (still open)**: [확인] not revisionist. None of the four decks touches a Li-coordinate or
  mapping-protocol question; the manifests' own `"question"` fields are about wavefunction instability
  and the IRC integrator only.
- 🟡 **Consequence the ADR does not draw**: items 5+6 together reject two of the three TS attempts,
  leaving `U56_RA_scan` as the **sole** surviving candidate for U-56a. That makes C4 worse, not better.

### C4 — 🔴🔴 **BLOCKER: U-56a is NOT closed. ADR-116's note declares a stage gate passed on the wrong instrument.**

ADR-116 (`01_DECISION_LOG.md:9658-9662`) and `05_STATE.md:8` and `:1776` state: *"U-56a is the binary
feasibility gate … keyed to `endpoint_prep_product`'s certification … It is not keyed to any TS
candidate's fate. **Neither stage 3 nor stage 4 gates U-56a.**"*

**Five independent sources contradict this:**

1. **ADR-109 §Decision 1** (`01_DECISION_LOG.md:9047-9048`), the *user ruling* ADR-116 claims to be
   "clarifying": *"U-56a = binary feasibility (has ONE TS **search** met all eight §39.39(b)
   conditions end to end)."* The gate is keyed to a **TS search**, not to an endpoint.
2. **§39.39(a)** (`02_METHOD_SPEC.md:12327`): *"U-56a binary FEASIBILITY: has ONE TS search met every
   condition, end to end?"*; §39.39(d) U56-1 spells out the verification as *"an exactly-one-imaginary-
   frequency check, the mode-overlap Ω, and a two-directional IRC (C-2)"*.
3. **§39.32(g) condition 7** (`02_METHOD_SPEC.md:11519-11525`) — one of the **eight**: *"the IRC verdict
   passes C-2 (both directions: normal termination, n_points ≥ 5, |ΔE| > 0.05 eV) … the connection must
   be ESTABLISHED by EITHER convergence OR `maxpoints` + B+ agreement **in both directions**."*
   Endpoint certification is **condition 1**, not the gate.
4. **`05_STATE.md:520`** itself, in the lead's own document: *"The endpoint certification FAILED —
   U-56a's **prerequisite 1** is NOT satisfied."* The §2 line proposer11 relied on
   (`05_STATE.md:1609`, *"GATE-CRITICAL — this is what actually closes U-56a"*) was shorthand for
   "the last remaining prerequisite", not "the whole gate". proposer11 explicitly flagged that it was
   relying on that phrasing instead of re-deriving ADR-109 and asked critic to check exactly this
   (§39.123 closing line). This is that check: **the phrasing was misread.**
5. **The code's own record.** `U56_RA_scan/u56_attempt.json`: `"status": "ts_candidate_produced"`,
   `"note": "판정(C-2 IRC verdict, U-56a pass)은 수집/리뷰 단계가 한다"` — the harness itself says the
   U-56a pass verdict is rendered from the C-2 IRC verdict.

**And condition 7 is measurably unmet for the only surviving candidate:**
```
U56_RA_scan/irc_completion_forward.json : normal_termination false, maxpoints_reached false, truncated true
U56_RA_scan/irc_completion_reverse.json : normal_termination false, maxpoints_reached false, truncated true
```
Branch (a) (convergence) fails — the forward arm `Error termination via Lnk1e` at
`irc_forward.log:30457`. Branch (b) requires B+ agreement **in both directions**, and §39.113(1)
(`02_METHOD_SPEC.md:20393-20396`) already ruled the **reverse** arm `low_confidence` (1.71 arc units,
6 points, 1.02-unit mid/last gap) — *and ADR-116 item 5 itself restates that downgrade as "unchanged"
in the same ADR that declares the gate closed.* **ADR-116 contradicts itself internally.**

→ **What breaks**: U-56a is the gate that blocks all S3 production. Reporting it CLOSED unblocks a
multi-thousand-core-h stage on a gate that is not passed — and §39.32(g) closes with the explicit
prohibition: *"a TS 'success' obtained without 1-7 does not close U-56 and must not be reported as
closing it. That is the entire lesson of P1 — 302 core-h that count in neither direction."*
→ **Direction**: this is **not** a core-h error, it is a **silent scientific/governance error** with a
core-h consequence downstream. It is the most expensive item in this review.
→ **Fix**: retract the U-56a note from ADR-116, `05_STATE.md:8`, `:1760`, `:1776`. Restate: U-56a's
condition 1 (endpoints) is satisfied; condition 7 is **not**, for the sole surviving candidate; the
open path to closing it is (i) stage 4 resolving the **forward** arm, plus (ii) a longer or redone
**reverse** IRC to lift the `low_confidence` downgrade. **Stage 4 therefore DOES gate U-56a**, and
stage 4 alone is not sufficient — that second half is currently invisible in every document.

**On the conditional risk ADR-116 flags** (stage 3 UNSTABLE reaching back to R-A's certificates): the
framing is right, but see C6-5 — the class it names ("cation+open-shell") is not the class that was
measured.

### C5 — ADR-117's resubmit recipe: **FINDING ×3** (fix, then run)

**(a) `%nprocshared=1`: [확인] confirmed in both decks** — line 1 of
`3_rc_reactant_21atom/stability_probe.gjf` and of `4_irc_recorrect_restart/irc_recorrect_probe.gjf`.
- 🟡 ADR-117 says *"each `manifest.json` independently records `"nprocshared": 1`"*. **False for
  stage 4**: `4_irc_recorrect_restart/manifest.json` has no `deck_meta` block and no `nprocshared` key
  at all. Stage 3's does (`deck_meta.nprocshared: 1`). Cosmetic, but the sentence says "verified
  directly".
- 🔴 **The G16 precedence claim is not the binding fact, and the recipe leaves a trap behind.**
  [의심] on precedence itself (no G16 on this machine to test; the documented reading is that Link 0
  commands override environment defaults, so the lead's direction is the standard one). **But [확인]
  on something stronger: `GAUSS_NPROCSHARED` is not a Gaussian 16 environment variable.** G16's Link 0
  default for `%NProcShared` is `GAUSS_PDEF`. Corroboration from this project rather than from memory:
  `grep -rn "GAUSS_" src/ tools/` returns only `GAUSS_EXEDIR` and `GAUSS_SCRDIR` — the project has
  never used a core-count environment variable, and every production job sets cores the other way
  (`U56_RA_scan/irc_forward.gjf:1` = `%nprocshared=64`, matching
  `U56_RA_scan.qsub` `select=1:ncpus=64:mpiprocs=64`).
  ⟹ `export GAUSS_NPROCSHARED=4` in §R39.79's skeleton is a **no-op regardless of precedence**. The
  lead's *conclusion* (both paths in ADR-117) is correct; the *reason* given is not the binding one.
  → **Fix**: delete the `export GAUSS_NPROCSHARED=4` line from the script rather than leaving it in
  with a comment. Left in place it is an active trap: the next reader who removes `%nprocshared` from
  a deck believing the environment will supply 4 gets 1 core silently — the exact failure this ADR
  exists to prevent, a third time.

**(b) Walltimes.**
- stage 3 @ 4 cores / 16 h: **safe.** Worst case 30 core-h ÷ (realistic 3-3.5× SMP speedup) ≈ 8.6-10 h.
- stage 4 @ 1 core / 30 h: **safe, and now for a measured reason.** From C1: ≈1.05 core-h/point at
  64 cores ⟹ ≤10 new points ≈ 11 core-h ≈ 11 h at 1 core (cheaper at 1 core — no parallel overhead).
  Even the worst branch (`recorrect=never` silently ignored ⟹ repeat the failing corrector loop) costs
  the measured 10.6 core-h of that loop and still fits.
- 🔴 **fallback stage 3 @ 1 core / 32 h: FINDING — under-margined.** ADR-117 explicitly sizes off the
  *original* 3-30 core-h ceiling "so a repeat kill is not plausible", and gives the primary path a
  **>2×** factor and stage 4 a **1.5×** factor. The fallback gets **32 h against a 30 core-h worst
  case = 1.07×.** → **What breaks**: a stage-3 run in the upper half of its own declared band gets
  wall-killed again, and by ADR-117's own stated sizing basis. → **Direction**: costs core-h (up to
  ~30 wasted) plus a full queue round-trip. → **Fix**: `walltime=45:00:00` — still inside ADR-114's
  48 h cap (`01_DECISION_LOG.md:9492`), and 1.5× the same bound stage 4 was given.

**(c) `%mem=4GB` at 4 cores / 334 bf: OK, not the next thing to blow up.** Evidence rather than
assertion: stage 3 already executed 8 SCF cycles at `MaxMem= 536870912` words (= 4 GB) with
`Gau-53946.int` and `Gau-53946.d2e` both **0 bytes** — fully direct SCF, no integral spill to disk.
The stability pass is AO-direct (`CISAX will form 3 AO SS matrices at one time`), i.e. ~334² × 3 × 8 B
≈ 2.7 MB, and it already completed at 173 bf under the same 4 GB. One caveat worth a line in the
recipe: G16's `%mem` is the **total** for the job, so 4 cores means ~1 GB/thread — still ample here,
but raising cores without raising `%mem` is the general trap.

**(d) Copying the decks: safe in itself, but the instruction as written defeats the clean-restart
ruling.** I read both `.gjf` files end to end. Fully self-contained: relative `%chk`, **inline** `gen`
basis (no `@` include of `inputs/basis/def2-SVPD.gbs`), inline PCM `read` section (`eps=18.5`) as the
last section, no absolute paths. Copying breaks nothing; provenance survives if `manifest.json` and
`probe_point.xyz` travel with it.
🔴 **But ADR-117 says "copy the two deck **directories**".** `3_rc_reactant_21atom/` also contains the
stale, possibly mid-write `stability_probe.chk` (3,940,352 B) and 155 MB of orphaned scratch
(`Gau-53946.rwf` 157,253,632 B, `.d2e`, `.int`, `.skr`, `Gau-53945.inp`). → **What breaks**: G16 opens
an existing `%chk` read/write; a SIGKILL-truncated checkpoint can abort the job at Link 1, which is
precisely the "unverifiable chk" risk §R39.79(c) wrote a whole paragraph to avoid — reintroduced by
the copy instruction. → **Direction**: costs a queue round-trip plus 155 MB of pointless copying; low
risk of a silent wrong answer (default guess is Harris, not `read`, so a stale density is not picked
up). → **Fix**: copy `stability_probe.gjf` + `probe_point.xyz` + `manifest.json` only, into an empty
directory. For stage 4, `irc_recorrect_probe.gjf` + `irc_forward_recorrect_probe.chk` +
`manifest.json` — the `.chk` there **is** the input and must travel byte-exact (verified identical to
`U56_RA_scan/irc_forward.chk`).

**(e) Clean-restart ruling: [확인] correct, and for a stronger reason than the ADR gives.** The ADR
argues from file size and an unverifiable checkpoint. The decisive fact is in the log: stage 3's SCF
had reached `RMSDP=1.77D-04` (`3_…/stability_probe.log:544`) against a requested `1.00D-08` (`:425`).
There is **no converged density in that checkpoint to reuse** — `guess=read` would restart from a
mid-DIIS density with essentially no accuracy benefit over the Harris guess. Start clean. Confirmed.

**(f) `plan.py` / `spec_digest` / `cause_class` / `cli.py` stale-branch: [확인] CLEAR.** The recipe is
`g16 < <deck>.gjf` inside a PBS script that `cd`s into a deck directory. It invokes no `sei_pilot`
entry point, no `cli.py`, reads no `spec_digest`, and creates no plan Item — there is no path by which
it can fire `U56_RA_scan`'s 336 core-h. Two residual notes, neither blocking: (i) the ad-hoc script
keeps `#PBS -V` **without** the production `.qsub`'s `unset SEI_QC_PURPOSE / SEI_SOLVENT_POLICY_JSON /
SEI_C8_ENDPOINTS_JSON` block — harmless because no project code runs in this job, but do not copy this
script shape into anything that does; (ii) the "fresh writable directory" of path 1 should be **outside
`sei_pilot_work/`** as well as outside `cpu_machine_pilot_results/`, so the collector never sees it.

### C6 — What the lead, proposer11 and engineer12 all missed: **FINDING ×5**

1. 🔴 **Stage 4's route has an unpriced failure mode that produces a wrong scientific conclusion, not
   just a wasted job.** `irc=(restart,...)` reads the IRC state from the checkpoint. Whether G16
   honours a *newly added* `recorrect=never` on a restart, or takes its IRC options from the stored
   state, is [의심] — nobody here has G16 to test it, and the deck's own manifest already flags the
   route `[NEEDS VERIFICATION]`. Everyone priced the *malformed-route* branch ("fails at ~zero cost,
   which is itself informative"). **Nobody priced the branch where the route is accepted and the option
   is silently dropped**: stage 4 then reproduces the identical crash and gets read as "the integrator
   hypothesis is also dead", leaving the anomaly permanently unexplained under the project's only
   surviving TS candidate. → **Direction**: silently changes a scientific conclusion. → **Fix, zero
   cost**: before interpreting stage 4, grep the new log for `Recorrection delta-x convergence
   threshold:`. It appears once per corrector step in `irc_forward.log` (20+ times in the failing
   segment alone). **If it still appears, `recorrect=never` did not take effect and the result carries
   no information.** Put that line in the recipe.
2. **Stage 4's `%chk` resolves correctly**: relative filename, and the script `cd`s into
   `4_irc_recorrect_restart/` before invoking `g16`. Confirmed against the killed job's own script
   (`submit_diagnostics.pbs`), which uses the same `( cd "$d" && g16 < … )` shape. OK.
3. 🟢 **There is a fifth diagnostic, and it is the cheapest one in the round.** Per C2(e), the 20
   corrector trial geometries are complete and converged in `irc_forward.log` (last block at `:30018`).
   `stable=opt` at the **last rejected trial geometry** costs ~0.5-0.8 core-h by the measured stage-1/2
   anchor and closes ADR-115's residual gap outright — the difference between "falsified upstream of
   the failure" and "falsified at the failure". `tools/build_u56_ra_stability_probe.py` already parses
   this exact log. Recommended, not required; the ruling does not depend on it.
4. 🟡 **§R39.79's PBS resource line deviates from the only shape this project records as accepted by
   the site.** Proposed: `#PBS -l select=1:ncpus=4:mpiprocs=1:ompthreads=4`. The project's canonical
   form is `ncpus=N:mpiprocs=N` (`tests/test_pbs_script_shape.py:93`, and `U56_RA_scan.qsub`'s header
   comment: *"이전 판은 필터 훅(`job_submit_filter`)에 4/4 거부됐다"* — a previous form was rejected
   4/4 by the site's submit filter). `ompthreads` appears **nowhere** in this repository.
   → **Direction**: costs latency and a round-trip, not core-h or science, but on a recipe whose entire
   purpose is not to be rejected/killed a second time. → **Fix**: use
   `select=1:ncpus=4:mpiprocs=4`, matching the shape the site has actually accepted.
5. 🔴 **"21-atom cation-radical" is factually wrong, and the claim built on it has no variance in its
   own dataset.** Every job in this batch is `Charge = 0 Multiplicity = 2` — verified directly in the
   logs of `endpoint_prep_reactant`, `endpoint_prep_product`, `endpoint_prep_rc_reactant`,
   `U56_RA_scan`, `U56_RA_qst2`, `U56_RB_scan`, and in all four diagnostic decks and manifests
   (`"charge": 0, "multiplicity": 2`). `endpoint_prep_rc_reactant`'s own provenance file is named
   `input_provenance.li_ec2_radical_reactant.provenance.json` — a **neutral** Li(EC)₂ doublet radical.
   §39.113(c) (`02_METHOD_SPEC.md:20185`) claims the MO-coefficient magnitude *"tracks more closely with
   net charge / open-shell character"*; that claim was carried into §R39.78, §39.120 and ADR-117
   (*"~2× the MO-coefficient magnitude in a regime that tracks charge rather than atom count"*).
   **Charge is constant at 0 across all five data points and multiplicity is constant at 2 — the
   dataset contains zero variation in either.** The only quantities that do vary are atom count
   (11 vs 21) and basis size (173 vs 334 bf), and the measured `EigKep` trend ADR-115 itself cites
   (4.2-4.5e-5 → 1.06e-5) tracks **basis size**.
   → **What breaks**: not today's decision (stage 3 must run either way — different molecule, 2× the
   coefficient, 334 bf). What breaks is the **scope of whatever stage 3 returns**. STABLE would be read
   as "the cation+open-shell class is fine" when nothing cationic was measured; UNSTABLE would be read
   as a class-level C-8 risk for "cation+open-shell chemistry" (ADR-116's conditional risk, and
   §39.113(c)'s T21-se completion-risk escalation) on the same non-existent basis.
   → **Direction**: silently changes a scientific conclusion's scope; no core-h. → **Fix**: describe
   the system as what it is — a **neutral 21-atom open-shell doublet, 334 basis functions** — and
   restate the correlation as with basis size / diffuse-function count, which is what was measured.

### C7 — Documentation integrity: **FINDING**

- 🔴 **ADR-116 vs ADR-109 / §39.39 / §39.32(g) / `05_STATE.md:520` / `u56_attempt.json`** — see C4.
  This is the blocking contradiction.
- 🔴 **ADR-116 internal contradiction**: item 5 preserves the reverse arm's `low_confidence` B+
  downgrade ("unchanged and unrelated — not reopened") while the U-56a note declares the gate closed.
  Condition 7 needs B+ agreement in **both** directions. Both statements cannot be true.
- 🟡 **ADR-117**: "each `manifest.json` independently records `nprocshared: 1`" — false for stage 4
  (no such key). See C5(a).
- 🟡 **§39.118**: "rising monotonically" — false. See C2(b). ADR-115's own wording is fine.
- 🟢 **ADR-104/106/108 (PCM ε 18.5)**: no contradiction. All three probe logs report
  `Solvent : Acetone, Eps= 18.500000 Eps(inf)= 1.846337`, identical to the production
  `irc_forward.log` — the solvent deck was **applied**, not merely accepted (§39.39(b) condition 8's
  shape), and the diagnostics are on the same footing as the jobs they interrogate.
- 🟢 **ADR-112 (P1 out)**: untouched. **ADR-114 (48 h cap)**: not violated — but the fallback path
  leaves 16 h of headroom unused while running a 1.07× margin (C5(b)).
- 🟢 **`05_STATE.md` §1e**: an accurate summary of the three ADRs. It inherits their errors
  (`cation-radical` at the stage-3 table row; the `GAUSS_NPROCSHARED` framing) but does not add new
  overstatement, and it is correctly explicit that the resubmit is DECIDED-not-EXECUTED. The U-56a
  overstatement lives at `:8`, `:1760`, `:1776`, outside §1e.
- 🟢 **`src/session_digest/docparse.py::parse_team` — lead's belief CONFIRMED, by execution, not by
  reading.** `parse_team` at `:206-210` appends any non-table, non-blockquote, non-empty line to
  `cur["task"]`, and `cur` is **never reset when the table ends**, so all trailing prose in the
  `## 팀 상태` section lands in the last row. Demonstrated:
  ```
  PYTHONPATH=src python3 -c "from session_digest import docparse; \
    print(len(docparse.parse_team(open('docs/05_STATE.md').read())[-1]['task']))"
  ```
  → engineer12's row carries ~4,000 characters, absorbing the Retired list, the RESUME block, the
  language policy and all seven standing engineering rules. This is **structural and pre-existing** —
  the logic is unconditional and does not depend on anything edited today. **Not a regression.** Not
  fixed (not my file); the one-line fix if anyone wants it is to reset `cur = None` on the first
  non-table line after a row.

### 확인하지 못한 것

1. **G16 Link 0 vs environment precedence, and `IRC=Restart` option handling** — no G16, `formchk` or
   `chkchk` on this machine (`which g16 formchk chkchk` returns nothing). Both are [의심]. The
   `GAUSS_NPROCSHARED`-is-not-a-G16-variable point (C5(a)) does not depend on either and stands on the
   repository's own evidence.
2. **Whether the site's `job_submit_filter` accepts `ompthreads=`** — cannot be tested from here. Flagged
   on the basis of the project's own recorded 4/4 rejection of a non-canonical form.
3. **Stage 3's `stability_probe.chk` internal state** — cannot be opened here. Irrelevant to the ruling:
   C5(e) shows the SCF had not converged, so there is nothing worth reusing regardless.
4. **The cluster-side `$GAUSS_SCRDIR`** — engineer12 already flagged this correctly; unverifiable from
   here, and the returned tree shows scratch landing in the job's own directory
   (`Gau-53946.rwf` alongside the deck), so a resubmit will write ~150 MB+ wherever it runs.

### 요약 — GO / NO-GO

**NO-GO on the resubmit recipe as it currently stands.** Three fixes, none of them research:
raise the fallback stage-3 wall 32 h → 45 h; copy deck **files** not deck **directories**; delete the
`export GAUSS_NPROCSHARED=4` line. Plus one zero-cost addition: the `Recorrection delta-x` grep that
tells you whether stage 4's result means anything.
**BLOCK, separately and more importantly, on the U-56a closure claim** — it must be retracted from
ADR-116 and `05_STATE.md` before it is reported to the user or acted on downstream. The compute is
cheap; the gate is not.

**Reported to**: team-lead (BLOCK on U-56a, NO-GO on the recipe as staged), proposer (C2(e) false
"untestable by construction", C6-5 the cation-radical mislabel, C4's condition-7 chain), engineer
(C5(a) `GAUSS_NPROCSHARED`, C5(b) fallback margin, C6-4 PBS resource shape).

---

## 2026-08-22 (26차 배치) — critic (critic16, successor to critic15): R-9 / §39.124 review — the reverse-arm flatness finding is **falsified at the source**

**Scope, as assigned by lead**: five items — (1) the `arc_length_reached_reverse_new >= 4.27`
`[ESTIMATE]` floor (`02_METHOD_SPEC.md` §39.124(3)); (2) the condition-7 spec-vs-code gap
(§39.124(1)(c)); (3) three lead-found defects in
`src/pilot_package/tools/build_u56_ra_irc_recorrect_probe.py` (`05_STATE.md` §1f "NEW (lead…)");
(4) the reverse-arm flatness finding (§39.124(1)(b)); (5) the sequencing argument (§39.124(4)).
Everything below was re-derived from primary sources (raw `.log`/`.xyz`/`.json` in
`cpu_machine_pilot_results/`, `src/`), never from another agent's summary. **Nothing in `src/`,
`tools/` or any other document was modified.** Abbreviation expansions used here: **R-9** = the
reverse-arm work item; **B+** = the two-terminal-optimisation basin comparator (§39.70); **U-56a** =
the binary feasibility gate for starting stage 3 (S3) production (ADR-109); **D(i)/D(ii)** =
candidate D's tight re-optimisation / reactant-match halves; **RT-N** = one cluster round trip
(~3.5 calendar days).

🔴 **A note on timing that affects how this batch should be read**: `coder15` was already live and
had already landed `guards.reactant_match()`, its wiring in `payload/U56.sh`, and
`tests/test_bplus.py` **before** this review began (files mtime 2026-08-22 15:22; `ListAgents` shows
`coder15` joined ~6 min before I started). §1f's ruling was "critic16 NOW; coder15 AFTER critic's
verdict". That ordering did not hold, and the code that landed bakes in the premise this batch
falsifies. Reviewed as-found, not as-planned.

### 판정 / Verdict

**BLOCK** — not on core-h grounds (cost is genuinely non-binding, engineer13 is right), but because
two of §39.124's three headline findings rest on a **misread of which file holds which geometry**,
and a 30.0–49.9 core-h mandatory job plus a shipped `src/` change were both justified by that misread.

---

### 치명적 (결과가 틀림) / CRITICAL — the finding is wrong, not just weakly supported

**C1. 🔴🔴 BLOCKER — §39.124(1)(b) measured the B+ *start* geometries and reported them as the
*optimised* results. The flatness finding is falsified.**

`02_METHOD_SPEC.md` §39.124(1)(b) / `05_STATE.md` §1f finding (b) state: *"The two terminal
optimizations sit **0.17 Å apart** … yet agree to 0.000127 eV"*, from *"I read the actual `.xyz`
geometries (`reactant_certified.xyz`, `bplus_reverse_mid.xyz`, `bplus_reverse_last.xyz`)"*.

[확인] `bplus_reverse_mid.xyz` / `bplus_reverse_last.xyz` are **not** the optimised endpoints. They
are the B+ **start** points, and they say so in their own comment line:

```
$ head -2 .../U56_RA_scan/bplus_reverse_mid.xyz
11
B+ start (mid, path point 2, arc 0.68385)
```

`payload/U56.sh:1044-1047` writes them from `g16.parse_irc_path_frames`, i.e. raw IRC path points,
*before* the terminal optimisation runs. Verified numerically: each `.xyz` is byte-for-geometry
identical to the corresponding `.gjf` **input** block (max atomic displacement **0.0000 Å**, all 11
atoms, both points).

The real optimised endpoints, read with the project's own parser
(`sei_pilot.criteria.g16.last_geometry`) from `bplus_reverse_{mid,last}.log`:

| geometry | O(1)–C(2), the declared break bond |
|---|---|
| `reactant_certified.xyz` | 1.4143 Å |
| **optimised** `bplus_reverse_mid` | **1.4145 Å** |
| **optimised** `bplus_reverse_last` | **1.4148 Å** |
| (start points, what §39.124(b) actually measured) | mid 1.6111 Å, last 1.4364 Å |

Full internal-coordinate comparison (all 55 pairwise distances, orientation-invariant, so no
alignment artefact):

```
optimised mid  vs optimised last          max |Δd| over 55 pairs = 0.0091 Å
optimised last vs certified reactant      max |Δd| = 0.465 Å — and EVERY deviation > 0.02 Å
                                          involves Li10 only:
                                            H6–Li10 4.743 → 5.208   (0.465)
                                            C2–Li10 4.456 → 4.744   (0.288)
                                            O1–Li10 3.113 → 3.363   (0.250)
                                          the organic skeleton matches to ≤ 0.02 Å
```

⟹ **The two reverse B+ optimisations converged to the same structure (0.0003 Å apart on the break
bond, ≤0.0091 Å across every internal distance), and that structure is the certified reactant up to
a ≤0.47 Å displacement of Li — the one soft cation coordinate `bplus_agreement` deliberately
excludes** (§39.70 / C-3; `guards.py`'s own note records `d(Li–O)` spanning 1.95–3.40 Å across
0.06 eV).

Consequences, each of which is itself actionable:

1. **The "surface too flat to tell" conclusion is unsupported.** Two starts 0.17 Å apart converged
   to within 0.0003 Å. That is the comparator **discriminating**, not failing to. Apply §39.76's own
   test to the finding: *if the surface were NOT flat, would the numbers §39.124(b) quoted look any
   different?* **No — they are the start points, which are 0.17 Å apart by construction** (that is
   what `bplus_sample_points` is for). The quoted evidence has **zero** discriminating power for the
   claim it was used to support.
2. **Candidate D(i) is priced against a phantom.** `03_COMPUTE_PLAN.md` §R39.81 makes D **mandatory,
   run regardless of A/B or any cost ceiling**, at **30.0–49.9 core-h**, whose stated purpose is
   *"to settle whether (b)'s 0.17 Å gap is a real feature or a loose-optimization artifact."*
   **There is no 0.17 Å gap between the optimised points.** → Cancel D(i) as scoped, or re-scope it
   to a question that exists.
3. **Finding (c)'s worked example is void.** §39.124(1)(c) and §1f both argue the reading matters
   because *"a literal both-points reading would reject `mid` (0.197 Å out) while `last` passes
   (0.022 Å)."* Measured on the optimised endpoints the deltas are **0.0002 Å (mid)** and
   **0.0005 Å (last)**. Under every reading of condition 7, **both pass.** The reading question is
   real as a spec question but has **no consequence on this data**, and must stop being described as
   the thing that could reject `mid`.
4. **`guards.reactant_match()`'s docstring now ships the false premise as measured fact** —
   `guards.py:507-509` states *"`last` passes any plausible reading (0.022 Å) while `mid` would fail
   a strict one (0.197 Å)"*, and `tests/test_bplus.py:117-128`'s
   `test_a_stretched_but_still_bonded_point_reports_the_delta_without_deciding` is built on it. The
   **function** reads the right geometries (`U56.sh:1080-1081` passes `g16.last_geometry(log)`, not
   the `.xyz`) — the code is correct, the justification around it is not.

→ **고쳐라**: retract §39.124(1)(b) and the derived text in `05_STATE.md` §1f finding (b)/(c);
re-scope or cancel candidate D(i) in §R39.81; correct `guards.py`'s docstring and the test's
docstring. Record it as a correction, not an erasure, per the project's own convention.

**C2. 🔴 BLOCKER-adjacent — `guards.reactant_match()` can never return `True`. Condition 7's
reactant-match half is a gate that cannot open.**

[확인] `guards.py:539-585`: `match` is set to `False` only when the covalent graphs differ; in the
graph-agreeing branch it is left `None`. There is no path to `True`. The project's own test asserts
this for two **identical** geometries:

```python
# tests/test_bplus.py:113-117
r = guards.reactant_match(a, list(a), self.BREAK_PAIR)
self.assertIsNone(r["match"], "graph agreement alone must not become True (finding (b))")
```
(I ran the suite myself: `PYTHONPATH=src/pilot_package python3 -m unittest discover -s tests -p
"test_bplus.py"` → `Ran 32 tests … OK`.)

Failure scenario: a caller implementing condition 7 as *"reverse endpoint must match the certified
reactant"* asks for `match is True`. It is never `True`, therefore condition 7 never passes,
therefore **U-56a can never close** — including today, where the reverse endpoint matches the
certified reactant to 0.0005 Å on the ruled coordinate. The `None` is defended by finding (b), which
C1 falsifies.

The stated blocker to a tolerance was *"no measured bracket exists."* One exists now, from this
reaction's own already-paid runs, in exactly the two-sided form `BPLUS_ENERGY_TOLERANCE_EV` itself
was derived in (`guards.py:360-370`):

```
SAME basin (measured)      optimised reverse mid/last vs certified reactant   Δ(break bond) 0.0002 / 0.0005 Å
DIFFERENT basin (measured) optimised forward mid/last vs certified reactant   Δ(break bond) 1.748 / 1.700 Å
                                                                              (3.1620 / 3.1138 vs 1.4143)
⟹ ~3,400× separation. Any tolerance in 0.01–0.5 Å passes what it must and separates what it must.
```

→ **고쳐라**: proposer rules a break-bond tolerance against that bracket; coder makes `match` capable
of `True`. Until then do not describe D(ii) as "implementing condition 7" — it implements the
reporting half only.

**C3. 🔴 The `maxpoints=30` ruling is unimplemented, and the trivial fix is not sufficient by
itself.** [확인] I ran the builder for the reverse direction:

```
$ python3 tools/build_u56_ra_irc_recorrect_probe.py --job-dir .../U56_RA_scan \
      --out-dir /tmp/probetest --direction reverse
route: #p nosymm wB97XD/gen scrf=(pcm,solvent=acetone,read) geom=check guess=read \
       irc=(restart,recorrect=never) Int(Grid=UltraFine)
```

`build()` assembles `irc_opts = ["restart"]` (+`recorrect=never`, +optional `stepsize`) —
`maxpoints` and the direction keyword are never written (`build_u56_ra_irc_recorrect_probe.py:88-95`).
The lead's reading is **confirmed**: the ruled `maxpoints=30` would hold only by the same silent
checkpoint inheritance the project refuses to trust for `recorrect=never` (hence the mandatory
`Recorrection delta-x convergence threshold:` grep). Both cannot be right.

Two things the "state it explicitly" fix does **not** cover:
- **The direction keyword should NOT get the same treatment blindly.** `irc_reverse.chk` holds a
  single-direction run, so bare `restart` resumes the correct branch. Adding `reverse` to a
  `restart` route is a keyword combination this project has never smoked and, on some G16 builds,
  reads as "now do the other direction from the saddle" — which would silently start a *new* forward
  walk and burn the round trip. **[의심], not confirmed — no G16 here.** → Do not add it. Verify by
  reading the restart log's first `NET REACTION COORDINATE` (must resume at ≈1.706, not 0.34) and
  the break bond (must be ≈1.41, not increasing) before interpreting anything.
- **`maxpoints=30` on a restart is ambiguous between "30 total" and "30 more."** [의심] Unverifiable
  here. Cost impact trivial either way; state which you assumed in the manifest so the returned log
  can falsify it.

**C4. 🔴 `%nprocshared=1` at `maxpoints=30` breaks ADR-114's 48 h wall cap — a sharper hazard than
"ADR-117 repeat."** [확인] `build(..., total_cores=1)` writes `%nprocshared=1`
(`build_u56_ra_irc_recorrect_probe.py:112`); the generated reverse deck carries it. Note the staged
stage 4 is *self-consistent* at 1 core (`submit_stage4.pbs`: `select=1:ncpus=1`, deck
`%nprocshared=1`), so it is **not** an ADR-117 deck/allocation mismatch. The real exposure is wall
clock:

```
candidate A at maxpoints=30 = 24 remaining points x 1.92-3.63 core-h/pt (engineer13's measured bracket)
  at 64 cores (as priced, §R39.81)   0.7 - 1.4 h   ✅
  at the tool's default 1 core       46  -  87 h   ❌ pessimistic branch EXCEEDS ADR-114's 48 h cap
```

That is the same wall-kill that produced ADR-117 (PBS 23731675, `walltime 7244 exceeded limit 7200`),
reachable purely from a default. → Build candidate A with an explicit `--total-cores 64` **and** a
matching `select=1:ncpus=64`; or make `--total-cores` required with no default.

---

### 중대 / MAJOR — waste, or a decision that cannot be evaluated

**M1. The acceptance criterion of §39.124(3) is prose-only — "program-evaluable" is not yet true.**
[확인] `grep -rn "4\.27" src/ tests/` returns only unrelated basis-set and fixture hits. There is no
constant, and `irc_completion_*.json` carries no arc field at all
(keys: `_note, maxpoints_reached, minimum_found, normal_termination, path_calculation_complete,
termination_reason, truncated`). `arc_length_reached_reverse_new` names a quantity nothing emits.
It is computable (`g16.parse_irc_arc_lengths`, `criteria/g16.py:268`) but is not computed. Same
"ruled but unwired" family as C3. → Emit arc length into `irc_completion_*.json`, then the criterion
can be evaluated by a program rather than by a person with a grep.

**M2. §39.124's `maxpoints=30` justification cites §39.116 for the opposite of what §39.116 ruled.**
[확인] The addendum's reason 1 says a self-declared `PES minimum detected on this side` stop is
*"categorically stronger evidence"*, *"the same self-declared stop `U56_RB_scan` produced,
§39.116"*. §39.116(b)-(c) ruled that exact stop an **artefact**: the declared minimum was 0.0009 Å
from the saddle, and *"do not count this arm as C-2 'connection established' evidence."* I
re-derived it: `U56_RB_scan` both arms stopped at **1 point**, arc **0.18324** (forward) /
**0.22291** (reverse). The precedent cited as the strongest-evidence case is the project's own
worked example of the weakest. The ruling (`maxpoints=30`) still stands on reason 2 and on M4 below
— **the ruling survives, its first justification does not.**

**M3. 🔴 A live risk this creates for candidate A that no document names.** §39.116's artefact
mechanism is *a fixed force-threshold minimum-detection test firing on a flat coordinate*. The
reverse arm's terminal region **is** low-gradient (max force 1.6–3.3 × 10⁻⁴ au at both B+ points).
So candidate A's *best* outcome — an early `PES minimum detected on this side` — is precisely the
outcome §39.116 says can be an artefact, and §39.124(3)'s criterion has **no branch for it**: three
AND-ed clauses, all written for the truncated/B+ branch. → Add the §39.116 test explicitly: a
declared minimum counts only if it is structurally distinct from the preceding path point (state the
coordinate and the comparison; do not invent a threshold, report the delta).

**M4. §39.124(3)'s three clauses conflict with §39.32(g) branch (a), and nothing says which
governs.** Condition 7 establishes the connection by **EITHER** convergence **OR**
`maxpoints`+B+ agreement. §39.124(3) is a single AND-block (`n ≥ 10 AND bplus.agreement AND
arc ≥ 4.27`) with no branch scoping. A reverse restart that converges to a genuine, structurally
distinct minimum at n = 8 / arc 3.9 satisfies §39.32(g) branch (a) and **fails** §39.124(3) as
written. → Scope the criterion explicitly to branch (b).

**M5. Item (3)-4 confirmed, and it is worse than "wrong for reverse": the string is wrong for
forward too.** [확인] The manifest's `estimated_cost` is hardcoded at
`build_u56_ra_irc_recorrect_probe.py:152-155` and emitted verbatim under `--direction reverse`:
*"~29 remaining points at most (maxpoints=30 minus 20 already computed and stored)"*. `30 − 20 = 10`,
not 29 — the headline number contradicts its own parenthetical. For reverse the true figure is
`30 − 6 = 24`. Standing rule 1 (unit-in-the-cell / a number must describe the route it is attached
to) violated three ways in one string. → Compute it from `direction` and the checkpoint's own point
count.

---

### 사소 / MINOR

- **N1.** `shutil.copyfile(src_chk, dst_chk)` (`:76`) has no overwrite guard, and the module
  docstring claims *"Re-running is idempotent."* It is idempotent for the *source*, but re-running
  the builder into an out-dir where the probe has already run **silently overwrites the progressed
  checkpoint** — i.e. destroys the run's IRC path. Diagnostic-only today; guard it before this
  pattern is reused.
- **N2.** `bplus_sample_points` picks `mid` on the reverse arm by a margin of 0.0037 arc units
  (|0.68385 − 0.85292| = 0.16907 vs |1.02571 − 0.85292| = 0.17279). Effectively a coin flip between
  path points 2 and 3. Not load-bearing here (C1 shows both would optimise to the same place), but
  worth knowing before anyone treats "the midpoint" as a stable choice.
- **N3.** Running the builder from `src/` emits `package_fingerprint f15cce8bfb4ed4e2`, not the live
  package `a7b668127d052e33` (`05_STATE.md` §4 RESUME (5)). Expected given the un-rebuilt
  comment-only diff, but any deck built now will carry a fingerprint that matches no released
  package. State it in the handoff.

---

### 비판이 통과한 것 / What survived review — negative results, reported as required

- **P1. The 4.27 floor is NOT unsatisfiable, and I checked the way it could have been.** My concern
  was that the reverse arm reaches its endpoint in far less arc than forward (break-coordinate
  travel: reverse TS→reactant 1.7286 → 1.4143 = 0.31 Å; forward TS→product ≈ 1.0 Å), so a floor
  calibrated on forward's arc could reject a *successful* reverse run. Tested with a mass-weighted
  Kabsch superposition in G16's own arc units (amu^½·bohr), validated against the log
  (TS→point 2 computed 0.683 vs log arc 0.684; TS→point 5 computed 1.679 vs log 1.706 — a
  straight-line chord, correctly slightly under the path length):

  ```
  IRC point 5 (arc 1.706) -> the minimum its own B+ optimisation reached   >= 4.76 arc units
  ⟹ total reverse path length >= 1.71 + 4.76 = 6.47 arc units  (forward's measured total: 6.83)
  ```
  So arc ≥ 4.27 is ~66 % of the reverse arm's own estimated path length and is comfortably
  reachable. **The concern is refuted by data; the floor's *magnitude* survives.** Two by-products:
  (i) the break-bond coordinate is a poor progress proxy here — at point 5 it has already reached the
  reactant's value while ≥73 % of the mass-weighted path remains, which is an independent reason
  §39.124(b)'s "0.022 Å, which is reassuring" was reading the wrong coordinate; (ii) **`maxpoints=15`
  would have undershot**: 9 new points × 0.3415 = 3.07 arc, total 4.78 — clearing the 4.27 floor
  while stopping ~1.7 arc units short of the actual minimum. proposer12's `maxpoints=30` over
  engineer13's 15 is **independently vindicated**, on a ground neither of them stated.
- **P2. The floor's *derivation* is still weak, and `[ESTIMATE]` is the right label but the review
  trigger is not concrete enough.** 6.83 is not a measurement of sufficiency — it is where forward
  happened to crash; what made forward "sufficient" was n = 20 ≥ 10, a frame count. At the measured
  rate (0.3415 arc/frame, identical on both arms) `arc ≥ 4.27` is algebraically `n ≥ 12.5`, so
  against an unchanged step size the clause adds 25 % margin and nothing else — which is fine,
  because its **only stated job is candidate B's changed step size**, and for that it does work.
  A midpoint of n = 2 is defensible *as an interim placeholder with that narrow job*, and P1 shows it
  lands in a sane place. → Keep it; make the trigger fire: *"supersede when a third measured
  truncated-IRC arc exists, or when any reverse arm reaches a structurally distinct minimum"* is
  checkable; *"once more measured cases exist"* is not.
- **P3. Condition 7's reading — my verdict, which §39.124 declined to give.** *"in both branches the
  reverse endpoint must match the certified reactant"* (§39.32(g), the §39.55(d) form). **"Both
  branches" means the two establishment branches just enumerated** — convergence, and
  `maxpoints`+B+ — **not the two B+ start points.** Three reasons: the clause is appended to an
  `EITHER … OR` and "branches" has an antecedent in the same sentence; "endpoint" is singular and
  `mid` is by construction a *mid*point (`bplus_sample_points`), not an endpoint; and the whole point
  of `mid` is to detect a bifurcation *between* the samples, which requires it to be allowed to
  differ. ⟹ **Condition 7 constrains `last` only, and it constrains it in the convergence branch
  too** — which today has no check at all. C1 makes this moot on the present data (both points match
  to ≤0.0005 Å) but it is the ruling coder needs. Note the current implementation runs on both
  points, which is harmless and arguably better as *reporting* — it must simply not be combined into
  a verdict that requires both.
- **P4. The gradient-angle signature of §39.124(1)(a) reproduces exactly, and — unlike most
  agreements this project has been burned by — it has a real negative control.** Re-derived by grep
  from both raw logs:
  ```
  forward  1.06 … 31.39 41.26 41.36 47.09 48.00 51.95 52.00 | 55.19 54.13 57.13 55.14 58.21 55.57
           58.82 55.71 59.18 55.74 59.39 55.71        (climb over 7, then a 2-cycle in 55.1-59.4)
  reverse  0.29 0.98 0.64 0.43 4.19 | 48.89 59.74 52.28 58.81 51.83 … 58.8907 51.8366
                                                      (no climb; a 2-cycle in 51.8-58.9 immediately)
  ```
  Both die on `Maximum number of corrector steps exceded` → `Error termination via Lnk1e`. Applying
  §39.76's test: *would this look any different if the two arms did NOT share a mechanism?* **Yes —
  and I found the control.** `U56_RA_qst2` crashed with the **same terminal message** on both arms
  but in a completely different band (forward terminal ≈17.4–17.9°, reverse ≈13–23°). So the
  *message* has zero discriminating power (three of four crashed arms share it) while the *band*
  has real discriminating power. **§39.124(4)'s sequencing keeps its basis.** One caveat worth
  recording: a shared 2-cycle may be a property of the shared `calcfc` Hessian and step size rather
  than of the crash geometries — which if anything **strengthens** "same response to
  `recorrect=never`", so the ruling is unaffected either way.
- **P5. Everything else I re-derived reproduces.** Reverse arc table 0.34199/0.68385/1.02571/1.36739/
  **1.70584**, 5 frames excluding the saddle; forward 20 frames, **6.83462**; B+ gap **1.02199**;
  `energy_delta_ev` 1.268e-4 eV from the two final `SCF Done` lines (−349.620907545 /
  −349.620912204 Ha); `irc_completion_reverse.json` `maxpoints_reached: false`,
  `normal_termination: false`, `truncated: true`; `irc_forward.chk` and `irc_reverse.chk` both
  **10,342,400 B**; both B+ optimisations printed genuinely converged `Item` tables (max force
  3.26e-4 / 1.61e-4 au, all four criteria YES on the final step). The reverse restart deck the
  builder emits carries the **correct** solvent — `scrf=(pcm,solvent=acetone,read)` + `eps=18.5`,
  byte-identical to `irc_reverse.gjf`'s — so C-5 is not at risk here.

---

### 확인하지 못한 것 / Could not verify

1. **G16 restart semantics** — whether `maxpoints=30` on an `irc=restart` counts total or additional
   points, and whether adding `reverse` to a restart route resumes or restarts. No G16 on this
   machine; the project has none either. Both are resolved by the post-run checks named in C3, at
   zero cost.
2. **Whether `irc=restart` will in fact inherit `maxpoints` from the checkpoint.** The same
   uncertainty that makes the `recorrect=never` grep mandatory applies here, in the opposite
   direction, and cannot be settled without running it. C3 removes the dependency instead.
3. **Whether candidate D(i) at tight convergence would add anything after C1.** With the optimised
   points already 0.0003 Å apart the *stated* question is answered. Whether a tight re-optimisation
   plus a frequency calculation would settle the residual **Li**-position question (the only real
   difference from the certified reactant, ≤0.47 Å) is a proposer call on a coordinate that
   §39.70 deliberately excludes from the comparator — I am not ruling it, only noting that the Li
   displacement, not a break-bond gap, is what is actually left.
4. **The 0.0091 Å mid-vs-last agreement is orientation-invariant and solid; the mass-weighted
   figures in P1 are chord lower bounds, not path lengths.** The ≥6.47 arc total is therefore a
   floor. It is enough to refute "4.27 is unreachable"; it is not a prediction of where the run
   stops.

### 요약 — GO / NO-GO

**BLOCK.** Nothing is scheduled, so nothing is burning — but three things must change before
candidate A is built or D(i) is funded:
1. **Retract §39.124(1)(b)** and the derived §1f text; **cancel or re-scope candidate D(i)**
   (30.0–49.9 core-h against a gap that does not exist); correct the docstring and test rationale
   that already shipped on that premise.
2. **Rule a break-bond tolerance** against the 0.0005 Å / 1.70 Å bracket above so
   `reactant_match()` can return `True`. Today condition 7's reactant half cannot be satisfied by
   any input.
3. **Build candidate A only with explicit `maxpoints`, explicit `--total-cores 64`, and a matching
   `ncpus=64`.** At the tool's default of 1 core the pessimistic branch runs 87 h against a 48 h cap.

Cost verdict unchanged from engineer13: cost is not the binding constraint. **The binding constraint
is that two ruled findings measured the wrong file.**

**Reported to**: team-lead (BLOCK + the D(i) cancellation, which is a budget line), `coder15`
(C1's docstring/test correction, C2's tolerance gap, C3/C4/M5's tool fixes — sent directly, it is
already mid-implementation), `proposer12` (C1 retraction, M2's mis-citation of §39.116, M3/M4's
missing branches, P2/P3's rulings needed), `engineer13` (D(i) re-scope, C4's 1-core wall exposure
against the 64-core pricing).

### 26차 배치 — 추가 (critic16): review of proposer12's three new rulings (§39.124 correction block)

proposer12 retracted finding (b), struck the §39.116 mis-citation, withdrew candidate D(i), and
supplied three new rulings. **Retraction and D(i) withdrawal: confirmed correct, nothing further.**
The three new rulings are **author-originated numbers written after my review**, so §4 standing rule 6
applies to them too. Two of the three have a defect. Re-derived from primary sources as before.

**A1. 🔴 Ruling 2 drops the reactant-match from branch (a) — it re-creates finding (c)'s gap on the
other branch.** [확인] As written: *"IF branch (a) (normal termination, `minimum_found: true`, AND
ruling 3's distinctness check passes) THEN condition 7 is satisfied outright for that direction.
ELSE IF branch (b) … apply (3)'s full AND-block, with the reactant-match check (ruling 1) on `last`
only."* The reactant-match is attached to branch (b) alone. But §39.32(g)'s ruled text is *"…**AND in
both branches** the reverse endpoint must match the certified reactant"* — the clause is appended
**outside** the `EITHER…OR`, which is the entire basis on which I ruled "branches" = the two
establishment branches (26차 배치 P3). My own verdict said so explicitly: *"it constrains `last` only,
**and it constrains it in the convergence branch too** — which today has no check at all."*

Failure scenario, and it is the exact one condition 7 exists to prevent: candidate A's restart
terminates normally, declares a minimum, and that minimum is structurally distinct from the preceding
point — but it is **not** the certified reactant (a different conformer, a different Li-coordination
minimum, or a path that bifurcated past point 5, which is R-1/R-2's own named residual risk). Under
ruling 2, condition 7 passes **outright**, U-56a closes, and S3 production starts on an IRC that never
connected to the certified reactant. That is P1's failure — *"302 core-h that count in neither
direction"* — reproduced through a branch nobody checks.
→ **고쳐라**: apply the ruling-1 reactant match to the branch-(a) endpoint as well. Branch (a) needs
*fewer* clauses than branch (b) (no frame count, no arc floor — those substitute for ground truth B+
lacks), but the reactant match is not one of the clauses branch (a) makes redundant. It is the only
clause that checks *which* minimum was reached.

**A2. 🔴 Ruling 3's ~0.05 Å distinctness threshold is on the wrong side of the measured
step-to-step spacing — it will fire on healthy IRCs.** Ruling 3 flags a declared minimum as
"artifact-suspicious" when the max pairwise heavy-atom distance change **from the immediately
preceding IRC point** is below ~0.05 Å, borrowing ruling 1's number. [확인] I measured what a healthy
IRC on this exact system actually does between consecutive path points, using the project's own
`g16.parse_irc_path_frames` and §39.116(d)'s own rotation-invariant metric:

```
consecutive-point max pairwise distance change, U56_RA_scan
  reverse (5 frames)   0.059  0.060  0.061  0.054            min 0.054 A
  forward (20 frames)  0.060  0.061  0.063  0.064  0.063 …    min 0.045 A, max 0.064 A
§39.116(d)'s confirmed-artifact case                          0.0203-0.0228 A
ruling 3's threshold                                          ~0.05 A
```

The threshold sits **inside the normal band** (0.045–0.064 Å), not below it. A completely healthy IRC
step measures 0.045–0.064 Å, so a legitimate final step — which is typically a *truncated* step, G16
shortening the last increment as it closes on the minimum — lands under 0.05 Å routinely. The
criterion would then demand a human read on the successful outcome it was written to protect, while
the real artifact signature (0.0203–0.0228 Å) is only ~2–3× below the normal band, so the two
populations are not well separated by any single number in this region.
→ **고쳐라**: anchor the threshold **below** the measured normal band, not at ruling 1's number —
≤0.025 Å is what §39.116(d)'s own measurement supports, and it leaves the healthy 0.045–0.064 Å band
clear by ~2×. Better still, report the delta **alongside the measured normal band for that same run**
(the median consecutive-point delta of its own path), which is free, self-calibrating, and needs no
ruled constant at all — the same "gate-before-you-pay against a number the pipeline already emits"
shape as standing rule 5.

**A3. 🔴 Ruling 1's 0.05 Å and ruling 3's 0.05 Å are two unrelated physical quantities wearing the
same number.** Ruling 1's is the distance between two **independently optimised structures**; ruling
3's is an **IRC step-to-step displacement**. Nothing derives one from the other; ruling 3 reuses it
because it was to hand. This is the "a constant in disguise" / "placeholder promoted to a decision"
pattern the project has recorded repeatedly (ADR-098/100, and `bplus_sample_points`'s own docstring on
index fractions). Whatever numbers survive A2, they should not be the same symbol.

**A4. 🟡 Ruling 1 has no energy clause, and the case it cannot exclude is the one already measured on
this project.** `reactant_match` compares covalent graph + break-bond distance. `bplus_agreement`'s
own docstring says why that is not enough: *"two COORDINATION ISOMERS can share a covalent graph and
sit in different basins. That is measured, not hypothetical — §39.42(a) found a 21-atom seed landing
**0.686 eV** from its five siblings with the same covalent graph."* This is not hypothetical here
either: the reverse endpoint differs from the certified reactant almost entirely in **Li** position
(O1–Li10 3.113 → 3.363 Å, H6–Li10 4.743 → 5.208 Å) — precisely a coordination difference, and
precisely what Layer-I exclusion removes from the structural comparison by design.

The clause is **free** — both energies are already on disk, same level, same route, same solvent
(`endpoint_certs.json` confirms `wB97XD/def2-SVPD grid=ultrafine scrf=(pcm,solvent=acetone,read)
['eps=18.5']` on both sides):

```
certified reactant  endpoint_prep_reactant/endpoint_tight.log   E = -349.620897014 Ha   (opt=tight)
optimised last      bplus_reverse_last.log                      E = -349.620912204 Ha   (opt=loose)
optimised mid       bplus_reverse_mid.log                       E = -349.620907545 Ha   (opt=loose)
Δ(last − reactant) = −1.519e-5 Ha = −4.13e-4 eV   ⟹ inside BPLUS_ENERGY_TOLERANCE_EV (1.0e-3 eV)
                                                     and 1,600× below the measured different-basin
                                                     scale (0.686 eV)
```
⟹ **The reverse endpoint is the certified reactant's minimum on the energy clause too**, and the
0.25 Å Li displacement costs 4e-4 eV — a direct measurement of that coordinate's softness, consistent
with `guards.py`'s own 1.95–3.40 Å across 0.06 eV note. → Add the energy clause to ruling 1, reusing
`BPLUS_ENERGY_TOLERANCE_EV` rather than a new constant.
⚠ **Matched-method caveat, stated because this project has been bitten by it**: that Δ compares an
`opt=tight` energy against an `opt=loose` one, and the loose optimisation's own last cycle still moved
1.9e-4 eV. The comparison is inside its own resolution by only ~2×. It is decisive against the
0.686 eV different-basin scale and should be read that way, not as a 4-decimal agreement.

**A5. 🟢 What I checked and found correct in the new block.** §39.116(d) does exist and does record
0.0203–0.0228 Å for the artifact case — the citation is accurate. `Maximum Displacement 0.010000`
does appear in `bplus_reverse_last.log`'s `Item` table, and 0.010 Bohr = 0.00529 Å is right, as is
"0.05 Å is ~10× that". √(0.0005 × 1.7) = 0.029 Å is right. The break-bond table in the correction
block reproduces my numbers exactly. One wording nit: that threshold is per **internal coordinate**,
not "per atom" — which makes it a *better* anchor for a bond-distance tolerance than the doc claims,
not worse.

**A6. 🟡 Nit, fragility not error.** `endpoint_certs.json`'s `reactant_xyz` is an absolute
`/scratch/...` cluster path, and `U56.sh:1108-1117` opens it directly. Off the original cluster the
`except OSError` branch records `_status: "NOT computed"` — honest, not silent, so this is not a
correctness defect. But it means the newly-added condition-7 check is the one most likely to be
skipped on any re-run from a different root. Resolve against the job dir first, fall back to the
recorded path.

**판정 on the new rulings**: retraction, D(i) withdrawal, §39.116 strike, and ruling 1's **distance**
anchor — **OK**. Ruling 1 needs the energy clause (A4). **Ruling 2 (A1) and ruling 3 (A2/A3) are
FIX-THEN-RUN** — neither costs core-h to fix, and A1 in particular must not reach a gate decision as
written.

**Reported to**: `proposer12` (A1–A4, directly), team-lead (A1 as the one that bears on U-56a's gate).

### 26차 배치 — 추가 2 (critic16): review of the SECOND correction block — one implementability blocker, one degenerate test

proposer12's A1/A3/A5 fixes are **correct and adopted without further comment**. A2's re-derivation
reproduces (their 5 deltas include the saddle→point-1 step my 4 omitted; the 4 overlapping values
match to three decimals). Three defects remain in the fixes themselves, one of which stops ruling 1
from being implementable at all.

**B1. 🔴 BLOCKER for ruling 1 — the new energy clause has no data source anywhere in the job
directory the check runs from.** [확인] Ruling 1 (corrected) requires *"(ii) energy agreement within
the existing `BPLUS_ENERGY_TOLERANCE_EV`"* between the B+ endpoint and the certified reactant. The
B+ payload block (`payload/U56.sh:1105-1117`) reads `endpoint_certs.json`. I checked both candidate
carriers:

```
U56_RA_scan/endpoint_certs.json        keys: reaction, method, required_level, reactant_cert{optimised,
                                       converged, n_imag, level, source, solvent_config, solvent_route},
                                       reactant_xyz, reactant_source, product_cert, product_xyz,
                                       product_source, declared_planar        -> NO energy
endpoint_prep_reactant/f1_observables.json   keys: angle_li_o_c, n_imag_at_convergence,
                                       n_imag_entering_tight_stage, normal_termination, opt_converged,
                                       ring_bond_lengths, s2_stage1_rough, s2_stage2_tight,
                                       start_selection, symmetric_fingerprint_at_convergence,
                                       _s2_note, _n_imag_entering_tight_stage_status  -> NO energy
```

The certified reactant's energy (−349.620897014 Ha) exists **only** in
`endpoint_prep_reactant/endpoint_tight.log` — a **different job directory**, reachable only through
`reactant_cert.source`, which is an absolute `/scratch/q656a01/...` path that additionally points at
`f1_observables.json`, the file that does not carry the number.

Failure scenario, and it is the project's own signature failure: coder implements clause (ii), the
lookup fails, `U56.sh`'s `except (OSError, KeyError, IndexError, ValueError)` records
`_status: "NOT computed"`, `match` stays `None` — and condition 7 is un-satisfiable again,
**silently, on the exact axis just added to fix it.** "Ruled but unwired," one layer further out
again.
→ **고쳐라**: make the certified energy a **recorded field**, not a cross-job log grep at gate time —
`endpoint_prep` emits it into `f1_observables.json`, and the cert resolver copies it into
`endpoint_certs.json` alongside `reactant_xyz`. For R-A specifically the number cannot be emitted
retroactively; back-fill it from the returned tree with provenance
(`endpoint_prep_reactant/endpoint_tight.log`, final `SCF Done`, `opt=tight` level3, three repeated
`SCF Done` lines at that value). Until that field exists, ruling 1 clause (ii) is prose.

**B2. 🔴 The self-calibrating relative test is degenerate on exactly the case it was written for.**
A2's preferred check: *"flag if the declared-minimum step is under half of that same run's own median
consecutive-point delta."* [확인] With **one** post-saddle point — which is precisely `U56_RB_scan`,
the confirmed-artifact case §39.116(d) measured — the run has exactly one consecutive delta, the
median **is** that delta, and the test reduces to `d < 0.5·d`, which is **never true**. The preferred
test can never fire on the canonical artifact. With two deltas it fires only if `d₂ < d₁/3`, also
very strict. The cause is that the step under test is included in its own reference set.
The absolute floor would still catch RB (0.0203–0.0228 Å < 0.025 Å), but A2 says the relative test is
**"preferred where available"**, and a median of one element *is* available to a naive implementation
— so the fallback that works is the one the rule tells you not to use.
→ **고쳐라**: compute the median over the **prior** deltas only, excluding the step under test, and
declare the relative test available only at **≥3 prior deltas**; below that the ≤0.025 Å absolute
floor governs. State the precedence explicitly so an implementer cannot pick the degenerate branch.

**B3. 🟡 Ruling 1 is now two clauses and needs `bplus_agreement`'s conservative rule, not a bare
`AND`.** `bplus_agreement` is explicit about this (`guards.py:396-398`): *"graphs agree but energies
do not, or the reverse ⟹ genuine ambiguity ⟹ `None`, never `True`."* Ruling 1 as written is a plain
conjunction. If distance passes and energy fails (or is absent — see B1), a bare `AND` yields
`False`, which under C-2/ADR-066 would be a **chemical fail** the project has ruled must be
`indeterminate` instead. → Mirror the parent comparator's three-way shape: both pass ⟹ `True`; both
fail ⟹ `False`; split, or either input missing ⟹ `None`.

**B4. 🟡 One justification in A2 is unsupported and this run's own data argues against it.** A2
explains the fix partly by *"the step immediately before a genuine successful termination is typically
smaller than mid-path cruising steps (adaptive integrators commonly shrink step size approaching a
stationary point)."* [의심 → 확인 against data] G16's IRC takes a fixed mass-weighted step by default
(`StepSize`), and the measured path is nearly uniform: 0.0582 / 0.0592 / 0.0604 / 0.0605 / 0.0538 Å —
a 12 % spread with no shrinking trend, the final step 11 % below the median rather than a fraction of
it. The forward arm is the same (0.045–0.064 Å over 19 steps). I cannot verify G16's internal
behaviour near a declared minimum without a G16 install, but the claim is asserted as general and is
not visible in the only two paths we have.
→ The **fix direction is right and unaffected** — the measured band is a sufficient anchor on its own.
Drop the adaptive-integrator rationale rather than leave an unverified mechanism load-bearing in a
gate's justification.

**B5. 🟢 Confirmed correct, no action.** A1's branch-(a) fix reads exactly as it should (both branches
converge on the same endpoint check; they differ only in how the connection is established). A3 is
genuinely resolved by A2's renumbering. A5's "per internal (redundant) coordinate" correction is
right, and proposer12's own observation that it *strengthens* the anchor is correct — no two-atom
propagation argument is needed when the threshold is already expressed on the coordinate being tested.
The A4 energies re-read independently and match: −349.620897014 / −349.620912204 Ha, Δ = −4.13e-4 eV.
The matched-method caveat is stated at the right strength.

**판정**: **FIX-THEN-RUN.** B1 must land before ruling 1 clause (ii) can be called implemented — it is
a schema/back-fill change, ~0 core-h. B2 is a one-line scoping fix. B3 and B4 are hygiene. None of
this changes the verdict on `U56_RA_scan`'s reverse arm, which passes both of ruling 1's clauses on
the numbers already measured.

**Reported to**: `proposer12` (B2/B3/B4), `coder15` (B1's schema + back-fill, B3's three-way shape),
team-lead (B1 as the one that would otherwise re-open condition 7 silently).

### 26차 배치 — 추가 3 (critic16, final pass): two residual defects in the third correction's pseudocode

B2's precedence fix, B3's three-way logic and B4's retraction are all **correct in direction**. Two
defects remain, both in the implementation-ready pseudocode coder15 was told to build from, both
one-line fixes. This is my last pass unless something new lands.

**C1. 🔴 B2's `if/else` lets the relative test *override* the absolute floor, and the class it lets
through is the one §39.116(c) explicitly predicted.** As written:

```
if len(prior_deltas) >= 3:  flag if last_step < 0.5 * median(prior_deltas)   # relative
else:                       flag if last_step <= 0.025 Å                     # absolute
```
With ≥3 prior deltas the 0.025 Å floor **stops being applied at all**. Failure scenario: a soft,
floppy path whose every step is tiny — prior deltas median 0.008 Å, declared-minimum step 0.005 Å.
`0.005 > 0.5 × 0.008 = 0.004`, so **not flagged**, even though 0.005 Å is 4× below the confirmed
artifact magnitude and the whole path has gone nowhere. That is not a hypothetical class:
§39.116(c)'s own methods flag says *"if G16's default IRC minimum-detection criterion can fire this
early on a soft-mode system, other soft/floppy Li-coordinate TS attempts in this project … may be at
risk of the same false-early-stop."* A relative test is scale-free by construction, so it cannot see
a path that is uniformly degenerate — which is precisely that predicted class.
→ **고쳐라**: `OR`, not `if/else`. The absolute floor is a floor; it should always apply.
```
flag if (last_step <= 0.025 Å)
     OR (len(prior_deltas) >= 3 AND last_step < 0.5 * median(prior_deltas))
```
Strictly safer, same cost, and it keeps RB caught by the same clause it is caught by today.

**C2. 🟡 B3's three-way pseudocode drops the covalent-graph clause — a regression against the code
already shipped.** The stated rule is over **distance** and **energy** only:
`match = True if distance_ok AND energy_ok`. But `guards.reactant_match()` as implemented
(`guards.py:539-556`) already computes `covalent_graphs_match`, and that is the **only** tolerance-free
input in the function — a differing covalent graph is an unambiguous non-match needing no ruled
number, which is exactly why the original implementation used it as its sole source of a definite
`False`. Under B3's pseudocode as written, a geometry whose graph differs (a *different* bond broke)
but whose declared break-bond distance and energy happen to agree would return **`True`**.
Energetically improbable, but the check is free and already written; removing it from the ruled form
loses the one clause that needs no tolerance at all.
→ **고쳐라**: three inputs, not two — graph mismatch ⟹ `False` outright (as today); otherwise apply
B3's three-way over distance and energy. That is also the exact shape of the parent comparator
(`bplus_agreement` = graph AND energy, with the split case ⟹ `None`), so it is consistency, not a new
idea.

**Everything else in the third correction is confirmed.** B2's core insight (the tested step must
never be inside its own reference set) is right and the `>= 3 prior deltas` gate is the right
availability condition; B3's `None`-on-split/missing mirrors `bplus_agreement` correctly and, with
B1 outstanding, correctly predicts that `match` is `None` for every input today; B4's retraction is
complete and the fix correctly now rests on the measured band alone. B1 remains the item that blocks
implementation, unchanged.

**판정, closing this batch**: **FIX-THEN-RUN.** Nothing in the R-9 plan is scheduled or submitted, no
core-h is at risk, and every outstanding item (B1's energy field + backfill, C1's `OR`, C2's graph
clause, plus the earlier tool fixes: explicit `maxpoints`, explicit 64 cores, direction-correct cost
string) is a data-plumbing or one-line change. The scientific conclusions that survived three rounds
of attack — the 4.27 arc floor, `maxpoints=30`, stage-4-first sequencing, and condition 7 binding
`last` in both branches — stand.

**Reported to**: `proposer12` (C1/C2), `coder15` (C1/C2 in implementation-ready form, since they are
building from the third correction's pseudocode), team-lead (batch close).

### 26차 배치 — 종결 확인 (critic16): fourth correction block verified, no new findings

Read §39.124's fourth correction block directly (not taken from proposer12's report). **Both fixes
are correct as written and no new defect was introduced.**

- **C1** — now `flag if last_step <= 0.025 OR (len(prior_deltas) >= 3 AND last_step < 0.5 *
  median(prior_deltas))`. Strictly more permissive in what it flags than the `if/else` form, so it
  can only catch more cases, never fewer; `U56_RB_scan` (zero prior deltas, 0.0203-0.0228 Å) is still
  caught by the absolute floor.
- **C2** — restated as the three-tier form with the covalent-graph mismatch as an unconditional,
  tolerance-free `False` ahead of the distance/energy three-way. [확인] This matches what
  `guards.reactant_match()` already ships (`guards.py:539-556`: `if not
  out["covalent_graphs_match"]: out["match"] = False`, short-circuiting before any distance is
  considered). proposer12's reading is right that the regression was in the restated prose, never in
  the built code. The `both clauses fail ⟹ False` branch is consistent with the parent comparator's
  own treatment (`bplus_agreement`, same shape, framed under ADR-066 as a bifurcation finding rather
  than a chemical fail).

**26차 배치 CLOSED at FIX-THEN-RUN.** Four correction rounds; every catch in each direction was real,
none required a re-run, and no core-h was ever at risk because nothing in the R-9 plan is scheduled.
Outstanding work is entirely with `coder15`: B1's certified-energy field plus the one-off R-A backfill
(−349.620897014 Ha, `endpoint_prep_reactant/endpoint_tight.log`, level3 `opt=tight`), C1's `OR`, C2's
three-tier form, the `/scratch` path resolution in `endpoint_certs.json`, and the three builder fixes
(explicit `maxpoints`, explicit `--total-cores 64`, direction-correct `estimated_cost`). Until B1
lands, `reactant_match` returns `None` on every real input — correct behaviour, not a passing gate.

**Scientific conclusions standing at close**: `arc >= 4.27` (reachable; reverse path ≥6.47 arc units);
`maxpoints=30` over 15 (15 clears the floor but stops ~1.7 arc units short of the minimum);
stage-4-first sequencing (the ~52-59° gradient-angle band discriminates, the terminal error message
does not — `U56_RA_qst2` is the control); condition 7 binds `last` only, in both establishment
branches. **U-56a remains OPEN**; nothing in this batch closes it.

## 2026-08-22 (27차 배치) — critic16: verification of `coder15`'s build against real output, and the R-9 close-out judgement

Lead asked three questions before calling R-9 closed: (1) does the energy extraction actually
reproduce −349.620897014 Ha; (2) are C1 (`OR`) and C2 (three-tier graph clause) really in the shipped
code; (3) does the opt-in design break anything quietly in U-56. All three answered by **running the
code against the returned tree**, not by reading `coder15`'s report.

### 🟢 (1) Energy extraction — CONFIRMED EXACT, and it fixes the path fragility too

```
$ g16.parse_scf(open('endpoint_prep_reactant/endpoint_tight.log').read())['final_energy_hartree']
-349.620897014        == the value I measured by hand in 26차 배치:  True
```
`U56.sh::resolve()` reads it from `workdir/jobs/<endpoint_key>/endpoint_tight.log` — the **same log
the certified geometry already comes from**, resolved relative to the workdir, not through
`endpoint_certs.json`'s absolute `/scratch/...` string. That is a better fix than the backfill I
asked for: it is a real extraction, it carries no hardcoded number, and it closes my earlier
`/scratch` portability nit as a side effect. **B1 is closed.** For already-returned trees the field
is regenerated on the next collect rather than needing a hand-written value — no `[FIXTURE]` risk.

### 🟢 (2) C1 and C2 — CONFIRMED, by execution

- **C1**: `MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS = 3` (`guards.py:833`) and the combination is a
  genuine `OR` — `suspicious = (delta <= floor) OR (len(prior_deltas) >= 3 AND delta <
  0.5*median(prior_deltas))`. The absolute floor is always evaluated; the `≥3 prior deltas`
  availability gate I asked for is implemented and named as a constant. `U56_RB_scan` (zero prior
  deltas) still falls to the floor and is still caught.
- **C2**: the three-tier form is shipped and behaves as ruled. Verified by running it on the real
  geometries, including the two cases the ruling is *about*:
  ```
  REAL  last vs certified reactant       match=True   graph=True  Δd=0.0005 Å  ΔE=0.000413 eV
  SPLIT distance passes, energy fails    match=None   ("a genuine SPLIT … not a guessed False")
  BOTH  clauses fail                     match=False
  graph mismatch                         match=False  (unconditional, checked before either clause)
  ```
  🔴 **Correction to my own earlier reading, recorded rather than quietly dropped**: at ~15:5x I read
  an in-flight version of this block whose first branch was `if distance_ok is False or energy_ok is
  False: match = False` and was about to report it as a spec-vs-code divergence. It had already been
  superseded by the time I executed it. Reading a file that another agent is mid-edit on is a real
  hazard of this arrangement; **executing the function is what settled it**, which is the same lesson
  as §39.76 applied to me.
- **B4**: the retracted adaptive-integrator claim is recorded as retracted at `guards.py:792`, not
  silently deleted. Correct.

**This is the first time `reactant_match` can return `True`** — my 26차 배치 C2 blocker is discharged
on the real data, with the measured margin (Δd 0.0005 Å against 0.05 Å; ΔE 4.13e-4 eV against
1e-3 eV, 1,660× below the 0.686 eV coordination-isomer scale).

### 🔴 (3) The opt-in design DOES break something quietly — one line, demonstrated

The comment at `guards.py:274-282` states the clause is skipped only when *"the caller does not
supply it at all (the key is absent, **not merely `None`-valued**)"*. The code is
`reactant_match_last = d.get("reactant_match")`, which **cannot tell those two apart.** Measured:

```
key ABSENT                    ok=True   fails=0   via='a: both directions converged'
key present, value = None     ok=True   fails=0   via='a: both directions converged'   <-- 🔴
key present, {'match': None}  ok=False  fails=1   via=None                              (correct)
key present, {'match': True}  ok=True   fails=0   via='a: both directions converged'    (correct)
```

This is not hypothetical: `U56.sh:1121-1133` builds `reactant_match = {"mid": None, "last": None,
"_status": "NOT computed: …"}` on its own exception path. A consumer that passes
`out["reactant_match"]["last"]` into the direction dict therefore passes **`None` exactly when the
check failed to run** — and the clause is skipped, and branch (a) reports
`connection_established_via = "a: both directions converged"` with **no reactant check performed**.
"Unknown is not permission" inverted, on the branch A1 was written to protect.
→ **고쳐라**, one line: `if "reactant_match" in d:` … then require `_reactant_match_ok()`. Key
present with a `None` value must **fail**, not skip.

### 🔴 The clause has no production caller — implemented, not in force

`grep` for callers of `irc_verdict` / `irc_direction_ok` across `src/`: the only production caller is
`criteria/p1.py::evaluate_p1`, which does not supply `reactant_match`. `U56.sh` **produces** the
verdict into `bplus_<direction>.json` but nothing consumes it into a C-2 verdict. So today, on every
live path, condition 7's reactant-match clause is **skipped**. That is honest opt-in and it is the
right call for P1 (permanently excluded, ADR-112) — but it means the correct statement is *"the
clause exists and is correct; nothing evaluates it yet"*, **not** "condition 7 is implemented."
`minimum_distinctness` is in the same state and `coder15` recorded that one explicitly
(`test_guard_reach.py:156` `DEFERRED_NO_CONSUMER_YET`); the `irc_direction_ok` consult path for
`reactant_match` is not recorded there and should be.

### 🟡 Stale registry entry

`tests/test_guard_reach.py:246`'s `reactant_match` entry still reads *"No distance tolerance is ruled
yet, so `match` cannot yet become True (only an outright graph bifurcation yields False)."* Both
halves are now false — the tolerance is ruled (`REACTANT_MATCH_TOLERANCE_ANG = 0.05`) and I obtained
`match=True` on real data above. A reach registry that describes the old behaviour is the exact
artefact class this project keeps being bitten by.

### 🔴 The builder fixes from 26차 배치 have NOT landed

`tools/build_u56_ra_irc_recorrect_probe.py`, current state: `total_cores=1` at `:56`,
`%nprocshared=%d` at `:115`, no `maxpoints` anywhere in the route, and `estimated_cost` at `:154-155`
still the hardcoded *"~29 remaining points at most (maxpoints=30 minus 20 already computed)"*.
**Candidate A still cannot be built safely** — at the default 1 core with `maxpoints=30` the
pessimistic branch is 46–87 h against ADR-114's 48 h cap.

### 🟢 Tests — run by me, from the right working directory

```
$ cd tests && python3 -m unittest discover -s . -p "test_*.py"
Ran 1729 tests in 110.735s
FAILED (failures=4, skipped=14)
```
The 4 are pre-existing and unrelated: 2 × `test_build_stamp` (the known un-rebuilt package, §4
RESUME (5)) and 2 × `test_session_digest` (`05_STATE.md`'s "Current phase" heading not parsing —
checked, **not** caused by my appends to this file, which is the only file I write).
`coder15`'s "4 unrelated failures" report is **accurate**. ⚠ My own first attempt ran
`discover -s tests` from the repo root and produced 9 failures including 5 in `test_bplus`; those
were entirely a working-directory artefact (`tests/context.py` and the fixture paths resolve relative
to `tests/`). Recording it so it is not mistaken for a finding, and so the next person does not
repeat it.

### 판정 — can R-9 be called CLOSED?

**NO — not yet. R-9's *planning* is closed; its *implementation* is partial and its *submission* has
not happened.** Three things must land first, none of them research and none costing core-h:

1. **The one-line opt-in fix** (`"reactant_match" in d`) — without it a failed check reads as a pass
   on branch (a), which is worse than not having the clause.
2. **A production consumer** that supplies `reactant_match` (the `last` point only) into the
   direction dict, or an explicit `DEFERRED_NO_CONSUMER_YET` entry saying there is none — pick one,
   but the current state ("wired on the consult side, no producer, not registered as deferred") is
   the one state that reads as done and is not.
3. **The three builder fixes** — explicit `maxpoints`, explicit `--total-cores 64`, direction-correct
   `estimated_cost`. Candidate A's deck is the deliverable R-9 exists to enable.

Plus the standing facts: **stage 4 has not run**, and **U-56a is OPEN**. Nothing in this batch or the
last changes that.

**What is genuinely done and should be recorded as such**: the §39.124 ruling set (four correction
rounds, all defects closed), the energy-extraction fix (B1), C1/C2 as ruled and verified by
execution, `reactant_match` returning a real `True` on real data for the first time, and D(i)'s
30.0–49.9 core-h withdrawn from the budget.

**Reported to**: team-lead (the close-out judgement), `coder15` (the opt-in one-liner, the missing
consumer/registry entry, the stale reach text, and the three still-unlanded builder fixes).

### 27차 배치 — 추가 (critic16): final execution-verification of `coder15`'s last three fixes, and the R-9 close-out ruling

All three verified by **running** the code, plus a judgement on the `shutil.copyfile` item `coder15`
correctly flagged as not being on its list.

**🟢 (1) The opt-in fix rejects the `U56.sh` error-path shape. VERIFIED.** `guards.py:290` now reads
`reactant_match_supplied = "reactant_match" in d`, separately from the value. Measured across both
branches:

```
(a) key ABSENT             ok=True   fails=0  tags=[]           via='a: both directions converged'
(a) key present = None     ok=False  fails=1  tags=['unknown']  via=None      <-- the U56.sh shape
(a) {'match': None}        ok=False  fails=1  tags=['unknown']  via=None
(a) {'match': False}       ok=False  fails=1  tags=['chemical'] via=None
(a) {'match': True}        ok=True   fails=0  tags=[]           via='a: both directions converged'
(b) key present = None     ok=False  fails=1  tags=['unknown']  via=None
(b) {'match': True}        ok=True   fails=0  tags=[]           via='b: maxpoints + B+ agreement'
```
Exactly right: absent ⟹ opt out; present-but-`None` ⟹ **fail**, tagged `unknown` (not `chemical` —
correct, an absent measurement is not a chemical finding); `False` ⟹ fail tagged `chemical`. Both
branches behave identically, which is A1's whole point.

**🟢 (2) The three builder fixes landed, and the direction keyword was NOT touched. VERIFIED.** Ran
the builder for both directions:

```
forward  %nprocshared=64 | irc=(restart,recorrect=never,maxpoints=30) | "~10 remaining (30 minus 20)"
reverse  %nprocshared=64 | irc=(restart,recorrect=never,maxpoints=30) | "~24 remaining (30 minus 6)"
```
- `total_cores=64` is the default (`:93`) — the 46–87 h wall exposure against ADR-114's 48 h cap is
  gone; at 64 cores the same worst case is ~1.4 h.
- `maxpoints=30` is written into the route as a named constant `IRC_RESTART_MAXPOINTS` with the
  ruling's own provenance attached, so proposer12's decision no longer depends on silent checkpoint
  inheritance. The `recorrect=never` grep stays mandatory for the *other* option, unchanged.
- The cost string is direction-aware and the old internal contradiction ("~29" against its own
  "30 minus 20") is gone; both arithmetic values are now correct.
- 🟢 **No `direction` keyword in the route** — `irc=(restart,recorrect=never,maxpoints=30)` — and
  `:130-132` records *why* not, citing the unsmoked-restart hazard. This is what I asked for: the
  correct fix was to leave it out and verify direction from the restart log instead (first
  `NET REACTION COORDINATE` must resume at ≈1.706, break bond ≈1.41 and not increasing).

**🟢 (3) The no-producer gap is documented where it will actually be read. VERIFIED.**
`test_guard_reach.py`'s `EXPECTED_REACHED["irc_verdict"]` reason string now states that
`irc_direction_ok`'s `direction["reactant_match"]` consult **has no live producer** —
`evaluate_p1` is the only caller and does not supply the key, so the clause is skipped on every
production path that exists today. Putting it there rather than in `DEFERRED_NO_CONSUMER_YET` is the
right call and `coder15` explains why (`irc_direction_ok` itself *is* reached, so it cannot carry a
deferred entry of its own). The stale `reactant_match` registry text I flagged at `:246` is also
fixed and now records the verified `True`.

**🟢 Tests, run by me** — `cd tests && python3 -m unittest discover -s . -p "test_*.py"` →
**Ran 1737 tests, FAILED (failures=4, skipped=14)**, the same four pre-existing and unrelated
(2 × `test_build_stamp`, the known un-rebuilt package; 2 × `test_session_digest`, `05_STATE.md`'s
"Current phase" heading). `coder15`'s report is accurate.

### Judgement on the `shutil.copyfile` overwrite guard (my 26차 배치 N1)

**What it is**: `build()` does `shutil.copyfile(src_chk, dst_chk)` (`:109`) with no guard, while the
module docstring (`:29-30`) claims *"Re-running is idempotent (the source .chk is copied, never
mutated)."* Idempotent for the **source**, yes. But re-running the builder into an `--out-dir` where
the probe has **already run** silently overwrites `irc_<dir>_recorrect_probe.chk` — which by then is
no longer a copy of the input, it is the **restart's own progressed IRC path**, the single artifact a
further restart would build on.

**Does it block R-9 CLOSED? NO.** Reasoning, so the decision is auditable rather than a shrug:
- The tool submits nothing, and the destructive sequence needs three steps in order: build → run →
  re-build into the *same* directory. The project's actual workflow does not do this — decks are
  built into `u56_diagnostics_resubmit_*/`, shipped, and run in the **job's** directory on the
  cluster; returned results land under `cpu_machine_pilot_results/`, which standing rule already
  makes read-only and which is never an `--out-dir`.
- The loss, if it did happen, is **recoverable and bounded**: a re-run of candidate A, 17.3–32.7
  core-h at 64 cores, ~1.4 h wall. It cannot produce a **wrong scientific answer**, only a repeated
  cost — which is the Tier-2 class, not Tier-1.
- Nothing in the R-9 deliverable set (ruling, pricing, the code the ruling triggered, a safely
  buildable deck) depends on it.

**But it should be fixed as its own item, and here is why it is not merely cosmetic**: the project's
standing restriction is *"never delete files without the user's permission."* A silent overwrite of a
progressed checkpoint is a deletion in effect, performed by a tool whose own docstring tells the
reader it cannot happen. That combination — a destructive default plus documentation asserting
safety — is what makes it worth three lines rather than zero: refuse when `dst_chk` exists and
differs from `src_chk`, unless an explicit `--force`. → **Tracked as a separate, low-priority item.
Not an R-9 blocker.**

### 판정 — R-9: CLOSED (with three named carry-overs)

**Yes, R-9 can be declared CLOSED.** Everything R-9 was scoped to deliver is done and independently
verified by execution:
- the ruling set — `§39.124` plus four correction rounds, every defect closed, nothing outstanding;
- the pricing — `§R39.81`, with D(i)'s 30.0–49.9 core-h withdrawn once its motivating finding was
  falsified;
- the `src/` changes the ruling triggered — `reactant_match` (returning a real `True` on real data),
  its both-branch consult with the opt-out that cannot be tripped by a failed measurement, the
  certified-energy extraction, `minimum_distinctness`, and the three builder fixes;
- a deck that can now be built safely, at the ruled cap, on the priced core count, without the
  unsmoked direction keyword.

🔴 **"CLOSED" must not be read as "candidate A is ready to submit."** Three things carry over, and
they belong to U-56a and to the tool, not to R-9:
1. **`reactant_match` has no live producer** into `irc_direction_ok`. Registered in the reach
   registry. The values *are* computed and written to `bplus_<direction>.json`, so a human evaluating
   condition 7 today has the numbers; what does not exist is an automated U-56 verdict function to
   consume them. Wire it when that function is built.
2. **`minimum_distinctness` is unwired**, registered as `DEFERRED_NO_CONSUMER_YET` — correct, since
   ruling 3 is a human-read prescription and no caller supplies path-frame geometry.
3. **The `shutil.copyfile` overwrite guard**, per the judgement above.

And the standing facts, unchanged by anything in this batch: **candidate A's deck is BUILD-NOW /
SUBMIT-GATED on stage 4's result**, **stage 4 has not run**, and **U-56a is OPEN**.

**Reported to**: team-lead (the CLOSED ruling and the three carry-overs), `coder15` (all three fixes
verified, nothing further requested).

---

## 2026-08-24 (28차 배치) — critic (critic17, successor to critic16): `coder16`'s idempotency fix (§1f carry-over 3) — the guard is real, but it covers only half the out-dir and is not in the shipped package

**Target**: `src/pilot_package/tools/build_u56_ra_irc_recorrect_probe.py` (the `dst_chk` clobber
guard, exit code 5, corrected docstring) and `tests/test_u56_ra_irc_recorrect_probe.py`
(`test_rerun_into_same_out_dir_refuses_to_clobber_existing_checkpoint`). Everything below is
re-derived from the files and from execution, not from `coder16`'s summary.
Abbreviations used here: **R-9** = the review round on §39.124's reverse-IRC arm, closed by
critic16 on 2026-08-22; **R-10** = the known pre-existing `test_session_digest` failure, not
chased here; **§1f carry-over 3** = `docs/05_STATE.md`'s third open carry-over, the false
idempotency claim in this tool; **candidate A** = the restart-from-checkpoint IRC run this tool
builds a deck for; **ADR-114** = the 48 h wall-clock cap.

## 판정
**FIX-THEN-RUN** — the fix itself is correct and does what its docstring says. Two reachable
clobber/lockout paths it does not close, and one deployment fact, must be handled before candidate
A is actually built. Nothing here reopens R-9.

## 치명적 (결과가 틀림 / 배포되지 않음)

- `src/pilot_package/tools/build_u56_ra_irc_recorrect_probe.py:118` — **[확인]** the `.chk` is
  copied **before** the three remaining failure returns (`return 2` unknown level at `:126`,
  `return 4` solvent refusal at `:132`, `return 3` basis error at `:166`). Any build that fails
  after the copy leaves `dst_chk` behind, and the corrected retry into the same `--out-dir` is then
  refused with a message that asserts something false.
  → Executed: `--level 99` into a fresh out-dir gives `unknown level: 99`, `rc=2`, and leaves
  `irc_forward_recorrect_probe.chk` (7 bytes) in the out-dir; the immediate rerun with `--level 3`
  prints `refusing to overwrite existing checkpoint ... -- a prior restart may have progressed it
  past this fresh copy` and returns 5. No restart ever ran; nothing was progressed. An operator who
  believes the message will now go hunting for a G16 run that does not exist, or will `rm` a file
  the tool told them might be precious.
  → Fix: copy the checkpoint **last** (keep the `os.path.exists(dst_chk)` refusal where it is, move
  the `shutil.copyfile` to just after the `.gjf` is written), so a build that cannot produce a deck
  leaves no state behind. Shortest correct diff; no new flags, no cleanup handler.

- `src/pilot_package/tools/build_u56_ra_irc_recorrect_probe.py:169,206` — **[확인]** the guard is
  keyed on `chk_name`, which **is** direction-specific (`irc_%s_recorrect_probe.chk`), but the two
  other outputs are **not**: `gjf_path` is the fixed `irc_recorrect_probe.gjf` and the manifest is
  the fixed `manifest.json`. Both are still written unconditionally. So the exact bug §1f
  carry-over 3 names — "a rebuild into a used out-dir silently destroys something already paid
  for" — survives across directions.
  → Executed: `--direction forward` into a fresh out-dir (`rc=0`, deck carries
  `%chk=irc_forward_recorrect_probe.chk`), then `--direction reverse` into the **same** out-dir:
  `rc=0`, no warning, the deck now carries `%chk=irc_reverse_recorrect_probe.chk` and
  `manifest.json`'s `"direction"` flipped to `reverse`. The forward deck and its manifest are gone;
  `irc_forward_recorrect_probe.chk` remains, orphaned.
  → Why this costs real core-hours: the runner `u56_diagnostics_resubmit_2026-08-22/
  submit_stage4.pbs:15` executes `g16 < irc_recorrect_probe.gjf` **by fixed filename** inside
  `4_irc_recorrect_restart/`. An operator who builds both directions into that one dir and submits
  runs the **reverse** restart while believing they submitted forward — a wrong-direction IRC at
  `maxpoints=30` (engineer13's own sizing: tens of core-h, up to ADR-114's 48 h wall) and a
  diagnostic answer attributed to the wrong arm.
  → Fix: make the deck and manifest direction-specific too (`irc_%s_recorrect_probe.gjf`,
  `manifest_%s.json`) **or** refuse when either already exists. If the deck filename changes,
  `submit_stage4.pbs`'s fixed `irc_recorrect_probe.gjf` must change with it — do not change one
  without the other.

## 중대 (낭비/재현불가)

- `tests/test_build_stamp.py:131` — **[확인]** the shipped tarball is stale and its own failure
  message now names this very file: `변경: tools/build_u56_ra_irc_recorrect_probe.py` (alongside
  `payload/BPLUS_REOPT.sh`, `payload/U56.sh`, `payload/endpoint_prep.sh`, `sei_pilot/cli.py`,
  `sei_pilot/guards.py` — the coder15 residue). This is correctly called "known-red", but its
  consequence is not cosmetic: **the idempotency guard is not in the artefact that ships to the
  HPC.** §1f carry-over 3 says the guard "must land before candidate A is actually built"; on the
  package as it stands today, it has not landed. `src/make_package.sh` must be re-run and the new
  package hash independently verified (as critic14 did for `a7b668127d052e33`) before candidate A
  is built from a deployed package. Not a defect in coder16's diff; a gate on using it.

## 사소

- `build_u56_ra_irc_recorrect_probe.py:97` — `os.makedirs(out_dir, exist_ok=True)` runs before
  every check, so even `--job-dir` with no checkpoint (`return 2`) leaves an empty out-dir behind.
  Harmless; folds into the "copy last" fix if that is done tidily.
- Exit codes are not documented anywhere in the tool (`2` = missing input / unknown level, `3` =
  basis, `4` = solvent, `5` = existing checkpoint). No caller reads them today (see below), so this
  is a note, not a defect.

## 확인한 것이 깨끗한 항목 (negative results, reported as required)

- **Exit code 5 is genuinely free.** `grep -n "return [0-9]"` over the file gives exactly
  `2,2,5,2,4,3,0` — `5` is used once and collides with nothing in this tool's space. **[확인]** And
  a collision could not have been silent-but-harmless-by-luck either: **no programmatic caller
  exists**. Nothing in `src/` or in any `.sh`/`.pbs` invokes this builder; the only non-`tests/`
  mentions are two prose references inside `build_u56_ra_stability_probe.py:35,223`. The `.pbs`
  files run `g16` on an already-built deck, never the builder. So exit codes reach a human shell
  only. No dispatch to break. **OK.**
- **Docstring is accurate and does not overclaim.** `:28-32` now says re-running into the same
  `--out-dir` "is **NOT** idempotent" and that `build()` "refuses to overwrite it" — both true as
  written, and it is the honest inverse of the false-assurance pattern that produced this bug and
  the opt-in bug before it. It does not claim a safety property the code lacks. Its one gap is by
  omission, not assertion: it says nothing about the deck/manifest still being overwritten, which
  is the 치명적 item above. **OK, revisit wording when that item is fixed.**
- **The test double is legitimate and it discriminates.** The guard is `os.path.exists`, so `.chk`
  content is irrelevant to the code path; hand-written bytes are a fair proxy. Applying "agreement
  is not identity": the test asserts nonzero return, `refusing to overwrite` on stderr, **and**
  byte-for-byte preservation of the file it planted — if the code still clobbered, all three would
  read differently (`rc=0`, empty stderr, bytes equal to the fresh source copy). It is not a test
  that passes either way. **OK.**
  The raised edge cases do not need separate tests: zero-length, half-written and byte-identical
  destinations all hit the same content-independent `exists` branch and all refuse, which is the
  conservative and correct outcome — a partially-copied `.chk` is exactly the file you least want
  overwritten silently, and refusing costs one `rm`. The genuinely untested case is not any of
  those; it is the **failed-build leftover** (치명적 item 1), where refusal is wrong.
- **Scope discipline is clean.** **[확인]** `find src tests docs -newermt 2026-08-23 -type f`
  returns only `tests/test_u56_ra_irc_recorrect_probe.py`,
  `src/pilot_package/tools/build_u56_ra_irc_recorrect_probe.py`, `docs/05_STATE.md` (the lead's own
  edit) and a `__pycache__` artefact. `guards.py`, `test_bplus.py`, `02_METHOD_SPEC.md` and
  `03_COMPUTE_PLAN.md` all still date 2026-08-22. Nothing under R-9 and neither unscoped carry-over
  (`reactant_match` producer, `minimum_distinctness` wiring) was touched. **OK.**

## 테스트 상태 (independently executed, not inherited)

- `python3 -m unittest test_u56_ra_irc_recorrect_probe -v` → **9 tests, OK**, including the new one.
- `python3 -m unittest discover -s tests -p "test_*.py"` → **Ran 1738 tests in 94.6s, FAILED
  (failures=3, skipped=14)**. `pytest` is not installed in this environment; `unittest` is the runner.
- Composition of the 3: `test_build_stamp.TestBuildStamp.test_real_repo_dist_is_fresh` and
  `test_build_stamp.TestWrongRootIsNotReportedAsStale.test_correct_root_still_verifies` (the two
  known stale-tarball reds, see 중대 above), plus
  `test_session_digest.TestAgainstRealDocs.test_real_render_does_not_crash_and_stays_short` (R-10,
  pre-existing, untouched by this diff, not chased here per the lead's instruction).
- This is consistent with coder16's reported 1738/4 given the lead's same-day `05_STATE.md` header
  fix closing one of the two `test_session_digest` failures. Test count matches exactly.

## 확인하지 못한 것

- Whether `IRC(Restart)` + `Geom=Check Guess=Read` + `maxpoints=30` is accepted by the target G16
  build. Unchanged by this diff and already flagged `[NEEDS VERIFICATION]` in the tool and manifest;
  no G16 install here to smoke it.
- Whether the operational workflow would ever in fact build both directions into
  `4_irc_recorrect_restart/`. I confirmed the mechanism and the fixed filename in
  `submit_stage4.pbs`; I did not find a written procedure either forbidding or prescribing it.
  Treated as reachable because §1f carry-over 3's own scenario is a human rerunning a build into a
  used out-dir.

**Reported to**: `coder16` (the two 치명적 items with reproduction commands), team-lead (verdict
FIX-THEN-RUN, and the stale-package gate before candidate A is built).

---

## 2026-08-24 (29차 배치) — critic17: recheck of `coder16`'s follow-up to the 28차 batch (copy-ordering + cross-direction guard only)

**Scope**: narrow recheck requested by the lead — the two 치명적 items from the 28차 batch, nothing
else. Not a re-review of the tool. Both re-derived by execution, not from `coder16`'s summary.

## 판정
**OK** — both defects are closed. No new defects. Verdict for the tool moves 28차's FIX-THEN-RUN →
**OK**, with the packaging gate (`src/make_package.sh` rebuild) still outstanding and unchanged.

## 두 항목 재검증

- **Item 1 (copy-before-validation self-lockout) — CLOSED. [확인]** `shutil.copyfile` moved to
  `:187`, after the level (`:139`), solvent (`:145`) and basis (`:179`) checks; the three-path
  exists-guard stays up front at `:113-124`. Executed the original repro: `--level 99` into a fresh
  out-dir gives `unknown level: 99`, `rc=2`, and the out-dir is now **empty** (`[]`, previously held
  a 7-byte checkpoint); the immediate `--level 3` retry into that same out-dir returns **rc=0**.
  The false "a prior restart may have progressed it" refusal is gone, and the new message wording
  ("a prior build (possibly a different `--direction`) may have progressed **or relied on** it") is
  accurate for all three guarded paths — it no longer asserts progression as fact.
- **Item 2 (cross-direction deck/manifest clobber) — CLOSED. [확인]** The guard now covers
  `dst_chk`, `gjf_path` and `manifest_path` together. Executed the original repro: forward build
  `rc=0`, then `--direction reverse` into the same out-dir returns **rc=5** naming
  `irc_recorrect_probe.gjf`; `md5sum` of the deck is byte-identical before and after
  (`7fde64380618e678a918a42ba50fbbd1`), `manifest.json`'s `"direction"` is still `forward`, and no
  reverse checkpoint was created — the out-dir is untouched. The `submit_stage4.pbs:15`
  wrong-direction submission path is therefore unreachable through this builder.
  `coder16` chose the guard over renaming the deck/manifest specifically to avoid touching
  `submit_stage4.pbs` and the already-built out-dir. **That is the correct call** and the one I
  would have preferred: the rename would have coupled a source fix to a shipped artefact and an
  operator-facing filename, for no additional safety.

## Do the new tests discriminate? (agreement is not identity)

- `test_building_the_other_direction_into_the_same_out_dir_is_refused_not_silent` — yes. It asserts
  nonzero return, the stderr string, **and** the deck's contents unchanged; under the old code all
  three read differently (`rc=0`, empty stderr, replaced deck). It would not pass either way.
- `test_a_failed_build_leaves_no_checkpoint_for_the_corrected_retry_to_trip_over` — yes for what it
  asserts (`dst_chk` absent after a failed build; under the old code the file existed), but see the
  사소 note below: it stops one step short of the behaviour it is named for.

## 사소 (no action required)

- `tests/test_u56_ra_irc_recorrect_probe.py` — the failed-build test asserts only the **precondition**
  (no leftover checkpoint), not the **outcome** (`coder16`'s message says it "reproduces repro 1:
  `--level 99` then a clean retry succeeds", but the test never runs the retry). The absence
  assertion is the load-bearing half and the outcome is what actually matters to an operator; I
  verified `rc=0` on the corrected retry by execution instead. Two lines (`proc2 = self._run();
  assertEqual(proc2.returncode, 0)`) would close the gap if the file is touched again — not worth a
  commit on its own.
- `build_u56_ra_irc_recorrect_probe.py:187` — the copy still precedes the deck/manifest **writes**,
  so an I/O failure mid-write (disk full, permissions) would leave `dst_chk` plus a partial deck and
  the retry would be refused. Materially different from the fixed bug — that is real leftover state
  from a real partial run, where refusing is the defensible default. Noted, not a defect.
- **Operational consequence worth stating once**: the guard now refuses a rebuild into ANY out-dir
  that already holds a deck or manifest, including the populated
  `u56_diagnostics_resubmit_2026-08-22/4_irc_recorrect_restart/`. That is intended and documented,
  but it means candidate A must be built into a **fresh** directory (and `submit_stage4.pbs` pointed
  at it), or the old files removed deliberately. Nobody should meet this for the first time at
  build time.

## 테스트 상태 (independently executed)

- `python3 -m unittest test_u56_ra_irc_recorrect_probe` → **Ran 11 tests, OK** (was 9; +2 new).
- `python3 -m unittest discover -s tests -p "test_*.py"` → **Ran 1740 tests in 94.7s, FAILED
  (failures=3, skipped=14)** — identical composition to the 28차 batch: the two known
  `test_build_stamp` stale-tarball reds and the pre-existing `test_session_digest.TestAgainstRealDocs`
  render-length failure (R-10, not chased). Matches `coder16`'s report exactly, count included.
- **Scope clean. [확인]** `find src tests docs -newermt "2026-08-24 00:00" -type f` (minus
  `__pycache__`) returns only the tool, its test, `docs/05_STATE.md` (lead) and `docs/04_REVIEW_LOG.md`
  (mine). `submit_stage4.pbs` and `u56_diagnostics_resubmit_2026-08-22/` untouched, as stated.

**Still open, unchanged by this batch**: the shipped tarball remains stale and still lists
`tools/build_u56_ra_irc_recorrect_probe.py` among the changes not in the package — the guard is not
in the deployed artefact until `src/make_package.sh` is re-run. Lead has ruled this non-blocking
while candidate A stays gated behind stage 4; it becomes blocking the moment candidate A is built
from a deployed package.

**Reported to**: team-lead (verdict OK, both items closed, packaging gate restated), `coder16`
(both fixes verified by execution, one two-line test suggestion, no rework requested).

---

## 2026-08-25 (30차 배치) — critic17: candidate A staging recheck (`candidate_a_reverse_2026-08-25/`)

**Scope**: the staged, NOT-submitted candidate A deck (reverse-arm `recorrect=never` IRC restart)
built by `coder16` with the existing, already-reviewed tool. No source code changed this round.
Seven points requested by the lead; all re-derived by execution here. Abbreviations: **candidate A**
= the reverse-arm restart ruled by proposer12 §39.124 and unblocked by proposer13 §39.125(3);
**§R39.81** = engineer13's pricing section in `03_COMPUTE_PLAN.md`; **ADR-114** = the 48 h wall cap;
**ADR-117** = the silent-override/harness-mismatch class of failure.

## 판정
**FIX-THEN-RUN** — the deck, the PBS script and the checkpoint are submit-ready and every number
checks out. **One defect in `README.md`'s mandatory post-run check makes that check unable to fail**,
which matters because it is the only gate standing between a returned log and a wrong scientific
conclusion. Fix the one line before the directory goes to the user; the job itself can be submitted
as staged.

## 치명적 (the check that cannot fail)

- `candidate_a_reverse_2026-08-25/README.md`, "AFTER the run — mandatory check" — **[확인]** the
  command is `grep -c "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log`,
  **without `-a`**. These G16 logs are binary-flagged (`file` on the returned stage 4 log reports
  `data`), and on a binary-flagged file the plain form does not report counts at all.
  → Measured on the real returned stage 4 log
  (`u56_diagnostics_resubmit_2026-08-22/4_irc_recorrect_restart/irc_recorrect_probe.log`), this
  machine's `grep` being `ugrep 7.8.4`:

        pat=[Recorrection delta-x convergence threshold:]  plain: out=[] rc=1  |  -a: out=[0] rc=1
        pat=[Bulirsch]                                     plain: out=[] rc=1  |  -a: out=[4] rc=0

  The control pattern **occurs 4 times** and the plain form still prints nothing and returns 1 —
  **byte-for-byte the same operator-visible result as the pattern that occurs zero times.** An
  operator running the README's command sees no output either way and reads it as "the line is
  absent, `recorrect=never` took effect." If `recorrect=never` were in fact silently dropped
  (critic15's original catch, §R39.81's own flagged ADR-117-class risk, the exact reason this check
  exists), this check would say nothing was wrong. A repeat crash would then be reported as evidence
  against the integrator hypothesis when it is a false negative — the failure the README's own next
  sentence warns about.
  → This is not a novel discovery about the environment either: **§39.125's own opening paragraph —
  the section this README cites — records it** ("they are binary-flagged, plain `grep` returns false
  zero matches — confirmed the hard way"), and proposer13's own run used `grep -ac`. The README
  shipped the form the project already knows fails.
  → **Fix**: `grep -ac "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log`. One
  character. Worth also stating the expected result inline (`0` = the option took effect, any
  nonzero = it did not, **no output at all = you dropped the `-a`**), since "no output" is precisely
  the ambiguous state that caused this.
  → **[의심]** on the cluster specifically: GNU `grep -c` may print the count where this machine's
  `ugrep` does not, so the check might happen to work there. That does not rescue it — the project's
  own on-record experience with these exact logs is false zero matches from the plain form, and the
  README must not ship a command whose correctness depends on which `grep` the login node has.

## 요청 항목별 판정 (items 1-7)

1. **`maxpoints=30` explicit — OK. [확인]** Read out of the deck's own route text, not merely
   present as a substring: `irc_recorrect_probe.gjf` line 4 is
   `#p nosymm wB97XD/gen scrf=(pcm,solvent=acetone,read) geom=check guess=read
   irc=(restart,recorrect=never,maxpoints=30) Int(Grid=UltraFine)`. `30` equals the tool's ruled
   constant (`IRC_RESTART_MAXPOINTS = 30`, `:71`) and equals the **original** reverse job's own cap
   (`U56_RA_scan/irc_reverse.gjf`: `irc=(calcfc,reverse,maxpoints=30)`). No other value appears
   anywhere in the staged directory, so the explicit-vs-inherited question proposer13 raised in
   §39.125(2) is moot here in the safest possible way: both readings give 30.
2. **64 cores — OK, all three agree. [확인]** `%nprocshared=64` (deck line 1),
   `#PBS -l select=1:ncpus=64:mpiprocs=1:ompthreads=64` (`submit_candidate_a.pbs:6`), and
   `manifest.json`'s recorded `invocation` ends `--direction reverse --total-cores 64`. This
   satisfies §R39.81 item 2's stated *requirement* (both the builder flag and the PBS request, not
   one or the other) — and is a real improvement on stage 4's own script, which requested
   `ncpus=1` with a `%nprocshared=1` deck.
3. **Checkpoint integrity — OK, verified by re-running the hashes. [확인]**
   `md5sum` of `U56_RA_scan/irc_reverse.chk` (source) and of the staged
   `irc_reverse_recorrect_probe.chk` both give **`7b4557b055f95d1ece2fb05851f8e037`**, matching
   coder16's reported value. Source mtime is `2026-08-21_18:09:55`, i.e. untouched by the
   2026-08-25 build. I also checked it is not a lookalike: the other two reverse checkpoints in the
   tree hash differently (`U56_RA_qst2` `3edfe2d5...`, `U56_RB_scan` `64347957...`), as does
   `U56_RA_scan/irc_forward.chk` (`87a378633c55f4df0021f133943cfe97`) — the file copied is the one
   the manifest names and no other.
4. **Walltime — OK, and it survives a check the citation does not make. [확인]** Arithmetic first:
   24 new points x 1.92-3.63 core-h/pt = 46.08-87.12 core-h; /64 cores = 0.72-1.36 h; 8 h / 1.36 h =
   **5.88x**. All as claimed, trivially inside ADR-114's 48 h.
   The load-bearing risk in a core-h/64 conversion is parallel efficiency — an 11-atom wB97XD job
   need not scale to 64 cores, and if the per-point anchor had been measured single-threaded, the
   real wall could have approached the 8 h cap. **It was not**: the original reverse run
   (`U56_RA_scan/irc_reverse.gjf`) itself ran at `%nprocshared=64`, and its own log's closing lines
   give `Job cpu time: 0 days 16 hours 59 minutes 2.4 seconds` against `Elapsed time: 0 days 0 hours
   20 minutes 24.8 seconds` — 16.98 core-h over 0.34 h wall, i.e. **~78% parallel efficiency already
   baked into the anchor**. Those 16.98 core-h over 6 points give **2.83 core-h/pt**, inside
   engineer13's 1.92-3.63 bracket, and 24 points at that run's measured 0.057 h/pt wall gives
   **1.36 h** — reproducing the cited pessimistic ceiling exactly, from the reaction's own log
   rather than from the pricing document. The estimate is additionally conservative because the
   anchor includes the original run's `calcfc` frequency calculation, which a restart does not
   repeat. **8 h is a sound, generous choice.**
5. **Direction-aware `estimated_cost` — OK, no regression. [확인]** `manifest.json` reads
   `"~24 remaining points at most (maxpoints=30 minus 6 already computed and stored)"` with
   `"direction": "reverse"` — reverse's own 6, not forward's 20. This is the exact string
   `test_maxpoints_is_written_for_the_reverse_direction_too` asserts, now confirmed on a real
   artefact rather than a fixture.
6. **README — one defect (치명적, above); everything else accurate. [확인]** The mandatory-grep
   *rationale* is right (silent-override risk, "treat a repeat crash as a false negative, not
   evidence"), the `candidate_a_kill.marker` note is present and correctly hedged (`[ASSUMPTION]` on
   the SIGTERM grace window, matching the marker the PBS `trap` actually writes), the "Do NOT run
   `./run.sh --submit`" instruction matches the stage3/4/probe5 precedent, and the stopping-condition
   note correctly labels the maxpoints-explicitness improvement as **"a prediction, not yet a
   measurement."** The provenance block's reproduction command matches `manifest.json`'s recorded
   `invocation`. Only the command itself is wrong.
7. **Scope — coder16 clean, but the lead's premise needs one correction. [확인]**
   `find -maxdepth 2 -newermt "2026-08-24 12:00"` returns `candidate_a_reverse_2026-08-25/` (all 5
   files, 10:00-10:01), `docs/02_METHOD_SPEC.md` (proposer13), `docs/05_STATE.md` (lead) and
   `docs/04_REVIEW_LOG.md` (mine) — nothing under `src/` or `tests/`, consistent with "no code
   changed this round."
   **However `u56_diagnostics_resubmit_2026-08-22/` is NOT untouched**: every file in it carries
   mtime `2026-08-25_09:45:37-42`, ~15 minutes *before* candidate A was staged. It now contains
   `4_irc_recorrect_restart/irc_recorrect_probe.log` (59,896 bytes, the returned stage 4 result),
   and that directory's `irc_forward_recorrect_probe.chk` now hashes `ca8e724c059321bd34b27d11aa83d6b6`
   — **no longer equal to its source** `U56_RA_scan/irc_forward.chk` (`87a378...`), i.e. the run
   progressed it, exactly as expected. This is the cluster copy-back, not a coder16 edit, and it is
   worth noting for one reason: it is a live instance of the state the new guard protects — that
   out-dir now holds a progressed checkpoint plus a deck and a manifest, and the builder will (and
   should) refuse to rebuild into it.

## 사소

- `submit_candidate_a.pbs:7-9` cites `03_COMPUTE_PLAN.md:19199-19228` for "46.1-87.1 core-h". That
  line range is the **withdrawn** `maxpoints=15` block, which states `9 pts x 1.92-3.63 = 17.3 -
  32.7 core-h`. The 24-point figures the comment actually quotes come from engineer13's item 2 at
  ~`19357-19365`. A reader following the citation lands on numbers that contradict the quoted ones
  and could reasonably conclude the walltime was sized off the withdrawn 9-point plan. The numbers
  are right; the pointer is not. Fix: cite `19357-19365` (the README's prose form, "§R39.81's full
  maxpoints=30/24-new-point outer bound", is already unambiguous and needs no change).
- `manifest.json`'s `purpose`/`question` fields still carry the tool's stock text describing this as
  the hypothesis "competing with `build_u56_ra_stability_probe.py`'s wavefunction-instability
  hypothesis" — that competition was resolved (§39.125(1): closed in substance). Tool-generated
  boilerplate, not coder16's writing, and the README carries the current framing; noted so nobody
  cites the manifest as a live statement of the open question.

## 확인하지 못한 것

- Whether the cluster's `grep` behaves like this machine's. Stated as `[의심]` above; it does not
  change the fix.
- G16 restart semantics for `maxpoints` (30 total vs 30 new). Unresolvable here, and **moot for this
  deck** — the checkpoint's inherited cap and the deck's explicit keyword are both 30, so the two
  readings differ only in whether 24 or 30 new points are budgeted, and 8 h covers both (30 pts x
  3.63 = 108.9 core-h = 1.70 h at 64 cores, still a 4.7x margin).
- Whether the route is valid on the reverse direction specifically. Unsmoked, correctly disclosed in
  the manifest's `route_syntax_status` and in §R39.81's ADR-117-class flag; a malformed route dies at
  ~zero cost.

**Reported to**: team-lead (verdict FIX-THEN-RUN, the one README fix, the miscited line range, and
the correction to the "resubmit dir untouched" premise), `coder16` (both fixes, with the measured
grep evidence).

---

## 2026-08-25 (31차 배치) — critic17: confirmation of the two candidate A staging fixes

**Scope**: narrow. Only the two items raised in the 30차 batch. Verified against the files, not
against `coder16`'s report.

## 판정
**OK — SUBMIT-READY.** Both fixed correctly. No new defects. The 30차 verdict moves
FIX-THEN-RUN → **OK**; nothing further from me blocks `qsub`.

- **Mandatory post-run check — FIXED. [확인]** `README.md:64` is now
  `grep -ac "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log`, and `:66-73`
  spell out all three outcomes explicitly, including the one that caused the defect: *"A blank
  result is NOT '0 matches' — it means `-a` was dropped and the check must be rerun correctly before
  it is trusted either way."* The three-way reading (blank = broken check, `0` = took effect,
  `>0` = did not, treat a repeat crash as a false negative) is the correct decision table and is
  stated in the order an operator meets it. The check can now fail, which was the entire point.
- **Pricing citation — FIXED. [확인]** `submit_candidate_a.pbs:8-10` now cites
  `03_COMPUTE_PLAN.md:19357-19365` and names the withdrawn block explicitly as excluded ("NOT the
  withdrawn 19199-19228 9-point/maxpoints=15 block"). Better than what I asked for: a reader who
  encounters the old range elsewhere is now warned off it rather than merely pointed away.
- **Nothing else moved. [확인]** `irc_recorrect_probe.gjf`, `irc_reverse_recorrect_probe.chk` and
  `manifest.json` all still carry mtime `2026-08-25_10:00:36`; only `README.md` (10:07:14) and
  `submit_candidate_a.pbs` (10:07:34) changed. Re-verified after the edits: the checkpoint still
  hashes **`7b4557b055f95d1ece2fb05851f8e037`** and the route line is unchanged
  (`%nprocshared=64`, `%chk=irc_reverse_recorrect_probe.chk`,
  `irc=(restart,recorrect=never,maxpoints=30)`). The documentation fixes did not disturb the
  scientific payload.

## 사소 (no action)

- `README.md:66-68` states as a general fact that plain `grep` on a binary-flagged file gives "no
  output at all, not even `0`". That is what I measured on this machine (`ugrep 7.8.4` in the `grep`
  position); GNU `grep -c` on the cluster may well print the count instead. The claim is therefore
  machine-specific, but the **instruction** it supports is correct on every implementation, and the
  error direction is safe — it pushes the operator to the form that works everywhere. Not worth an
  edit; noted only so a future reader does not cite this line as a portable fact about `grep`.
- `manifest.json` boilerplate (wavefunction hypothesis described as a live competitor) left as-is by
  agreement — it is the tool's standard text, not staging-specific, and changing it would be a tool
  edit outside this task. The README carries the current §39.125(1) framing where a reader needs it.
  I concur with that call.

**Reported to**: team-lead (OK, submit-ready), `coder16` (both confirmed).

**Addendum (same batch)** — `candidate_a_reverse_2026-08-25.tar.gz` (10:07:55, appeared during this
review) checked against the working directory, since a **stale tarball is this project's own
recurring failure mode** (`test_build_stamp`'s standing red). All five members hash identical to the
post-fix files on disk: `README.md` `d5229433...`, `submit_candidate_a.pbs` `3bc35d38...`,
`irc_recorrect_probe.gjf` `3fe3d107...`, `irc_reverse_recorrect_probe.chk`
`7b4557b055f95d1ece2fb05851f8e037`, `manifest.json` `2b4915fa...`. The archive carries the **fixed**
README (`grep -ac`) and the **corrected** citation, contains exactly the 5 intended files and nothing
else, and its checkpoint is still byte-identical to `U56_RA_scan/irc_reverse.chk`. **The artefact
that would actually be `scp`'d is the reviewed one. [확인]**

---

## 2026-08-25 (32차 배치) — critic17: Candidate B staging recheck (`candidate_b_reverse_stepsize_2026-08-25/`) — the staged deck is already superseded by §39.128

**Scope**: the staged Candidate B directory, its new builder
`src/pilot_package/tools/build_u56_ra_irc_stepsize_probe.py`, and the lead's seven points plus the
stepsize-rounding priority question. Abbreviations: **Candidate B** = the from-scratch reverse-arm
IRC redo with a reduced `StepSize` (proposer13 §39.127, revised §39.128); **f** = the step-size
fraction relative to G16's default (`f = N/10` for keyword `stepsize=N`); **§R39.82/83/84** =
engineer14's pricing sections in `03_COMPUTE_PLAN.md`; **arc floor** = proposer12's `arc >= 4.27`
path-length requirement (§39.124(3)).

## 판정
**BLOCK — do not bundle or submit the staged directory as it stands.** Not because of a defect in
`coder16`'s work (the build was correct against the ruling that existed when it ran) but because
**the ruling changed six minutes later**: `proposer13` §39.128 rules `stepsize=2` / `maxpoints=70`,
`engineer14` §R39.84 has already re-priced it, `src/`'s builder has already been updated to match —
and **the staged artefact still carries `stepsize=3` / `maxpoints=55`**. Rebuild the directory, then
this is a straightforward re-check.

Everything else I was asked to verify **passes**, including all three parts of the priority question.

## 치명적 — the staged artefact no longer matches the tool that built it

- `candidate_b_reverse_stepsize_2026-08-25/` vs `src/pilot_package/tools/build_u56_ra_irc_stepsize_probe.py`
  — **[확인]** I rebuilt from current `src/` into a scratch out-dir and diffed the route line:

        fresh build:  irc=(calcfc,reverse,recorrect=never,stepsize=2,maxpoints=70)
        staged deck:  irc=(calcfc,reverse,recorrect=never,stepsize=3,maxpoints=55)

  Constants in `src/` now read `IRC_STEPSIZE = 2` (`:92`), `IRC_MAXPOINTS = 70` (`:100`),
  `IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR = 63` (`:108`), mtime `2026-08-25_12:30:24`; the staged
  deck and manifest are `12:24:24`, the README `12:23:28`, the PBS script `12:22:50`. The package
  fingerprint differs accordingly (staged `d186703f2c97f4db`, current source `588ea87d42ea6bd5`).
  → **If this directory is bundled and submitted, the cluster runs the parameter set proposer13
  explicitly rejected** (§39.128: "no valid reason to accept the smaller margin"), at a
  `maxpoints` that §R39.84 no longer prices. The scientific result would be attributed to `f=0.20`
  in every document while the deck ran `f=0.30`.
  → The staleness is not confined to the deck: the manifest records `"stepsize": 3`,
  `"stepsize_f": 0.3`, `"maxpoints": 55`; `README.md` carries **5** references to the superseded
  values and `submit_candidate_b.pbs` **1**, plus a walltime justification quoting §R39.83's
  now-superseded `52 pts / 99.8-188.8 core-h / 1.6-2.9 h`.
  → **Fix**: rebuild the out-dir with the current tool and hand-update `README.md` and
  `submit_candidate_b.pbs` (both are hand-written, not tool-generated) to §39.128's rationale and
  §R39.84's numbers. Note the builder's own idempotency guard will (correctly) refuse to rebuild
  into the existing directory — remove it or build into a fresh one, deliberately.
  → **Walltime survives the change, but check the arithmetic when rewriting**: §R39.84 gives
  targeted `63 pts x 1.92-3.63 = 121.0-228.7 core-h` and ceiling `70 pts = 134.4-254.1 core-h`; at
  64 cores that is **1.89-3.57 h** targeted, **2.10-3.97 h** at the ceiling. The staged
  `walltime=10:00:00` still covers the worst case (~2.5x margin), so the header line need not
  change — only the justification comment under it, which currently quotes numbers ~40% too low.

## Priority #1 — the stepsize rounding, all three parts

- **(a) Is `StepSize` integer-only? Effectively yes, and I can now say what the unit actually is.
  [확인]** The decisive evidence is in this reaction's own from-scratch log,
  `U56_RA_scan/irc_reverse.log` (which ran with **no** `stepsize` keyword, i.e. the default):

        164:  Maximum points per path      =  30
        165:  Step size                    =   0.100 bohr
        1327: Supplied step size of   0.1000 bohr.
        1328:    Integration on MW PES will use step size of   0.3421 sqrt(amu)*bohr.

  So the default is `N=10` printed as **0.100 bohr** — the keyword's quantum is **0.01 bohr**, and
  `f = N/10` exactly. Because the quantum is 0.01 bohr, `f` is quantized in steps of 0.1 and
  **`f=0.25` is genuinely not representable**, independent of whether G16 would reject `2.5`
  syntactically. Corroborating in-project evidence: the restart tool's own CLI
  (`--step-size`, `type=int`, help "0.01 Bohr units") and engineer14's §R39.83 ("rounds to an
  integer keyword value (2 or 3)"). **[의심]** whether G16 hard-errors or silently truncates on a
  non-integer — no G16 here to test — but it does not matter for a deck that writes `2`.
  **One correction owed, and it is a units correction, which this project treats as Tier 1**: both
  the builder's `IRC_STEPSIZE` comment and §39.128's status line describe the unit as
  `0.01 Bohr*amu^(1/2)`. That conflates two different quantities the log prints separately: the
  keyword is in **Cartesian bohr** (0.100 bohr), which G16 then *converts* to a mass-weighted step
  of **0.3421 sqrt(amu)*bohr**. The ratio `f = N/10` — which is all the sizing depends on — is
  unaffected, so no number changes; but the label is wrong and should be corrected before someone
  uses it to convert something where the factor matters.
- **(b) Point-count arithmetic — re-derived, both values confirmed. [확인]**
  `4.27 / (0.3415 x 0.20) = 62.52` → 63 points (round up; a fractional point cannot clear a
  threshold). `4.27 / (0.3415 x 0.30) = 41.68` → ~42. Both match. The follow-on claims also hold:
  at `maxpoints=55`, `f=0.20` reaches only `55 x 0.0683 = 3.76` arc — **short of the 4.27 floor**,
  so `coder16`'s stated reason for rejecting `stepsize=2` *at a fixed `maxpoints=55`* was factually
  correct, and `f=0.30` does clear it (`55 x 0.10245 = 5.63`). §39.128 did not overturn that
  arithmetic; it removed the premise, ruling `maxpoints=55` to be the free variable. §R39.84's
  `70 - 63 = 7` points (11.1%) margin also checks out, as does `63 x 0.0683 = 4.30 > 4.27`.
- **(c) Is `f=0.30` still below the measured contraction scale? Yes, but by a third as much.
  [확인]** The scale is Point 7's own forced contraction, `0.116 / 0.336 = 0.3452`. Both integers
  satisfy the inequality (`0.30 < 0.345`, `0.20 < 0.345`); the margins are **0.045** vs **0.145**,
  i.e. 13% vs 42% of the hazard scale. So `coder16`'s "still safe" claim is literally true and
  proposer13's "three times the margin" is also true — they are not in conflict, and the "13-point
  margin" `coder16` cited is a **`maxpoints`** margin, not a **contraction-scale** margin. Those
  were the two quantities being traded against each other, which is exactly what §39.128 resolved.
  I am not re-litigating the choice; the facts above are what the lead asked to route.
  Worth attaching to that routing: the contraction scale is a **single measurement (n=1)**, which
  proposer13 flags themselves — the case for more margin rests on that, not on a tighter bound.

## 중대 — a cheap check that would falsify the whole f mapping in the run's first seconds

- `candidate_b_reverse_stepsize_2026-08-25/README.md:120` — **[확인]** the post-run route check is
  `grep -ac "stepsize" irc_stepsize_probe.log`. G16 echoes the submitted route text near the top of
  every log, so this counts **the input we already have on disk**; it cannot distinguish "G16
  honoured `stepsize=2`" from "G16 parsed and ignored it." (Measured: a log from a run with no
  `stepsize` keyword gives 0, so it discriminates *deck contents*, which were never in doubt.)
  → The strong check costs nothing and this project's own logs already establish its expected
  values. A from-scratch `calcfc` run prints the supplied step and its mass-weighted conversion
  (lines 165 / 1327-1328 above). Candidate B at `stepsize=2` **must** print
  `Step size = 0.020 bohr` and `Integration on MW PES will use step size of 0.0684 sqrt(amu)*bohr`
  (`0.3421 x 0.20`). If it prints `0.100 bohr` / `0.3421`, the keyword was silently ignored — and
  that is visible within seconds of job start, **before** 121-229 core-h are spent. This converts
  the `[NEEDS VERIFICATION]` that currently sits on the entire `f = N/10` mapping into a
  measurement. Recommend it replace, or accompany, the `grep -ac "stepsize"` line.
  (Note for whoever reads the log: the **restart** form prints the mass-weighted number directly
  instead — Candidate A's log line 116 reads `Step size = 0.342 sqrt(amu)*bohr`. Candidate B is
  from-scratch, so expect the `bohr` form.)
- **The `recorrect=never` check was dropped from Candidate B's README.** Candidate A's README
  carries `grep -ac "Recorrection delta-x convergence threshold:"`; B's does not, even though B
  **carries `recorrect=never` forward** (§39.127's amendment) and a silent drop would invalidate
  the run the same way. The README argues the risk is structurally different because there is no
  checkpoint to inherit a stale option from — true as to *mechanism*, but the check tests the
  *effect*, not the mechanism, and it is a proven discriminator on exactly this deck type:
  the original from-scratch reverse run (default recorrection) gives **30**, Candidate A's returned
  run (`recorrect=never`) gives **0**. Restore it.

## 요청 항목별 (1-7)

1. **Route match to §39.127 — OK apart from the superseded values. [확인]** `calcfc` ✓, `reverse` ✓,
   `recorrect=never` carried forward ✓ (§39.127's amendment, correctly applied), `maxpoints` written
   explicitly and not left at the project's usual 30 ✓. Only `stepsize`/`maxpoints` are stale.
2. **64 cores — OK. [확인]** `%nprocshared=64` in the deck, `#PBS -l select=1:ncpus=64:mpiprocs=1:
   ompthreads=64`, and the manifest's recorded invocation carries `--total-cores 64`.
3. **Geometry source — OK, verified programmatically. [확인]** Parsed all three coordinate blocks
   and compared as floats: staged deck vs the original production `U56_RA_scan/irc_reverse.gjf` →
   **11/11 atoms, max absolute coordinate delta 0.0000000000, zero element mismatches**; staged deck
   vs `ts.xyz` → identical by the same measure. Exact equality, not "close".
4. **Idempotency guard — OK, present from the start and it works. [확인]** Executed: first build
   `rc=0`, second build into the same out-dir `rc=5` with `refusing to overwrite existing ...`, and
   the deck's md5 was unchanged afterwards. The guard sits before every fallible step, and this tool
   writes no checkpoint bytes at all (G16 creates the `.chk` at run time), so the copy-ordering
   defect from the restart tool cannot arise here — the lesson transferred correctly rather than
   being re-learned. `tests/test_u56_ra_irc_stepsize_probe.py`: **7 tests, OK**, including a
   failed-build-leaves-no-deck test and a refuse-to-clobber test.
5. **`estimated_cost` conflation — OK, the shipped version is clean. [확인]** The manifest reads
   "~42 points expected to clear the arc>=4.27 floor (StepSize=3, f=0.30 —
   `IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR`, **NOT maxpoints=55, which is a safety cap with margin,
   not the target count**)". The expected count and the cap are named separately and the cap is
   explicitly disclaimed as a target. (The numbers themselves are the superseded ones, per the
   BLOCK — but the *structure* is right and will stay right after a rebuild, since both values come
   from constants.)
6. **Walltime citation — OK this time. [확인]** `submit_candidate_b.pbs` cites
   `03_COMPUTE_PLAN.md:19627-19634`; `:19627-19628` is the `cost, 1 attempt  52 pts x 1.92-3.63 =
   99.8 - 188.8 core-h` row and `:19630-19634` is the `cores/wall` row giving `1.6 - 2.9 h`. Both
   quoted figures are inside the cited range — the miscitation from the previous round did not
   recur. (The *content* is superseded by §R39.84; the citation is accurate to what it points at.)
7. **Scope — `u56_diagnostics_resubmit_2026-08-22/` untouched; `candidate_a_reverse_2026-08-25/` is
   NOT, and for a notable reason. [확인]** Candidate A **has been submitted and has returned**:
   that directory now holds `irc_recorrect_probe.log` (62,527 bytes) and PBS output files
   `sei_u56_candidate_a_reverse.{e,o}23757537`, all mtime `2026-08-25_11:57:31`, with the job output
   reading `start 2026-08-25T02:29:47Z / end 02:30:54Z rc=0`. Its checkpoint now hashes
   `473cf0f30444c893104fe156d0765039`, no longer the `7b4557b0...` I verified at staging — the run
   progressed it, as expected. `README.md` is still `d5229433291b895e7ef72143dcfe707f`, i.e. the
   reviewed text is intact. This is the results copy-back, not a `coder16` edit. Otherwise only
   `docs/02_METHOD_SPEC.md`, `docs/03_COMPUTE_PLAN.md`, `docs/05_STATE.md`,
   `tests/test_u56_ra_irc_stepsize_probe.py` and the new builder changed.

## 부수 확인 — Candidate A's own mandatory check, run on the returned log

Since the artefact under review depends on §39.126's reading of that run, I ran the gate I insisted
on in the 30차 batch, verbatim, on the real returned log:
`grep -ac "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log` → **0**.
`recorrect=never` **did** take effect on Candidate A, so §39.126's analysis is not resting on a
silently-dropped option, and Candidate B's premise is sound on that specific point. The corrected
`-a` form did its job on a real artefact, which is the first time it has been exercised for real.

## 테스트 상태 (independently executed)

- `python3 -m unittest test_u56_ra_irc_stepsize_probe` → **7 tests, OK**.
- `python3 -m unittest discover -s tests -p "test_*.py"` → **Ran 1747 tests in 98.4s, FAILED
  (failures=3, skipped=14)** — same three as every batch this week: two `test_build_stamp`
  stale-tarball reds and `test_session_digest.TestAgainstRealDocs` (R-10). No new failures from the
  new tool. Note the first of those is now *also* stale with respect to this new builder.

## 확인하지 못한 것

- Whether G16 rejects or truncates a non-integer `stepsize`. No G16 available; moot for a deck
  writing an integer.
- Whether arc/point really scales linearly with `f` for a *changed* corrector. engineer14 flags this
  `[ESTIMATE]` themselves; the whole point-count sizing rests on it, and the banner check
  recommended above tests the *step*, not the resulting *arc rate* — the first point's printed arc
  will be the real test, and it is worth reading at point 1 rather than at the end.
- The `f` value itself — proposer13's call, already ruled in §39.128; I supply facts only, per the
  lead's instruction not to duplicate that judgment.

**Reported to**: team-lead (BLOCK on bundling, the three priority answers, the units correction),
`coder16` (the rebuild requirement and the two README check improvements).

---

## 2026-08-25 (33차 배치) — critic17: confirm-only pass on the rebuilt Candidate B

**Scope**: narrow, as requested — (a) the rebuilt deck's parameters, (b) the three fixes from the
32차 batch, (c) regressions. Items 1-7 of the 32차 batch were clean before the BLOCKER and are not
re-derived here except where a rebuild could have disturbed them.

## 판정
**OK — the 32차 BLOCK is lifted.** All three fixes are correct, the rebuild is genuine, and nothing
regressed. One phrasing nit, no action needed.

## (a) Parameters — confirmed, in the strongest available form

- `irc_stepsize_probe.gjf:4` now reads
  `irc=(calcfc,reverse,recorrect=never,stepsize=2,maxpoints=70)`. **[확인]**
- Stronger than reading the file: I rebuilt from current `src/` into a scratch out-dir and diffed.
  **The staged deck is byte-identical to a fresh build**, and the staged manifest differs from a
  fresh one in the `provenance` key **only** (timestamp/fingerprint). So the directory was genuinely
  regenerated by the tool, not hand-patched to look right — the failure mode a `grep` for
  `stepsize=2` would not have caught. Manifest now carries `"stepsize": 2`, `"stepsize_f": 0.2`,
  `"maxpoints": 70`.

## (b) The three fixes

1. **Unit label — corrected, and correctly. [확인]** `README.md:37-42` now says "integer in units
   of 0.01 CARTESIAN bohr/step", names the wrong label explicitly, and keeps the distinction that
   matters: the log prints the supplied step in plain bohr (`Step size = 0.100 bohr` at default
   `N=10`) and only then converts, separately, to `0.3421 sqrt(amu)·bohr`. It also states plainly
   that `f = N/10` is unaffected and no ruled number changes — which is the honest scope of the
   correction, neither inflated nor buried.
2. **Stepsize-honored check — present, and the commands actually work. [확인]**
   `README.md:139-148` gives `grep -a "Step size"` and `grep -a "Integration on MW PES"`, expected
   `0.020 bohr` and `0.0684 sqrt(amu)*bohr`. I verified the expected value independently
   (`0.3421 × 0.20 = 0.0684`, matching G16's own 4-decimal print width) and **ran both commands
   against a real log** to confirm they print rather than silently suppress:

        grep -a "Step size"            ->  Step size                    =   0.100 bohr
        grep -a "Integration on MW PES" ->  Integration on MW PES will use step size of 0.3421 sqrt(amu)*bohr.

   The README also states the failure reading (`0.100`/`0.3421` = keyword ignored), cites the
   reference lines (`irc_reverse.log:165`, `:1327-1328`), and warns that the restart form prints the
   mass-weighted number directly instead (`irc_recorrect_probe.log:116`) so the two log shapes are
   not confused. That last point was mine and it was carried over accurately.
3. **`Recorrection` check — restored, with `-a` and with its evidence. [확인]**
   `README.md:155-161`: `grep -ac "Recorrection delta-x convergence threshold:"`, expected `0`,
   and it cites the discriminator I measured — 30 occurrences in the original default-recorrection
   run, 0 in Candidate A's returned log — plus the correct consequence (a nonzero count makes a
   repeat crash a false negative, not evidence). The README is honest that the check was "dropped
   from an earlier draft by mistake" rather than quietly reinstating it.

## (c) Regressions — none found

- **Cost separation preserved.** `estimated_cost` now reads "~63 points expected to clear the
  arc>=4.27 floor (StepSize=2, f=0.20 ... **NOT maxpoints=70, which is a safety cap with margin,
  not the target count**)" — the structure I checked at 55/42 survived the parameter change, as
  expected since both values come from constants.
- **Walltime arithmetic re-checked against §R39.84. [확인]** `submit_candidate_b.pbs:26-28`:
  63 pts × 1.92-3.63 = 121.0-228.7 core-h → **1.89-3.57 h** ("1.9-3.6h" ✓); 70 pts × 1.92-3.63 =
  134.4-254.1 core-h → **2.10-3.97 h** ("2.1-4.0h" ✓); `walltime=14:00:00` against the 3.97 h
  pessimistic ceiling is **3.53x** ("~3.5x" ✓). No `[PROVISIONAL]` markers remain in the README,
  PBS script or manifest (grep count 0 in all three).
- **Surviving mentions of the superseded values are historical, not stale. [확인]** Every remaining
  `stepsize=3` / `maxpoints=55` / `f=0.30` / `99.8` / `188.8` occurrence sits in an explicitly
  past-tense clause ("this coder's first build picked...", "§39.128 corrected...", "the two land
  within rounding of"). That is the project's own standing rule — record the rejected path, do not
  delete it — correctly applied, and I checked each one rather than counting them.
- **Scope clean. [확인]** `find -maxdepth 2 -newermt "2026-08-25 12:30"` returns only the four
  Candidate B files, `docs/03_COMPUTE_PLAN.md` (engineer14), `docs/05_STATE.md` (lead),
  `docs/04_REVIEW_LOG.md` (mine) and `tests/test_u56_ra_irc_stepsize_probe.py`. The builder itself
  was not touched after 12:30 — independently corroborated by the byte-identical rebuild above.
  `candidate_a_reverse_2026-08-25/` and `u56_diagnostics_resubmit_2026-08-22/` untouched.
- `python3 -m unittest test_u56_ra_irc_stepsize_probe` → **7 tests, OK**.

## 사소 (no action)

- `README.md:117-124`-style phrasing "G16 logs are binary-flagged" is over-general as a blanket
  statement: `file` reports `u56_diagnostics_resubmit_2026-08-22/4_irc_recorrect_restart/
  irc_recorrect_probe.log` as **`data`** but both `U56_RA_scan/irc_reverse.log` and
  `candidate_a_reverse_2026-08-25/irc_recorrect_probe.log` as **`ASCII text`** — it varies per run,
  presumably with whether NUL bytes land in a given log. This does not weaken the advice, it
  **strengthens** it: since an operator cannot predict which kind they will get, unconditional `-a`
  is exactly right. Only the blanket wording is loose. (Same nit as the 31차 batch, now with the
  mechanism identified.)

**Reported to**: team-lead (OK, BLOCK lifted), `coder16` (all three confirmed).

---

## 2026-08-25 (34차 배치) — critic17: combined recheck of the three-tier bundle (EulerPC tier 2, DVV tier 3, `README_BUNDLE.md`)

**Scope**: `candidate_b2_eulerpc_2026-08-25/`, `candidate_b3_dvv_2026-08-25/`, `README_BUNDLE.md`,
and the two new builders. Tier 1 (Candidate B) confirmed untouched, not re-reviewed (33차 verdict
stands). Abbreviations: **tier 1/2/3** = StepSize / EulerPC / DVV escalations; **DVV** = damped
velocity Verlet integrator; **HPC** = G16's default Hratchian-Schlegel predictor-corrector;
**rung 1/2/3** = §39.130's DVV fallback ladder (`calcfc` kept / dropped / `GradientOnly` added).

## 판정
**OK — the bundle may be tarred.** All 8 decks are byte-identical to fresh builds from current
`src/`, every priority item checks out, and `README_BUNDLE.md` is accurate against the rulings.

**One defect, and it is NOT in the bundle**: a misquoted primary source in
`build_u56_ra_irc_dvv_probe.py:138`, inherited from §39.130. It does not change any deck's bytes and
does not appear in any operator-facing file, so it does not gate the tar — but it should be fixed in
`src/` and in `02_METHOD_SPEC.md` §39.130, and it has a real consequence for how rung 3 is read.

## Priority 1 — the `gaussian.com/irc/` quotes, fetched independently

Fetched `https://gaussian.com/irc/` myself (HTTP 200, 175,314 bytes), stripped to text, and read the
entries. **Two of the three claims are exactly right; one is misattributed.**

- ✅ **EulerPC shares HPC's corrector — CONFIRMED verbatim.** *"EulerPC — Use the first-order Euler
  integration for the predictor step along with the HPC corrector step."* proposer13's §39.129
  correction to their own §39.127 framing is correct, and it is the load-bearing reason tier 2 is
  the weaker bet. Their quote is accurate word-for-word.
- ✅ **`ReCorrect` scope and defaults — CONFIRMED verbatim, including the clause the tier design
  rests on.** *"ReCorrect[=when] — Controls testing-and-recomputing for the correction step of HPC
  and EulerPC IRCs."* and, further down the same entry, ***"The default is Yes for EulerPC and HPC,
  and Never for other integrators."*** So `recorrect=never` is meaningful for EulerPC (tier 2 writes
  it — correct) and DVV falls in "other integrators" where the default is already `Never` (tier 3
  omits it — correct, and it matches the documented default rather than merely being harmless).
  Independent cross-check from this project's own data: the original HPC run
  (`irc_reverse.log`, default `ReCorrect=Yes`) contains **30** `Recorrection delta-x convergence
  threshold:` lines, Candidate A's `recorrect=never` run contains **0** — the documented default and
  the measured behaviour agree.
- ❌ **"DVV is the default for `IRC=GradientOnly` calculations" — MISATTRIBUTED. [확인]** The doc
  says that of **EulerPC**, not DVV. Verbatim: *"EulerPC — Use the first-order Euler integration for
  the predictor step along with the HPC corrector step. **This is the default for IRC=GradientOnly
  calculations.**"* The DVV entry is one sentence and says nothing about `GradientOnly`: *"DVV — Use
  the damped velocity verlet integrator [Hratchian02]."*
  → Where it lives: `02_METHOD_SPEC.md` §39.130 (rung-3 rationale, as a quoted doc statement) and,
  propagated, `src/pilot_package/tools/build_u56_ra_irc_dvv_probe.py:138`. It did **not** reach
  `candidate_b3_dvv_2026-08-25/README.md`, its PBS scripts or its manifests — I grepped all of them.
  → **The rung-3 route is still legal**, on a different and better quote from the `GradientOnly`
  entry itself: *"GradientOnly — Use an algorithm that does not require second derivatives... **Can
  be combined with EulerPC (the default), HPC, Euler, or DVV.**"* That sentence licenses
  `DVV`+`GradientOnly` explicitly, so no deck needs to change. Replace the citation, don't replace
  the route.
  → **But the correct fact makes rung 3 more dangerous than the ruling implies, and that is the part
  worth acting on.** `GradientOnly`'s own default algorithm is **EulerPC** — tier 2's algorithm,
  which uses the HPC corrector this entire tier exists to bypass. So rung 3 is precisely the rung
  where a dropped/ignored `DVV` keyword would silently produce the wrong algorithm with `rc=0` and a
  normal-looking log. §39.130's own Check 1/Check 2 (`Integration scheme` echo, zero
  `Bulirsch-Stoer`) already catch this, but they are written tier-wide; **rung 3 deserves them
  flagged as non-optional**, on this specific mechanism rather than on general principle.

## Priority 2 — route text, all 8 decks

**[확인]** Compared each against the ruled text character by character:

| deck | route (IRC options) | ruled at | verdict |
|---|---|---|---|
| `irc_eulerpc_probe.gjf` | `calcfc,reverse,EulerPC,recorrect=never,stepsize=2,maxpoints=100` | §39.129(1) | exact |
| `irc_eulerpc_smoke.gjf` | same, `maxpoints=2` | §39.129 addendum / §R39.85 | exact |
| `irc_dvv_rung1_full.gjf` | `calcfc,reverse,DVV,stepsize=2,maxpoints=100` | §39.130(1) preferred | exact |
| `irc_dvv_rung2_full.gjf` | `reverse,DVV,stepsize=2,maxpoints=100` | §39.130(1) fallback | exact |
| `irc_dvv_rung3_full.gjf` | `reverse,DVV,GradientOnly,stepsize=2,maxpoints=100` | §39.130(1) last rung | exact |
| the three `_smoke` DVV decks | as above, `maxpoints=3` | §R39.86 | exact |

- `recorrect=never` is **present in both EulerPC decks and absent from all six DVV decks** — the
  deliberate asymmetry §39.130(2) rules, and (per the fetch above) the one that matches the
  documented default. **[확인]**
- Note on rung 2, since it will look wrong to a future reader: it carries neither `calcfc`/`RCFC`
  nor `GradientOnly`, and the doc states *"one of RCFC and CalcFC must be specified"*. That is not a
  defect — rung 2 exists **only** as the fallback to try if rung 1's smoke errors on the
  `calcfc`+`DVV` combination, and its own 3-point smoke is exactly what would surface this at ~zero
  cost. It must never be submitted as an independent first choice; `README_BUNDLE.md` and the tier-3
  README both state the conditional ordering correctly.

## Priority 3 — no-clobber, verified by building, not by reading

**[확인]** Built into scratch directories rather than inspecting the guard:
- Second identical invocation of each tool → `rc=5`, `refusing to overwrite existing ...`, and the
  md5 of every file in the directory unchanged.
- All eight variants **coexist in one directory**: `--smoke`/full for EulerPC and `--rung {1,2,3}` ×
  `--smoke`/full for DVV produced 16 files (8 decks + 8 manifests) with distinct names, no refusal,
  no overwrite.
- **Every one of the 8 staged decks is byte-identical to its fresh rebuild** from current `src/`.
  That is the check that rules out hand-editing, which reading the routes could not.

## Priority 4 — cost/wall, re-derived

**[확인]** Against §R39.85/86, arithmetic redone rather than compared:
- **Tier 2**: 63 pts × 1.92-7.3 = 121.0-459.9 targeted; 100 × 1.92-7.3 = 192.0-730.0 ceiling; smoke
  1-2 pts = 1.9-14.6. Wall ceiling 100 × 1.8-6.8 min = 180-680 min = **3.0-11.3 h**. `walltime=40h`
  → **3.54x** ("~3.5x" ✓). All match.
- **Tier 3**: 100 × 1.0-10.9 = **100.0-1090.0** core-h ceiling; smoke 1-3 pts = 1.0-32.7. Wall
  94-1020 min = **1.6-17.0 h**. `walltime=44h` → **2.59x** ("~2.6x" ✓), correctly described as the
  narrowest and as necessity under ADR-114's 48 h cap rather than a corner cut.
- **Combined**: 134.4+192.0+100.0 = **426.4**; 254.1+730.0+1090.0 = **2,074.1** core-h;
  2,074.1/8,238 = **25.2%** ✓. Every figure in `README_BUNDLE.md`'s table reproduces.
- **Rung-3 `10.9 core-h/pt`-as-a-FLOOR caveat landed where §R39.86 put it**: present in
  `submit_dvv_r3_full.pbs:43` **and** `candidate_b3_dvv_2026-08-25/README.md:94`, both stating it as
  a floor rather than a ceiling for that rung. §R39.86's companion recommendation (a fresh smoke at
  rung 3 rather than reusing rung 1's) is also carried.
- All 8 PBS scripts request `select=1:ncpus=64:mpiprocs=1:ompthreads=64` and all 8 decks carry
  `%nprocshared=64` (checked by `uniq -c`: 8 of each, no outliers).

## Priority 5 — `README_BUNDLE.md`

**[확인] Accurate.** Submission order (tier 1 unconditional → tier 2 only on a genuine tier-1
failure → tier 3 only on a genuine tier-2 failure) matches §39.129/130's sequencing; the smoke-first
table matches (tier 1 deliberately no smoke per §39.127, tiers 2/3 yes); the DVV three-rung ladder is
described with the correct conditional trigger (**rung 1's smoke *errors*** → rung 2, not "rung 1
fails scientifically"); the check counts it advertises are real (tier 2 README has exactly 4
mandatory checks, tier 3 exactly 5); the cost table reproduces as above.
Two things it does that are better than required and worth preserving in any edit: it states plainly
that the three tiers are **not** equally likely and that tier 2 is a *weaker* bet than originally
framed (rather than presenting a neutral menu), and it distinguishes "the tier failed" from "a check
came back ambiguous" — instructing a rerun rather than an escalation in the second case, which is
the exact reasoning error a hurried operator would otherwise make.

## Priority 6 — geometry, tests, scope

- **Geometry — all 8 decks exact. [확인]** Parsed each coordinate block and compared to
  `U56_RA_scan/ts.xyz` as floats: 11/11 atoms, **max absolute delta 0.0000000000**, zero element
  mismatches, in every one of the eight.
- **Tests. [확인]** `test_u56_ra_irc_eulerpc_probe` + `test_u56_ra_irc_dvv_probe` → **19 tests, OK**.
  Full suite → **Ran 1766 tests, FAILED (failures=3, skipped=14)** — the same two `test_build_stamp`
  stale-tarball reds and `test_session_digest` (R-10). No new failures.
- **Scope. [확인]** Tier 1's directory is untouched (all four files still 12:34-12:37, before this
  round's 13:2x-13:3x work). Changed since 13:00: only the two new staging directories,
  `README_BUNDLE.md`, `docs/02_METHOD_SPEC.md` (proposer13), `docs/03_COMPUTE_PLAN.md` (engineer14),
  `docs/05_STATE.md` (lead) and the two new test files. Earlier returned results
  (`candidate_a_reverse_2026-08-25/`, `u56_diagnostics_resubmit_2026-08-22/`) untouched.

## 사소

- `candidate_b2_eulerpc_2026-08-25/README.md:117-131` — Check 1's negative test (`grep -a "Using LQA
  Reaction Path Following"`, absence ⇒ EulerPC probably took effect) is **vacuous on a run that
  computed zero points**: the string appears roughly once per computed point (measured: **6**
  occurrences in the 6-point original, **1** in Candidate A's single-new-point restart), so a smoke
  that dies before the first point also shows zero. The README never claims absence proves success,
  but an operator reading quickly could take it that way. One clause — "only meaningful if the log
  shows at least one completed point" — closes it. Both referenced strings do exist in real logs, and
  `Integration scheme = HPC` is at `irc_reverse.log:166` exactly as the tier-3 README states.

## 확인하지 못한 것

- The positive echo strings for the Euler predictor and for DVV's `Integration scheme` value. Both
  READMEs mark these `[NEEDS VERIFICATION]` and tell the reader to take them from the smoke's own
  returned log rather than guessing — the correct handling; no G16 here to settle them.
- Whether `StepSize` means anything under DVV's adaptive stepping. §39.130(3) flags it, the tier-3
  README's Check 3 tells the reader to measure the realized arc/point rather than trust the request.
- Whether rung 2 errors on the missing `CalcFC`/`RCFC`. That is what its smoke is for.

**Reported to**: team-lead (OK to bundle; the misquote and its rung-3 consequence),
`coder16` (the `:138` comment fix and the Check-1 clause), `proposer13` (the §39.130 misattribution
at source, since the doc is the shared memory and the tool comment only inherited it).

---

## 2026-08-25 (35차 배치) — critic17: confirmation of the two 34차 fixes, and an unprompted check of the shipped tarball

**Scope**: narrow — the citation fix, the Check-1 clause, and (not requested) whether
`sei_reverse_arm_bundle_2026-08-25.tar.gz` actually contains them.

## 판정
**OK — the bundle as tarred is the reviewed one.** Both fixes are correct and complete, the rung-3
rebuild disturbed nothing, and the archive on disk matches the fixed tree member for member.

- **Citation fix — correct. [확인]** `build_u56_ra_irc_dvv_probe.py:137-144` now states the
  misattribution explicitly, gives DVV's actual one-sentence entry, and cites the real supporting
  text from `GradientOnly`'s own entry ("Can be combined with EulerPC (the default), HPC, Euler, or
  DVV"). It says plainly that rung 3's route is unaffected — which is the honest scope, since the
  route never depended on the wrong quote.
- **The sharper consequence landed in the operator-facing document, which is where it matters.
  [확인]** `candidate_b3_dvv_2026-08-25/README.md:40-47` now carries it as its own red-flagged
  block: `GradientOnly`'s default is `EulerPC`, so a dropped or ignored `DVV` at rung 3 silently
  becomes an EulerPC run at `rc=0` with no symptom, and **"Checks 1 and 2 below are NOT optional at
  rung 3 — they are the only thing that catches this specific failure mode."** That is stronger than
  what I asked for and correctly scoped to rung 3 rather than smeared across the tier.
- **Check-1 clause — correct, and it names the observable. [확인]**
  `candidate_b2_eulerpc_2026-08-25/README.md:134-140` states the negative test is only meaningful
  once at least one IRC point has completed, carries the measured evidence (6 occurrences in the
  6-point original, 1 in Candidate A's single-new-point restart), gives the reason a zero can be
  spurious ("nothing computed yet, not 'EulerPC correctly avoided HPC's predictor'"), and tells the
  reader **what to look for instead** (`SCF Done` / `Point Number`) rather than leaving "confirm a
  point completed" as an exercise.
- **The rung-3 rebuild changed only what it should have. [확인]** Both rung-3 routes are unchanged
  (`irc=(reverse,DVV,GradientOnly,stepsize=2,maxpoints=3|100)`); re-running the full 8-variant
  rebuild from current `src/` into a scratch dir gives **all 8 decks byte-identical** to the staged
  ones again, and the two rung-3 manifests differ from freshly-built ones in `provenance` only — so
  the new `rung_note` text is baked into the tool and reproduces, rather than being a one-off edit.
- **Tests. [확인]** 19/19 on the two tool test files.

## Unprompted — the shipped archive

`sei_reverse_arm_bundle_2026-08-25.tar.gz` appeared at 13:45:16 during this pass, after the 13:42
fixes. Timestamps are not evidence, so I compared content: **all 31 members hash identical to the
working tree**, the archive's copies of both READMEs carry the fixed text, and the misquoted string
`DVV is "the default for` appears in **no member**. Membership is exactly the intended 31 (README_BUNDLE
+ tier 1's 4 + tier 2's 7 + tier 3's 19), with nothing extra swept in. **The artefact that would be
`scp`'d is the reviewed one.** Checked because a stale archive is this project's own repeat failure
mode (`test_build_stamp`'s standing red, and the same check caught nothing wrong on Candidate A's
tarball either — a negative result worth recording, not skipping).

**Reported to**: team-lead (both fixes confirmed, tarball verified), `coder16` (same).

---

## 2026-08-25 (36차 배치) — critic17: B+ closing jobs (`pilot_tests/bplus_reverse_new_2026-08-25/`) — the decks are clean; the README's post-run workaround is not

**Scope**: the two B+ terminal opts that, with `reactant_match(last)`, close U-56a condition 7's
reverse branch; the new `build_u56_bplus_reverse_opt.py`; the README's post-run pipeline.
Rulings: §39.131 (proposer13), §R39.87 (engineer14). Abbreviations: **B+** = the terminal-optimisation
comparator that checks two points of an IRC path relax to the same structure; **mid/last** =
§39.131's Point 35 / Point 70 of Candidate B's returned path; **PYBPLUS** = the Python heredoc at
`payload/U56.sh:1071-1155` that computes the B+ verdict.

## 판정
**FIX-THEN-RUN, with the scoping made explicit: the two jobs are safe to submit now.** Geometries,
route, guard cross-check, no-clobber, costs and walltimes are all clean and independently
reproduced. **The fix is needed before anyone acts on the returned result**, not before `qsub` —
it is in the README's instructions for closing the gate, which is the step after these jobs land.

## 치명적 — the documented workaround points at a test-fixture channel that this path never reads

- `pilot_tests/bplus_reverse_new_2026-08-25/README.md`, "Known gap" paragraph — **[확인]** it tells
  the reader that if a definite `match: true/false` is wanted instead of the documented `None`,
  `SEI_C8_ENDPOINTS_JSON` is "the existing, documented channel for backfilling that field on an
  older cert — a one-off env var, not new code." Three separate checks say that is wrong here:
  1. **The code the README tells you to run never reads it.** I extracted the PYBPLUS body exactly
     as step 3 instructs and grepped it: it contains **one** environment reference,
     `os.environ["SEI_PKG_ROOT"]` (line 2). It loads `endpoint_certs.json` from the job directory
     directly. Setting `SEI_C8_ENDPOINTS_JSON` and re-running step 3 changes **nothing**, silently —
     the operator gets `None` again with no error and no explanation of why the documented fix
     did not work.
  2. **Where it *is* read, it is a different stage.** `U56.sh:167` consumes it inside the block that
     *writes* the certification, i.e. during a full harness run, not at B+ gate time. Reaching it
     would mean re-running certification, which is not "a one-off env var" on an already-returned
     cert.
  3. **And it is labelled, by this codebase, as not-a-certification.** `U56.sh:173` stamps anything
     injected that way `"cert:SEI_C8_ENDPOINTS_JSON [FIXTURE] -- test injection, not a
     certification"`; `P1.sh:86` calls it a 테스트 전용 데이터 주입 채널 (test-only data injection
     channel); and both job templates unset it at job start
     (`local.sh.tmpl:8`, `pbs.sh.tmpl:25`) precisely so it cannot reach a real cluster job.
  → **Why this matters more than a broken command**: the thing being decided is the closing gate of
  U-56a condition 7. If this instruction were ever made to work, condition 7's reverse branch would
  be closed on data the codebase itself marks as a test fixture. The correct answer is the one
  `U56.sh:1119` gives *before* it names the env var: `None` on an older cert **is** the honest
  answer under Rule 18. If a definite verdict is genuinely required, it has to come from
  re-certifying the reactant through `endpoint_prep.sh` so the cert carries a real
  `energy_hartree` — a computation, not an environment variable.
  → **Not coder16's invention**: the claim is inherited verbatim from the code comment at
  `U56.sh:1119-1121`. Fix belongs in both places, and the comment is the more dangerous of the two
  because it will be re-read by everyone who touches this gate. Same shape as the §39.130 misquote
  earlier today — an authoritative-sounding pointer that nobody had followed end to end.
  → **Confirmed the gap itself is real**: I walked `U56_RA_scan/endpoint_certs.json` for any key
  containing "energy" — there are none, on any branch of the document. And running the pipeline
  reproduces exactly the documented symptom (below).

## Priority-by-priority

1. **Geometry extraction — exact, and the "obvious" re-derivation is the one that is wrong.
   [확인]** Parsed the returned `irc_stepsize_probe.log` myself. It holds 71 `Point Number:` blocks
   (0 = saddle) and 70 path points; `parse_irc_path_frames` returns 70 frames with
   `arc[34] = 2.38953` and `arc[69] = 4.77975`. Both staged decks **and** both `.xyz` files are
   byte-exact against those frames: **max absolute coordinate delta 0.0000000000**, zero element
   mismatches, 11/11 atoms, on all four files.
   ⚠ **Recorded because it will trip the next person**: my first independent pass parsed the
   `CURRENT STRUCTURE` blocks instead, and got a **~0.001 Å** mismatch (0.0013 mid, 0.0010 last) —
   which looks exactly like a defect and is not one. This project's convention, stated in
   `parse_irc_path_frames`'s own docstring (`criteria/g16.py:343-353`), is *the orientation block
   preceding each `NET REACTION COORDINATE` line*, not the `CURRENT STRUCTURE` summary printed after
   it; the two differ slightly because one is the geometry the energy/gradient was evaluated at and
   the other is the post-corrector path point. The decks follow the convention, which is also what
   the original B+ jobs used — and consistency with those is the entire point of a comparator.
   0.001 Å is orders below any `opt=loose` convergence threshold, so nothing turns on it
   scientifically; it turns on provenance, and the provenance is right.
2. **`bplus_sample_points` cross-check — reproduced, and the refusal is real. [확인]** Ran
   `guards.bplus_sample_points()` directly on the log's own 70 arcs: **`(34, 69)`**, arcs
   `2.38953 / 4.77975`; half-of-last is `2.389875` and index 34 is the nearest, as the function
   intends. Then I forced a disagreement by truncating the log to 40 points (sample becomes
   `(19, 39)`) and ran the builder: **exit 6**, no files written, with a message that names both
   readings and says *"STOP and report this, do not pick a side"* — the right instruction for a
   guard that cannot know which side is wrong. A guard that refuses is only worth having if it can
   fire; this one fires.
3. **Route identity — byte-identical. [확인]** `diff` of the `%`-directives and route line between
   the new `bplus_reverse_mid.gjf` and the ORIGINAL
   `U56_RA_scan/bplus_reverse_mid.gjf`: no differences. All four B+ decks (2 new, 2 original) carry
   exactly one route, `#p nosymm wB97XD/gen scrf=(pcm,solvent=acetone,read) opt=(loose,maxcycles=100)
   Int(Grid=UltraFine)`, i.e. the `endpoint_opt_rough` family the original jobs used. Correct family:
   the comparator's validity depends on the two runs being the same kind of relaxation, and they are.
4. **The cost-anchor "discrepancy" — there isn't one; both readings are right, and both parties
   already documented it. [확인]** Both numbers come from the same two logs, from two different
   cells:

        bplus_reverse_mid.log   Job cpu time 12h30m30.7s = 12.51 core-h CONSUMED
                                Elapsed 13m44.7s = 824.7 s x 64 cores / 3600 = 14.66 core-h RESERVED
        bplus_reverse_last.log  Job cpu time  8h 2m 6.3s =  8.04 core-h CONSUMED
                                Elapsed  9m40.6s = 580.6 s x 64 cores / 3600 = 10.32 core-h RESERVED

   Ratios 85.3% and 77.9% — ordinary parallel efficiency, the same 78% band this reaction's other
   64-core jobs show. §R39.87 already prints **both** cells and labels the second "cross-check: Job
   cpu time ... (77% of nominal)", and coder16's PBS comments quote both raw values verbatim
   (`12.51 core-h ... (Job cpu time 12h30m30.7s, Elapsed time 13m44.7s)`). So the provenance is
   fully auditable on both sides and no number is wrong.
   **The one residue, and it is standing-rule-1**: coder16's README/PBS call the consumed figure
   "core-h" without qualifying it, and **for budget accounting against the guard margin the reserved
   figure is the correct one** — you are billed for the whole node whether or not it is busy.
   Writing "12.51 core-h consumed / 14.66 reserved" costs four words and removes the ambiguity.
   Nothing turns on it here (two jobs, ~25 core-h reserved, immaterial against ~8,238), but the same
   ambiguity at scale is exactly how a budget quietly under-counts by 15-28%.
5. **README instructions — run cold, verbatim; they work, and the `SEI_PKG_ROOT` warning is correct.
   [확인]** On a fresh `cp -r` copy: the `sed -n '1071,1155p'` extraction yields 85 lines that
   `ast.parse` accepts as valid Python; run with `PYTHONPATH=` only it fails exactly as the README
   warns (`KeyError: 'SEI_PKG_ROOT'`, raised at line 2 before any import); run as instructed it
   completes and prints the documented summary line, writing `bplus_reverse.json`. On the ORIGINAL
   logs (the only dry run available until the new jobs return) it produced
   `agreement=True`, `covalent_graphs_match=True`, `energy_delta_ev=0.000127`, and
   `reactant_match(mid/last)=None/None` — **the documented gap reproduces exactly**, and the reason
   is visible in the JSON: the distance clause passes comfortably (`delta_ang = 0.000164` against
   the 0.05 Å tolerance) and it is the energy clause alone that is unknown. The README's *framing*
   of that `None` ("a genuine SPLIT/unknown, not a false positive or negative") is right; only its
   proposed remedy is wrong (see 치명적 above).
6. **Scope, no-clobber, tests, walltime — all clean. [확인]** Rebuilding from the real log into a
   scratch dir reproduces all four artefacts **byte-identical** to the staged ones; a second build
   into the same directory refuses with exit 5 and leaves them unchanged. Walltime `02:00:00`
   against measured elapsed 13m44.7s / 9m40.6s = **8.7x / 12.4x** (README claims ">8x" / ">12x" ✓),
   and the margins are correctly computed against *elapsed*, which is what a wall-clock cap
   constrains. `test_u56_bplus_reverse_opt` → **6 tests, OK**; full suite → **Ran 1772 tests,
   FAILED (failures=3, skipped=14)**, the same two `test_build_stamp` stale-tarball reds and
   `test_session_digest` (R-10), no new failures. Changed since 15:00: only the new staging
   directory, the new tool, its test file, and the three documents owned by proposer13/engineer14/
   the lead.

## 부수 확인 — last round's unit derivation is now confirmed by measurement

In the 32차 batch I derived `f = N/10` from the log banner (`Step size = 0.100 bohr` at the default
`N=10`, converted by G16 to `0.3421 sqrt(amu)*bohr`) and predicted that `stepsize=2` would give
`0.3421 × 0.20 = 0.0684` arc per point. Candidate B's returned run gives **`4.77975 / 70 =
0.06828`** — **0.2% from the prediction**. The keyword was honoured, it means what we said it means,
and the point-count sizing that the whole tier rested on was sound. Recording it because a
prediction that survives contact with the real run is worth as much as a defect found.

## 확인하지 못한 것

- Whether `reactant_match["last"]` will be `None` on the NEW logs too. It almost certainly will —
  the cause is the cert, not the logs — but that is the gate's actual outcome and cannot be known
  until the jobs return. **This is the item to decide before reading the result, not after**: either
  accept the documented unknown under Rule 18, or re-certify. Do not let it be settled by whoever
  is holding the terminal at the time.
- Whether the two new opts converge at all. `opt=(loose,maxcycles=100)` on a geometry already close
  to a minimum is the lowest-risk job of this round, and the README correctly says not to run the
  comparison with `pick_status=ok` if either job fails.

**Reported to**: team-lead (FIX-THEN-RUN with the submit/read scoping, the fixture-channel finding,
the resolved cost question), `coder16` (README fix + the units label), and flagged that
`U56.sh:1119-1121`'s own comment carries the same wrong pointer.

---

## 2026-08-37 (37차 배치) — critic17: confirmation of the two 36차 fixes — one is complete, one left a contradicting copy behind

**Scope**: narrow — the `SEI_C8_ENDPOINTS_JSON` correction, the consumed/reserved units labelling,
and whether anything else moved.

## 판정
**FIX-THEN-RUN (unchanged verdict, smaller remainder).** The units fix is complete. The
workaround fix is correct where it was applied, but **the same wrong claim survives one screen away
in the same file**, and the file now contradicts itself. The two jobs remain safe to submit; this is
still a before-you-read-the-result item, not a before-`qsub` one.

## 남은 결함 — `payload/U56.sh:136-137` still points at the channel that was just corrected away

**[확인]** `coder16` reports having checked this sibling comment and deliberately left it, on the
grounds that it sits inside `resolve()` "where the env var IS actually read during a live run".
That reasoning is about *whether* the variable is read; the sentence is about *what it is a fix
for*. Verbatim, `:136-137`:

    # `None` on an older cert that predates this field (Rule 18) -- see `SEI_C8_ENDPOINTS_JSON`
    # below for the existing, documented one-off backfill channel for exactly that case.

"Exactly that case" is *an older cert that predates the field* — precisely the case the new
correction at `:1120-1124` now says the channel does **not** address ("does NOT backfill an
already-returned cert"). So `U56.sh` now asserts both propositions, 984 lines apart, and `:137` is
the copy a reader meets **first** (it sits in the certification block, which is where anyone tracing
`energy_hartree` starts). Mitigating, and the reason this is a defect rather than a blocker: `:137`
says "see ... below", and what is below is now the correction — a reader who follows the pointer
lands on the truth. A reader who quotes the sentence does not.
→ **Fix**: same edit as `:1120`, or simply delete the second clause of `:137` — `None` under Rule 18
stands on its own without a pointer to a remedy that isn't one.
→ Recording the pattern, since this is its third instance today (§39.130's misquoted doc line, the
README's inherited workaround, now this): **an authoritative-sounding cross-reference that nobody
had followed end to end.** Each was cheap to check and none had been checked. The cost of checking
is one `grep`; the cost of not checking, here, would have been closing U-56a condition 7 on a
channel the codebase labels a test fixture.

## 확인된 수정

- **Workaround correction — correct where applied. [확인]**
  `pilot_tests/bplus_reverse_new_2026-08-25/README.md:136` now leads with
  *"`SEI_C8_ENDPOINTS_JSON` does NOT fix this on an already-returned job — do not try it"* and keeps
  the accurate framing of the `None` above it. `U56.sh:1120-1124` carries the same correction with
  the three supporting locations named (`:167` reads it during a fresh certification, `:173` stamps
  it `[FIXTURE]`, `P1.sh:86` and the two job templates). `bash -n src/pilot_package/payload/U56.sh`
  passes — I ran it rather than taking the report's word, since a comment edit inside a file full of
  heredocs is exactly where an unbalanced quote hides.
- **Units labelling — complete, all three files. [확인]** README rows 50-51 and both PBS scripts now
  read "12.51 core-h consumed / 14.66 core-h reserved (85% efficiency)" and "8.04 consumed / 10.32
  reserved (78%)", with the raw cells still quoted alongside and the walltime margins still stated
  against **elapsed**, which is the quantity a wall-clock cap actually constrains. Nothing to add.
- **The decks did not move. [확인]** All six artefacts (`.gjf` ×2, `.xyz` ×2, `manifest_*.json` ×2)
  still carry mtime `15:46:52`, i.e. the documentation edits did not disturb the reviewed payload.
- **Suite unchanged. [확인]** `Ran 1772 tests, FAILED (failures=3, skipped=14)` — identical count and
  composition to before the edit, so the `U56.sh` change introduced nothing.
  One correction to `coder16`'s framing, since it matters for what the red means: they reported the
  two `test_build_stamp` failures as "now from the U56.sh edit itself, as expected". They are not
  *from* it — that pair has been red since 2026-08-22 and the edit merely added one more filename to
  an already-long list. The failure message currently names **ten** stale files:
  `payload/BPLUS_REOPT.sh`, `payload/U56.sh`, `payload/endpoint_prep.sh`, `sei_pilot/cli.py`,
  `sei_pilot/guards.py`, and all five `tools/build_u56_*` builders. **The package has now diverged
  from `src/` across every tool this work item produced** — still non-blocking while everything is
  hand-staged, and still the thing that must happen before anything ships from the package.

**Reported to**: team-lead (units fix confirmed, the surviving contradicting comment, the
ten-file package divergence), `coder16` (the `:137` remainder).

---

## 2026-08-25 (38차 배치, interim) — critic17: §39.132's backfill provenance, verified ahead of the final pass

**Scope**: only the lead's two verification asks on proposer13's §39.132 (backfill
`reactant_cert.energy_hartree` from `endpoint_prep_reactant/endpoint_tight.log`). Logged now rather
than held for the final pass, since it is self-contained and the number is about to be used.

## 판정
**The backfill is legitimate and the value is correct.** It is primary measured data, and it is
categorically different from the fixture channel I rejected in the 36차 batch. Two things to carry
into how the result is read, neither of them objections.

- **Value confirmed, and uniquely identified. [확인]**
  `cpu_machine_pilot_results/sei_pilot_work/jobs/endpoint_prep_reactant/endpoint_tight.log` gives
  four `SCF Done` lines, the last three all reading **`E(UwB97XD) = -349.620897014 A.U.`**
  (19 → 12 → 6 → 1 cycles; proposer13's "3 re-evaluations" ✓), `Charge = 0 Multiplicity = 2` ✓,
  two `Normal termination` ✓, route `#p nosymm wB97XD/gen scrf=(pcm,solvent=acetone,read)
  opt=(tight,calcfc...)` ✓. Exactly the cited number, to all nine decimals.
- **It is the RIGHT log, and that was worth checking, because four near-identical siblings exist.
  🔴 [확인]** My own first `find | head -1` grabbed the wrong one. The tree contains:

        endpoint_prep_reactant/                    -349.620897014   solvent=acetone   <- CERTIFIED
        endpoint_prep_reactant_epsinf_full/        -349.620897959   solvent=generic   (eps-infinity)
        endpoint_prep_reactant.reset.1787267829/   -349.620693198   solvent=generic
        endpoint_prep_rc_reactant/                 -691.712104723   (different system, the RC)
        endpoint_prep_product/                     -349.660390954   (the product)

  The `epsinf_full` sibling differs by **9.45e-7 Hartree = 2.6e-5 eV** — close enough to look right
  in a spot check and wrong in provenance (a non-equilibrium ε∞ solvation run, `solvent=generic`).
  What settles it is not proximity but the certificate's own pointer: `endpoint_certs.json` records
  `reactant_source: ["cert:endpoint_prep(endpoint_prep_reactant)", "geometry:endpoint_tight.log"]`
  and `reactant_cert.source = .../jobs/endpoint_prep_reactant/f1_observables.json`, with
  `solvent_config` recording `scrf=(pcm,solvent=acetone,read) ['eps=18.5']` — which matches the
  chosen log's route and **not** the two `solvent=generic` siblings. proposer13 picked the log the
  cert itself names. **Whoever applies the backfill must copy the directory name from the cert, not
  from a `find`** — this is the one step where a plausible wrong answer is one keystroke away.
- **Categorically different from `SEI_C8_ENDPOINTS_JSON`, and the distinction is not a formality.
  [확인]** The fixture channel injects operator-supplied JSON and the codebase stamps the result
  `[FIXTURE] -- test injection, not a certification` (`U56.sh:173`). This backfill copies a
  converged SCF energy out of the certified reactant's own primary log — the same job the cert
  already points at for its geometry — into the field a later schema version would have carried
  automatically. Same job, same level, same charge/spin, same solvent, no new compute, and the
  provenance label `[MEASURED, from endpoint_tight.log]` says exactly where it came from. That is
  recovering existing certified data, not injecting new data.
- **Tight-vs-loose precedent — real, already caveated in code, and worth one number the ruling does
  not state. [확인]** `guards.py:579` records the measured `certified reactant (opt=tight) vs
  bplus_reverse_last.log (opt=loose)` offset as **Δ = -4.13e-4 eV**, and proposer12's own docstring
  already warns it "is NOT a matched-method one (tight vs loose) and should not be leaned on that
  close to the tolerance in a future, closer case." Against `BPLUS_ENERGY_TOLERANCE_EV = 1.0e-3` eV
  (`guards.py:425`), that systematic offset consumes **41% of the tolerance budget** before any real
  physical difference is measured. Two consequences, both worth stating before the number is read:
  (i) discrimination is **not** at risk — the hazard the clause exists for is the 0.686 eV
  same-graph coordination isomer, 686x the tolerance, which no 4e-4 offset can disguise;
  (ii) but a *pass* is not automatically a clean pass. proposer13's "~1,660x below 0.686 eV" is the
  right comparison for "can this still catch an isomer"; the operative comparison for the boolean
  is against 1.0e-3. **Report the measured `energy_delta_ev`, not just `match: true/false`** — if
  the new `last` lands materially above the historical ~4e-4 while still under 1.0e-3, that is
  proposer12's caveat becoming operative, and it should be read as marginal rather than clean.

**Reported to**: team-lead (verified; the wrong-sibling hazard and the 41%-of-tolerance framing).

---

## 2026-08-25 (39차 배치) — critic17: final confirm pass on the B+ closing jobs — three of six items did not land

**Scope**: the lead's six-item checklist on `pilot_tests/bplus_reverse_new_2026-08-25/` and the
`payload/U56.sh` comment edits.

## 판정
**NOT OK — do not tar yet.** Items 1, 4 and 6 landed. **Items 2, 3 and 5 did not**, and item 5 is a
command that fails when run as written. Back to `coder16` per the lead's own routing. The decks
themselves remain clean and untouched — nothing here is about the two jobs, all three are about the
instructions for closing the gate afterwards.

## ✅ Landed

1. **Backfill README step — complete. [확인]** Working-copy-only warning is explicit and names the
   read-only tree; the JSON edit is shown literally with "leave every existing key as-is"; the label
   is exactly `[MEASURED, from endpoint_tight.log, backfilled per §39.132]`. It also re-derives the
   value independently (route, `Charge = 0 Multiplicity = 2`, `Normal termination` ×2, identical
   across the last 3 SCF evaluations) rather than citing proposer13, and states plainly why this is
   not the fixture channel.
4. **`U56.sh:136-138` — fixed, and better than the deletion I asked for. [확인]** It now reads
   *"`SEI_C8_ENDPOINTS_JSON` (below) is NOT a remedy for that case — see the corrected note further
   down in this file's own `PYBPLUS` block (search this file for \"does NOT backfill\" — not a line
   number, which ...)"*. Cross-referencing by searchable string instead of line number is the right
   fix for a file whose line numbers demonstrably drift; the contradiction is gone.
6. **Decks untouched, scope clean, tests pass. [확인]** All six deck artefacts still `15:46:52`;
   changes since 16:00 are only `README.md`, the two `.pbs` files, `payload/U56.sh` and two docs.
   Both PBS still carry the consumed/reserved labelling and `walltime=02:00:00`.
   `test_u56_bplus_reverse_opt` → **6 tests, OK**.

## ❌ Did not land

- **Item 5 — the `sed` range is STILL wrong, and the command fails when run. 🔴 [확인]** The README
  says `sed -n '1071,1162p'` and states the delimiters are `:1070`/`:1163`. The live file:

        grep -n "PYBPLUS" src/pilot_package/payload/U56.sh
        1074:  ... <<'PYBPLUS'          <- opening delimiter
        1167:PYBPLUS                    <- closing delimiter

  So the body is **`1075,1166`** — the README is off by 4 at both ends. Run verbatim, its command
  produces a file that begins with shell text (`else`, `echo "[U56] B+ ${dir}: start points
  unavailable ..."`) and ends mid-statement inside `json.dump(`; `python3` on it raises
  **`IndentationError: unexpected indent`**. Verified `sed -n '1075,1166p'` starts at
  `import json, os, sys` and ends on the closing `print(...)`, and parses.
  → **This is the second drift of this number today**, and the cause is now self-inflicted: the
  item-4 comment edit at `:136-138` pushed everything below it down by 4 *after* the range was
  recomputed. The README's own "re-check this range against the live file" warning is what keeps
  this honest — but a documented command that is wrong on arrival makes that warning load-bearing
  every single time, and it will drift again on the next comment edit.
  → **Fix, tested here, no new code and no re-check step**: anchor on the delimiters instead of
  line numbers —

        awk "/<<'PYBPLUS'/{f=1;next} /^PYBPLUS\$/{f=0} f" src/pilot_package/payload/U56.sh \
          > /tmp/bplus_compute.py

    I ran it: parses clean and is **byte-identical** to `sed -n '1075,1166p'`. It cannot drift,
    which retires the whole class of defect rather than patching today's instance.
- **Item 2 — the wrong-sibling carry did not land. 🔴 [확인]** `grep -i` for `reactant_source`,
  `solvent_config`, `epsinf`, `sibling` across the README returns **nothing**. The README names the
  correct directory and shows the route/charge/mult check (which would catch a `solvent=generic`
  sibling *if* the reader compared them), but it never tells the reader to locate the log via
  `endpoint_certs.json`'s own `reactant_source` / `solvent_config` fields, and never warns that four
  near-identical siblings exist. The hazard, restated from the 38차 batch: `endpoint_prep_reactant_
  epsinf_full/endpoint_tight.log` is **2.6e-5 eV away** from the right value and one glob
  (`endpoint_prep_reactant*`) from being picked. I made this exact mistake myself on first pass.
- **Item 3 — the marginal-reading carry did not land. 🔴 [확인]** `grep -i` for `marginal` returns
  nothing. `energy_delta_ev` appears only in step 5's restatement of the pass criterion and in the
  dry-run quote. There is no instruction to record the measured value, and no rule for reading a
  result materially above ~4e-4 while under 1.0e-3 as marginal → proposer review. As written, step 5
  still frames the outcome as a boolean, which is the framing the 38차 batch flagged.

## 부수 — the lead's sanity check on the dry run: the reading is right

`reactant_match(last)=True` with `energy_delta_ev = 0.000413 eV` on the OLD points is exactly what
should be expected, and it is a useful confirmation rather than a coincidence: the old
`bplus_reverse_last` optimisation converged to the certified reactant, so the residual energy
difference is the **tight-vs-loose method offset alone** — and `guards.py:579` records that offset,
measured independently on this same pair, as **Δ = -4.13e-4 eV**. The two agree to three significant
figures. That is a clean cross-check of the backfilled pipeline.
It also confirms the 38차 framing empirically rather than by argument: with the systematic already
consuming 0.000413 of the 0.001 eV tolerance, **59% of the budget is what remains for real physical
signal** on the new points. Discrimination is safe (the coordination-isomer hazard is 0.686 eV, 686x
the tolerance), but this is precisely why the measured number, not the boolean, is what should be
reported — which is item 3.

**Reported to**: `coder16` (the three misses, with the tested `awk` replacement), team-lead
(NOT OK, do not tar).

---

## 2026-08-25 (40차 배치) — critic17: item 5 fixed at the root; items 2 and 3 missed a second time

**Scope**: the three outstanding items from the 39차 batch.

## 판정
**NOT OK — still do not tar, but the remainder is now two paragraphs of README text.** Item 5 is
fixed properly and at the root. **Items 2 and 3 have now been asked for twice and are still absent**
— they were not mentioned in `coder16`'s report either, which is how a carry gets lost rather than
declined.

## ✅ Item 5 — fixed at the root, and verified by running it verbatim. [확인]

The README no longer hardcodes a line range. Its command, run exactly as printed:

    awk "/<<'PYBPLUS'\$/{flag=1;next}/^PYBPLUS\$/{flag=0}flag" src/pilot_package/payload/U56.sh \
      > /tmp/bplus_compute.py
    python3 -c "import ast; ast.parse(open('/tmp/bplus_compute.py').read())"

→ 92 lines, starts at `import json, os, sys`, ends on the closing `print(...)`, `ast.parse` clean,
zero `PYBPLUSPICK`/`BPLUS_PTS=` contamination. The collision claim is sound and I checked the
mechanism rather than accepting it: the `$` anchor is what does the work — `<<'PYBPLUSPICK'`
(`:1037`) cannot match `/<<'PYBPLUS'$/`, and the literal word `PYBPLUS` inside the comment at `:138`
cannot match `/^PYBPLUS$/` because that line starts with whitespace and `#`. Adding the `ast.parse`
line is the right instinct independent of the anchor: it converts a silent truncation into a loud
failure, which is exactly what the two previous drifts lacked.
**This is the better outcome than the fix I asked for.** I flagged one wrong number; `coder16`
removed the whole class, including the other hardcoded line-number citations in both the README and
their own new `U56.sh` comment. Three of this session's defects (§39.130's misquote, the workaround
pointer, this) were stale cross-references; retiring the mechanism beats correcting the instance.

## ❌ Items 2 and 3 — absent for the second consecutive pass. [확인]

`grep -i` over `pilot_tests/bplus_reverse_new_2026-08-25/README.md`:
`reactant_source` / `solvent_config` / `epsinf` / `sibling` → **no matches**;
`marginal` / `4e-4` / `4.13` → **no matches**. Restating both, minimally, so they can be pasted:

- **(2)** The README must say to locate the reactant log via `endpoint_certs.json`'s own
  `reactant_source` (`"cert:endpoint_prep(endpoint_prep_reactant)"`) and `solvent_config`
  (`solvent=acetone, eps=18.5`) fields — **not** by `find`/glob — and must name the hazard: four
  near-identical siblings exist, of which `endpoint_prep_reactant_epsinf_full/endpoint_tight.log`
  is **2.6e-5 eV** from the right value, uses `solvent=generic`, and matches the glob
  `endpoint_prep_reactant*`.
- **(3)** Step 5 must instruct recording the measured `energy_delta_ev`, and reading a value
  materially above ~4e-4 eV while still under 1.0e-3 eV as **MARGINAL → proposer review**, not as a
  clean boolean pass.

## 부수 — full pipeline re-run cold, independently

Fresh `cp -r`, backfill applied by hand, `coder16`'s own awk extraction, run cold:

    [U56] B+ reverse: agreement=True reactant_match(mid/last)=True/True
    agreement: True   energy_delta_ev: 0.00012677784731211835
    last: distance clause PASSES: worst break-bond delta 0.0005 A against tolerance 0.0500 A
          energy   clause PASSES: 0.000413341 eV against tolerance 0.001 eV

Reproduces `coder16`'s report exactly, and `0.000413341` matches `guards.py:579`'s independently
measured tight-vs-loose offset (`-4.13e-4 eV`) to three significant figures — the backfilled
pipeline is sound. It also puts a sixth digit on the 38차 framing: the systematic consumes
**41.3%** of the 0.001 eV tolerance, leaving 58.7% for real physical signal on the new points. That
number is the entire reason item 3 exists.

`bash -n payload/U56.sh` passes. All six deck artefacts still `15:46:52` — untouched across three
rounds of documentation edits. `test_u56_bplus_reverse_opt` → 6 tests, OK.

**Reported to**: `coder16` (items 2 and 3, restated as paste-ready text), team-lead (NOT OK; the
remainder is two paragraphs).

---

## 2026-08-25 (41차 배치) — critic17: B+ closing jobs — OK, all six items closed

**Scope**: items 2 and 3 from the 39/40차 batches, plus a final end-to-end re-verification of the
whole directory against the current files.

## 판정
**OK — clear to tar.** All six of the lead's checklist items are closed. Nothing outstanding from me
on this work item.

## 확인

- **Item 2 — landed, and better than my version. [확인]** `README.md:111-126` leads with
  *"Wrong-sibling hazard — locate this log by PROVENANCE, never by `find`/glob"*, says outright "do
  not search for `endpoint_tight.log` by filename", and gives the provenance path: take the
  directory from `endpoint_certs.json`'s `reactant_source` first element
  (`cert:endpoint_prep(endpoint_prep_reactant)`), then cross-check `reactant_cert.solvent_config`
  contains `eps=18.5`.
  **`coder16` corrected me on the facts and is right**: I wrote "four near-identical siblings"; the
  precise statement is **five** `endpoint_tight.log` files, enumerated by name, of which only three
  match the `endpoint_prep_reactant*` glob and two (`endpoint_prep_rc_reactant`,
  `endpoint_prep_product`) are different systems entirely. They got that by running `find` rather
  than assuming the naming pattern — the same discipline I had asked for, applied to my own claim.
  Their independently re-derived ε∞ delta (**2.571e-5 eV**) also matches mine
  (9.45e-7 Hartree × 27.2114 = 2.5717e-5 eV) and is quoted at the right precision.
- **Item 3 — landed with a usable decision rule, not just the number. [확인]**
  `README.md:183-192` carries the Δ = -4.13e-4 eV systematic and the **41% of the 1.0e-3 eV budget**
  framing, then states the rule in two branches: comfortably below ~4e-4 = clean pass; materially
  above ~4e-4 while under 1.0e-3 = **MARGINAL, flag for `proposer` review, do not read as a boolean
  pass closing condition 7 outright**. It cites `guards.py`'s own caveat verbatim as the authority,
  and applies the rule to the dry-run's own `0.000413 eV` to demonstrate it reads as clean (matching
  the known systematic, not exceeding it). Step 5's heading is now *"record the number, not just the
  boolean"* — which is the behaviour change the item was for.
- **Item 5 — re-verified against the current file. [확인]** `coder16` notes their awk switch and my
  39차 finding crossed; correct, and no further action. Re-ran the README's own command verbatim
  against `U56.sh` **as it stands after today's further comment edits**: 92 lines, `ast.parse` OK.
  This is the point of a delimiter-anchored extraction — it survived two more edits to the file
  without anyone re-checking a number.
- **Step renumbering — checked, coherent. [확인]** `coder16` found and fixed stale step references
  on their own pass (not something I flagged). Verified the result: steps run 1-5 with no gaps or
  duplicates, and every internal reference resolves correctly — "see step 4 below for why" (the
  extraction step), "steps 2-5 above produce…" (the dry-run summary), "do not use it for step 2
  above" (the backfill), "do not run step 4 with `pick_status=ok`" (the run). No dangling pointer.
- **Full pipeline, re-run cold against current files. [확인]** Fresh `cp -r`, backfill applied,
  README's own awk extraction, run as instructed:
  `[U56] B+ reverse: agreement=True reactant_match(mid/last)=True/True`. `bash -n payload/U56.sh`
  passes. `test_u56_bplus_reverse_opt` → 6 tests, OK.
- **Decks untouched through five rounds of documentation edits. [확인]** All six artefacts
  (`.gjf` ×2, `.xyz` ×2, `manifest_*.json` ×2) still carry mtime `15:46:52` — the same timestamp
  they had when I first verified their geometries against `parse_irc_path_frames` in the 36차 batch.
  Everything since has been documentation; the reviewed payload never moved.

## Standing items, unchanged and not mine to close

- The package remains diverged from `src/` across **ten** files including every builder this work
  item produced (`test_build_stamp`'s standing red). Non-blocking while hand-staged; the gate before
  anything ships from the package rather than from a staging directory.
- `test_session_digest.TestAgainstRealDocs` (R-10) still red, pre-existing, untouched all round.

**Reported to**: team-lead (OK, clear to tar), `coder16` (both items confirmed; their correction to
my sibling count accepted).

**Addendum to the 41차 batch** — `coder16` tightened the README once more *after* that batch's
verification (mtime `16:19:38`, content-only). Re-verified against the newer file rather than
letting the earlier OK stand on a superseded state:

- Both markers still present (`reactant_source` ×1, `marginal` ×3). The two additions are factually
  correct and I checked each against the source rather than the report: the ε∞ sibling's route
  really is `scrf=(pcm,solvent=generic,read)` (not `solvent=acetone`), which is a **better tell than
  the energy delta** — a route line is unambiguous where 2.6e-5 eV is not; and "5 hits: the 4 WRONG
  siblings above plus the 1 correct one" reconciles my count with theirs accurately (1 correct +
  4 others, of which only `endpoint_prep_reactant_epsinf_full` and
  `endpoint_prep_reactant.reset.*` are the same system). The text also now names the glob trap
  explicitly (`endpoint_prep_reactant*` matches the ε∞ sibling).
- Nothing regressed: steps still run 1-5 with every internal reference resolving; the README's own
  awk extraction still parses clean against current `U56.sh`; the full pipeline re-run cold still
  gives `agreement=True reactant_match(mid/last)=True/True`; `test_u56_bplus_reverse_opt` 6/6.
- **Decks still `15:46:52`**, PBS still `16:02`. Six rounds of documentation edits, payload untouched.

**Verdict unchanged: OK, clear to tar.**

---

## 2026-08-25 (42차 배치) — critic17: §39.133 verified cold, and the exhaustive condition-2 audit

**Scope**: the lead's two pre-closure tasks. Abbreviations: **U-56a** = the eight-condition gate on
this project's first production TS+IRC run; **condition 2** = *"nosymm on every route from the
perturbation onward; the point group emitted from the log at step 1 AND at convergence, as DATA"*
(`02_METHOD_SPEC.md:11511-11512`); **B+** = the two-point terminal-optimisation comparator;
**branch (b)** = condition 7's `maxpoints` + B+ establishment route.

## 판정
**Task 1 (§39.133): CONFIRMED**, every number reproduced independently, and the distance clause is
**not** degenerate — verified from raw coordinates, with a decomposition §39.133 does not contain.
**Task 2 (condition 2): CLEAN on the `nosymm` half — 16/16 evidence-bearing routes — but the second
half of the clause is NOT satisfied as written.** No artifact anywhere in the chain records the
point group. The *fact* of C1 is established beyond doubt from the primary logs (I checked nine),
so this is a **recording gap, not an evidentiary one** — but it is the literal text of condition 2,
and whether the ADR may close over it is a spec reading for `proposer13`/the lead, not mine.

## Task 1 — §39.133, re-run cold from a fresh working copy

Fresh `cp -r` of `U56_RA_scan`, backfill applied by hand, the two REAL returned logs copied in, the
README's own `awk` extraction (`ast.parse` clean), run as documented. Output:

    agreement: True      energy_delta_ev: 0.0004197356332540831
    reactant_match["last"]: match=True
      distance clause PASSES: 0.00013324 A  (tolerance 0.05 A)
      energy   clause PASSES: 0.00026727 eV (tolerance 0.001 eV)

**All four branch-(b) clause values reproduce.** One transcription-level note: §39.133 quotes the
distance as `0.0001337` Å; the run gives `0.00013324` Å. Same run (the energy and agreement figures
match to all quoted digits), a mis-transcribed 4th significant figure, **no consequence whatever** at
375x below tolerance — recorded only so a future reader diffing the two does not think they are
looking at two different runs.

**The sign flip — checked against the raw signed energies, and §39.133's reading holds.** NEW:
`-349.620887192 − (-349.620897014) = +9.822e-6` Ha = +2.673e-4 eV (loose point *above* the tight
reactant, the physically expected direction). OLD: `-349.620912204 − (-349.620897014) = -1.519e-5` Ha
= -4.13e-4 eV. `guards.reactant_match` stores `abs(...)` (`guards.py:520`), so the sign cannot reach
the gate. The "two-sided noise around a shared floor" reading is sound, and I would add one point in
its favour that §39.133 does not make: the two samples come from **different geometries** (Candidate
B's Point 70 at arc 4.78 vs the old path's endpoint at arc ~1.7), so they are genuinely independent
draws, not a repeated measurement that changed sign.

### The distance clause — "would it look any different if the claim were false"

The lead flagged `1.3e-4 Å` as suspiciously small. It is **real and non-degenerate**, and here is the
evidence rather than the assurance:

- **The pair is the right one.** `u56_R-A_mapping.json` gives `break_roles = [["O_ether","C_sp3"]]`
  with `O_ether: [1,4]`, `C_sp3: [2,3]`; the guard selects indices (1,2) = **O(2nd atom), C(3rd)** —
  the alkyl C–O bond this reaction breaks ("LiEC(radical) ring-opening via the ALKYL C-O"). Confirmed
  the elements at those indices are O and C in both structures.
- **I recomputed both distances myself** from `reactant_certified.xyz` and the last orientation block
  of the NEW `bplus_reverse_last.log`: reactant `1.4143065182` Å, point `1.4144397553` Å, delta
  `0.0001332371` Å — **reproducing the guard's own `reactant_ang`/`point_ang`/`delta_ang` to ten
  decimals.** Not a degenerate self-comparison: the two coordinate sets are different objects
  (they do not even share a reference frame).
- **And the decisive check the gate does not perform** — a frame-invariant comparison of all 55
  internal distances:

        organic core only (10 atoms, 45 pairs)   RMS = 0.005789 A   max = 0.018999 A
        Li-to-everything      (10 pairs)          RMS = 0.227263 A   max = 0.479891 A

  So the two structures are **not** geometrically identical: the organic framework agrees to 0.006 Å
  RMS, while Li's distances to the far side of the molecule differ by up to **0.48 Å**. Decomposed
  atom by atom, Li's *primary coordination is preserved* — `Li–O_carbonyl 1.8613 → 1.8545` Å
  (−0.007) and `Li–C0 2.8456 → 2.8490` (+0.003) — while `Li–O_ether 3.1133 → 3.3592` (+0.246) and
  the long Li···H distances grow by 0.19-0.48 Å. That is a **soft tilt/rotation about a retained
  Li–O_carbonyl contact, not a change of coordination site.**
  **This strengthens §39.133 rather than undermining it**, and on evidence the ruling does not cite:
  the named hazard for this clause is a coordination isomer sharing a covalent graph and a
  break-bond distance (`guards.py:574-576`, §39.42(a), 0.686 eV apart). A genuine isomer would show
  Li on a *different* donor; here Li–O_carbonyl is conserved to 0.4% and Li–O_ether stays >3.3 Å
  (non-bonded). The energy clause says the same thing independently: 2.673e-4 eV is **2,500x below**
  the isomer separation.
  **One wording consequence for the ADR**: "the reverse endpoint matches the certified reactant" is
  true in the ruled sense (graph + break bond + energy) but is **not** geometric identity. §39.133
  quotes `li_displacement_ang = 0.0573 Å` for *mid vs last*; the reactant-vs-last Li difference is an
  order of magnitude larger. Do not let the 0.0573 figure be read as the reactant-vs-endpoint one.

## Task 2 — condition 2, exhaustive

**Scope, read from the ruled text first** (`:11511-11512`): *"nosymm on every route from the
perturbation onward"*, the perturbation being C-9's, ruled to sit **before endpoint-prep stage 1**
(§39.x: *"nosymm + the C-9 perturbation belong to the ROUGH stage, perturbation BEFORE stage 1"*, and
`endpoint_opt_rough`/`endpoint_opt_freq` were added to `_nosymm_required_job_types` for exactly this).
So the endpoint certification jobs are **in** scope, not only the TS chain. Audited against that.

### (a) `nosymm` — CLEAN SWEEP, 16/16 evidence-bearing routes

| file | route (abbrev.) | nosymm |
|---|---|---|
| `endpoint_prep_reactant/endpoint_rough.gjf` | `opt=(loose,maxcycles=100)` | ✅ |
| `endpoint_prep_reactant/endpoint_tight.gjf` | `opt=(tight,calcfc,maxcycles=200) freq` | ✅ |
| `endpoint_prep_product/endpoint_rough.gjf` | `opt=(loose,maxcycles=100)` | ✅ |
| `endpoint_prep_product/endpoint_rough_alt.gjf` | `opt=(loose,maxcycles=100)` | ✅ |
| `endpoint_prep_product/endpoint_tight.gjf` | `opt=(tight,calcfc,maxcycles=200) freq` | ✅ |
| `U56_RA_scan/scan.gjf` | `opt=(modredundant,maxcycles=100)` | ✅ |
| `U56_RA_scan/scan_refine.gjf` | `opt=(modredundant,maxcycles=100)` | ✅ |
| `U56_RA_scan/ts_opt.gjf` | `opt=(ts,calcfc,noeigentest,maxcycles=100) freq` | ✅ |
| `U56_RA_scan/irc_forward.gjf` | `irc=(calcfc,forward,maxpoints=30)` | ✅ |
| `U56_RA_scan/irc_reverse.gjf` | `irc=(calcfc,reverse,maxpoints=30)` | ✅ |
| `U56_RA_scan/bplus_forward_{mid,last}.gjf` | `opt=(loose,maxcycles=100)` | ✅ ✅ |
| `U56_RA_scan/bplus_reverse_{mid,last}.gjf` | `opt=(loose,maxcycles=100)` | ✅ ✅ |
| `candidate_b_reverse_stepsize_2026-08-25/irc_stepsize_probe.gjf` | `irc=(calcfc,reverse,recorrect=never,stepsize=2,maxpoints=70)` | ✅ |
| `bplus_reverse_new_2026-08-25/bplus_reverse_{mid,last}.gjf` | `opt=(loose,maxcycles=100)` | ✅ ✅ |

**And it was honoured, not merely requested** — the B-2 hazard the spec names is G16 re-detecting
symmetry and undoing the perturbation, which only the *log* can settle. Nine evidence logs, first and
last occurrence of the point-group banner in each: **all report `Full point group C1 NOp 1`**
(`endpoint_rough`, `endpoint_tight` ×2 endpoints, `ts_opt`, `irc_forward`, `irc_reverse`,
`irc_stepsize_probe`, both new `bplus_reverse_*`). Occurrence counts 5-72 per log; first and last
agree in every one. **Step 1 and convergence both C1, measured, in every evidence-bearing job.**

**A false alarm I chased down rather than reported**: a naive sweep of all 197 `.gjf` in the tree
shows **124 without `nosymm`**, six of them inside U-56a's own job directories. All six are
`smoke/smoke_L{1,2}.gjf`, and they are **H₂** — two hydrogens 0.74 Å apart, charge 0, multiplicity 1
— single-point route/basis/solvent syntax probes, not the reaction system. They optimise nothing (so
no perturbation can be undone), contribute to no condition, and their job_type `sp` is deliberately
absent from `_nosymm_required_job_types`. Their logs' `D*H` point group is simply H₂'s correct
symmetry. **Not a gap.** Recording the chase because "124 routes lack nosymm" is what this audit
would have said if I had stopped at the grep.

### (b) "the point group ... as DATA" — 🔴 NOT SATISFIED AS WRITTEN

The clause has two halves and the second one is a *recording* requirement: the point group must be
emitted **as DATA** ("so 'symmetry was broken' is a measurement, §0-g's order"). Searched every JSON
artifact in `U56_RA_scan/`, both `endpoint_prep_*` job dirs and the staged directories:

- **No artifact records a point-group value.** Every occurrence of the string `point_group` in
  recorded data is the field **`"is_point_group_detection": false`** —
  `endpoint_prep_{reactant,product}/f1_observables.json` (`symmetric_fingerprint_at_convergence`),
  the same two jobs' `stage1_exit_structural_set.json`, and `U56_RA_scan/c8_precondition.json`
  (`symmetric_placement_fingerprint`). What those record is `"check_name":
  "heavy_atom_coplanarity_only"` — a narrower geometric heuristic which, to its credit, **says
  outright that it is not a point-group detection**.
- The machinery exists and is unwired for this: `criteria/g16.py:944` defines `parse_point_group()`,
  and `collect.py:879` carries a `stored_point_group` field — neither reaches any artifact in this
  chain.
- `ts_opt.meta.json`, `irc_reverse.meta.json` and `deck_verification.json` contain no point-group
  field at all.

**How to read this, stated precisely so the ADR can be written either way**: the substantive
requirement — that symmetry was broken and stayed broken, at step 1 and at convergence — **is
satisfied and I verified it directly on nine primary logs**. What is missing is the clause's
*form*: it is not recorded as structured data, so today the only evidence is this audit and the raw
logs. Against ADR-116's precedent (a closure claimed on a condition nobody had re-derived), the
difference matters: this one has now been re-derived, exhaustively, from primary sources. Whether
that discharges "as DATA" or whether the emit-list must be wired first is `proposer13`'s call.
Wiring it appears cheap (the parser exists), and it is the kind of thing far easier to add before a
closure ADR than to retrofit after one.

## 확인하지 못한 것

- The other six conditions. I audited condition 2 as asked and verified condition 7's branch (b);
  conditions 1, 3, 4, 5, 6 stand on prior record and I did **not** re-derive them this round. If the
  ADR is to claim all eight, someone should say plainly which of the other five have been
  independently re-checked and when — the same question that produced ADR-116.

**Reported to**: team-lead (both tasks; the recording gap flagged as a spec-reading call, not a
unilateral BLOCKER), `proposer13` (the "as DATA" reading and the Li-decomposition strengthening).

---

## 2026-08-25 (43차 배치) — critic17: wave-1 combined verification pass (six items, proposer13's pre-commit gate)

**Scope**: the six builds the lead listed. Abbreviations: **wave 1** = the S3 attempt round specified
by §39.136; **STOP_AFTER** = `SEI_U56_STOP_AFTER`, the staged circuit-breaker env flag;
**T21-se** = the 21-atom attempt whose stage-1 cost is being measured before stage 2 is paid for;
**stage 0** = the 12-seed unbiased-MD rediscovery comparator; **sealed file** =
`config/stage0_sealed_targets_T1-T4.json`, proposer13's pre-registered T1-T4 target list.

## 판정
**FIX-THEN-RUN.** Priority 2 (the package) is **fully verified and clears its gate**. Priority 1's
unset path is verified bit-identical, but **one defect in the deliberate-stop path defeats the
circuit breaker's purpose and must be fixed before T21-se runs through it**. Items 3, 4, 6 carry one
defect each, none blocking. Item 5 is clean on its stated claims with one hardening worth taking.

## 🔴 BLOCKER-class — the circuit breaker's stop is classified as a retryable failure

`payload/U56.sh:86` writes terminal status **`stopped_after_stage`**, and **nothing consumes it**.
Confirmed by execution, not by reading:

    stopped_after_stage      cause=unknown      should_retry=True
    ts_candidate_produced    cause=success      should_retry=False
    wall_exhausted           cause=budget       should_retry=False

`outcome.py:24-27` states the rule itself: *"An unlisted status is `unknown` (and therefore
retried), so a payload that invents a new status string without adding it here gets a loud retry,
not a silent skip."* `stopped_after_stage` is not in `CAUSE_BY_STATUS` (grep: it appears in exactly
two places in the whole tree — the writer at `U56.sh:86` and the assertion at
`tests/test_u56_stop_after.py:115`), so it falls to `unknown`, and `unknown ∈ RETRY_CLASSES`
(`outcome.py:66`).
→ **Consequence, and it is the precise inverse of the feature's purpose**: the circuit breaker exists
so that T21-se's stage 1 runs ALONE and the harness stops until a human reads the real cost. Under
the scheduler, that deliberate stop is now read as an unknown failure and **re-queued**. The job
re-runs stage 1 — the expensive stage this protocol exists to meter — stops again, and repeats,
spending exactly the budget the staged protocol was built to control while producing what
`outcome.py`'s own `input_defect` comment calls "the appearance of effort".
→ **Fix**: add `stopped_after_stage` to `CAUSE_BY_STATUS` in a class that is **not** in
`RETRY_CLASSES` and **not** `SUCCESS` (it is neither a failure nor a completion). The existing
classes do not have an obvious home for "deliberate operator-requested halt" — `budget` would work
mechanically and read wrong; a new non-retry class is cleaner. **That taxonomy choice is
`proposer13`/`coder16`'s, not mine** — the constraint is what I am asserting: it must not retry and
must not read as success. A test asserting `should_retry(cause_for("stopped_after_stage")) is False`
would have caught this and belongs with the fix.

## Item 1 — STOP_AFTER, the rest

- **UNSET path: verified bit-identical in behaviour. [확인]** The change is additive and minimal:
  one function (`_sei_u56_stop_after_check`, `:83-90`) whose first line is
  `[ "${SEI_U56_STOP_AFTER:-}" = "$1" ] || return 0`, and **exactly one call site** (`:641`). I
  executed the real function under four environments:

        UNSET              -> no output, rc 0, execution continues
        SET to another stage-> no output, rc 0, execution continues
        SET to ""          -> no output, rc 0, execution continues
        SET to u56_scan    -> message, _write_terminal, exit 5

  The payload runs under `set -u` only (`:34`, no `-e`), so a `return 0` cannot alter control flow.
  With the variable unset the entire delta is one no-op call. **proposer13's blocking sequencing
  requirement is met.**
- **Deliberate-stop path mechanics: correct apart from the taxonomy defect above. [확인]** exit 5
  matches the documented exit map (`:31`), and `_write_terminal` (`:48-50`) routes through
  `sei_terminal` with reaction/method/level context, i.e. the C-13 mechanism, not an ad-hoc marker.
- **Wall-tripwire "comment substring collision": does not exist in this file, and the real ordering
  is untouched. [확인]** The scanner uses a bare `re.finditer(r"sei_stage ")` over the whole source,
  which would count a comment. Measured: **6 lines contain `sei_stage `, all 6 are real call sites,
  0 in comments.** Trap armed at `:101`, first real call `:640`, last `:1115`, trap disarmed
  `:1264` — armed before the first and disarmed after the last, substantively. And the new check is
  placed **after** its stage completes (`U56_CURRENT_STAGE=u56_scan` → `sei_stage u56_scan …` →
  `_sei_u56_stop_after_check u56_scan`), so no `sei_stage` call was reordered.
  **사소**: the scanner remains fragile by construction — one future comment containing
  `sei_stage ` would corrupt its min/max. The sibling test in the same file already filters with
  `re.match(r"\s*(&&\s*)?sei_stage ", line)`; using that filter in both would retire the fragility.
  Same class as the line-number drift retired yesterday.
- `test_u56_stop_after` + `test_u56_wall_tripwire`: **12 tests, OK.**

## Item 2 — the package rebuild: VERIFIED, gate retired

Ran the critic12/13 pattern rather than reading the report.

- `sha256sum src/dist/sei_pilot_cpu.tar.gz` = `98bc5dab…2853d9`, **matches its `.sha256` file**.
- **Extracted the tarball and compared every stamped file against `src/`: 116/117 byte-identical.**
  The 117th is `README_USER.gpu.md`, explained and then confirmed: the CPU tarball ships
  `README_USER.md`, and `cmp` proves it equals `src/pilot_package/README_USER.cpu.md` — a build-time
  rename, not a divergence.
- **`package_fingerprint` recomputed BY ME from the extracted tarball** (not from `src/`):
  **`b5198f100497b3e6`** — matches coder16's reported value exactly.
  `source_digest bfb592af252119ef`, `n_files 117` as stated. (Note the build's own warning, which is
  correct and worth keeping: the tarball `sha256` changes on every rebuild because gzip stores an
  mtime — identity comparisons must use `source_digest`, not the sha256.)
- `payload/U56.sh` **in the tarball is byte-identical to `src/`**, carries the STOP_AFTER change
  (5 occurrences), and passes `bash -n` **as extracted**.
- `test_build_stamp`: **20 tests, OK** — the ten-file divergence gate is retired.
- **Full suite: `Ran 1799 tests … OK (skipped=14)`, zero failures**, matching the reported 1799/0.
  Both standing reds from this whole round (`test_build_stamp` ×2, `test_session_digest` R-10) are
  now green. **This is the first fully green suite I have seen in this engagement.**

## Item 3 — R-10 renderer: bounded against the vector that caused it

- **Bounded by construction on the growth path that matters. [확인]** I drove the renderer with
  synthetic rosters rather than trusting today's document:

        active=5  stopped=17   -> 46 lines
        active=5  stopped=50   -> 46 lines
        active=5  stopped=200  -> 46 lines     <- flat: the stopped roster cannot grow the digest
        active=20 stopped=50   -> 76 lines
        active=60 stopped=50   -> 156 lines

  R-10's actual cause was the **monotonically accumulating stopped roster** (this project has
  retired 17+ teammates and never removes one). That term is now flat at any size. ✓
- **The residual, named rather than glossed**: the active roster is **uncapped by design**
  (`render.py:138-142`), so total length is `constant + 2·len(active)` — linear and unbounded in
  principle. That is a deliberate trade (`:133-135`: you must always see who is working now), it
  does not accumulate (active count falls when teammates stop), and it is operator-controlled. Not a
  defect; worth stating so nobody later reports "R-10 regressed" when a 12-teammate round renders
  long.
- **The reorientation purpose survives. [확인]** What is capped is *history* (stopped teammates);
  what is uncapped is *current state* (active, and the `--full` escape restores everything). Real
  digest measured: **76 lines default, 136 with `--full`** (coder16 reported 97→77; the 1-line
  difference is trailing-newline counting).

## Item 4 — `qc_levels.json` IRC templates: correct where ruled, one latent trap

- **Ruled change present. [확인]** `irc_forward`/`irc_reverse` now read
  `irc=(calcfc,{direction},recorrect=never,maxpoints=30)` — `recorrect=never` added,
  **`maxpoints` still explicit** (§39.136(2)'s "EXPLICIT `maxpoints` … avoids the
  unwired-maxpoints artifact class"), `nosymm` retained.
- 🔴 **`irc_forward_rcfc` / `irc_reverse_rcfc` did NOT get `recorrect=never`.** They read
  `irc=(rcfc,{direction},maxpoints=30)`. The corrector failure mode `recorrect=never` fixes is a
  property of the corrector, not of where the Hessian came from, so the ruling's stated basis
  ("adopted as the production default") applies to them identically.
  → **Latent, not active**: I verified the switch is off — `b0_reactions.json` has
  `irc_hessian_source = calcfc`, and `_irc_rcfc_note` says the lead turns rcfc on only after a route
  smoke. So wave 1 will not hit it.
  → **But it is a trap on a documented future action.** That same note ends *"켜면 그대로 동작해야
  한다"* (when switched on it should just work). Whoever flips that one config value gets IRCs
  running with the **default corrector** — the exact setting that killed both R-A arms — while every
  other IRC in production carries `recorrect=never`, and nothing would flag it. Two words in the
  template now removes it.

## Item 5 — R-B submission builder: claims hold; one hardening worth taking

- **Byte-diff claim CONFIRMED. [확인]** `diff` of the generated `U56_RB_scan_wave1.qsub` against the
  real returned `U56_RB_scan.qsub`, with the job key substituted, is **empty**. The wall time
  (`10:56:15`) and `select=1:ncpus=64:mpiprocs=64` are inherited from the real returned job, not
  invented — the right provenance for a redo.
- **Deployment provenance — the honest answer is "a path, not a package".** The generated qsub sets
  `SEI_PKG_ROOT=/scratch/…/sei_pilot_cpu` and the cmd runs
  `bash /scratch/…/sei_pilot_cpu/payload/U56.sh`. It therefore runs **whatever is unpacked at that
  path when the job starts** — the rebuilt package only if someone deployed it. There is no digest
  assertion. **coder16 documented this** (`rb_redo/README.md:75-82, 103-106`, including that
  `recorrect=never` "only takes effect if the deployed package" is the new one), so it is not an
  undocumented trap — but the failure is silent and severe: with a stale package on the cluster,
  `SEI_U56_STOP_AFTER` is an unrecognised variable that is **ignored**, and T21-se's staged stage-1
  run would proceed through every stage.
  → **Cheap hardening, and I verified the anchor exists**: `BUILD_STAMP.json` is not shipped in the
  tarball, but `sei_pilot/version.py` is — I recomputed `b5198f100497b3e6` from the extracted package
  with `version.provenance(root=…)`. Three lines in the qsub can compute the deployed root's
  fingerprint and refuse if it is not `b5198f100497b3e6`, turning a silent wrong-package run into a
  loud refusal. Same lesson as the `grep -a` fix: a check that exists only as prose is a check that
  is skipped.

## Item 6 — stage 0: protocol and blindness verified; the manifest does not reproduce

- **Protocol matches §39.47(b). [확인]** `N_SEEDS=12`, `TIME_PS=100.0`, `nvt=true`, unbiased
  (`stage0_md.sh:2,6-8` and the header's explicit "NOT metadynamics"), 1500 K, `seed=${i}` for
  i=1..12 so every trajectory's seed is fixed and recorded — reproducibility by construction.
  Sizing: 12 cores (one per seed), 6 h wall against the measured 0.54 h/100 ps single-seed anchor.
- **ADR-110 explicit xtb cores. [확인]** `OMP_NUM_THREADS=1` per seed, with `"cores": 1` written
  into each seed's own record — explicit, matching the anchor the wall-time figure was measured
  against, not a scheduler default.
- **Sealed file: hash confirmed and it binds the structure. [확인]**
  `sha256(config/stage0_sealed_targets_T1-T4.json)` = **`69ce2848ca346ccc107178104b85dcc4cb7a4321
  2d71bb7c966f6450bbc3f2c2`**, matching proposer13's stated `69ce2848…` and the package's own
  `BUILD_STAMP` entry. Its `reactant_xyz_sha256` = `8cdbf3e84f0efebc…` and I recomputed the actual
  `inputs/li_ec2_radical_reactant.xyz` — **identical**. The seal binds the exact structure that
  ships in the package.
- **Blindness boundary: HOLDS. [확인]** Every reference to the sealed file anywhere in
  `payload/`, `sei_pilot/` and `tools/` is a **comment**. Grepping the filename
  `stage0_sealed_targets` across all `.py`/`.sh` while excluding comment lines returns **nothing** —
  no import, no `open()`, no path. The classifier reads only the job dir and `time_ps`, and derives
  events from generic graph perception (`xyzgraph.bond_list`/`connected_components`), with the
  starting state honestly documented as 3 covalent fragments so a baseline is not mistaken for an
  event.
- 🔴 **The staged `manifest.json` does not reproduce from the current builder.** A fresh run of
  `tools/build_wave1_stage0_submission.py` produces `.qsub` and `.cmd.sh` **byte-identical** to the
  staged ones, but a manifest that differs in three keys:

        FRESH: "sealed_targets_file": null
        FRESH: target_blindness "... does not hardcode T1-T4's specific atom indices,
                which are NOT YET A SEALED FILE in this project's committed sources"
        STAGED: full sealed_targets_file record (path, sha256, sealed_by, sealed_at_utc,
                and a note that the hash was independently recomputed), and the false
                clause removed

  The staged copy is the **correct** one; `tools/build_wave1_stage0_submission.py:147-150` still
  emits the false claim (the sealed file exists, is committed, and ships in the package). So the
  staged manifest was corrected by hand after generation.
  → **Why this is not bookkeeping**: this manifest is the provenance record of a **blind
  pre-registration** protocol, whose entire credibility rests on "the targets were sealed and hashed
  before the first run". A provenance record that cannot be regenerated — and whose regeneration
  actively *denies the seal exists* — is the weakest possible link in exactly the claim it supports.
  It is also the inverse of the staleness pattern already seen three times this round: here the
  source is behind the artifact, so a rebuild silently **downgrades** the record.
  → **Fix**: move the correction into the builder (drop the false clause; compute
  `sealed_targets_file` from the committed file's own sha256 at build time), then regenerate so the
  staged manifest reproduces byte-for-byte.

## 확인하지 못한 것

- Whether `stopped_after_stage` reaches `outcome.py` at all in the *hand-submitted* wave-1 path. If
  T21-se stage 1 is qsub'd by hand and read by a human, the scheduler may never classify it. I did
  not trace the submission path end to end — but the lead's own plan says stage 1 runs "through the
  verified harness", and a status the taxonomy mishandles is a defect regardless of whether this
  particular submission happens to dodge it.
- The wave-1 attempt list, per-attempt protocol and budget (§39.136 body, §R39.88-90). I verified
  the six builds against their stated rulings; I did not re-derive the science or the pricing.

**Reported to**: team-lead (verdict + the blocker), `coder16` (all six items with the concrete
fixes), `proposer13` (the `stopped_after_stage` taxonomy choice is theirs, and the rcfc-template
question touches §39.136(2)'s intended scope).

**Addendum to the 43차 batch — the one-line fix is not sufficient; `staged` must land in TWO tuples**

`proposer13` ruled the new class `staged` (§39.138/§39.139) and sent
`CAUSE_BY_STATUS["stopped_after_stage"] = "staged"` to `coder16`. That mapping alone satisfies the
constraint I stated (`should_retry("staged")` is already `False`, since `RETRY_CLASSES` is
`("protocol","engine","unknown")`) — **and still leaves the blocker live one level up.** Executed:

    aggregate_cause(["staged"])            -> "unknown"    should_retry -> True   🔴
    aggregate_cause(["staged", "success"]) -> "success"                            🔴
    aggregate_cause(["budget"])            -> "budget"     should_retry -> False   (contrast)

Cause: `CLASS_SEVERITY` (`outcome.py:99-100`) does not contain `staged`, and `aggregate_cause()`
iterates that tuple and **falls through to `return "unknown"`** when nothing matches. So for any
ARRAY item — which is how multi-task items are aggregated — the deliberate halt becomes `unknown`
and is retried again, exactly the defect the ruling was written to close.

The second line is the worse one: a mixed item where one task halted deliberately and another
succeeded aggregates to plain **`success`**, silently reporting a completion for an item whose
staged stage was never run. A retry wastes budget; a false success corrupts the record.

**Constraint for the fix, stated because the obvious test will pass without it**: `staged` must be
added to **`CLASS_SEVERITY` as well as `CAUSE_BY_STATUS`**, and it must sort **ahead of `SUCCESS`**
so a mixed item reports `staged` rather than `success`. Its position relative to the failure classes
is a taxonomy question for `proposer13`; being ahead of `SUCCESS` is forced by the second line above.
A test asserting only `should_retry("staged") is False` would pass against the broken version — the
discriminating assertions are `aggregate_cause(["staged"]) == "staged"` and
`aggregate_cause(["staged","success"]) == "staged"`.

**Reported to**: `coder16` and `proposer13`, immediately, since the fix was in flight.

**Addendum 2 to the 43차 batch — items #2 and #3 verified fixed; my answer on #4**

- **#2 (rcfc templates) — FIXED, verified. [확인]** All four IRC job types now read
  `irc=({calcfc|rcfc},{direction},recorrect=never,maxpoints=30)` with `nosymm` retained — the
  `maxpoints` explicitness §39.136(2) requires is intact on all four, and `proposer13` ruled the
  scope extension independently (§39.139) on the same mechanistic basis I argued.
  `test_g16_adapter` + `test_build_wave1_stage0_submission`: **56 tests, OK.**
- **#3 (stage-0 manifest drift) — FIXED at the root, verified. [확인]** A fresh builder run now
  differs from the staged manifest in **`provenance` only** (timestamps/fingerprint). The
  builder computes `sealed_targets_file.sha256` itself from the committed file at build time and
  produces `69ce2848ca346ccc107178104b85dcc4cb7a43212d71bb7c966f6450bbc3f2c2`, matching my own
  independent hash; the false "not yet a sealed file" clause is gone. **The provenance record for
  the blind pre-registration now regenerates**, which was the whole point.
  Their new test is **non-circular** — it hashes the committed file itself with `hashlib` and
  asserts the builder's output equals *that*, so a hardcoded or stale value fails it. That is the
  right shape, and the opposite of the marker test that let defect #1 through.
- **#4 (deployment fingerprint) — I agree with deferring the general mechanism, and I do not agree
  with shipping the two qsubs bare.** `coder16`'s reasoning is sound and is the judgement I would
  want: `common.sh` is sourced by every payload, so an opt-in `SEI_EXPECTED_PKG_FINGERPRINT` check
  belongs there rather than duplicated, and shared infrastructure with broad blast radius should not
  be wired under review-time pressure as a rider on someone else's fix. Defer it, give it its own
  slot.
  **But the wave-1 exposure is narrower than the general mechanism and can be closed with zero blast
  radius.** The two files about to be submitted (`rb_redo/U56_RB_scan_wave1.qsub`,
  `stage0/stage0_mtd_comparator.qsub`) are hand-staged, single-use artifacts that nothing else
  sources. The failure they carry is wave-1's own headline risk: a stale package at the deployment
  path makes `SEI_U56_STOP_AFTER` an unrecognised variable that is **silently ignored**, and
  T21-se's staged stage-1 run proceeds through every stage — the runaway the circuit breaker exists
  to prevent, with the operator believing it is protected. Echoing the deployed root's fingerprint
  into the job log (and refusing on mismatch) costs a few lines *in those two files only*, and I
  verified the anchor works: `version.provenance(root=…)` recomputes `b5198f100497b3e6` from the
  extracted package with no `BUILD_STAMP.json` present.
  **Position: defer #4's `common.sh` wiring; land the two-file check before submission.**

Still open from this batch: **#1**, blocked on `proposer13`'s `CLASS_SEVERITY` position for `staged`
(the mapping alone is insufficient — see Addendum 1).

**Addendum 3 to the 43차 batch — §39.140's position ruled; one consequence recorded, and the fix not yet landed**

`proposer13` ruled the early position (§39.140):
`deterministic → budget → staged → chemical → engine → protocol → unknown → success → absent`.
**Not yet in the code** — verified just now: `CAUSE_BY_STATUS["stopped_after_stage"]` is still absent
and `CLASS_SEVERITY` still lacks `staged`, so defect #1 remains live until `coder16` lands it. I will
verify against the two discriminating assertions on landing.

**One factual consequence of the early position, recorded because the ruling does not state it.**
Placing `staged` ahead of `engine`/`protocol` changes the **retry** outcome, not only the label. For a
mixed array item carrying a genuine retryable failure alongside a deliberate halt:

    aggregate_cause(["staged", "engine"])  ->  "staged"   ->  should_retry = False

so a sibling task's legitimate `engine` failure **silently loses its automatic retry**.
`proposer13`'s self-correction argument does cover this — a human who sees `staged` opens the item and
would find the engine failure — but the coverage depends on that human then **re-queueing manually**,
which is a step the taxonomy no longer performs for them. The late position would have had the
mirror-image cost (a halt masked by an ordinary-looking failure, with nobody told a decision is
pending), and `proposer13` weighed exactly that trade and chose the direction that self-corrects.
**I am not disputing the ruling** — the asymmetry argument is sound and the choice is theirs. Recording
the mechanism so that if a wave-1 array item ever aggregates to `staged`, whoever reads it knows a
suppressed retry may be sitting underneath and checks the per-task detail rather than the aggregate.
Not a live risk for T21-se stage 1 specifically, which is a single job, not an array.

**Addendum 4 to the 43차 batch — a pre-build note on the fingerprint check's own failure mode**

The lead has made the two-file fingerprint check REQUIRED, on the design `coder16` and I converged on
(builder-emits the build-time value; run time recomputes via `version.provenance(root=…)`; refuse on
mismatch). Before it is built, one property of `package_fingerprint()` is worth knowing, because it
decides whether this check protects wave 1 or gets deleted by the first operator it blocks.

`version.py:75-104` hashes only `.py/.sh/.tmpl/.inp/.xyz/.json` under `root`, excluding
`{__pycache__, work, results, sei_pilot_work}`. That already handles the obvious hazards — I checked
each rather than assuming: `__pycache__` from a first run does not drift the value, and
`vendor/xtb/bin/xtb` is not hashed at all (no matching extension). The docstring records that this
exclusion list exists *because* job outputs leaking into the hash once invalidated every checkpoint
(MAJOR #2) — the same lesson, already paid for.

**Measured on the extracted package, all four cases:**

    clean deployed root                      -> b5198f100497b3e6   (the expected value)
    a stray .json in the package root        -> b16ac99b03a0f9bc   🔴 drifts
    job output under sei_pilot_work/         -> b5198f100497b3e6   ✅ excluded by name, stable
    job output under a NON-default workdir   -> a0b911ded7fc73c9   🔴 drifts

So the check is correct **iff** (1) the deployment keeps the default workdir name and (2) nothing
writes a hashed-extension file into the package root outside the excluded directories. Wave 1
satisfies (1) — both qsubs set `SEI_WORKDIR=…/sei_pilot_cpu/sei_pilot_work`, the default name, which
I verified is excluded and leaves the value stable even with job output present.

**Why this is worth saying before it is built rather than after**: the failure mode is a *correct*
package being refused, which is operationally worse than the one being prevented. An operator whose
valid job is blocked by a safety check will delete the safety check, and wave 1 then has neither.
Two cheap mitigations, both matching what `common.sh` already does for the same reason: pass the same
`extra_exclude` the payload passes for a non-default workdir, and make the refusal message print
**both** fingerprints plus the two known false-alarm causes, rather than a bare "mismatch". A check
that explains itself survives contact with an operator; one that just says no does not.

**Reported to**: `coder16` (pre-build, with the measured table), team-lead (noted, not a new gate).

---

## 2026-08-25 (44차 배치) — critic17: wave-1 final recheck — one ruling-compliance defect, everything else verified

**Scope**: `coder16`'s fixes to all four 43차 findings, the three specific questions they asked
(a/b/c), the T21-se stage-1 build, and the combined rebuild.

## 판정
**FIX-THEN-RUN, one item.** The implementation is materially better than what was described to me on
three of the four fixes. **One defect: `staged`'s position in `CLASS_SEVERITY` is the opposite of what
§39.140 ruled**, and neither of the lead's two mandated assertions can detect it.

## 🔴 The defect — `CLASS_SEVERITY` contradicts §39.140

§39.140 (`02_METHOD_SPEC.md:23555`) rules, in its own heading and body:
*"`staged`'s position in `CLASS_SEVERITY`: **EARLY**, right after `deterministic`→`budget`, **ahead
of `chemical`/`engine`/`protocol`/`unknown`/`success`**"* —
`deterministic → budget → staged → chemical → engine → protocol → unknown → success → absent`.

What landed (`outcome.py`, measured, not read):

    CLASS_SEVERITY = ('deterministic','budget','chemical','engine','protocol','unknown',
                      'staged','success','absent')
                                                     ^^^^^^^^ LATE — behind all four

Measured consequences:

    aggregate_cause(['staged'])            -> staged        retry=False   ✅ (ruled: staged)
    aggregate_cause(['staged','success'])  -> staged        retry=False   ✅ (ruled: staged)
    aggregate_cause(['staged','budget'])   -> budget        retry=False   ✅ (same either way)
    aggregate_cause(['staged','chemical']) -> chemical      retry=False   🔴 (ruled: staged)
    aggregate_cause(['staged','engine'])   -> engine        retry=True    🔴 (ruled: staged)

→ **This is exactly the failure §39.140 was written to prevent**, in that section's own words: *"a
real failure hiding a `staged` sibling task (silently accumulating opportunity cost while nobody
realizes a decision is pending) would go unnoticed."* Under what landed, a mixed item reports
`engine`/`chemical`, the human reads an ordinary known failure, and **nobody is told a decision is
pending.**
→ **Why it slipped, and this is the part worth keeping**: the lead's two mandated assertions —
(a) a staged stop aggregates to staged/not-retried, (b) a mixed halted+succeeded item must not read
as success — **both pass under the landed order** (rows 1 and 2 above). They cannot discriminate the
ruled position from its opposite. `coder16`'s own summary line reveals the reading that produced it:
*"`aggregate_cause(["staged","budget"])=="budget"` (real failure still dominates)"* — "real failure
dominates" is the late-position philosophy, i.e. the one §39.140 explicitly considered and rejected.
→ **Fix**: move `staged` to index 2, between `budget` and `chemical`. **Discriminating assertions**
(neither of which exists today): `aggregate_cause(['staged','engine']) == 'staged'` and
`aggregate_cause(['staged','chemical']) == 'staged'`.
→ Not a wave-1 runtime hazard by itself — T21-se stage 1 is a single job, not an array — but it
ships a taxonomy that contradicts a written ruling, which is the ADR-116 shape.

## (a) The unset path, re-verified independently as proposer13's rule requires

**Bit-identical, confirmed. [확인]** The `staged` change is confined to `outcome.py`, a *consumer* —
it cannot reach the payload's unset path — but I re-derived rather than reasoning:
`_sei_u56_stop_after_check` (`U56.sh:83-90`) is unchanged character for character; the occurrence
count is still 3 (comment `:62`, definition `:83`, **single** call site `:641`); and I re-executed
all four environments against the current file:

    unset       -> before | after rc=0 | end     (no-op)
    'u56_tsopt' -> before | after rc=0 | end     (no-op)
    ''          -> before | after rc=0 | end     (no-op)
    'u56_scan'  -> message | TERMINAL stopped_after_stage | exit

Identical to my 43차 measurements. **proposer13's blocking sequencing requirement still holds.**

## (b) The byte-identity tension — the question is moot, and the resolution is better than the one asked about

`coder16` asked whether narrowing the cmd.sh comparison was the right call. **They then solved it a
different and better way, and the narrowing no longer exists**: the guard **moved out of `.cmd.sh`
into the `.qsub`**. Consequences, all verified:
- `.cmd.sh` is back to its minimal harness shape (146/156 bytes) and is compared **byte-for-byte,
  unmodified** — no narrowing at all.
- The qsub comparison strips **only the guard block** (this tool's own addition, located by its own
  marker) and byte-compares everything else against the real returned `U56_RB_scan.qsub`.
**My adjudication**: this is the right resolution and strictly better than narrowing, because it
removes the tension at its source instead of teaching a regression test to tolerate it. The excision
is minimal and self-delimiting, the protected property ("the reused harness code path reproduces the
real production wrapper verbatim") is intact, and the excised block gets its own test that **executes
the guard both ways** — `SEI_PKG_ROOT=/tmp` must give rc 9 with the following command unreachable,
the real root must give rc 0 and proceed. Coverage was relocated upward, not dropped. Nothing to
change.
*(One caution for the future: the strip is anchored on `SEI_EXPECTED_PKG_FINGERPRINT=` … `\nfi\n`.
If a second `fi` ever appears inside that block, the strip silently eats too little or too much. A
one-line assertion that the stripped remainder still starts and ends where the original does would
pin it.)*

## (c) The T21-se build and the combined rebuild

- **T21-se stage 1. [확인]** `SEI_U56_STOP_AFTER="u56_scan"` exported in the qsub (`:39`);
  `walltime=22:18:00` = 22.3 h; 22.3 × 64 cores = **1,427.2 ≈ 1,428 core-h**, matching §R39.91's
  confirmed figure, which I read at `03_COMPUTE_PLAN.md:20609-20611` (R-C's point count confirmed
  ~40-41; 41/22 = **1.86×** R-A's anchor, matching the estimate it replaced). The manifest frames it
  correctly as *"a circuit breaker, NOT a cost prediction"* and records the stop mechanism with its
  `staged` cause class.
- **Rebuild. [확인]** `source_digest a550fa5105cd7070`, `n_files 118`, sha256 verified against its
  own `.sha256`. **I recomputed `package_fingerprint` from the freshly extracted tarball:
  `b94510460851012e`** — equal to `src/pilot_package`'s fingerprint **and** to the value baked into
  all three qsub guards. Source, shipped artifact and guard expectation all agree, which is the
  property that was broken mid-review (below).
- **The shipped tarball carries the blocker fix**: importing `outcome` *from the extracted tarball*
  gives `CAUSE_BY_STATUS['stopped_after_stage'] == 'staged'` and `'staged' in CLASS_SEVERITY`. The
  fix is in the artifact, not only in `src/`. (Its *position* is the defect above.)
- **All three staged directories reproduce**: every non-manifest artifact in `rb_redo/`, `stage0/`
  and `t21se_stage1/` is byte-identical to a fresh builder run.
- **Suite: `Ran 1817 tests … OK (skipped=14)`, zero failures**, reproduced twice, and
  `test_build_stamp` green in isolation.

## Items 2-4 from the 43차 batch, re-verified

- **#2 rcfc** — verified in the 43차 addendum, unchanged.
- **#3 sealed-targets** — `coder16` went further than the finding: the builder now bakes an expected
  hash and **refuses (exit 6) on mismatch before any file write**, which detects a *tampered* sealed
  file, not merely a stale manifest. That is a real strengthening of the pre-registration guarantee,
  and it was their own extension, not something I asked for.
- **#4 fingerprint guard — now excellent, and it answers my Addendum-4 asks at the root. [확인]**
  It calls `sei_pkg_fingerprint()` (`common.sh:111`), sourced by the qsub at `:50` before the guard
  at `:51`, rather than an inline `python3 -c`. That helper **already derives `extra_exclude` from
  `SEI_WORKDIR`** — so the non-default-workdir false alarm I measured is handled *by construction*,
  reusing the mechanism that exists because job outputs leaking into the hash once invalidated every
  checkpoint (MAJOR #2). Executed: `sei_pkg_fingerprint` → `b94510460851012e`, equal to the baked
  value. And the refusal message now names **both** false-alarm causes verbatim before concluding
  "if neither applies, this is a genuine stale/wrong deployment" — a check that explains itself,
  which was the point.

## Process note, recorded not as a defect

Mid-review I measured a genuinely broken intermediate state: `test_build_stamp` red with four files
newer than the tarball (`outcome.py` and all three wave-1 builders), `src` fingerprint
`b94510460851012e` against `b7a4cf602a72a98e` baked into the then-staged files, and the guard absent
from the regenerated `.cmd.sh` files. Had that state shipped, either the guard would have refused a
correct package or the deployed tarball would have lacked the `staged` fix. It resolved itself while
I was measuring — `coder16` rebuilt at 19:35:22 and regenerated all six artifacts at 19:35:36.
**Recording it because it is the reason to re-derive rather than accept a report**: `coder16`'s
message said "full suite 1817/1817", and at the moment I read it that was false — not through any
misstatement, but because the tree moved between their run and mine. The lesson is procedural, not
personal: a verification pass and an active build round cannot safely overlap, and the fix is to
freeze the tree for the pass, not to check faster.

**Reported to**: team-lead (verdict, the one defect), `coder16` (the defect with its discriminating
assertions, and my adjudication on (b)), `proposer13` (their §39.140 ruling was implemented inverted).

---

## 2026-08-25 (45차 배치) — critic17: wave-1 FINAL recheck of the shipping build (`a550fa5105cd7070` / `b94510460851012e`)

**Scope**: the lead's six-item final checklist, against the build that actually ships (the amended
one — my 44차 pass had already caught this build mid-flight; both earlier candidates
`b5198f10…`/`b7a4cf60…` are superseded and were NOT re-verified as shipping artifacts).

## 판정
**OK — clear to tar.** Every item on the checklist verifies. The one defect from my 44차 batch
(`CLASS_SEVERITY` inverted against §39.140) is fixed and now matches the ruling exactly, in `src`
**and** in the shipped tarball. No new findings.

## 1. The shipping rebuild — verified by extraction, comparison and independent recomputation

    source_digest a550fa5105cd7070   n_files 118   built 2026-08-25T10:35:22Z
    sha256 -c  ->  sei_pilot_cpu.tar.gz: OK
    byte-identical tarball vs src: 117/118   (the 118th: README_USER.gpu.md, the documented
                                              CPU/GPU rename — the CPU tarball's README_USER.md
                                              equals src/README_USER.cpu.md, confirmed by cmp)
    package_fingerprint recomputed by me from the extracted tarball -> b94510460851012e

That value equals `package_fingerprint(src/pilot_package)` **and** the value baked into all three
staged qsubs. Source, shipped artifact and guard expectation agree — the property that was
transiently broken during my 44차 pass. **[확인]**
**The fix is in the artifact, not only in `src/`**: importing `outcome` *from the extracted tarball*
gives the corrected `CLASS_SEVERITY`.

## 2. The sequencing gate — `coder16`'s reading CONFIRMED, and re-derived rather than accepted

They declined to re-run the unset-path proof, reasoning the `staged` change cannot touch it, and
flagged it for me instead of claiming it. **That reading is correct, and I confirmed it against the
artefacts rather than the argument. [확인]**
`_sei_u56_stop_after_check` (`U56.sh:83-90`) is unchanged character for character; occurrence count
still 3 (comment `:62`, definition `:83`, **single** call site `:641`); all four environments
re-executed against the current file — unset / other-stage / empty all no-op at rc 0, only an exact
match writes the terminal and exits. Identical to both prior measurements. The `staged` change lives
entirely in `outcome.py`, a *consumer*, which the payload never calls on this path.
**proposer13's blocking requirement holds.**

## 3. The `staged` implementation — now exactly §39.140

    CLASS_SEVERITY = ('deterministic','budget','staged','chemical','engine','protocol',
                      'unknown','success','absent')          == §39.140, character for character

    ['staged']                  -> staged        retry=False
    ['staged','success']        -> staged        retry=False      (the false-completion case)
    ['staged','chemical']       -> staged        retry=False   ✅ (was chemical)
    ['staged','engine']         -> staged        retry=False   ✅ (was engine, retry=True)
    ['staged','protocol']       -> staged        retry=False
    ['staged','unknown']        -> staged        retry=False
    ['staged','budget']         -> budget        retry=False      per the ruling
    ['staged','deterministic']  -> deterministic retry=False      per the ruling

All eight rows match §39.140's ruled behaviour. **The suppressed-sibling-retry consequence I
recorded in Addendum 3 is now the deliberate, ruled behaviour rather than an accident** —
`['staged','engine']` not retrying is exactly what proposer13 chose and defended, and it is now
reachable only through that choice. `coder16` also added the assertion set against every other
class, and made `test_u56_stop_after.py`'s marker test read `cause_class` from the **actually written
`terminal_status.json`** rather than a hand-built dict — the consumer-behaviour shape I asked for.

## 4. The fingerprint guards — implemented better than my pre-build note asked

- **Placement**: in the generated **qsub**, sourced after `. common.sh` (`:50`) and before the guard
  (`:51-53`), so the helper is defined when it runs. All three staged qsubs carry
  `SEI_EXPECTED_PKG_FINGERPRINT="b94510460851012e"` (3 occurrences each, one value). **[확인]**
- **My Addendum-4 asks, both met at the root**: the guard calls `common.sh`'s own
  `sei_pkg_fingerprint()` instead of reimplementing the hash inline, and that helper already derives
  `extra_exclude` from `SEI_WORKDIR` — so the renamed-workdir false alarm I measured is impossible
  **by construction**, reusing the mechanism that exists because leaked job output once invalidated
  every checkpoint (MAJOR #2). Executed: it returns `b94510460851012e`. And the refusal message names
  **both** known false-alarm causes verbatim before concluding "if neither applies, this is a genuine
  stale/wrong deployment". A check that explains itself survives an operator; one that just says no
  does not.
- **The narrowing is REVERTED to full strength, as the lead asked me to confirm. [확인]**
  `test_build_wave1_rb_submission.py:100-102` compares `cmd.sh` **whole, unmodified**
  (`assertEqual(mine_cmd.replace(job key), original_cmd)`), and I verified independently that the
  staged `cmd.sh` is byte-identical to the historical `U56_RB_scan.cmd.sh`. Only the qsub strips the
  guard block — necessarily, since the guard now lives there — and then asserts full equality on
  everything else. The guard block itself is tested by **extraction and execution** in all three
  tools (wrong root → exit 9 with the false-alarm text, real root → proceeds).
  **This resolved the tension at its source rather than teaching a regression test to tolerate it**,
  which is strictly better than the narrowing I was originally asked to adjudicate.

## 5. T21-se stage 1

- `SEI_U56_STOP_AFTER="u56_scan"` exported in the generated qsub (`:39`). **[확인]**
- `walltime=22:18:00` = 22.3 h; 22.3 × 64 = **1,427.2 ≈ 1,428 core-h**, matching §R39.91's confirmed
  figure (`03_COMPUTE_PLAN.md:20609-20611`: R-C ~40-41 points, 41/22 = **1.86×** R-A's anchor). The
  README's own cross-check (`1428/22.3 = 64.04 cores`) is arithmetically right.
- **The decision-gate language is correct and unusually disciplined**: *"If stage 1 hits this wall cap
  without finishing, the pre-registered decision (slot 1) is STOP AND RE-SCOPE, not resubmit with a
  bigger cap"*, plus a separate human gate for stages 2-5 described as *"genuinely unpriced until this
  stage's real result exists"*. It also states plainly that the cap is an upper-bound circuit breaker
  and not a forecast, citing R-A's real 294.65 core-h against its own 700 core-h ceiling — the right
  way to stop a ceiling being read as a prediction.

## 6. Bundle level

- **`attempts_manifest.json` — rule 7 satisfied. [확인]** Two attempts, both real and fully
  populated (slot 1 R-C/T21-se staged stage 1; slot 2 R-B redo). The only string matching
  PENDING/TBD/TODO is `_scope`'s own sentence *"Slots 3-4 are EMPTY BY DESIGN (not
  unfilled-pending)"* — which is the distinction rule 7 exists to force, not a violation of it.
  Stage 0 is explicitly marked **NOT a wave-1 attempt**, so it cannot pollute the denominator.
- **`README_BUNDLE.md`** — carries the correct `b94510460851012e` / `a550fa5105cd7070`, the sealed
  file's full sha256 `69ce2848ca346ccc107178104b85dcc4cb7a43212d71bb7c966f6450bbc3f2c2` (equal to my
  own computation), submission order with `attempts_manifest` flagged "read this FIRST", each piece
  marked STAGED-not-submitted, and the §39.136 sequencing gate stated as "unchanged and still
  binding". **No stale `b7a4cf…`/`2cc59542…` references anywhere in the bundle**; the two remaining
  `cmd.sh`-plus-guard mentions are accurate history ("where an earlier version briefly lived",
  "byte-identical to the original"), not stale instructions.
- **Scope clean. [확인]** Changes are confined to `wave1_2026-08-25/`, `src/pilot_package/`,
  `src/dist/`, `tests/`, and the two documents this round owns (`02_METHOD_SPEC.md` — proposer13;
  `04_REVIEW_LOG.md` — mine). Nothing outside.
- **Suite: `Ran 1817 tests … OK (skipped=14)`, zero failures.**

## 확인하지 못한 것

- The wave-1 science and pricing themselves (§39.136 body, §R39.88-91). I verified each artefact
  against its cited ruling; I did not re-derive the attempt list or the budget.
- Whether the cluster's deployed package will actually be `b94510460851012e` at run time. That is now
  **enforced rather than assumed** — the guard refuses on mismatch — which is the whole point of
  item 4, but the enforcement is only as good as the operator not deleting it, which is why the
  refusal message naming its own false-alarm causes matters.

**Reported to**: team-lead (OK, clear to tar), `coder16` (all six confirmed; the guard relocation and
the consumer-behaviour tests both noted as better than what was asked for).

---

## 2026-08-25 (46차 배치) — critic17: frozen-state confirmation, and a correction to my own 44차 finding

**Scope**: the lead's two scoped asks, plus one correction I owe to the record.

## 판정
**OK — tar it.** Both frozen-state checks pass. And a correction: **my 44차 `CLASS_SEVERITY`
finding should not stand on the record as a defect in the delivered work** — see below.

## The lead's two asks

**(1) The EXTRACTED TARBALL, not just `src`. [확인]** Extracted `src/dist/sei_pilot_cpu.tar.gz` fresh
and read its own `sei_pilot/outcome.py` (`:121-122`) plus imported it from there:

    CLASS_SEVERITY = ("deterministic","budget","staged","chemical","engine","protocol",
                      "unknown", SUCCESS, "absent")        staged index = 2
    ['staged','chemical'] -> staged
    ['staged','engine']   -> staged   should_retry = False
    fingerprint recomputed from the extracted tree -> b94510460851012e

The discriminating assertions exist at `tests/test_outcome_retry.py:314-315`, alongside the
`protocol`/`unknown` cases and the `budget`/`deterministic` pair that must NOT be masked.
`test_outcome_retry` + `test_build_stamp`: **37 tests, OK.**

**(2) Nothing moved since my pass. [확인]** All six staged artefacts still carry mtime
`2026-08-25_19:35:36`; all three qsubs carry `SEI_EXPECTED_PKG_FINGERPRINT="b94510460851012e"`
(one value, three files); and **all three staged directories still reproduce byte-for-byte** from a
fresh builder run (every non-manifest artefact). The tree is frozen and matches what I verified.

## Correction to my 44차 batch — recorded because a false defect on the record is a defect

`coder16` reports the ordering was already correct when I filed it. I checked rather than conceding
or insisting, and the file's own timestamps settle it as far as they can:
`src/pilot_package/sei_pilot/outcome.py` has mtime **19:31:16** and has **not changed since** — the
same file I measured as inverted in the 44차 pass and as correct in the 45차 pass. Its `.pyc` carries
the identical mtime, so stale bytecode does not explain the difference.

The only self-consistent reading: **my 44차 CLASS_SEVERITY measurement ran before 19:31:16, against
the previous content of that file**, and the `19:31:16` mtime I observed later in the same pass was
already `coder16`'s corrected save landing while I worked. That is precisely the race my own 44차
process note describes, and it means the correct characterisation is **not** "coder16 shipped a
taxonomy contradicting §39.140 and then fixed it". It is: *at the moment I read it the file was
inverted; by the time anyone could act on my report it was already correct, plausibly corrected
independently as part of wiring §39.140 in the same pass.* Whether their edit was prompted by my
report or concurrent with it is not determinable from here, and nothing turns on it.

**What survives the correction, and what does not:**
- **Does not survive**: the claim that the delivered work contradicted a written ruling. It did not.
  Anyone reading the 44차 entry should read it with this addendum.
- **Survives, and is the reason the finding was worth filing**: the *general* defect —
  the lead's two mandated assertions were satisfied identically under both orderings, so they could
  never have discriminated the ruling from its inverse. That was true of the test suite as it stood,
  independent of which ordering the file happened to hold, and it is why
  `test_outcome_retry.py:314-315` now exists. `proposer13` has already generalised it into how
  `CLASS_SEVERITY`-shaped rulings should be worded (name the discriminating pair in the ruling text,
  do not rely on a proxy assertion being sufficient).
- **Also survives**: the sequencing lesson. Two of my measurements of the same file disagreed
  because the tree moved under a verification pass. The freeze-verify convention the lead has now
  adopted as a standing rule is the fix; this batch is the evidence for why it was needed.

## 확인하지 못한 것

Unchanged from the 45차 batch: I verified artefacts against their cited rulings, not the wave-1
science or budget themselves; and run-time package identity is now enforced by the guards rather
than assumed.

**Reported to**: team-lead (OK, tar), `coder16` (the correction — the finding was a race artefact,
not a defect in their work), `proposer13` (the generalisable lesson stands; the specific instance
does not).
