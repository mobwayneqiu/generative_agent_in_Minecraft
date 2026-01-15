from datetime import datetime # type: ignore
import re
from typing import Tuple, Optional, Union # type: ignore

def get_persona_firstname(persona: str):
    name = persona.split("Name:")[1].split("\n")[0].strip()
    return name

def get_persona_lifestyle(persona: str):
    lifestyle = persona.split("Lifestyle:")[1].split("\n")[0].strip()
    return lifestyle
    
def get_hour_from_int(hour):
    """
    使用 datetime 模块将 0-23 的小时数转换为 12 小时制格式，输出类似 "8 a.m." 或 "3 p.m." 的字符串。
    """
    if not isinstance(hour, int) or not (0 <= hour < 24):
        raise ValueError("Hour must be an integer between 0 and 23")
    dt = datetime(2000, 1, 1, hour, 0)
    time_str = dt.strftime("%I %p").lstrip("0")
    time_str = time_str.replace("AM", "a.m.").replace("PM", "p.m.")
    return time_str

def find_contained_keyword(input_str, keyword_list, case_sensitive=True):
    """
    在输入字符串中按出现顺序查找第一个匹配的关键词（同一位置优先最长关键词）
    
    参数:
        input_str (str): 被检索的长字符串
        keyword_list (list): 关键词列表
        case_sensitive (bool): 是否区分大小写，默认True
        
    返回:
        str/None: 第一个匹配的关键词，无匹配返回None
    """
    # 预处理目标字符串
    target_str = input_str.lower() if not case_sensitive else input_str
    matches = []
    
    for keyword in keyword_list:
        # 处理当前关键词的匹配条件
        search_term = keyword.lower() if not case_sensitive else keyword
        start_idx = target_str.find(search_term)
        
        if start_idx != -1:
            # 记录起始位置、负长度（用于排序）、原始关键词
            matches.append((start_idx, -len(keyword), keyword))
    
    if not matches:
        return None
    
    # 排序规则：先按起始位置升序，再按关键词长度降序
    matches.sort(key=lambda x: (x[0], x[1]))
    
    # 返回第一个匹配项
    return matches[0][2]

class ActionObjectExtractor:
    """
    用于从文本中提取 SO 二元组的工具类
    """
    def normalize_pair_str(self, s: str) -> str:
        """
        统一中英文括号，去除首尾空白，补全括号。
        """
        s = s.strip()
        s = s.replace("（", "(").replace("）", ")")
        if not s.startswith("("):
            s = "(" + s
        if not s.endswith(")"):
            s = s + ")"
        return s

    def regex_extract_pair(self, s: str) -> Optional[Tuple[str, str]]:
        """
        正则提取二元组：(subj, obj)
        """
        pattern = r"""
        ^\(\s*
        (?P<subj>[^,]+?)\s*,\s*
        (?P<obj>[^)]+?)\s*
        \)$
        """
        m = re.match(pattern, s, re.VERBOSE)
        if not m:
            return None
        return m.group("subj").strip(), m.group("obj").strip()

    def fallback_split_pair(self, s: str) -> Tuple[str, str]:
        """
        保底分割：去掉括号，按逗号/分号/斜杠分割，取第一和最后两段。
        """
        core = s.strip().lstrip("(").rstrip(")")
        parts = re.split(r"[;,/]+", core)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) == 0:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        # 2及以上：第一当主语，最后当宾语
        return parts[0], parts[-1]

    def extract_subject_object(self, text: str) -> Tuple[str, str]:
        """
        从大段文本中定位最后的二元组 '(..., ...)' 并提取 (subject, object)；
        若未找到任何二元组，则对全文本直接尝试解析。
        """
        # 查找所有“不含嵌套括号”的二元组
        pattern = r"\([^()]*?,[^()]*?\)"
        matches = list(re.finditer(pattern, text))
        if matches:
            last_pair = matches[-1].group()
            s = self.normalize_pair_str(last_pair)
            res = self.regex_extract_pair(s)
            if res:
                return res
            else:
                return self.fallback_split_pair(s)
        else:
            # 整段当二元组尝试
            s = self.normalize_pair_str(text)
            res = self.regex_extract_pair(s)
            if res:
                return res
            else:
                return self.fallback_split_pair(s)


