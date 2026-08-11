import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
import threading
from utils.history_manager import HistoryManager


RED_ALL = list(range(1, 36))   # 前区 1-35
BLUE_ALL = list(range(1, 13))  # 后区 1-12


def _parse_result(result_str):
    """解析 'r1,r2,r3,r4,r5|b1,b2' → (red_list, blue_list)。后区为2个号码。"""
    if not result_str or "|" not in result_str:
        return [], []
    try:
        rp, bp = result_str.split("|", 1)
        red = [int(x) for x in rp.split(",")]
        blue = [int(x) for x in bp.split(",")]
        return red, blue
    except Exception:
        return [], []


def _dlt_prize_level(front_count, back_count):
    """根据前区命中数(0-5)和后区命中数(0-2)返回大乐透奖级（官方9级制）。

    一等奖 5+2；二等奖 5+1；三等奖 5+0；四等奖 4+2；五等奖 4+1；
    六等奖 3+2；七等奖 4+0；八等奖 3+1 / 2+2；
    九等奖 3+0 / 2+1 / 1+2 / 0+2；其余为未中奖。
    """
    f, b = front_count, back_count
    if f == 5 and b == 2:
        return "一等奖"
    if f == 5 and b == 1:
        return "二等奖"
    if f == 5 and b == 0:
        return "三等奖"
    if f == 4 and b == 2:
        return "四等奖"
    if f == 4 and b == 1:
        return "五等奖"
    if f == 3 and b == 2:
        return "六等奖"
    if f == 4 and b == 0:
        return "七等奖"
    if (f == 3 and b == 1) or (f == 2 and b == 2):
        return "八等奖"
    if (f == 3 and b == 0) or (f == 1 and b == 2) or (f == 2 and b == 1) or (f == 0 and b == 2):
        return "九等奖"
    return "未中奖"


