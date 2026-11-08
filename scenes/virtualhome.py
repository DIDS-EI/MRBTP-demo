"""virtualhome —— VirtualHome / 家庭服务**符号**场景（纯数据声明）。

与 ``scenes/home_service.py`` 的区别：那个是 MiniGrid 网格上的「家庭服务」
配色 + 专属行为库；这个是论文 Table 2/3/4 用的 VirtualHome 域，世界只是一组
谓词，物体类别、13 个动作的 pre/add/del、互斥检测来自
``core/envs/domains/virtualhome``，由 ``backends/virtualhome`` 驱动。

任务刻意选 ``IsOpen(fridge)``：老版本 ``Walk`` 的 del_set 会清掉所有其它
``IsNear``，而 ``check_conflict`` 规定一个前提集合最多只能有一个 ``IsNear``；
「先抓取再走到别处」这类目标在没有 LLM 预规划子树时会被规划器判为冲突。
单目标 + 单个 IsNear 可以纯靠 MRBTP 回链，适合做主 app 的开箱冒烟场景。
需要跑论文那 75 个任务 / LLM 子树请用 ``examples/paper_reproduction/repro/``。

运行::

    python -m app.run --scenario virtualhome --renderer none --agents 2

该场景同时把 ``backend`` 和 ``behavior_lib`` 都指向 ``virtualhome``，所以
只写 ``--scenario virtualhome`` 就足够；``--backend`` / ``--domain`` 可覆盖。
"""
from __future__ import annotations

from app.scenario import Scenario
from core.envs.domains.virtualhome.model import DEFAULT_TASK, EXPANDABLE_ACTIONS

# CLI 上用的场景名。无 THEME：符号后端没有画面，不需要配色主题。
NAME = "virtualhome"


def make(num_agent: int = 2) -> Scenario:
    """造一个自包含的 VirtualHome 符号任务（按队伍规模复制动作空间）。"""
    space = [list(EXPANDABLE_ACTIONS) for _ in range(num_agent)]
    task = {
        "id": DEFAULT_TASK["id"],
        "objects": list(DEFAULT_TASK["objects"]),
        "action_space": space,
        "init_state": list(DEFAULT_TASK["init_state"]),
        "goal": list(DEFAULT_TASK["goal"]),
    }

    return Scenario(
        name=NAME,
        env_id="symbolic://virtualhome",   # 符号后端不会 gym.make，仅作标识
        num_agent=num_agent,
        balls=[],                          # 没有网格物体
        goal=frozenset(task["goal"]),
        composite_library=[],              # 不用 LLM 式宏子树
        behavior_lib="virtualhome",        # standalone 域，不叠加 MiniGrid 原语
        backend="virtualhome",
        symbolic_task=task,
    )
