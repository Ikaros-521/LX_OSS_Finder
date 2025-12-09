import React, { useEffect, useRef, useState } from "react";
import ResultCard from "./components/ResultCard";
import { RepoResult } from "./types";

// 生产环境使用相对路径，开发环境使用配置的地址
const API_BASE = import.meta.env.VITE_API_BASE || 
  (import.meta.env.PROD ? "/api" : "http://localhost:8020");

const App: React.FC = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<RepoResult[]>([]);
  const [intent, setIntent] = useState<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const [perPage, setPerPage] = useState(12);
  const [includeName, setIncludeName] = useState(true);
  const [includeDescription, setIncludeDescription] = useState(true);
  const [includeReadme, setIncludeReadme] = useState(true);
  const [includeTopics, setIncludeTopics] = useState(true);
  const [pushedWithinDays, setPushedWithinDays] = useState(1825); // 5 年
  const [minStars, setMinStars] = useState(0);
  const [useCache, setUseCache] = useState(false);
  const [limit, setLimit] = useState(10);
  const [sort, setSort] = useState<"best" | "stars" | "updated">("best");

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const runSearch = () => {
    if (!query.trim()) return;
    // close previous stream
    eventSourceRef.current?.close();

    setLoading(true);
    setError(null);
    setResults([]);
    setIntent([]);

    const params = new URLSearchParams({
      query: query.trim(),
      use_cache: String(useCache),
      per_page: String(perPage),
      include_name: String(includeName),
      include_description: String(includeDescription),
      include_readme: String(includeReadme),
      include_topics: String(includeTopics),
      pushed_within_days: String(pushedWithinDays),
      min_stars: String(minStars),
      limit: String(limit),
      sort,
    });
    const url = `${API_BASE}/search/stream?${params.toString()}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.addEventListener("intent", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        setIntent(data.keywords || []);
      } catch {
        // ignore parse errors
      }
    });

    es.addEventListener("item", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data) as RepoResult;
        setResults((prev) => [...prev, data]);
      } catch (err) {
        console.error("parse item error", err);
      }
    });

    es.addEventListener("error", (e) => {
      const msg = (e as MessageEvent).data || "Stream error";
      setError(typeof msg === "string" ? msg : "Stream error");
      setLoading(false);
      es.close();
    });

    es.addEventListener("done", () => {
      setLoading(false);
      es.close();
    });
  };

  const cancelSearch = () => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <header className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-3xl font-bold text-slate-900">洛曦开源项目检索器</h1>
        <p className="mt-2 text-slate-600">
          输入需求，自动匹配高质量开源仓库（GitHub）。接口基于 FastAPI + OpenAI + GitHub API。
        </p>
      </header>

      <main className="mx-auto max-w-4xl px-4 pb-12">
        <div className="rounded-2xl bg-white p-6 shadow-md ring-1 ring-slate-200">
          <label className="block text-sm font-medium text-slate-700">需求描述</label>
          <div className="mt-2 flex flex-col gap-3 md:flex-row">
            <input
              type="text"
              placeholder="例如：想做抖音直播弹幕自动发送"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-3 text-base shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            />
            <div className="flex gap-2">
              <button
                onClick={runSearch}
                disabled={loading}
                className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "流式检索中..." : "立即搜索"}
              </button>
              <button
                onClick={cancelSearch}
                disabled={!loading}
                className="inline-flex items-center justify-center rounded-xl border border-slate-300 px-4 py-3 text-slate-700 shadow-sm transition hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                停止
              </button>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-wrap items-center gap-3 text-sm text-slate-700">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={includeName} onChange={(e) => setIncludeName(e.target.checked)} />
                搜仓库名（in:name）
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeDescription}
                  onChange={(e) => setIncludeDescription(e.target.checked)}
                />
                搜简介（in:description）
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeReadme}
                  onChange={(e) => setIncludeReadme(e.target.checked)}
                />
                搜 README（in:readme）
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeTopics}
                  onChange={(e) => setIncludeTopics(e.target.checked)}
                />
                搜 Topics（topic:kw）
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={useCache} onChange={(e) => setUseCache(e.target.checked)} />
                使用缓存
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
              <label className="flex flex-col gap-1">
                <span>每页拉取</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={perPage}
                  onChange={(e) => setPerPage(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                  className="rounded border border-slate-200 px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span>排序</span>
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as "best" | "stars" | "updated")}
                  className="rounded border border-slate-200 px-2 py-1"
                >
                  <option value="best">相关度（默认）</option>
                  <option value="stars">星标（高到低）</option>
                  <option value="updated">最近更新</option>
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span>最小 Stars</span>
                <input
                  type="number"
                  min={0}
                  value={minStars}
                  onChange={(e) => setMinStars(Math.max(0, Number(e.target.value) || 0))}
                  className="rounded border border-slate-200 px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span>最近更新（天内）</span>
                <input
                  type="number"
                  min={0}
                  max={2000}
                  value={pushedWithinDays}
                  onChange={(e) =>
                    setPushedWithinDays(Math.max(0, Math.min(2000, Number(e.target.value) || 0)))
                  }
                  className="rounded border border-slate-200 px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span>返回结果数（上限）</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={limit}
                  onChange={(e) => setLimit(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                  className="rounded border border-slate-200 px-2 py-1"
                />
              </label>
            </div>
          </div>
          {intent.length > 0 && (
            <div className="mt-3 text-sm text-slate-600">
              解析关键词：{" "}
              {intent.map((kw) => (
                <span key={kw} className="mr-2 rounded bg-slate-100 px-2 py-1">
                  {kw}
                </span>
              ))}
            </div>
          )}
          {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
        </div>

        <div className="mt-6 space-y-4">
          {results.map((repo) => (
            <ResultCard repo={repo} key={repo.full_name} />
          ))}
          {!loading && results.length === 0 && (
            <p className="text-center text-sm text-slate-500">暂无结果，试试更明确的描述或更换关键词。</p>
          )}
          {loading && results.length === 0 && (
            <p className="text-center text-sm text-slate-500">正在流式获取结果...</p>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;

