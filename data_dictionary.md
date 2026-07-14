# 字段说明

## manual_gold.csv

| 字段 | 说明 |
|---|---|
| record_id | 人工gold记录编号 |
| company_name | 公司名称 |
| stock_code | 股票代码 |
| market | 负责市场 |
| event_type | 事件类型，例如定向发行、PE/VC持股、IPO节点、排除样本 |
| event_subject | 事件主体，例如发行人、发行人股东、子公司 |
| event_date | 事件日期或期间 |
| investor_or_party | 投资方、股东或相关主体 |
| organization_type | 机构类型 |
| issued_shares_10k | 发行股数，单位：万股 |
| price_per_share_yuan | 每股价格，单位：元/股 |
| amount_10k_yuan | 金额，单位：万元 |
| registered_capital_after_10k | 变更后注册资本，单位：万元 |
| holding_shares_10k | 持股数量，单位：万股 |
| holding_ratio_pct | 持股比例，单位：% |
| post_ipo_total_capital_10k | IPO后总股本，单位：万股 |
| source_pages | PDF证据页 |
| gold_status | keep 或 exclude |
| field_source | 字段来源：直接披露、计算、人工判断等 |
| manual_judgement | 人工判断说明 |
| note | 补充说明 |

## auto_output_candidates.csv

| 字段 | 说明 |
|---|---|
| auto_id | 自动候选编号 |
| event_type | 自动识别的事件类型 |
| event_subject | 自动识别的事件主体 |
| source_pages | 候选来源页 |
| candidate_status | 候选状态 |
| extraction_method | 抽取方法 |
| confidence | 人工设置的候选置信度，用于说明复核优先级 |
| evidence_text | 从PDF文本截取的证据片段 |

## comparison_auto_vs_manual.csv

| 字段 | 说明 |
|---|---|
| record_id | 对应manual gold记录 |
| manual_event_type | 人工事件类型 |
| manual_status | 人工状态 |
| auto_id | 对应自动候选编号 |
| auto_status | 自动候选状态 |
| match_level | 匹配层级 |
| review_comment | 复核说明 |
