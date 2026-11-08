"""``python -m backends.virtualhome.check`` —— 符号后端的一体化自检。

覆盖三件事：

1. **协议**：后端 / 智能体满足 ``SimBackend`` / ``SimAgent``，且已注册；
2. **链路**：``make_backend → plan_behavior_trees → execute`` 真的把目标达成；
3. **等价性**：新域的动作模型 / 初始状态 / 冲突检测与
   ``examples/paper_reproduction/repro/domains.py`` 逐项一致（examples 可用时）。

从仓库根运行::

    .venv/bin/python -m backends.virtualhome.check
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_protocol(backend):
    from core.interfaces import SimAgent, SimBackend, available_backends

    assert "virtualhome" in available_backends(), "后端没有注册"
    assert isinstance(backend, SimBackend), "不满足 SimBackend 协议"
    assert all(isinstance(a, SimAgent) for a in backend.agents), \
        "智能体不满足 SimAgent 协议"
    print("[OK ] SimBackend / SimAgent 协议 + 注册")


def check_model_equivalence():
    """与论文复现域逐动作比对；examples 不可用时跳过。"""
    # 追加而非置顶：该目录下有 ``domains.py`` 等顶层模块，放到 sys.path[0]
    # 可能遮蔽仓库根的同名包，进而污染后续 import。
    sys.path.append(str(ROOT / "examples" / "paper_reproduction"))
    try:
        from repro.domains import (build_vh_action_lists as legacy_actions,
                                   make_conflict_fn as legacy_conflict,
                                   vh_start_state as legacy_start)
    except Exception as exc:                       # pragma: no cover
        print(f"[skip] 复现域不可用：{type(exc).__name__}: {exc}")
        return

    from core.envs.domains.virtualhome.model import (build_action_lists,
                                                     make_conflict_fn,
                                                     start_state)

    task_file = ROOT / "examples/paper_reproduction/data/tasks/vh_homo_25.json"
    task = json.loads(task_file.read_text(encoding="utf-8"))[0]

    old = [a for ls in legacy_actions(task["objects"], task["action_space"])
           for a in ls]
    new = [a for ls in build_action_lists(task["objects"], task["action_space"])
           for a in ls]
    sig = lambda a: (a.name, frozenset(a.pre), frozenset(a.add),
                     frozenset(a.del_set), a.cost, a.duration)
    assert [sig(a) for a in old] == [sig(a) for a in new], "动作模型不一致"
    assert frozenset(legacy_start(task)) == frozenset(start_state(task)), \
        "初始状态不一致"

    cf_old, cf_new = legacy_conflict(2), make_conflict_fn(2)
    cases = [
        ["IsOpen(fridge)", "IsClose(fridge)"],
        ["IsNear(agent-0,milk)", "IsNear(agent-1,fridge)"],
        ["IsLeftHandEmpty(agent-0)", "IsLeftHolding(agent-0,milk)"],
        ["IsOpen(fridge)"],
    ]
    assert [cf_old(c) for c in cases] == [cf_new(c) for c in cases], \
        "冲突检测不一致"
    print(f"[OK ] 与 repro 域等价（{len(new)} 个 grounded 动作 / 初始状态 / 冲突检测）")


def check_end_to_end(num_agent: int = 2):
    import backends.virtualhome  # noqa: F401  触发注册
    from core.interfaces import make_backend
    from app.scenario import SCENARIOS
    from app.planner import plan_behavior_trees
    from app.executor import execute

    scenario = SCENARIOS["virtualhome"](num_agent=num_agent)
    backend = make_backend(scenario.backend, scene=scenario)
    check_protocol(backend)

    plan = plan_behavior_trees(backend, scenario, goal=scenario.goal)
    result = execute(backend, plan, max_steps=50)
    assert result.success, f"执行未达成目标（steps={result.steps}）"
    assert backend.goal <= backend.state, \
        f"目标谓词未全部成立：{sorted(backend.goal - backend.state)}"
    print(f"[OK ] {num_agent} agents：规划 {plan.planning_time:.3f}s / "
          f"展开 {plan.expanded_num} 节点，执行 {result.steps} 步达成目标")


def check_composite_macro():
    """宏子树端到端冒烟：CompositeActionPlanner + Fix* 接单节点 + 双 tick。"""
    import backends.virtualhome                     # noqa: F401
    from app.executor import execute
    from app.planner import plan_behavior_trees
    from app.scenario import Scenario
    from core.envs.domains.virtualhome.model import EXPANDABLE_ACTIONS
    from core.interfaces import make_backend

    actions = list(EXPANDABLE_ACTIONS)
    task = {
        "objects": ["milk", "fridge", "kitchentable", "tv"],
        "action_space": [actions, actions],
        "init_state": ["IsClose(fridge)"],
        "goal": ["IsIn(milk,fridge)"],
    }
    scenario = Scenario(
        name="vh-macro-check", env_id="symbolic://virtualhome", num_agent=2,
        balls=[], goal=frozenset(task["goal"]),
        composite_library=[
            {"PutMilkInFridge": [
                "Walk(self,milk)",
                "RightGrab(self,milk)",
                "Walk(self,fridge)",
                "Open(self,fridge)",
                "RightPutIn(self,milk,fridge)",
            ]},
            {},
        ],
        behavior_lib="virtualhome", backend="virtualhome",
        symbolic_task=task,
    )

    env = make_backend("virtualhome", scene=scenario)
    assert {"SelfAcceptTask", "FinishTask"} <= set(env.behavior_lib["Action"])
    assert "IsSelfTask" in env.behavior_lib["Condition"]
    plan = plan_behavior_trees(env, scenario, goal=scenario.goal)
    result = execute(env, plan, max_steps=60)
    assert result.success, f"宏子树未达成目标（steps={result.steps}）"
    assert env.goal <= env.state, "宏子树执行后目标谓词不全"
    print(f"[OK ] 宏子树（Fix* 接单节点 + 双 tick）{result.steps} 步达成目标")


def main() -> int:
    # 先跑主链路，最后才把 examples/ 加进 sys.path 做可选等价性比对，
    # 避免复现脚本的 import 影响规划器的模块解析。
    for n in (2, 4):
        check_end_to_end(n)
    check_composite_macro()
    check_model_equivalence()
    print("\nVirtualHome 符号后端自检全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