class PredictionModel:
    def __init__(self, parent):
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.history_manager = HistoryManager()
        self.prediction_data = {}
        self.prediction_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prediction_data.json"
        )
        self.saved_predictions_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "saved_predictions.json"
        )
        self.settings_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prediction_settings.json"
        )
        self.saved_predictions = []
        self.settings = {}
        self.status_var = tk.StringVar(value="")

        self._load_prediction_data()
        self._load_saved_predictions()
        self._load_settings()
        self._build_ui()

    def _load_prediction_data(self):
        if os.path.exists(self.prediction_file):
            try:
                with open(self.prediction_file, 'r', encoding='utf-8') as f:
                    self.prediction_data = json.load(f)
            except Exception:
                self.prediction_data = {}

    def _save_prediction_data(self):
        try:
            with open(self.prediction_file, 'w', encoding='utf-8') as f:
                json.dump(self.prediction_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _is_legacy_data(self):
        """检测 prediction_data 是否为旧结构（red_kill/blue 而非 front/back）。"""
        if not self.prediction_data or "params" not in self.prediction_data:
            return False
        params = self.prediction_data["params"]
        # 旧结构有 kill_count 无 front_count
        if "kill_count" in params and "front_count" not in params:
            return True
        # 双重校验：检查预测者数据字段
        predictions = self.prediction_data.get("predictions", {})
        for pred_data in predictions.values():
            predictors = pred_data.get("predictors", [])
            if predictors:
                first = predictors[0]
                if "red_kill" in first or "blue" in first:
                    if "front" not in first:
                        return True
                break
        return False

    def _load_saved_predictions(self):
        if os.path.exists(self.saved_predictions_file):
            try:
                with open(self.saved_predictions_file, 'r', encoding='utf-8') as f:
                    self.saved_predictions = json.load(f)
            except Exception:
                self.saved_predictions = []
        else:
            self.saved_predictions = []

    def _save_saved_predictions(self):
        try:
            with open(self.saved_predictions_file, 'w', encoding='utf-8') as f:
                json.dump(self.saved_predictions, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _load_settings(self):
        """加载参数设置，使启动时恢复上次保存的参数。"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = {}
        else:
            self.settings = {}

    def _write_settings_file(self):
        """将当前参数写入设置文件，返回是否成功。"""
        self.settings = {
            "predictor_count": self.predictor_count_var.get(),
            "front_count": self.front_count_var.get(),
            "back_count": self.back_count_var.get(),
            "min_streak_front": self.min_streak_front_var.get(),
            "min_streak_back": self.min_streak_back_var.get(),
            "predict_periods": self.predict_periods_var.get(),
        }
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _save_settings(self):
        """保存设置按钮：持久化当前参数并提示。"""
        if self._write_settings_file():
            messagebox.showinfo("成功", "参数设置已保存，下次启动将自动加载当前参数")
        else:
            messagebox.showerror("错误", "设置保存失败，请检查文件写入权限")

    def _refresh_saved_list(self):
        total = len(self.saved_predictions)
        opened = len([r for r in self.saved_predictions if r.get("result")])
        pending = total - opened
        self.stats_label.config(
            text=f"已保存 {total} 期预测记录（已开奖 {opened} 期，待开奖 {pending} 期），点击\"预测对错统计\"查看详情"
        )

    def _build_ui(self):
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 参数设置
        param_frame = ttk.LabelFrame(main_frame, text="参数设置", padding=8)
        param_frame.pack(fill=tk.X, pady=(0, 8))

        param_row = ttk.Frame(param_frame)
        param_row.pack(fill=tk.X)

        ttk.Label(param_row, text="预测者数量：").pack(side=tk.LEFT, padx=(5, 2), pady=5)
        self.predictor_count_var = tk.StringVar(value=str(self.settings.get("predictor_count", "5000")))
        ttk.Entry(param_row, textvariable=self.predictor_count_var, width=10).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        ttk.Label(param_row, text="每预测者前区数量：").pack(side=tk.LEFT, padx=2, pady=5)
        self.front_count_var = tk.StringVar(value=str(self.settings.get("front_count", "8")))
        ttk.Entry(param_row, textvariable=self.front_count_var, width=6).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        ttk.Label(param_row, text="每预测者后区数量：").pack(side=tk.LEFT, padx=2, pady=5)
        self.back_count_var = tk.StringVar(value=str(self.settings.get("back_count", "4")))
        ttk.Entry(param_row, textvariable=self.back_count_var, width=6).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        ttk.Label(param_row, text="前区最小连续命中：").pack(side=tk.LEFT, padx=2, pady=5)
        self.min_streak_front_var = tk.StringVar(value=str(self.settings.get("min_streak_front", "3")))
        ttk.Entry(param_row, textvariable=self.min_streak_front_var, width=6).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        ttk.Label(param_row, text="后区最小连续命中：").pack(side=tk.LEFT, padx=2, pady=5)
        self.min_streak_back_var = tk.StringVar(value=str(self.settings.get("min_streak_back", "3")))
        ttk.Entry(param_row, textvariable=self.min_streak_back_var, width=6).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        ttk.Label(param_row, text="预测期数：").pack(side=tk.LEFT, padx=2, pady=5)
        self.predict_periods_var = tk.StringVar(value=str(self.settings.get("predict_periods", "30")))
        ttk.Entry(param_row, textvariable=self.predict_periods_var, width=6).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        tk.Button(param_row, text="  🔄 应用参数并生成预测数据  ", bg="#5bc0de", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._generate_predictions).pack(side=tk.LEFT, padx=6, pady=8)

        self.btn_add_predict = tk.Button(param_row, text="  ➕ 补齐预测  ", bg="#f0ad4e", fg="white",
                                         relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                                         command=self._add_predictions)
        self.btn_add_predict.pack(side=tk.LEFT, padx=6, pady=8)

        tk.Button(param_row, text="  💾 保存设置  ", bg="#6f42c1", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._save_settings).pack(side=tk.LEFT, padx=6, pady=8)

        # 查询区
        query_frame = ttk.LabelFrame(main_frame, text="查询预测数据", padding=8)
        query_frame.pack(fill=tk.X, pady=(0, 8))

        query_row = ttk.Frame(query_frame)
        query_row.pack(fill=tk.X)

        ttk.Label(query_row, text="预测者ID：").pack(side=tk.LEFT, padx=(5, 2), pady=5)
        self.query_pid_var = tk.StringVar(value="1")
        ttk.Entry(query_row, textvariable=self.query_pid_var, width=10).pack(side=tk.LEFT, padx=(2, 10), pady=5)

        tk.Button(query_row, text="  🔍 查询该预测者所有期预测数据  ", bg="#5cb85c", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._query_predictor_data).pack(side=tk.LEFT, padx=10, pady=5)

        tk.Button(query_row, text="  🔄 刷新开奖结果  ", bg="#f0ad4e", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._refresh_results).pack(side=tk.LEFT, padx=6, pady=5)

        self.btn_calc_kill = tk.Button(query_row, text="  ⚡ 计算前区杀号+后区杀号  ", bg="#d9534f", fg="white",
                                       relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9, "bold"),
                                       command=self._calculate_kill_numbers)
        self.btn_calc_kill.pack(side=tk.LEFT, padx=6, pady=5)

        # 预测者历史数据
        self.query_result_frame = ttk.LabelFrame(main_frame, text="预测者历史数据", padding=5)
        self.query_result_frame.pack(fill=tk.X, pady=(0, 8))

        query_columns = ("issue", "result", "front", "back", "front_hit", "back_hit")
        self.query_tree = ttk.Treeview(self.query_result_frame, columns=query_columns, show="headings", height=8)
        self.query_tree.heading("issue", text="期号")
        self.query_tree.heading("result", text="开奖号")
        self.query_tree.heading("front", text="前区预测")
        self.query_tree.heading("back", text="后区预测")
        self.query_tree.heading("front_hit", text="前区命中")
        self.query_tree.heading("back_hit", text="后区命中")
        self.query_tree.column("issue", width=80, anchor=tk.CENTER)
        self.query_tree.column("result", width=120, anchor=tk.CENTER)
        self.query_tree.column("front", width=220, anchor=tk.CENTER)
        self.query_tree.column("back", width=120, anchor=tk.CENTER)
        self.query_tree.column("front_hit", width=70, anchor=tk.CENTER)
        self.query_tree.column("back_hit", width=70, anchor=tk.CENTER)

        self.query_tree.tag_configure("hit_row", foreground="#d32f2f")
        self.query_tree.tag_configure("pending", foreground="#999999")
        self.query_tree.tag_configure("result_blue", foreground="#1976d2")

        query_scrollbar = ttk.Scrollbar(self.query_result_frame, orient=tk.VERTICAL, command=self.query_tree.yview)
        self.query_tree.configure(yscrollcommand=query_scrollbar.set)
        self.query_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        query_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双栏：红球杀号 + 蓝球定胆
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # 左栏：红球
        red_frame = ttk.Frame(content_frame)
        red_frame.grid(row=0, column=0, sticky="nsew", padx=3)

        red_kill_frame = ttk.LabelFrame(red_frame, text="前区杀号结果", padding=5)
        red_kill_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.red_kill_label = ttk.Label(red_kill_frame,
                                        text="前区杀号对应预测期数：- | 杀号条目数：0 | 去重后杀号数：0")
        self.red_kill_label.pack(anchor=tk.W, pady=(0, 5))

        red_cols = ("predictor_id", "seq", "kill_num", "streak", "hit_rate")
        self.red_kill_tree = ttk.Treeview(red_kill_frame, columns=red_cols, show="headings", height=10)
        self.red_kill_tree.heading("predictor_id", text="预测者ID")
        self.red_kill_tree.heading("seq", text="序号")
        self.red_kill_tree.heading("kill_num", text="杀号数字")
        self.red_kill_tree.heading("streak", text="连续命中期数")
        self.red_kill_tree.heading("hit_rate", text="历史命中率")
        self.red_kill_tree.column("predictor_id", width=70, anchor=tk.CENTER)
        self.red_kill_tree.column("seq", width=50, anchor=tk.CENTER)
        self.red_kill_tree.column("kill_num", width=80, anchor=tk.CENTER)
        self.red_kill_tree.column("streak", width=100, anchor=tk.CENTER)
        self.red_kill_tree.column("hit_rate", width=100, anchor=tk.CENTER)

        red_kill_scroll = ttk.Scrollbar(red_kill_frame, orient=tk.VERTICAL, command=self.red_kill_tree.yview)
        self.red_kill_tree.configure(yscrollcommand=red_kill_scroll.set)
        self.red_kill_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        red_kill_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        red_remain_frame = ttk.LabelFrame(red_frame, text="前区剩余号码", padding=5)
        red_remain_frame.pack(fill=tk.X)
        self.red_remain_label = ttk.Label(red_remain_frame, text="前区剩余号码总数：35")
        self.red_remain_label.pack(anchor=tk.W, pady=(0, 5))
        self.red_remain_text = tk.Text(red_remain_frame, height=3, bg="white", relief=tk.SUNKEN,
                                       font=("微软雅黑", 10), wrap=tk.WORD)
        self.red_remain_text.pack(fill=tk.X)
        self.red_remain_text.insert(tk.END, " ".join(f"{n:02d}" for n in RED_ALL))
        self.red_remain_text.config(state=tk.DISABLED)

        # 右栏：蓝球
        blue_frame = ttk.Frame(content_frame)
        blue_frame.grid(row=0, column=1, sticky="nsew", padx=3)

        blue_kill_frame = ttk.LabelFrame(blue_frame, text="后区杀号结果", padding=5)
        blue_kill_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.blue_pred_label = ttk.Label(blue_kill_frame,
                                         text="后区杀号对应预测期数：- | 杀号条目数：0 | 去重后杀号数：0")
        self.blue_pred_label.pack(anchor=tk.W, pady=(0, 5))

        blue_cols = ("predictor_id", "seq", "kill_num", "streak", "hit_rate")
        self.blue_pred_tree = ttk.Treeview(blue_kill_frame, columns=blue_cols, show="headings", height=10)
        self.blue_pred_tree.heading("predictor_id", text="预测者ID")
        self.blue_pred_tree.heading("seq", text="序号")
        self.blue_pred_tree.heading("kill_num", text="杀号数字")
        self.blue_pred_tree.heading("streak", text="连续命中期数")
        self.blue_pred_tree.heading("hit_rate", text="历史命中率")
        self.blue_pred_tree.column("predictor_id", width=70, anchor=tk.CENTER)
        self.blue_pred_tree.column("seq", width=50, anchor=tk.CENTER)
        self.blue_pred_tree.column("kill_num", width=80, anchor=tk.CENTER)
        self.blue_pred_tree.column("streak", width=100, anchor=tk.CENTER)
        self.blue_pred_tree.column("hit_rate", width=100, anchor=tk.CENTER)

        blue_scroll = ttk.Scrollbar(blue_kill_frame, orient=tk.VERTICAL, command=self.blue_pred_tree.yview)
        self.blue_pred_tree.configure(yscrollcommand=blue_scroll.set)
        self.blue_pred_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        blue_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        blue_remain_frame = ttk.LabelFrame(blue_frame, text="后区剩余号码", padding=5)
        blue_remain_frame.pack(fill=tk.X)
        self.blue_remain_label = ttk.Label(blue_remain_frame, text="后区剩余号码总数：12")
        self.blue_remain_label.pack(anchor=tk.W, pady=(0, 5))
        self.blue_remain_text = tk.Text(blue_remain_frame, height=3, bg="white", relief=tk.SUNKEN,
                                        font=("微软雅黑", 10), wrap=tk.WORD)
        self.blue_remain_text.pack(fill=tk.X)
        self.blue_remain_text.insert(tk.END, " ".join(f"{n:02d}" for n in BLUE_ALL))
        self.blue_remain_text.config(state=tk.DISABLED)

        # 保存区
        save_frame = ttk.LabelFrame(main_frame, text="保存剩余号码与统计", padding=8)
        save_frame.pack(fill=tk.X, pady=(8, 0))

        save_row1 = ttk.Frame(save_frame)
        save_row1.pack(fill=tk.X)

        ttk.Label(save_row1, text="期号：").pack(side=tk.LEFT, padx=(5, 2), pady=5)
        self.save_issue_var = tk.StringVar()
        ttk.Entry(save_row1, textvariable=self.save_issue_var, width=12).pack(side=tk.LEFT, padx=(2, 15), pady=5)

        tk.Button(save_row1, text="  💾 保存当前预测结果  ", bg="#5bc0de", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._save_remain_numbers).pack(side=tk.LEFT, padx=6, pady=5)

        tk.Button(save_row1, text="   预测对错统计  ", bg="#337ab7", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._calc_prediction_stats).pack(side=tk.LEFT, padx=6, pady=5)

        stats_frame = ttk.Frame(save_frame)
        stats_frame.pack(fill=tk.X, pady=(5, 0))

        self.stats_label = ttk.Label(stats_frame, text="点击\"预测对错统计\"按钮查看详细统计和记录")
        self.stats_label.pack(anchor=tk.W, padx=5)

        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(fill=tk.X, pady=(5, 0))

        self._refresh_saved_list()
        self._set_default_issue()

    def _get_next_issue(self):
        history = self.history_manager.get_all()
        if not history:
            return ""
        history_sorted = sorted(history, key=lambda x: str(x["issue"]))
        latest_issue = str(history_sorted[-1]["issue"])
        try:
            year = int(latest_issue[:4])
            period_num = int(latest_issue[4:])
            next_period = period_num + 1
            if next_period > 999:
                next_period = 1
                year += 1
            return f"{year}{next_period:03d}"
        except Exception:
            return ""

    def _set_default_issue(self):
        # 默认填入预测数据中的 next_issue；否则用历史最新期号
        if self.prediction_data and "params" in self.prediction_data:
            ni = self.prediction_data["params"].get("next_issue", "")
            if ni:
                self.save_issue_var.set(ni)
                return
        ni = self._get_next_issue()
        if ni:
            self.save_issue_var.set(ni)

    def _generate_one_predictor(self, pid, front_count, back_count):
        return {
            "predictor_id": pid + 1,
            "front": random.sample(RED_ALL, min(front_count, 35)),
            "back": random.sample(BLUE_ALL, min(back_count, 12))
        }

    def _generate_predictions(self):
        try:
            predictor_count = int(self.predictor_count_var.get())
            front_count = int(self.front_count_var.get())
            back_count = int(self.back_count_var.get())
            predict_periods = int(self.predict_periods_var.get())

            if predictor_count <= 0 or predict_periods <= 0:
                messagebox.showerror("错误", "预测者数量和预测期数必须大于0")
                return
            if front_count <= 0 or back_count <= 0:
                messagebox.showerror("错误", "前区/后区数量必须大于0")
                return
            if front_count > 35:
                messagebox.showerror("错误", "每预测者前区数量不能超过35")
                return
            if back_count > 12:
                messagebox.showerror("错误", "每预测者后区数量不能超过12")
                return

            history = self.history_manager.get_all()
            history.sort(key=lambda x: str(x["issue"]))
            recent_history = history[-predict_periods:] if len(history) > predict_periods else history

            if not recent_history:
                messagebox.showerror("错误", "历史数据为空，请先在历史查询中添加开奖记录")
                return

            latest_issue = str(recent_history[-1]["issue"])
            year = int(latest_issue[:4])
            period_num = int(latest_issue[4:])
            next_period = period_num + 1
            if next_period > 999:
                next_period = 1
                year += 1
            next_issue = f"{year}{next_period:03d}"

            total = predict_periods + 1

            def do_gen():
                predictions = {}
                for i, record in enumerate(recent_history):
                    issue = str(record["issue"])
                    result_num = record["number"]
                    predictions[issue] = {
                        "result": result_num,
                        "predictors": []
                    }
                    for pid in range(predictor_count):
                        predictions[issue]["predictors"].append(self._generate_one_predictor(pid, front_count, back_count))

                    if (i + 1) % 5 == 0 or i == len(recent_history) - 1:
                        self.root.after(0, lambda p=i + 1, t=total: self.status_var.set(f"正在生成预测数据... {p}/{t}"))

                predictions[next_issue] = {"result": "", "predictors": []}
                for pid in range(predictor_count):
                    predictions[next_issue]["predictors"].append(self._generate_one_predictor(pid, front_count, back_count))

                self.prediction_data = {
                    "params": {
                        "predictor_count": predictor_count,
                        "front_count": front_count,
                        "back_count": back_count,
                        "min_streak_front": int(self.min_streak_front_var.get()),
                        "min_streak_back": int(self.min_streak_back_var.get()),
                        "predict_periods": predict_periods,
                        "next_issue": next_issue
                    },
                    "predictions": predictions
                }

                self._save_prediction_data()
                self.root.after(0, lambda: messagebox.showinfo(
                    "成功", f"已生成{predictor_count}个预测者，{len(recent_history)}期历史预测 + 1期新预测（{next_issue}）"))
                self.root.after(0, lambda: self.status_var.set(f"已生成 {total} 期预测数据"))
                self.root.after(0, self._set_default_issue)

            self.status_var.set(f"正在生成预测数据... 0/{total}")
            # 应用参数时自动保存设置，避免下次启动回到默认值
            self._write_settings_file()
            threading.Thread(target=do_gen, daemon=True).start()

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def _add_predictions(self):
        if not self.prediction_data or "predictions" not in self.prediction_data:
            messagebox.showerror("错误", "请先生成预测数据后再补齐")
            return

        history = self.history_manager.get_all()
        if not history:
            messagebox.showerror("错误", "历史数据为空")
            return

        predictions = self.prediction_data["predictions"]
        history_sorted = sorted(history, key=lambda x: str(x["issue"]))
        history_issues = [str(h["issue"]) for h in history_sorted]
        history_map = {str(h["issue"]): h["number"] for h in history_sorted}
        predicted_issues_set = set(predictions.keys())

        max_history_issue = history_issues[-1]
        max_history_year = int(max_history_issue[:4])
        max_history_num = int(max_history_issue[4:])

        max_pred_issue = max(predicted_issues_set)
        max_pred_year = int(max_pred_issue[:4])
        max_pred_num = int(max_pred_issue[4:])

        all_issues = []
        cur_year, cur_num = max_pred_year, max_pred_num
        while True:
            issue = f"{cur_year}{cur_num:03d}"
            if cur_year > max_history_year or (cur_year == max_history_year and cur_num > max_history_num):
                break
            if cur_year == max_pred_year and cur_num == max_pred_num:
                cur_num += 1
                if cur_num > 999:
                    cur_num = 1
                    cur_year += 1
                continue
            all_issues.append(issue)
            cur_num += 1
            if cur_num > 999:
                cur_num = 1
                cur_year += 1

        missing_issues = all_issues
        next_year, next_num = max_history_year, max_history_num + 1
        if next_num > 999:
            next_num = 1
            next_year += 1
        next_issue_new = f"{next_year}{next_num:03d}"
        need_add_next = next_issue_new not in predicted_issues_set

        if not missing_issues and not need_add_next:
            messagebox.showinfo("提示", "所有历史期号和新一期都已预测，无需补齐")
            return

        params = self.prediction_data.get("params", {})
        predictor_count = params.get("predictor_count", 0)
        front_count = params.get("front_count", 8)
        back_count = params.get("back_count", 4)

        total_issues = len(missing_issues) + (1 if need_add_next else 0)
        current_progress = 0

        def do_add():
            nonlocal current_progress
            try:
                added_count = 0

                def gen_predictors(issue_name):
                    new_preds = []
                    for pid in range(predictor_count):
                        new_preds.append(self._generate_one_predictor(pid, front_count, back_count))
                        if (pid + 1) % 500 == 0:
                            pi = int((pid + 1) / predictor_count * 100)
                            self.root.after(0, lambda p=current_progress, t=total_issues, i=issue_name, x=pi:
                                            self.status_var.set(f"正在补齐预测... {p}/{t} ({i}: {x}%)"))
                    return new_preds

                for issue in missing_issues:
                    predictions[issue] = {
                        "result": history_map.get(issue, ""),
                        "predictors": gen_predictors(issue)
                    }
                    added_count += 1
                    current_progress += 1
                    if current_progress % 5 == 0 or current_progress == total_issues:
                        self.root.after(0, lambda p=current_progress, t=total_issues:
                                        self.status_var.set(f"正在补齐预测... {p}/{t}"))

                if need_add_next:
                    predictions[next_issue_new] = {"result": "", "predictors": gen_predictors(next_issue_new)}
                    added_count += 1
                    current_progress += 1
                    self.root.after(0, lambda p=current_progress, t=total_issues:
                                    self.status_var.set(f"正在补齐预测... {p}/{t}"))
                    self.prediction_data["params"]["next_issue"] = next_issue_new

                self._save_prediction_data()
                msg = f"已补齐 {added_count} 期预测数据"
                if need_add_next:
                    msg += f"（含新一期 {next_issue_new}）"
                self.root.after(0, lambda m=msg: messagebox.showinfo("成功", m))
                self.root.after(0, lambda: self.status_var.set(f"已补齐 {added_count} 期"))
                self.root.after(0, self._refresh_saved_list)
                self.root.after(0, self._set_default_issue)
            except Exception as e:
                self.root.after(0, lambda err=str(e): messagebox.showerror("补齐预测错误", f"错误信息：{err}"))
                self.root.after(0, lambda: self.status_var.set("补齐预测失败"))

        self.status_var.set(f"正在补齐预测... 0/{total_issues}")
        threading.Thread(target=do_add, daemon=True).start()

    def _query_predictor_data(self):
        if not self.prediction_data or "predictions" not in self.prediction_data:
            messagebox.showerror("错误", "请先生成预测数据")
            return

        if self._is_legacy_data():
            messagebox.showerror(
                "数据结构不兼容",
                "检测到旧版预测数据结构（red_kill/blue），请先点击\"应用参数并生成预测数据\"重新生成。"
            )
            return

        try:
            pid = int(self.query_pid_var.get()) - 1
        except ValueError:
            messagebox.showerror("错误", "请输入有效的预测者ID")
            return

        params = self.prediction_data.get("params", {})
        predictor_count = params.get("predictor_count", 0)
        if pid < 0 or pid >= predictor_count:
            messagebox.showerror("错误", f"预测者ID必须在1-{predictor_count}之间")
            return

        predictions = self.prediction_data["predictions"]
        issues = sorted(predictions.keys(), reverse=True)

        for item in self.query_tree.get_children():
            self.query_tree.delete(item)

        for issue in issues:
            pred_data = predictions[issue]
            result_str = pred_data.get("result", "")
            predictors = pred_data["predictors"]
            if pid >= len(predictors):
                continue
            pred = predictors[pid]
            front = pred.get("front", [])
            back = pred.get("back", [])

            if result_str:
                red_result, blue_result = _parse_result(result_str)
                # 聚合命中：前区所有序号都对=对；后区所有序号都对=对（后区2个号码）
                front_hit = all(n in red_result for n in front) if front else False
                back_hit = all(n in blue_result for n in back) if back else False
                front_hit_str = "对" if front_hit else "错"
                back_hit_str = "对" if back_hit else "错"
                tags = ("hit_row",) if (front_hit and back_hit) else ()
                display_result = result_str
            else:
                front_hit_str = ""
                back_hit_str = ""
                tags = ("pending",)
                display_result = "待开奖"

            self.query_tree.insert("", tk.END, values=(
                issue, display_result,
                " ".join(f"{n:02d}" for n in front),
                " ".join(f"{n:02d}" for n in back),
                front_hit_str, back_hit_str
            ), tags=tags)

    def _refresh_results(self):
        if not self.saved_predictions:
            messagebox.showinfo("提示", "暂无保存的预测记录")
            return

        history = self.history_manager.get_all()
        history_map = {str(h["issue"]): h["number"] for h in history}

        updated_count = 0
        for rec in self.saved_predictions:
            issue = rec["issue"]
            old_result = rec.get("result", "")
            new_result = history_map.get(issue, "")

            front_remain = rec.get("front_remain", [])
            back_remain = rec.get("back_remain", [])

            if not new_result:
                if old_result:
                    rec["result"] = ""
                    rec["front_hit"] = False
                    rec["back_hit"] = False
                    updated_count += 1
            elif old_result != new_result:
                rec["result"] = new_result
                red_result, blue_result = _parse_result(new_result)
                rec["front_hit"] = all(r in front_remain for r in red_result)
                rec["back_hit"] = all(b in back_remain for b in blue_result)
                updated_count += 1

        predictions_updated = 0
        if self.prediction_data and "predictions" in self.prediction_data:
            predictions = self.prediction_data["predictions"]
            for issue, pred_data in predictions.items():
                if pred_data.get("result", "") == "" and issue in history_map:
                    pred_data["result"] = history_map[issue]
                    predictions_updated += 1
            if predictions_updated > 0:
                self._save_prediction_data()

        if updated_count > 0:
            self._save_saved_predictions()
            self._refresh_saved_list()
            messagebox.showinfo("成功", f"已同步 {updated_count} 条记录（预测数据同步 {predictions_updated} 条）")
        else:
            messagebox.showinfo("提示", "数据已是最新，无需更新")

    def _calc_prediction_stats(self):
        if not self.saved_predictions:
            messagebox.showinfo("提示", "暂无保存的预测记录")
            return

        # 预计算每期已开奖记录的命中数与奖级
        # opened: list of (rec, front_hit_count, back_hit_count, prize_level)
        opened = []
        for rec in self.saved_predictions:
            result = rec.get("result", "")
            if not result:
                continue
            red_result, blue_result = _parse_result(result)
            front_remain_set = set(rec.get("front_remain", []))
            back_remain_set = set(rec.get("back_remain", []))
            f_cnt = sum(1 for r in red_result if r in front_remain_set)
            b_cnt = sum(1 for b in blue_result if b in back_remain_set)
            prize = _dlt_prize_level(f_cnt, b_cnt)
            opened.append((rec, f_cnt, b_cnt, prize))

        total = len(opened)
        if total == 0:
            messagebox.showinfo("提示", "暂无已开奖的预测记录")
            return

        # 全命中统计（前区5个全在剩余中 / 后区2个全在剩余中）
        front_hit_count = sum(1 for _, f, _, _ in opened if f == 5)
        back_hit_count = sum(1 for _, _, b, _ in opened if b == 2)
        both_hit = sum(1 for _, f, b, _ in opened if f == 5 and b == 2)
        neither = sum(1 for _, f, b, _ in opened if f < 5 and b < 2)

        front_rate = f"{front_hit_count / total * 100:.1f}%"
        back_rate = f"{back_hit_count / total * 100:.1f}%"
        both_rate = f"{both_hit / total * 100:.1f}%"
        neither_rate = f"{neither / total * 100:.1f}%"

        stats_text = (f"已开奖 {total} 期 | "
                      f"前区全中 {front_hit_count}/{total} ({front_rate}) | "
                      f"后区全中 {back_hit_count}/{total} ({back_rate}) | "
                      f"前后区双中 {both_hit}/{total} ({both_rate}) | "
                      f"全未中 {neither}/{total} ({neither_rate})")
        self.stats_label.config(text=stats_text)

        # 奖级分布
        prize_order = ["一等奖", "二等奖", "三等奖", "四等奖", "五等奖",
                       "六等奖", "七等奖", "八等奖", "九等奖", "未中奖"]
        prize_dist = {p: 0 for p in prize_order}
        for _, _, _, prize in opened:
            prize_dist[prize] = prize_dist.get(prize, 0) + 1
        win_total = total - prize_dist.get("未中奖", 0)

        top = tk.Toplevel(self.parent)
        top.title("预测对错统计")
        top.geometry("1040x640")
        top.transient(self.parent)
        top.grab_set()

        summary_frame = ttk.LabelFrame(top, text="对错总览", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(summary_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text=f"总开奖期数：{total} 期", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text=f"前后区双中：{both_hit} 期 ({both_rate})", foreground="#d32f2f",
                  font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text=f"全未中：{neither} 期 ({neither_rate})", foreground="#388e3c",
                  font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=10)

        row2 = ttk.Frame(summary_frame)
        row2.pack(fill=tk.X, pady=(8, 2))
        ttk.Label(row2, text=f"前区全中：{front_hit_count}/{total} ({front_rate})", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text=f"后区全中：{back_hit_count}/{total} ({back_rate})", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text=f"中奖合计：{win_total}/{total} ({win_total / total * 100:.1f}%)",
                  foreground="#d32f2f", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=10)

        prize_frame = ttk.LabelFrame(top, text="奖级分布", padding=10)
        prize_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        prize_row = ttk.Frame(prize_frame)
        prize_row.pack(fill=tk.X)
        for p in prize_order:
            cnt = prize_dist.get(p, 0)
            fg = "#d32f2f" if p == "一等奖" else ("#388e3c" if p == "未中奖" else "#333333")
            ttk.Label(prize_row, text=f"{p}：{cnt}", foreground=fg,
                      font=("微软雅黑", 9, "bold" if p == "一等奖" else "normal")).pack(side=tk.LEFT, padx=8)

        list_frame = ttk.LabelFrame(top, text="详细记录", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        columns = ("issue", "front_cnt", "front_remain", "back_cnt", "back_remain", "result", "front", "back", "prize")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        tree.heading("issue", text="期号")
        tree.heading("front_cnt", text="前区个数")
        tree.heading("front_remain", text="前区剩余号码")
        tree.heading("back_cnt", text="后区个数")
        tree.heading("back_remain", text="后区剩余号码")
        tree.heading("result", text="开奖号")
        tree.heading("front", text="前区命中")
        tree.heading("back", text="后区命中")
        tree.heading("prize", text="奖级")
        tree.column("issue", width=80, anchor=tk.CENTER)
        tree.column("front_cnt", width=60, anchor=tk.CENTER)
        tree.column("front_remain", width=200, anchor=tk.CENTER)
        tree.column("back_cnt", width=60, anchor=tk.CENTER)
        tree.column("back_remain", width=90, anchor=tk.CENTER)
        tree.column("result", width=120, anchor=tk.CENTER)
        tree.column("front", width=70, anchor=tk.CENTER)
        tree.column("back", width=70, anchor=tk.CENTER)
        tree.column("prize", width=80, anchor=tk.CENTER)

        tree.tag_configure("all_hit", foreground="#d32f2f", font=("", 10, "bold"))
        tree.tag_configure("red_hit", foreground="#f57c00")
        tree.tag_configure("blue_hit", foreground="#1976d2")
        tree.tag_configure("win", foreground="#1976d2")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for rec in reversed(self.saved_predictions):
            issue = rec.get("issue", "")
            front_remain = rec.get("front_remain", [])
            back_remain = rec.get("back_remain", [])
            result = rec.get("result", "待开奖")
            has_result = bool(result) and result != "待开奖"

            if has_result:
                red_result, blue_result = _parse_result(result)
                front_remain_set = set(front_remain)
                back_remain_set = set(back_remain)
                f_cnt = sum(1 for r in red_result if r in front_remain_set)
                b_cnt = sum(1 for b in blue_result if b in back_remain_set)
                prize = _dlt_prize_level(f_cnt, b_cnt)
                f_str = f"{f_cnt}/5"
                b_str = f"{b_cnt}/2"
                p_str = prize
                # 标签：一等奖(红粗) > 前区全中(橙) > 后区全中(蓝) > 其他中奖(蓝) > 未中
                if f_cnt == 5 and b_cnt == 2:
                    tags = ("all_hit",)
                elif f_cnt == 5:
                    tags = ("red_hit",)
                elif b_cnt == 2:
                    tags = ("blue_hit",)
                elif prize != "未中奖":
                    tags = ("win",)
                else:
                    tags = ()
            else:
                f_str = ""
                b_str = ""
                p_str = ""
                tags = ()

            tree.insert("", tk.END, values=(
                issue,
                len(front_remain),
                " ".join(f"{n:02d}" for n in front_remain),
                len(back_remain),
                " ".join(f"{n:02d}" for n in back_remain),
                result,
                f_str, b_str, p_str
            ), tags=tags)

    def _calculate_kill_numbers(self):
        if not self.prediction_data or "predictions" not in self.prediction_data:
            messagebox.showerror("错误", "请先生成预测数据")
            return

        if self._is_legacy_data():
            messagebox.showerror(
                "数据结构不兼容",
                "检测到旧版预测数据结构（red_kill/blue），请先点击\"应用参数并生成预测数据\"重新生成。"
            )
            return

        try:
            min_streak_front = int(self.min_streak_front_var.get())
            min_streak_back = int(self.min_streak_back_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的连续命中期数")
            return

        if min_streak_front <= 0 or min_streak_back <= 0:
            messagebox.showerror("错误", "前区/后区最小连续命中期数必须大于0")
            return

        predictions = self.prediction_data["predictions"]
        params = self.prediction_data.get("params", {})
        predictor_count = params.get("predictor_count", 0)
        front_count = params.get("front_count", 8)
        back_count = params.get("back_count", 4)
        next_issue = params.get("next_issue", "")

        if not next_issue or next_issue not in predictions:
            messagebox.showerror("错误", "未找到下一期预测数据")
            return

        next_pred_data = predictions[next_issue]
        next_predictors = next_pred_data["predictors"]

        history_issues = sorted(
            [k for k in predictions.keys() if k != next_issue and predictions[k].get("result", "")],
            reverse=True
        )
        total_periods = len(history_issues)

        if total_periods == 0:
            messagebox.showerror("错误", "没有可用的历史预测数据用于计算")
            return

        def do_calc():
            # 预缓存每期开奖红球集合与后区号码集合，避免重复 _parse_result
            history_red = {}
            history_blue = {}
            for issue in history_issues:
                red_result, blue_result = _parse_result(predictions[issue]["result"])
                history_red[issue] = set(red_result)
                history_blue[issue] = set(blue_result)

            # 预缓存每期 predictors 列表引用，减少 dict 查找
            issue_predictors = {issue: predictions[issue]["predictors"] for issue in history_issues}

            front_kill_details = []  # (pid, seq, kill_num, streak, hit_rate)
            front_kill_set = set()
            back_kill_details = []
            back_kill_set = set()

            for pid in range(predictor_count):
                if pid >= len(next_predictors):
                    break
                next_pred = next_predictors[pid]
                next_front = next_pred.get("front", [])
                next_back = next_pred.get("back", [])

                # ---------- 前区：每个序号 i 独立计算 streak ----------
                for i in range(front_count):
                    if i >= len(next_front):
                        break
                    kill_num = next_front[i]

                    streak = 0
                    hit_count = 0
                    streak_active = True
                    for issue in history_issues:  # 已 reverse=True，从新到旧
                        predictors = issue_predictors[issue]
                        if pid >= len(predictors):
                            break
                        front_list = predictors[pid].get("front", [])
                        if i >= len(front_list):
                            break  # 该期该序号缺失，视为"错"，streak 中断
                        num = front_list[i]
                        if num in history_red[issue]:
                            hit_count += 1
                            if streak_active:
                                streak += 1
                        else:
                            streak_active = False  # streak 冻结，hit_count 后续仍可累加

                    if streak >= min_streak_front:
                        front_kill_set.add(kill_num)
                        front_kill_details.append(
                            (pid + 1, i + 1, f"{kill_num:02d}", streak, f"{hit_count}/{total_periods}")
                        )

                # ---------- 后区：每个序号 i 独立计算 streak ----------
                for i in range(back_count):
                    if i >= len(next_back):
                        break
                    kill_num = next_back[i]

                    streak = 0
                    hit_count = 0
                    streak_active = True
                    for issue in history_issues:
                        predictors = issue_predictors[issue]
                        if pid >= len(predictors):
                            break
                        back_list = predictors[pid].get("back", [])
                        if i >= len(back_list):
                            break
                        num = back_list[i]
                        if num in history_blue[issue]:
                            hit_count += 1
                            if streak_active:
                                streak += 1
                        else:
                            streak_active = False

                    if streak >= min_streak_back:
                        back_kill_set.add(kill_num)
                        back_kill_details.append(
                            (pid + 1, i + 1, f"{kill_num:02d}", streak, f"{hit_count}/{total_periods}")
                        )

                if (pid + 1) % 500 == 0:
                    self.root.after(0, lambda p=pid + 1, t=predictor_count:
                                    self.status_var.set(f"正在计算杀号... {p}/{t}"))

            # 排序：streak 降序、pid 升序、seq 升序
            front_kill_details.sort(key=lambda x: (-x[3], x[0], x[1]))
            back_kill_details.sort(key=lambda x: (-x[3], x[0], x[1]))

            front_remain = sorted(set(RED_ALL) - front_kill_set)
            back_remain = sorted(set(BLUE_ALL) - back_kill_set)

            def update_ui():
                # 前区
                for item in self.red_kill_tree.get_children():
                    self.red_kill_tree.delete(item)
                for detail in front_kill_details:
                    self.red_kill_tree.insert("", tk.END, values=detail)

                self.red_kill_label.config(
                    text=f"前区杀号对应预测期数：{total_periods}期历史 + {next_issue}期新预测 | "
                         f"杀号条目数：{len(front_kill_details)} | 去重后杀号数：{len(front_kill_set)}"
                )
                self.red_remain_label.config(text=f"前区剩余号码总数：{len(front_remain)}")
                self.red_remain_text.config(state=tk.NORMAL)
                self.red_remain_text.delete(1.0, tk.END)
                self.red_remain_text.insert(tk.END, " ".join(f"{n:02d}" for n in front_remain))
                self.red_remain_text.config(state=tk.DISABLED)

                # 后区
                for item in self.blue_pred_tree.get_children():
                    self.blue_pred_tree.delete(item)
                for detail in back_kill_details:
                    self.blue_pred_tree.insert("", tk.END, values=detail)

                self.blue_pred_label.config(
                    text=f"后区杀号对应预测期数：{total_periods}期历史 + {next_issue}期新预测 | "
                         f"杀号条目数：{len(back_kill_details)} | 去重后杀号数：{len(back_kill_set)}"
                )
                self.blue_remain_label.config(text=f"后区剩余号码总数：{len(back_remain)}")
                self.blue_remain_text.config(state=tk.NORMAL)
                self.blue_remain_text.delete(1.0, tk.END)
                self.blue_remain_text.insert(tk.END, " ".join(f"{n:02d}" for n in back_remain))
                self.blue_remain_text.config(state=tk.DISABLED)

                self.status_var.set("杀号计算完成")
                messagebox.showinfo(
                    "成功",
                    f"杀号计算完成\n前区剩余：{len(front_remain)}个\n后区剩余：{len(back_remain)}个"
                )

            self.root.after(0, update_ui)

        self.status_var.set(f"正在计算杀号... 0/{predictor_count}")
        threading.Thread(target=do_calc, daemon=True).start()

    def _save_remain_numbers(self):
        issue = self.save_issue_var.get().strip()
        if not issue:
            messagebox.showerror("错误", "请输入期号")
            return

        # 从当前 UI 读取前区剩余号码和后区剩余号码
        self.red_remain_text.config(state=tk.NORMAL)
        front_remain_str = self.red_remain_text.get(1.0, tk.END).strip()
        self.red_remain_text.config(state=tk.DISABLED)

        self.blue_remain_text.config(state=tk.NORMAL)
        back_remain_str = self.blue_remain_text.get(1.0, tk.END).strip()
        self.blue_remain_text.config(state=tk.DISABLED)

        try:
            front_remain = [int(x) for x in front_remain_str.split()]
            if not all(1 <= n <= 35 for n in front_remain):
                raise ValueError
        except Exception:
            messagebox.showerror("错误", "前区剩余号码无效，请先点击\"计算前区杀号+后区杀号\"")
            return

        try:
            back_remain = [int(x) for x in back_remain_str.split()] if back_remain_str else []
            if not all(1 <= n <= 12 for n in back_remain):
                raise ValueError
        except Exception:
            messagebox.showerror("错误", "后区剩余号码无效")
            return

        history = self.history_manager.get_all()
        history_map = {str(h["issue"]): h["number"] for h in history}
        result = history_map.get(issue, "")

        front_hit = False
        back_hit = False
        if result:
            red_result, blue_result = _parse_result(result)
            front_hit = all(r in front_remain for r in red_result)
            back_hit = all(b in back_remain for b in blue_result)

        for rec in self.saved_predictions:
            if rec["issue"] == issue:
                messagebox.showwarning("提示", f"期号 {issue} 已存在，请勿重复保存")
                return

        new_record = {
            "issue": issue,
            "front_remain": front_remain,
            "back_remain": back_remain,
            "result": result,
            "front_hit": front_hit,
            "back_hit": back_hit
        }
        self.saved_predictions.append(new_record)
        self.saved_predictions.sort(key=lambda x: x["issue"])
        self._save_saved_predictions()
        self._refresh_saved_list()
        messagebox.showinfo("成功", f"期号 {issue} 的预测结果已保存\n前区剩余：{len(front_remain)}个\n后区剩余：{len(back_remain)}个")
