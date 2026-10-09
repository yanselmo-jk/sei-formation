#!/bin/bash
# QC 코드 어댑터 — P1/P1b/P5가 공유한다. **Gaussian16 우선.**
#
# 🔴 사용자 클러스터에는 orca/qchem/psi4 가 **하나도 없고 gaussian16 이 있다**(lead 확인).
#    ORCA 문법에서 포팅한 것이 아니라 **재작성**이다 — 입력 형식(.gjf)과 출력 형식이
#    완전히 다르다.
#
# 🔴 레벨(범함수/기저)은 **config/qc_levels.json 단일 출처**에서 온다. 여기 하드코딩 금지.
#    (`wb97x-d3` 를 셸에 박아 두었다가 SCF 시작 후에야 터진 일이 있었다.)
#
# 🔴 route 사전검증: 본계산 전에 **수초짜리 H2 입력**으로 route line 수용 여부를 확인한다.
#    범함수·기저 이름이 틀리면 여기서 잡고, 후보를 함께 출력한 뒤 중단한다.

sei_qc_detect() {
  [ -n "${SEI_QC:-}" ] && return 0
  # 🔴 실패를 **구분**한다. 예전에는 전부 rc=3("QC 코드 없음")으로 뭉개져서,
  #    실클러스터에서 P1/P1b/P5 가 죽었을 때 원인을 알 수 없었다.
  #    (실제 원인: 로그인에서 바이너리로 찾아 module load 줄이 안 들어갔고,
  #     계산 노드 PATH 에는 g16 이 없었다.)
  #    구분: module_load_failed / loaded_but_not_runnable / absent
  SEI_QC_DETAIL=""
  SEI_QC_MODULE="${SEI_QC_MODULE:-}"
  local module_state="not_attempted"

  # (1) 잡 스크립트가 이미 module load 를 했으면 PATH 에 보인다.
  #     여기서 한 번 더 시도하는 이유: 템플릿의 module 줄이 실패해도(사이트마다
  #     module 함수가 로그인 셸에서만 정의되는 경우가 있다) 여기서 되살릴 수 있다.
  # 🔴 `module load` EXIT STATUS IS NOT A SUCCESS SIGNAL ON THIS SITE.
  #    Real incident: loading a non-existent modulefile printed
  #      ModuleCmd_Load.c(208):ERROR:105: Unable to locate a modulefile for 'gaussian/g16.c01.lin'
  #    and we still recorded state="loaded", so we never tried the fallbacks — even though a
  #    working module (gaussian/g16.a03) was sitting in the fallback list.
  #    ⟹ Success is defined as **the binary appears and is executable**, never as exit 0.
  #    ⟹ And we walk the candidate list instead of attempting exactly one name.
  SEI_QC_MODULE_TRIED=""
  if command -v module > /dev/null 2>&1 || type module > /dev/null 2>&1; then
    local cand_list cand
    cand_list="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import envpaths
d, fb = envpaths.configured_gaussian_modules()
pre = os.environ.get("SEI_QC_MODULE") or ""
out = ([pre] if pre else []) + ([d] if d else []) + list(fb)
seen = set()
print("\n".join(x for x in out if x and not (x in seen or seen.add(x))))' 2>/dev/null)"
    for cand in ${cand_list}; do
      SEI_QC_MODULE_TRIED="${SEI_QC_MODULE_TRIED}${cand} "
      # 🔴 array 태스크별 파일 — 22태스크가 한 module_load.log 에 섞여 깨졌던 그 파일.
      module load "${cand}" >> "${SEI_JOB_DIR}/module_load${SEI_TASK_FILE_SUFFIX:-}.log" 2>&1 || true
      # 🔴 the only question that matters: is the binary there now?
      if command -v g16 > /dev/null 2>&1 || command -v g09 > /dev/null 2>&1; then
        SEI_QC_MODULE="${cand}"
        module_state="loaded"
        break
      fi
      module_state="module_load_failed"
      module unload "${cand}" > /dev/null 2>&1 || true
    done
  else
    module_state="module_command_missing"
  fi

  local out
  out="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import envpaths
from sei_pilot.shellrun import Shell
name, path = envpaths.resolve_qc(Shell())
print("%s\t%s" % (name or "", path or ""))' 2>/dev/null)"
  SEI_QC_BIN="$(printf '%s' "$out" | cut -f2)"
  local nm
  nm="$(printf '%s' "$out" | cut -f1)"

  if [ -n "${SEI_QC_BIN}" ]; then
    SEI_QC="gaussian16"
    [ "$nm" = "g09" ] && SEI_QC="gaussian09"
    # 🔴 찾았다고 끝이 아니다 — **실제로 실행되는지** 본다.
    #    경로가 로그인 노드에만 있는 공유되지 않은 경로일 수 있다.
    if [ ! -x "${SEI_QC_BIN}" ]; then
      SEI_QC=none
      SEI_QC_DETAIL="loaded_but_not_runnable: ${SEI_QC_BIN} 가 실행 가능하지 않다 "
      SEI_QC_DETAIL="${SEI_QC_DETAIL}(계산 노드에 없거나 권한 없음)"
    fi
  elif command -v orca > /dev/null 2>&1; then
    SEI_QC=orca; SEI_QC_BIN="$(command -v orca)"
  else
    SEI_QC=none; SEI_QC_BIN=""
    case "${module_state}" in
      module_load_failed)
        SEI_QC_DETAIL="module_load_failed: none of the candidates produced a runnable binary. tried: ${SEI_QC_MODULE_TRIED:-(none)}" ;;
      module_command_missing)
        SEI_QC_DETAIL="module_command_missing: 계산 노드 셸에 module 명령이 없다" ;;
      loaded)
        SEI_QC_DETAIL="loaded_but_binary_absent: module 은 로드됐는데 g16/g09 가 PATH 에 없다" ;;
      *)
        SEI_QC_DETAIL="absent: 시도할 모듈이 지정되지 않았고 PATH 에도 없다" ;;
    esac
  fi
  export SEI_QC SEI_QC_BIN SEI_QC_DETAIL

  # 🔴 로그인에서 본 경로가 계산 노드에도 있는지 기록한다. [UNVERIFIED] 를 없애는 값이다.
  local login_path="${SEI_QC_LOGIN_PATH:-}"
  local login_exists="unknown"
  if [ -n "${login_path}" ]; then
    if [ -e "${login_path}" ]; then login_exists="yes"; else login_exists="no"; fi
  fi
  # 🔴 array 태스크별 파일(adapter.t<N>.json). 비-array 잡은 접미사가 비어 이전과 같다.
  cat > "${SEI_JOB_DIR}/adapter${SEI_TASK_FILE_SUFFIX:-}.json" <<EOF
{"qc_code": "${SEI_QC}", "binary": "${SEI_QC_BIN}",
 "module_requested": "${SEI_QC_MODULE}",
 "modules_tried": "${SEI_QC_MODULE_TRIED:-}",
 "module_state": "${module_state}",
 "failure_detail": "${SEI_QC_DETAIL}",
 "login_binary_path": "${login_path}",
 "login_binary_exists_on_compute_node": "${login_exists}",
 "hostname": "$(hostname 2>/dev/null || echo unknown)",
 "detected_via": "module load(있으면) → envpaths.resolve_qc(PATH + extra + qc_env_vars)",
 "note": "실패 사유를 구분해 남긴다: module_load_failed / module_command_missing / loaded_but_binary_absent / loaded_but_not_runnable / absent"}
