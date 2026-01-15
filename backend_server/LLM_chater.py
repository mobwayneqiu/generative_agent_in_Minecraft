from ollama import AsyncClient
from ollama import Client
import re # type: ignore
import json


with open("./config/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
MODEL_NAME = config.get("OLLAMA_CONFIG").get("MODEL_NAME")

class DialogueManager:
    def __init__(self, prompt_path='prompt/system_prompt.txt'):
        self.client = Client(host='http://localhost:11434')
        self.model = MODEL_NAME
        self.conversations = {}
        
        # 加载提示词文件内容
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
    
    async def _generate_response(self, bot_name: str, sender: str, message: str) -> str:
        conversation_key = f"{bot_name}_{sender}"
        
        # 初始化对话历史记录
        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = [{
                'role': 'system',
                'content': self.system_prompt
            }]
        # 添加用户消息
        self.conversations[conversation_key].append({
            'role': 'user',
            'content': message
        })
        # try:
        response = self.client.chat(
            model=self.model,
            messages=self.conversations[conversation_key],
            options={'temperature': 0.5}
        )
        raw = response['message']['content']
        cleaned = self._clean_response(raw)
        self.conversations[conversation_key].append({
            'role': 'assistant',
            'content': cleaned
        })
        return cleaned
    
    def _clean_response(self, text: str) -> str:
        """清洗回复内容：移除<think>标签和多余空格"""
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    async def run_prompt(self, username, prompt):
        response = await self._generate_response("assistent", username, prompt)
        return response
    
class LLMResponse:
    def __init__(self, prompt_path='prompt/system_prompt.txt'):
        self.client = Client(host='http://localhost:11434')
        self.model = 'llama3.1:8b'
        self.conversations = {}
        
        # 加载提示词文件内容
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
    
    def _generate_response(self, bot_name: str, sender: str, message: str) -> str:
        """生成并返回清洗后的回复，使用 bot_name 与 sender 构成唯一对话上下文"""
        conversation_key = f"{bot_name}_{sender}"
        
        # 初始化对话历史记录
        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = [{
                'role': 'system',
                'content': self.system_prompt
            }]
        
        # 添加用户消息
        self.conversations[conversation_key].append({
            'role': 'user',
            'content': message
        })
        
        # try:
        # 使用 asyncio.run 同步调用异步方法
        response = self.client.chat(
            model=self.model,
            messages=self.conversations[conversation_key],
            options={'temperature': 0.5}
        )
        raw = response['message']['content']
        cleaned = self._clean_response(raw)
        self.conversations[conversation_key].append({
            'role': 'assistant',
            'content': cleaned
        })
        return cleaned
    
    def _clean_response(self, text: str) -> str:
        """清洗回复内容：移除<think>标签和多余空格"""
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def run_prompt(self, prompt):
        response = self._generate_response("assistent", "user", prompt)
        return response