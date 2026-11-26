import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  Binary,
  CheckCircle2,
  Clock3,
  Code2,
  Cpu,
  Database,
  FileCode2,
  GitBranch,
  Layers,
  LayoutDashboard,
  Menu,
  Play,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Terminal,
  X,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const API = 'http://127.0.0.1:5000/api';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, group: 'WORKSPACE' },
  { id: 'lexer', label: '01 · MiniLang & Lexer', icon: Binary, group: 'COMPILER MODULES' },
  { id: 'parser', label: '02 · Parser & AST', icon: GitBranch, group: 'COMPILER MODULES' },
  { id: 'semantic', label: '03 · Semantic & Symbol Table', icon: ShieldCheck, group: 'COMPILER MODULES' },
  { id: 'optimizer', label: '04 · IR & Optimization', icon: Layers, group: 'COMPILER MODULES' },
  { id: 'codegen', label: '05 · Target Code & Run', icon: Terminal, group: 'COMPILER MODULES' },
  { id: 'history', label: 'Compilation History', icon: Clock3, group: 'INSIGHTS' },
  { id: 'database', label: 'Database Explorer', icon: Database, group: 'SYSTEM' },
];

const DEFAULT_SOURCE = `# MiniLang Compiler Studio — 5-Phase Demo
LET base_val: INT = 20 + 10 * 2;
LET scale: FLOAT = 1.5;
LET final_val: FLOAT = base_val * scale;
LET banner: STR = "MiniLang Executed Cleanly!";

DISPLAY banner;
DISPLAY final_val;
`;

