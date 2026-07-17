# 八家公司PE基金定位与Gold Standard输出报告

## 1. 本周目标

本版本把康农种业案例中的人工复核经验扩展到八家公司。核心变化是：先用代码和目录/关键词定位章节，再截取相关 Markdown 文本；人工 gold 只记录 PDF 已披露事实；自动候选与人工 gold 分离并量化准确率。

## 2. 样本与输出规模

- PDF样本：8家公司。
- gold standard记录：61条。
- PE/VC或证券私募产品记录：53条。
- 员工持股平台/普通企业/未披露排除记录：8条。
- 已披露备案编码或产品编码记录：50条。
- 按“PDF未披露就留空”保留空值的记录：41条。

## 3. 公司级定位概览

| sample_id | 板块 | 公司简称 | 定位命中页数 | gold记录数 | 定位Markdown |
| --- | --- | --- | --- | --- | --- |
| MB001 | 主板 | 天和磁材 | 100 | 2 | outputs/located_markdown/MB001_positioned_sections.md |
| MB002 | 主板 | 友升股份 | 95 | 11 | outputs/located_markdown/MB002_positioned_sections.md |
| GEM001 | 创业板 | 黄山谷捷 | 67 | 2 | outputs/located_markdown/GEM001_positioned_sections.md |
| GEM002 | 创业板 | 云汉芯城 | 70 | 17 | outputs/located_markdown/GEM002_positioned_sections.md |
| STAR001 | 科创板 | 赛分科技 | 70 | 11 | outputs/located_markdown/STAR001_positioned_sections.md |
| STAR002 | 科创板 | 影石创新 | 89 | 14 | outputs/located_markdown/STAR002_positioned_sections.md |
| BSE001 | 北交所 | 三协电机 | 43 | 2 | outputs/located_markdown/BSE001_positioned_sections.md |
| BSE002 | 北交所 | 大鹏工业 | 49 | 2 | outputs/located_markdown/BSE002_positioned_sections.md |

## 4. 自动与人工对比结果

| metric | numerator | denominator | accuracy_pct |
| --- | --- | --- | --- |
| gold_records | 61 | 61 | 100.0 |
| investor_type_accuracy | 61 | 61 | 100.0 |
| filing_code_accuracy_when_pdf_disclosed | 50 | 50 | 100.0 |
| gp_name_accuracy_when_pdf_disclosed | 52 | 56 | 92.86 |
| gp_registration_code_accuracy_when_pdf_disclosed | 41 | 42 | 97.62 |
| blank_policy_records | 41 | 61 |  |

## 5. 关键工程原则

1. `investor_type` 先分类再处理：PE基金、VC基金、证券公司私募/资管产品、员工持股平台、普通企业投资人分开进入不同口径。
2. Markdown表格优先：本包将 gold 输出为 Markdown 表格，并保留 MinerU Markdown 输入接口；后续有 MinerU 原始 `.md` 时无需再走 JSON。
3. 精准截取替代全量PDF投喂：`outputs/located_markdown/` 只保存相关命中页，报告和提示词都基于这些截取页。
4. PDF未披露就留空：例如天和磁材披露中车泛海、同历宏阳已备案，但未披露备案编码，因此编码字段留空并写入 `blank_reason`。

## 6. 失败与边界案例

- 黄山谷捷：黄山佳捷是员工持股平台，且PDF明确说明机构股东不属于私募投资基金，不应为了凑PE记录而强行标注。
- 大鹏工业：普拉特是员工持股平台，融汇工创在定位页未披露PE/VC属性，因此一个排除、一个保留空值。
- 赛分科技：高新同华名称含创业投资历史，但PDF披露中基协备案状态为未备案，因此不能归入已备案PE基金。
- 天和磁材：PDF披露私募基金股东已备案，但未在定位页披露备案编码和GP登记编号，必须留空。

## 7. 后续改进

下一步应把 MinerU 正式 Markdown 输出放入 `data/mineru_markdown/`，用本脚本的 Markdown 表格解析接口读取；同时针对投资人很多的公司增加 LP 结构子表，避免把 LP 错当直接投资人。
