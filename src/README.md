# src/ — 파일럿 인도 패키지 (coder 산출물)

> 대상 스펙: `docs/03_COMPUTE_PLAN.md` **§R2-6** (구성요소 A~D) + **§11.5**(P1b/P2ext 확장),
> 제약: **ADR-004**(HPC 직접 접근 불가 — 사용자 수동 제출), **§R2-8 Case B**(air-gapped 기본).
>
> 이 디렉터리에는 **파일럿 인도 패키지만** 있다. S1/S2/S3 본 파이프라인은 착수하지 않았다.

```
src/
├── digest.sh                # 🟢 L3: 세션을 열 때 이것부터 — "여기서부터 시작" 다이제스트
├── session_digest/          #    문서 파서(순수) + 분류 + 변경분 + 렌더
├── batch.sh                 # 🟢 L4: 배치를 제출하기 전에 이것으로 검증
├── batch_planner/           #    왕복 구조 검증 V1~V8 + 달력 산정 + 문서 드리프트
├── config/                  #    rt_plan.json (왕복 구조·RT-3 DAG·자료구조 규칙)
├── make_package.sh          # 테스트+스모크 후 tarball **2개** 생성 (cpu/gpu)
└── pilot_package/           # ← 프로파일별로 잘려 사용자에게 가는 트리
    ├── run.sh               # 사용자 진입점 (dry-run / submit / collect / status / merge)
    ├── PROFILE              # 빌드 시 박히는 cpu|gpu (run.sh 가 읽는다)
    ├── README_USER.cpu.md   # 사용자용 안내 — CPU 클러스터
    ├── README_USER.gpu.md   # 사용자용 안내 — GPU 머신
    ├── modules.conf         # (선택) 사이트 module load 훅. 기본 미동봉
    ├── containers/          # Apptainer .sif 슬롯 — 🔴 현재 비어 있음(빌드 수단 없음)
    ├── config/              # graph_layers.json — Li 배위 임계·τ (코드가 아니라 데이터)
    ├── inputs/              # 계산 입력 구조 (EC+Li 라디칼 2종, 148원자 액체 box, CP2K 템플릿)
    │   └── p5_species/      #   P5 대표 소분자 14종 (3~21원자 × 전하 −1/0/+1 × 개각)
    ├── payload/             # 노드에서 도는 셸: 프로브 / P1 / P1b / P2 / P2ext / p2_scaling / P3 / P4
    ├── tools/               # 결정론적 box 생성기, 노드 프로브 집계기
    └── sei_pilot/           # 파이썬 (표준 라이브러리만)
        ├── cli.py           # preflight / submit / collect / status
        ├── plan.py          # 항목 정의·자원 산정·가드 적용  ← 스펙과 코드가 만나는 곳
        ├── budget.py        # 🔴 자원 하드가드 (숫자는 여기 한 곳에만)
        ├── scheduler.py     # SLURM / PBS / 순수셸 어댑터 (모킹 경계)
        ├── shellrun.py      # subprocess를 부르는 유일한 모듈 + FakeShell
        ├── sysprobe.py      # A1/A2/A3/A8/IO/Q2/GPU 파서(순수함수) + 수집기
        ├── probes.py        # many-task 처리량 / 큐 대기 분석
        ├── collect.py       # 아티팩트 → 판정 조립
        ├── report.py        # sei_probe_report.json (schema 1.1)
        ├── state.py         # 마커 기반 멱등 재개
        ├── enumerate_gen1.py# P3용 b2f2 그래프 편집 열거기(참조 구현)
        ├── config.py        # 설정 로더 (화학 파라미터는 데이터, ADR-001)
        └── criteria/        # 🔴 파일럿 자동 판정 — 전부 순수 함수
            ├── endpoints.py #   IRC 끝점 2층 그래프 R1~R3 + τ 병합 (02_METHOD_SPEC §12.3)
            └── p1/p1b/p2/p3/p4/xyzgraph/cost
```

## 🔴 패키지는 **둘**이다 (CPU 머신 / GPU 머신이 물리적으로 분리)

```
dist/sei_pilot_cpu.tar.gz   → HPC 클러스터(SLURM/PBS)   가드 5,000 core-h / 24 h
dist/sei_pilot_gpu.tar.gz   → GPU 머신(기본 셸 실행)     가드 4 GPU-h / 60 core-h / 24 h
```

* **코드는 하나다.** `plan.default_items(profile)` 가 항목 집합만 분기한다
  (복제하면 다음 수정에서 두 벌이 어긋난다).