EOF
}

# --- Gaussian 입력 생성 ------------------------------------------------------
# $1=출력.gjf  $2=level(1|2)  $3=job_type  $4=charge  $5=mult  $6=xyz파일  [$7=extra]
sei_qc_input() {
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$@" <<'PY'
import json, os, re, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import basisset, config
from sei_pilot import solvent as solvent_mod

out_path, level, job_type, charge, mult, xyz_path = sys.argv[1:7]
extra = sys.argv[7] if len(sys.argv) > 7 else ""
cfg = config.load("qc_levels.json", {})
code = "gaussian16"
spec = (cfg.get(code) or {})
# level 인자는 "2" 처럼 짧게도, "level4_gen" 처럼 온전한 키로도 올 수 있다.
level_key = level if str(level).startswith("level") else ("level%s" % level)
lvl = spec.get(level_key) or {}
if not lvl:
    sys.stderr.write("알 수 없는 레벨: %s (정의된 것: %s)\n"
                     % (level, ", ".join(sorted(k for k in spec if k.startswith("level")))))
    sys.exit(2)
route_tmpl = (spec.get("job_types") or {}).get(job_type)
if not route_tmpl:
    sys.stderr.write("알 수 없는 job_type: %s (정의: %s)\n"
                     % (job_type, ", ".join(sorted((spec.get('job_types') or {})))))
    sys.exit(2)

# 🔴 [ADR-105/108] 용매는 solvent.resolve_solvent_deck() **한 곳**에서만 온다.
#    이전 판은 여기서 lvl["solvent_line"](정적 acetonitrile ε 35.7)을 그대로 스플라이스
#    했고, 그 경로로 P1/P1b/P5 가 14,464 core-h 를 잘못된 용매에서 돌았다(ADR-066/067).
#    거부(SolventUndecided/SolventDescriptorsMissing)는 폴백 없이 여기서 멈춘다 —
#    endpoint_prep 의 C-5 거부(exit 4, zero chemistry)와 같은, 의도된 결과다.
#    [P-0] pcm_numeric 후보 덱은 `read` 추가 입력 섹션(extra_input_lines)을 갖는다.
#    SEI_QC_PURPOSE=smoke 일 때만 미검증(deck_verified=false) 후보가 통과한다.
fields = {"functional": lvl.get("functional", "?"), "basis": lvl.get("basis", "?")}
solvent_section_lines = []
solvent_deck_label = None
purpose = os.environ.get("SEI_QC_PURPOSE") or "production"
# [S-1] 이 실행의 smoke 가 남긴 ε 실증 기록 — 있으면 본계산 게이트가 열린다
#       (config deck_verified 를 코드가 올리지 않고도 한 왕복에 끝나는 이유).
_rv = None
try:
    with open(os.path.join(os.environ["SEI_JOB_DIR"], "deck_verification%s.json"
                           % (os.environ.get("SEI_TASK_FILE_SUFFIX") or ""))) as fh:
        _rv = json.load(fh)
except (OSError, ValueError, KeyError):
    _rv = None
for ph in set(re.findall(r"{(\w+)}", route_tmpl)):
    if ph == "solvent" or ph.startswith("solvent_"):
        variant = None if ph == "solvent" else ph[len("solvent_"):]
        try:
            # [user ruling 2026-08-21] no EpsInf plumbing: the PCM deck names a carrier
            # solvent (solvent.PCM_CARRIER_SOLVENT) and overrides only eps. See solvent.py.
            deck = solvent_mod.resolve_solvent_deck(
                solvent_mod.load_policy(), variant, purpose,
                runtime_verification=_rv)
        except (solvent_mod.SolventUndecided,
                solvent_mod.SolventDescriptorsMissing) as exc:
            sys.stderr.write("solvent_refused (C-5): %s\n" % exc)
            sys.exit(4)
        fields[ph] = deck["route_fragment"]
        for line in deck["extra_input_lines"]:
            if line not in solvent_section_lines:
                solvent_section_lines.append(line)
        solvent_deck_label = deck["label"] or solvent_deck_label
if solvent_deck_label:
    # 라벨은 출력에도 실린다 (P-0 요구 1). stderr 는 meta.err 로 남는다.
    sys.stderr.write("solvent_deck_label: %s\n" % solvent_deck_label)
route = route_tmpl.format(**fields)
if extra:
    route = route + " " + extra

# 🔴 %mem: G16은 메모리가 모자라면 조용히 느려지는 게 아니라 galloc 으로 죽는다.
#    프로브가 잰 노드 RAM(SEI_NODE_RAM_GB)을 쓰고, 없으면 보수적으로 4 GB.
pol = cfg.get("resource_policy") or {}
ram = float(os.environ.get("SEI_NODE_RAM_GB") or 0)
if ram > 0:
    mem = ram * float(pol.get("mem_fraction_of_node", 0.7))
else:
    mem = 4.0
mem = max(float(pol.get("mem_floor_gb", 2)), min(mem, float(pol.get("mem_cap_gb", 200))))
nproc = int(os.environ.get("SEI_TOTAL_CORES") or 1)

def _read_coords(path):
    lines = open(path).read().splitlines()
    n = int(lines[0].split()[0])
    return open(path).read(), [l for l in lines[2:2 + n] if l.strip()]

xyz_text, coords = _read_coords(xyz_path)

# 🔴 QST2 같은 **양끝단** job_type 은 분자 지정이 2벌 필요하다(반응물 → 생성물).
#    두 번째 구조는 SEI_QC_XYZ2 로 받는다. 필요한데 없으면 조용히 단끝단으로
#    돌지 않고 **여기서 멈춘다** (그러면 route 와 입력이 어긋나 G16이 죽는다).
# 🔴 [U56-2, B-1] relaxed scan(opt=modredundant)의 ModRedundant 추가 입력 섹션.
#    좌표 지정("B i j S N step")은 role→index mapping 에서 deck builder(b0f_deck.py)가
#    만들어 파일로 넘긴다 — 원자 index 를 여기·config 어디에도 박지 않는다(§39.26(d)).
#    route 가 modredundant 인데 섹션이 없으면 **여기서 멈춘다**: G16 이 다음 섹션(gen
#    기저 블록)을 ModRedundant 입력으로 읽어 쓰레기 스캔이 조용히 돈다.
modred_path = os.environ.get("SEI_QC_MODREDUNDANT_FILE") or ""
modred_lines = []
route_wants_modred = "modredundant" in route.lower()
if route_wants_modred:
    try:
        modred_lines = [l.strip() for l in open(modred_path).read().splitlines()
                        if l.strip()]
    except OSError:
        modred_lines = []
    if not modred_lines:
        sys.stderr.write("job_type=%s (opt=modredundant) 는 ModRedundant 섹션이 필요하다. "
                         "SEI_QC_MODREDUNDANT_FILE 이 없거나 비었다 (%r). 스캔 좌표는 "
                         "deck builder 의 role→index mapping 에서만 온다 — 여기서 지어 "
                         "넣지 않는다.\n" % (job_type, modred_path))
        sys.exit(2)
elif modred_path:
    sys.stderr.write("경고: SEI_QC_MODREDUNDANT_FILE 가 주어졌지만 job_type=%s 의 route 에 "
                     "modredundant 가 없다 — 무시한다.\n" % job_type)
    modred_path = ""

pair_types = set(spec.get("_pair_job_types") or [])
xyz2_path = os.environ.get("SEI_QC_XYZ2") or ""
coords2 = None
if job_type in pair_types:
    if not xyz2_path:
        sys.stderr.write("job_type=%s 는 구조 2벌이 필요하다. SEI_QC_XYZ2 를 지정하라.\n"
                         % job_type)
        sys.exit(2)
    xyz2_text, coords2 = _read_coords(xyz2_path)
    xyz_text = xyz_text + xyz2_text          # 원소 커버리지는 두 구조 합집합으로
elif xyz2_path:
    sys.stderr.write("경고: SEI_QC_XYZ2 가 주어졌지만 job_type=%s 는 단일 구조다 — 무시한다.\n"
                     % job_type)

# 🔴 `gen` 기저 사전검증 — **입력 파일을 쓰기 전에** 한다.
#    검사 대상은 "기저 이름이 유효한가"가 아니라 "동봉 블록이 이 분자의 등장 원소를
#    전부 덮는가"다. 못 덮으면 G16은 좌표를 다 읽고 SCF 직전에 죽는다.
basis_block = None
basis_info = {}
if (lvl.get("basis") or "").lower() == "gen":
    try:
        loaded = basisset.load_for_level(lvl)
        els = basisset.elements_in_xyz(xyz_text)
        basisset.check_coverage(els, loaded["text"],
                                context="%s / %s, 입력=%s"
                                        % (lvl.get("label", "?"),
                                           lvl.get("basis_real_name", "?"),
                                           os.path.basename(xyz_path)))
        basis_block = basisset.block(loaded["text"], only=els)
        basis_info = {"basis_real_name": lvl.get("basis_real_name"),
                      "basis_file": lvl.get("basis_file"),
                      "elements_in_molecule": els,
                      "elements_in_basis": basisset.parse_elements(loaded["text"]),
                      "elements_emitted": els,
                      "has_ecp": basisset.has_ecp(loaded["text"])}
    except basisset.BasisError as exc:
        sys.stderr.write("%s\n" % exc)
        sys.exit(3)
    if basis_info.get("has_ecp"):
        sys.stderr.write("🔴 동봉 기저에 ECP 블록이 있다. `gen` 만으로는 부족하고 "
                         "route 에 `pseudo=read` 와 ECP 블록이 더 필요하다. "
                         "지금 어댑터는 ECP를 처리하지 않는다 — 조용히 진행하지 않는다.\n")
        sys.exit(3)

with open(out_path, "w") as fh:
    fh.write("%%nprocshared=%d\n" % nproc)
    fh.write("%%mem=%dGB\n" % int(mem))
    # 🔴 [ADR-107 클래스, proposer7 지적] %chk 는 상대경로다(cwd = job/step dir). array
    #    태스크가 같은 디렉터리를 공유하면 고정 이름은 서로의 .chk 를 덮어쓰거나 잘못
    #    읽는다 — 크래시가 아니라 **조용히 틀린 답**이다(IRC 가 남의 Hessian 을 읽는
    #    형태). A-1 per-task 격리 패턴(SEI_TASK_FILE_SUFFIX)을 %chk 파일명에도 물린다.
    #    비-array 잡은 접미사가 비어 이전과 바이트 동일하다.
    fh.write("%%chk=%s%s.chk\n" % (os.path.splitext(os.path.basename(out_path))[0],
                                   os.environ.get("SEI_TASK_FILE_SUFFIX") or ""))
    fh.write(route + "\n")
    fh.write("\n")
    fh.write("sei_pilot %s %s\n" % (job_type, level_key))
    fh.write("\n")
    fh.write("%s %s\n" % (charge, mult))
    def _emit(rows):
        for c in rows:
            f = c.split()
            fh.write("%-3s %14.8f %14.8f %14.8f\n"
                     % (f[0], float(f[1]), float(f[2]), float(f[3])))
        fh.write("\n")
    _emit(coords)
    # [U56-2] ModRedundant 섹션 — 분자 지정 **바로 뒤**, gen 기저 블록 **앞** (G16 의
    # 추가 입력 섹션 순서). 🔴 이 순서(좌표 → modredundant → 기저 → 용매 read)는
    # 후보이며 클러스터 route smoke 가 실증하기 전까지 [UNVERIFIED] 다 — 용매 read
    # 섹션의 기존 주석과 같은 지위.
    if modred_lines:
        for line in modred_lines:
            fh.write(line + "\n")
        fh.write("\n")
    if coords2 is not None:
        # 두 번째 분자 지정: title → 빈 줄 → charge mult → 좌표 → 빈 줄
        fh.write("sei_pilot %s %s (structure 2)\n" % (job_type, level_key))
        fh.write("\n")
        fh.write("%s %s\n" % (charge, mult))
        _emit(coords2)
    # gen 기저 블록은 **좌표 뒤 빈 줄 다음**에 온다. 블록 뒤에도 빈 줄이 필요하다.
    if basis_block:
        fh.write(basis_block)
        fh.write("\n")
    # [P-0] scrf `read` 추가 입력 섹션 — gen 기저 블록 **뒤**, 각 섹션은 빈 줄로 닫는다.
    # 🔴 이 섹션 순서(기저 → 용매)는 후보이며, 클러스터 route smoke 가 실증하기 전까지
    #    [UNVERIFIED] 다 (solvent.UNVERIFIED_DECK_LABEL 이 meta 에 함께 실린다).
    if solvent_section_lines:
        for line in solvent_section_lines:
            fh.write(line + "\n")
        fh.write("\n")
out = {"route": route, "mem_gb": int(mem), "nprocshared": nproc,
       "n_structures": 2 if coords2 is not None else 1,
       "chk_file": "%s%s.chk" % (os.path.splitext(os.path.basename(out_path))[0],
                                 os.environ.get("SEI_TASK_FILE_SUFFIX") or ""),
       "modredundant_lines": modred_lines,
       "solvent_extra_input_lines": solvent_section_lines,
       "solvent_deck_label": solvent_deck_label,
       "level": level_key, "level_label": lvl.get("label"),
       "job_type": job_type, "level_status": lvl.get("_status", "")}
out.update(basis_info)
print(json.dumps(out, ensure_ascii=False))
PY
}

