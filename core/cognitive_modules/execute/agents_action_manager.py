# agents_action_manager.py
import json
import random

from tools.fileloader import fileLoader
from core.cognitive_modules.execute.action_handler import get_agent_location, get_action_object, get_action_tuple
from core.cognitive_modules.execute.actions_library import go_to_destination
from core.memory_structures.agents_memory_manager import MemoryService
from core.cognitive_modules.reaction.agent_react_manager import ReflectService
from core.cognitive_modules.execute.agents_chat_manager import ReaciToChat
from core.cognitive_modules.plan.plan import PlanManager
from tools.metaClass import Meta
from tools.global_methods import *
from schedule import schedule

with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    

class AgentsActionManager(metaclass=Meta):
    """
    管理单个 Agent 的行为执行。
    时间驱动逻辑由 global_timer.py 提供。
    """
    _schedule_cache = {}

    def __init__(self, name: str):
        self.name = name
        # 加载角色设定和记忆
        self.persona = fileLoader(config['AGENTS_PATH'][name]['prompt_path'])
        self.memory = MemoryService()
        self.reflect = ReflectService()
        self.isChatting = False
        self.should_react = False
        self.today_is_chatted = False
        self.isTalkingAbout = ""
        self.chat = []
        self.summary_chat = ""
        

        # 加载日常计划并预处理
        # self.daily_plan = PlanManager(self.persona, self).expanded_schedule
        
        with open(f"./schedule/{self.name}.json", "r", encoding='utf-8')as f:
            self.daily_plan = json.load(f)['schedule']
        # self.daily_plan = schedule
        self._build_schedule_cache()

        # 当前目标地点和坐标
        self.destination = None
        self.location = None
        
        self.schedule = {"schedule": self.daily_plan}
        with open(f"./schedule/{self.name}.json", "w", encoding='utf-8')as f:
            f.write(json.dumps(self.schedule, indent=1))
        print(self.daily_plan, file=open("./log/schedule_log01.txt", "a"))

    def get_instance(self, target_name):
        # 通过类属性访问其他实例
        return AgentsActionManager.instances.get(target_name)
    
    def _build_schedule_cache(self):
        """将 schedule 转换为时间区间后缓存"""
        total = 0
        intervals = []
        for activity, duration in self.daily_plan:
            intervals.append((total, total + duration, activity))
            total += duration
        assert total == 1440, f"{self.name} 日程总时长应为1440分钟，当前为{total}"
        self._schedule_cache[self.name] = intervals

    def get_current_activity(self, current_time: int) -> str:
        """
        返回指定游戏内时间的活动。
        :param current_time: 游戏内分钟数 0-1439
        """
        for start, end, activity in self._schedule_cache.get(self.name, []):
            if start <= current_time < end:
                return activity
        return None
    async def execute_behavior(self, bot_manager, current_time: int, global_events: list):
        """
        根据传入时间调用行为，优化事件处理逻辑
        :param bot_manager: 对应的 AsyncBotManager 实例
        :param current_time: 当前游戏内时间（分钟）
        """
        current_act = self.get_current_activity(current_time)
        print(f"[{self.name}] is {current_act}")
        hour = current_time // 60
        minute = current_time % 60
        clock = f"{hour:02d}:{minute:02d}"
        
        

        # 使用全局事件进行推理
        relevant_events = [e for e in global_events if self.name != e['subject']]
        
        event_processed = False
        new_events = []

        if relevant_events:
            selected_event = random.choice(relevant_events)
            
            # 睡眠事件特殊处理
            if selected_event['object'] == "sleep" or selected_event['description'] == "sleeping" or self.today_is_chatted == True:
                # 直接生成基础事件不触发反应
                subject, object = await get_action_object(self.name, current_act)
                subject, predicate, object = await get_action_tuple(self.name, current_act, subject, object)
                
                await self.memory.store_memory(
                    self.name, current_act, 
                    self.name, predicate, object
                )
                
                new_event = {
                    "subject": subject,
                    "object": object,
                    "description": f"{current_act}"
                }
                new_events.append(new_event)
                event_processed = True
            else:
                target_agent_name = selected_event['subject']
                target_agent = self.get_instance(target_agent_name)
                if target_agent is None:
                    print(f"[ERROR] Agent {target_agent_name} 未注册!")
                    return new_events
                
                # 确保 target_agent 有 name 属性
                if not hasattr(target_agent, 'name'):
                    print(f"[ERROR] Agent {target_agent} 属性不完整")
                    return new_events
                
                subject, object = await get_action_object(target_agent.name, selected_event['description'])
                subject, predicate, object = await get_action_tuple(target_agent.name, selected_event['description'], subject, object)
                
                await self.memory.store_memory(
                    self.name, selected_event['description'], 
                    subject, predicate, object
                )
                
                related_memories = self.memory.search_memory(target_agent.name)  
                if self.isChatting == False:
                    self.should_react = self.reflect.decide_to_reaction(
                        clock,
                        self,
                        current_action=current_act,
                        observed_event=selected_event,
                        target_persona=target_agent.name,
                        related_memories=related_memories
                    )
                    if self.should_react:
                        # 生成对话反应
                        self.isChatting = True
                        self.isTalkingAbout = self.reflect.get_is_talking_about(self, current_act, selected_event, target_agent.name, related_memories)
                        
                        chat = ReaciToChat().generate_dialogue(
                            clock, 
                            self, 
                            current_act,
                            target_agent_name, 
                            selected_event, 
                            self.isTalkingAbout,
                            self.chat,
                            related_memories
                        )
                        self.should_react = False
                        target_agent.isChatting = True
                        target_agent.should_react = True
                        target_agent.isTalkingAbout = self.isTalkingAbout
                        bot_manager.bot.chat(chat)
                        print(f"[{self.name}]: {chat}")
                        self.chat.append([self.name, chat])
                        target_agent.chat.append([self.name, chat])
                        current_act = f"{self.name} is talking to {target_agent_name} about {self.isTalkingAbout} said {chat}."
                        new_event = {
                            "subject": self.name,
                            "object": target_agent.name,
                            "description": f"{current_act}"
                        }
                        new_events.append(new_event)
                        event_processed = True
                else:
                    if len(self.chat) < 10 and self.should_react == True: # 轮到自己说话
                        chat = ReaciToChat().generate_dialogue(
                            clock, 
                            self, 
                            current_act,
                            target_agent_name, 
                            selected_event, 
                            self.isTalkingAbout,
                            self.chat,
                            related_memories
                        )
                        self.should_react = False
                        target_agent.isChatting = True
                        target_agent.should_react = True
                        bot_manager.bot.chat(chat)
                        print(f"[{self.name}]: {chat}")
                        self.chat.append([self.name, chat])
                        target_agent.chat.append([self.name, chat])
                        # 更新当前行为描述
                        current_act = f"{self.name} is talking to {target_agent_name} about {self.isTalkingAbout} said {chat}."
                        new_event = {
                            "subject": self.name,
                            "object": target_agent.name,
                            "description": f"{current_act}"
                        }
                        new_events.append(new_event)
                    elif len(self.chat) < 5 and self.should_react == False: # 未轮到自己说话
                        current_act = f"{self.name} is Listening to {target_agent_name} said about {self.isTalkingAbout}."
                        new_event = {
                            "subject": self.name,
                            "object": target_agent.name,
                            "description": f"{current_act}"
                        }
                        self.should_react = True
                        target_agent.should_react = False
                        new_events.append(new_event)
                    else: # 对话结束
                        self.isChatting = False
                        self.should_react = False
                        self.isTalkingAbout = ""
                        target_agent.isChatting = False
                        target_agent.should_react = False
                        target_agent.isTalkingAbout = ""
                        self.today_is_chatted = True
                        target_agent.today_is_chatted = True
                        
                        self.summary_chat = self.reflect.summarize_chat(self, self.chat, target_agent.name)
                        target_agent.summary_chat = self.summary_chat
                        
                        await self.memory.store_memory(
                            self.name, self.summary_chat, 
                            self.name, "Talks to", target_agent.name
                        )
                        await target_agent.memory.store_memory(
                            target_agent.name, self.summary_chat, 
                            target_agent.name, "Talks to", self.name
                        )
                        decide_to_alter_plan = self.reflect.decide_to_alter_plan(self, self.chat, self.summary_chat)
                        if decide_to_alter_plan:
                            self.persona = replace_persona_currently(self.persona, self.summary_chat)
                            self.daily_plan = PlanManager(self.persona, self).expanded_schedule
                            self._build_schedule_cache()
                            with open(f"./schedule/{self.name}.json", "w", encoding='utf-8')as f:
                                f.write(json.dumps(self.schedule, indent=1))
                        target_decide_to_alter_plan = target_agent.reflect.decide_to_alter_plan(target_agent, self.chat, self.summary_chat)
                        if target_decide_to_alter_plan:
                            target_agent.persona = replace_persona_currently(target_agent.persona, self.summary_chat)
                            target_agent.daily_plan = PlanManager(target_agent.persona, target_agent).expanded_schedule
                            target_agent._build_schedule_cache()
                            with open(f"./schedule/{target_agent.name}.json", "w", encoding='utf-8')as f:
                                f.write(json.dumps(target_agent.schedule, indent=1))
                        self.chat = []
                        target_agent.chat = []
                    event_processed = True

        # 统一处理事件存储与位置更新
        if not event_processed:
            subject, object = await get_action_object(self.name, current_act)
            subject, predicate, object = await get_action_tuple(
                self.name, current_act, subject, object
            )
            await self.memory.store_memory(
                self.name, current_act, 
                self.name, predicate, object
            )
            
            new_event = {
                "subject": subject,
                "object": object,
                "description": f"{current_act}"
            }
            new_events.append(new_event)

        # 位置更新逻辑
        new_dest, new_loc = await get_agent_location(
            self.name, self.destination, self.location, current_act
        )
        if new_dest != self.destination:
            self.destination = new_dest
            self.location = new_loc
            await go_to_destination(bot_manager, self.destination, self.location)

        return new_events

    # async def execute_behavior(self, bot_manager, current_time: int, global_events: list):
    #     """
    #     根据传入时间调用行为。
    #     :param bot_manager: 对应的 AsyncBotManager 实例
    #     :param current_time: 当前游戏内时间（分钟）
    #     """
    #     current_act = self.get_current_activity(current_time)
    #     print(f"[{self.name}] is {current_act}", file=open("./log/schedule_log01.txt", "a"))

    #     # 使用全局事件进行推理
    #     relevant_events = [e for e in global_events if self.name != e['subject']]
    #     if relevant_events:
    #         selected_event = random.choice(relevant_events)
    #         if selected_event['object'] == "sleep" or selected_event['description'] == "is sleeping":
    #             pass # 如果选择到的事件是睡觉则跳到父if的else
    #         target_persona=selected_event['subject']
    #         related_memories=self.memory.search_memory(selected_event['subject'])
    #         should_react = self.reflect.decide_to_reaction(
    #             self,
    #             current_action=current_act,
    #             observed_event=selected_event,
    #             target_persona=target_persona, 
    #             related_memories=related_memories
    #         )
    #         if should_react:
    #             chat = ReaciToChat().generate_dialogue(current_time, self, current_act, target_persona, selected_event, self.chat, related_memories)
    #             bot_manager.bot.chat(chat)
    #             print(f"[{self.name}]: {chat}", file=open("./log/schedule_log01.txt", "a"))
                
    #             self.chat.append([self.name, chat])
                
    #             current_act = f"{self.name} is talking to {target_persona} said {chat}."
    #             subject, object = await get_action_object(self.name, current_act)
    #             subject, predicate, object = await get_action_tuple(self.name, current_act, subject, object)
                
    #             new_event = {
    #                 "subject": subject,
    #                 "object": object,
    #                 "description": current_act
    #             }
                
    #             await self.memory.store_memory(self.name, current_act, self.name, predicate, object)
    #             return [new_event]
    #         else:
    #             subject, object = await get_action_object(self.name, current_act)
    #             subject, predicate, object = await get_action_tuple(self.name, current_act, subject, object)
    #             await self.memory.store_memory(self.name, current_act, self.name, predicate, object)
                
    #             # 生成新事件
    #             new_event = {
    #                 "subject": subject,
    #                 "object": object,
    #                 "description": f"{current_act}"
    #             }
    #             return [new_event]
    #     subject, object = await get_action_object(self.name, current_act)
    #     subject, predicate, object = await get_action_tuple(self.name, current_act, subject, object)
    #     await self.memory.store_memory(self.name, current_act, self.name, predicate, object)
        
    #     # 生成新事件
    #     new_event = {
    #         "subject": subject,
    #         "object": object,
    #         "description": f"{current_act}"
    #     }
    #     # 获取新目标地点与坐标
    #     new_dest, new_loc = await get_agent_location(
    #         self.name, self.destination, self.location, current_act
    #     )

    #     # 如目标更新，执行移动
    #     if new_dest != self.destination:
    #         self.destination = new_dest
    #         self.location = new_loc
    #         await go_to_destination(bot_manager, self.destination, self.location)
                
    #     return [new_event]