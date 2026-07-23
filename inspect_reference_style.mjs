import fs from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { FileBlob, SpreadsheetFile } = require("@oai/artifact-tool");

const refs = [
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/001282_三联锻造_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/301563_云汉芯城_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/301581_黄山谷捷_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/603418_友升股份_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/688758_赛分科技_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/688775_影石创新_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/920100_三协电机_三表抽取.xlsx",
  "C:/Users/29818/Documents/xwechat_files/wxid_mdm501526cx122_1a20/msg/file/2026-07/920116_星图测控_三表抽取.xlsx",
];

const outDir = "tmp_workbook/reference_style";
await fs.mkdir(outDir, { recursive: true });

const summaries = [];
for (const file of refs) {
  const blob = await FileBlob.load(file);
  const workbook = await SpreadsheetFile.importXlsx(blob);
  const inspect = await workbook.inspect({
    kind: "workbook,sheet,table,region,computedStyle",
    range: "A1:K12",
    maxChars: 12000,
    tableMaxRows: 8,
    tableMaxCols: 12,
    tableMaxCellChars: 80,
  });
  const safe = file.split("/").pop().replace(".xlsx", "");
  await fs.writeFile(`${outDir}/${safe}.inspect.ndjson`, inspect.ndjson ?? String(inspect), "utf8");
  const sheetInfo = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 4000 });
  await fs.writeFile(`${outDir}/${safe}.sheets.ndjson`, sheetInfo.ndjson ?? String(sheetInfo), "utf8");
  const firstSheet = (sheetInfo.ndjson.match(/"name":"([^"]+)"/) || [])[1];
  if (firstSheet) {
    const preview = await workbook.render({ sheetName: firstSheet, range: "A1:K18", scale: 1, format: "png" });
    await fs.writeFile(`${outDir}/${safe}.${firstSheet}.png`, new Uint8Array(await preview.arrayBuffer()));
  }
  summaries.push({ file, inspect: inspect.ndjson ?? String(inspect) });
}
await fs.writeFile(`${outDir}/reference_style_summary.json`, JSON.stringify(summaries, null, 2), "utf8");
console.log(`Reference inspection written to ${outDir}`);
