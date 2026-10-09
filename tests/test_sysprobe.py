"""환경 프로브 파서 테스트 (A1/A2/A3/A8/IO/Q2/GPU).

이 파서들은 우리가 **볼 수 없는 클러스터**의 출력을 읽는다. 실제 출력 견본을
문자열로 박아 두고 회귀 테스트한다. 견본이 틀리면 파서도 틀리므로,
견본 출처(명령)를 각 테스트에 명시한다.
"""

import unittest

import context  # noqa: F401
from sei_pilot import sysprobe as sp

LSCPU = """Architecture:            x86_64
CPU op-mode(s):          32-bit, 64-bit
CPU(s):                  128
On-line CPU(s) list:     0-127
Thread(s) per core:      2
Core(s) per socket:      32
Socket(s):               2
Model name:              AMD EPYC 7543 32-Core Processor
"""

SINFO_PART = """cpu*|7-00:00:00|420|257000|128
gpu|1-00:00:00|24|515000|64
debug|30:00|4|257000|128
long|infinite|10|257000|128
"""

SCONTROL = """Configuration data as of 2026-01-01
MaxArraySize            = 1001
MaxJobCount             = 20000
SchedulerType           = sched/backfill
MaxSubmitJobsPerUser    = 5000
"""

DF = """Filesystem     Type   1-blocks         Used    Available Capacity Mounted on
10.0.0.1@o2ib:/lustre lustre 1099511627776000 549755813888000 549755813888000  50% /scratch
"""


class TestCpuMemory(unittest.TestCase):
    def test_lscpu(self):
        c = sp.parse_lscpu(LSCPU)
        self.assertEqual(c["cpus"], 128)
        self.assertEqual(c["sockets"], 2)
        self.assertEqual(c["cores_per_socket"], 32)
        self.assertEqual(c["threads_per_core"], 2)
        # 🔴 HT가 켜져 있으면 CPU(s)=128 이지만 물리 코어는 64다.
        # core-h 견적에 논리코어를 쓰면 2배 틀린다.
        self.assertEqual(c["physical_cores"], 64)

    def test_lscpu_empty(self):
        c = sp.parse_lscpu("")
        self.assertIsNone(c["cpus"])
        self.assertIsNone(c["physical_cores"])

    def test_free_bytes(self):
        text = "               total        used        free\nMem:   270000000000  1  2\n"
        self.assertAlmostEqual(sp.parse_free(text, unit="b"), 270.0, places=1)

    def test_free_unit_is_explicit_not_guessed(self):
        text = "Mem: 257000 1 2\n"
        self.assertAlmostEqual(sp.parse_free(text, unit="m"), 269.5, places=1)
        self.assertAlmostEqual(sp.parse_free(text, unit="b"), 0.0, places=1)

    def test_meminfo(self):
        self.assertAlmostEqual(sp.parse_meminfo("MemTotal:       263847936 kB\n"),
                               270.2, places=1)


class TestWalltime(unittest.TestCase):
    def test_formats(self):
        self.assertAlmostEqual(sp.parse_slurm_walltime("7-00:00:00"), 168.0)
        self.assertAlmostEqual(sp.parse_slurm_walltime("24:00:00"), 24.0)
        self.assertAlmostEqual(sp.parse_slurm_walltime("30:00"), 0.5)
        self.assertAlmostEqual(sp.parse_slurm_walltime("1-12:30:00"), 36.5)

    def test_infinite_is_none_not_zero(self):
        """무제한을 0으로 만들면 모든 잡이 wall 가드에 걸린다."""
        self.assertIsNone(sp.parse_slurm_walltime("infinite"))
        self.assertIsNone(sp.parse_slurm_walltime("UNLIMITED"))
        self.assertIsNone(sp.parse_slurm_walltime(""))
        self.assertIsNone(sp.parse_slurm_walltime("garbage"))


