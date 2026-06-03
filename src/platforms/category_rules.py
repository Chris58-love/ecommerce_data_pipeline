from src.constants import CATEGORIES
from src.utils.text_utils import normalize_col_name, normalize_text


JD_CATEGORY_RULES = [
    ("医疗器械", ["医疗", "洗牙器", "冲牙器", "洁牙仪", "牙线", "牙签", "水牙线", "超声波清洗机", "器械", "假牙清洁", "假牙清洗", "牙套清洁", "保持器清洁", "牙刷消毒器", "口腔镜", "正畸蜡", "牙菌斑显示剂"]),
    ("漱口水/护理用品", ["漱口水", "口腔喷雾", "口气清新", "口喷", "美白贴", "美白牙贴"]),
    ("牙刷", ["牙刷", "电动牙刷", "刷头"]),
    ("牙膏", ["牙膏", "牙粉", "洗牙粉"]),
    ("药物", ["药", "丸", "胶囊", "片", "含片", "清胃", "牛黄", "藿香", "龙胆", "维生素", "益生菌", "消炎", "溃疡", "牙痛"]),
]

DOUYIN_CATEGORY_DICT = {
    "牙刷": ["牙刷", "手动牙刷", "电动牙刷", "声波牙刷", "旋转牙刷", "儿童牙刷", "成人牙刷", "正畸牙刷", "软毛牙刷", "万毛牙刷", "替换刷头", "牙刷头", "刷头"],
    "牙膏": ["牙膏", "成人牙膏", "儿童牙膏", "婴童牙膏", "孕妇牙膏", "防蛀牙膏", "抗敏感牙膏", "护龈牙膏", "美白牙膏", "多效牙膏", "酵素牙膏", "牙粉", "洁牙粉", "口腔护理套装", "旅行口腔清洁护理用品"],
    "医疗器械": ["牙线", "牙线棒", "牙签", "牙缝刷", "牙间刷", "水牙线", "冲牙器", "家用冲牙器", "便携冲牙器", "超声波洗牙器", "洁牙仪", "去牙结石器", "超声波清洗机", "假牙清洗机", "牙刷消毒器", "牙刷杀菌盒", "假牙清洁片", "假牙清洁液", "义齿清洁剂", "牙套清洁片", "保持器清洁片", "牙科镜子", "口腔镜", "器", "器械", "其它口腔护理设备"],
    "药物": ["药用漱口水", "抗菌漱口水", "含氟漱口水", "治疗用", "口腔溃疡凝胶", "口腔溃疡贴", "牙痛水", "牙周炎护理液", "牙龈消炎含片", "口腔保湿凝胶", "牙本质脱敏剂", "牙齿再矿化液", "正畸蜡", "牙菌斑显示剂", "药", "溃疡", "消炎", "牙痛"],
    "漱口水/护理用品": ["漱口水", "口气清新喷雾", "口腔喷雾", "牙齿美白贴", "美白牙贴", "牙齿美白凝胶", "牙齿美白笔", "牙齿美白套装", "牙齿美白/护理剂", "舌苔刷", "舌刮器", "牙齿抛光器", "无糖口香糖", "口腔喷剂"],
}


def classify_jd_keyword(keyword: str):
    text = normalize_col_name(keyword)
    if not text:
        return "其他", 0.0, "关键词为空"
    for category, words in JD_CATEGORY_RULES:
        for word in words:
            if category == "药物" and "制药" in text:
                continue
            if normalize_col_name(word) in text:
                return category, 0.9, f"命中关键词: {word}"
    return "其他", 0.4, "规则未命中"


def classify_douyin_category(fine_category: str, title: str = ""):
    text = normalize_col_name(f"{fine_category} {title}")
    fine = normalize_col_name(fine_category)
    if not fine or fine in {"未知", "nan"}:
        return "其他", 0.2, "细分类目未知"
    for category, items in DOUYIN_CATEGORY_DICT.items():
        for item in items:
            item_norm = normalize_col_name(item)
            if fine == item_norm:
                return category, 0.95, f"词典完全匹配: {item}"
    for category, items in DOUYIN_CATEGORY_DICT.items():
        for item in items:
            item_norm = normalize_col_name(item)
            if item_norm and (item_norm in text or fine in item_norm):
                return category, 0.85, f"词典包含匹配: {item}"
    return "其他", 0.4, "规则未命中"


def accept_ai_category(result: dict, min_confidence: float = 0.70):
    category = result.get("category")
    confidence = float(result.get("confidence") or 0)
    return category in CATEGORIES and category != "其他" and confidence >= min_confidence
