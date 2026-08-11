import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.messagebox import showwarning, showinfo, askyesno
from datetime import datetime
from utils.history_manager import HistoryManager


def _calc_attrs(red, blue):
    """根据前区列表(5个int)和后区列表(2个int)计算所有属性。"""
    red_sorted = sorted(red)
    sum_val = sum(red_sorted)
    span = red_sorted[-1] - red_sorted[0]

    odd = sum(1 for n in red_sorted if n % 2 == 1)
    even = 5 - odd
    odd_even = f"{odd}:{even}"

    small = sum(1 for n in red_sorted if n <= 17)
    big = 5 - small
    big_small = f"{small}:{big}"

    z1 = sum(1 for n in red_sorted if 1 <= n <= 12)
    z2 = sum(1 for n in red_sorted if 13 <= n <= 23)
    z3 = sum(1 for n in red_sorted if 24 <= n <= 35)
    zones = f"{z1}:{z2}:{z3}"

    consec = _consecutive_type(red_sorted)
    return {
        "sum": sum_val,
        "span": span,
        "odd_even": odd_even,
        "big_small": big_small,
        "zones": zones,
        "consecutive": consec,
    }


def _consecutive_type(red_sorted):
    """返回连号类型：无连号/2连/3连/4连+。"""
    runs = []
    run_len = 1
    for i in range(1, len(red_sorted)):
        if red_sorted[i] - red_sorted[i - 1] == 1:
            run_len += 1
        else:
            if run_len >= 2:
                runs.append(run_len)
            run_len = 1
    if run_len >= 2:
        runs.append(run_len)

    if not runs:
        return "无连号"
    max_run = max(runs)
    if max_run >= 4:
        return "4连+"
    if max_run == 3:
        return "3连"
    return "2连"


def _format_red(red):
    return " ".join(f"{n:02d}" for n in sorted(red))


def _format_blue(blue):
    """后区2个号码，空格分隔。"""
    if isinstance(blue, list):
        return " ".join(f"{n:02d}" for n in sorted(blue))
    return f"{blue:02d}"


def _parse_number_str(number_str):
    """解析 'r1,r2,r3,r4,r5|b1,b2' 字符串，返回 (red_list, blue_list) 或 None。"""
    try:
        if "|" not in number_str:
            return None
        red_part, blue_part = number_str.split("|", 1)
        red = [int(x) for x in red_part.split(",")]
        blue = [int(x) for x in blue_part.split(",")]
        if len(red) != 5 or len(set(red)) != 5:
            return None
        if any(not (1 <= n <= 35) for n in red):
            return None
        if len(blue) != 2 or len(set(blue)) != 2:
            return None
        if any(not (1 <= n <= 12) for n in blue):
            return None
        return red, blue
    except Exception:
        return None


