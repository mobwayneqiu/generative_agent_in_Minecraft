import logging
import json
import re
import numpy as np
from datetime import datetime
from typing import List, Dict
from sentence_transformers import SentenceTransformer

from backend_server.LLM_chater import LLMResponse

logger = logging.getLogger(__name__)
manager = LLMResponse()
bot_name = "assistant"

SIMILARITY_THRESHOLD = 0.85  # 相似度阈值

class MemoryRepository:
    def __init__(self, storage_path: str):
        self.nodes: Dict[str, dict] = {}
        self._counter = 1
        self.storage_path = storage_path
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 存储归一化的嵌入向量矩阵
        self.embeddings = np.empty((0, self.model.get_sentence_embedding_dimension()), dtype=np.float32)
        
        # 初始化示例节点
        self.add_node("Sophia Yang", "be friends with", "Ethan Choi", 10.0, "Sophia Yang and Ethan Choi are friends.")

    def _next_id(self) -> str:
        nid = f"node_{self._counter}"
        self._counter += 1
        return nid

    def add_node(self, subject: str, predicate: str, obj: str,
                 poignancy: float, description: str) -> None:
        """新增记忆节点，自动进行向量相似度去重"""
        try:
            # 生成归一化的嵌入向量
            new_embedding = self.model.encode(
                description,
                convert_to_tensor=False,
                normalize_embeddings=True
            )
            new_embedding = new_embedding.astype(np.float32).reshape(1, -1)

            # 相似性检查
            if self._check_similarity(new_embedding):
                logger.info(f"Similar memory exists, skip adding: {description}")
                return

            # 创建新节点
            node_id = self._next_id()
            self.nodes[node_id] = {
                "node_id": node_id,
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "poignancy": poignancy,
                "keywords": [subject.strip(), obj.strip()],
                "description": description,
                "embedding": new_embedding.flatten().tolist(),
            }
            
            # 更新嵌入矩阵
            self.embeddings = np.vstack([self.embeddings, new_embedding])
            logger.debug(f"Added new memory: {description}")

        except Exception as e:
            logger.error(f"Failed to add node: {str(e)}")

    def _check_similarity(self, new_embedding: np.ndarray) -> bool:
        """检查新嵌入向量与现有记忆的相似度"""
        if self.embeddings.size == 0:
            return False

        # 快速余弦相似度计算（基于归一化向量）
        similarities = np.dot(self.embeddings, new_embedding.T).flatten()
        max_similarity = np.max(similarities)
        
        logger.debug(f"Max similarity with existing memories: {max_similarity:.4f}")
        return max_similarity >= SIMILARITY_THRESHOLD

    def search_nodes_by_keyword(self, query: str, top_k: int = 10) -> List[dict]:
        """基于语义相似度的记忆检索"""
        try:
            query_embedding = self.model.encode(
                query,
                convert_to_tensor=False,
                normalize_embeddings=True
            ).astype(np.float32)

            # 使用矩阵运算
            similarities = np.dot(self.embeddings, query_embedding)
            sorted_indices = np.argsort(similarities)[::-1][:top_k]

            return [{
                "description": list(self.nodes.values())[i]["description"],
                "keywords": list(self.nodes.values())[i]["keywords"]
            } for i in sorted_indices if i < len(self.nodes)]

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    def save_to_json(self, name: str) -> None:
        """保存时自动过滤重复数据"""
        serialized = {
            k: {**v, "embedding": v["embedding"]}
            for k, v in self.nodes.items()
        }
        with open(f"{self.storage_path}/{name}.json", "w") as f:
            json.dump({"nodes": serialized}, f, indent=2)

    def load_from_json(self, name: str) -> None:
        """加载时重建嵌入矩阵"""
        try:
            with open(f"{self.storage_path}/{name}.json", "r") as f:
                data = json.load(f)

            self.nodes = data.get("nodes", {})
            self.embeddings = np.empty((0, self.model.get_sentence_embedding_dimension()), dtype=np.float32)
            
            # 批量处理嵌入向量
            embeddings_list = []
            for node_id, node in self.nodes.items():
                # 兼容旧数据格式
                if "embedding" not in node:
                    embedding = self.model.encode(
                        node.get("description", ""),
                        normalize_embeddings=True
                    ).astype(np.float32)
                    node["embedding"] = embedding.tolist()
                
                embeddings_list.append(node["embedding"])
            
            # 一次性构建矩阵
            if embeddings_list:
                self.embeddings = np.vstack(embeddings_list)
            
            # 更新ID计数器
            if self.nodes:
                last_id = max(int(k.split("_")[1]) for k in self.nodes)
                self._counter = last_id + 1

        except FileNotFoundError:
            logger.info(f"New memory file created: {name}")
        except Exception as e:
            logger.error(f"Failed to load memory: {str(e)}")

    async def score_importance(self, memory_content: str) -> float:
        """
        调用 LLM 评分（1-10），返回 0.0-1.0。
        """
        system_prompt = (
            "A chat between a curious user and an artificial intelligence assistant. The assistant "
            "gives helpful, detailed, and polite answers to the user's questions.\n"
            "###ASSISTANT: "
        )
        template = (
            "On the scale of 1 to 10, where 1 is not important at all"
            " (e.g., brushing teeth) and 10 is"
            " extremely important (e.g., a break up), rate the importance"
            " of the following memory. Reply with a single integer.\n"
            f"Memory: {memory_content}\nRating: "
        )
        prompt = system_prompt + template
        score_str = manager.run_prompt(prompt)
        logger.debug(f"Raw LLM score: {score_str}")
        match = re.search(r"(\d+)", score_str)
        if match:
            val = int(match.group(1))
            return float(val)
        return 0.0

    def format_memories(self, memories: List[dict]) -> str:
        """
        将检索到的记忆列表格式化为可读文本。
        假设每个 dict 中含有 'page_content' 和 metadata['created_at']。
        """
        lines = []
        seen = set()
        for mem in memories:
            content = mem["page_content"]
            if content in seen:
                continue
            seen.add(content)
            ts = datetime.fromisoformat(mem["metadata"]["created_at"])
            formatted = ts.strftime("%B %d, %Y, %I:%M %p")
            lines.append(f"- {formatted}: {content.strip()}")
        return "\n".join(lines)