sei_qc_run() {   # $1=작업디렉터리 $2=입력.gjf(상대) $3=로그(상대)
  ( cd "$1" && "${SEI_QC_BIN}" < "$2" > "$3" 2>&1 )
}

# --- route 사전검증 ----------------------------------------------------------
# 🔴 본계산 전에 **실제로 쓸 route** 를 H2로 수초 돌린다.
#    이름이 틀리면 여기서 잡고 후보를 출력한다(왕복 1회 = 3.5일을 지키는 장치).
sei_qc_smoke() {
  # 🔴 array 태스크별 디렉터리(smoke.t<N>/) — 태스크들이 같은 h2/gjf/log 를 덮어쓰지 않게.
  local d="${SEI_JOB_DIR}/smoke${SEI_TASK_FILE_SUFFIX:-}" lvl rc_all=0
  mkdir -p "$d"
  case "${SEI_QC}" in
    gaussian16|gaussian09) ;;
    orca) echo "smoke=orca_path_not_supported_here"; return 1 ;;
    *) echo "smoke=skipped_no_adapter"; return 1 ;;
  esac

  printf '2\nH2 route 검증용\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n' > "$d/h2.xyz"
  for lvl in 1 2; do
    # [P-0] smoke 는 미검증 후보 덱도 통과시킨다 (SEI_QC_PURPOSE=smoke) — 이 스모크가
    #       바로 그 후보 덱을 실증하는 장치이기 때문이다. 본계산 경로는 계속 거부된다.
    if ! SEI_QC_PURPOSE=smoke sei_qc_input "$d/smoke_L${lvl}.gjf" "$lvl" sp 0 1 "$d/h2.xyz" \
         > "$d/smoke_L${lvl}.meta.json" 2>"$d/smoke_L${lvl}.err"; then
      echo "smoke_L${lvl}=input_generation_failed"
      # 🔴 C-5 용매 거부 등 사유를 stdout 에도 올린다 — .err 파일만 남기면 사람이
      #    "왜 안 돌았나"를 왕복 한 번 더 써서 물어야 한다.
      sed 's/^/    ↳ /' "$d/smoke_L${lvl}.err" 2>/dev/null | head -8
      rc_all=1; continue
    fi
    sei_qc_run "$d" "smoke_L${lvl}.gjf" "smoke_L${lvl}.log"
    if grep -q "Normal termination" "$d/smoke_L${lvl}.log" 2>/dev/null; then
      echo "smoke_L${lvl}=ok"
    else
      rc_all=1
      echo "smoke_L${lvl}=fail"
      echo "  ↳ Gaussian이 이 route 를 받아들이지 않았다. 본계산을 시작하지 않는다."
      echo "  ↳ route: $(grep -m1 '^#' "$d/smoke_L${lvl}.gjf")"
      echo "  ↳ 고칠 곳: config/qc_levels.json 의 gaussian16.level${lvl}"
      echo "  ↳ 🔴 이 레벨은 아직 proposer 판정 대기다 — config 의 _status 를 보라"
      echo "       (ADR-029 기본 레벨은 VV10 계열이라 G16에 없을 수 있다)."
      echo "       실패해도 그것 자체가 회신할 정보다."
      echo "  ↳ Gaussian 원문 (마지막 25줄):"
      tail -25 "$d/smoke_L${lvl}.log" 2>/dev/null | sed 's/^/      /'
    fi
  done
  # 🔴 [§39.74 / §39.90] "a route smoke that does not exercise every stage the route contains
  #    is not a route smoke." The EpsInf sentinel lived ONLY in the Hessian path; an sp smoke
  #    passed while every freq stage in the round died. So the smoke now also runs `freq` on
  #    H2 at each level (seconds) and records G16's own `NEqPCM:` line and `Solvent :` block,
  #    which is proposer8's requested measurement of what THIS build does with the named
  #    carrier solvent + numeric eps (documentation sources disagree; the log settles it).
  #    [lead/user 2026-08-21, 3-deck H2 smoke] two freq decks per level:
  #      production  = the live policy deck (solvent=acetone, eps=18.5)      -> GATES production
  #      legacy      = generic + eps + EpsInf=eps (the deck the 18.5 arm ran) -> COMPARISON ONLY,
  #                    recorded, never gates (a failure here is information, not a stop)
  local tag jt
  for lvl in 1 2; do
    for tag in production legacy; do
      jt=freq; [ "$tag" = legacy ] && jt=freq_smoke_legacy_generic
      if ! SEI_QC_PURPOSE=smoke sei_qc_input "$d/smoke_freq_${tag}_L${lvl}.gjf" "$lvl" "$jt" 0 1 "$d/h2.xyz" \
           > "$d/smoke_freq_${tag}_L${lvl}.meta.json" 2>"$d/smoke_freq_${tag}_L${lvl}.err"; then
        echo "smoke_freq_${tag}_L${lvl}=input_generation_failed"
        sed 's/^/    ↳ /' "$d/smoke_freq_${tag}_L${lvl}.err" 2>/dev/null | head -8
        [ "$tag" = production ] && rc_all=1
        continue
      fi
      sei_qc_run "$d" "smoke_freq_${tag}_L${lvl}.gjf" "smoke_freq_${tag}_L${lvl}.log"
      if grep -q "Normal termination" "$d/smoke_freq_${tag}_L${lvl}.log" 2>/dev/null \
         && ! grep -q "Error termination" "$d/smoke_freq_${tag}_L${lvl}.log" 2>/dev/null; then
        echo "smoke_freq_${tag}_L${lvl}=ok"
      else
        echo "smoke_freq_${tag}_L${lvl}=fail"
        if [ "$tag" = production ]; then
          rc_all=1
          echo "  ↳ 🔴 freq 단계가 이 덱을 받지 않았다 — 본계산의 Hessian 도 같은 자리에서 죽는다."
        else
          echo "  ↳ (legacy comparison deck only -- recorded, does not stop production)"
        fi
        grep -m3 "NEqPCM\|EpsInf\|Error termination" "$d/smoke_freq_${tag}_L${lvl}.log" 2>/dev/null | sed 's/^/      /'
      fi
    done
  done
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$d" "${SEI_JOB_DIR}" <<'PY'
import json, os, re, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
d, jobdir = sys.argv[1], sys.argv[2]
out = {"code": os.environ.get("SEI_QC"), "levels": {}, "freq_smoke": {}}
def _block(lines, start_re, n):
    for i, ln in enumerate(lines):
        if re.match(start_re, ln):
            return [l.rstrip() for l in lines[i:i + n]]
    return []
