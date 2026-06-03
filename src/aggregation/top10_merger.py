import pandas as pd


OUTPUT_COLUMNS = [
    "平台", "主题关键词", "指标类型", "月份", "排名", "关键词", "原始值", "排序值",
    "搜索人数", "搜索次数", "点击人数", "点击次数", "点击率", "成交金额", "成交单量",
    "成交转化率", "在线商品数", "来源文件", "来源工作表",
]


def merge_top10(jd_top10_dfs=None, jd_keyword: str = "") -> pd.DataFrame:
    rows = []
    for metric, df in (jd_top10_dfs or {}).items():
        if df is None or df.empty:
            continue
        frame = df.copy()
        frame.insert(0, "指标类型", metric)
        frame.insert(0, "主题关键词", jd_keyword)
        frame.insert(0, "平台", "jd")
        for col in OUTPUT_COLUMNS:
            if col not in frame.columns:
                frame[col] = ""
        rows.append(frame[OUTPUT_COLUMNS])
    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.concat(rows, ignore_index=True)
