from __future__ import annotations

import random
import io
import re
import itertools
import numpy as np
from core.envs.gridenv.minigrid.magrid_env import MiniGridMAGridEnv
from core.envs.gridenv.minigrid.magrid import MiniGridMAGrid


from minigrid.core.mission import MissionSpace
from minigrid.minigrid_env import MiniGridEnv
from minigrid.envs.babyai.core.verifier import GoToInstr, PickupInstr

from core import BehaviorLibrary

from core.envs.gridenv.minigrid.utils import obj_to_planning_name
from typing import Any, SupportsFloat
from gymnasium.core import ActType, ObsType
from core.envs.gridenv.minigrid.objects import CAN_GOTO,CAN_PICKUP,CAN_TOGGLE

# Quick start. Run this in console: python -m minigrid.manual_control --env BabyAI-BossLevelNoUnlock-v0

def default_behavior_lib_path() -> str:
    """Absolute path of the built-in MiniGrid behavior library.

    This is the historical, hard-coded location.  It is now exposed as a
    helper so (a) the env can fall back to it when no scene-specific library
    is injected, and (b) scene libraries can ``import`` these primitives and
    only add a few domain-specific nodes on top.
    """
    from core.utils import get_root_path
    return f"{get_root_path()}/envs/gridenv/minigrid/behavior_lib"


def gen_mission_func(env):
    def _gen_mission():
        return env.mission
    return _gen_mission