async function callApi(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function AstTreeView({ node, depth = 0 }) {
  if (!node) return null;
  const kids = node.children || [];
  return (
    <div style={{ marginLeft: depth === 0 ? 0 : 18, paddingLeft: depth === 0 ? 0 : 12, borderLeft: depth === 0 ? 'none' : '1px dashed #3a4c70', marginTop: 6 }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '5px 10px', borderRadius: 8, background: '#142038', border: '1px solid #2f4269', fontSize: 12 }}>
        <span className="mono" style={{ fontSize: 10, color: '#9eb0ff' }}>{node.kind}</span>
        <strong className="mono">{node.label}</strong>
        <span style={{ fontSize: 10, color: '#7b8ba8' }}>L{node.line || 1}</span>
      </div>
      {kids.map((c) => (
        <AstTreeView key={c.id} node={c} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState('overview');
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [programName, setProgramName] = useState('MiniLang Demo');
  const [optimize, setOptimize] = useState(true);
  const [result, setResult] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [history, setHistory] = useState([]);
  const [dbSummary, setDbSummary] = useState(null);
  const [dbTable, setDbTable] = useState('compilation_runs');
  const [dbRows, setDbRows] = useState([]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const loadLists = useCallback(async () => {
    try {
      const [progs, hist, summary] = await Promise.all([
        callApi('/programs'),
        callApi('/history'),
        callApi('/database/summary'),
      ]);
      setPrograms(progs);
      setHistory(hist);
      setDbSummary(summary);
      setStatusMsg('');
    } catch (e) {
      setStatusMsg(`Backend offline (${e.message}). Run START_APP.bat or run-backend.bat first.`);
    }
  }, []);

  const runCompile = useCallback(async (src = source, opt = optimize, title = programName) => {
    setBusy(true);
    try {
      const data = await callApi('/compile', {
        method: 'POST',
        body: JSON.stringify({ source: src, optimize: opt, program_name: title }),
      });
      setResult(data);
      const [hist, summary] = await Promise.all([callApi('/history'), callApi('/database/summary')]);
      setHistory(hist);
      setDbSummary(summary);
      setStatusMsg('');
    } catch (e) {
      setStatusMsg(`Compile error: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }, [source, optimize, programName]);

  const saveCurrentProgram = async () => {
    try {
      await callApi('/programs', {
        method: 'POST',
        body: JSON.stringify({ title: programName || 'Custom Sample', category: 'Saved', source }),
      });
      await loadLists();
      setStatusMsg('Saved sample program to SQLite.');
    } catch (e) {
      setStatusMsg(e.message);
    }
  };

  const loadDbRows = useCallback(async (tbl) => {
    try {
      const res = await callApi(`/database/${tbl}`);
      setDbTable(tbl);
      setDbRows(res.rows || []);
    } catch (e) {
      setStatusMsg(e.message);
    }
  }, []);

  useEffect(() => {
    loadLists();
    runCompile(DEFAULT_SOURCE, true, 'MiniLang Demo');
  }, []);

  useEffect(() => {
    if (page === 'database') {
      loadDbRows(dbTable);
    }
  }, [page, dbTable, loadDbRows]);

  const activeNav = NAV_ITEMS.find((n) => n.id === page) || NAV_ITEMS[0];
  const chartData = [
    { stage: 'Tokens', count: result?.tokens?.length || 0 },
    { stage: 'Symbols', count: result?.symbolTable?.length || 0 },
    { stage: 'TAC Raw', count: result?.tacBefore?.length || 0 },
    { stage: 'TAC Opt', count: result?.tacAfter?.length || 0 },
    { stage: 'Folded', count: result?.foldedConstants || 0 },
  ];

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark"><Code2 size={20} /></div>
          <div>
            <div className="brand-name">Compiler<span>Lab</span></div>
            <div className="brand-sub">MINILANG STUDIO</div>
          </div>
          <button className="secondary-btn mobile-btn" style={{ marginLeft: 'auto', padding: 6 }} onClick={() => setMobileOpen(false)}>
            <X size={16} />
          </button>
        </div>

        <div className="workspace-chip">
          <div className="workspace-avatar">CD</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700 }}>Compiler Design</div>
            <div style={{ fontSize: 10, color: '#7e8ea9' }}>5-Phase Pipeline</div>
          </div>
        </div>

        {['WORKSPACE', 'COMPILER MODULES', 'INSIGHTS', 'SYSTEM'].map((grp) => (
          <div className="nav-group" key={grp}>
            <div className="nav-label">{grp}</div>
            {NAV_ITEMS.filter((item) => item.group === grp).map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  className={`nav-item ${page === item.id ? 'active' : ''}`}
                  onClick={() => {
                    setPage(item.id);
                    setMobileOpen(false);
                  }}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                  {item.id === 'database' && <span className="nav-badge">SQL</span>}
                </button>
              );
            })}
          </div>
        ))}

        <div className="sidebar-bottom">
          <div className="engine-box">
            <span className="status-dot" />
            <div>
              <div style={{ fontWeight: 700, fontSize: 11 }}>Flask + SQLite Engine</div>
              <div style={{ fontSize: 10, color: '#7d8da8' }}>Port 5000 · Local DB</div>
            </div>
          </div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="secondary-btn mobile-btn" onClick={() => setMobileOpen(true)}>
              <Menu size={18} />
            </button>
            <div className="breadcrumb">
              CompilerLab <span>/</span> <strong>{activeNav.label}</strong>
            </div>
          </div>

          <div className="topbar-actions">
            <div className="conn-pill">
              <span className="status-dot" /> Backend API
            </div>
            <button className="secondary-btn" onClick={() => { loadLists(); runCompile(source, optimize, programName); }}>
              <RefreshCw size={14} /> Refresh
            </button>
            <button className="primary-btn" onClick={() => runCompile(source, optimize, programName)} disabled={busy}>
              <Play size={14} /> {busy ? 'Compiling...' : 'Compile & Run'}
            </button>
          </div>
        </header>

        <main className="page-body">
          {statusMsg && (
            <div className="banner-err">
              <span>{statusMsg}</span>
            </div>
          )}

          {result && result.diagnostics?.length > 0 && (
            <div className="banner-err">
              <div>
                <strong>Diagnostics ({result.diagnostics.length}):</strong>{' '}
                {result.diagnostics.map((d, idx) => `[${d.stage} L${d.line}] ${d.message}`).join(' · ')}
              </div>
            </div>
          )}

          {result && (!result.diagnostics || result.diagnostics.length === 0) && (
            <div className="banner-ok">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontWeight: 700 }}>
                <CheckCircle2 size={15} /> Compiled &amp; Executed Cleanly
              </span>
              <span className="mono" style={{ fontSize: 11 }}>
                Folded: {result.foldedConstants} · Time: {result.execution?.durationMs ?? 0} ms
              </span>
            </div>
          )}

          <div className="page-head">
            <div>
              <div className="eyebrow">COMPILER DESIGN / INTERACTIVE WORKBENCH</div>
              <h1>{activeNav.label}</h1>
              <p>Click any module in the left sidebar or use the quick stage buttons to inspect each compiler phase.</p>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {['lexer', 'parser', 'semantic', 'optimizer', 'codegen'].map((stageId, idx) => (
                <button
                  key={stageId}
                  className={page === stageId ? 'primary-btn' : 'secondary-btn'}
                  onClick={() => setPage(stageId)}
                >
                  Mod 0{idx + 1}
                </button>
              ))}
            </div>
          </div>

          <div className="metrics-row">
            <div className="metric-box">
              <div className="metric-top"><span>Tokens Generated</span><Binary size={16} color="#7c8cff" /></div>
              <div className="metric-num">{result?.tokens?.length ?? 0}</div>
              <div className="metric-sub">Module 01 Lexical Scanner</div>
            </div>
            <div className="metric-box">
              <div className="metric-top"><span>Symbol Table Entries</span><ShieldCheck size={16} color="#39d9c6" /></div>
              <div className="metric-num">{result?.symbolTable?.length ?? 0}</div>
              <div className="metric-sub">Module 03 Semantic Scope</div>
            </div>
            <div className="metric-box">
              <div className="metric-top"><span>Constants Folded</span><Sparkles size={16} color="#bc91ff" /></div>
              <div className="metric-num">{result?.foldedConstants ?? 0}</div>
              <div className="metric-sub">Module 04 IR Optimization</div>
            </div>
            <div className="metric-box">
              <div className="metric-top"><span>Execution Time</span><Cpu size={16} color="#ffb86b" /></div>
              <div className="metric-num">{result?.execution?.durationMs ?? 0} <small style={{ fontSize: 12 }}>ms</small></div>
              <div className="metric-sub">Module 05 Target Output</div>
            </div>
          </div>

          {page === 'overview' && (
            <>
              <div className="hero-card">
                <div>
                  <div className="eyebrow">MINI COMPILER ARCHITECTURE</div>
                  <h2>MiniLang <span>5-Phase</span> Translation Pipeline</h2>
                  <p>
                    Write MiniLang code, run lexical and syntax parsing, verify types and symbols, optimize Three-Address Code with constant folding, and execute generated Python target code.
                  </p>
                </div>
                <button className="primary-btn" onClick={() => setPage('lexer')}>
                  Open Module 01 <Play size={14} />
                </button>
              </div>

              <div className="grid-2">
                <section className="panel">
                  <div className="panel-title">
                    <span>MiniLang Source Editor</span>
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 500 }}>
                      <input type="checkbox" checked={optimize} onChange={(e) => setOptimize(e.target.checked)} />
                      Constant Folding
                    </label>
                  </div>
                  <div className="sample-row">
                    {programs.map((p) => (
                      <button
                        key={p.id}
                        className="secondary-btn"
                        style={{ fontSize: 11, padding: '6px 10px' }}
                        onClick={() => {
                          setProgramName(p.title);
                          setSource(p.source_code);
                          runCompile(p.source_code, optimize, p.title);
                        }}
                      >
                        {p.title}
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                    <input
                      value={programName}
                      onChange={(e) => setProgramName(e.target.value)}
                      placeholder="Program title"
                      style={{ flex: 1, background: '#090f1d', border: '1px solid #2a3954', color: '#e6eeff', borderRadius: 8, padding: '7px 10px', fontSize: 12 }}
                    />
                    <button className="secondary-btn" onClick={saveCurrentProgram}>
                      <Save size={13} /> Save Sample
                    </button>
                  </div>
                  <textarea className="editor-area" value={source} onChange={(e) => setSource(e.target.value)} />
                </section>

                <section className="panel">
                  <div className="panel-title">
                    <span>Compiler Stage Counts</span>
                    <BarChart3 size={16} color="#7c8cff" />
                  </div>
                  <div style={{ height: 240 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid stroke="#23314a" strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="stage" tick={{ fill: '#94a4c0', fontSize: 11 }} />
                        <YAxis tick={{ fill: '#94a4c0', fontSize: 11 }} allowDecimals={false} />
                        <Tooltip contentStyle={{ background: '#111b2e', border: '1px solid #2a3a58', borderRadius: 8, color: '#eef3ff' }} />
                        <Bar dataKey="count" fill="#7c8cff" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ marginTop: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>Latest Target Output</div>
                    <pre className="code-pre" style={{ minHeight: 74 }}>
                      {result?.execution?.stdout || result?.execution?.stderr || 'No stdout yet.'}
                    </pre>
                  </div>
                </section>
              </div>
            </>
          )}

          {page === 'lexer' && (
            <div className="grid-2">
              <section className="panel">
                <div className="panel-title"><span>Source Input</span></div>
                <textarea className="editor-area" value={source} onChange={(e) => setSource(e.target.value)} />
                <div style={{ marginTop: 10 }}>
                  <button className="primary-btn" onClick={() => runCompile(source, optimize, programName)}>
                    <Play size={14} /> Run Lexer
                  </button>
                </div>
              </section>
              <section className="panel">
                <div className="panel-title"><span>Token Stream ({result?.tokens?.length ?? 0})</span></div>
                <div className="token-cards">
                  {(result?.tokens || []).map((t, idx) => (
                    <div className="tok-box" key={idx}>
                      <span className="tok-tag">{t.type}</span>
                      <div className="mono" style={{ fontWeight: 700, fontSize: 13 }}>{t.value}</div>
                      <div style={{ fontSize: 10, color: '#7c8ca8', marginTop: 4 }}>Line {t.line}, Col {t.column}</div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}

          {page === 'parser' && (
            <div className="grid-2">
              <section className="panel">
                <div className="panel-title"><span>Source Input</span></div>
                <textarea className="editor-area" value={source} onChange={(e) => setSource(e.target.value)} />
                <div style={{ marginTop: 10 }}>
                  <button className="primary-btn" onClick={() => runCompile(source, optimize, programName)}>
                    <Play size={14} /> Parse AST
                  </button>
                </div>
              </section>
              <section className="panel">
                <div className="panel-title"><span>Abstract Syntax Tree (AST)</span></div>
                <div style={{ maxHeight: 440, overflow: 'auto', padding: 6 }}>
                  <AstTreeView node={optimize ? result?.optimizedAst : result?.ast} />
                </div>
              </section>
            </div>
          )}

          {page === 'semantic' && (
            <section className="panel">
              <div className="panel-title"><span>Symbol Table &amp; Type Checking</span></div>
              <table className="data-tbl">
                <thead>
                  <tr>
                    <th>Identifier</th>
                    <th>Type</th>
                    <th>Scope</th>
                    <th>Declared Line</th>
                    <th>Initialized</th>
                    <th>Used</th>
                  </tr>
                </thead>
                <tbody>
                  {(result?.symbolTable || []).map((s, idx) => (
                    <tr key={idx}>
                      <td className="mono" style={{ fontWeight: 700 }}>{s.name}</td>
                      <td>{s.type}</td>
                      <td>{s.scope}</td>
                      <td>L{s.declaredLine}</td>
                      <td>{s.initialized ? 'Yes' : 'No'}</td>
                      <td>{s.used ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {page === 'optimizer' && (
            <div className="grid-2">
              <section className="panel">
                <div className="panel-title"><span>Before Optimization (Three-Address Code)</span></div>
                <pre className="code-pre">{(result?.tacBefore || []).join('\n') || '# Empty'}</pre>
              </section>
              <section className="panel">
                <div className="panel-title"><span>After Constant Folding ({result?.foldedConstants ?? 0} folded)</span></div>
                <pre className="code-pre">{(result?.tacAfter || []).join('\n') || '# Empty'}</pre>
              </section>
            </div>
          )}

          {page === 'codegen' && (
            <div className="grid-2">
              <section className="panel">
                <div className="panel-title"><span>Generated Python Target Code</span></div>
                <pre className="code-pre">{result?.targetCode || '# No code'}</pre>
              </section>
              <section className="panel">
                <div className="panel-title"><span>Execution Output (stdout)</span></div>
                <pre className="code-pre" style={{ background: '#07221f', borderColor: '#1d5b54', color: '#9ff7ec' }}>
                  {result?.execution?.stdout || result?.execution?.stderr || '(No output)'}
                </pre>
              </section>
            </div>
          )}

          {page === 'history' && (
            <section className="panel">
              <div className="panel-title"><span>Recent Compilation Runs ({history.length})</span></div>
              <table className="data-tbl">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Program</th>
                    <th>Status</th>
                    <th>Tokens</th>
                    <th>Folded</th>
                    <th>Time (ms)</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id}>
                      <td>#{h.id}</td>
                      <td>{h.program_name}</td>
                      <td>{h.success ? 'Success' : 'Error'}</td>
                      <td>{h.token_count}</td>
                      <td>{h.folded_constants}</td>
                      <td>{h.duration_ms}</td>
                      <td>
                        <button
                          className="secondary-btn"
                          style={{ padding: '4px 9px', fontSize: 11 }}
                          onClick={() => {
                            setSource(h.source_code);
                            setProgramName(h.program_name);
                            runCompile(h.source_code, Boolean(h.optimize_enabled), h.program_name);
                            setPage('overview');
                          }}
                        >
                          Load
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {page === 'database' && (
            <section className="panel">
              <div className="panel-title">
                <span>SQLite Database Explorer ({dbSummary?.database_file || 'database/compiler_studio.db'})</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['compilation_runs', 'saved_programs'].map((t) => (
                    <button
                      key={t}
                      className={dbTable === t ? 'primary-btn' : 'secondary-btn'}
                      onClick={() => loadDbRows(t)}
                    >
                      {t} ({dbSummary?.tables?.[t] ?? 0})
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="data-tbl">
                  <thead>
                    <tr>
                      {(dbRows[0] ? Object.keys(dbRows[0]) : ['id']).map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dbRows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {Object.values(row).map((val, cIdx) => (
                          <td key={cIdx} className="mono" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {String(val ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </main>

        <footer className="footer">
          <span>CompilerLab · 5-Phase MiniLang Studio</span>
          <span>Flask Backend + SQLite + React Vite</span>
        </footer>
      </div>
    </div>
  );
}
