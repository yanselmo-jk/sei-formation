#!/usr/bin/env python3
"""probe_node.sh가 잰 원시 타이밍 → node_probe.json.

셸 안에 python 헤레독을 중첩하면 파싱이 깨진다(실제로 깨졌다). 파일로 분리한다.
인자: <job_dir> <t0> <t1> <t2> <t3> <t4> <bytes>
시간은 epoch 초(소수 가능), bytes는 순차 read/write에 쓴 바이트 수.
"""

import json
import os
import sys

ENV_KEYS = ("SCRATCH", "WORK", "TMPDIR", "HOME", "SLURM_CPUS_ON_NODE",
            "SLURM_JOB_NUM_NODES", "SLURM_JOB_PARTITION", "PBS_NODEFILE",
            "OMP_NUM_THREADS")


def main():
    if len(sys.argv) < 8:
        sys.stderr.write("usage: node_probe_summary.py JOBDIR t0 t1 t2 t3 t4 BYTES\n")
        return 2
    d = sys.argv[1]
    try:
        t0, t1, t2, t3, t4 = [float(x) for x in sys.argv[2:7]]
        nbytes = float(sys.argv[7])
        io = {"seq_write_bytes": nbytes, "seq_write_s": t1 - t0,
              "seq_read_bytes": nbytes, "seq_read_s": t2 - t1,
              "smallfile_count": 1000, "smallfile_s": t4 - t3}
    except ValueError:
        io = None
    # 🔴 Gaussian 탐지 결과를 회신에 싣는다. 예전에는 **모듈 로드 전** PATH 만 봐서
    #    계산 노드에서 `g16=ABSENT` 로 보였고, 로그인에는 바이너리가 있어 planner 가
    #    "있다"고 판단했다 ⇒ P1/P1b/P5 가 전부 rc=3 으로 죽었다.
    gaussian = {}
    try:
        with open(os.path.join(d, "gaussian_probe.txt")) as fh:
            for line in fh:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    if k == "module_tried_failed":
                        gaussian.setdefault("modules_tried_failed", []).append(v)
                    else:
                        gaussian[k] = v
    except OSError:
        gaussian = {"_note": "gaussian_probe.txt 없음 (구버전 probe_node)"}
    gaussian["_meaning"] = (
        "g16_before_module 이 ABSENT 인데 module_ok 가 있으면, **모듈을 로드해야만** "
        "계산 노드에서 g16 이 보인다는 뜻이다. 그 경우 잡 스크립트가 반드시 "
        "`module load` 를 해야 한다.")
    out = {"io": io,
           "gaussian": gaussian,
           "env_paths": dict((k, os.environ.get(k)) for k in ENV_KEYS)}
    with open(os.path.join(d, "node_probe.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
