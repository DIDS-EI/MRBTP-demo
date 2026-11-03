"""common.py —— examples/paper_reproduction 四个复现脚本的共享基础设施。

本目录用 **mrbtp-demo 自己的算法**（app.planner.plan_behavior_trees + app.executor.execute）
去复现论文 MRBTP（arXiv:2502.18072）的 Fig4 / Table1 / Table2 / Table3。

与论文口径的对应 & 适配说明
============================
论文原实验用真实 MRBTP、多套仿真环境（warehouse / VirtualHome）、真实 LLM 预规划子树、
每格 500 trials。mrbtp-demo 是教学 demo：只有 3 个网格 project、无 LLM、规模小。
因此这里是**忠实结构、缩小规模**的近似复现——曲线形状 / 指标趋势对得上即可，
绝对数值不追求与论文逐位相同。三处关键适配：

1. **α（Homogeneity 同质性）作为自变量** —— 论文横扫 α∈[0,1]。demo 里 α 由每个 agent
   的宏库（composite_library）决定。我们在**同一个 project 场景**上，通过重新分配宏库
   构造出若干 α 档位：宏库越互不重叠 α 越大（异构），越共享 α 越小（同构）。
   见 ``make_alpha_variants``。

2. **FP（Action Failure Probability 动作失败概率）** —— demo 的 execute 无此参数。
   用 monkeypatch 让每个 agent 这一 tick 选出的高层原语以概率 p 失效（改成 done、
   不推进栅格），等价于「机器人尝试动作但失败」。见 ``inject_action_failure``。

3. **Comm（通信广播次数）** —— 论文统计意图共享的广播条数。demo 里一个 agent 接下
   新宏任务并把子目标写进共享信念空间时发生一次广播。我们 monkeypatch
   ``agent.update_current_task`` 计数。无通信（share_belief=False）时 executor 会
   ``_disable_belief_sharing`` 覆盖这些方法 → 计数器不触发 → Comm=0。见 ``install_comm_counter``。

4. **"LLM 预规划子树" ↔ composite_action 宏库** —— demo 无 LLM。论文里 LLM 把长程
   任务预规划成子树；demo 的 ``use_composite_actions=True`` 用**预置宏库**扮演同一角色
   （宏 = 一段预规划好的多步子树）。Table3 的 LLM 平均响应 4.2s 在 demo 中不存在，
   PT 只反映回链搜索墙钟时间。
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Callable, Dict, List, Optional

# ---- 无头 & import 路径 ----------------------------------------------------- #
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]                       # examples/paper_reproduction/ → 仓库根
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
# ablation_study 里有 homogeneity.py，复用它算 α
_ABLATION = _REPO / "examples" / "ablation_study"
if str(_ABLATION) not in sys.path:
    sys.path.insert(0, str(_ABLATION))

from minigrid.core.actions import Actions        # noqa: E402
from app.planner import plan_behavior_trees       # noqa: E402
from app.executor import execute                  # noqa: E402
from app.scenario import Scenario                 # noqa: E402
from homogeneity import homogeneity_alpha, alpha_breakdown  # noqa: E402


# --------------------------------------------------------------------------- #
# 工具：吞掉规划/执行内部的海量调试 print（stderr 保留）
# --------------------------------------------------------------------------- #
@contextlib.contextmanager
def silence_stdout():
    devnull = open(os.devnull, "w")
    old = sys.stdout
    try:
        sys.stdout = devnull
        yield
    finally:
        sys.stdout = old
        devnull.close()


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# 1) 动态加载三个 project 的 build_scenario（复用练习场景，不重复定义）
# --------------------------------------------------------------------------- #
@dataclass
class ProjectSpec:
    key: str
    title: str
    solve_path: Path
    build_scenario: Callable
    alpha: float = 0.0
    num_agent: int = 0


def _load_build_scenario(solve_path: Path) -> Callable:
    spec = importlib.util.spec_from_file_location(
        f"_solve_{solve_path.parent.parent.name}", solve_path)
    mod = importlib.util.module_from_spec(spec)
    projects_dir = solve_path.parents[2]          # .../examples/projects
    if str(projects_dir) not in sys.path:
        sys.path.insert(0, str(projects_dir))
    spec.loader.exec_module(mod)
    return mod.build_scenario


# 论文复现默认只用 proj2 / proj3。proj1 是原生 DoorKey（无 domain 宏库），
# 纯原子/分工模式下回链搜索空间爆炸（>20s 超时），且规模上不适合 α×FP 多格扫描；
# proj2/proj3 有完整 domain 宏库、各配置规划都 <3s，适合缩小规模的忠实结构复现。
# 需要含 proj1 时显式传 keys=("proj1","proj2","proj3")。
PAPER_PROJECTS = ("proj2", "proj3")

_PROJECT_DEFS = {
    "proj1": ("proj1 · 原生 DoorKey 取钥匙开门搬运",
              "proj1_two_rooms/solution/solve.py"),
    "proj2": ("proj2 · 家庭整理 搬·擦·扫",
              "proj2_home/solution/solve.py"),
    "proj3": ("proj3 · 战场 运输·占领·构筑",
              "proj3_battle/solution/solve.py"),
}


def discover_projects(keys=PAPER_PROJECTS) -> List[ProjectSpec]:
    root = _REPO / "examples" / "projects"
    specs: List[ProjectSpec] = []
    for key in keys:
        title, rel = _PROJECT_DEFS[key]
        path = root / rel
        build = _load_build_scenario(path)
        with silence_stdout():
            sc = build()
        specs.append(ProjectSpec(
            key=key, title=title, solve_path=path, build_scenario=build,
            alpha=homogeneity_alpha(sc.composite_library),
            num_agent=sc.num_agent,
        ))
    return specs


# --------------------------------------------------------------------------- #
# 2) α 扫描：在同一 project 上重分配宏库，构造不同 α 档位
# --------------------------------------------------------------------------- #
def make_alpha_variants(spec: ProjectSpec):
    """基于一个 project 原始宏库，构造几档不同 α 的「同一场景变体」。

    做法：原始配置三人宏库互不相同 → α 最高（最异构）。要降低 α（更同构），
    就让 agent 之间**共享**宏——把某些 agent 的宏库替换成别人的拷贝，制造冗余。
    返回 [(alpha, build_variant_fn), ...]，alpha 从高到低。

    注意：这里只重写 composite_library（能力分配），goal/env/num_agent 不变，
    所以「同一个任务、同一张图，只是把技能在队员间的分配方式改了」——正是论文
    里 α 作为团队同质性自变量的语义。
    """
    with silence_stdout():
        base = spec.build_scenario()
    orig_lib = copy.deepcopy(base.composite_library)
    n = len(orig_lib)

    def _rebuild(new_lib):
        def _fn():
            with silence_stdout():
                sc = spec.build_scenario()
            sc.composite_library = copy.deepcopy(new_lib)
            return sc
        return _fn

    variants = []

    # 档位 High：原始（各不相同）—— α 最大
    variants.append((homogeneity_alpha(orig_lib), _rebuild(orig_lib)))

    # 档位 Mid：后 n-1 个 agent 共享 agent-0 的宏（部分重叠）—— α 中
    if n >= 2:
        mid = [copy.deepcopy(orig_lib[0])]
        for i in range(1, n):
            merged = copy.deepcopy(orig_lib[i])
            merged.update(copy.deepcopy(orig_lib[0]))   # 每人多拿一份 agent-0 的宏
            mid.append(merged)
        variants.append((homogeneity_alpha(mid), _rebuild(mid)))

    # 档位 Low：所有 agent 宏库合并成同一个大全集（人人都会全部宏）—— α 最小（最同构）
    if n >= 2:
        allmacros: Dict[str, list] = {}
        for lib in orig_lib:
            allmacros.update(copy.deepcopy(lib))
        low = [copy.deepcopy(allmacros) for _ in range(n)]
        variants.append((homogeneity_alpha(low), _rebuild(low)))

    # 按 α 从高到低排序、去重相近档位
    variants.sort(key=lambda x: -x[0])
    dedup = []
    for a, fn in variants:
        if not dedup or abs(dedup[-1][0] - a) > 1e-3:
            dedup.append((round(a, 3), fn))
    return dedup


# --------------------------------------------------------------------------- #
# 3) FP 注入 与 Comm 计数（monkeypatch，非侵入 mrbtp-demo 源码）
# --------------------------------------------------------------------------- #
def inject_action_failure(env, p: float, rng: random.Random) -> None:
    """monkeypatch 每个 agent.step：这一 tick 选出的非空闲原语以概率 p 失效。"""
    if p <= 0:
        return
    for agent in env.agents:
        orig_step = agent.step

        def make(orig, ag):
            def wrapped():
                action = orig()
                if action != Actions.done and rng.random() < p:
                    ag.action = Actions.done
                    return Actions.done
                return action
            return wrapped

        agent.step = make(orig_step, agent)


def install_comm_counter(env) -> dict:
    """monkeypatch 每个 agent.update_current_task：接下新宏任务→广播意图，计一次。

    无通信（share_belief=False）时 executor 的 _disable_belief_sharing 会先替换掉
    update_current_task/finish_current_task，我们的 wrapper 随之失效 → Comm=0，
    正好对应论文「无意图共享则无广播」。"""
    counter = {"n": 0}
    for agent in env.agents:
        orig = agent.update_current_task

        def make(orig, ag):
            def wrapped():
                if getattr(ag, "current_task", None) is not None:
                    counter["n"] += 1
                return orig()
            return wrapped

        agent.update_current_task = make(orig, agent)
    return counter


# --------------------------------------------------------------------------- #
# 4) 指标采集：一次「规划 + 执行」，返回 SR/TS/RS/Comm/EC/PT
# --------------------------------------------------------------------------- #
STALL_LIMIT = 40   # 全队连续这么多步零活跃原语 → 判定死锁提前结束（避免空转满 max_steps）


def _count_active(env) -> int:
    return sum(1 for a in env.agents
               if getattr(a, "action", None) not in (None, Actions.done))


@dataclass
class RunMetrics:
    success: bool
    planning_time: float     # PT：回链搜索墙钟秒数
    expanded_num: int        # EC：扩展条件数
    team_steps: int          # TS：并行仿真步数
    robot_steps: int         # RS：各 agent 非空闲原语之和
    comm: int                # Comm：意图广播次数


def run_once(build_scenario: Callable, *, single_expand: bool, share_belief: bool,
             use_composite_actions: bool = True, fp: float = 0.0,
             seed: int = 0, max_steps: int = 600) -> RunMetrics:
    """一次完整「规划 + 执行」并采集全部六项指标。"""
    with silence_stdout():
        scenario = build_scenario()
        env = scenario.build_env(render=False)
        plan = plan_behavior_trees(
            env, scenario, optimal=True,
            use_composite_actions=use_composite_actions,
            single_expand=single_expand, verbose=False)

        rng = random.Random(seed)
        comm = install_comm_counter(env)     # 先装计数器
        inject_action_failure(env, fp, rng)  # 再注入 FP

        robot_steps = {"n": 0}
        stall = {"s": 0}

        def on_step(rec, e):
            active = _count_active(e)
            robot_steps["n"] += active
            stall["s"] = 0 if active else stall["s"] + 1

        def should_stop(rec, e):
            return stall["s"] >= STALL_LIMIT

        random.seed(seed)
        result = execute(env, plan, share_belief=share_belief,
                         max_steps=max_steps, on_step=on_step,
                         should_stop=should_stop, print_ticks=False)

    return RunMetrics(
        success=result.success,
        planning_time=plan.planning_time,
        expanded_num=plan.expanded_num,
        team_steps=result.steps,
        robot_steps=robot_steps["n"],
        comm=comm["n"],
    )


def plan_only(build_scenario: Callable, *, single_expand: bool,
              use_composite_actions: bool = True, repeats: int = 3):
    """只规划、取中位数，返回 (planning_time, expanded_num)。规划确定性，与 seed 无关。"""
    times, exps = [], []
    for _ in range(repeats):
        with silence_stdout():
            scenario = build_scenario()
            env = scenario.build_env(render=False)
            plan = plan_behavior_trees(
                env, scenario, optimal=True,
                use_composite_actions=use_composite_actions,
                single_expand=single_expand, verbose=False)
        times.append(plan.planning_time)
        exps.append(plan.expanded_num)
    return median(times), int(median(exps))


# --------------------------------------------------------------------------- #
# 5) 结果落盘：CSV + Markdown 表
# --------------------------------------------------------------------------- #
RESULTS_DIR = _HERE.parent / "results"


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_md_table(path: Path, title: str, headers: List[str],
                   rows: List[List], note: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    if note:
        lines += [note, ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
