"""
Reusable web crawler using Crawl4AI.

Usage:
    # Single page → markdown (goes to output/misc/)
    uv run python crawl.py https://example.com

    # Single page with project name → output/acra-annual-returns/
    uv run python crawl.py https://example.com -p acra-annual-returns

    # Deep crawl (BFS, follow links up to depth 2, max 20 pages)
    uv run python crawl.py https://example.com -p acra --deep bfs --depth 2 --max-pages 20

    # Deep crawl with domain filter (stay on same domain)
    uv run python crawl.py https://example.com -p acra --deep bfs --max-pages 10 --same-domain

    # Deep crawl with URL pattern filter
    uv run python crawl.py https://example.com -p acra --deep best --keywords "annual returns,filing" --max-pages 15

Output structure: output/{project}/{pages}.md or output/{project}/{timestamp}/ for deep crawls.
"""

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy, BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, URLPatternFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer


OUTPUT_DIR = Path(__file__).parent / "output"


def sanitize_filename(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.netloc + parsed.path
    name = re.sub(r"[^\w\-.]", "_", name)
    return name.strip("_")[:120]


def build_deep_strategy(args):
    filters = []
    if args.same_domain:
        domain = urlparse(args.url).netloc
        filters.append(DomainFilter(allowed_domains=[domain]))
    if args.url_pattern:
        filters.append(URLPatternFilter(patterns=args.url_pattern))

    filter_chain = FilterChain(filters) if filters else None
    common = dict(
        max_depth=args.depth,
        max_pages=args.max_pages,
        filter_chain=filter_chain,
    )

    if args.deep == "bfs":
        return BFSDeepCrawlStrategy(**common)
    elif args.deep == "dfs":
        return DFSDeepCrawlStrategy(**common)
    elif args.deep == "best":
        keywords = [k.strip() for k in (args.keywords or "").split(",") if k.strip()]
        if not keywords:
            print("Error: --keywords required for 'best' strategy", file=sys.stderr)
            sys.exit(1)
        scorer = KeywordRelevanceScorer(keywords=keywords, weight=0.7)
        return BestFirstCrawlingStrategy(url_scorer=scorer, **common)


def get_project_dir(project: str) -> Path:
    project_dir = OUTPUT_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


async def crawl_single(url: str, project: str):
    project_dir = get_project_dir(project)
    browser_config = BrowserConfig(headless=True, text_mode=True)
    run_config = CrawlerRunConfig()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
        if not result.success:
            print(f"Failed: {result.error_message}", file=sys.stderr)
            sys.exit(1)

        outfile = project_dir / f"{sanitize_filename(url)}.md"
        outfile.write_text(result.markdown, encoding="utf-8")
        print(f"Saved: {outfile} ({len(result.markdown)} chars)")
        return outfile


async def crawl_deep(url: str, args):
    project_dir = get_project_dir(args.project)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = project_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    strategy = build_deep_strategy(args)
    browser_config = BrowserConfig(headless=True, text_mode=True)
    run_config = CrawlerRunConfig(deep_crawl_strategy=strategy, stream=True)

    pages = []
    async with AsyncWebCrawler(config=browser_config) as crawler:
        async for result in await crawler.arun(url=url, config=run_config):
            if result.success:
                filename = sanitize_filename(result.url) + ".md"
                outfile = run_dir / filename
                outfile.write_text(result.markdown, encoding="utf-8")
                pages.append(result.url)
                print(f"  [{len(pages)}] {result.url} → {filename}")
            else:
                print(f"  [!] Failed: {result.url} — {result.error_message}", file=sys.stderr)

    index = run_dir / "_INDEX.md"
    lines = [f"# Crawl: {url}", f"Date: {datetime.now().isoformat()}", f"Pages: {len(pages)}", ""]
    for i, page_url in enumerate(pages, 1):
        filename = sanitize_filename(page_url) + ".md"
        lines.append(f"{i}. [{page_url}]({filename})")
    index.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nDone: {len(pages)} pages saved to {run_dir}/")
    return run_dir


def main():
    parser = argparse.ArgumentParser(description="Crawl a website and output markdown")
    parser.add_argument("url", help="Starting URL to crawl")
    parser.add_argument("-p", "--project", default="misc", help="Project folder name (default: misc)")
    parser.add_argument("--deep", choices=["bfs", "dfs", "best"], help="Deep crawl strategy")
    parser.add_argument("--depth", type=int, default=2, help="Max crawl depth (default: 2)")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages to crawl (default: 20)")
    parser.add_argument("--same-domain", action="store_true", help="Only follow links on the same domain")
    parser.add_argument("--url-pattern", nargs="+", help="URL patterns to include (e.g. '*annual*')")
    parser.add_argument("--keywords", help="Comma-separated keywords for 'best' strategy scoring")
    args = parser.parse_args()

    if args.deep:
        asyncio.run(crawl_deep(args.url, args))
    else:
        asyncio.run(crawl_single(args.url, args.project))


if __name__ == "__main__":
    main()
