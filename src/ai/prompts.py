def _json_only() -> str:
    return "你只能返回严格 JSON，不要 markdown，不要解释性文字，不要编造不存在字段。confidence 必须是 0 到 1。"


def build_platform_detection_prompt(filename, parent_dir, relative_path, sheet_names, headers, samples):
    return (
        f"{_json_only()}\n判断表格平台，只允许 jd/douyin/unknown。\n"
        f"文件名: {filename}\n父级目录: {parent_dir}\n相对路径: {relative_path}\n"
        f"sheet列表: {sheet_names}\n表头样本: {headers}\n数据样本: {samples}\n"
        '返回格式: {"platform":"jd|douyin|unknown","keyword":"","confidence":0.0,"reason":""}'
    )


def build_keyword_extraction_prompt(filename, parent_dir):
    return f'{_json_only()}\n从文件名和父级目录提取主题关键词。文件名:{filename} 父级目录:{parent_dir}\n返回 {{"keyword":"","confidence":0.0,"reason":""}}'


def build_sheet_type_detection_prompt(sheet_name, headers, samples):
    return f'{_json_only()}\n判断 sheet 类型 data/summary/instruction/empty/unknown。sheet:{sheet_name} 表头:{headers} 样本:{samples}\n返回 {{"sheet_type":"unknown","confidence":0.0,"reason":""}}'


def build_column_mapping_prompt(required_columns, actual_columns):
    return f'{_json_only()}\n从真实列名中映射字段，不能编造列名。需要字段:{required_columns} 真实列名:{actual_columns}\n返回 {{"mapping":{{}},"confidence":0.0,"reason":""}}'


def build_date_inference_prompt(filename, parent_dir, sheet_names=None, samples=None):
    return f'{_json_only()}\n推断月份，统一 YYYY-MM，无法判断返回 null。文件名:{filename} 父级目录:{parent_dir} sheet:{sheet_names} 样本:{samples}\n返回 {{"month":null,"confidence":0.0,"reason":""}}'


def build_category_review_prompt(platform, items, allowed_categories):
    return f'{_json_only()}\n对电商口腔护理类目做分类审核，只能从 {allowed_categories} 选择。平台:{platform} 待分类:{items}\n返回 {{"items":[{{"keyword":"","category":"其他","confidence":0.0,"reason":""}}]}} 或单项 {{"category":"其他","confidence":0.0,"reason":""}}'


def build_numeric_anomaly_review_prompt(field_name, samples):
    return f'{_json_only()}\n分析数值解析失败样本，仅给建议。字段:{field_name} 样本:{samples}\n返回 {{"can_auto_apply":false,"confidence":0.0,"strategy":"","reason":""}}'


def build_top10_review_prompt(records):
    return f'{_json_only()}\n检查 Top10 结果质量，只写报告不修改数据。记录:{records}\n返回 {{"issues":[],"confidence":0.0,"summary":""}}'


def build_merge_consistency_prompt(summary):
    return f'{_json_only()}\n检查京东和抖音合并一致性，只写报告。摘要:{summary}\n返回 {{"issues":[],"confidence":0.0,"summary":""}}'


def build_error_fix_prompt(errors):
    return f'{_json_only()}\n根据错误生成中文修复建议。错误:{errors}\n返回 {{"suggestions":[{{"error_type":"","reason":"","fix":""}}],"confidence":0.0}}'


def build_final_summary_prompt(stats):
    return f'{_json_only()}\n生成非技术用户可读处理摘要。统计:{stats}\n返回 {{"summary":"","confidence":0.0}}'
