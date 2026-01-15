# global_timer.py
import asyncio
from mcrcon import MCRcon

from tools.global_methods import get_minecraft_time
from core.cognitive_modules.execute.agents_action_manager import AgentsActionManager


class GlobalTimer:
    """
    全局中枢计时器：每5分钟一跳，驱动所有 Agent 的行为执行。
    - 游戏时间从所有 Agent 最早起床时间前5分钟开始
    - 与 AsyncBotManager 一一对应。
    """
    def __init__(self, agent_names, bot_managers):
        assert len(agent_names) == len(bot_managers), \
            "agent_names 与 bot_managers 数量必须一致"
        self.bot_managers = bot_managers
        self.agents = [AgentsActionManager(name) for name in agent_names]
        
        # 计算初始时间 --------------------------------------------------
        # 获取所有 Agent 的起床时间（睡眠结束时间）
        wakeup_times = [
            agent.daily_plan[0][1]  # daily_plan[0] 是 ('sleeping', duration)
            for agent in self.agents
        ]
        earliest_wakeup = min(wakeup_times)
        # start_time = max(earliest_wakeup - 5, 0)  # 前5分钟且不低于0
        start_time = max(earliest_wakeup + 240, 0)
        # 游戏时间初始化为开始时间（模1440处理跨天）
        self.current_time = start_time % 1440
        
        self.global_events = []  # 全局事件表
        self.new_events_buffer = []  # 用于暂存新事件
        # print("已注册 Agents:", AgentsActionManager.instances.keys())

    async def start(self):
        print("++++++++++++++++++ Time Start ++++++++++++++++++")
        while True:
            hour = self.current_time // 60
            minute = self.current_time % 60
            minecraft_time = get_minecraft_time(self.current_time)
            print("-----------------------------------------------")
            print(f"[Time: {hour:02d}:{minute:02d}]")
            with MCRcon("127.0.0.1", "123456") as mcr:
                mcr.command(f"time set {minecraft_time}")
            # 并行执行所有 Agent 行为，并等待全部完成
            tasks = [
                agent.execute_behavior(
                    bot_manager, 
                    self.current_time,
                    list(self.global_events)  # 传递当前事件的副本
                )
                for agent, bot_manager in zip(self.agents, self.bot_managers)
            ]
            
            # 收集所有Agent生成的新事件
            agent_results = await asyncio.gather(*tasks)
            self.new_events_buffer = [event for sublist in agent_results for event in sublist]
            
            # 更新全局事件表
            await asyncio.sleep(5)
            self.global_events = self.new_events_buffer
            self.current_time = (self.current_time + 5) % 1440


# import asyncio
# from agents_action_manager import AgentsActionManager

# class GlobalTimer:
#     """
#     全局中枢计时器：每5分钟一跳，驱动所有 Agent 的行为执行。
#     与 AsyncBotManager 一一对应。
#     """
#     def __init__(self, agent_names, bot_managers):
#         assert len(agent_names) == len(bot_managers), \
#             "agent_names 与 bot_managers 数量必须一致"
#         self.current_time = 0  # 游戏内时间（分钟数，0-1439）
#         # 实例化所有 Agent 管理器
#         self.agents = [AgentsActionManager(name) for name in agent_names]
#         # 对应的 Bot 管理器列表
#         self.bot_managers = bot_managers

#     async def start(self):
#         while True:
#             hour = self.current_time // 60
#             minute = self.current_time % 60
#             print(f"\n游戏内时间: {hour:02d}:{minute:02d}")

#             # 并行执行所有 Agent 行为，并等待全部完成
#             tasks = [
#                 agent.execute_behavior(bot_manager, self.current_time)
#                 for agent, bot_manager in zip(self.agents, self.bot_managers)
#             ]
#             await asyncio.gather(*tasks)  # 并行执行并等待

#             # 等待真实时间1秒（模拟游戏内5分钟）
#             await asyncio.sleep(5)
#             self.current_time = (self.current_time + 5) % 1440

