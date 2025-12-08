import React from "react";
import { RepoResult } from "../types";

type Props = {
  repo: RepoResult;
};

const ResultCard: React.FC<Props> = ({ repo }) => {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <a
          href={repo.html_url}
          target="_blank"
          rel="noreferrer"
          className="text-lg font-semibold text-indigo-600 hover:underline"
        >
          {repo.full_name}
        </a>
        <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">
          Score {repo.score.toFixed(2)}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-700">{repo.description}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
        {repo.language && <span className="rounded bg-slate-100 px-2 py-1">{repo.language}</span>}
        <span className="rounded bg-slate-100 px-2 py-1">⭐ {repo.stars}</span>
        <span className="rounded bg-slate-100 px-2 py-1">Updated {repo.updated_at?.slice(0, 10)}</span>
        {repo.topics.slice(0, 3).map((topic) => (
          <span key={topic} className="rounded bg-emerald-50 px-2 py-1 text-emerald-700">
            {topic}
          </span>
        ))}
      </div>
      <p className="mt-3 text-sm text-slate-800">{repo.reason}</p>
    </div>
  );
};

export default ResultCard;

