# SEI Formation Simulation — Project Brief

> 이 파일은 **불변 사양(spec)** 이다. organizer만 수정한다.
> 모든 팀원(agent)은 작업 시작 전 이 파일을 반드시 읽는다.

> 🟢 **용어를 모르면 `docs/06_GLOSSARY.md` 를 먼저 보라.** `B0`/`B1`, `C-N`, `S1~S4`, `κ`,
> `P1`/`P6`, `U-55`, 라벨 규약, 그리고 **표기 충돌 4건**이 한 장에 있다.
> ⚠ 이 브리프에는 `B0` 라는 단어가 한 번도 나오지 않는데 다른 문서에는 84번 나온다 — 그 격차를
> 메우는 파일이다.

## 1. 목표

Li-ion battery의 **SEI(Solid Electrolyte Interphase) 형성 과정**을 다단계 계산으로
시뮬레이션한다. 최종 산출물은 "electrolyte 조성 → SEI 조성/두께/성장속도"를 예측하는
재현 가능한 계산 파이프라인이다.

## 2. 4단계 전략 (사용자 정의, 상위 골격은 고정)

| Stage | 내용 | 핵심 출력 |
|---|---|---|
| S1 | Electrolyte 내 species가 **전자를 받는 과정**의 activation barrier 계산 | ΔG‡_reduction, ΔG_rxn, λ (per species / per solvation env) |
| S2 | 환원된 **radical species가 다른 species와 만드는 생성물 탐색** (2차·3차 반응 포함) | reaction network (nodes=species, edges=reactions) |
| S3 | 각 반응의 **reaction pathway 탐색 및 activation barrier 계산** | TS 구조, ΔG‡, ΔG, 검증된 IRC |
| S4 | 계산된 barrier로 **kMC 또는 microkinetics** 구현 | 시간에 따른 SEI 조성/두께, 민감도 분석 |

각 stage의 *구체적 방법론은 미정*이며, 이를 정하는 것이 팀의 첫 임무다.

## 3. 계산 자원 (하드 제약)

- **HPC**: 100+ nodes (CPU). 배치 큐 기반. → plane-wave/GTO DFT, AIMD, many-task 병렬
- **GPU 머신**: 3+ 대 × H100 80GB 2장 = **최소 6× H100**. → MLIP 학습/추론, GPU-DFT, MD
- 자원은 크지만 **무한하지 않다.** 모든 방법론 제안은 반드시 node-hour / GPU-hour 예산과
  wall-clock 완료 시점을 동반해야 한다. 예산 없는 제안은 미완성으로 간주한다.

## 4. 팀 구성 및 역할 (Claude Code **agent teams**)

| 지위 | teammate 이름 | agent type | 모델 | 역할 | 소유 문서 |
|---|---|---|---|---|---|
| **lead** | — | `sei-organizer` | opus | 총괄, 중재, 게이트, task list | `01_DECISION_LOG.md`, `05_STATE.md` |
| teammate | `proposer` | `sei-proposer` | opus | 과학적 방법론 (정확도 대변) | `02_METHOD_SPEC.md` |
| teammate | `engineer` | `sei-engineer` | opus | 계산 예산·일정 (처리량 대변) | `03_COMPUTE_PLAN.md` |
| teammate | `coder` | `sei-coder` | opus | 확정 스펙의 구현 | `src/`, `tests/` |
| teammate | `critic` | `sei-critic` | sonnet | 리뷰 (수정 권한 없음) | `04_REVIEW_LOG.md` |

**의도된 긴장 관계**: proposer는 정확도를, engineer는 처리량을 대변한다. 둘의 충돌은
버그가 아니라 설계다. 둘은 **서로 직접 메시지를 주고받아** 예산 상한 ↔ 방법 재단을
왕복한 뒤, 남은 쟁점만 lead가 중재해 `01_DECISION_LOG.md`에 기록한다.

### 실행 방법

```bash
cd /home/yanselmo/0_claude_projects
claude --agent sei-organizer          # 세션 전체가 organizer(=lead)가 된다
```

`.claude/settings.json`의 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`이 이 프로젝트에서만
agent teams를 켠다. lead에게 자연어로 지시하면 teammate를 spawn한다:

```
proposer와 engineer 두 명을 띄워서 S1 방법론 후보를 확정해줘.
proposer는 sei-proposer, engineer는 sei-engineer agent type을 써.
```

- teammate 목록은 프롬프트 아래 agent panel에 뜬다. ↑↓로 선택, Enter로 해당 세션 열기,
  거기서 직접 대화 가능. `x`로 중지, Ctrl+T로 task list 토글.
- teammate 권한 요청은 **lead 세션에 뜬다.** 거기서 승인한다.
- **한 번에 다 띄우지 마라.** teammate마다 별도 context window를 소모한다.
  Phase 0~1은 proposer+engineer 둘, 구현기에 coder+critic.

### agent teams의 제약 (설계 시 반드시 감안)

- teammate의 **idle 알림에는 출력이 실려 오지 않는다.** 결과는 소유 문서 또는 명시적
  메시지로만 전달된다. 그래서 모든 역할에 "문서 갱신 + lead에게 메시지" 를 강제해 두었다.
- **중첩 팀 불가**: teammate는 teammate를 spawn할 수 없다. lead만 팀을 관리한다.
- **lead 고정**: 세션당 팀 하나, lead 교체 불가.
- **`/resume`으로 teammate는 복원되지 않는다.** 재개 시 새로 spawn해야 한다.
  → 그래서 모든 상태를 `docs/`에 파일로 남기는 것이 선택이 아니라 필수다.
- teammate 권한 모드는 spawn 시 lead와 동일하게 시작한다. 개별 지정 불가.
- 토큰 소모가 단일 세션보다 크게 늘어난다. 놀고 있는 teammate는 shutdown시킨다.

## 5. 문서 규약

```
sei_formation/
├── docs/
│   ├── 00_PROJECT_BRIEF.md   # 이 파일 (organizer only)
│   ├── 01_DECISION_LOG.md    # ADR 형식 결정 기록 (organizer only)
│   ├── 02_METHOD_SPEC.md     # proposer 산출물
│   ├── 03_COMPUTE_PLAN.md    # engineer 산출물
│   ├── 04_REVIEW_LOG.md      # critic 산출물
│   └── 05_STATE.md           # 현재 상태 / 다음 액션 (organizer only)
├── src/                      # coder 산출물
└── tests/                    # coder 산출물
```

- 서브에이전트는 서로의 대화를 보지 못한다. **파일이 유일한 공유 기억이다.**
- 모든 에이전트는 작업 종료 시 자기 소유 문서를 갱신하고, 요약을 반환한다.
- 확정되지 않은 것은 `[UNRESOLVED]` 태그로 명시한다. 조용히 가정하지 않는다.

## 6. 과학적 무결성 규칙 (전원 적용)

1. **수치에는 출처를 붙인다.** 문헌값이면 인용, 계산값이면 방법+기저+용매모델, 추정값이면 `[ESTIMATE]`.
2. 사용하지 않은 방법을 사용했다고 쓰지 않는다. 돌리지 않은 계산 결과를 쓰지 않는다.
3. gas-phase 값을 solution-phase 결론에 그대로 쓰지 않는다.
4. 실패·미수렴·기각된 경로도 기록한다. 음성 결과는 삭제 대상이 아니다.