class TestSinfo(unittest.TestCase):
    def test_partitions(self):
        parts = sp.parse_sinfo_partitions(SINFO_PART)
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0]["name"], "cpu")
        self.assertTrue(parts[0]["is_default"])       # '*' 접미
        self.assertAlmostEqual(parts[0]["walltime_max_h"], 168.0)
        self.assertEqual(parts[0]["nodes"], 420)
        self.assertEqual(parts[0]["cores_per_node"], 128)
        self.assertAlmostEqual(parts[0]["ram_gb_per_node"], 269.5, places=0)
        self.assertIsNone(parts[3]["walltime_max_h"])  # infinite

    def test_gres_gpu_detection(self):
        text = "cpu*|(null)\ngpu|gpu:a100:4\n"
        g = sp.parse_sinfo_gres(text)
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["partition"], "gpu")

    def test_scontrol_config(self):
        cfg = sp.parse_scontrol_config(SCONTROL)
        self.assertEqual(cfg["MaxArraySize"], 1001)
        self.assertEqual(cfg["MaxJobCount"], 20000)
        self.assertEqual(cfg["SchedulerType"], "sched/backfill")

    def test_sacctmgr(self):
        rows = sp.parse_sacctmgr_assoc("proj1|cpu|normal|100|cpu=1000\n")
        self.assertEqual(rows[0]["qos"], "normal")
        self.assertEqual(rows[0]["max_jobs"], 100)


class TestFilesystemAndGpu(unittest.TestCase):
    def test_df(self):
        rows = sp.parse_df(DF)
        self.assertEqual(rows[0]["fs_type"], "lustre")
        self.assertAlmostEqual(rows[0]["avail_tb"], 549.76, places=1)
        self.assertEqual(rows[0]["mount"], "/scratch")

    def test_df_garbage_is_skipped(self):
        self.assertEqual(sp.parse_df("df: /scratch: No such file\n"), [])

    def test_quota_unparsable_keeps_raw(self):
        q = sp.parse_quota("Disk quotas for user x: none")
        self.assertFalse(q["parsed"])
        self.assertIn("Disk quotas", q["raw"])

    def test_nvidia_smi(self):
        g = sp.parse_nvidia_smi("NVIDIA H100 80GB HBM3, 81559 MiB\n"
                                "NVIDIA H100 80GB HBM3, 81559 MiB\n")
        self.assertTrue(g["present"])
        self.assertEqual(g["count"], 2)
        self.assertIn("H100", g["model"])

    def test_nvidia_smi_absent(self):
        self.assertFalse(sp.parse_nvidia_smi("")["present"])


class TestSoftwareAndNetwork(unittest.TestCase):
    def test_module_avail(self):
        text = ("--- /opt/modules ---\n"
                "cp2k/2024.1  orca/6.0.0(default)  gcc/12.2  something-else\n")
        mods = sp.parse_module_avail(text)
        self.assertIn("cp2k/2024.1", mods)
        self.assertTrue(any(m.startswith("orca/6.0.0") for m in mods))
        self.assertNotIn("something-else", mods)

    def test_network_probe_parse(self):
        n = sp.parse_network_probe("dns=ok\nhttps=200\ngit=ok\n")
        self.assertTrue(n["https"] and n["git"] and n["dns"])
        n2 = sp.parse_network_probe("dns=fail\nhttps=fail\ngit=absent\n")
        self.assertFalse(n2["https"] or n2["git"])

    def test_io_rates(self):
        r = sp.io_rates_from_raw({"seq_write_bytes": 1e9, "seq_write_s": 2.0,
                                  "seq_read_bytes": 1e9, "seq_read_s": 0.5,
                                  "smallfile_count": 1000, "smallfile_s": 0.1})
        self.assertAlmostEqual(r["seq_write_mbs"], 500.0)
        self.assertAlmostEqual(r["seq_read_mbs"], 2000.0)
        self.assertAlmostEqual(r["smallfile_creates_per_s"], 10000.0)

    def test_io_rates_missing(self):
        r = sp.io_rates_from_raw(None)
        self.assertIsNone(r["seq_write_mbs"])


if __name__ == "__main__":
    unittest.main()
