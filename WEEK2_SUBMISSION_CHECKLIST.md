# Week 2 GitHub提交清单

## 必交文件

- `company_lists/week2_2025_company_list.csv`
- `source_notes/2025_company_list_source.md`
- `source_notes/prospectus_download_method.md`
- `source_notes/version_rules.md`
- `code/01_build_company_list/build_week2_2025_company_list.py`
- `code/02_fetch_prospectus_urls/fetch_week2_prospectus_urls.py`
- `code/03_download_pdfs/download_week2_pdfs.py`
- `code/04_parse_pdf_to_markdown/parse_week2_pdfs.py`
- `code/05_locate_relevant_sections/locate_week2_sections.py`
- `code/06_extract_pevc_info/extract_week2_pevc_info.py`
- `code/07_validate_outputs/validate_week2_outputs.py`
- `outputs/week2_sample_outputs/candidate_texts/`
- `outputs/week2_sample_outputs/sample_json/`
- `outputs/week2_sample_outputs/week2_output_summary.csv`
- `logs/download_log.csv`
- `logs/parse_log.csv`
- `logs/locate_log.csv`
- `logs/extraction_log.csv`
- `logs/validation_log.csv`
- `logs/error_cases.md`
- `weekly_reports/week2.md`
- `PR_WEEK2_DESCRIPTION.md`

## 本周统计

- 负责板块：科创板。
- 样本范围：2025年科创板上市公司。
- 企业数量：19家。
- PDF获取：19/19成功。
- PDF页数：8791页。
- 候选文本：19份。
- JSON输出：19份。
- JSON结构校验：19/19通过。
- 人工复核标记：19/19均标记 `review_required=yes`。

## GitHub提交说明

本提交版已排除大文件和可再生文件：

- 不提交 `raw_pdfs/`。
- 不提交 `outputs/week2_sample_outputs/parsed_texts/`。
- 不提交 `source_company_list_star_2021_2025.xlsx`。
- 不提交 `__pycache__/` 和 `*.pyc`。

以上排除规则已写入 `.gitignore`。如果需要复现PDF和解析缓存，可按 `PR_WEEK2_DESCRIPTION.md` 中的运行顺序重新生成。
