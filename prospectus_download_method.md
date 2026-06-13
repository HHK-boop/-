# 招股说明书下载方法

## 下载目标

下载每家公司“首次公开发行股票并上市招股说明书”的正式稿PDF，保存到 `raw_pdfs/`。文件命名规则为：

```text
样本ID_股票代码.pdf
```

例如：`STAR002_688775.pdf`。

## 下载流程

1. 根据任务书样本表确定公司名称、股票代码和板块。
2. 在公告库中检索公司代码对应的招股说明书公告。
3. 优先选择标题含“首次公开发行股票并在xx上市招股说明书”的正式稿。
4. 进入公告详情页，解析PDF链接。
5. 由脚本下载PDF，并记录下载时间、文件大小、状态和错误信息。

## 对应脚本

- 样本和URL整理：`code/01_build_company_list/build_week1_company_list.py`
- PDF下载：`code/03_download_pdfs/download_week1_pdfs.py`

## 日志字段

`logs/download_log.csv` 包含：

- `company_name`
- `stock_code`
- `prospectus_url`
- `file_name`
- `download_time`
- `status`
- `file_size`
- `error_message`

本次结果：8条下载记录均为 `success`。

## Week 2补充：2025年科创板批量下载

第二周下载对象为2025年科创板19家公司正式招股说明书。下载脚本为：

```text
code/03_download_pdfs/download_week2_pdfs.py
```

运行逻辑：

1. 读取 `company_lists/week2_2025_company_list.csv`。
2. 优先复用本地前期抓取PDF缓存。
3. 若本地缓存不存在，则使用 `prospectus_url` 从巨潮静态PDF地址下载。
4. 保存到 `raw_pdfs/week2/`，文件名为 `sample_id_stockcode.pdf`。
5. 写入 `logs/download_log.csv` 和 `logs/week2_download_log.csv`。

本周结果：19家公司PDF全部成功，日志中的 `source=local_cache` 表示复用了前期巨潮抓取的本地PDF文件。
