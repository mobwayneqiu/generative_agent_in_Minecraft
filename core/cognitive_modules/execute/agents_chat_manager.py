from datetime import datetime # type: ignore
from dis import Instruction
from tkinter import dialog
from typing import Dict, Any # type: ignore
import re

from ollama import chat

from backend_server.LLM_chater import LLMResponse

manager = LLMResponse()
model_name = "ASSISTANT"
your_name = "USER"

# class GenerativeAgent:

system_prompt: str = (
    "A chat between a curious user and an artificial intelligence assistant. The assistant "
    "gives helpful, detailed, and polite answers to the user's questions.\n"
    "###USER: %s\n"
    "###ASSISTANT: ")

def chain(self, prompt):
    return

async def _get_entity_from_observation(self, observation: str) -> str:

    instruction = (
        f"Extract the entity from the following observation without explanation. Return a Subject name( e.g. Bob )\n"
        f"Observation: {observation}\n"
    )
    prompt = system_prompt % instruction
    print(prompt)
    a =  await manager.generate_response("assistant", your_name, prompt)
    print(a)
    return a

async def _get_entity_action(self, observation: str, entity_name: str) -> str:
    instruction = (
        f"In {self.name}'s eye. What is the {entity_name} doing in the following observation? Describe in 20 words. \n"
        f"Observation: {observation}\n"
    )
    prompt = system_prompt % instruction
    print(prompt)
    a = await manager.generate_response("assistant", your_name, prompt)
    print(a)
    return a

async def summarize_related_memories(self, observation: str) -> str:
    """Summarize memories that are most relevant to an observation."""
    prompt = (
         "{q1}?\n"
        "Context from memory:\n"
        "{relevant_memories}\n"
        "Relevant context:\n"
        "{q2}?\n"
    )
    entity_name = await _get_entity_from_observation(self, observation)
    entity_action = await _get_entity_action(self, observation, entity_name)
    q1 = f"What is the relationship between {self.name} and {entity_name}? Describe in 20 words."
    q2 = f"{entity_action}"
    a = await manager.generate_response("assistant", your_name, prompt
                                        .replace("{q1}",q1)
                                        .replace("{q2}",q2)
                                        .replace("{relevant_memories}", self.memory))
    print(a)
    return a
    
# 被动说话
async def summarize_speaker_memories(self, speaker: str, observation: str) -> str:
    instruction = (
        f"what is the most possible relationship between {self.name} and {speaker} in the"
        f" following observation? Describe in 20 words. Do not embellish if you don't know. Do not return a list.\n"
        "Observation: {relevant_memories}\n"
    )
    prompt = system_prompt % instruction

    a = await manager.generate_response("assistant", your_name, prompt
                                           .replace("{observation}", observation)
                                           .replace("{relevant_memories}", await summarize_related_memories(self, observation)))
    print(a)
    return a

async def _compute_agent_summary(self) -> str:
    instruction = (
        f"Summarize {self.name}'s core characteristics given the following input. Do not "
        f"embellish if you don't know. Do not return a list. Describe in 20 words. \n"
        "Input: {agent_summary}\n"
        "{relevant_memories}"
    )
    prompt = system_prompt % instruction

    # The agent seeks to think about their core characteristics.
    a = await manager.generate_response("assistant", your_name, prompt
                                        .replace("{agent_summary}", self.prompt)
                                        .replace("{relevant_memories}", self.memory))
    print(a)
    return a

async def _generate_dialogue_reaction(self, speaker: str, observation: str, call_to_action_template: str):
    """React to a given observation or dialogue act."""
    summary = (
        "{agent_summary_description}"
        + "\nIt is {current_time}."
        + "\n{agent_name}'s status: {agent_status}"
        + "\nSummary of relevant context from {agent_name}'s memory:"
        + "\n{relevant_memories}"
        + "\nMost recent observations: {most_recent_memories}"
        + "\n{agent_name}'s Observation: {observation}"
        + "\n\n"
    )
    agent_summary_description = await _compute_agent_summary(self)
    relevant_memories_str = await summarize_speaker_memories(self, speaker, observation)
    current_time_str = datetime.now().strftime("%B %d, %Y, %I:%M %p")
    kwargs: Dict[str, Any] = dict(
        agent_summary_description=agent_summary_description,
        current_time=current_time_str,
        relevant_memories=relevant_memories_str,
        most_recent_memories=self.status,
        agent_name=self.name,
        observation= speaker + " said " + observation + self.event,
        agent_status=self.status,
    )
    prompt = summary.format(**kwargs) + call_to_action_template
    print("prompt:\n",prompt)
    dialogue = await manager.generate_response("assistant", your_name, prompt)
    print(dialogue)
    return dialogue, summary