for lvl in ("1", "2"):
    for tag in ("production", "legacy"):
        try:
            ft = open(os.path.join(d, "smoke_freq_%s_L%s.log" % (tag, lvl)),
                      errors="replace").read()
        except OSError:
            ft = ""
        try:
            fmeta = json.load(open(os.path.join(d, "smoke_freq_%s_L%s.meta.json" % (tag, lvl))))
        except (OSError, ValueError):
            fmeta = {}
        fs = g16.summarize(ft)
        lines = ft.splitlines()
        # [lead 2026-08-21] everything the 3-deck comparison reads, verbatim from G16:
        out["freq_smoke"]["%s_level%s" % (tag, lvl)] = {
            "deck": tag, "route": fmeta.get("route"),
            "solvent_extra_input_lines": fmeta.get("solvent_extra_input_lines"),
            "ok": bool(fs["normal_termination"] and "Error termination" not in ft),
            "failure_reason": fs["failure_reason"],
            "elapsed": fs.get("timings"),
            "n_frequencies": fs["n_frequencies"],
            "frequencies_cm1": g16.parse_frequencies(ft),
            "neqpcm_lines": [l.strip() for l in lines if "NEqPCM" in l][:4],
            # PCM header: Atomic radii / Cavity type / 1st-2nd derivative terms ...
            "pcm_block": _block(lines, r"\s*Polarizable Continuum Model", 22),
            # Solvent : <name>, Eps, Eps(infinity), RSolv, density, HB acidity/basicity ...
            "solvent_block": _block(lines, r"\s*Solvent\s*:", 13),
            "g_cav_disp_rep_present": {k: (k in ft) for k in ("G(cav)", "G(disp)", "G(rep)")},
            "cavitation_mentions": len(re.findall(r"(?i)cavitation", ft)),
            "epsinf_sentinel_seen": "EpsInf not defined" in ft,
        }