* 회신 파일이 다르다: `sei_probe_report.cpu.json` / `.gpu.json`
* 두 개를 합치는 도구를 제공한다: `python3 -m sei_pilot.cli merge a.json b.json -o merged.json`
  — **손실 없이** 합치고, 프로파일이 섞이면 덮어쓰지 않고 경고한다.
* 🔴 **P4의 CPU 기준값은 "같은 GPU 머신의 CPU"** 다. 머신이 분리돼 HPC CPU와 직접 비교가
  불가능하기 때문이며, 그 사실이 회신 JSON에 명시된다(HPC 대비 환산은 CPU 패키지의
  노드 사양으로 사후 보정).

## 설계에서 반드시 알아야 할 5가지

1. **자원 상한을 스케줄러가 강제한다.** 각 항목은 core-h 예산을 선언하고,
   `wall = 예산 / 코어수` 로 wall을 역산해 제출한다. 파이썬이 폭주해도 스케줄러가 죽인다.
   가드 숫자는 `budget.py` 한 곳에만 있다(**4,000 core-h / 24 h**, §11.5 + lead 승인).
2. **판정은 전부 순수 함수**(`criteria/`)다. 클러스터 호출(`shellrun`)과 분리돼 있어
   스케줄러 없는 우리 박스에서 192개 테스트로 검증된다.
3. **실패는 데이터다.** 미수렴·도구 부재·큐 거부는 예외가 아니라 `failures[]`/`skip_reason`
   으로 회신된다. 한 항목의 실패가 다른 항목을 죽이지 않는다.
4. **멱등 재개 — 3중**: (a) `run.sh` 재실행은 완료 항목을 건너뛴다, (b) 체인 링크는
   **논리 키**(`SEI_LOGICAL_KEY`) 완료 마커를 보고 즉시 종료한다, (c) `sei_stage` 가
   단계별 체크포인트를 남겨 잘린 지점부터 이어받는다. 이중 실행이 일어나면
   `execution_audit` 로 회신 JSON에 드러난다.
5. **모르는 것은 모른다고 회신한다.** 측정 못 한 항목은 `unresolved_for_lead[]` 에
   사유와 함께 실린다. 침묵으로 '측정됨'처럼 보이게 하지 않는다.

## L3 — 세션 상태 자동요약 (`src/digest.sh`)

산발적으로 접속하는 사람의 **재오리엔테이션 세금**(§R3.1 [ESTIMATE] 15~20%)을 겨냥한다.
문서를 요약하지 않고 **행동 범주로 분리**한다:

```
[0] 지금 프로젝트를 좌우하는 것   [4] 지난 세션 이후 바뀐 것   ← 여기가 핵심
[3] 내가 답해야 하는 것 (사람)    [1] 지금 당장 할 수 있는 것   [2] 막혀 있는 것
```

* 분류 우선순위: 해소됨 → 사람만 답 가능 → teammate 대기 → 열린 질문. **세 범주는 배타적**이다.
* **소유자 인식**: `— 사용자` / `proposer:` / 소제목 `외부 대기` 를 읽어 액션의 주인을 판정한다.
  🔴 **사용자 소유 액션은 [1]이 아니라 [3]에 올린다** — 임계 경로가 목록에 묻히면 안 된다.
* 🔴 **신선도 표시**: git이 없으므로 (a) 파일 mtime(즉시 얻는 **하한**) + (b) 스냅샷 관측 이력을
  결합해 `⏳9일 경과` 를 붙이고, 「다음 액션」 절이 오래 안 바뀌면 **경고 배너**를 띄운다.
  관측 이력이 없으면 `≥N일` 로 쓴다 — 아는 것보다 더 아는 척하지 않는다.
* 변경분은 `.session_state/` 스냅샷과 비교해 낸다. **`docs/` 는 읽기만 한다**(다른 teammate 소유).
* `--check` 는 파싱 건전성을 종료코드로 알린다 — 문서 규약이 바뀌어 **조용히 빈 다이제스트**가
  나오는 것이 이 도구의 가장 위험한 실패 모드이므로, 그것을 실패로 만든다.

## L4 — 배치 통합 계획기/검증기 (`src/batch.sh`)

**왕복을 늘리는 배치를 제출 전에 거부한다.** 왕복 1회 = 달력 3.5일이고,
🔴 **RT-3(S2 자율 DAG)을 쪼개면 1.5~2.0주를 잃는다**(§R8.5).

