# [Week 2][科创板组] 2025年样本与市场级流程提交

## 本周提交内容

### 1. 企业清单

- 文件路径：`company_lists/week2_2025_company_list.csv`
- 样本范围：2025年科创板上市公司，共19家。
- 数据来源：前期巨潮资讯网/CNINFO抓取结果，并保留巨潮PDF链接。

### 2. 代码

新增第二周脚本：

- `code/week2_common.py`
- `code/01_build_company_list/build_week2_2025_company_list.py`
- `code/02_fetch_prospectus_urls/fetch_week2_prospectus_urls.py`
- `code/03_download_pdfs/download_week2_pdfs.py`
- `code/04_parse_pdf_to_markdown/parse_week2_pdfs.py`
- `code/05_locate_relevant_sections/locate_week2_sections.py`
- `code/06_extract_pevc_info/extract_week2_pevc_info.py`
- `code/07_validate_outputs/validate_week2_outputs.py`

运行顺序：

```powershell
python code/01_build_company_list/build_week2_2025_company_list.py
python code/02_fetch_prospectus_urls/fetch_week2_prospectus_urls.py
python code/03_download_pdfs/download_week2_pdfs.py
python code/04_parse_pdf_to_markdown/parse_week2_pdfs.py
python code/05_locate_relevant_sections/locate_week2_sections.py
python code/06_extract_pevc_info/extract_week2_pevc_info.py
python code/07_validate_outputs/validate_week2_outputs.py
```

### 3. 日志

- 下载日志：`logs/download_log.csv`、`logs/week2_download_log.csv`
- 解析日志：`logs/parse_log.csv`、`logs/week2_parse_log.csv`
- 定位日志：`logs/locate_log.csv`、`logs/week2_locate_log.csv`
- 抽取日志：`logs/extraction_log.csv`、`logs/week2_extraction_log.csv`
- 校验日志：`logs/validation_log.csv`、`logs/week2_validation_log.csv`
- 失败案例：`logs/error_cases.md`

### 4. 样本结果

- 候选文本：`outputs/week2_sample_outputs/candidate_texts/`
- JSON样本：`outputs/week2_sample_outputs/sample_json/`
- 汇总表：`outputs/week2_sample_outputs/week2_output_summary.csv`

### 5. 主要问题

- 全文解析19份招股书耗时较长，本周改为统计全书页数并提取前180页用于章节定位。
- 规则抽取仍可能包含说明性短语，因此所有Week 2 JSON均标记 `review_required=yes`。
- 部分公司自动规则未识别到明确投资方，需要人工回到PDF候选页核对。

### 6. 需要老师确认的问题

- 第二周市场级流程是否可以采用“候选级JSON + 全部人工复核标记”的保守口径。
- 固定前180页定位是否可作为本周流程测试口径；第三周将尝试目录识别后按章节范围抽取。
