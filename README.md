# crawl4ai-tool

A CLI web crawler that converts web pages to markdown. Supports single-page and deep crawling (BFS, DFS, keyword-scored) with domain and URL pattern filtering.

Built on [crawl4ai](https://github.com/unclecode/crawl4ai).

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
git clone https://github.com/jiaweijwjw/crawl4ai-tool.git ~/code/tools/crawl4ai
cd ~/code/tools/crawl4ai
uv sync
uv run playwright install
```

## Output

Crawled pages are saved as markdown files in `output/{project}/`. Deep crawls create a timestamped subdirectory with an `_INDEX.md` listing all crawled pages.
