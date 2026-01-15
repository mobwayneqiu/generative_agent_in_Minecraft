import json
import re

from tools.global_methods import find_contained_keyword
from backend_server.LLM_chater import DialogueManager
from tools.global_methods import ActionObjectExtractor, ActionTupleExtractor
object_extractor = ActionObjectExtractor()
tuple_extractor = ActionTupleExtractor()
llm = DialogueManager()

with open("./config/map.json", "r") as f:
    world_points = json.load(f)

destinations = []
locations = []
for destination, location in world_points.get('location'):
    destinations.append(destination)
    locations.append(location)

async def _get_location_prompt(name, old_destination, curr_action):
    prompt = (
            f"Output: [destination]\n"
            f"Here's the latest destination of this agent: {old_destination}.\n"
            f"current action: {curr_action}\n\n"
            f"You should output one of the list of the destineations:{destinations}\n"
            f"You should output like such example:\n"
            f"Output: [cafe]\n"
            f"Output {name}'s current location without any discribtion.\n"
            "Output:\n"
        )
    return prompt

async def get_agent_location(name, old_destination, old_location, curr_action):
    prompt = await _get_location_prompt(name, old_destination, curr_action)
    response = await llm.run_prompt(name, prompt)
    print(prompt, file=open("./log/prompt_log.txt", "a"))
    print(response, file=open("./log/prompt_log.txt", "a"))
    new_destination = find_contained_keyword(response, destinations, case_sensitive=False)
    new_location = []
    for destination, location in world_points.get("location"):
        if destination == new_destination:
            new_location = location
            break
    if new_destination is not None and new_location is not None:
        return new_destination, new_location
    else:
        return old_destination, old_location
    
    
async def _get_object_prompt(name, curr_act):
    prompt = (
        f"Task: Turn the input into (subject, object).\n"
        f"Here's the example output for each input:\n"
        f"---\n"
        f"Input: Sam Johnson is eating breakfast.\n"
        f"Output: (Sam Johnson, breakfast)\n"
        f"---\n"
        f"Input: Dolores Murphy is playing tennis.\n"
        f"Output: (Dolores Murphy, tennis)\n"
        f"---\n"
        f"Input: Joon Park is brewing coffee.\n"
        f"Output: (Joon Park, coffee)\n"
        f"---\n"
        f"Input: Jane Cook is sleeping.\n"
        f"Output: (Jane Cook, sleep)\n"
        f"---\n"
        f"Input: Michael Bernstein is writing email on a computer.\n"
        f"Output: (Michael Bernstein, email)\n"
        f"---\n"
        f"Input: Percy Liang is teaching students in a classroom.\n"
        f"Output: (Percy Liang, students)\n"
        f"---\n"
        f"Input: Merrie Morris is running on a treadmill.\n"
        f"Output: (Merrie Morris, treadmill)\n"
        f"---\n"
        f"Now output {name}'s current action into (subject, object), any part of output should not be None."
        f"Input: {name} is {curr_act}"
        f"Output: ({name},"
    )
    return prompt

async def get_action_object(name, curr_act):
    prompt = await _get_object_prompt(name, curr_act)
    response = await llm.run_prompt(name, prompt)
    subject, object = object_extractor.extract_subject_object(response)
    return subject, object

async def _get_tuple_prompt(name, curr_act, subject, object):
    prompt = (
        f"Task: Turn the input into (subject, predicate, object).\n"
        f"Here's the example output for each input:\n"
        f"---\n"
        f"Input: Sam Johnson is eating breakfast. (Dolores Murphy, breakfast)\n"
        f"Output: (Dolores Murphy, eat, breakfast)\n"
        f"---\n"
        f"Input: Joon Park is brewing coffee. (Joon Park, coffee)\n"
        f"Output: (Joon Park, brew, coffee)\n"
        f"---\n"
        f"Input: Michael Bernstein is writing email on a computer. (Michael Bernstein, email)\n"
        f"Output: (Michael Bernstein, write, email)\n"
        f"---\n"
        f"Input: Percy Liang is teaching students in a classroom. (Percy Liang, students)\n"
        f"Output: (Percy Liang, teach, students)\n"
        f"---\n"
        f"Input: Merrie Morris is running on a treadmill. (Merrie Morris, treadmill)\n"
        f"Output: (Merrie Morris, run, treadmill)\n"
        f"---\n"
        f"Input: Jane Cook is sleeping. (Jane Cook, sleep)\n"
        f"Output: (Jane Cook, is, sleep)\n"
        f"---\n"
        f"Now output {name}'s current action into (subject, predicate, object), any part of output should not be None."
        f"Input: {name} is {curr_act}. ({subject}, {object})\n"
        f"Output: ({name},"
    )
    return prompt

async def get_action_tuple(name, curr_act, subject, object):
    prompt = await _get_tuple_prompt(name, curr_act, subject, object)
    response = await llm.run_prompt(name, prompt)
    subject, predicate, object = tuple_extractor.get_action_tuple(response)
    return subject, predicate, object
    