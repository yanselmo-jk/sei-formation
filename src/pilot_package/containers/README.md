# containers/ — Apptainer `.sif` 슬롯 (현재 **비어 있음**)

## 현황 (정직하게)

`03_COMPUTE_PLAN.md` §R2-6 D-3은 "xtb/CREST/PySCF/geomeTRIC/ASE를 담은 Apptainer
`.sif` 동봉"을 요구한다. **이 패키지에는 `.sif`가 들어 있지 않다.**

이유: 우리 개발 환경(16 vCPU WSL, ADR-004)에 apptainer/singularity/docker가 설치돼
있지 않아 이미지를 **빌드할 수단이 없다.** 없는 것을 있다고 쓰지 않는다.

⇒ 현재 이 패키지의 소프트웨어 탐색 순서는 실질적으로
**모듈 → 시스템 바이너리 → graceful skip** 이다.

## `.sif`를 쓰려면 (사용자/관리자)

1. 이미지를 이 디렉터리에 넣는다.
2. `manifest.json` 을 만든다. 키는 도구 이름, 값은 파일명이다.

```json
{
  "xtb":  "qcstack.sif",
  "orca": "orca6.sif",
  "cp2k": "cp2k-2024.1.sif"
}
```

3. 그러면 `run.sh --dry-run` 이 자동으로 인식한다
   (`apptainer` 또는 `singularity` 실행 파일이 PATH에 있어야 한다).

## 대안 — 모듈 시스템 (권장, 더 간단)

패키지 루트에 `modules.conf` 를 만들면 모든 잡이 실행 전에 그것을 source 한다.

```bash
module load cp2k/2024.1
module load orca/6.0.0
```

인터넷 없는 계산 노드를 기본 가정으로 하므로, 어떤 경로도 네트워크를 요구하지 않는다.
