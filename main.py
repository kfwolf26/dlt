import tkinter as tk
from tkinter import ttk
from modules.filter_tool import FilterTool
from modules.history_query import HistoryQuery
from modules.trend_chart import TrendChart
from modules.prediction_model import PredictionModel
from modules.location_dingdan import LocationDingDan


class DLTShrinkTool:
    def __init__(self, root):
        self.root = root
        self.root.title("大乐透过滤工具（狼奖多多）")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        filter_tab = ttk.Frame(self.notebook)
        self.notebook.add(filter_tab, text="  🎯 过滤工具  ")
        self.filter_tool = FilterTool(filter_tab)

        history_tab = ttk.Frame(self.notebook)
        self.notebook.add(history_tab, text="  📊 历史查询  ")
        self.history_query = HistoryQuery(history_tab)

        trend_tab = ttk.Frame(self.notebook)
        self.notebook.add(trend_tab, text="  📈 走势图  ")
        self.trend_chart = TrendChart(trend_tab)

        prediction_tab = ttk.Frame(self.notebook)
        self.notebook.add(prediction_tab, text="  🔮 预测模型  ")
        self.prediction_model = PredictionModel(prediction_tab)

        dingdan_tab = ttk.Frame(self.notebook)
        self.notebook.add(dingdan_tab, text="  🎯 定位定胆  ")
        self.location_dingdan = LocationDingDan(dingdan_tab)


if __name__ == "__main__":
    root = tk.Tk()
    app = DLTShrinkTool(root)
    root.mainloop()
