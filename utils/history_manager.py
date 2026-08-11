import json
import os


class HistoryManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "history.json")
        self.history_data = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            return False

    def get_all(self):
        self.history_data = self._load_history()
        return self.history_data

    def get_by_issue(self, issue):
        self.history_data = self._load_history()
        for record in self.history_data:
            if str(record["issue"]) == str(issue):
                return record
        return None

    def add_record(self, record):
        self.history_data = self._load_history()
        for r in self.history_data:
            if str(r["issue"]) == str(record["issue"]):
                return False, "期号已存在"
        self.history_data.append(record)
        self.history_data.sort(key=lambda x: str(x["issue"]), reverse=True)
        if self._save_history():
            return True, "添加成功"
        return False, "保存失败"

    def delete_record(self, issue):
        self.history_data = self._load_history()
        original_len = len(self.history_data)
        self.history_data = [r for r in self.history_data if str(r["issue"]) != str(issue)]
        if len(self.history_data) < original_len:
            if self._save_history():
                return True, "删除成功"
            return False, "保存失败"
        return False, "未找到该记录"

    def clear_all(self):
        self.history_data = []
        if self._save_history():
            return True, "清空成功"
        return False, "保存失败"

    def batch_add(self, records):
        self.history_data = self._load_history()
        added_count = 0
        for record in records:
            exists = any(str(r["issue"]) == str(record["issue"]) for r in self.history_data)
            if not exists:
                self.history_data.append(record)
                added_count += 1
        if added_count > 0:
            self.history_data.sort(key=lambda x: str(x["issue"]), reverse=True)
            self._save_history()
        return added_count
