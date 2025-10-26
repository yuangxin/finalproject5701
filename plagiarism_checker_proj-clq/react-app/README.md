# React 作业相似度可视化

该项目基于 Create React App，使用你之前在 `react-visualizer/` 下编写的前端逻辑进行重构，支持通过 `npm start` 启动开发服务器实时查看结果。

## 目录结构
- `public/pair_summary.csv`：相似度统计表（运行 `python b.py` 生成）。
- `public/pair_results.json`：每对学生的详细匹配（含句子内容等信息）。
- `public/evidence_top.json`：`pair_results.json` 的精简映射，供旧版页面兼容使用。
- `public/documents.json`：每份作业的完整句子列表，用于文章对比视图。
- `src/App.js` / `src/App.css`：React 组件与样式，负责展示概览表格和高亮原文片段。

## 使用步骤
1. 在项目根目录生成最新结果：
   ```bash
   python b.py
   cp pair_summary.csv react-app/public/pair_summary.csv
   cp pair_results.json react-app/public/pair_results.json
   cp evidence_top.json react-app/public/evidence_top.json  # 可选，供兼容
   # 如需文章对比视图，可将原始作业拆句后写入 documents.json：
   # python - <<'PY' ...  (示例见下方 “生成 documents.json”)
   cp documents.json react-app/public/documents.json
   ```
   > 也可以修改脚本，直接输出到 `react-app/public`。

2. 启动开发服务器：
   ```bash
   cd react-app
   npm install   # 首次运行需要安装依赖
   npm start
   ```
   浏览器会自动打开 [http://localhost:3000](http://localhost:3000)，页面加载 CSV/JSON 并渲染双栏高亮视图。

3. 打包发布：
   ```bash
   npm run build
   ```
   生成的 `build/` 目录可直接部署到静态服务器。

## 数据加载说明
数据加载顺序如下（使用 `fetch`）：
1. `${PUBLIC_URL}/pair_summary.csv`（CRA 正确路径）
2. `./pair_summary.csv`
3. `/pair_summary.csv`
4. `pair_summary.csv`

`evidence_top.json` 同理。若全部路径均失败，将在页面顶部显示错误提示。

### 生成 documents.json 示例
```bash
python - <<'PY'
import json, re
from pathlib import Path
folder = Path("paraphrase_outputs")
docs = {}
for path in folder.glob("*.txt"):
    text = path.read_text(encoding="utf-8")
    sentences = [s.strip() for s in re.split(r"(?<=[。！？.!?;；])", text) if s.strip()]
    docs[path.stem] = {"sentences": sentences}
Path("documents.json").write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
PY
cp documents.json react-app/public/documents.json
```

## 样式亮点
- 表格行可点击切换，右侧面板会展示对应学生的高亮句段。
- 彩色编号标记匹配对，便于快速比对。
- 高亮颜色根据相似度自动渐变：相似度越高颜色越偏红，越低越偏绿。
- 所有样式集中在 `src/App.css`，可根据需求调整配色或布局。
