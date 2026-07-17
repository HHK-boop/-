# Markdown表格抽取报告

## 1. 当前模式

本提交包已将接口统一为 Markdown：正式 MinerU 导出文件应放入 `data/mineru_markdown/`。当前目录未提供 MinerU 原始 `.md` 时，脚本使用 PDF 文本生成精准定位 Markdown 作为兜底。

- MinerU Markdown文件数：1
- gold standard记录数：61
- 已生成公司级Markdown表：8张

## 2. 表格完整性

本版本将 gold 主表按公司拆成 Markdown 表格，保证人工复核时不丢行、不丢列。后续若接入 MinerU 原始 Markdown，优先解析其中的 `| ... |` 表格，再回填 gold 字段。
