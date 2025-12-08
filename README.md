<div align="center">
  <a href="#">
    <img src="https://raw.githubusercontent.com/LuoXi-Project/LX_Project_Template/refs/heads/main/ui/logo.png" width="240" height="240" alt="点我跳转文档">
  </a>
</div>

<div align="center">

# ✨ 洛曦开源项目检索器  ✨

[![][python]][python]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]
[![][github-forks-shield]][github-forks-link]
[![][github-issues-shield]][github-issues-link]  
[![][github-contributors-shield]][github-contributors-link]
[![][github-license-shield]][github-license-link]

</div>

基于 FastAPI + React 的开源项目智能检索器：将自然语言需求转为 GitHub 高级搜索，结合可用性评分与 LLM 解释，返回 Top3 推荐。

## 功能概览
- /search POST：接收 `{ "query": "..." }`，自动解析意图、构造 GitHub 搜索、计算综合评分、用 LLM 生成简短推荐理由。
- 缓存：相同查询 1 小时内复用结果，减少 GitHub / LLM 调用。
- 前端：React + Tailwind 简洁搜索页，展示评分、理由和 GitHub 链接。

## 环境变量
放在根目录 `.env`（后端读取）：
```
OPENAI_API_KEY=your_key
# 可选：自建或代理
# OPENAI_API_BASE=https://api.example/v1
GITHUB_TOKEN=your_github_token   # 推荐，避免匿名限流
CORS_ORIGINS=["http://localhost:5173"]
```

GITHUB_TOKEN获取：[GitHub OAuth](https://github.com/settings/tokens/new?description=lx-project-searcher)。

## 后端（FastAPI）
```
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020
```

主要模块：
- `services/intent_parser.py`：调用 OpenAI 将自然语言转为搜索关键词/语言过滤。
- `datasources/github_adapter.py`：生成高级搜索并调用 GitHub REST v3。
- `services/scoring.py`：活跃度、更新、新鲜度、文档线索综合得分。
- `services/reasoner.py`：基于仓库元数据的简短推荐理由（LLM）。
- `services/cache.py`：内存 TTL 缓存。

## 前端（React + Vite + Tailwind）
```
cd frontend
npm install
npm run dev   # 默认 5173
```
可通过 `.env` 设置后端地址：
```
VITE_API_BASE=http://localhost:8020
```

## 后续扩展
- 在 `app/datasources/` 下新增 gitee、gitlab 适配器并实现同样的 `search_repositories` 接口。
- 增加更细的评分维度（issue 响应速度、CI 状态）。
- 为关键逻辑添加单元测试与快照数据。



## 💡 提问的智慧

提交issues前请先阅读以下内容

https://lug.ustc.edu.cn/wiki/doc/smart-questions

## 🀅 开发&项目相关

可以使用 GitHub Codespaces 进行在线开发：

[![][github-codespace-shield]][github-codespace-link]  



## ⭐️ Star 经历

[![Star History Chart](https://api.star-history.com/svg?repos=Ikaros-521/LX_OSS_Finder&type=Date)](https://star-history.com/#Ikaros-521/LX_OSS_Finder&Date)


## 更新日志




[python]: https://img.shields.io/badge/python-3.10+-blue.svg?labelColor=black
[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-black?style=flat-square
[github-action-release-link]: https://github.com/actions/workflows/Ikaros-521/LX_OSS_Finder/release.yml
[github-action-release-shield]: https://img.shields.io/github/actions/workflow/status/Ikaros-521/LX_OSS_Finder/release.yml?label=release&labelColor=black&logo=githubactions&logoColor=white&style=flat-square
[github-action-test-link]: https://github.com/actions/workflows/Ikaros-521/LX_OSS_Finder/test.yml
[github-action-test-shield]: https://img.shields.io/github/actions/workflow/status/Ikaros-521/LX_OSS_Finder/test.yml?label=test&labelColor=black&logo=githubactions&logoColor=white&style=flat-square
[github-codespace-link]: https://codespaces.new/Ikaros-521/LX_OSS_Finder
[github-codespace-shield]: https://github.com/codespaces/badge.svg
[github-contributors-link]: https://github.com/Ikaros-521/LX_OSS_Finder/graphs/contributors
[github-contributors-shield]: https://img.shields.io/github/contributors/Ikaros-521/LX_OSS_Finder?color=c4f042&labelColor=black&style=flat-square
[github-forks-link]: https://github.com/Ikaros-521/LX_OSS_Finder/network/members
[github-forks-shield]: https://img.shields.io/github/forks/Ikaros-521/LX_OSS_Finder?color=8ae8ff&labelColor=black&style=flat-square
[github-issues-link]: https://github.com/Ikaros-521/LX_OSS_Finder/issues
[github-issues-shield]: https://img.shields.io/github/issues/Ikaros-521/LX_OSS_Finder?color=ff80eb&labelColor=black&style=flat-square
[github-license-link]: https://github.com/Ikaros-521/LX_OSS_Finder/blob/main/LICENSE
[github-license-shield]: https://img.shields.io/github/license/Ikaros-521/LX_OSS_Finder?color=white&labelColor=black&style=flat-square
[github-release-link]: https://github.com/Ikaros-521/LX_OSS_Finder/releases
[github-release-shield]: https://img.shields.io/github/v/release/Ikaros-521/LX_OSS_Finder?color=369eff&labelColor=black&logo=github&style=flat-square
[github-releasedate-link]: https://github.com/Ikaros-521/LX_OSS_Finder/releases
[github-releasedate-shield]: https://img.shields.io/github/release-date/Ikaros-521/LX_OSS_Finder?labelColor=black&style=flat-square
[github-stars-link]: https://github.com/Ikaros-521/LX_OSS_Finder/network/stargazers
[github-stars-shield]: https://img.shields.io/github/stars/Ikaros-521/LX_OSS_Finder?color=ffcb47&labelColor=black&style=flat-square
[pr-welcome-link]: https://github.com/Ikaros-521/LX_OSS_Finder/pulls
[pr-welcome-shield]: https://img.shields.io/badge/%F0%9F%A4%AF%20PR%20WELCOME-%E2%86%92-ffcb47?labelColor=black&style=for-the-badge
[profile-link]: https://github.com/LuoXi-Project

