"""scenes/ —— 后端无关的场景数据声明。

一个场景 = 房间布局 + 物体清单 + 任务目标（用现有谓词拼）。本包里的每个
模块只要导出两样东西，就会被 :mod:`app.scenario` 自动发现并注册进
``SCENARIOS``，无需改任何注册表：

    NAME              -- CLI 上用的场景名（字符串）
    make(num_agent)   -- 返回一个 app.scenario.Scenario 实例的工厂

加新场景 = 复制一份现成模块改数据，丢进本目录即可（详见 README.md）。
"""
