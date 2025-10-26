import React from "react";
import "./App.css";

const similarityToColor = (sim, alpha = 1) => {
  const clamped = Math.max(0, Math.min(1, sim ?? 0));
  const hue = 120 - clamped * 120; // 0→red, 1→green
  const saturation = 85;
  const lightness = 55;
  if (alpha >= 1) {
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  }
  return `hsla(${hue}, ${saturation}%, ${lightness}%, ${alpha})`;
};

const DEFAULT_SIM_THRESHOLD = 0.8;

const shorten = (text, limit = 120) => {
  if (!text) return "";
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= limit) return compact;
  return `${compact.slice(0, limit - 1)}…`;
};

const parseCSV = (text) => {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length <= 1) return [];
  const headers = lines[0].split(",").map((h) => h.trim());
  return lines
    .slice(1)
    .filter((row) => row.trim().length > 0)
    .map((line) => {
      const cells = line.split(",").map((cell) => cell.trim());
      const record = {};
      headers.forEach((header, idx) => {
        record[header] = cells[idx] ?? "";
      });
      const numericKeys = [
        "count",
        "mean_sim",
        "max_sim",
        "coverage_min",
        "coverage_a",
        "coverage_b",
        "student_a_sent_total",
        "student_b_sent_total",
        "score",
      ];
      numericKeys.forEach((key) => {
        if (key in record && record[key] !== "") {
          record[key] = Number(record[key]);
        }
      });
      return record;
    });
};

const parsePair = (pairStr) => {
  const match =
    typeof pairStr === "string"
      ? pairStr.match(/['"]?([\w\-. ]+)['"]?\s*,\s*['"]?([\w\-. ]+)['"]?/)
      : null;
  if (match) {
    return { a: match[1], b: match[2] };
  }
  return { a: pairStr, b: "" };
};

const pairListToKey = (pairArr) => {
  if (!Array.isArray(pairArr) || pairArr.length < 2) {
    return String(pairArr);
  }
  return `(${pairArr[0]}, ${pairArr[1]})`;
};

const pairKeyToArray = (key) => {
  if (!key) return ["", ""];
  const match = key.match(/\(?\s*['"]?([^,'"]+)['"]?\s*,\s*['"]?([^,'"]+)['"]?\s*\)?/);
  if (match) {
    return [match[1], match[2]];
  }
  return [String(key), ""];
};

const fetchTextWithFallback = async (paths) => {
  for (const path of paths) {
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        return await resp.text();
      }
    } catch (err) {
      console.warn(`加载 ${path} 失败：`, err);
    }
  }
  throw new Error(`无法找到目标文件：${paths.join(", ")}`);
};

const fetchJSONWithFallback = async (paths) => {
  for (const path of paths) {
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (err) {
      console.warn(`加载 ${path} 失败：`, err);
    }
  }
  return {};
};

const buildPreview = (hits) => {
  if (!Array.isArray(hits) || hits.length === 0) return "";
  return hits
    .slice(0, 2)
    .map(
      (hit) =>
        `[${(hit.sim ?? 0).toFixed(2)}] ${hit.sid_i || "A"}: ${shorten(
          hit.text_i || ""
        )}\n↔ ${hit.sid_j || "B"}: ${shorten(hit.text_j || "")}`
    )
    .join("\n\n");
};

const fetchDocumentTexts = async (paths) => {
  for (const path of paths) {
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        return await resp.json();
      }
    } catch (err) {
      console.warn(`加载 ${path} 失败：`, err);
    }
  }
  return null;
};

