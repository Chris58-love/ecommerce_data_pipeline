import pandas as pd


OUTPUT_COLUMNS = [
    "平台", "主题关键词", "时间", "分类名", "销量", "销售额", "浏览量", "订单量",
    "搜索人数_clean", "搜索次数_clean", "点击人数_clean", "点击次数_clean",
    "成交金额_clean", "成交单量_clean", "在线商品数_clean", "来源文件",
]


def merge_five_level(jd_df=None, douyin_df=None) -> pd.DataFrame:
    frames = []
    for df in [jd_df, douyin_df]:
        if df is None or df.empty:
            continue
        frame = df.copy()
        for col in OUTPUT_COLUMNS:
            if col not in frame.columns:
                frame[col] = 0 if col not in {"平台", "主题关键词", "时间", "分类名", "来源文件"} else ""
        frames.append(frame[OUTPUT_COLUMNS])
    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    result = pd.concat(frames, ignore_index=True)
    numeric_cols = [col for col in OUTPUT_COLUMNS if col not in {"平台", "主题关键词", "时间", "分类名", "来源文件"}]
    for col in numeric_cols:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0)
    return result
