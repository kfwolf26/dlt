import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.messagebox import showwarning, showinfo
import itertools


# ===== 大乐透规则常量 =====
# 前区：1-35 选 5；后区：1-12 选 2
FRONT_RANGE = list(range(1, 36))   # 1-35
BACK_RANGE = list(range(1, 13))    # 1-12
FRONT_PICK = 5
BACK_PICK = 2

# 5 个前区号码的奇偶比 / 大小比（奇:偶 / 小:大）
ODD_EVEN_OPTS = ["5:0", "4:1", "3:2", "2:3", "1:4", "0:5"]
BIG_SMALL_OPTS = ["5:0", "4:1", "3:2", "2:3", "1:4", "0:5"]

# 三区比：1区(1-12) : 2区(13-23) : 3区(24-35)，共 5 个前区号码
ZONE_OPTS = [
    "5:0:0", "4:1:0", "4:0:1", "3:2:0", "3:1:1", "3:0:2",
    "2:3:0", "2:2:1", "2:1:2", "2:0:3",
    "1:4:0", "1:3:1", "1:2:2", "1:1:3", "1:0:4",
    "0:5:0", "0:4:1", "0:3:2", "0:2:3", "0:1:4", "0:0:5"
]

# 和值范围：最小 1+2+3+4+5=15，最大 31+32+33+34+35=165
SUM_RANGE = list(range(15, 166))   # 15-165
# 跨度范围：最小 5-1=4，最大 35-1=34
SPAN_RANGE = list(range(4, 35))    # 4-34


