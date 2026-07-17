# 自动抽取与人工Gold对比

本表不是为了证明自动化已经完美，而是量化规则定位在当前八家公司中的可用程度。

| metric | numerator | denominator | accuracy_pct |
| --- | --- | --- | --- |
| gold_records | 61 | 61 | 100.0 |
| investor_type_accuracy | 61 | 61 | 100.0 |
| filing_code_accuracy_when_pdf_disclosed | 50 | 50 | 100.0 |
| gp_name_accuracy_when_pdf_disclosed | 52 | 56 | 92.86 |
| gp_registration_code_accuracy_when_pdf_disclosed | 41 | 42 | 97.62 |
| blank_policy_records | 41 | 61 |  |

口径说明：备案编码准确率只统计 gold 中 PDF 已披露编码的记录；PDF 未披露编码的记录不计入分母。