class MemoryService:
    def __init__(self):
        self._repo = MemoryRepository("./memory")

    def search_memory(self, query: str) -> List[dict]:
        return self._repo.search_nodes_by_keyword(query)

    async def store_memory(self, persona_name: str, content: str,
                           subject: str, predicate: str, obj: str) -> None:
        """
        新增一条记忆，自动计算重要性并保存到对应 persona 的 JSON 文件。
        """
        poignancy = await self._repo.score_importance(content)
        self._repo.add_node(subject, predicate, obj,
                            poignancy, description=content)
        self._repo.save_to_json(persona_name)


# import logging
# import json
# import re
# from collections import defaultdict
# from datetime import datetime  # type: ignore
# from typing import List, Tuple, Optional # type: ignore

# from backend_server.LLM_chater import LLMResponse

# logger = logging.getLogger(__name__)
# manager = LLMResponse()
# bot_name = "assistant"


# class MemoryRepository:
#     """
#     底层存储与辅助实现（打分、格式化、JSON 读写等）。
#     不直接暴露给业务调用。
#     """
#     def __init__(self, storage_path: str):
#         self.nodes = {}
#         self.inverted_index = defaultdict(list)
#         self._counter = 1
#         self.storage_path = storage_path
#         self.add_node("Sophia Yang", "be friends with", "Ethan Choi", 10.0, "Sophia Yang and Ethan Choi are friends.")

#     def _next_id(self) -> str:
#         nid = f"node_{self._counter}"
#         self._counter += 1
#         return nid

#     def add_node(self, subject: str, predicate: str, obj: str,
#                  poignancy: float, description: str) -> None:
#         node_id = self._next_id()
#         keywords = [subject.strip(), obj.strip()]
        
#         # 新增索引构建逻辑
#         for kw in keywords:
#             normalized_kw = kw.lower().strip()  # 标准化关键词
#             self.inverted_index[normalized_kw].append(node_id)
        
