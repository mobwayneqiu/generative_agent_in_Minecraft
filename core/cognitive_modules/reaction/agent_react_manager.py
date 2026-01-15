from gettext import find
from typing import Dict, List # type: ignore
import random
from backend_server.LLM_chater import LLMResponse
from tools.global_methods import find_yes_no
llm = LLMResponse()

class ReflectService:
    def __init__(self):
        pass
    
    def _get_decide_reaction_prompt(self, curr_time, agent, current_action: str, observed_event: Dict, target_persona: str, related_memories):
        """决策是否响应事件的方法"""
        prompt = (
            f"{agent.persona}\n"
            f"It's {curr_time}\n"
            f"In {agent.name}'s eyes, {target_persona} is {observed_event['description']}\n"
            f"The {agent.name}'s memories about {target_persona}: \n"
            f"{related_memories}\n"
            f"And now, {agent.name} is {current_action}.\n"
            f"Question:\n"
            f"Decide whether the current scene justifies speaking. Speaking is a rare interaction that should only occur when there is strong motivation. If the scene meets all of the criteria below, output exactly Yes. Otherwise, output exactly No. Do not output anything else.\n"
            f"[Motivation Threshold for Speaking] (all must be satisfied):\n"
            f"1. There is a clear external trigger (e.g., a direct question from the user, an urgent warning, or a major plot twist).\n"
            f"2. The agent’s internal goals or needs **urgently** require a verbal response (e.g., to unlock essential information, resolve a critical conflict, or correct a key misunderstanding)."
            f"3. Speaking would significantly alter subsequent decisions or meaningfully advance the task; if not, silence is preferable."
            f"Is it necessary for {agent.name} to start a conversation with {target_persona}?\n"
            f"Your task:\n"
            f"If any of the above conditions is not met, output No\n"
            f"Responses must be exactly “Yes” or “No” (case-sensitive), with no additional words, punctuation, or explanation.\n"
        )
        return prompt
    
    def decide_to_reaction(self, curr_time, agent, current_action: str, observed_event: Dict, target_persona: str, related_memories) -> bool:
                # 调用LLM（假设有异步调用接口）
        prompt = self._get_decide_reaction_prompt(curr_time, agent, current_action, observed_event, target_persona, related_memories)
        print(prompt, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        response = llm.run_prompt(prompt)
        print(response, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        return find_yes_no(response)
    
    def _get_summarize_chat_prompt(self, agent, chat_history, target_persona):
        prompt = (
            f"Output example: Sam and Tom talked about their meeting on Monday at 10:00 am. They both went to the gym.\n"
            f"{agent.persona}\n"
            f"Task: Summarize the conversation of {agent.name} with {target_persona}:\n"
            f"{chat_history}\n"
            f"Output: {agent.name} and {target_persona} talked about ...\n"
        )
        return prompt
    
    def summarize_chat(self, agent, chat_history, target_persona) -> str:
        prompt = self._get_summarize_chat_prompt(agent, chat_history, target_persona)
        print(prompt, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        response = llm.run_prompt(prompt)
        print(response, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        summary_chat = response
        return summary_chat
    
    def _get_decide_alter_plan_prompt(self, agent, chat_history, summary_chat):
        prompt = (
            f"{agent.persona}\n"
            f"Here's the {agent.name}'s daily plan yet. A plan represents its schedule and the minutes it takes, starting at 0:00 on a day:\n"
            f"{agent.daily_plan}\n"
            f"Chat history:\n"
            f"{chat_history}\n"
            f"Summary of a conversation:\n"
            f"{summary_chat}\n"
            f"Decide weather to change the {agent.name}'s plan based on the conversation, the content of the conversation needs to be motivated enough to change\n"
            f"If {agent.name} need to change the plan, output 'Yes'. Otherwise, output 'No'. Do not output anything else.\n"
        )
        return prompt
    
    def decide_to_alter_plan(self, agent, chat_history, summary_chat) -> bool:
        prompt = self._get_decide_alter_plan_prompt(agent, chat_history, summary_chat)
        print(prompt, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        response = llm.run_prompt(prompt)
        print(response, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        print(response)
        return find_yes_no(response)
    
    # def _get_alter_plan_prompt(self, agent, summary_chat):
    #     prompt = (
    #         f"Here's the {agent.name}'s daily plan. A plan represents its schedule and the minutes it takes, starting at 0:00 on a day:\n"
    #         f"{agent.daily_plan}\n"
    #         f"Here's the summary of the conversation:\n"
    #         f"{summary_chat}\n"
    #         f"Task: Refer to the summary conversation to make minimal changes to this plan:\n"
    #         f"Output: {agent.daily_plan[0]}"
    #     )
    #     return prompt
    
    def _get_is_talking_about_prompt(self, agent, current_action: str, observed_event: Dict, target_persona: str, related_memories):
        prompt = (
            f"{agent.persona}\n"
            f"In {agent.name}'s eyes, {observed_event['description']}\n"
            f"The {agent.name}'s memories about {target_persona}: \n"
            f"{related_memories}\n"
            f"And now, {agent.name} is {current_action}.\n"
            f"Question:"
            f"{agent.name} want to talk to {target_persona}. What would they talk about? Output the topic.\n"
            f"Your task: Output the topic of the conversation. If the content contains time, the time needs to be emphasized\n"
            f"Output:\n"
        )
        return prompt
    
    def get_is_talking_about(self, agent, current_action: str, observed_event: Dict, target_persona: str, related_memories) -> str:
        prompt = self._get_is_talking_about_prompt(agent, current_action, observed_event, target_persona, related_memories)
        response = llm.run_prompt(prompt)
        topic = response.strip(":")[1]
        return topic