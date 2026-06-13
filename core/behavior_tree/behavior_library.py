import os
from core.utils import ROOT_PATH
import importlib.util
import copy
from core.behavior_tree.base_nodes import Action,Condition

def get_classes_from_folder(folder_path):
    cls_dict = {}
    for filename in os.listdir(folder_path):
        if filename.endswith('.py'):
            # 构建模块的完整路径
            module_path = os.path.join(folder_path, filename)
            # 获取模块名（不含.py扩展名）
            module_name = os.path.splitext(filename)[0]

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取模块中定义的所有类
            for name, obj in module.__dict__.items():
                if isinstance(obj, type):
                    cls_dict[module_name] = obj

    return cls_dict


class BehaviorLibrary(dict):
    def __init__(self, lib_path=None):
        super().__init__()
        if lib_path:
            self.load_from_btml(lib_path)

    def clone(self):
        return copy.deepcopy(self)

    def load_from_btml(self, lib_path):
        """Load Condition/Action node classes from one or more library roots.

        Args:
            lib_path: either a single library-root path (the historical
                behaviour) **or** an ordered iterable of paths.  When several
                paths are given they are loaded as an *overlay*: each later
                root is merged on top of the earlier ones, and a node whose
                class name collides with an already-loaded one overrides it.
                This is what lets a *domain* library (e.g. ``home_service`` /
                ``battlefield``) reuse the shared MiniGrid primitives by simply
                listing ``[minigrid_root, domain_root]`` — the domain folder
                only needs to ship its handful of new nodes, never copies of
                the grid primitives.

        A single string keeps the exact previous semantics, so every existing
        caller (and the byte-for-byte default behaviour) is preserved.
        """
        # Reset once, then merge every requested root into the same dicts.
        self['Action'] = {}
        self['Condition'] = {}

        if isinstance(lib_path, (str, bytes, os.PathLike)):
            paths = [lib_path]
        else:
            paths = list(lib_path)

        for root in paths:
            self._merge_root(root)

    def _merge_root(self, lib_path):
        """Merge a single library root's nodes into ``self`` (overlay-friendly)."""
        folder_list = os.listdir(lib_path)

        for folder_name in folder_list:
            path = os.path.join(lib_path, folder_name)
            if os.path.isfile(path):
                continue
            for name, cls in get_classes_from_folder(path).items():
                if issubclass(cls, Action):
                    self['Action'][name] = cls
                elif issubclass(cls, Condition):
                    self['Condition'][name] = cls
                else:
                    raise TypeError(name + ' is not Action or Condition.')

    def load_from_dict(self, lib_dict):
        for node_type, node_list in lib_dict.items():
            node_dict = {}
            for node in node_list:
                node_dict[node.__name__] = node
            self[node_type] = node_dict

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