class HistoryQuery:
    def __init__(self, parent):
        self.parent = parent
        self.history_manager = HistoryManager()
        self._build_ui()

    def _build_ui(self):
        add_frame = ttk.LabelFrame(self.parent, text="添加开奖记录", padding=10)
        add_frame.pack(fill=tk.X, padx=10, pady=10)

        row1 = ttk.Frame(add_frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="期号：").pack(side=tk.LEFT, padx=5)
        self.history_issue_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.history_issue_var, width=12).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="前区(1-35，5个，空格分隔)：").pack(side=tk.LEFT, padx=5)
        self.history_red_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.history_red_var, width=28).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="后区(1-12，2个)：").pack(side=tk.LEFT, padx=5)
        self.history_blue_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.history_blue_var, width=10).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="日期：").pack(side=tk.LEFT, padx=5)
        self.history_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(row1, textvariable=self.history_date_var, width=12).pack(side=tk.LEFT, padx=5)

        btn_row = ttk.Frame(add_frame)
        btn_row.pack(fill=tk.X, pady=5)
        tk.Button(btn_row, text="  ➕ 添加记录  ", bg="#5cb85c", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._add_history_record).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="  📥 批量导入  ", bg="#5bc0de", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._batch_import_history).pack(side=tk.LEFT, padx=6)

        search_frame = ttk.LabelFrame(self.parent, text="搜索查询", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        search_row = ttk.Frame(search_frame)
        search_row.pack(fill=tk.X, pady=5)

        ttk.Label(search_row, text="搜索前区(空格分隔)：").pack(side=tk.LEFT, padx=5)
        self.search_number_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.search_number_var, width=22).pack(side=tk.LEFT, padx=5)

        ttk.Label(search_row, text="期号范围：").pack(side=tk.LEFT, padx=5)
        self.search_issue_start_var = tk.StringVar()
        self.search_issue_end_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.search_issue_start_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(search_row, text="-").pack(side=tk.LEFT)
        ttk.Entry(search_row, textvariable=self.search_issue_end_var, width=10).pack(side=tk.LEFT, padx=2)

        ttk.Label(search_row, text="按年查询：").pack(side=tk.LEFT, padx=5)
        self.search_year_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.search_year_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(search_row, text="(如 2024)").pack(side=tk.LEFT)

        tk.Button(search_row, text="  🔍 搜索  ", bg="#337ab7", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._search_history).pack(side=tk.LEFT, padx=10)
        tk.Button(search_row, text="  📋 显示全部  ", bg="#f0ad4e", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._show_all_history).pack(side=tk.LEFT, padx=6)
        tk.Button(search_row, text="  📊 统计分析  ", bg="#5bc0de", fg="white",
                  relief=tk.RAISED, padx=5, pady=3, font=("微软雅黑", 9),
                  command=self._analyze_history).pack(side=tk.LEFT, padx=6)

        list_frame = ttk.LabelFrame(self.parent, text="历史记录", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("期号", "前区", "后区", "日期", "和值", "跨度", "奇偶", "大小", "三区", "连号")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)

        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=80, anchor="center")

        self.history_tree.column("期号", width=90)
        self.history_tree.column("前区", width=170)
        self.history_tree.column("后区", width=70)
        self.history_tree.column("日期", width=100)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=tree_scroll.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        del_btn_frame = ttk.Frame(list_frame)
        del_btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(del_btn_frame, text="  🗑 删除选中  ", bg="#d9534f", fg="white",
                  relief=tk.RAISED, padx=5, pady=2, font=("微软雅黑", 9),
                  command=self._delete_history_record).pack(side=tk.LEFT, padx=6)
        tk.Button(del_btn_frame, text="  ⚠ 清空全部  ", bg="#777", fg="white",
                  relief=tk.RAISED, padx=5, pady=2, font=("微软雅黑", 9),
                  command=self._clear_all_history).pack(side=tk.LEFT, padx=6)

        self._refresh_history_list()

    def _parse_red_input(self, text):
        """解析前区输入，返回 list[int] 或 None。"""
        try:
            nums = [int(x) for x in text.replace(",", " ").split()]
            if len(nums) != 5 or len(set(nums)) != 5:
                return None
            if any(not (1 <= n <= 35) for n in nums):
                return None
            return nums
        except Exception:
            return None

    def _parse_blue_input(self, text):
        """解析后区输入，返回 list[int] 或 None。"""
        try:
            nums = [int(x) for x in text.replace(",", " ").split()]
            if len(nums) != 2 or len(set(nums)) != 2:
                return None
            if any(not (1 <= n <= 12) for n in nums):
                return None
            return nums
        except Exception:
            return None

    def _add_history_record(self):
        issue = self.history_issue_var.get().strip()
        red_text = self.history_red_var.get().strip()
        blue_text = self.history_blue_var.get().strip()
        date = self.history_date_var.get().strip()

        if not issue:
            showwarning("提示", "请输入期号")
            return
        red = self._parse_red_input(red_text)
        if red is None:
            showwarning("提示", "前区需输入5个1-35的不重复数字（空格分隔）")
            return
        blue = self._parse_blue_input(blue_text)
        if blue is None:
            showwarning("提示", "后区需输入2个1-12的不重复数字（空格分隔）")
            return

        attrs = _calc_attrs(red, blue)
        record = {
            "issue": issue,
            "number": f"{','.join(str(n) for n in sorted(red))}|{','.join(str(n) for n in sorted(blue))}",
            "red": sorted(red),
            "blue": sorted(blue),
            "date": date,
            **attrs,
        }

        success, msg = self.history_manager.add_record(record)
        if success:
            self._refresh_history_list()
            self.history_issue_var.set("")
            self.history_red_var.set("")
            self.history_blue_var.set("")
            showinfo("成功", f"已添加期号 {issue}：{_format_red(red)} + {_format_blue(blue)}")
        else:
            showwarning("提示", msg)

    def _batch_import_history(self):
        import_window = tk.Toplevel(self.parent)
        import_window.title("批量导入开奖历史")
        import_window.geometry("560x420")

        ttk.Label(import_window, text="每行格式：期号,r1,r2,r3,r4,r5,b1,b2,日期", font=("Arial", 10)).pack(pady=10)
        ttk.Label(import_window, text="示例：2024001,1,5,12,18,25,7,9,2024-01-01", foreground="gray").pack()
        ttk.Label(import_window, text="（日期可省略，默认今天）", foreground="gray").pack()

        import_text = scrolledtext.ScrolledText(import_window, width=60, height=18, font=("Arial", 10))
        import_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def do_import():
            content = import_text.get(1.0, tk.END).strip()
            if not content:
                showwarning("提示", "请输入要导入的记录")
                return

            lines = content.splitlines()
            records = []
            for line in lines:
                parts = line.strip().split(',')
                if len(parts) < 8:
                    continue
                try:
                    issue = parts[0].strip()
                    red = [int(x) for x in parts[1:6]]
                    blue = [int(x) for x in parts[6:8]]
                    date = parts[8].strip() if len(parts) > 8 else datetime.now().strftime("%Y-%m-%d")
                    if len(red) != 5 or len(set(red)) != 5:
                        continue
                    if any(not (1 <= n <= 35) for n in red):
                        continue
                    if len(blue) != 2 or len(set(blue)) != 2:
                        continue
                    if any(not (1 <= n <= 12) for n in blue):
                        continue
                    attrs = _calc_attrs(red, blue)
                    records.append({
                        "issue": issue,
                        "number": f"{','.join(str(n) for n in sorted(red))}|{','.join(str(n) for n in sorted(blue))}",
                        "red": sorted(red),
                        "blue": sorted(blue),
                        "date": date,
                        **attrs,
                    })
                except Exception:
                    continue

            added_count = self.history_manager.batch_add(records)
            if added_count > 0:
                self._refresh_history_list()
                showinfo("成功", f"成功导入 {added_count} 条记录")
                import_window.destroy()
            else:
                showwarning("提示", "没有有效记录被导入")

        ttk.Button(import_window, text="导入", command=do_import).pack(pady=10)

    def _delete_history_record(self):
        selected = self.history_tree.selection()
        if not selected:
            showwarning("提示", "请先选中要删除的记录")
            return

        if askyesno("确认", "确定要删除选中的记录吗？"):
            for item in selected:
                issue = self.history_tree.item(item)["values"][0]
                self.history_manager.delete_record(issue)
            self._refresh_history_list()
            showinfo("成功", "已删除选中记录")

    def _clear_all_history(self):
        if not self.history_manager.get_all():
            showwarning("提示", "历史记录已为空")
            return

        if askyesno("确认", "确定要清空全部历史记录吗？此操作不可恢复！"):
            self.history_manager.clear_all()
            self._refresh_history_list()
            showinfo("成功", "已清空全部历史记录")

    def _search_history(self):
        search_red_text = self.search_number_var.get().strip()
        issue_start = self.search_issue_start_var.get().strip()
        issue_end = self.search_issue_end_var.get().strip()
        search_year = self.search_year_var.get().strip()

        search_red = None
        if search_red_text:
            search_red = self._parse_red_input(search_red_text)
            if search_red is None:
                showwarning("提示", "搜索前区需为5个1-35不重复数字")
                return
            search_red = sorted(search_red)

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for record in self.history_manager.get_all():
            match = True
            if search_red is not None:
                rec_red = sorted(record.get("red", []))
                if rec_red != search_red:
                    match = False
            if issue_start and record["issue"] < issue_start:
                match = False
            if issue_end and record["issue"] > issue_end:
                match = False
            if search_year:
                issue_year = str(record["issue"])[:4]
                if issue_year != search_year:
                    match = False
            if match:
                self._insert_tree_record(record)

    def _show_all_history(self):
        self.search_number_var.set("")
        self.search_issue_start_var.set("")
        self.search_issue_end_var.set("")
        self.search_year_var.set("")
        self._refresh_history_list()

    def _insert_tree_record(self, record):
        self.history_tree.insert("", tk.END, values=(
            record["issue"],
            _format_red(record.get("red", [])),
            _format_blue(record.get("blue", [])),
            record["date"],
            record.get("sum", 0),
            record.get("span", 0),
            record.get("odd_even", "-"),
            record.get("big_small", "-"),
            record.get("zones", "-"),
            record.get("consecutive", "-"),
        ))

    def _refresh_history_list(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for record in self.history_manager.get_all():
            self._insert_tree_record(record)

    def _analyze_history(self):
        if not self.history_manager.get_all():
            showwarning("提示", "暂无历史数据，请先添加开奖记录")
            return

        analyze_window = tk.Toplevel(self.parent)
        analyze_window.title("历史数据分析")
        analyze_window.geometry("780x680")

        range_frame = ttk.LabelFrame(analyze_window, text="统计范围", padding=10)
        range_frame.pack(fill=tk.X, padx=10, pady=10)

        range_row = ttk.Frame(range_frame)
        range_row.pack(fill=tk.X, pady=5)

        ttk.Label(range_row, text="期号范围：").pack(side=tk.LEFT, padx=5)
        analyze_issue_start_var = tk.StringVar()
        analyze_issue_end_var = tk.StringVar()
        ttk.Entry(range_row, textvariable=analyze_issue_start_var, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(range_row, text="-").pack(side=tk.LEFT)
        ttk.Entry(range_row, textvariable=analyze_issue_end_var, width=12).pack(side=tk.LEFT, padx=2)

        ttk.Label(range_row, text="按年统计：").pack(side=tk.LEFT, padx=10)
        analyze_year_var = tk.StringVar()
        ttk.Entry(range_row, textvariable=analyze_year_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(range_row, text="(如 2024)").pack(side=tk.LEFT)

        def do_analyze():
            issue_start = analyze_issue_start_var.get().strip()
            issue_end = analyze_issue_end_var.get().strip()
            analyze_year = analyze_year_var.get().strip()

            filtered_data = self.history_manager.get_all().copy()
            if issue_start:
                filtered_data = [r for r in filtered_data if str(r["issue"]) >= issue_start]
            if issue_end:
                filtered_data = [r for r in filtered_data if str(r["issue"]) <= issue_end]
            if analyze_year:
                filtered_data = [r for r in filtered_data if str(r["issue"])[:4] == analyze_year]

            if not filtered_data:
                showwarning("提示", "没有符合条件的数据")
                return

            total_count = len(filtered_data)

            red_freq = {i: 0 for i in range(1, 36)}
            blue_freq = {i: 0 for i in range(1, 13)}
            sum_freq = {}
            span_freq = {}
            odd_even_freq = {}
            big_small_freq = {}
            zones_freq = {}
            consec_freq = {}

            for record in filtered_data:
                red = record.get("red", [])
                blue = record.get("blue", [])
                if not isinstance(blue, list):
                    blue = [blue]
                for n in red:
                    if 1 <= n <= 35:
                        red_freq[n] += 1
                for n in blue:
                    if 1 <= n <= 12:
                        blue_freq[n] += 1
                sum_freq[record.get("sum", 0)] = sum_freq.get(record.get("sum", 0), 0) + 1
                span_freq[record.get("span", 0)] = span_freq.get(record.get("span", 0), 0) + 1
                oe = record.get("odd_even", "-")
                odd_even_freq[oe] = odd_even_freq.get(oe, 0) + 1
                bs = record.get("big_small", "-")
                big_small_freq[bs] = big_small_freq.get(bs, 0) + 1
                zn = record.get("zones", "-")
                zones_freq[zn] = zones_freq.get(zn, 0) + 1
                cc = record.get("consecutive", "-")
                consec_freq[cc] = consec_freq.get(cc, 0) + 1

            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, "=" * 60 + "\n")
            range_desc = "全部"
            if issue_start or issue_end:
                range_desc = f"{issue_start or '开始'} ~ {issue_end or '结束'}"
            if analyze_year:
                range_desc = f"{analyze_year}年"
            result_text.insert(tk.END, f"大乐透历史数据统计（范围：{range_desc}，共 {total_count} 期）\n")
            result_text.insert(tk.END, "=" * 60 + "\n\n")

            result_text.insert(tk.END, "【前区出现频率（1-35）】\n")
            for i in range(1, 36):
                count = red_freq.get(i, 0)
                pct = count / total_count * 100 if total_count > 0 else 0
                result_text.insert(tk.END, f"{i:02d}({count},{pct:.1f}%) ")
                if i % 7 == 0:
                    result_text.insert(tk.END, "\n")
            result_text.insert(tk.END, "\n\n")

            result_text.insert(tk.END, "【后区出现频率（1-12）】\n")
            for i in range(1, 13):
                count = blue_freq.get(i, 0)
                pct = count / total_count * 100 if total_count > 0 else 0
                result_text.insert(tk.END, f"{i:02d}({count},{pct:.1f}%) ")
                if i % 6 == 0:
                    result_text.insert(tk.END, "\n")
            result_text.insert(tk.END, "\n\n")

            def print_dist(title, freq_dict, sort_key=None):
                result_text.insert(tk.END, f"【{title}】\n")
                items = sorted(freq_dict.items(), key=sort_key if sort_key else lambda x: -x[1])
                for k, v in items:
                    pct = v / total_count * 100 if total_count > 0 else 0
                    result_text.insert(tk.END, f"  {k}：{v} 次 ({pct:.1f}%)\n")
                result_text.insert(tk.END, "\n")

            print_dist("奇偶比分布", odd_even_freq)
            print_dist("大小比分布", big_small_freq)
            print_dist("三区比分布", zones_freq)
            print_dist("连号分布", consec_freq)

            result_text.insert(tk.END, "【和值分布（前10高频）】\n")
            for k, v in sorted(sum_freq.items(), key=lambda x: -x[1])[:10]:
                pct = v / total_count * 100 if total_count > 0 else 0
                result_text.insert(tk.END, f"  和值 {k}：{v} 次 ({pct:.1f}%)\n")
            result_text.insert(tk.END, "\n")

            result_text.insert(tk.END, "【跨度分布】\n")
            for k in sorted(span_freq.keys()):
                v = span_freq[k]
                pct = v / total_count * 100 if total_count > 0 else 0
                result_text.insert(tk.END, f"  跨度 {k}：{v} 次 ({pct:.1f}%)\n")
            result_text.insert(tk.END, "\n" + "=" * 60 + "\n分析完成！\n")

        ttk.Button(range_row, text="开始统计", command=do_analyze).pack(side=tk.RIGHT, padx=10)

        result_frame = ttk.Frame(analyze_window, padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        result_text = scrolledtext.ScrolledText(result_frame, width=90, height=30, font=("Consolas", 10))
        result_text.pack(fill=tk.BOTH, expand=True)

        do_analyze()