for lvl in ("1", "2"):
    log = os.path.join(d, "smoke_L%s.log" % lvl)
    try:
        text = open(log, errors="replace").read()
    except OSError:
        text = ""
    s = g16.summarize(text)
    try:
        meta = json.load(open(os.path.join(d, "smoke_L%s.meta.json" % lvl)))
    except (OSError, ValueError):
        meta = {}
    out["levels"]["level%s" % lvl] = {
        "ok": s["normal_termination"], "failure_reason": s["failure_reason"],
        "failure_message": s["failure_message"][:200],
        # [P-0] 후보 덱 라벨과 read 섹션 — 이 스모크가 실증 대상 형식 그 자체를 실었다는
        # 기록 (라벨은 코드와 출력 양쪽, ADR-108).
        "solvent_deck_label": meta.get("solvent_deck_label"),
        "solvent_extra_input_lines": meta.get("solvent_extra_input_lines"),
        # B-1: g16.summarize() no longer has a bare `route` field (RT-1's
        # 70-column truncation, no marker). `route_echoed` is the reassembled
        # route from the same call; `route_echoed_is_complete` says whether the
        # reassembly could confirm the echo was not itself cut.
        "route_requested": meta.get("route"), "route_echoed": s.get("route_echoed"),
        "route_echoed_is_complete": s.get("route_echoed_is_complete"),
        "level_status": meta.get("level_status", ""),
        "mem_gb": meta.get("mem_gb"), "nprocshared": meta.get("nprocshared")}
