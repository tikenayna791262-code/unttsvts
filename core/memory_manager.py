import sqlite3
import os
import json
from datetime import datetime

class MemoryManager:
    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), "data", "memory.db")
        self._init_db()

    def _init_db(self):
        """初始化记忆数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 创建记忆表：存储对话、用户偏好、重要事件
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                role TEXT,
                content TEXT,
                tags TEXT,
                importance INTEGER DEFAULT 1
            )
        ''')
        conn.commit()
        conn.close()

    def save_chat(self, role, content, tags=""):
        """保存一条对话到长期记忆"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO long_term_memory (timestamp, role, content, tags) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role, content, tags)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[记忆库错误] 保存失败: {e}")
            return False
        
    def is_important(self, content):
        """
        利用简单的规则或关键词初步过滤（节省 API 调用）
        """
        keywords = ["叫", "喜欢", "住", "去", "做", "安排", "提醒", "密码", "账号", "地址", "电话"]
        # 如果包含这些关键词，或者长度超过一定限制，初步认为可能重要
        return any(k in content for k in keywords) or len(content) > 30

    def search_memory(self, query, limit=5):
        """简单关键词检索（后续可升级为向量检索）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 搜索包含关键词的记录
            cursor.execute(
                "SELECT role, content FROM long_term_memory WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f'%{query}%', limit)
            )
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception:
            return []

    def get_recent_context(self, limit=10):
        """获取最近的历史上下文"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM long_term_memory ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            results = cursor.fetchall()[::-1] # 翻转回正序
            conn.close()
            return results
        except Exception:
            return []
        
    def get_all_memories(self):
        """获取所有存下的对话记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, role, content FROM long_term_memory ORDER BY id ASC")
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception:
            return []

    def wipe_and_summarize(self, summary_text):
        """清空旧记忆并存入一条核心总结"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 1. 删除所有旧对话
            cursor.execute("DELETE FROM long_term_memory")
            # 2. 插入 AI 生成的阶段性总结
            cursor.execute(
                "INSERT INTO long_term_memory (timestamp, role, content, tags, importance) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "system", f"【核心记忆档案】: {summary_text}", "archive", 5)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"总结存入失败: {e}")
            return False

# 实例化
memory_sys = MemoryManager()