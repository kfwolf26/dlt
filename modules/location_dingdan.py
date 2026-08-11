import tkinter as tk
from tkinter import ttk
import random
from utils.history_manager import HistoryManager

PREDICTOR_NAMES = [
    "神算子", "好运来", "金手指", "财源广", "福星照",
    "财运通", "吉祥星", "如意宝", "聚宝盆", "鸿运达"
]


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


class LocationDingDan:
    def __init__(self, parent):
        self.parent = parent
        self.history_manager = HistoryManager()
        self.predictors = {}
        self.canvas_frames = {}
        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        tabs = [
            ("red_unpositioned", "前区不定位三胆"),
            ("red_positioned", "前区定位三胆"),
            ("blue", "后区定三胆"),
            ("red_kill", "前区杀三码")
        ]

        for tab_key, tab_name in tabs:
            tab_frame = ttk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=f"  {tab_name}  ")
            self._build_sub_tab(tab_frame, tab_key)

    def _build_sub_tab(self, parent, tab_key):
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(control_frame, text="统计期数：").pack(side=tk.LEFT, padx=(0, 5))
        period_var = tk.StringVar(value="25")
        ttk.Entry(control_frame, textvariable=period_var, width=8).pack(side=tk.LEFT, padx=(0, 10))

        # 前区定位三胆需要选择位置（前区5个号码，位置1-5）
        pos_var = None
        if tab_key == "red_positioned":
            ttk.Label(control_frame, text="定位位置：").pack(side=tk.LEFT, padx=(10, 5))
            pos_var = tk.IntVar(value=1)
            for i in range(1, 6):
                ttk.Radiobutton(control_frame, text=str(i), variable=pos_var, value=i).pack(side=tk.LEFT, padx=2)

        self.predictors[tab_key] = {
            "period_var": period_var,
            "pos_var": pos_var,
            "data": {}
        }

        tk.Button(control_frame, text="  🔄 刷新  ", bg="#5bc0de", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=lambda k=tab_key: self._refresh_tab(k)).pack(side=tk.LEFT, padx=5)

        result_frame = ttk.LabelFrame(parent, text="预测结果", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        canvas = tk.Canvas(result_frame, bg="white")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        table_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=table_frame, anchor=tk.NW)

        table_frame.bind("<Configure>", lambda e, c=canvas: self._on_frame_configure(c))

        self.canvas_frames[tab_key] = {
            "canvas": canvas,
            "table_frame": table_frame,
            "labels": []
        }

        self._refresh_tab(tab_key)

    def _on_frame_configure(self, canvas):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _get_next_issue(self):
        history = self.history_manager.get_all()
        if not history:
            return ""
        history.sort(key=lambda x: str(x["issue"]), reverse=True)
        latest_issue = str(history[0]["issue"])
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

    def _refresh_tab(self, tab_key):
        history = self.history_manager.get_all()
        if not history:
            self._clear_table(tab_key)
            return

        history.sort(key=lambda x: str(x["issue"]), reverse=False)

        try:
            periods = int(self.predictors[tab_key]["period_var"].get())
        except ValueError:
            periods = 25

        recent_history = history[-periods:] if len(history) > periods else history

        all_data = {}
        for record in recent_history:
            issue = str(record["issue"])
            result_num = record["number"]
            predictors_data = self._generate_predictors_for_period(tab_key, result_num)
            all_data[issue] = {
                "result": result_num,
                "predictors": predictors_data
            }

        next_issue = self._get_next_issue()
        if next_issue:
            all_data[next_issue] = {
                "result": "",
                "predictors": self._generate_predictors_for_period(tab_key, "")
            }

        self.predictors[tab_key]["data"] = all_data
        self._display_results(tab_key)

    def _generate_predictors_for_period(self, tab_key, result_str):
        """根据 tab 类型生成预测者的3个号码 + 命中情况。"""
        predictors_data = []
        red_result, blue_result = _parse_result(result_str) if result_str else ([], [])
        blue_result_set = set(blue_result) if isinstance(blue_result, list) else ({blue_result} if blue_result else set())

        pos_idx = 1
        if tab_key == "red_positioned" and self.predictors.get(tab_key, {}).get("pos_var"):
            pos_idx = self.predictors[tab_key]["pos_var"].get()

        for i in range(10):
            name = PREDICTOR_NAMES[i]
            hit_numbers = []

            if tab_key == "red_unpositioned":
                # 从1-35选3个前区胆码，命中=任一胆码在5个前区号码中
                numbers = sorted(random.sample(range(1, 36), 3))
                if red_result:
                    hit_numbers = [n for n in numbers if n in red_result]

            elif tab_key == "red_positioned":
                # 给指定位置出3个候选号，命中=该位置前区号码∈候选（前区5个号码，位置1-5）
                numbers = sorted(random.sample(range(1, 36), 3))
                if red_result and 1 <= pos_idx <= 5:
                    target = red_result[pos_idx - 1]
                    hit_numbers = [n for n in numbers if n == target]

            elif tab_key == "blue":
                # 从1-12选3个后区候选，命中=候选号在2个后区号码中
                numbers = sorted(random.sample(range(1, 13), 3))
                if blue_result_set:
                    hit_numbers = [n for n in numbers if n in blue_result_set]

            elif tab_key == "red_kill":
                # 从1-35选3个前区杀号，命中=3个杀号均不在5个前区号码中
                numbers = sorted(random.sample(range(1, 36), 3))
                if red_result:
                    if all(n not in red_result for n in numbers):
                        hit_numbers = numbers  # 全部命中（杀号全错=预测对）

            predictors_data.append({
                "name": name,
                "numbers": numbers,
                "hit_numbers": hit_numbers
            })

        return predictors_data

    def _display_results(self, tab_key):
        self._clear_table(tab_key)
        table_frame = self.canvas_frames[tab_key]["table_frame"]
        labels = []

        header_font = ("微软雅黑", 9, "bold")
        cell_font = ("微软雅黑", 9)

        row = 0
        ttk.Label(table_frame, text="期号", font=header_font, width=10, anchor=tk.CENTER).grid(row=row, column=0, padx=2, pady=2, sticky="nsew")
        ttk.Label(table_frame, text="开奖号", font=header_font, width=14, anchor=tk.CENTER).grid(row=row, column=1, padx=2, pady=2, sticky="nsew")

        col = 2
        for idx, name in enumerate(PREDICTOR_NAMES):
            ttk.Label(table_frame, text=name, font=header_font, width=15, anchor=tk.CENTER).grid(row=row, column=col, columnspan=3, padx=2, pady=2, sticky="nsew")
            col += 3
            if idx < len(PREDICTOR_NAMES) - 1:
                sep = ttk.Separator(table_frame, orient='vertical')
                sep.grid(row=row, column=col, sticky='ns', padx=1)
                col += 1

        ttk.Label(table_frame, text="统计概况", font=header_font, width=10, anchor=tk.CENTER).grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

        row += 1

        data = self.predictors[tab_key]["data"]
        for issue in sorted(data.keys()):
            record = data[issue]
            result_num = record["result"]
            is_next = result_num == ""

            if is_next:
                ttk.Label(table_frame, text=issue, font=("微软雅黑", 9, "bold"), width=10, anchor=tk.CENTER, foreground="#f57c00").grid(row=row, column=0, padx=2, pady=2, sticky="nsew")
                ttk.Label(table_frame, text="待开奖", font=("微软雅黑", 9, "bold"), width=14, anchor=tk.CENTER, foreground="#f57c00").grid(row=row, column=1, padx=2, pady=2, sticky="nsew")
            else:
                ttk.Label(table_frame, text=issue, font=cell_font, width=10, anchor=tk.CENTER).grid(row=row, column=0, padx=2, pady=2, sticky="nsew")
                ttk.Label(table_frame, text=result_num, font=cell_font, width=14, anchor=tk.CENTER, foreground="#1976d2").grid(row=row, column=1, padx=2, pady=2, sticky="nsew")

            col = 2
            total_hits = 0
            for idx, pred in enumerate(record["predictors"]):
                numbers = pred["numbers"]
                hit_numbers = pred["hit_numbers"]

                for num in numbers:
                    if num in hit_numbers:
                        lbl = tk.Label(table_frame, text=f"{num:02d}", font=cell_font, width=5, anchor=tk.CENTER, foreground="#d32f2f")
                        total_hits += 1
                    else:
                        lbl = tk.Label(table_frame, text=f"{num:02d}", font=cell_font, width=5, anchor=tk.CENTER, foreground="#333333")
                    lbl.grid(row=row, column=col, padx=1, pady=2, sticky="nsew")
                    labels.append(lbl)
                    col += 1

                if idx < len(record["predictors"]) - 1:
                    sep = ttk.Separator(table_frame, orient='vertical')
                    sep.grid(row=row, column=col, sticky='ns', padx=1)
                    col += 1

            ttk.Label(table_frame, text=str(total_hits), font=cell_font, width=10, anchor=tk.CENTER).grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

            row += 1

        self.canvas_frames[tab_key]["labels"] = labels

        canvas = self.canvas_frames[tab_key]["canvas"]
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _clear_table(self, tab_key):
        table_frame = self.canvas_frames[tab_key]["table_frame"]
        for widget in table_frame.winfo_children():
            widget.destroy()
        self.canvas_frames[tab_key]["labels"] = []