class FilterTool:
    def __init__(self, parent):
        self.parent = parent
        self.filter_vars = self._init_filter_vars()

        main_pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_pane, width=600)
        main_pane.add(left_frame, weight=1)
        left_canvas = tk.Canvas(left_frame, bg="white")
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=left_canvas.yview)
        self.filter_content = tk.Frame(left_canvas, bg="white")
        self.filter_content.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=self.filter_content, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        right_frame = ttk.Frame(main_pane, width=600)
        main_pane.add(right_frame, weight=1)
        ttk.Label(right_frame, text="过滤结果", font=("Arial", 12, "bold")).pack(pady=5)
        self.result_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        self.start_btn = tk.Button(btn_frame, text="  🚀 开始过滤  ", bg="#5cb85c", fg="white",
                                   relief=tk.RAISED, padx=5, pady=4, font=("微软雅黑", 9, "bold"),
                                   command=self.start_filter)
        self.start_btn.pack(side=tk.LEFT, padx=6)
        self.clear_btn = tk.Button(btn_frame, text="  🗑 清空条件  ", bg="#f0ad4e", fg="white",
                                   relief=tk.RAISED, padx=5, pady=4, font=("微软雅黑", 9),
                                   command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=6)
        self.help_btn = tk.Button(btn_frame, text="  💡 使用说明  ", bg="#5bc0de", fg="white",
                                   relief=tk.RAISED, padx=5, pady=4, font=("微软雅黑", 9),
                                   command=self.show_help)
        self.help_btn.pack(side=tk.RIGHT, padx=6)

        self._build_filter_ui()

    def _init_filter_vars(self):
        v = {}

        # 1. 前区定位：5个位置，每位置35个布尔
        v["front_pos"] = [[tk.BooleanVar() for _ in range(35)] for _ in range(5)]

        # 2. 前区杀号
        v["front_kill"] = [tk.BooleanVar() for _ in range(35)]

        # 3. 前区胆码
        v["front_dan"] = [tk.BooleanVar() for _ in range(35)]

        # 4. 后区杀号
        v["back_kill"] = [tk.BooleanVar() for _ in range(12)]

        # 5. 后区定胆
        v["back_dan"] = [tk.BooleanVar() for _ in range(12)]

        # 6. 和值
        v["sum_mode"] = tk.IntVar(value=1)
        v["sum_val"] = [tk.BooleanVar() for _ in range(15, 166)]

        # 7. 跨度
        v["span_mode"] = tk.IntVar(value=1)
        v["span"] = [tk.BooleanVar() for _ in range(4, 35)]

        # 8. 奇偶比
        v["oe_mode"] = tk.IntVar(value=1)
        v["oe"] = [tk.BooleanVar() for _ in ODD_EVEN_OPTS]

        # 9. 大小比
        v["bs_mode"] = tk.IntVar(value=1)
        v["bs"] = [tk.BooleanVar() for _ in BIG_SMALL_OPTS]

        # 10. 三区比
        v["zone_mode"] = tk.IntVar(value=1)
        v["zone"] = [tk.BooleanVar() for _ in ZONE_OPTS]

        # 11. 连号
        v["consec_mode"] = tk.IntVar(value=0)  # 0不过滤 1必无 2必有任意 3必有2连 4必有3连+

        # 12. 号码组（最多5组）
        v["number_group"] = []
        for _ in range(5):
            v["number_group"].append({
                "nums": [tk.BooleanVar() for _ in range(35)],
                "count": tk.StringVar(value="0")
            })

        return v

    def _build_filter_ui(self):
        # 1. 前区定位
        self._add_section_title("1. 前区定位（位置1-5，每位勾选可能号码；不勾选=不限制该位）")
        pos_container = tk.Frame(self.filter_content, bg="white")
        pos_container.pack(fill=tk.X, padx=10, pady=5)
        for pos_idx in range(5):
            row = tk.Frame(pos_container, bg="white")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"位置{pos_idx + 1}：", bg="white", width=8).pack(side=tk.LEFT)
            digit_frame = tk.Frame(row, bg="white")
            digit_frame.pack(side=tk.LEFT)
            for i in range(35):
                r = i // 12
                c = i % 12
                tk.Checkbutton(digit_frame, variable=self.filter_vars["front_pos"][pos_idx][i],
                               text=f"{i + 1:02d}", bg="white").grid(row=r, column=c, padx=1)
            btn_frame = tk.Frame(row, bg="white")
            btn_frame.pack(side=tk.LEFT, padx=10)
            ttk.Button(btn_frame, text="全选",
                       command=lambda idx=pos_idx: self._select_pos(idx, True)).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="取消",
                       command=lambda idx=pos_idx: self._select_pos(idx, False)).pack(side=tk.LEFT, padx=2)

        # 2. 前区杀号
        self._add_section_title("2. 前区杀号（勾选需要排除的前区号码1-35）")
        self._add_front_checkgroup(self.filter_content, self.filter_vars["front_kill"])

        # 3. 前区胆码
        self._add_section_title("3. 前区胆码（勾选必含的前区号码，最多5个）")
        self._add_front_checkgroup(self.filter_content, self.filter_vars["front_dan"])

        # 4. 后区杀号
        self._add_section_title("4. 后区杀号（勾选需要排除的后区号码1-12）")
        self._add_back_checkgroup(self.filter_content, self.filter_vars["back_kill"])

        # 5. 后区定胆
        self._add_section_title("5. 后区定胆（勾选必含的后区号码，最多2个）")
        self._add_back_checkgroup(self.filter_content, self.filter_vars["back_dan"])

        # 6. 和值
        self._add_section_title("6. 前区和值过滤（15-165，5个前区号码之和）")
        self._add_mode_checkgroup(self.filter_content, self.filter_vars["sum_mode"],
                                  self.filter_vars["sum_val"], SUM_RANGE, cols=12)

        # 7. 跨度
        self._add_section_title("7. 前区跨度过滤（4-34，最大前区-最小前区）")
        self._add_mode_checkgroup(self.filter_content, self.filter_vars["span_mode"],
                                  self.filter_vars["span"], SPAN_RANGE, cols=12)

        # 8. 奇偶比
        self._add_section_title("8. 奇偶比过滤（奇:偶，5个前区号码的奇偶比）")
        self._add_mode_checkgroup(self.filter_content, self.filter_vars["oe_mode"],
                                  self.filter_vars["oe"], ODD_EVEN_OPTS, cols=6)

        # 9. 大小比
        self._add_section_title("9. 大小比过滤（小:大，小=1-17，大=18-35）")
        self._add_mode_checkgroup(self.filter_content, self.filter_vars["bs_mode"],
                                  self.filter_vars["bs"], BIG_SMALL_OPTS, cols=6)

        # 10. 三区比
        self._add_section_title("10. 三区比过滤（1区1-12 : 2区13-23 : 3区24-35）")
        self._add_mode_checkgroup(self.filter_content, self.filter_vars["zone_mode"],
                                  self.filter_vars["zone"], ZONE_OPTS, cols=7)

        # 11. 连号
        self._add_section_title("11. 连号过滤")
        consec_frame = ttk.Frame(self.filter_content)
        consec_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Radiobutton(consec_frame, text="不过滤", variable=self.filter_vars["consec_mode"], value=0).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(consec_frame, text="必须无连号", variable=self.filter_vars["consec_mode"], value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(consec_frame, text="必有任意连号", variable=self.filter_vars["consec_mode"], value=2).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(consec_frame, text="必有2连", variable=self.filter_vars["consec_mode"], value=3).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(consec_frame, text="必有3连+", variable=self.filter_vars["consec_mode"], value=4).pack(side=tk.LEFT, padx=5)

        # 12. 号码组
        self._add_section_title("12. 号码组过滤（最多5组，勾选号码+指定出现次数0-5）")
        for i in range(5):
            group_frame = tk.Frame(self.filter_content, relief=tk.RAISED, borderwidth=1, bg="white")
            group_frame.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(group_frame, text=f"第{i + 1}组：", bg="white").pack(side=tk.LEFT, padx=5)
            num_frame = tk.Frame(group_frame, bg="white")
            num_frame.pack(side=tk.LEFT, padx=5)
            for j in range(35):
                r = j // 12
                c = j % 12
                tk.Checkbutton(num_frame, variable=self.filter_vars["number_group"][i]["nums"][j],
                               text=f"{j + 1:02d}", bg="white").grid(row=r, column=c, padx=1)
            tk.Label(group_frame, text="出现次数：", bg="white").pack(side=tk.LEFT, padx=5)
            ttk.Entry(group_frame, textvariable=self.filter_vars["number_group"][i]["count"], width=5).pack(side=tk.LEFT)
            tk.Label(group_frame, text="（0-5）", bg="white").pack(side=tk.LEFT)

    def _select_pos(self, pos_idx, state):
        for var in self.filter_vars["front_pos"][pos_idx]:
            var.set(state)

    def _add_section_title(self, text):
        tk.Label(self.filter_content, text=text, font=("Arial", 10, "bold"),
                 fg="#2c3e50", bg="white").pack(anchor="w", padx=10, pady=(10, 5))

    def _add_front_checkgroup(self, parent, var_list):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=10, pady=5)
        item_frame = tk.Frame(frame, bg="white")
        item_frame.pack(side=tk.TOP, padx=5, pady=5)
        for i, var in enumerate(var_list):
            r = i // 12
            c = i % 12
            tk.Checkbutton(item_frame, variable=var, text=f"{i + 1:02d}", bg="white").grid(row=r, column=c, padx=2, pady=2)
        btn_frame = tk.Frame(frame)
        btn_frame.pack(side=tk.TOP, padx=5)
        ttk.Button(btn_frame, text="全选", command=lambda: self._check_all(var_list, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=lambda: self._check_all(var_list, False)).pack(side=tk.LEFT, padx=5)

    def _add_back_checkgroup(self, parent, var_list):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=10, pady=5)
        item_frame = tk.Frame(frame, bg="white")
        item_frame.pack(side=tk.TOP, padx=5, pady=5)
        for i, var in enumerate(var_list):
            r = i // 6
            c = i % 6
            tk.Checkbutton(item_frame, variable=var, text=f"{i + 1:02d}", bg="white").grid(row=r, column=c, padx=3, pady=2)
        btn_frame = tk.Frame(frame)
        btn_frame.pack(side=tk.TOP, padx=5)
        ttk.Button(btn_frame, text="全选", command=lambda: self._check_all(var_list, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=lambda: self._check_all(var_list, False)).pack(side=tk.LEFT, padx=5)

    def _add_mode_checkgroup(self, parent, mode_var, var_list, item_list, cols=10):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=10, pady=5)
        mode_frame = tk.Frame(frame)
        mode_frame.pack(side=tk.TOP, padx=5)
        ttk.Radiobutton(mode_frame, text="排除选中", variable=mode_var, value=0).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="包含选中", variable=mode_var, value=1).pack(side=tk.LEFT, padx=5)
        item_frame = tk.Frame(frame, bg="white")
        item_frame.pack(side=tk.TOP, padx=5, pady=5)
        for idx, (item, var) in enumerate(zip(item_list, var_list)):
            r = idx // cols
            c = idx % cols
            tk.Checkbutton(item_frame, variable=var, text=str(item), bg="white").grid(row=r, column=c, padx=2, pady=2)
        btn_frame = tk.Frame(frame)
        btn_frame.pack(side=tk.TOP, padx=5)
        ttk.Button(btn_frame, text="全选", command=lambda: self._check_all(var_list, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=lambda: self._check_all(var_list, False)).pack(side=tk.LEFT, padx=5)

    def _check_all(self, var_list, state):
        for var in var_list:
            var.set(state)

    def _parse_filters(self):
        f = {}

        # 1. 前区定位
        f["front_pos"] = []
        for pos_idx in range(5):
            allowed = {i + 1 for i, var in enumerate(self.filter_vars["front_pos"][pos_idx]) if var.get()}
            f["front_pos"].append(allowed)

        # 2. 前区杀号
        f["front_kill"] = {i + 1 for i, var in enumerate(self.filter_vars["front_kill"]) if var.get()}

        # 3. 前区胆码
        f["front_dan"] = {i + 1 for i, var in enumerate(self.filter_vars["front_dan"]) if var.get()}

        # 4. 后区杀号
        f["back_kill"] = {i + 1 for i, var in enumerate(self.filter_vars["back_kill"]) if var.get()}

        # 5. 后区定胆
        f["back_dan"] = {i + 1 for i, var in enumerate(self.filter_vars["back_dan"]) if var.get()}

        # 6. 和值
        f["sum_mode"] = self.filter_vars["sum_mode"].get()
        f["sum_val"] = {i + 15 for i, var in enumerate(self.filter_vars["sum_val"]) if var.get()}

        # 7. 跨度
        f["span_mode"] = self.filter_vars["span_mode"].get()
        f["span"] = {i + 4 for i, var in enumerate(self.filter_vars["span"]) if var.get()}

        # 8. 奇偶比
        f["oe_mode"] = self.filter_vars["oe_mode"].get()
        f["oe"] = {ODD_EVEN_OPTS[i] for i, var in enumerate(self.filter_vars["oe"]) if var.get()}

        # 9. 大小比
        f["bs_mode"] = self.filter_vars["bs_mode"].get()
        f["bs"] = {BIG_SMALL_OPTS[i] for i, var in enumerate(self.filter_vars["bs"]) if var.get()}

        # 10. 三区比
        f["zone_mode"] = self.filter_vars["zone_mode"].get()
        f["zone"] = {ZONE_OPTS[i] for i, var in enumerate(self.filter_vars["zone"]) if var.get()}

        # 11. 连号
        f["consec_mode"] = self.filter_vars["consec_mode"].get()

        # 12. 号码组
        f["number_group"] = []
        for group in self.filter_vars["number_group"]:
            nums = {i + 1 for i, var in enumerate(group["nums"]) if var.get()}
            if not nums:
                continue
            cnt_str = group["count"].get().strip()
            cnt = int(cnt_str) if cnt_str.isdigit() and 0 <= int(cnt_str) <= 5 else 0
            f["number_group"].append((nums, cnt))

        return f

    def _calc_oe(self, combo):
        odd = sum(1 for n in combo if n % 2 == 1)
        return f"{odd}:{5 - odd}"

    def _calc_bs(self, combo):
        small = sum(1 for n in combo if n <= 17)
        return f"{small}:{5 - small}"

    def _calc_zones(self, combo):
        z1 = sum(1 for n in combo if 1 <= n <= 12)
        z2 = sum(1 for n in combo if 13 <= n <= 23)
        z3 = sum(1 for n in combo if 24 <= n <= 35)
        return f"{z1}:{z2}:{z3}"

    def _calc_consec(self, combo):
        runs = []
        run_len = 1
        for i in range(1, len(combo)):
            if combo[i] - combo[i - 1] == 1:
                run_len += 1
            else:
                if run_len >= 2:
                    runs.append(run_len)
                run_len = 1
        if run_len >= 2:
            runs.append(run_len)
        return runs

    def _front_combo_pass(self, combo, f):
        combo_list = list(combo)
        combo_set = set(combo)

        # 1. 前区定位
        for pos_idx in range(5):
            if f["front_pos"][pos_idx] and combo_list[pos_idx] not in f["front_pos"][pos_idx]:
                return False

        # 2. 前区杀号
        if f["front_kill"] and (combo_set & f["front_kill"]):
            return False

        # 3. 前区胆码
        if f["front_dan"] and not f["front_dan"].issubset(combo_set):
            return False

        # 4. 和值
        if f["sum_val"]:
            s = sum(combo)
            if f["sum_mode"] == 1 and s not in f["sum_val"]:
                return False
            if f["sum_mode"] == 0 and s in f["sum_val"]:
                return False

        # 5. 跨度
        if f["span"]:
            sp = combo_list[-1] - combo_list[0]
            if f["span_mode"] == 1 and sp not in f["span"]:
                return False
            if f["span_mode"] == 0 and sp in f["span"]:
                return False

        # 6. 奇偶比
        if f["oe"]:
            oe = self._calc_oe(combo)
            if f["oe_mode"] == 1 and oe not in f["oe"]:
                return False
            if f["oe_mode"] == 0 and oe in f["oe"]:
                return False

        # 7. 大小比
        if f["bs"]:
            bs = self._calc_bs(combo)
            if f["bs_mode"] == 1 and bs not in f["bs"]:
                return False
            if f["bs_mode"] == 0 and bs in f["bs"]:
                return False

        # 8. 三区比
        if f["zone"]:
            zn = self._calc_zones(combo)
            if f["zone_mode"] == 1 and zn not in f["zone"]:
                return False
            if f["zone_mode"] == 0 and zn in f["zone"]:
                return False

        # 9. 连号
        if f["consec_mode"] != 0:
            runs = self._calc_consec(combo)
            if f["consec_mode"] == 1:  # 必须无连号
                if runs:
                    return False
            elif f["consec_mode"] == 2:  # 必有任意连号
                if not runs:
                    return False
            elif f["consec_mode"] == 3:  # 必有2连（最长连=2）
                if not runs or max(runs) != 2:
                    return False
            elif f["consec_mode"] == 4:  # 必有3连+
                if not runs or max(runs) < 3:
                    return False

        # 10. 号码组
        for nums, cnt in f["number_group"]:
            actual = len(combo_set & nums)
            if actual != cnt:
                return False

        return True

    def _back_single_pass(self, b, f):
        if b in f["back_kill"]:
            return False
        if f["back_dan"] and b not in f["back_dan"]:
            return False
        return True

    def start_filter(self):
        self.result_text.delete(1.0, tk.END)
        try:
            f = self._parse_filters()

            # 胆码数量校验
            if len(f["front_dan"]) > 5:
                showwarning("提示", "前区胆码不能超过5个")
                return
            if len(f["back_dan"]) > 2:
                showwarning("提示", "后区定胆不能超过2个（后区只选2个号码）")
                return

            self._log(f"前区胆码：{sorted(f['front_dan']) if f['front_dan'] else '无'}")
            self._log(f"前区杀号：{sorted(f['front_kill']) if f['front_kill'] else '无'}")
            self._log(f"后区定胆：{sorted(f['back_dan']) if f['back_dan'] else '无'}")
            self._log(f"后区杀号：{sorted(f['back_kill']) if f['back_kill'] else '无'}")
            self._log("")

            # 1. 生成前区组合并过滤
            self._log("正在生成并过滤前区组合（共 324,632 个）...")
            self.result_text.update()

            front_combos = []
            for combo in itertools.combinations(range(1, 36), 5):
                if self._front_combo_pass(combo, f):
                    front_combos.append(combo)
            self._log(f"前区过滤后剩余：{len(front_combos)} 个组合")

            # 2. 后区过滤（从1-12选2个，先筛单号，再组合并校验定胆覆盖）
            back_candidates = [b for b in range(1, 13) if self._back_single_pass(b, f)]
            back_combos = []
            for combo in itertools.combinations(back_candidates, 2):
                if f["back_dan"] and not f["back_dan"].issubset(set(combo)):
                    continue
                back_combos.append(combo)
            self._log(f"后区过滤后剩余：{len(back_combos)} 个组合")
            if back_combos:
                self._log("  示例：" + "  ".join("+".join(f"{n:02d}" for n in c) for c in back_combos[:10]))

            # 3. 组合输出
            total = len(front_combos) * len(back_combos)
            self._log(f"\n最终注数：{total} 注")

            if total == 0:
                self._log("\n暂无符合所有条件的号码！")
            else:
                # 限制输出数量避免卡死
                show_limit = 5000
                self._log("\n" + "=" * 60)
                if total <= show_limit:
                    count = 0
                    for front in front_combos:
                        front_str = " ".join(f"{n:02d}" for n in front)
                        for back in back_combos:
                            back_str = " ".join(f"{n:02d}" for n in back)
                            self._log(f"{front_str} + {back_str}")
                            count += 1
                    self._log(f"\n共输出 {count} 注")
                else:
                    self._log(f"（数量过多（{total} 注），仅显示前 {show_limit} 注示例）")
                    count = 0
                    for front in front_combos:
                        front_str = " ".join(f"{n:02d}" for n in front)
                        for back in back_combos:
                            back_str = " ".join(f"{n:02d}" for n in back)
                            self._log(f"{front_str} + {back_str}")
                            count += 1
                            if count >= show_limit:
                                break
                        if count >= show_limit:
                            break

            self._log("\n" + "=" * 60)
            self._log("过滤完成！（注：彩票开奖随机，本工具仅为号码筛选，不保证中奖）")

        except Exception as e:
            showwarning("错误", f"过滤过程中出现异常：{str(e)}")

    def _log(self, text):
        self.result_text.insert(tk.END, text + "\n")
        self.result_text.see(tk.END)

    def clear_all(self):
        for pos in self.filter_vars["front_pos"]:
            for var in pos:
                var.set(False)
        for var in self.filter_vars["front_kill"]:
            var.set(False)
        for var in self.filter_vars["front_dan"]:
            var.set(False)
        for var in self.filter_vars["back_kill"]:
            var.set(False)
        for var in self.filter_vars["back_dan"]:
            var.set(False)

        for key in ["sum_val", "span", "oe", "bs", "zone"]:
            for var in self.filter_vars[key]:
                var.set(False)

        for key in ["sum_mode", "span_mode", "oe_mode", "bs_mode", "zone_mode"]:
            self.filter_vars[key].set(1)
        self.filter_vars["consec_mode"].set(0)

        for group in self.filter_vars["number_group"]:
            for var in group["nums"]:
                var.set(False)
            group["count"].set("0")

        self.result_text.delete(1.0, tk.END)

    def show_help(self):
        help_text = """
大乐透过滤工具使用说明：

【彩票规则】
- 前区：从1-35中选5个不重复号码
- 后区：从1-12中选2个不重复号码
- 总注数：21,425,712

【过滤条件】
1. 前区定位：勾选位置1-5每个位置的可能号码（不勾选=不限制该位）
2. 前区杀号：勾选需要排除的前区号码（前区组合中不出现这些号码）
3. 前区胆码：勾选必含的前区号码（最多5个）
4. 后区杀号：勾选需要排除的后区号码
5. 后区定胆：勾选必含的后区号码（最多2个，后区只选2个号）
6. 和值：5个前区号码之和（范围15-165）
7. 跨度：最大前区-最小前区（范围4-34）
8. 奇偶比：5个前区号码的奇:偶比（如3:2表示3奇2偶）
9. 大小比：小(1-17):大(18-35)
10. 三区比：1区(1-12):2区(13-23):3区(24-35)
11. 连号：5种模式（不过滤/必无/必有任意/必有2连/必有3连+）
12. 号码组：每组勾选号码并指定在5个前区号码中出现的精确次数（0-5）

【模式说明】
- 包含选中：仅保留命中勾选项的组合
- 排除选中：排除命中勾选项的组合

【输出】
- 结果超过5000注时仅显示前5000注示例，但会显示总数
- 输出格式：01 05 12 18 25 + 07 09

注意事项：
- 过滤条件过多可能导致无符合条件的号码
- 彩票开奖为随机事件，本工具仅为号码筛选，不保证中奖
        """
        showinfo("使用说明", help_text)
