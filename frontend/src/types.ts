export type RepoResult = {
  name: string;
  full_name: string;
  html_url: string;
  description?: string;
  language?: string;
  stars: number;
  updated_at: string;
  topics: string[];
  score: number;
  reason: string;
};

export type SearchResponse = {
  query: string;
  intent_keywords: string[];
  results: RepoResult[];
};

