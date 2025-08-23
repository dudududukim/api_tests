import json
import os
from datetime import datetime
from typing import List, Dict


class ConversationManager:
    def __init__(self, history_file="conversation_history.json", max_history=40):
        self.history_file = history_file
        self.max_history = max_history
        self.conversation_history = self.load_history()
    
    def load_history(self) -> List[Dict]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"대화 기록 저장 실패: {e}")
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.save_history()
    
    def get_messages_for_api(self) -> List[Dict]:
        return [{"role": msg["role"], "content": msg["content"]} 
                for msg in self.conversation_history[-self.max_history * 2:]]
    
    def clear_history(self):
        self.conversation_history = []
        self.save_history()
