# 八家公司PE基金定位与Gold Standard提交包

姓名：霍泓锟  
任务：八家公司招股书 PE/VC 投资人定位、`investor_type` 分类、PE基金深度字段提取与 gold standard 输出

## 核心产出

| 文件 | 说明 |
|---|---|
| `outputs/gold_standard.csv` | 人工确认后的 gold standard 主表，共 61 条记录 |
| `outputs/gold_standard.jsonl` | 便于后续导入数据库的 JSON Lines |
| `outputs/eight_company_gold_standard.xlsx` | Excel 汇总，含 gold、自动对比、准确率、PDF清单 |
| `outputs/toc_keyword_positioning.csv` | 代码定位页码和关键词命中证据 |
| `outputs/located_markdown/` | 每家公司精准截取后的 Markdown 证据页 |
| `outputs/markdown_tables/` | 由 gold 输出的 Markdown 表格，避免表格结构丢失 |
| `outputs/auto_output_candidates.csv` | 规则抽取候选结果 |
| `outputs/comparison_auto_vs_manual.csv` | 自动候选与人工 gold 的字段级对比 |
| `outputs/accuracy_report.md` | 自动/人工准确率量化报告 |
| `docs/methodology.md` | 方法说明：TOC/关键词定位、Markdown表格、分类和空值原则 |
| `docs/manual_review_guide.md` | 人工复核和双人一致性对比操作指南 |

## 一键复现

```bash
pip install -r requirements.txt
python run_pipeline.py
python code/check_submission.py
```

自检通过时会看到：

```text
SUBMISSION CHECK PASSED
Eight-company positioning, gold standard, Markdown tables and accuracy files are complete.
```

## 方法要点

1. 先通过目录/关键词定位章节，再截取相关 Markdown，不全量投喂 PDF。
2. `investor_type` 先分类，再按 PE基金、VC基金、证券公司私募、员工持股平台、普通企业投资人分别处理。
3. PE基金深度字段优先提取备案编码、基金管理人/GP、管理人登记编号、LP结构披露情况。
4. PDF 未披露的字段保持空值，并在 `blank_reason` 写明原因。
5. 自动候选与人工 gold 分开保存，用 `comparison_auto_vs_manual.csv` 量化差异。