class ActionTupleExtractor:
    """
    用于从文本中提取 SPO 三元组的工具类
    """
    def _normalize_triple_str(self, s: str) -> str:
        s = s.strip()
        s = s.replace("（", "(").replace("）", ")")
        if not s.startswith("("):
            s = "(" + s
        if not s.endswith(")"):
            s = s + ")"
        return s

    def _regex_extract(self, s: str) -> Optional[Tuple[str, str, str]]:
        pattern = r"""
        ^\(\s*
        (?P<subj>[^,]+?)\s*,\s*
        (?P<pred>[^,]+?)\s*,\s*
        (?P<obj>[^)]+?)\s*
        \)$
        """
        m = re.match(pattern, s, re.VERBOSE)
        if not m:
            return None
        return m.group("subj").strip(), m.group("pred").strip(), m.group("obj").strip()

    def _fallback_split(self, s: str) -> Tuple[str, str, str]:
        core = s.strip().lstrip("(").rstrip(")")
        parts = re.split(r"[;,/]+", core)
        parts = [p.strip() for p in parts if p.strip()]
        while len(parts) < 3:
            parts.append("")
        if len(parts) > 3:
            subj = parts[0]
            obj  = parts[-1]
            pred = " ".join(parts[1:-1])
        else:
            subj, pred, obj = parts
        return subj, pred, obj

    def _extract_spo_from_triple(self, triple_str: str) -> Tuple[str, str, str]:
        """
        对单纯三元组字符串做提取
        """
        s = self._normalize_triple_str(triple_str)
        res = self._regex_extract(s)
        if res:
            return res
        else:
            return self._fallback_split(s)

    def get_action_tuple(self, text: str) -> Tuple[str, str, str]:
        """
        从大段文本中定位最后的 '(..., ..., ...)'，并提取 SPO；
        若未找到括号，就直接对全文本做尝试。
        """
        # 向后查找最后一个符合三段式括号的子串
        matches = list(re.finditer(r"\([^()]*?,[^()]*?,[^()]*?\)", text))
        if matches:
            last = matches[-1].group()
            return self._extract_spo_from_triple(last)
        else:
            # 整段当三元组处理
            return self._extract_spo_from_triple(text)
        
def find_yes_no(text: str) -> Union[bool, str]:
    """
    在 text 中检索第一个出现的 “Yes” 或 “No”（不区分大小写）。
    - 如果第一个匹配的是 “Yes”，返回 True（布尔值）。
    - 如果第一个匹配的是 “No”，返回 False（布尔值）。
    - 如果两者都没找到，返回字符串 "False"。
    """
    # 编译一个不区分大小写的正则，匹配 Yes 或 No
    pattern = re.compile(r"\b(yes|no)\b", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return "False"
    token = match.group(1).lower()
    return True if token == "yes" else False

def replace_persona_currently(persona, new_currently):
        """
        将文本文件中以 'Currently:' 开头的那一行替换为 new_currently。
        """
        # 构造替换后的完整行
        replacement_line = f'Currently: {new_currently}'
        
        # 使用正则替换以 Currently: 开头的整行
        new_persona = re.sub(r'^Currently:.*$', replacement_line, persona, flags=re.MULTILINE)
        return new_persona

def get_minecraft_time(real_minutes):
    """
    将现实分钟数映射为Minecraft世界时间
    
    参数：
    real_minutes -- 现实时间的分钟数（0-1439）
    
    返回：
    Minecraft时间刻（0-23999），0刻对应现实中午夜的白天开始
    """
    # 核心转换逻辑
    minecraft_ticks = (real_minutes * 24000) // 1440
    phase_offset = 18000
    return (minecraft_ticks + phase_offset) % 24000