class MiniGridToMAGridEnv(MiniGridMAGridEnv):
    def __init__(
        self,
        minigrid_env: MiniGridEnv,
        num_agent: int = 1,
        behavior_lib_path: str | None = None,
        **kwargs
    ):
        # Which behavior library (Condition/Action node folder) this env's
        # agents plan with.  ``None`` falls back to the built-in MiniGrid
        # library, so the historical behaviour is preserved byte-for-byte.
        # A scenario can inject a *scene-specific* library (e.g. the home /
        # battle domains under ``core/envs/domains/``) by passing an absolute
        # path here; see ``Scenario.behavior_lib_path`` and ``build_env``.
        self.behavior_lib_path = behavior_lib_path or default_behavior_lib_path()

        self.width = minigrid_env.width
        self.height = minigrid_env.height

        minigrid_env.reset()
        self.minigrid_env = minigrid_env

        self.actions_lists = None


        # self.instrs = minigrid_env.instrs
        self.instrs = getattr(minigrid_env, 'instrs', None)


        mission_space = MissionSpace(mission_func=gen_mission_func(minigrid_env))

        super().__init__(mission_space=mission_space,
                         num_agent = num_agent,
                         # Pass width/height separately instead of a single
                         # ``grid_size`` so NON-SQUARE layouts (e.g. the
                         # self-built scene maps in scenes/) keep their
                         # real height.  Using ``grid_size=width`` forced the
                         # env to a WxW square, leaving self.height wrong (15
                         # instead of 7) while self.grid was the true 15x7 ->
                         # the pygame renderer then ran j past the grid and
                         # hit ``assert 0 <= j < self.height``.
                         width = minigrid_env.width,
                         height = minigrid_env.height,

                         tile_size=minigrid_env.tile_size,
                         render_mode=None,
                         agent_view_size=minigrid_env.agent_view_size,
                         screen_size=minigrid_env.screen_size,

                         **kwargs)
        self.render_mode = "human"
        self.create_behavior_libs()

        # Assign cells to rooms
        self.room_cells,self.cells_room = self.assign_cells_to_rooms()
        self.action_list = None

        self.obj_type_num = None
        self.id2obj = None
        self.obj_name2id = None
        self.obj_id2name=None

        # Initialize a dictionary to map doors to their corresponding keys
        self.door_key_map = None
        self.key_door_map = None


        ## need to put in after reset()
        # self.get_objects_lists()
        # self.adj_rooms_doors = self.get_adjacent_rooms_and_doors()

        # ---- Domain fluent store (additive; grid primitives never touch it) --
        # A set of *symbolic* predicate strings that are NOT derivable from the
        # grid geometry — e.g. ``IsClean(ball-0)`` or ``IsSecured(room-1)``.
        # Domain Condition nodes (under ``core/envs/domains/<d>/behavior_lib``)
        # read this set; domain Action nodes flip a fluent on/off once the agent
        # has physically reached the relevant cell on the grid.  This is the
        # seam that lets the SAME plan run abstractly on the grid today and on a
        # robot simulator later (the simulator backend just maintains the same
        # fluent contract from real sensor/actuator state).  ``None`` until the
        # first reset so a fresh world always starts from a clean slate.
        self.domain_state: set | None = None

        self.verbose=False

    def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, Any] | None = None,
    ) -> tuple[ObsType, dict[str, Any]]:
        super().reset(seed=seed, options=options)

        self.get_objects_lists()
        # self.adj_rooms_doors = self.get_adjacent_rooms_and_doors()

        # Each episode starts from a clean fluent slate; the scenario seeds the
        # domain-specific initial fluents (e.g. which balls start dirty) right
        # after the final reset in ``Scenario.build_env`` via ``seed_domain_state``.
        self.domain_state = set()


    def assign_cells_to_rooms(self):
        """
        Assign walkable positions to different rooms in the MiniGridEnv environment.

        Returns:
            dict: A dictionary where keys are room indices and values are lists of walkable cell positions.
        """
        width, height = self.minigrid_env.grid.width, self.minigrid_env.grid.height
        visited = set()
        room_cells = {}

        def dfs(x, y, room_index):
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited:
                    continue
                visited.add((cx, cy))
                if room_index not in room_cells:
                    room_cells[room_index] = []
                room_cells[room_index].append((cx, cy))
                for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                    if 0 <= nx < width and 0 <= ny < height:
                        if (nx, ny) in visited: continue
                        cell = self.minigrid_env.grid.get(nx, ny)
                        if cell is None:
                            stack.append((nx, ny))
                        elif cell.type != "wall" and cell.type != "door":
                            stack.append((nx, ny))

        room_index = 0
        for i in range(width):
            for j in range(height):
                cell = self.minigrid_env.grid.get(i, j)
                if (i,j) in visited: continue
                if cell is None:
                    dfs(i, j, room_index)
                    room_index += 1
                elif cell.type != "wall" and cell.type != "door":
                    dfs(i, j, room_index)
                    room_index += 1

        cells_room = {}
        for room_index, cells in room_cells.items():
            for cell in cells:
                cells_room[cell] = room_index

        return room_cells,cells_room


    def get_room_index(self, pos):
        """
        Given a position (i, j), return the room index.

        Args:
            i (int): The x-coordinate of the position.
            j (int): The y-coordinate of the position.

        Returns:
            int: The index of the room that the position belongs to, or -1 if the position is not walkable.
        """
        # i,j = pos
        # for room_index, cells in self.room_cells.items():
        #     if (i, j) in cells:
        #         return room_index
        if isinstance(pos, np.ndarray):
            pos = tuple(pos.tolist())
        if pos in self.cells_room:
            return self.cells_room[pos]
        return -1

    # ------------------------------------------------------------------ #
    # Domain fluent helpers (additive; used only by domain behavior libs)  #
    # ------------------------------------------------------------------ #
    def has_fluent(self, predicate: str) -> bool:
        """Return whether a symbolic domain fluent currently holds.

        Domain Condition nodes call this to evaluate predicates that are not
        derivable from grid geometry (``IsClean``, ``IsSecured`` ...).  Returns
        ``False`` before the first reset so evaluation is always safe.
        """
        return bool(self.domain_state) and predicate in self.domain_state

    def set_fluent(self, predicate: str, value: bool = True) -> None:
        """Add (``value=True``) or remove (``value=False``) a domain fluent.

        Domain Action nodes call this once the agent has physically reached the
        target cell on the grid, so the symbolic world state stays in lock-step
        with the geometric one.  A simulator backend would maintain the same
        fluent contract from real sensor / actuator readings.
        """
        if self.domain_state is None:
            self.domain_state = set()
        if value:
            self.domain_state.add(predicate)
        else:
            self.domain_state.discard(predicate)

    def place_object_in_room(self, obj, room_index):
        """
        Place an object in a random position in the specified room.

        Args:
            room_index (int): The index of the room.
            obj (WorldObj): The object to place.

        Returns:
            tuple: The position where the object was placed, or None if no valid position was found.
        """
        if room_index not in self.room_cells:
            raise ValueError(f"Room index {room_index} does not exist.")

        room_positions = self.room_cells[room_index]
        random.shuffle(room_positions)

        for pos in room_positions:
            x, y = pos
            cell = self.minigrid_env.grid.get(x, y)
            if cell is None:
                self.minigrid_env.grid.set(x, y, obj)
                obj.cur_pos = (x, y)
                return (x, y)

        return None

    def place_object_x_y(self, obj, x,y):
        """
        Place an object in a random position in the specified room.

        Args:
            room_index (int): The index of the room.
            obj (WorldObj): The object to place.

        Returns:
            tuple: The position where the object was placed, or None if no valid position was found.
        """

        cell = self.minigrid_env.grid.get(x, y)
        if cell is None:
            self.minigrid_env.grid.set(x, y, obj)
            obj.cur_pos = (x, y)
            return (x, y)

        return None

    def initialize_objects_name_id(self):
        # Initialize dictionaries for counting object types and mapping names to IDs
        self.obj_type_num = {}
        self.id2obj = {}
        self.obj_name2id = {}
        self.obj_id2name={}

        # Initialize a dictionary to map doors to their corresponding keys
        self.door_key_map = {}
        self.key_door_map = {}
        # Temporary storage for locked doors and keys
        locked_doors = {}
        keys = {}

        # Assign IDs and count object types
        for obj in self.obj_list:
            # Add a private 'id' attribute to each object in the list if it doesn't already have one
            if not hasattr(obj, 'id') or obj.id is None:
                if obj.type not in self.obj_type_num:
                    self.obj_type_num[obj.type] = 0
                obj.id = f"{obj.type}-{self.obj_type_num[obj.type]}"
                self.obj_type_num[obj.type] += 1

            self.id2obj[obj.id] = obj
            obj.name = obj_to_planning_name(obj)
            self.obj_name2id[obj.name] = obj.id

            # Record locked doors and keys
            if obj.type == 'door' and obj.is_locked:
                locked_doors[obj.id] = obj.color
            elif obj.type == 'key':
                keys[obj.color] = obj.id
                # if obj.color not in keys:
                #     keys[obj.color] = []
                # keys[obj.color].append(obj.id)


        # Bind locked doors to their corresponding keys
        for door_id, door_color in locked_doors.items():
            if door_color in keys:
                self.door_key_map[door_id] = keys[door_color]
        self.key_door_map = {key_id: door_id for door_id, key_id in self.door_key_map.items()}

        # for door_id, door_color in locked_doors.items():
        #     if door_color in keys:
        #         if door_id not in self.door_key_map:
        #             self.door_key_map[door_id] = []
        #         self.door_key_map[door_id].append(keys[door_color])
        #
        #         key_id_ls  = keys[door_color]
        #         for key_id in key_id_ls:
        #             self.key_door_map[key_id]=door_id


        self.obj_id2name = {id_: name for name, id_ in self.obj_name2id.items()}


    def get_adjacent_rooms_and_doors(self):
        """
        Get all adjacent rooms and their connecting doors.

        Returns:
            list: A list of tuples (from_room_id, to_room_id, door_id).
        """
        doors_to_adj_rooms = {}
        adj_rooms_to_doors = {}
        door_positions = []

        for obj in self.obj_list:
            if obj.type == 'door':
                door_positions.append((obj.cur_pos[0], obj.cur_pos[1], obj.id))

        width, height = self.minigrid_env.grid.width, self.minigrid_env.grid.height
        for (i, j, door_id) in door_positions:
            adjacent_rooms = set()
            for nx, ny in [(i+1, j), (i-1, j), (i, j+1), (i, j-1)]:
                if 0 <= nx < width and 0 <= ny < height:
                    for room_id, positions in self.room_cells.items():
                        if (nx, ny) in positions:
                            adjacent_rooms.add(room_id)
            if len(adjacent_rooms) == 2:
                from_room_id, to_room_id = tuple(adjacent_rooms)
                doors_to_adj_rooms[door_id] = (from_room_id, to_room_id)
                adj_rooms_to_doors[(from_room_id, to_room_id)] = door_id

        return doors_to_adj_rooms,adj_rooms_to_doors


    def _gen_grid(self, width, height):
        # self.minigrid_env._gen_grid(self.width, self.height)

        for i in range(self.num_agent):
            self.agents[i].position = self.minigrid_env.agent_pos
            self.agents[i].direction = self.minigrid_env.agent_dir

        self.agent_pos = self.minigrid_env.agent_pos
        self.agent_dir = self.minigrid_env.agent_dir
        self.grid = self.minigrid_env.grid
        # self.grid.render = MAGrid(self.width, self.height).render.__get__(self.grid, Grid)

        self.grid.render = lambda *args,**kwargs: MiniGridMAGrid.render(self.grid,*args,**kwargs)
        # self.grid = MAGridEnv()


    def get_goal(self):

        if self.instrs==None:
            return None

        name = f"{self.instrs.desc.color}_{self.instrs.desc.type}"
        x, y = self.instrs.desc.obj_set[0].cur_pos
        planning_name = f"{name}-{x}_{y}"

        # Check if the planning name exists in the name-to-ID mapping
        if planning_name in self.obj_name2id:
            obj_id = self.obj_name2id[planning_name]
        else:
            # If not found, assign a default ID using the type from instruction's descriptor with suffix '0'
            obj_id = str(self.instrs.desc.type) + "-0"

        if isinstance(self.instrs, GoToInstr):
            return {f"IsNear(agent-0,{obj_id})", }
        if isinstance(self.instrs, PickupInstr):
            return {f"IsHolding(agent-0,{obj_id})"}

    def create_behavior_libs(self):
        # Load the behavior library this env was configured with (scene-specific
        # if a scenario injected one, otherwise the built-in MiniGrid library).
        behavior_lib = BehaviorLibrary(self.behavior_lib_path)
        for agent in self.agents:
            agent.behavior_lib = behavior_lib

    def get_objects_lists(self):
        obj_list = []
        self.cache = {}
        # list all Objects in env
        for i in range(self.grid.width):
            for j in range(self.grid.height):
                cell = self.grid.get(i, j)
                if cell is None:
                    continue

                if cell.type != "wall":
                    if cell.cur_pos == None:
                        cell.cur_pos = (i,j)
                    obj_list.append(cell)

        print("\n" + "-" * 10 + " Objects in the env " + "-" * 10)
        for obj in obj_list:
            # if obj.cur_pos==None:
            #     print(obj.type)
            # else:
            print(obj.type,obj.cur_pos[0],obj.cur_pos[1])

        self.obj_list = obj_list

        # Initialize dictionaries for counting object types and mapping names to IDs
        self.initialize_objects_name_id()

        self.doors_to_adj_rooms,self.adj_rooms_to_doors = self.get_adjacent_rooms_and_doors()
        # obj cache
        can_goto, can_pickup, can_toggle = self.initialize_cache()

    def initialize_object_list(self, key, valid_types):
        """
        Initialize and cache a list of objects of specified types in the environment.
        """
        if key not in self.cache:
            self.cache[key] = [obj.id for obj in self.obj_list if obj.type in valid_types]
        return self.cache[key]

    def initialize_cache(self):
        """
        Utilize the generic helper function to initialize all relevant object lists.
        """
        can_goto = self.initialize_object_list("can_goto", CAN_GOTO)
        can_pickup = self.initialize_object_list("can_pickup", CAN_PICKUP)
        can_toggle = self.initialize_object_list("can_toggle", CAN_TOGGLE)
        return can_goto, can_pickup, can_toggle

    def get_initial_state(self):
        agent = self.agents[0]

        states_ls = set()
        for act_ls in self.action_model:
            for act in act_ls:
                states_ls |= act.pre
                states_ls |= act.add
                states_ls |= act.del_set
        # Determine one by one if the current state is satisfied.

        import copy
        from core.utils.any_tree_node import AnyTreeNode
        from core.behavior_tree.constants import NODE_TYPE
        from core.behavior_tree import BTML
        from core.behavior_tree.behavior_tree import BehaviorTree
        from core.behavior_tree import Status
        from core.utils import parse_predicate_logic

        # Use the SAME behavior library the agents plan with, so the condition
        # classes that evaluate the initial state match the action model.
        behavior_lib = BehaviorLibrary(self.behavior_lib_path)
        start = copy.deepcopy(states_ls)
        for state in states_ls:

            cls_name, args = parse_predicate_logic(state)
            condition_node = behavior_lib["Condition"][cls_name](*args)
            condition_node.bind_agent(agent)
            status = condition_node.update()
            if status == Status.FAILURE:
                start -= {state}
        return start


    def get_map(self):
        width, height = self.minigrid_env.grid.width, self.minigrid_env.grid.height
        cell_width = 10   # Set the width of each cell
        map_string = io.StringIO()  # Use StringIO to construct the string

        # Determine the positions of agents
        pos2angent_dic={}
        for agent in self.agents:
            pos = agent.position
            if not isinstance(pos, tuple):  # Check if pos is not a tuple
                raise TypeError("The variable 'pos' must be of type tuple")
            if pos in pos2angent_dic:
                pos2angent_dic[pos].append(str(agent.id))
            else:
                pos2angent_dic[pos] = [(str(agent.id))]


        for j in range(height):
            for i in range(width):
                cell = self.minigrid_env.grid.get(i, j)
                pos = (i,j)
                if pos in pos2angent_dic:
                    pos = (i, j)
                    agents_str = "agent-"+','.join(pos2angent_dic[pos])
                    map_string.write(f"{agents_str:<{cell_width}}")
                    continue
                if cell is None:
                    map_string.write(f"{' . ':<{cell_width}}")
                elif cell.type == "wall":
                    map_string.write(f"{' WALL ':<{cell_width}}")
                    # map_string.write(f"{' # ':<{cell_width}}")
                else:
                    map_string.write(f"{cell.id:<{cell_width}}")
            map_string.write("\n")  # Add newline character

        map_str = map_string.getvalue()  # Get the complete string
        map_string.close()  # Close the StringIO object
        return map_str

    def check_conflict(self, premise_condition):
        near_state_dic = {}
        holding_state_dic = {}
        empty_hand_dic = {}
        room_state_dic = {}
        toggle_state_dic = {}

        for c in premise_condition:
            # Detect IsNear() patterns
            match_near = re.search(r'IsNear\(([^)]+)\)', c)
            if match_near:
                content = match_near.group(1)
                elements = content.split(',')
                agent_id = elements[0].strip()
                obj_id = elements[1].strip()
                if agent_id in near_state_dic:
                    if near_state_dic[agent_id] != obj_id:
                        if self.verbose:
                            print(
                                f"Conflict detected: {agent_id} is near more than one object: {near_state_dic[agent_id]} and {obj_id}.")
                        return True
                else:
                    near_state_dic[agent_id] = obj_id

            # Detect IsHolding() patterns
            match_holding = re.search(r'IsHolding\(([^)]+)\)', c)
            if match_holding:
                content = match_holding.group(1)
                elements = content.split(',')
                agent_id = elements[0].strip()
                obj_id = elements[1].strip()
                if agent_id in holding_state_dic:
                    if holding_state_dic[agent_id] != obj_id:
                        if self.verbose:
                            print(
                                f"Conflict detected: {agent_id} is holding more than one object: {holding_state_dic[agent_id]} and {obj_id}.")
                        return True
                elif agent_id in empty_hand_dic:
                    if self.verbose:
                        print(
                            f"Conflict detected: {agent_id} is reported both holding {obj_id} and having an empty hand.")
                    return True
                else:
                    holding_state_dic[agent_id] = obj_id

            # Detect IsHandEmpty() patterns
            match_empty = re.search(r'IsHandEmpty\(([^)]+)\)', c)
            if match_empty:
                agent_id = match_empty.group(1).strip()
                if agent_id in holding_state_dic:
                    if self.verbose:
                        print(
                            f"Conflict detected: {agent_id} is reported both having an empty hand and holding {holding_state_dic[agent_id]}.")
                    return True
                empty_hand_dic[agent_id] = True

            # Detect IsInRoom() patterns
            match_room = re.search(r'IsInRoom\(([^,]+),(\d+)\)', c)
            if match_room:
                entity_id = match_room.group(1).strip()
                room_id = match_room.group(2).strip()
                if entity_id in room_state_dic:
                    if room_state_dic[entity_id] != room_id:
                        if self.verbose:
                            print(
                                f"Conflict detected: {entity_id} is reported in more than one room: {room_state_dic[entity_id]} and {room_id}.")
                        return True
                else:
                    room_state_dic[entity_id] = room_id

            # IsOpen() and IsClose() must not both hold for the same object
            # Detect IsOpen() / IsClose() patterns
            match_open = re.search(r'IsOpen\(([^)]+)\)', c)
            match_close = re.search(r'IsClose\(([^)]+)\)', c)

            if match_open:
                obj_id = match_open.group(1).strip()
                if obj_id in toggle_state_dic and toggle_state_dic[obj_id] == 'close':
                    if self.verbose:
                        print(f"Conflict detected: {obj_id} is reported both open and close.")
                    return True
                toggle_state_dic[obj_id] = 'open'
            if match_close:
                obj_id = match_close.group(1).strip()
                if obj_id in toggle_state_dic and toggle_state_dic[obj_id] == 'open':
                    if self.verbose:
                        print(f"Conflict detected: {obj_id} is reported both open and close.")
                    return True
                toggle_state_dic[obj_id] = 'close'

        return False