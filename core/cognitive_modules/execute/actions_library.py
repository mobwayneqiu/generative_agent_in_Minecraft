# action.py
import json
import asyncio
from javascript import require

pathfinder = require('mineflayer-pathfinder')
Vec3 = require("vec3").Vec3

with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
RANGE_GOAL = config.get("RANGE_GOAL")

async def act_reading(bot, destination):
    """
    bot 执行 "reading" 动作：根据 location 从配置中读取坐标，并控制 bot 移动到该位置。
    """
    bot.loadPlugin(pathfinder.pathfinder)
    location = config.get("LOCATION", {}).get(destination,{})
    print(f"📍 [{bot.username}] 正在前往 {destination} 读书")
    bot.pathfinder.setGoal(pathfinder.goals.GoalNear(location.get("x"), location.get("y"), location.get("z"), RANGE_GOAL))
    await asyncio.sleep(10)

async def go_to_destination(bot_manager, destination, location):
    """
    bot 执行 "go_to_destination" 动作：根据 location 坐标，控制 bot 移动到该位置。
    """
    bot_manager.bot.loadPlugin(pathfinder.pathfinder)
    movements = pathfinder.Movements(bot_manager.bot)
    bot_manager.bot.pathfinder.setMovements(movements)
    print(f"[{bot_manager.name}] 正在移动到 {destination} ，坐标 {location}")
    bot_manager.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(location[0], location[1], location[2], RANGE_GOAL))

async def act_follow(bot, name):
    """
    bot 执行 "follow" 动作：跟随目标（对象名称字符串）。
    """
    bot.loadPlugin(pathfinder.pathfinder)
    movements = pathfinder.Movements(bot)
    player = bot.players[name]
    target = player.entity
    pos = target.position
    bot.pathfinder.setMovements(movements)
    bot.pathfinder.setGoal(pathfinder.goals.GoalNear(pos.x, pos.y, pos.z, RANGE_GOAL))

    await asyncio.sleep(1)

async def act_stare(bot, name):
    player = bot.players[name]
    target = player.entity
    pos = target.position
    print(f"👀 [{bot.username}] 正在注视 {name}")
    bot.lookAt(pos.offset(0, 1.6, 0))

    await asyncio.sleep(1)

# 动作处理字典，将动作类型映射到对应函数
ACTION_HANDLERS = {
    "reading": act_reading,
    "follow": act_follow,
    "stare": act_stare,
}

async def execute_action(bot, action):
    """
    通用的动作执行接口
    
    参数:
      bot: 当前的 bot 对象
      action: 动作列表，例如 ["reading", "park"]、["follow", "Isabel"]、["stare", "Bob"]
    """
    if not (isinstance(action, list) and len(action) >= 2):
        print("⚠️ 无效的动作格式")
        return

    action_type = action[0]
    target = action[1]
    handler = ACTION_HANDLERS.get(action_type)
    if handler:
        # 在事件循环中异步调用动作函数
        await handler(bot, target)
    else:
        print(f"⚠️ 未知的动作类型: {action_type}")
