from datetime import datetime # type: ignore
import ast # type: ignore
import re # type: ignore

from tools.global_methods import *
from backend_server.LLM_chater import LLMResponse
llm = LLMResponse()

class PlanManager:
    def __init__(self, persona: str, agent):
        cur_date = datetime.now().strftime("%A %B %d")
        self.wake_up_hour = self.generate_wake_up_hour(persona)
        print(self.wake_up_hour)
        self.daily_plan = self.generate_first_daily_plan(agent, persona, self.wake_up_hour)
        print(self.daily_plan)
        self.hourly_schedule = self.generate_hourly_schedule(persona, self.wake_up_hour, self.daily_plan)
        print(self.hourly_schedule)
        self.expanded_schedule = self.generate_task_details(persona, self.hourly_schedule, cur_date)
        for i, task in enumerate(self.expanded_schedule):
            print(f"[{i}, {task}]\n")
        
    def _get_wake_up_hour_prompt(self, persona, lifestyle, firstname, cur_date):
        prompt = (
            f"{persona}\n"
            f"Current Date: {cur_date}\n\n"
            f"In general, {lifestyle}\n"
            f"output {firstname}'s wake up hour with a single number:"
        )
        return prompt

    def generate_wake_up_hour(self, persona):
        """ INPUT: persona
            OUTPUT: wake_up_hour: int
        """
        firstname = get_persona_firstname(persona)
        lifestyle = get_persona_lifestyle(persona)
        cur_date = datetime.now().strftime("%A %B %d")
        prompt = self._get_wake_up_hour_prompt(persona, lifestyle, firstname,cur_date)
        response = llm.run_prompt(prompt)
        match = re.search(r"\d+", response)
        wake_up_hour = int(match.group()) if match else None
        return wake_up_hour
        
    def _get_daily_plan_prompt(self, agent, persona, lifestyle, firstname, cur_date, wake_up_hour):
        prompt = (
            f"{persona}\n"
            f"Current Date: {cur_date}\n\n"
            f"In general, {lifestyle}\n"
        )
        if len(agent.summary_chat) > 0:
            prompt += f"Currently, {agent.summary_chat}\n"
        prompt += (
            f"Today is {cur_date}, Here is {firstname}'s plan today in broad-strokes (with the time of the day. e.g., ['wake up and complete the morning routine at 8:00 am', 'open the cafe at 8:00 am', 'work at the cafe counter until 8 pm', 'close the cafe at 8 pm', 'have dinner at 8:30 pm', 'watch TV from 7 to 8 pm', 'do some cleaning up or prepare for the Valentine's Day party']): ['wake up and complete the morning routine at {get_hour_from_int(wake_up_hour)}', '...', Return in a list and WITHOUT EXPLAINATION. "
        )
        return prompt

    def generate_first_daily_plan(self, agent, persona, wake_up_hour):
        firstname = get_persona_firstname(persona)
        lifestyle = get_persona_lifestyle(persona)
        cur_date = datetime.now().strftime("%A %B %d")
        prompt = self._get_daily_plan_prompt(agent, persona, lifestyle, firstname, cur_date, wake_up_hour)
        response = llm.run_prompt(prompt)
        # match = re.search(r"\[.*?\]", response)
        # if match:
        #     daily_plan = ast.literal_eval(match.group())
        # else:
        #     daily_plan = []
        items = re.findall(r"'([^']*)'", response)
        daily_plan = [item.strip() for item in items if item.strip()]
        return daily_plan

    def _init_hourly_schedule_prompt(self, persona, cur_date, hour_str):
        hourly_schedule_format = "Hourly schedule format:\n"
        for hour in hour_str:
            hourly_schedule_format += f"[{cur_date} -- {hour}] Activiity: [Fiil in]\n"
        hourly_schedule_format += "===\n"
        prompt = (
            f"{hourly_schedule_format}\n"
            f"{persona}\n"
            f"Current Date: {cur_date}\n\n"
        )
        return prompt

    def generate_hourly_schedule(self, persona, wake_up_hour, daily_plan):
        """ INPUT: persona
            OUTPUT: hourly_schedule: list of strings
        """
        hour_str = ["00:00 AM", "01:00 AM", "02:00 AM", "03:00 AM", "04:00 AM", 
                "05:00 AM", "06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM", 
                "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", 
                "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM",
                "08:00 PM", "09:00 PM", "10:00 PM", "11:00 PM"]
        cur_date = datetime.now().strftime("%A %B %d")
        activity = []
        diversity_repeat_count = 3
        for i in range(diversity_repeat_count):
            activity_set = set(activity)
            if len(activity_set) < 5:
                activity = []
                for count, curr_hour_str in enumerate(hour_str):
                    if wake_up_hour > 0:
                        activity += ['sleeping']
                        wake_up_hour -= 1
                    else:
                        activity.append(self.run_llm_prompt_generate_hourly_schedule(persona, daily_plan, cur_date, curr_hour_str, activity, hour_str))
        
        # 压缩日程
        hourly_compressed = []
        prev = None
        prev_count = 0
        for act in activity:
            if act != prev:
                prev_count = 1
                hourly_compressed += [[act, prev_count]]
                prev = act
            else:
                if hourly_compressed:
                    hourly_compressed[-1][1] += 1
        
        # 转换分钟制
        minute_compressed = []
        for act, hour in hourly_compressed:
            minute_compressed += [[act, hour*60]]
        
        return minute_compressed
        
    def run_llm_prompt_generate_hourly_schedule(self,
                                                persona, 
                                                daily_plan, 
                                                cur_date, 
                                                curr_hour_str, 
                                                activity, 
                                                hour_str):
        prompt = self._init_hourly_schedule_prompt(persona, cur_date, hour_str)
        def create_prompt_input(persona,
                                daily_plan,
                                curr_hour_str,
                                activity,
                                hour_str):
            # schedule_format = ""
            # for hour in hour_str:
            #     schedule_format += f"[{cur_date} -- {hour}] Activiity: [Fiil in]\n"
            intermission_str = f"Here the originally intended hourly breakdown of"
            intermission_str += f" {get_persona_firstname(persona)}'s schedule today: "
            for count, plan in enumerate(daily_plan):
                intermission_str += f"{str(count+1)}) {plan}, "
            intermission_str += "\n"
            
            prior_schedule = ""
            if activity:
                prior_schedule += "\n"
                for count, act in enumerate(activity):
                    prior_schedule += f"[{cur_date} -- {hour_str[count]}] Activity:"
                    prior_schedule += f" {get_persona_firstname(persona)}"
                    prior_schedule += f" is {act}\n"
            
            prompt_ending = f"[{cur_date} -- {curr_hour_str}] Activity:"
            prompt_ending += f" {get_persona_firstname(persona)} is"
            
            prompt_input = ""
            prompt_input += prompt
            prompt_input += prior_schedule
            prompt_input += intermission_str
            prompt_input += f"What would {get_persona_firstname(persona)} do in {curr_hour_str}? Output without explainationin 8 words. Don't format the output and don't output the updated schedule \n"
            prompt_input += prompt_ending
            
            print(prompt_input)
            return prompt_input
        
        prompt_input = create_prompt_input(persona, daily_plan, curr_hour_str, activity, hour_str)
        response = llm.run_prompt(prompt_input)
        hourly_act = response.strip().split(".")[0]
        return response

    # def _get_schedule_details_prompt(persona, hourly_schedule, cur_date):
        
        

    def _get_schedule_details_prompt(self, persona, hourly_schedule, index, cur_date):
        with open("./template/schedule_details_template.txt", "r", encoding='utf-8') as f:
            template = f.read()
        prompt = (
            f"Describe subtasks in 5 min increments, here is the output example. \n"
            f"{template}\n"
            f"And here is your task: \n"
            f"{persona}\n"
            f"Current Date: {cur_date}\n\n"
            f"Today is {cur_date},  "
        )
        previous_item = hourly_schedule[index - 1] if index > 0 else None
        current_item = hourly_schedule[index]
        next_item = hourly_schedule[index + 1] if index < len(hourly_schedule) - 1 else None
        
        schedule_description = ""
        start_time = sum(duration for _, duration in hourly_schedule[:index])  # 计算 index 之前的总时间

        # 获取前一项、当前项、后一项
        previous_item = hourly_schedule[index - 1] if index > 0 else None
        current_item = hourly_schedule[index]
        next_item = hourly_schedule[index + 1] if index < len(hourly_schedule) - 1 else None

        def format_schedule(start, duration, task):
            """格式化时间段"""
            end = start + duration
            h1, m1 = divmod(start, 60)
            h2, m2 = divmod(end, 60)
            p1, p2 = ("AM" if h1 < 12 else "PM"), ("AM" if h2 < 12 else "PM")
            segment = f"{h1 % 12}:{m1:02d}{p1} ~ {h2 % 12}:{m2:02d}{p2}"
            return f"From {segment}, {get_persona_firstname(persona)} is planning on {task.lower()}.", segment

        # 生成描述列表
        descriptions = []
        if previous_item:
            desc = format_schedule(start_time - previous_item[1], previous_item[1], previous_item[0])[0]
            descriptions.append(desc)
        desc, schedule_time = format_schedule(start_time, current_item[1], current_item[0])
        descriptions.append(desc)
        if next_item and index < len(hourly_schedule) - 1:
            desc = format_schedule(start_time + current_item[1], next_item[1], next_item[0])[0]
            descriptions.append(desc)

        # 拼接最终描述
        schedule_description = " ".join(descriptions)
        
        prompt_task = f"In 5 min increments, list the subtasks {get_persona_firstname(persona)} does when {get_persona_firstname(persona)} is {hourly_schedule[index][0]} from {schedule_time} (total duration in minutes {hourly_schedule[index][1]}), strictly follow the example output given."
        prompt += schedule_description
        prompt += prompt_task
        
        return prompt
        
        
    def generate_task_details(self, persona, hourly_schedule, cur_date):
        def _clean_up(text):     
            # 提取子任务条目
            pattern = r"\d+\)\s*(.+?)\s*\(duration in minutes:\s*(\d+)"
            entries = [[task, int(duration)] for task, duration in re.findall(pattern, text)]
            return entries
        
        def _verify_duration(tasks, total_duration):
            """验证总时间是否合理"""
            tasks = list(tasks)
            for task in tasks:
                total_duration -= task[1]
            last_task = list(tasks[-1])  # Convert tuple to list
            last_task[1] += total_duration
            tasks[-1] = tuple(last_task)
            return tasks
        
        index = 1
        while index < len(hourly_schedule):
            prompt = self._get_schedule_details_prompt(persona, hourly_schedule, index, cur_date)
            print(prompt)
            response = llm.run_prompt(prompt)
            refined_tasks = _clean_up(response)
            verified_tasks = _verify_duration(refined_tasks, hourly_schedule[index][1])
            print(verified_tasks)
            hourly_schedule = hourly_schedule[:index] + verified_tasks + hourly_schedule[index + 1:]
            index += len(verified_tasks)
        
        return hourly_schedule

    
        


# def main():
#     with open("./persona/Sophia Yang.txt", "r", encoding='utf-8') as f:
#         persona = f.read()
#     cur_date = datetime.now().strftime("%A %B %d")
#     wake_up_hour = generate_wake_up_hour(persona)
#     print(wake_up_hour)
#     daily_plan = generate_first_daily_plan(persona, wake_up_hour)
#     print(daily_plan)
#     hourly_schedule = generate_hourly_schedule(persona, wake_up_hour, daily_plan)
#     print(hourly_schedule)
#     expanded_schedule = generate_task_details(persona, hourly_schedule, cur_date)
#     for i, task in enumerate(expanded_schedule):
#         print(f"[{i}, {task}]\n")
    
    
    
# main()