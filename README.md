# PE/VC招股说明书项目 - 第一周交付包

姓名：霍泓锟

本目录按老师任务书的第一周要求整理，目标是“统一样本、跑通最小闭环”。当前已完成 8 家公共样本的招股说明书来源整理、PDF下载、文本解析、相关章节定位、候选文本截取、样本JSON生成和结构校验。

## 目录说明

- `company_lists/week1_public_samples.csv`：第一周8家公共样本清单，含公司、代码、板块、招股书链接、上市日期和处理状态。
- `raw_pdfs/`：下载后的8份招股说明书PDF。
- `outputs/week1_parsed_texts/`：PDF解析后的全文文本。
- `outputs/week1_candidate_texts/`：按关键词和页码定位切出的候选证据文本。
- `outputs/week1_sample_json/`：结构化抽取结果，每个JSON对应一家公司。
- `logs/`：下载、解析、定位、抽取、校验日志。
- `source_notes/`：数据来源、下载方法、网站采集方法和版本选择规则说明。
- `weekly_reports/week1.md`：第一周汇报。
- `code/`：各环节可复现脚本。

## 运行顺序

在 `C:\Users\29818\Desktop\霍泓锟 第一周\team-star` 下依次运行：

```powershell
python code/01_build_company_list/build_week1_company_list.py
python code/03_download_pdfs/download_week1_pdfs.py
python code/04_parse_pdf_to_markdown/parse_pdfs.py
python code/05_locate_relevant_sections/locate_sections.py
python code/06_extract_pevc_info/extract_pevc_info.py
python code/07_validate_outputs/validate_outputs.py
```

本次运行结果：8份PDF全部下载成功，8份全文解析成功，8家公司均生成候选文本和JSON，结构校验均通过；其中部分公司因投资方字段保守抽取，被标记为需人工复核。

## Week 2补充

第二周已新增2025年科创板市场级处理流程：

- 企业清单：`company_lists/week2_2025_company_list.csv`
- 来源说明：`source_notes/2025_company_list_source.md`
- 输出目录：`outputs/week2_sample_outputs/`
- 周报：`weekly_reports/week2.md`
- PR说明：`PR_WEEK2_DESCRIPTION.md`

第二周处理结果：2025年科创板19家公司全部完成PDF获取、轻量解析、候选章节定位、候选JSON抽取和结构校验。所有JSON均为候选级结果，统一标记为需人工复核。