const SummaryTable = ({ rows, selectedPair, onSelect }) => {
  if (!rows.length) {
    return <p className="placeholder">暂无数据。</p>;
  }

  return (
    <div className="card">
      <h2 className="card-title">总体概览</h2>
      <table className="summary-table">
        <thead>
          <tr>
            <th style={{ width: "20%" }}>学生组合</th>
            <th style={{ width: "12%" }}>count</th>
            <th style={{ width: "12%" }}>mean_sim</th>
            <th style={{ width: "12%" }}>max_sim</th>
            <th style={{ width: "12%" }}>coverage_min</th>
            <th style={{ width: "12%" }}>score</th>
            <th>preview</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const { a, b } = row.pairParsed;
            const pairLabel = `${a} ↔ ${b}`;
            const isSelected =
              selectedPair &&
              selectedPair.pairParsed.a === a &&
              selectedPair.pairParsed.b === b;
            return (
              <tr
                key={row.pair}
                className={isSelected ? "selected" : ""}
                onClick={() => onSelect(row)}
              >
                <td>{pairLabel}</td>
                <td>{row.count}</td>
                <td>{row.mean_sim.toFixed(3)}</td>
                <td>{row.max_sim.toFixed(3)}</td>
                <td>{row.coverage_min.toFixed(3)}</td>
                <td>
                  <span className="score-pill">{row.score.toFixed(3)}</span>
                </td>
                <td>
                  <pre className="preview">{row.preview || "-"}</pre>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const PairDetails = ({ row, pairDetails, evidence }) => {
  if (!row) {
    return (
      <div className="card">
        <p className="placeholder">请选择上方表格中的一组学生。</p>
      </div>
    );
  }
  const detail = pairDetails[row.pair];
  const hits = detail?.hits || evidence[row.pair] || [];
  const { a, b } = row.pairParsed;

  const leftSegments = new Map();
  const rightSegments = new Map();

  hits.slice(0, 12).forEach((hit, idx) => {
    const rawSim = hit.sim ?? 0;
    const sim = Math.max(0, Math.min(1, rawSim));
    const color = similarityToColor(sim);
    const highlight = similarityToColor(sim, 0.35);
    const label = idx + 1;

    const leftKey = `${hit.sid_i}-${hit.did_i}-${hit.i}`;
    if (!leftSegments.has(leftKey)) {
      leftSegments.set(leftKey, {
        label,
        color,
        highlight,
        sim,
        sid: hit.sid_i || a,
        did: hit.did_i || "",
        text: hit.text_i || "",
        index: hit.i,
      });
    }

    const rightKey = `${hit.sid_j}-${hit.did_j}-${hit.j}`;
    if (!rightSegments.has(rightKey)) {
      rightSegments.set(rightKey, {
        label,
        color,
        highlight,
        sim,
        sid: hit.sid_j || b,
        did: hit.did_j || "",
        text: hit.text_j || "",
        index: hit.j,
      });
    }
  });

  return (
    <div className="card">
      <div className="detail-header">
        <h2>
          {a} ↔ {b}
        </h2>
        <div className="metrics">
          <span>count: {row.count}</span>
          <span>mean_sim: {row.mean_sim.toFixed(3)}</span>
          <span>max_sim: {row.max_sim.toFixed(3)}</span>
          <span>coverage_min: {row.coverage_min.toFixed(3)}</span>
          <span>score: {row.score.toFixed(3)}</span>
        </div>
      </div>

      <div className="columns">
        <div className="column">
          <h3>{a}</h3>
          {leftSegments.size === 0 ? (
            <p className="empty">无匹配片段</p>
          ) : (
            Array.from(leftSegments.values()).map((seg) => (
              <div
                className="segment"
                key={`${seg.sid}-${seg.did}-${seg.index}`}
                style={{
                  "--highlight-color": seg.highlight,
                  borderColor: seg.highlight,
                }}
              >
                <span className="badge" style={{ backgroundColor: seg.color }}>
                  {seg.label}
                </span>
                <div className="meta">
                  {seg.sid}
                  {seg.did ? ` · ${seg.did}` : ""} · sent #{seg.index}
                  {typeof seg.sim === "number" ? ` · sim ${seg.sim.toFixed(3)}` : ""}
                </div>
                <div className="content">{seg.text}</div>
              </div>
            ))
          )}
        </div>
        <div className="column">
          <h3>{b}</h3>
          {rightSegments.size === 0 ? (
            <p className="empty">无匹配片段</p>
          ) : (
            Array.from(rightSegments.values()).map((seg) => (
              <div
                className="segment"
                key={`${seg.sid}-${seg.did}-${seg.index}`}
                style={{
                  "--highlight-color": seg.highlight,
                  borderColor: seg.highlight,
                }}
              >
                <span className="badge" style={{ backgroundColor: seg.color }}>
                  {seg.label}
                </span>
                <div className="meta">
                  {seg.sid}
                  {seg.did ? ` · ${seg.did}` : ""} · sent #{seg.index}
                  {typeof seg.sim === "number" ? ` · sim ${seg.sim.toFixed(3)}` : ""}
                </div>
                <div className="content">{seg.text}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const SentenceViewer = ({
  documents,
  selectedDocs,
  onSelectDocs,
  pairDetails = {},
  threshold,
  onThresholdChange,
}) => {
  const [left, right] = selectedDocs;
  const docKeys = Object.keys(documents);
  const effectiveThreshold =
    typeof threshold === "number" && !Number.isNaN(threshold)
      ? Math.max(0, Math.min(1, threshold))
      : DEFAULT_SIM_THRESHOLD;

  const handleChange = (side, value) => {
    const next = [...selectedDocs];
    next[side === "left" ? 0 : 1] = value || null;
    onSelectDocs(next);
  };

  const currentDetail = React.useMemo(() => {
    if (!left || !right) return null;
    const k1 = pairListToKey([left, right]);
    if (pairDetails && pairDetails[k1]) return pairDetails[k1];
    const k2 = pairListToKey([right, left]);
    return (pairDetails && pairDetails[k2]) || null;
  }, [left, right, pairDetails]);

  const sentencesForDoc = React.useMemo(() => {
    if (!currentDetail?.sentences) return {};
    return currentDetail.sentences;
  }, [currentDetail]);

  const renderDoc = (docId) => {
    if (!docId) {
      return <p className="empty">请选择一篇文章</p>;
    }
    const doc = documents[docId];
    if (!doc) {
      return <p className="empty">未找到文章内容</p>;
    }
    const sentenceEntries = sentencesForDoc[docId] || {};
    const sentenceNodes = doc.sentences.map((text, idx) => {
      const entry = sentenceEntries[idx];
      const hits = Array.isArray(entry?.hits) ? entry.hits : [];
      const matches = hits.filter((h) => typeof h.sim === "number" && h.sim >= effectiveThreshold);
      const bestSim = matches.length ? Math.max(...matches.map((h) => h.sim)) : null;
      const isSuspect = bestSim !== null;
      const inlineColor = isSuspect ? similarityToColor(bestSim, 0.35) : undefined;

      const sentenceContent = (
        <span
          className={`doc-inline-content${isSuspect ? " suspect" : ""}`}
          style={
            isSuspect
              ? {
                  "--highlight-color": inlineColor,
                }
              : undefined
          }
        >
          {text}
        </span>
      );
      const sentenceSimLabel = isSuspect && bestSim !== null ? (
        <span className="doc-inline-sim">{bestSim.toFixed(3)}</span>
      ) : null;

      return (
        <React.Fragment key={idx}>
          <span className={`docinline-sentence${isSuspect ? " suspect" : ""}`}>
            <span className="docinline-number">{idx + 1}.</span>
            {sentenceContent}
            {sentenceSimLabel}
          </span>
          {" "}
        </React.Fragment>
      );
    });

    return (
      <div className="doc-viewer">
        <h3>{docId}</h3>
        <p className="doc-paragraph">{sentenceNodes}</p>
      </div>
    );
  };

  return (
    <div className="card">
      <div className="viewer-header">
        <h2>文章对比查看</h2>
        <div className="viewer-controls">
          <div className="threshold-control">
            <label htmlFor="sim-threshold">相似度阈值：{effectiveThreshold.toFixed(2)}</label>
            <input
              id="sim-threshold"
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={effectiveThreshold}
              onChange={(e) => onThresholdChange?.(Number(e.target.value))}
            />
          </div>
          <div className="doc-select">
            <label>
              左侧：
              <select
                value={left || ""}
                onChange={(e) => handleChange("left", e.target.value)}
            >
              <option value="">请选择</option>
              {docKeys.map((docId) => (
                <option key={docId} value={docId}>
                  {docId}
                </option>
              ))}
            </select>
          </label>
          <label>
            右侧：
            <select
              value={right || ""}
              onChange={(e) => handleChange("right", e.target.value)}
            >
              <option value="">请选择</option>
              {docKeys.map((docId) => (
                <option key={docId} value={docId}>
                  {docId}
                </option>
              ))}
            </select>
          </label>
          </div>
        </div>
      </div>
      <div className="columns document-columns">
        <div className="column">{renderDoc(left)}</div>
        <div className="column">{renderDoc(right)}</div>
      </div>
    </div>
  );
};

function App() {
  const [rows, setRows] = React.useState([]);
  const [evidence, setEvidence] = React.useState({});
  const [pairDetails, setPairDetails] = React.useState({});
  const [documents, setDocuments] = React.useState({});
  const [selectedDocs, setSelectedDocs] = React.useState([null, null]);
  const [selected, setSelected] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [simThreshold, setSimThreshold] = React.useState(DEFAULT_SIM_THRESHOLD);

  React.useEffect(() => {
    const load = async () => {
      try {
        const base = process.env.PUBLIC_URL || "";
        const csvText = await fetchTextWithFallback([
          `${base}/pair_summary.csv`,
          "./pair_summary.csv",
          "/pair_summary.csv",
          "pair_summary.csv",
        ]);
        const parsedRows = parseCSV(csvText);

        const detailCandidate = await fetchJSONWithFallback([
          `${base}/pair_results.json`,
          "./pair_results.json",
          "/pair_results.json",
          "pair_results.json",
        ]);
        let detailMap = {};
        let evidenceData = {};
        const transformHitsToSentences = (pairHits = []) => {
          const sentences = {};
          const normalizedHits = [];
          const ensure = (sid, sentId, text, did) => {
            if (!sentences[sid]) sentences[sid] = {};
            if (!sentences[sid][sentId]) {
              sentences[sid][sentId] = {
                text,
                did,
                hits: [],
              };
            }
            return sentences[sid][sentId];
          };
          pairHits.forEach((hit) => {
            if (!hit) return;
            const {
              sid_i,
              sid_j,
              sent_id_i,
              sent_id_j,
              text_i,
              text_j,
              did_i,
              did_j,
              sim,
              i,
              j,
            } = hit;
            const numericSim = typeof sim === "number" ? sim : Number(sim);
            const normalized = {
              i: typeof i === "number" ? i : null,
              j: typeof j === "number" ? j : null,
              sim: numericSim,
              sid_i,
              sid_j,
              did_i,
              did_j,
              sent_id_i,
              sent_id_j,
              text_i,
              text_j,
            };
            normalizedHits.push(normalized);

            if (sid_i != null && typeof sent_id_i === "number") {
              const entry = ensure(sid_i, sent_id_i, text_i, did_i);
              entry.hits.push({
                other_sid: sid_j,
                other_sent_id: sent_id_j,
                other_text: text_j,
                sim: numericSim,
              });
            }
            if (sid_j != null && typeof sent_id_j === "number") {
              const entry = ensure(sid_j, sent_id_j, text_j, did_j);
              entry.hits.push({
                other_sid: sid_i,
                other_sent_id: sent_id_i,
                other_text: text_i,
                sim: numericSim,
              });
            }
          });
          return { normalizedHits, sentences };
        };

        if (detailCandidate && Array.isArray(detailCandidate.pairs)) {
          detailCandidate.pairs.forEach((detail) => {
            const key = pairListToKey(detail.pair);
            let sentences = detail.sentences;
            let hits = detail.hits || [];
            if (!sentences) {
              const converted = transformHitsToSentences(detail.hits || []);
              hits = converted.normalizedHits;
              sentences = converted.sentences;
            }
            detailMap[key] = {
              ...detail,
              hits,
              sentences,
            };
            evidenceData[key] = hits;
          });
        } else {
          evidenceData = await fetchJSONWithFallback([
            `${base}/evidence_top.json`,
            "./evidence_top.json",
            "/evidence_top.json",
            "evidence_top.json",
          ]);
          detailMap = Object.fromEntries(
            Object.entries(evidenceData).map(([key, hits]) => {
              const pair = pairKeyToArray(key);
              const converted = transformHitsToSentences(Array.isArray(hits) ? hits : []);
              return [
                key,
                {
                  pair,
                  hits: converted.normalizedHits,
                  sentences: converted.sentences,
                },
              ];
            })
          );
          Object.entries(detailMap).forEach(([key, detail]) => {
            evidenceData[key] = detail.hits;
          });
        }

        const enrichedRows = parsedRows.map((row) => {
          const pairParsed = parsePair(row.pair);
          const preview = buildPreview(evidenceData[row.pair]);
          return { ...row, pairParsed, preview };
        });

        const docs = await fetchDocumentTexts([
          `${base}/documents.json`,
          "./documents.json",
          "/documents.json",
          "documents.json",
        ]);
        if (docs) {
          setDocuments(docs);
        } else {
          console.warn("documents.json 未找到，文章对比功能不可用。");
        }

        setRows(enrichedRows);
        setEvidence(evidenceData);
        setPairDetails(detailMap);
        if (!selectedDocs[0] && enrichedRows[0]) {
          setSelectedDocs([enrichedRows[0].pairParsed.a, enrichedRows[0].pairParsed.b]);
        }
        setSelected(enrichedRows[0] || null);
      } catch (err) {
        setError(err.message || "加载数据失败");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="page">
      <h1>相似作业可视化报告</h1>
      {loading && <p className="placeholder">正在载入数据…</p>}
      {error && <p className="placeholder error">{error}</p>}
      {!loading && !error && (
        <>
          <SummaryTable
            rows={rows}
            selectedPair={selected}
            onSelect={setSelected}
          />
          <PairDetails
            row={selected}
            evidence={evidence}
            pairDetails={pairDetails}
          />
          <SentenceViewer
            documents={documents}
            selectedDocs={selectedDocs}
            onSelectDocs={setSelectedDocs}
            pairDetails={pairDetails}
            threshold={simThreshold}
            onThresholdChange={setSimThreshold}
          />
        </>
      )}
    </div>
  );
}

export default App;
