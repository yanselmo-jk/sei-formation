# SEI 파일럿 패키지 — **GPU 머신용** (읽는 데 1분)

> 이 패키지는 **GPU가 달린 머신**에서 실행합니다.
> CPU 클러스터용 패키지(`sei_pilot_cpu.tar.gz`)는 **따로 있습니다.** 둘 다 실행해 주세요.

## 하실 일 (3가지)

```bash
tar xf sei_pilot_gpu.tar.gz
cd sei_pilot_gpu

./run.sh --dry-run     # 1분. GPU/CUDA/python 스택만 점검합니다.
./run.sh               # 실제 실행 (배치 스케줄러 없이 백그라운드로 돕니다)
```

끝나면 아래 파일 **하나만** 회신해 주세요.

```
sei_pilot_work/results/sei_probe_report.gpu.json
```

## 안전장치

| 항목 | 값 |
|---|---|
| GPU 사용 상한 | **4 GPU-hour** |
| CPU 사용 상한 | 60 core-hour (아래 참조) |
| 실행 1건 wall-time 상한 | **24 시간** |

상한을 넘는 작업은 **시작 자체가 되지 않습니다.**

## 필요한 것

`python3`(3.6+) + NVIDIA 드라이버. 계산에는 `gpu4pyscf` 와 `pyscf` 가 필요하지만,
**없으면 "이 머신에서는 GPU-DFT를 쓸 수 없다"는 측정 결과로 기록하고 정상 종료**합니다.
(그것도 우리에게는 답입니다. 억지로 설치하지 마세요.)

### gpu4pyscf 설치가 막히면

🔴 **`pip install gpu4pyscf-cuda12x` 만으로는 부족할 수 있습니다.**
import 시 `libnvJitLink.so` / `libcusolver.so` 를 못 찾는다는 오류가 나면
CUDA 런타임 라이브러리를 함께 설치하세요:

```bash
pip install nvidia-nvjitlink-cu12 nvidia-cusolver-cu12 nvidia-cublas-cu12 \
            nvidia-cusparse-cu12 nvidia-cufft-cu12 nvidia-curand-cu12 \
            nvidia-cuda-runtime-cu12 nvidia-cuda-nvrtc-cu12
```

**왜 한 번에 다 적어 두는가**: 이 오류는 **없는 라이브러리를 하나씩만** 알려주기 때문에
고치고 다시 돌리기를 반복하다 포기하기 쉽습니다. 위 목록을 한 번에 설치하면 대개 끝납니다.
(`LD_LIBRARY_PATH` 설정은 **필요 없습니다** — 경로 문제가 아니라 패키지 부재입니다.)

⚠ **그래도 안 되면 그대로 두셔도 됩니다.** "이 머신에서는 GPU-DFT를 쓸 수 없다"가
회신에 기록되고, 그것도 저희에게는 유효한 답입니다. 억지로 설치하지 마세요.
다만 위 설치로 풀리는 경우와 구분하기 위해, 실패 원인이 **"고칠 수 있는 환경 문제"인지**
스크립트가 자동으로 분류해 기록합니다.

**계산 레벨**: `wB97X-V / def2-TZVP` — 범함수는 생산 레벨(ADR-029)과 같고,
기저는 GPU 메모리 상한 측정이 왜곡되지 않도록 diffuse 함수를 뺀 것입니다
(생산은 `def2-TZVPPD`). 이 차이는 회신 JSON에 그대로 기록됩니다.
**계산 시작 전에 범함수·기저 이름을 먼저 검증**하며, 이름이 틀리면 SCF를 시작하지 않고
유효한 후보 목록과 함께 즉시 종료합니다.

## 무엇을 재는가

| 항목 | 내용 |
|---|---|
| 환경 프로브 | GPU 모델·메모리·개수, 드라이버/CUDA, **이 머신의 CPU 코어 수**, python 스택 |
| **P4** | GPU4PySCF 단일점+gradient **vs 같은 머신의 CPU** — 정확도(1e-5 Hartree)와 속도비, 메모리 상한 원자 수 |

🔴 **GPU 모델명이 회신에 반드시 기록됩니다.** 어느 GPU에서 잰 값인지 모르면 그 숫자는
쓸모가 없기 때문입니다. 대상 기종(H100)이 아닌 GPU에서 실행하면 결과에 **`[SMOKE — not H100]`**
표시가 붙고, **메모리 상한 원자 수는 비워집니다** — 속도와 달리 메모리 용량은 기종 간 환산이
불가능하기 때문입니다(12.9 GB ↔ 80 GB).

🔴 **속도비의 기준(분모)은 "이 GPU 머신의 CPU"입니다** — HPC 노드의 CPU가 아닙니다.
두 머신이 분리돼 있어 직접 비교가 불가능하기 때문이며, HPC 노드 대비 환산은 저희가
CPU 패키지의 노드 사양으로 사후 보정합니다. (그 사실이 회신 JSON에 명시됩니다.)

## 배치 스케줄러가 있는 머신이라면

기본은 **셸(백그라운드) 실행**입니다. 이 머신에 SLURM/PBS가 있고 그쪽으로 제출하길 원하시면
`./run.sh --use-scheduler` 로 실행해 주세요.

## 중간에 끊겨도 괜찮습니다

`./run.sh` 를 다시 실행하면 끝난 것은 건너뜁니다. 수집만 다시 하려면 `./run.sh --collect`.
