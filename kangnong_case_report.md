# 康农种业案例报告：从PDF证据到manual gold

姓名：霍泓锟  
负责市场：北交所  
公司：康农种业  
代码：920403  

## 1. 为什么选择康农种业

康农种业适合作为单公司深讲样本，原因是它同时包含：

- 2020年定向发行，可以做发行数量、价格、募集金额的数值闭合；
- 发行前PE/VC股东楚商澴锋，可以说明“PE/VC持股”和“融资轮次”不能混同；
- 子公司股权收购/转让，可以作为自动化误判样本；
- 发行前股东结构表，可以做存量持股比例校验。

因此，这个案例能较好回应老师要求的三个重点：是否理解公司、是否能从个案提炼方法、是否能反思自动化。

## 2. 股本变化时间线

| 时间 | 事件 | 处理口径 |
|---|---|---|
| 2016-05-23 | 全国股转系统挂牌 | 背景信息，不作为PE/VC融资事件 |
| 2018-01-15 | 交易方式变更为集合竞价 | 交易制度变化，不作为股本变化 |
| 2020-09至2020-11 | 定向发行324.00万股，10.00元/股，募集3240.00万元 | 发行人层面的真实股本变化 |
| 2021-01-25 | 实际控制人变化 | 控制权信息，与融资事件分开 |
| 招股书签署日 | 楚商澴锋持有222.20万股，占比5.63% | PE/VC发行前持股，不强行写成融资轮次 |
| 2023-03至2023-12 | 北交所发行上市审批 | IPO节点，可用于退出方式和发行后股本校验 |

## 3. PDF证据

### 3.1 定向发行数量、价格和募集金额

![2020年定向发行](../evidence/screenshots/evidence_p046_financing.png)

招股书第46页附近披露：公司2020年定向发行324.00万股，发行价格为10.00元/股，募集资金总额为3240.00万元。

![验资及注册资本变化](../evidence/screenshots/evidence_p047_capital_verified.png)

招股书第47页附近披露：大信会计师事务所出具验资报告，确认募集资金总额3240.00万元，公司注册资本增至3946.00万元。

可验证：

```text
324.00万股 x 10.00元/股 = 3240.00万元
```

### 3.2 楚商澴锋PE/VC属性和发行前持股

![楚商澴锋基金备案信息](../evidence/screenshots/evidence_p050_chushang_basic.png)

招股书第50页附近披露：楚商澴锋为私募股权投资基金，具有基金备案编号和基金管理人信息。

![发行前股东表](../evidence/screenshots/evidence_p052_top_shareholders.png)

招股书第52页附近披露：楚商澴锋持有222.20万股，占发行前总股本5.63%。

可验证：

```text
222.20 / 3946.00 x 100% = 5.6310%
```

该比例与PDF中的5.63%一致。

### 3.3 自动化容易误判的子公司股权变化

![子公司股权变化误判样本](../evidence/screenshots/evidence_p159_subsidiary_changes.png)

招股书第159页附近出现“收购”“股权转让”“价款”等词，但它描述的是致力种业、泰悦中药材、四川康农等子公司股权或合并范围变化。主体不是发行人康农种业，因此不能进入发行人PE/VC融资事件表。

## 4. manual gold 结果

| record_id | 事件类型 | 主体 | 状态 | 证据页 | 人工判断 |
|---|---|---|---|---|---|
| KG-GOLD-001 | directed_issuance | issuer | keep | 46;47 | 发行人层面的真实股本变化 |
| KG-GOLD-002 | pevc_preipo_holding | issuer_shareholder | keep | 50;52 | PE/VC发行前持股，不直接写成融资轮次 |
| KG-GOLD-003 | ipo_issue_endpoint | issuer | keep | 19;52 | IPO发行上市节点和股本闭合校验 |
| KG-GOLD-004 | subsidiary_equity_transfer | subsidiary | exclude | 159 | 子公司股权变化，作为误判样本排除 |

完整数据见 `outputs/manual_gold.csv`。

## 5. 自动化流程

本作业的自动化流程从PDF开始：

```text
PDF -> 关键页文本抽取 -> 规则候选召回 -> auto_output -> manual_gold对照 -> validation_report
```

运行命令：

```bash
python run_pipeline.py
python code/check_submission.py
```

自动化脚本会生成：

- `outputs/parsed_evidence_pages.csv`
- `outputs/auto_output_candidates.csv`
- `outputs/manual_gold.csv`
- `outputs/comparison_auto_vs_manual.csv`
- `outputs/evidence_index.csv`
- `outputs/validation_report.md`
- `outputs/teacher_discussion_questions.md`

## 6. 自动化失败点反思

| 失败点 | 康农种业中的体现 | 改进方向 |
|---|---|---|
| 只靠关键词 | 第159页也有“股权、转让、价款” | 增加event_subject字段，先判断主体 |
| 存量和流量混淆 | 楚商澴锋发行前持股不等于新增融资 | 区分pevc_preipo_holding和financing_event |
| 单位混乱 | 万元、元/股、万股并存 | 保留原文单位，再做统一换算 |
| 证据链不足 | 只有数值无法回答老师追问 | 每条gold保留source_pages和截图 |
| auto和manual混合 | 自动候选不能直接进入最终表 | 分成auto_output、manual_gold、comparison |

## 7. 展示时可回答的问题

### Q1：楚商澴锋为什么算PE/VC？

因为PDF披露其为私募股权投资基金，并给出基金备案编号和基金管理人信息。

### Q2：为什么不能写成一轮融资？

因为发行前股东表只证明其持股，不证明具体入股时间、方式和价格。因此当前只写为PE/VC发行前持股。

### Q3：第159页为什么排除？

因为主体是子公司股权和合并范围变化，不是发行人康农种业股本变化。

## 8. 下一步计划

1. 继续回到历史沿革章节，补充楚商澴锋具体入股时间和交易方式；
2. 将表格抽取从纯文本规则升级为结构化表格解析；
3. 将该模板复制到更多北交所公司；
4. 对每家公司都保留manual_gold、auto_output、comparison三层结果。