# array 태스크별 파일(smoke_levels.t<N>.json). 비-array 는 접미사가 비어 이전과 같다.
sfx = os.environ.get("SEI_TASK_FILE_SUFFIX") or ""
json.dump(out, open(os.path.join(jobdir, "smoke_levels%s.json" % sfx), "w"),
          ensure_ascii=False, indent=1)

# --- [S-1] ε 실증: route echo 만으로는 부족하다 — eps 는 read 추가 입력 섹션에 있어
#     G16 이 그 섹션을 무시해도 route echo 는 멀쩡하다. G16 **출력**에서 유전상수
#     후보값을 파싱해 요청값과 대조하고, 결과(증거 원문 포함)를 deck_verification 에
#     남긴다. pcm_numeric 이고 불일치/부재면 rc 1 → payload 가 본계산 전에 멈춘다.
#     매치되면 이 기록이 같은 잡의 본계산 게이트를 연다(runtime verification, S-2:
#     config deck_verified 는 코드가 올리지 않는다 — lead 몫).
from sei_pilot import solvent as solvent_mod
policy = solvent_mod.load_policy() or {}
if policy.get("model") == "pcm_numeric":
    eps_req = float(policy.get("epsilon") or 0)
    found_values, evidence = [], []
    for lvl in ("1", "2"):
        try:
            text = open(os.path.join(d, "smoke_L%s.log" % lvl), errors="replace").read()
        except OSError:
            text = ""
        rec = g16.parse_scrf_dielectric(text)
        found_values += rec["values"]
        evidence += [l for l in rec["evidence_lines"] if l not in evidence]
    matched = any(abs(v - eps_req) < 1e-6 for v in found_values)
    ver = {
        "model": "pcm_numeric",
        "eps_requested": eps_req,
        "eps_found_values": found_values,
        "eps_matched": bool(matched),
        "evidence_lines": evidence[:10],
        "_echo_caveat": ("evidence 에는 read 입력 섹션의 에코가 섞일 수 있다 — "
                         "원문으로 판단하라. 파싱 패턴 자체가 후보다(첫 실 로그가 검증)."),
        "label": (solvent_mod.VERIFIED_IN_RUN_LABEL if matched
                  else solvent_mod.UNVERIFIED_DECK_LABEL),
    }
    ver["freq_smoke"] = out["freq_smoke"]
    json.dump(ver, open(os.path.join(jobdir, "deck_verification%s.json" % sfx), "w"),
              ensure_ascii=False, indent=1)
    if not matched:
        print("smoke_eps_verification=FAILED")
        print("  ↳ 🔴 요청 ε=%s 가 G16 출력에서 확인되지 않았다 (발견값: %s)."
              % (eps_req, found_values or "없음"))
        print("  ↳ 후보 덱 형식(read 섹션의 eps=)이 이 G16 에서 적용되지 않았을 수 있다.")
        print("  ↳ 증거 원문은 deck_verification%s.json — 그대로 회신하라." % sfx)
        sys.exit(1)
    print("smoke_eps_verification=ok (eps=%s, 증거 %d줄 — 원문은 deck_verification%s.json)"
          % (eps_req, len(evidence), sfx))
PY
  # 위 python 이 rc 1 이면 (ε 미실증) smoke 실패로 취급한다 — payload 의
  # "route 검증 실패 → 중단"(exit 4)으로 이어져 본계산 전에 0 core-h 로 끝난다.
  [ $? -ne 0 ] && rc_all=1
  return $rc_all
}
