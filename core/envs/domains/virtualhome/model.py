"""VirtualHome / Home-Service 的 **纯符号 STRIPS 域**。

这是 ``examples/paper_reproduction/repro/domains.py`` 里 (b) Home Service /
VirtualHome 那一半动作的正式域版本：物体类别、13 个可展开动作的
``pre/add/del``、互斥条件检测、初始状态构造逐字节移植自重构前的
``mabtpg/envs/virtualhome/``（``tools.py``、``behavior_lib/Action/*.py``、
``envs/vh_computation_env.py``）。

与复现脚本的关系
-----------------
``repro/domains.py`` 保留自己的副本不动，以保证已归档的论文复现实验逐位可复现；
本模块是给**主应用**（``core/envs/domains`` 注册表 → ``backends/virtualhome``
→ ``app.run``）用的单一事实来源。两者的动作模型等价，可用
``python -m backends.virtualhome.check`` 做逐动作比对。

这里没有任何 Unity / 渲染 / gymnasium 依赖：世界就是一个谓词字符串集合。
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Set

# --------------------------------------------------------------------------- #
# 物体类别（逐字节移植 tools.py:get_classify_objects_dic）
# --------------------------------------------------------------------------- #
SURFACES = {"kitchentable", "towelrack", "bench", "kitchencabinet", "mousemat",
            "boardgame", "coffeetable", "fryingpan", "radio", "cuttingboard",
            "floor", "tvstand", "bathroomcounter", "oventray", "chair",
            "kitchencounter", "rug", "bookshelf", "nightstand", "cabinet",
            "desk", "stove", "bed", "sofa", "plate", "bathroomcabinet", "table"}

GRABBABLE = {"sundae", "toothpaste", "clothesshirt", "crackers", "pudding", "alcohol",
             "boardgame", "wallphone", "remotecontrol", "whippedcream", "hanger",
             "cutlets", "candybar", "wine", "toiletpaper", "slippers", "cereal", "apple",
             "magazine", "wineglass", "milk", "cupcake", "folder", "wallpictureframe",
             "cellphone", "coffeepot", "crayons", "box", "fryingpan", "radio", "chips",
             "cuttingboard", "lime", "mug", "rug", "carrot", "cutleryfork", "clothespile",
             "notes", "plum", "cookingpot", "toy", "salmon", "peach", "condimentbottle",
             "hairproduct", "salad", "mouse", "clock", "washingsponge", "bananas",
             "dishbowl", "oventray", "chocolatesyrup", "creamybuns", "pear", "chair",
             "condimentshaker", "bellpepper", "paper", "plate", "facecream", "breadslice",
             "candle", "towelrack", "pancake", "cutleryknife", "kitchenknife", "milkshake",
             "dishwashingliquid", "keyboard", "towel", "toothbrush", "book", "juice",
             "waterglass", "barsoap", "mincedmeat", "clothespants", "chicken",
             "poundcake", "pillow", "pie", "rag", "duster", "papertowel", "brush"}

CAN_OPEN = {"coffeemaker", "cookingpot", "toothpaste", "coffeepot", "kitchencabinet",
            "washingmachine", "window", "printer", "curtains", "closet", "box",
            "microwave", "hairproduct", "dishwasher", "radio", "fridge", "toilet", "book",
            "garbagecan", "magazine", "nightstand", "cabinet", "milk", "desk", "stove",
            "door", "folder", "clothespile", "bathroomcabinet", "oven"}

CONTAINERS = {"coffeemaker", "kitchencabinet", "washingmachine", "printer", "toaster",
              "closet", "box", "microwave", "dishwasher", "fryingpan", "fridge", "toilet",
              "garbagecan", "sink", "bookshelf", "nightstand", "cabinet", "stove",
              "folder", "clothespile", "bathroomcabinet", "oven", "cookingpot", "desk"}

HAS_SWITCH = {"coffeemaker", "cellphone", "candle", "faucet", "washingmachine", "printer",
              "wallphone", "remotecontrol", "computer", "toaster", "microwave",
              "dishwasher", "clock", "radio", "lightswitch", "fridge", "tablelamp",
              "stove", "tv", "oven"}

CATEGORIES: Dict[str, Set[str]] = {
    "SURFACES": SURFACES,
    "CAN_OPEN": CAN_OPEN,
    "CONTAINERS": CONTAINERS,
    "GRABBABLE": GRABBABLE,
    "HAS_SWITCH": HAS_SWITCH,
}

# 动作时长（逐字节移植各 Action.__init__ 的 act_max_step）。
# 符号后端默认把每个动作压成「一拍完成」；这些数值保留为上游语义元数据，
# 需要真实时长的实验可以读 ``VHAction.duration``。
VH_DURATION = {
    "Walk": 30, "Open": 10, "Close": 5,
    "RightGrab": 2, "LeftGrab": 2, "RightPut": 2, "LeftPut": 2,
    "RightPutIn": 2, "LeftPutIn": 2, "RightGrabFrom": 2, "LeftGrabFrom": 2,
    "SwitchOn": 2, "SwitchOff": 2,
}

#: 老版本 ``Env.create_action_model`` 只展开 can_be_expanded=True 的动作。
EXPANDABLE_ACTIONS = (
    "Walk", "Open", "Close",
    "RightGrab", "LeftGrab", "RightPut", "LeftPut",
    "RightPutIn", "LeftPutIn", "SwitchOn", "SwitchOff",
)


class VHAction:
    """规划器消费的 STRIPS 动作模型（字段与 ``PlanningAction`` 对齐）。

    ``name`` 同时是行为树节点的实例化名 ``Cls(args)``，例如
    ``Walk(agent-0,fridge)``；BTML 由 ``core.utils.parse_predicate_logic``
    拆成 ``("Walk", ("agent-0", "fridge"))``。
    """

    def __init__(self, name: str, pre: Iterable[str], add: Iterable[str],
                 del_set: Iterable[str], *, cost: float = 1,
                 duration: int = 1):
        self.name = name
        self.pre = frozenset(pre)
        self.add = frozenset(add)
        self.del_set = frozenset(del_set)
        self.cost = cost
        self.real_cost = cost
        self.priority = cost
        self.duration = duration
        # 兼容 ``PlanningAction`` 的历史字段（部分工具会读）
        self.vaild_num = 0
        self.vild_args = set()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return (f"VHAction({self.name!r}, pre={set(self.pre)!r}, "
                f"add={set(self.add)!r}, del={set(self.del_set)!r})")


def filter_objects_to_get_category(objects: Iterable[str]) -> Dict[str, Set[str]]:
    """VHCompEnv.filter_objects_to_get_category：按当前任务 objects 求类别交集。"""
    objs = set(objects)
    return {cat: (members & objs) for cat, members in CATEGORIES.items()}


def make_conflict_fn(num_agent: int):
    """VHCompEnv.check_conflict 的等价实现：互斥状态 → 条件不可同时成立。"""
    opposite = {
        "IsOpen": "IsClose", "IsClose": "IsOpen",
        "IsSwitchedOff": "IsSwitchedOn", "IsSwitchedOn": "IsSwitchedOff",
    }
    hand_opposite = {
        "IsLeftHandEmpty": "IsLeftHolding", "IsLeftHolding": "IsLeftHandEmpty",
        "IsRightHandEmpty": "IsRightHolding", "IsRightHolding": "IsRightHandEmpty",
    }

    def conflict(conds) -> bool:
        obj_state: Dict[str, Set[str]] = {}
        agent_state: Dict[str, Set[str]] = {
            f"agent-{i}": set() for i in range(num_agent)
        }
        is_near = False
        for c in conds:
            m = re.search(r"agent-\d+", c)
            aid = m.group() if m else None
            if "IsNear" in c:
                if is_near:
                    return True
                is_near = True
                continue
            for state, anti in opposite.items():
                if state in c:
                    arg = re.search(r"\((.*?)\)", c)
                    obj = arg.group(1) if arg else ""
                    if obj and obj in obj_state and anti in obj_state[obj]:
                        return True
                    obj_state.setdefault(obj, set()).add(state)
                    break
            if aid is not None:
                for state, anti in hand_opposite.items():
                    if state in c and anti in agent_state[aid]:
                        return True
                    if state in c:
                        agent_state[aid].add(state)
                        break
        return False

    return conflict


def build_action_lists(objects: Sequence[str],
                       action_space: Sequence[Sequence[str]]) -> List[List[VHAction]]:
    """按每个机器人的 action_space 生成 grounded 动作模型。

    与 ``repro.domains.build_vh_action_lists`` 逐动作等价（同样对物体集合
    ``sorted()``，避免 PYTHONHASHSEED 造成 grounded 顺序漂移）。
    """
    cat = filter_objects_to_get_category(objects)
    all_objs = sorted(set(objects))
    surfaces = sorted(cat["SURFACES"])
    grabbable = sorted(cat["GRABBABLE"])
    containers = sorted(cat["CONTAINERS"])
    can_open = sorted(cat["CAN_OPEN"])
    has_switch = sorted(cat["HAS_SWITCH"])

    out: List[List[VHAction]] = []
    for i, space in enumerate(action_space):
        aid = f"agent-{i}"
        acts: List[VHAction] = []
        for pred in space:
            if pred == "Walk":
                for obj in all_objs:
                    acts.append(VHAction(
                        name=f"Walk({aid},{obj})",
                        pre=frozenset(),
                        add=frozenset({f"IsNear({aid},{obj})"}),
                        del_set=frozenset(f"IsNear({aid},{p})" for p in all_objs if p != obj),
                        duration=VH_DURATION["Walk"],
                    ))
            elif pred in ("RightGrab", "LeftGrab"):
                side = "Right" if pred.startswith("Right") else "Left"
                for obj in grabbable:
                    acts.append(VHAction(
                        name=f"{pred}({aid},{obj})",
                        pre=frozenset({f"Is{side}HandEmpty({aid})", f"IsNear({aid},{obj})"}),
                        add=frozenset({f"Is{side}Holding({aid},{obj})",
                                       f"Is{side}HandFull({aid})"}),
                        del_set=(frozenset({f"Is{side}HandEmpty({aid})"})
                                 | frozenset(f"IsOn({obj},{p})" for p in surfaces)
                                 | frozenset(f"IsIn({obj},{p})" for p in containers)),
                        duration=VH_DURATION[pred],
                    ))
            elif pred in ("RightPut", "LeftPut"):
                side = "Right" if pred.startswith("Right") else "Left"
                for obj in grabbable:
                    for place in surfaces:
                        acts.append(VHAction(
                            name=f"{pred}({aid},{obj},{place})",
                            pre=frozenset({f"Is{side}Holding({aid},{obj})",
                                           f"IsNear({aid},{place})"}),
                            add=frozenset({f"Is{side}HandEmpty({aid})",
                                           f"IsOn({obj},{place})"}),
                            del_set=frozenset({f"Is{side}Holding({aid},{obj})",
                                               f"Is{side}HandFull({aid})"}),
                            duration=VH_DURATION[pred],
                        ))
            elif pred in ("RightPutIn", "LeftPutIn"):
                side = "Right" if pred.startswith("Right") else "Left"
                for obj in grabbable:
                    for place in containers:
                        pre = {f"Is{side}Holding({aid},{obj})", f"IsNear({aid},{place})"}
                        if place in can_open:
                            pre.add(f"IsOpen({place})")
                        acts.append(VHAction(
                            name=f"{pred}({aid},{obj},{place})",
                            pre=frozenset(pre),
                            add=frozenset({f"Is{side}HandEmpty({aid})",
                                           f"IsIn({obj},{place})"}),
                            del_set=frozenset({f"Is{side}Holding({aid},{obj})",
                                               f"Is{side}HandFull({aid})"}),
                            duration=VH_DURATION[pred],
                        ))
            elif pred == "Open":
                for obj in can_open:
                    acts.append(VHAction(
                        name=f"Open({aid},{obj})",
                        pre=frozenset({f"IsClose({obj})", f"IsNear({aid},{obj})",
                                       f"IsLeftHandEmpty({aid})"}),
                        add=frozenset({f"IsOpen({obj})"}),
                        del_set=frozenset({f"IsClose({obj})"}),
                        duration=VH_DURATION["Open"],
                    ))
            elif pred == "Close":
                for obj in can_open:
                    acts.append(VHAction(
                        name=f"Close({aid},{obj})",
                        pre=frozenset({f"IsOpen({obj})", f"IsNear({aid},{obj})",
                                       f"IsLeftHandEmpty({aid})"}),
                        add=frozenset({f"IsClose({obj})"}),
                        del_set=frozenset({f"IsOpen({obj})"}),
                        duration=VH_DURATION["Close"],
                    ))
            elif pred in ("SwitchOn", "SwitchOff"):
                on = pred == "SwitchOn"
                cur, nxt = (("IsSwitchedOff", "IsSwitchedOn") if on
                            else ("IsSwitchedOn", "IsSwitchedOff"))
                for obj in has_switch:
                    acts.append(VHAction(
                        name=f"{pred}({aid},{obj})",
                        pre=frozenset({f"IsLeftHandEmpty({aid})", f"IsNear({aid},{obj})",
                                       f"{cur}({obj})"}),
                        add=frozenset({f"{nxt}({obj})"}),
                        del_set=frozenset({f"{cur}({obj})"}),
                        duration=VH_DURATION[pred],
                    ))
            # Grab/Put/PutIn/*GrabFrom 的通用版本 can_be_expanded=False，忽略
        out.append(acts)
    return out


def normalize_action_space(action_space: Sequence[Sequence[str]],
                           num_agent: int) -> List[List[str]]:
    """把任务的 action_space 拉伸 / 截断到 CLI 指定的机器人数量。"""
    space = [list(s) for s in action_space]
    if not space:
        space = [list(EXPANDABLE_ACTIONS)]
    if len(space) < num_agent:
        space = space + [list(space[-1]) for _ in range(num_agent - len(space))]
    return space[:num_agent]


def start_state(task: dict, num_agent: int | None = None) -> frozenset:
    """02_load_json_evaluate.py:103-119：init_state + 每个 agent 左右手为空。"""
    n = num_agent if num_agent is not None else len(task["action_space"])
    state = set(task["init_state"])
    for i in range(n):
        state.add(f"IsRightHandEmpty(agent-{i})")
        state.add(f"IsLeftHandEmpty(agent-{i})")
    return frozenset(state)


def goal_state(task: dict) -> frozenset:
    """任务的目标谓词集合。"""
    return frozenset(task["goal"])


#: 主应用自带的、开箱即可规划的 VirtualHome 任务。
#:
#: 选 ``IsOpen(fridge)`` 而不是 ``IsIn(milk,fridge)`` 是刻意的：老版本
#: ``Walk`` 的 del_set 会清掉所有其它 ``IsNear``，而 ``check_conflict`` 规定
#: 一个前提集合里最多只能有一个 ``IsNear``；因此「先抓取再走到别处」这类
#: 目标在没有 LLM 预规划子树时会被规划器判为冲突（论文靠子树规避）。
#: 单目标 + 单个 IsNear 的任务可以纯靠 MRBTP 回链，适合做主 app 的冒烟场景。
DEFAULT_TASK: dict = {
    "id": "vh_default_open_fridge",
    "objects": ["milk", "fridge", "kitchentable", "tv"],
    "action_space": [list(EXPANDABLE_ACTIONS)],
    "init_state": ["IsClose(fridge)", "IsSwitchedOff(tv)"],
    "goal": ["IsOpen(fridge)"],
}