async def generate_dialogue(self, speaker: str, observation: str):
    """React to a given observation."""
    call_to_action_template = (
        "What would {agent_name} say? To end the conversation, write without explaination in 20 words:"
        ' GOODBYE: "what to say". Otherwise to continue the conversation,'
        ' write without explaination in 20 words: SAY: "what to say next"\n\n'
    )
    dialogue, environment = await _generate_dialogue_reaction(
        self,
        speaker,
        observation,
        call_to_action_template.replace("{agent_name}", self.name)
    )
    action = await generate_action(self, environment, dialogue)
    
    result = dialogue.strip().split("\n")[0]
    
    if "GOODBYE:" in result:
        farewell = result.split("GOODBYE:")[-1]
        save_memory = (
            f"{self.name} observed "
            f"{observation} and said {farewell}\n"
        )
        with open(self.memory_path, 'a', encoding='utf-8') as f:
                f.write("\n"+save_memory)
        
        # self.memory.save_context(
        #     {},
        #     {
        #         self.memory.add_memory_key: f"{self.name} observed "
        #                                     f"{observation} and said {farewell}"
        #     },
        # )
        return False, f"{self.name} said {farewell}", action
    if "SAY:" in result:
        response_text = result.split("SAY:")[-1]
        save_memory = (
            f"{self.name} observed "
            f"{observation} and said {response_text}"
        )
        with open(self.memory_path, 'a', encoding='utf-8') as f:
                f.write("\n"+save_memory)
        # self.memory.save_context(
        #     {},
        #     {
        #         self.memory.add_memory_key: f"{self.name} observed "
        #                                     f"{observation} and said {response_text}"
        #     },
        # )
        return True, f"{self.name} said {response_text}", action
    else:
        return False, result, ""
    
async def generate_action(self, environment, dialogue):
    instruction = (
        f"{environment}"
        f"{self.name} said {dialogue}\n"
        f"What is {self.name}'s action ? Output without any EXPLAINTION in 20 words: "
        "<subject> <Predicate> <Object>"
    )
    action = await manager.generate_response("assistant", your_name, instruction)
    print(action)
    return action

def get_speaker_relationship(self_agent_name: str, other_agent_name: str, obervation: str, relevent_memories: str):
    instruction = (
        f"what is the most possible relationship between {self_agent_name} and {other_agent_name} in the"
        f" following observation? Describe in 20 words. Do not embellish if you don't know. Do not return a list.\n"
        f"Observation: {obervation}\n"
        f"Relevant memories: {relevent_memories}\n"
    )
    prompt = system_prompt % instruction
    return manager.run_prompt(prompt)

class ReaciToChat:
    def _get_dialogue_prompt(self,
                        curr_time,
                        agent,
                        self_agent_status: str, 
                        other_agent_name: str, 
                        observation: str,
                        chat_topic: str, 
                        chat_history,
                        relevant_memories: str):
        self.relationship = get_speaker_relationship(agent.name, other_agent_name, observation, relevant_memories)
        if chat_history:
            chat_history = chat_history[-4:]
        instuction = (
            f"{agent.persona}\n"
            f"It is {curr_time}.\n"
            f"{agent.name}'s status: {self_agent_status}\n"
            f"Summary of relevant context from {agent.name}'s memory:\n"
            f"{relevant_memories}\n"
            f"{agent.name}'s Observation: {observation}\n"
            f"{agent.name} wants to talk with {other_agent_name} about {chat_topic}.\n"
        )
        if len(chat_history) > 0:
            instuction += f"{agent.name} and {other_agent_name}'s chat history:\n{chat_history}\n"
            instuction +=f"What would {agent.name} respond to {other_agent_name}? Output without explaination in 20 words:\n{agent.name} said:\n"
        else:
            instuction += f"and now.{agent.name} haven't talked to {other_agent_name} yet.\n"
            instuction +=f"What would {agent.name} say hello to {other_agent_name}? Output without explaination in 20 words:\n{agent.name} said:\n"
        return instuction
    
    def generate_dialogue(self, 
                          curr_time, 
                          agent, 
                          self_agent_status: str, 
                          other_agent_name: str, 
                          observation: str, 
                          chat_topic: str, 
                          chat_history, 
                          relevant_memories: str):
        def _clean_up(s: str)-> str:
            """
            如果字符串 s 中包含两个双引号(")，则返回第一个和第二个双引号之间的内容；
            否则返回原字符串 s。
            """
            # 查找第一个匹配的双引号对
            match = re.search(r'"([^"]*)"', s)
            if match:
                return match.group(1)
            else:
                return s
        prompt = system_prompt % self._get_dialogue_prompt(curr_time, agent, self_agent_status, other_agent_name, observation, chat_topic, chat_history, relevant_memories)
        print(prompt, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        result = manager.run_prompt(prompt)
        print(result, file=open("./log/prompt_log01.txt", "a", encoding="utf-8"))
        dialogue = _clean_up(result)
        return dialogue