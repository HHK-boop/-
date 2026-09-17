"""Week 13 batch extraction and review-queue pipeline.

The pipeline starts only from the Week 12 queue and paginated prospectus text.
It does not read Gold or Final records. Every extracted value remains a
candidate until a reviewer confirms the original prospectus page.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
INPUT = ROOT / "data" / "input_week12"
SOURCE_TEXTS = ROOT / "data" / "source_texts"
OLD_CANDIDATES = ROOT / "data" / "input_week3_candidates"
DERIVED = ROOT / "data" / "derived"
OUTPUTS = ROOT / "outputs"
VALIDATION = ROOT / "validation"
LOGS = ROOT / "logs"
RUN_DATE = "2026-09-16"

PAGE_RE = re.compile(r"<!--\s*page:(\d+)\s*-->")

CHAPTER_RULES = {
    "历史沿革与股本形成": ("历史沿革", "股本形成", "股权演变", "设立以来", "历次增资"),
    "股东与股权结构": ("股东情况", "股权结构", "主要股东", "前十名股东", "持股比例"),
    "特殊投资条款": ("特殊投资条款", "特殊投资约定", "对赌", "回购安排", "反稀释"),
    "基金与备案": ("私募投资基金", "基金备案", "基金业协会", "创业投资", "股权投资基金"),
}

EVENT_RULES = {
    "capital_increase": {
        "label": "增资认缴",
        "terms": ("增资", "定向发行", "认购", "新增注册资本", "增加注册资本", "股权认购款"),
    },
    "equity_transfer": {
        "label": "股权转让",
        "terms": ("股权转让", "股份转让", "转让给", "受让", "大宗交易", "股份回购"),
    },
    "equity_snapshot": {
        "label": "股权快照",
        "terms": ("股东持股情况", "股本结构", "持股数量", "持股比例", "前十名股东"),
    },
    "fund_filing": {
        "label": "基金备案",
        "terms": ("私募投资基金", "基金备案", "基金业协会", "备案编码", "备案号"),
    },
    "special_rights": {
        "label": "特殊投资条款",
        "terms": ("特殊投资条款", "特殊投资约定", "对赌", "回购权", "优先购买权", "共同出售权", "反稀释"),
    },
}

INVESTOR_SUFFIX_RE = re.compile(
    r"[一-龥A-Za-z0-9（）()·]{2,36}?(?:创业投资基金|股权投资基金|产业投资基金|投资基金|"
    r"创业投资|股权投资|产业投资|投资管理|投资合伙企业(?:（有限合伙）|\(有限合伙\))?|"
    r"合伙企业(?:（有限合伙）|\(有限合伙\))|有限合伙|创投|资本)"
)

DATE_RE = re.compile(r"20\d{2}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?")
AMOUNT_RE = re.compile(r"(?:人民币\s*)?[\d,]+(?:\.\d+)?\s*(?:亿元|万元|元)")
SHARES_RE = re.compile(r"[\d,]+(?:\.\d+)?\s*(?:万)?股")
RATIO_RE = re.compile(r"\d+(?:\.\d+)?\s*%")


def ensure_dirs() -> None:
    for path in (SOURCE_TEXTS, OLD_CANDIDATES, DERIVED, OUTPUTS, VALIDATION, LOGS):
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]], headers: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if headers is None:
        headers = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    headers.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKSPACE / path


def parse_pages(text: str) -> dict[int, str]:
    matches = list(PAGE_RE.finditer(text))
    pages: dict[int, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        pages[int(match.group(1))] = text[start:end].strip()
    return pages


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_match(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return normalize_text(match.group(0)) if match else ""


def keyword_context(text: str, terms: tuple[str, ...], width: int = 520) -> tuple[str, str]:
    positions = [(text.find(term), term) for term in terms if text.find(term) >= 0]
    if not positions:
        return "", ""
    position, term = min(positions, key=lambda item: item[0])
    start = max(0, position - 150)
    end = min(len(text), position + width)
    return term, normalize_text(text[start:end])


def classify_investor(name: str, context: str) -> tuple[str, str, str]:
    if any(term in name for term in ("员工持股", "职工持股", "持股平台")):
        return "员工持股平台", "no", "名称或上下文明确出现员工持股/持股平台"
    if any(term in name for term in ("政府投资基金", "产业引导基金", "引导基金", "国资", "财政")):
        return "政府基金/国资", "yes", "名称或上下文出现政府基金、引导基金或国资线索"
    if any(term in name for term in ("创业投资", "创投")):
        return "VC", "yes", "名称或上下文明确出现创业投资/创投"
    if any(term in name for term in ("股权投资", "私募股权", "并购基金", "投资基金")):
        return "PE", "yes", "名称或上下文明确出现股权投资基金、私募或投资基金"
    if any(term in name for term in ("产业投资", "战略投资")):
        return "CVC候选", "uncertain", "产业投资名称只能形成CVC候选，仍需核验出资人与主营关系"
    if any(term in name for term in ("有限公司", "股份有限公司")):
        return "企业法人候选", "uncertain", "企业名称本身不能证明属于CVC或PE/VC"
    if any(term in name for term in ("投资", "资本", "基金", "合伙")):
        return "机构投资者待核", "uncertain", "名称具有投资机构特征，但缺少基金属性证据"
    return "待人工确认", "uncertain", "仅凭当前文本无法可靠分类"


def extract_entities(text: str) -> list[str]:
    candidates: list[str] = []
    for raw in INVESTOR_SUFFIX_RE.findall(text):
        value = normalize_text(raw).strip("，。；：、()（）")
        value = re.sub(r"^.*(?:公司已收到定向发行对象|收到定向发行对象|定向发行对象为|发行对象为|对象为)", "", value)
        value = re.sub(r"^.*(?:基金管理人为|管理人为|受让)", "", value)
        if "是" in value:
            tail = value.rsplit("是", 1)[-1]
            if any(term in tail for term in ("投资", "基金", "合伙", "创投", "资本")):
                value = tail
        if "为" in value:
            tail = value.rsplit("为", 1)[-1]
            if any(term in tail for term in ("投资", "基金", "合伙", "创投", "资本")):
                value = tail
        if "与" in value:
            tail = value.rsplit("与", 1)[-1]
            if any(term in tail for term in ("投资", "基金", "合伙", "创投", "资本")):
                value = tail
        value = re.sub(r"^.*股份的", "", value)
        value = re.sub(r"^(?:公司|发行人|目标公司|投资者|其中|拟由|由|向|为|对象|约定|包括|以及|君以及)", "", value)
        value = re.sub(r"^[0-9一二三四五六七八九十]+[）.)、]", "", value)
        if not (2 <= len(value) <= 42):
            continue
        if value in {"计入资本", "注册资本", "实收资本", "投资资本", "公司投资", "有限合伙", "伙企业（有限合伙", "合伙企业（有限合伙"}:
            continue
        if any(
            bad in value
            for bad in (
                "本次投资",
                "投资协议",
                "投资风险",
                "证券投资",
                "资本公积",
                "注册资本",
                "实收资本",
                "主营业务为",
                "完成私募",
                "股权投资管理",
                "计入资本",
                "基金类型为",
                "担任执行事务合伙人",
            )
        ):
            continue
        if value.startswith(("伙企业", "企业（有限合伙", "管理企业", "中心（有限合伙", "心（有限合伙", "日完成", "理的有限合伙", "理股权投资基金", "型股权投资基金", "业投资基金")):
            continue
        if value in {"私募投资基金", "创业投资基金", "股权投资基金", "产业投资基金", "投资基金"}:
            continue
        if value not in candidates:
            candidates.append(value)
    return candidates[:12]


def entity_name_is_profile_quality(name: str, company_short: str) -> bool:
    if len(name) < 3:
        return False
    if name in {"股权投资", "创业投资", "产业投资", "私募投资基金", "实缴资本", "认缴资本"}:
        return False
    bad_terms = (
        "甲方",
        "乙方",
        "应充分",
        "实缴资本",
        "认缴资本",
        "注册资本",
        "盈余公积",
        "资本公积",
        "从事股权投资",
        "规定的私募",
        "管理私募",
        "基金类型",
        "而设立",
        "设立创业投资",
        "担任执行事务合伙人",
    )
    if any(term in name for term in bad_terms):
        return False
    if name.startswith(("关于", "在", "以", "中规定", "管理", "企业投资管理", "创业投资合伙企业", "资基金", "理人由")):
        return False
    if company_short and company_short.replace("*ST", "") in name and "股权投资" in name:
        return False
    return True


def transfer_is_boilerplate(page_text: str) -> bool:
    system_terms = any(term in page_text for term in ("全国股转系统", "全国中小企业股份转让系统", "公开转让"))
    event_terms = any(term in page_text for term in ("转让方", "受让方", "转让给", "受让", "大宗交易", "股份回购"))
    return system_terms and not event_terms


def page_relevance_score(page_text: str) -> int:
    score = 0
    weights = {
        "增资": 2,
        "定向发行": 3,
        "认购": 2,
        "股权转让": 3,
        "受让": 2,
        "大宗交易": 3,
        "创业投资": 3,
        "股权投资基金": 4,
        "基金备案": 4,
        "特殊投资条款": 4,
    }
    for term, weight in weights.items():
        score += min(page_text.count(term), 3) * weight
    if any(term in page_text for terms in CHAPTER_RULES.values() for term in terms):
        score += 3
    return score


def locate_chapters(company: dict[str, str], pages: dict[int, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for chapter, terms in CHAPTER_RULES.items():
        hits = []
        for page_no, page_text in pages.items():
            count = sum(page_text.count(term) for term in terms)
            if count:
                hits.append((page_no, count, [term for term in terms if term in page_text]))
        hits.sort(key=lambda item: (-item[1], item[0]))
        rows.append(
            {
                "stock_code": company["stock_code"],
                "company_short": company["company_short"],
                "chapter_group": chapter,
                "located": "是" if hits else "否",
                "first_page": min((item[0] for item in hits), default=""),
                "top_pages": "、".join(str(item[0]) for item in hits[:6]),
                "matched_terms": "、".join(dict.fromkeys(term for item in hits[:6] for term in item[2])),
                "hit_pages_count": len(hits),
            }
        )
    return rows


def build_evidence(
    company: dict[str, str], pages: dict[int, str]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    evidence_rows: list[dict[str, object]] = []
    entity_rows: list[dict[str, object]] = []
    seen_entities: set[tuple[str, str, int]] = set()
    counter = 0

    ranked_pages = sorted(pages.items(), key=lambda item: (-page_relevance_score(item[1]), item[0]))
    for event_code, rule in EVENT_RULES.items():
        matches: list[tuple[int, str, int]] = []
        for page_no, page_text in ranked_pages:
            count = sum(page_text.count(term) for term in rule["terms"])
            if count:
                matches.append((page_no, page_text, count))
        for page_no, page_text, term_count in matches[:8]:
            counter += 1
            matched_term, excerpt = keyword_context(page_text, rule["terms"])
            entities = extract_entities(excerpt)
            event_status = "保留为Auto候选"
            exclusion_reason = ""
            if event_code == "equity_transfer" and transfer_is_boilerplate(page_text):
                event_status = "排除为转让系统语境"
                exclusion_reason = "页面仅出现全国股转系统/公开转让，未出现明确转让方、受让方或回购主体"

            date_text = first_match(DATE_RE, excerpt)
            amount_text = first_match(AMOUNT_RE, excerpt)
            shares_text = first_match(SHARES_RE, excerpt)
            ratio_text = first_match(RATIO_RE, excerpt)
            features = sum(bool(item) for item in (date_text, amount_text or shares_text, entities))
            confidence = "高" if features == 3 and event_status.startswith("保留") else "中" if features >= 1 else "低"
            if event_status.startswith("排除"):
                confidence = "低"

            candidate_id = f"W13-{company['stock_code']}-{counter:03d}"
            evidence_rows.append(
                {
                    "candidate_id": candidate_id,
                    "stock_code": company["stock_code"],
                    "company_short": company["company_short"],
                    "event_code": event_code,
                    "event_type": rule["label"],
                    "source_page": page_no,
                    "matched_term": matched_term,
                    "term_hit_count": term_count,
                    "date_text": date_text,
                    "amount_text": amount_text,
                    "shares_text": shares_text,
                    "ratio_text": ratio_text,
                    "investor_candidate_count": len(entities),
                    "confidence": confidence,
                    "auto_status": event_status,
                    "exclusion_reason": exclusion_reason,
                    "evidence_excerpt": excerpt,
                    "source_url": company.get("source_url", ""),
                    "local_text_file": company.get("package_text_file", ""),
                    "gold_final_value": "",
                    "review_note": "待人工回原文页确认",
                }
            )

            for entity in entities:
                entity_key = (entity, event_code, page_no)
                if entity_key in seen_entities:
                    continue
                seen_entities.add(entity_key)
                investor_type, is_pevc, basis = classify_investor(entity, excerpt)
                entity_rows.append(
                    {
                        "entity_id": f"{candidate_id}-I{len(entity_rows) + 1:03d}",
                        "candidate_id": candidate_id,
                        "stock_code": company["stock_code"],
                        "company_short": company["company_short"],
                        "investor_name_candidate": entity,
                        "investor_type_candidate": investor_type,
                        "is_pevc_candidate": is_pevc,
                        "classification_basis": basis,
                        "source_page": page_no,
                        "final_investor_type": "",
                        "manual_review_status": "待人工确认",
                    }
                )
    return evidence_rows, entity_rows


def old_candidate_pages(source_stem: str) -> tuple[set[int], int, Path | None]:
    source = WORKSPACE / "team-star" / "outputs" / "week3_sample_outputs" / "candidate_texts" / f"{source_stem}_candidates.txt"
    if not source.exists():
        return set(), 0, None
    text = source.read_text(encoding="utf-8", errors="ignore")
    pages = {int(value) for value in re.findall(r"source_page=(\d+)", text)}
    count = len(re.findall(r"=====\s*candidate\s+\d+\s*=====", text))
    return pages, count, source


def build_review_queue(evidence: list[dict[str, object]]) -> list[dict[str, object]]:
    retained = [row for row in evidence if str(row["auto_status"]).startswith("保留")]
    priority_order = {"低": 0, "中": 1, "高": 2}
    ranked = sorted(
        retained,
        key=lambda row: (
            priority_order.get(str(row["confidence"]), 9),
            0 if row["event_code"] in {"equity_transfer", "fund_filing"} else 1,
            str(row["stock_code"]),
            int(row["source_page"]),
        ),
    )
    sample_size = max(24, round(len(retained) * 0.10)) if retained else 0
    rows: list[dict[str, object]] = []
    for index, item in enumerate(ranked[:sample_size], 1):
        reason = "低/中置信候选优先复核"
        if item["event_code"] == "equity_transfer":
            reason = "核对是否为真实股权转让，排除全国股转系统语境"
        elif item["event_code"] == "fund_filing":
            reason = "核对备案编码、管理人/GP及是否直接披露"
        rows.append(
            {
                "review_id": f"W13R{index:03d}",
                "priority": "P1" if item["confidence"] == "低" else "P2",
                "candidate_id": item["candidate_id"],
                "stock_code": item["stock_code"],
                "company_short": item["company_short"],
                "event_type": item["event_type"],
                "source_page": item["source_page"],
                "confidence": item["confidence"],
                "review_reason": reason,
                "human_decision": "",
                "corrected_value": "",
                "reviewer": "",
                "review_date": "",
                "evidence_excerpt": item["evidence_excerpt"],
            }
        )
    return rows


def main() -> None:
    ensure_dirs()
    queue = read_csv(INPUT / "week12_processing_queue.csv")
    p1 = [row for row in queue if row.get("priority", "").startswith("P1")]
    selected = sorted(p1, key=lambda row: (-int(row.get("keyword_hit_count") or 0), row.get("stock_code", "")))[:12]

    selected_rows: list[dict[str, object]] = []
    locator_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    entity_rows: list[dict[str, object]] = []
    crosscheck_rows: list[dict[str, object]] = []
    progress_rows: list[dict[str, object]] = []

    for order, row in enumerate(selected, 1):
        source_path = resolve_workspace_path(row.get("local_text_path", ""))
        if not source_path.exists():
            continue
        package_name = f"{row['stock_code']}_{source_path.name}"
        package_path = SOURCE_TEXTS / package_name
        shutil.copy2(source_path, package_path)

        source_stem = source_path.stem
        old_pages, old_count, old_source = old_candidate_pages(source_stem)
        if old_source:
            shutil.copy2(old_source, OLD_CANDIDATES / old_source.name)

        text = package_path.read_text(encoding="utf-8", errors="ignore")
        pages = parse_pages(text)
        company = {
            **row,
            "package_text_file": f"data/source_texts/{package_name}",
        }
        company_locators = locate_chapters(company, pages)
        company_evidence, company_entities = build_evidence(company, pages)
        locator_rows.extend(company_locators)
        evidence_rows.extend(company_evidence)
        entity_rows.extend(company_entities)

        retained = [item for item in company_evidence if str(item["auto_status"]).startswith("保留")]
        excluded = [item for item in company_evidence if str(item["auto_status"]).startswith("排除")]
        new_pages = {int(item["source_page"]) for item in retained}
        overlap = old_pages & new_pages
        recovery = round(len(overlap) / len(old_pages), 4) if old_pages else ""

        selected_rows.append(
            {
                "batch_order": order,
                "queue_id": row.get("queue_id", ""),
                "stock_code": row.get("stock_code", ""),
                "company_short": row.get("company_short", ""),
                "board": row.get("board", ""),
                "source_platform": row.get("source_platform", ""),
                "source_url": row.get("source_url", ""),
                "original_text_path": row.get("local_text_path", ""),
                "package_text_file": f"data/source_texts/{package_name}",
                "page_count": len(pages),
                "week12_keyword_hits": int(row.get("keyword_hit_count") or 0),
                "selection_reason": "第十二周P1队列中关键词命中数排名前12，且本地页码化文本完整",
                "missing_policy": "招股书未披露字段留空，不根据机构名称补写备案编码、GP或LP",
            }
        )
        crosscheck_rows.append(
            {
                "stock_code": row.get("stock_code", ""),
                "company_short": row.get("company_short", ""),
                "old_candidate_record_count": old_count,
                "old_unique_pages": len(old_pages),
                "week13_retained_records": len(retained),
                "week13_unique_pages": len(new_pages),
                "overlap_pages": len(overlap),
                "old_page_recovery_rate": recovery,
                "newly_located_pages": len(new_pages - old_pages),
                "comparison_scope": "定位结果一致性，不等同于Gold准确率",
            }
        )
        progress_rows.append(
            {
                "stock_code": row.get("stock_code", ""),
                "company_short": row.get("company_short", ""),
                "page_count": len(pages),
                "chapter_groups_located": sum(item["located"] == "是" for item in company_locators),
                "retained_auto_candidates": len(retained),
                "excluded_transfer_boilerplate": len(excluded),
                "investor_name_candidates": len(company_entities),
                "high_confidence_candidates": sum(item["confidence"] == "高" for item in retained),
                "processing_status": "Auto定位完成，进入人工Gold复核队列",
            }
        )

    review_rows = build_review_queue(evidence_rows)

    profile_groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in entity_rows:
        if not entity_name_is_profile_quality(str(row["investor_name_candidate"]), str(row["company_short"])):
            continue
        profile_groups[(str(row["stock_code"]), str(row["investor_name_candidate"]))].append(row)
    investor_profiles: list[dict[str, object]] = []
    for index, ((stock_code, investor_name), group) in enumerate(sorted(profile_groups.items()), 1):
        first = group[0]
        investor_profiles.append(
            {
                "profile_id": f"W13IP{index:03d}",
                "stock_code": stock_code,
                "company_short": first["company_short"],
                "investor_name_candidate": investor_name,
                "investor_type_candidate": first["investor_type_candidate"],
                "is_pevc_candidate": first["is_pevc_candidate"],
                "classification_basis": first["classification_basis"],
                "evidence_pages": "、".join(str(value) for value in sorted({int(item["source_page"]) for item in group})),
                "occurrence_count": len(group),
                "manual_review_status": "待人工确认",
                "amac_filing_code": "",
                "gp_name": "",
                "lp_structure": "",
                "deep_field_rule": "原文或权威来源未披露时留空",
            }
        )

    investor_type_rules = [
        {"type": "员工持股平台", "positive_rule": "名称或上下文明确出现员工持股、职工持股或持股平台", "negative_rule": "名称含投资/合伙但无员工属性时不得归类", "final_requirement": "核对招股书股东性质说明"},
        {"type": "政府基金/国资", "positive_rule": "政府投资基金、产业引导基金、财政或国资线索", "negative_rule": "仅有产业字样不得直接判断为政府基金", "final_requirement": "核对出资人或控制人来源"},
        {"type": "VC", "positive_rule": "名称或原文明确出现创业投资/创投", "negative_rule": "普通投资公司不得仅凭名称归VC", "final_requirement": "招股书或权威登记来源"},
        {"type": "PE", "positive_rule": "股权投资基金、私募股权、并购基金或投资基金", "negative_rule": "企业法人股东不自动归PE", "final_requirement": "基金属性及备案来源"},
        {"type": "CVC", "positive_rule": "产业投资主体且可确认其由产业企业控制", "negative_rule": "产业投资名称只能形成CVC候选", "final_requirement": "核对实际控制人及主营业务关系"},
        {"type": "企业法人候选", "positive_rule": "公司制主体但当前文本未证明基金属性", "negative_rule": "不与CVC或PE/VC混用", "final_requirement": "人工确认其投资目的与控制关系"},
        {"type": "自然人", "positive_rule": "原文明确为个人姓名或自然人股东", "negative_rule": "不得使用机构名称规则识别", "final_requirement": "核对股东性质栏"},
    ]

    event_summary: list[dict[str, object]] = []
    retained_all = [row for row in evidence_rows if str(row["auto_status"]).startswith("保留")]
    for event_code, rule in EVENT_RULES.items():
        event_rows = [row for row in retained_all if row["event_code"] == event_code]
        event_summary.append(
            {
                "event_code": event_code,
                "event_type": rule["label"],
                "candidate_records": len(event_rows),
                "companies_covered": len({row["stock_code"] for row in event_rows}),
                "high_confidence_records": sum(row["confidence"] == "高" for row in event_rows),
                "with_date": sum(bool(row["date_text"]) for row in event_rows),
                "with_amount_or_shares": sum(bool(row["amount_text"] or row["shares_text"]) for row in event_rows),
                "use_note": "Auto候选数量，需人工回原文确认后才能进入Gold/Final",
            }
        )

    quality_rows = [
        {"check_item": "入选公司数量", "status": "PASS" if len(selected_rows) == 12 else "FAIL", "value": len(selected_rows), "rule": "第十二周P1队列中选择12家公司"},
        {"check_item": "页码化文本可读取", "status": "PASS" if all(int(row["page_count"]) > 0 for row in selected_rows) else "FAIL", "value": sum(int(row["page_count"]) > 0 for row in selected_rows), "rule": "12家公司均有页码标记"},
        {"check_item": "来源URL覆盖", "status": "PASS" if all(row["source_url"] for row in selected_rows) else "WARN", "value": sum(bool(row["source_url"]) for row in selected_rows), "rule": "每家公司保留招股书URL"},
        {"check_item": "章节定位覆盖", "status": "PASS" if all(int(row["chapter_groups_located"]) >= 2 for row in progress_rows) else "WARN", "value": sum(int(row["chapter_groups_located"]) >= 2 for row in progress_rows), "rule": "每家公司至少定位2类章节"},
        {"check_item": "Auto与Gold隔离", "status": "PASS", "value": "Gold/Final列为空", "rule": "主流程未读取Gold或Final，人工字段保持空值"},
        {"check_item": "转让系统误命中过滤", "status": "PASS", "value": sum(int(row["excluded_transfer_boilerplate"]) for row in progress_rows), "rule": "公开转让/股转系统且无明确交易主体的页面不进入转让候选"},
        {"check_item": "10%人工复核队列", "status": "PASS" if len(review_rows) >= max(24, round(len(retained_all) * 0.10)) else "FAIL", "value": len(review_rows), "rule": "优先抽取低/中置信和转让/备案候选"},
        {"check_item": "未披露留空", "status": "PASS", "value": "AMAC/GP/LP未自动补写", "rule": "只记录来源页和候选，不根据名称猜测深度字段"},
    ]

    weekly_plan = [
        {"day": "第1天", "task": "确定首批扩样", "action": "从第十二周P1队列按关键词命中数和文本完整性选取12家", "output": "入选公司表与来源副本", "status": "已完成"},
        {"day": "第2天", "task": "章节定位", "action": "按历史沿革、股东结构、特殊条款、基金备案四类规则定位页码", "output": "章节定位表", "status": "已完成"},
        {"day": "第3天", "task": "事件候选抽取", "action": "按增资、转让、快照、备案和特殊权利分类截取证据", "output": "Auto证据候选表", "status": "已完成"},
        {"day": "第4天", "task": "投资主体分类", "action": "生成investor_type候选，CVC和基金属性保留人工确认", "output": "主体候选表与分类规则", "status": "已完成"},
        {"day": "第5天", "task": "交叉校验", "action": "与第三周旧定位页比较，量化重合页和新增定位页", "output": "旧新定位Cross-check", "status": "已完成"},
        {"day": "第6天", "task": "数据库验证", "action": "把公司、定位、候选、主体和复核队列导入临时PostgreSQL", "output": "表行数与查询披露", "status": "待统一入口运行"},
        {"day": "第7天", "task": "汇报整理", "action": "生成Excel、Word、日志和提交清单", "output": "第十三周提交包", "status": "待统一入口运行"},
    ]

    write_csv(DERIVED / "week13_selected_companies.csv", selected_rows)
    write_csv(DERIVED / "week13_chapter_locator.csv", locator_rows)
    write_csv(DERIVED / "week13_auto_evidence_candidates.csv", evidence_rows)
    write_csv(DERIVED / "week13_investor_candidates.csv", entity_rows)
    write_csv(DERIVED / "week13_investor_profile.csv", investor_profiles)
    write_csv(DERIVED / "week13_investor_type_rules.csv", investor_type_rules)
    write_csv(DERIVED / "week13_event_summary.csv", event_summary)
    write_csv(DERIVED / "week13_old_new_crosscheck.csv", crosscheck_rows)
    write_csv(DERIVED / "week13_company_progress.csv", progress_rows)
    write_csv(DERIVED / "week13_manual_review_queue.csv", review_rows)
    write_csv(DERIVED / "week13_weekly_plan.csv", weekly_plan)
    write_csv(VALIDATION / "week13_validation_summary.csv", quality_rows)

    recovery_values = [float(row["old_page_recovery_rate"]) for row in crosscheck_rows if row["old_page_recovery_rate"] != ""]
    summary = {
        "run_date": RUN_DATE,
        "selected_company_count": len(selected_rows),
        "source_page_count": sum(int(row["page_count"]) for row in selected_rows),
        "chapter_locator_record_count": len(locator_rows),
        "auto_candidate_record_count": len(evidence_rows),
        "retained_candidate_record_count": len(retained_all),
        "excluded_transfer_boilerplate_count": sum(str(row["auto_status"]).startswith("排除") for row in evidence_rows),
        "investor_candidate_record_count": len(entity_rows),
        "unique_investor_candidate_count": len(investor_profiles),
        "manual_review_queue_count": len(review_rows),
        "old_candidate_average_page_recovery_rate": round(sum(recovery_values) / len(recovery_values), 4) if recovery_values else None,
        "companies_with_all_four_chapter_groups": sum(int(row["chapter_groups_located"]) == 4 for row in progress_rows),
        "quality_checks_passed": sum(row["status"] == "PASS" for row in quality_rows),
        "quality_checks_total": len(quality_rows),
        "interpretation": "上述数量均为Auto定位与候选记录，不等同于人工Gold事件数。",
    }
    write_json(OUTPUTS / "week13_summary.json", summary)

    log_lines = [
        f"run_date={RUN_DATE}",
        f"selected_companies={len(selected_rows)}",
        f"source_pages={summary['source_page_count']}",
        f"auto_candidates={len(evidence_rows)}",
        f"retained_candidates={len(retained_all)}",
        f"excluded_transfer_boilerplate={summary['excluded_transfer_boilerplate_count']}",
        f"investor_candidates={len(entity_rows)}",
        f"unique_investor_candidates={len(investor_profiles)}",
        f"manual_review_queue={len(review_rows)}",
    ]
    (LOGS / "week13_pipeline.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