#         # 原有节点存储逻辑保持不变
#         self.nodes[node_id] = {
#             "node_id": node_id,
#             "subject": subject,
#             "predicate": predicate,
#             "object": obj,
#             "poignancy": poignancy,
#             "keywords": keywords,
#             "description": description,
#         }

#     def search_nodes_by_keyword(self, keyword: str) -> List[dict]:
#         results = []
#         for node in self.nodes.values():
#             if keyword in node["keywords"]:
#                 results.append({
#                     "description": node["description"],
#                     "keywords": node["keywords"]
#                 })
#         return results

#     def save_to_json(self, name: str) -> None:
#         with open(f"{self.storage_path}/{name}.json", "w") as f:
#             json.dump({"nodes": self.nodes}, f, indent=2)

#     def search_nodes_by_keyword(self, keyword: str) -> List[dict]:
#         # 使用倒排索引优化搜索
#         normalized_kw = keyword.lower().strip()
#         matched_ids = self.inverted_index.get(normalized_kw, [])
        
#         return [{
#             "description": self.nodes[node_id]["description"],
#             "keywords": self.nodes[node_id]["keywords"]
#         } for node_id in matched_ids]

#     def load_from_json(self, name: str) -> None:
#         with open(f"{self.storage_path}/{name}.json", "r") as f:
#             data = json.load(f)
#         self.nodes = data.get("nodes", {})
        
#         # 重建倒排索引
#         self.inverted_index.clear()
#         for node_id, node_data in self.nodes.items():
#             for kw in node_data["keywords"]:
#                 normalized_kw = kw.lower().strip()
#                 self.inverted_index[normalized_kw].append(node_id)
        
#         if self.nodes:
#             last_id = max(int(k.split("_")[1]) for k in self.nodes)
#             self._counter = last_id + 1

#     async def score_importance(self, memory_content: str) -> float:
#         """
#         调用 LLM 评分（1-10），返回 0.0-1.0。
#         """
#         system_prompt = (
#             "A chat between a curious user and an artificial intelligence assistant. The assistant "
#             "gives helpful, detailed, and polite answers to the user's questions.\n"
#             "###ASSISTANT: "
#         )
#         template = (
#             "On the scale of 1 to 10, where 1 is not important at all"
#             " (e.g., brushing teeth) and 10 is"
#             " extremely important (e.g., a break up), rate the importance"
#             " of the following memory. Reply with a single integer.\n"
#             f"Memory: {memory_content}\nRating: "
#         )
#         prompt = system_prompt + template
#         score_str = manager.run_prompt(prompt)
#         logger.debug(f"Raw LLM score: {score_str}")
#         match = re.search(r"(\d+)", score_str)
#         if match:
#             val = int(match.group(1))
#             return float(val)
#         return 0.0

#     def format_memories(self, memories: List[dict]) -> str:
#         """
#         将检索到的记忆列表格式化为可读文本。
#         假设每个 dict 中含有 'page_content' 和 metadata['created_at']。
#         """
#         lines = []
#         seen = set()
#         for mem in memories:
#             content = mem["page_content"]
#             if content in seen:
#                 continue
#             seen.add(content)
#             ts = datetime.fromisoformat(mem["metadata"]["created_at"])
#             formatted = ts.strftime("%B %d, %Y, %I:%M %p")
#             lines.append(f"- {formatted}: {content.strip()}")
#         return "\n".join(lines)


# class MemoryService:
#     def __init__(self):
#         self._repo = MemoryRepository("./memory")

#     def search_memory(self, keyword: str) -> List[dict]:
#         """
#         根据关键词检索记忆（只返回 description 与 keywords）。
#         """
#         return self._repo.search_nodes_by_keyword(keyword)

#     async def store_memory(self, persona_name: str, content: str,
#                            subject: str, predicate: str, obj: str) -> None:
#         """
#         新增一条记忆，自动计算重要性并保存到对应 persona 的 JSON 文件。
#         """
#         poignancy = await self._repo.score_importance(content)
#         self._repo.add_node(subject, predicate, obj,
#                             poignancy, description=content)
#         self._repo.save_to_json(persona_name)
