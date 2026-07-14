# 作业提交说明

本次提交选择康农种业作为单公司深讲样本，目标是形成一个高质量闭环，而不是铺开大量公司后留下大范围缺失。

## 已完成内容

- PDF原文：`data/raw/kangnong_prospectus.pdf`
- 人工gold：`data/manual_gold/kangnong_manual_gold.csv`
- 可复现代码：`code/kangnong_pipeline.py`
- 一键运行入口：`run_pipeline.py`
- 自动候选输出：`outputs/auto_output_candidates.csv`
- 人工与自动对比：`outputs/comparison_auto_vs_manual.csv`
- 数值闭合报告：`outputs/validation_report.md`
- PDF证据截图：`evidence/screenshots/`
- 展示问答口径：`outputs/teacher_discussion_questions.md`

## 与老师反馈的对应关系

| 老师反馈关注点 | 本提交如何回应 |
|---|---|
| gold是否可信 | manual_gold只放回到PDF确认的记录，并保留source_pages |
| auto和manual是否分开 | 分为manual_gold、auto_output、comparison三层 |
| 是否能从PDF开始复现 | run_pipeline.py从PDF抽关键页文本，再生成候选和校验 |
| 是否保留失败案例 | 第159页作为子公司股权变化误判样本，状态为exclude |
| 是否能数值闭合 | validation_report.md保留4项PASS检查 |
| 是否方便课堂讨论 | teacher_discussion_questions.md给出老师追问和回答口径 |

## 当前不足

1. 目前是康农种业单公司样例，不是全量北交所样本；
2. 自动抽取以规则为主，没有做复杂表格结构解析；
3. 楚商澴锋具体入股时间和入股方式还需继续补证据；
4. 后续应将本模板复制到更多北交所公司，形成统一三表。
