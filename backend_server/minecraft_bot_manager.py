# minecraft_bot_manager.py
import asyncio
import json
from javascript import require, On

from core.cognitive_modules.execute.agents_action_manager import AgentsActionManager

# 读取配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# DEFAULT_name = config.get().get("DEFAULT_name")
DEFAULT_HOST = config.get("CONNECT_CONFIG").get("DEFAULT_HOST")
DEFAULT_PORT = config.get("CONNECT_CONFIG").get("DEFAULT_PORT")
RANGE_GOAL = config.get("CONNECT_CONFIG").get("RANGE_GOAL")
mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
# mineflayerViewer = require('prismarine-viewer').mineflayer

class AsyncBotManager:
    all_bots = []
    current_turn_index = 0
    condition = asyncio.Condition()

    def __init__(self, name, host=DEFAULT_HOST, port=DEFAULT_PORT, 
                 loop=None):
        self.name = name
        self.host = host
        self.port = port
        self.loop = loop or asyncio.get_event_loop()
        self.bot = mineflayer.createBot({
            'host': self.host,
            'port': self.port,
            'username': self.name.split(" ")[0]
        })
        self.entity = None
        self._init_bot()
        AsyncBotManager.all_bots.append(self)

    def _init_bot(self):
        self.bot.entity = require("prismarine-entity")('1.8.9')
        self.bot.loadPlugin(pathfinder.pathfinder)
        On(self.bot, 'spawn')(lambda *args: self.handle_spawn(*args))
        # On(self.bot, 'end')(lambda *args: self.handle_end(*args))

    def handle_spawn(self, *args):
        print(f"机器人 {self.name} 已生成 👋")
        self.bot.movements = pathfinder.Movements(self.bot)
        # mineflayerViewer(self.bot, { "port": 3000 })
        
    async def behavior_loop(self):
        """行为执行主循环"""
        agent = AgentsActionManager(self.name)
        while True:
            await agent.execute_behavior(self)
            await asyncio.sleep(1)  # 防止过度占用CPU

    def handle_end(self, *args):
        print(f"❌ 机器人 {self.name} 已离线")
        self.loop.call_soon_threadsafe(self.loop.stop)