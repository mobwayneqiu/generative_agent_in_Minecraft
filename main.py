# main.py
import asyncio
import json
from backend_server.minecraft_bot_manager import AsyncBotManager
from backend_server.global_timer import GlobalTimer

async def main():
    # 读取配置，获取所有 Agent 名称
    with open('./config/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    agent_names = config.get("AGENTS_NAME", [])

    # 初始化 Minecraft Bot 管理器
    # bot_manager = AsyncBotManager("Ethan Choi", loop=asyncio.get_event_loop())
    bot_manager = [AsyncBotManager(name, loop=asyncio.get_event_loop()) 
           for name in config["AGENTS_NAME"]]
    # 创建并启动全局计时器
    timer = GlobalTimer(agent_names, bot_manager)
    await timer.start()

if __name__ == "__main__":
    asyncio.run(main())


# import asyncio
# import json
# from minecraft_bot_manager import AsyncBotManager
# from agents_action_manager import AgentsActionManager

# with open('./config/config.json', 'r', encoding='utf-8') as f:
#     config = json.load(f)

# async def main():
#     # 启动全局计时器
#     timer_task = asyncio.create_task(AgentsActionManager.run_global_timer())
    
#     # 初始化所有机器人
#     # bots = [AsyncBotManager(name, loop=asyncio.get_event_loop()) 
#     #        for name in config["AGENTS_NAME"]]
#     bots = AsyncBotManager("Ethan Choi", loop=asyncio.get_event_loop())
    
#     # 启动行为循环
#     await asyncio.gather(
#         timer_task,
#         # *[bot.behavior_loop() for bot in bots]
#         bots.behavior_loop()
#     )

# if __name__ == "__main__":
#     asyncio.run(main())