```bash
./src/batch.sh show                 # 확정 왕복 구조(7회) + RT-3 내부 DAG + 자료구조 금지 규칙
./src/batch.sh validate items.json  # 이 배치가 구조를 깨는지 (종료코드 1 = 불성립)
./src/batch.sh drift                # config ↔ 문서(§R8.5) 어긋남 점검
```

| 규칙 | 내용 |
|---|---|
| **V1** | 모든 작업이 정확히 하나의 RT에 배정됐는가 (미배정은 조용히 사라진다) |
| **V2** 🔴 | `must_not_split` RT(RT-2/3/7) 안에 사람 회신 지점이 2개 이상이면 **거부**. 대가를 주 단위로 함께 출력 |
| **V3** | 선행 작업이 뒤 왕복에 있지 않은가 |
| **V4** | 잡 wall ≤ 24 h (ADR-004). 초과 시 체인 분할 필요 |
| **V5** | RT당 사용자 개입 1회(`sbatch`) 초과 시 달력 비용 계산 |
| **V6** | 왕복 총 횟수가 확정 구조(7)를 넘지 않는가 |
| **V7** 🔴 | ADR-027 자료구조 규칙 — **원장 가지치기 / 가지친 network에서 완결성 계산 / 두 시계 수동 동기화** 금지 |
| **V8** | RT-3 작업의 stage가 DAG에 정의된 것인가 (오타 = 의존성 누락) |

**계획기이지 실행기가 아니다.** 본 파이프라인은 구현하지 않는다 — U-22가 열려 있고
단가가 전부 `[ESTIMATE]`이므로(ADR-004) 지금 실행기를 짜면 파라미터를 추정으로 박게 된다.

## 실행

```bash
./src/digest.sh                            # 세션 시작 시 (L3)
./src/batch.sh validate <items.json>       # 배치 제출 전 (L4)
python3 -m unittest discover -s tests      # 227 tests
src/pilot_package/run.sh --dry-run         # 이 박스에서도 돈다 (전부 graceful skip)
src/make_package.sh                        # dist/sei_pilot_{cpu,gpu}.tar.gz
```

## 🔴 검증되지 않은 부분 (critic·lead 필독)

우리 환경에는 스케줄러·QC 코드·GPU가 없다(ADR-004). 따라서 아래는 **사용자의
클러스터에서 처음 실행될 때가 최초 검증**이다. 코드에 `[UNVERIFIED]` 주석으로 표시했다.

| 대상 | 근거 없는 부분 | 완화 장치 |
|---|---|---|
| ORCA 입력 문법 (P1/P1b) | 키워드·출력 파일명(`*_NEB-TS_converged.xyz`, `_IRC_F_trj.xyz`) | 본계산 전 **수초짜리 smoke 테스트**. 실패하면 1,000 core-h를 쓰지 않고 즉시 종료 |
| CP2K 입력 (P2) | 기저/유사퍼텐셜 파일명, Mulliken 스핀 열 위치 | 1-step smoke 테스트 + `s_of_t.dat` 이중 경로 |
| xtb `--path` 옵션 (P3) | 6.x 문법 가정 | 실패는 수렴률 0으로 기록(측정값이 됨) |
| gpu4pyscf API (P4) | import 경로·gradient 반환형 | import 실패도 '이 클러스터에선 GPU-DFT 불가'라는 **측정 결과**로 회신 |
| sbatch/qsub 수용 여부 | 사이트 정책(QoS, 파티션명, 배열 상한) | `--dry-run` + 제출 실패의 부분 격리 |
| P1 초기 구조 | 이상화 기하이며 **최적화된 값이 아니다**. 진짜 TS라는 보장 없음 | 그래프·기하 무결성은 테스트로 검증. TS 여부는 파일럿 판정 기준 자체가 판단 |

## IRC 끝점 판정 (02_METHOD_SPEC §12.3, proposer 회신 반영)

2층 그래프 — Layer C(공유결합, Li 제외) / Layer I(Li 배위, 거리 기준) — 위에서
`R1 → R2a → R2b → R3` 순으로 판정한다. R2b(실체 수가 같은 배위 재배열)는 그래프가
아니라 **속도론**(τ=0.1 eV)으로 가르고, barrier를 모르면 **`undetermined`** 로 남긴다
(병합도 분리도 하지 않는다 — 조용한 기각은 ADR-003 축(b) 반응을 죽인다).

🔴 `config/graph_layers.json` 의 Li–X 접촉 임계는 **`[PLACEHOLDER-ESTIMATE]`** 다.
P1 구조·P2 궤적의 RDF 첫 최소로 실측해 교체해야 하며, 그때까지 **±0.2 Å 민감도**가
매 판정마다 함께 회신된다.
