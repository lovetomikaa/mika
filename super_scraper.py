"""
SuperScraper - 超级通用爬虫
支持：JS渲染、反爬绕过、Cookie管理、UA轮换、重试、内容提取

依赖安装：
    uv pip install httpx beautifulsoup4 lxml markdownify fake-useragent
    uv pip install playwright  # JS渲染需要
    playwright install chromium

用法：
    from super_scraper import SuperScraper

    scraper = SuperScraper()

    # 简单抓取
    text = scraper.fetch("https://example.com")

    # JS渲染模式
    text = scraper.fetch("https://spa-site.com", render=True)

    # 抓取并保存
    scraper.fetch_and_save("https://example.com/article", "output.md")

    # 自定义配置
    scraper = SuperScraper(
        proxies=["http://127.0.0.1:7890"],
        timeout=30,
        max_retries=5,
    )
"""

import httpx
import random
import time
import re
import json
from pathlib import Path
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, field
from typing import Optional
from bs4 import BeautifulSoup

try:
    from markdownify import markdownify as md
    HAS_MD = True
except ImportError:
    HAS_MD = False

try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
    HAS_UA = True
except ImportError:
    HAS_UA = False


# ============================================================
# 配置
# ============================================================

@dataclass
class ScraperConfig:
    """爬虫配置"""
    timeout: int = 20
    max_retries: int = 3
    retry_delay: float = 2.0          # 首次重试等待秒数，之后指数退避
    rate_limit: float = 1.0           # 请求间隔秒数
    proxies: list = field(default_factory=list)
    cookie_file: Optional[str] = None  # Cookie JSON 文件路径
    headers: dict = field(default_factory=dict)  # 额外自定义 headers


# ============================================================
# 反检测：User-Agent 池 + 常见浏览器指纹
# ============================================================

_FALLBACK_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
]


def _get_ua() -> str:
    if HAS_UA:
        try:
            return _ua.random
        except Exception:
            pass
    return random.choice(_FALLBACK_UAS)


# ============================================================
# 浏览器指纹 Headers
# ============================================================

def _build_headers(extra: dict = None) -> dict:
    """构建模拟真实浏览器的请求头"""
    h = {
        "User-Agent": _get_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Dnt": "1",
    }
    if extra:
        h.update(extra)
    return h


# ============================================================
# Cloudflare / 常见反爬绕过
# ============================================================

def _detect_cloudflare(status_code: int, text: str, headers: dict) -> bool:
    """检测 Cloudflare 挑战页"""
    if status_code in (403, 503):
        cf_h = headers.get("server", "").lower()
        if "cloudflare" in cf_h:
            return True
        if "cf-chl-bypass" in headers or "Checking your browser" in text[:2000]:
            return True
    return False


# ============================================================
# HTML → 可读文本
# ============================================================

_STRIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "svg"}
_STRIP_ATTRS = {"class", "style", "id", "onclick", "onload", "data-*"}


def html_to_text(html: str, url: str = "", mode: str = "text") -> str:
    """
    将 HTML 转换为可读内容

    mode:
        "text"     - 纯文本（最快）
        "markdown" - Markdown 格式（需要 markdownify）
        "html"     - 清洗后的 HTML
    """
    soup = BeautifulSoup(html, "lxml")

    # 移除无用标签
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # 移除注释
    from bs4 import Comment
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # 尝试提取正文（article > main > #content > body）
    content = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|article|post|entry", re.I))
        or soup.find(class_=re.compile(r"content|article|post|entry", re.I))
        or soup.body
        or soup
    )

    # 修正相对链接
    if url:
        for a in content.find_all("a", href=True):
            a["href"] = urljoin(url, a["href"])
        for img in content.find_all("img", src=True):
            img["src"] = urljoin(url, img["src"])

    if mode == "markdown" and HAS_MD:
        return md(str(content), strip=["img"]).strip()
    elif mode == "html":
        return str(content)
    else:
        return content.get_text(separator="\n", strip=True)


# ============================================================
# Cookie 管理
# ============================================================

def _load_cookies(cookie_file: str) -> dict:
    """从 JSON 文件加载 Cookie"""
    p = Path(cookie_file)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # EditThisCookie 导出格式
            return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
        elif isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


# ============================================================
# 主爬虫类
# ============================================================

class SuperScraper:
    """超级通用爬虫"""

    def __init__(self, proxies=None, timeout=20, max_retries=3,
                 rate_limit=1.0, cookie_file=None, headers=None):
        self.config = ScraperConfig(
            timeout=timeout,
            max_retries=max_retries,
            rate_limit=rate_limit,
            proxies=proxies or [],
            cookie_file=cookie_file,
            headers=headers or {},
        )
        self._last_request_time = 0
        self._playwright = None  # 延迟初始化

    # ---- HTTP 请求（带重试 + 退避） ----

    def _wait_rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit:
            time.sleep(self.config.rate_limit - elapsed)

    def _fetch_http(self, url: str, method: str = "GET", **kwargs) -> httpx.Response:
        """HTTP 请求，带重试和退避"""
        self._wait_rate_limit()

        headers = _build_headers(self.config.headers)

        # Cookie
        cookies = {}
        if self.config.cookie_file:
            cookies = _load_cookies(self.config.cookie_file)

        # 代理
        proxy = random.choice(self.config.proxies) if self.config.proxies else None

        last_err = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                with httpx.Client(
                    follow_redirects=True,
                    timeout=self.config.timeout,
                    proxy=proxy,
                    cookies=cookies,
                    verify=False,  # 忽略 SSL 证书问题
                ) as client:
                    resp = client.request(method, url, headers=headers, **kwargs)
                    self._last_request_time = time.time()

                    # Cloudflare 检测 → 自动切换 render 模式
                    if _detect_cloudflare(resp.status_code, resp.text, dict(resp.headers)):
                        print(f"  [!] Cloudflare detected, falling back to browser render...")
                        return None  # 信号：上层切换到 Playwright

                    return resp

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                last_err = e
                wait = self.config.retry_delay * (2 ** (attempt - 1))
                print(f"  [!] attempt {attempt} failed: {type(e).__name__}, retry in {wait}s...")
                time.sleep(wait)

        raise ConnectionError(f"请求失败 ({self.config.max_retries}次): {last_err}")

    # ---- Playwright 浏览器渲染 ----

    def _ensure_playwright(self):
        if self._playwright is None:
            try:
                from playwright.sync_api import sync_playwright
                self._playwright = sync_playwright().start()
            except ImportError:
                raise ImportError(
                    "需要 playwright: uv pip install playwright && playwright install chromium"
                )

    def _fetch_browser(self, url: str, wait_for: str = None,
                       wait_ms: int = 3000, scroll: bool = True) -> str:
        """用 Playwright 渲染页面并提取内容"""
        self._ensure_playwright()
        self._wait_rate_limit()

        browser = self._playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=_get_ua(),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )

        # 注入反检测脚本
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            window.chrome = { runtime: {} };
        """)

        # 加载 Cookie
        if self.config.cookie_file:
            cookies = _load_cookies(self.config.cookie_file)
            domain = urlparse(url).hostname
            context.add_cookies([
                {"name": k, "value": v, "domain": domain, "path": "/"}
                for k, v in cookies.items()
            ])

        page = context.new_page()
        try:
            page.goto(url, timeout=self.config.timeout * 1000, wait_until="domcontentloaded")

            # 等待特定元素出现
            if wait_for:
                page.wait_for_selector(wait_for, timeout=10000)
            else:
                page.wait_for_timeout(wait_ms)

            # 模拟滚动（触发懒加载）
            if scroll:
                page.evaluate("""
                    async () => {
                        for (let i = 0; i < 3; i++) {
                            window.scrollBy(0, window.innerHeight);
                            await new Promise(r => setTimeout(r, 500));
                        }
                    }
                """)

            html = page.content()
            self._last_request_time = time.time()
            return html

        finally:
            page.close()
            context.close()
            browser.close()

    # ---- 公共接口 ----

    def fetch(self, url: str, mode: str = "text", render: bool = False,
              wait_for: str = None, method: str = "GET", **kwargs) -> str:
        """
        抓取网页内容

        参数:
            url      - 目标 URL
            mode     - 返回格式: "text" / "markdown" / "html" / "raw"
            render   - 是否使用浏览器渲染（JS 页面、反爬页面）
            wait_for - CSS 选择器，等待该元素出现后再提取
            method   - HTTP 方法（GET/POST 等）

        返回:
            提取后的文本内容
        """
        # 优先尝试 HTTP
        if not render:
            resp = self._fetch_http(url, method=method, **kwargs)

            if resp is not None:
                if mode == "raw":
                    return resp.text
                return html_to_text(resp.text, url=url, mode=mode)

        # 回退到浏览器
        html = self._fetch_browser(url, wait_for=wait_for)
        if mode == "raw":
            return html
        return html_to_text(html, url=url, mode=mode)

    def fetch_and_save(self, url: str, output: str, mode: str = "markdown",
                       render: bool = False) -> str:
        """抓取并保存到文件"""
        text = self.fetch(url, mode=mode, render=render)
        p = Path(output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"[OK] saved to {p} ({len(text)} chars)")
        return str(p)

    def fetch_multiple(self, urls: list, mode: str = "text",
                       render: bool = False, delay: float = 2.0) -> dict:
        """批量抓取，返回 {url: content}"""
        results = {}
        for i, url in enumerate(urls):
            print(f"[{i+1}/{len(urls)}] {url}")
            try:
                results[url] = self.fetch(url, mode=mode, render=render)
            except Exception as e:
                print(f"  [FAIL] {e}")
                results[url] = None
            if i < len(urls) - 1:
                time.sleep(delay)
        return results

    def fetch_json(self, url: str, **kwargs) -> dict:
        """抓取 JSON API"""
        resp = self._fetch_http(url, **kwargs)
        if resp is None:
            raise RuntimeError("浏览器渲染不支持 JSON API，请用 fetch()")
        return resp.json()

    def close(self):
        """关闭浏览器实例"""
        if self._playwright:
            self._playwright.stop()
            self._playwright = None


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    import sys
    import io

    # Windows 编码修复
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="SuperScraper - 超级通用爬虫")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-m", "--mode", choices=["text", "markdown", "html", "raw"],
                        default="markdown", help="输出格式 (默认: markdown)")
    parser.add_argument("-r", "--render", action="store_true",
                        help="使用浏览器渲染（JS页面）")
    parser.add_argument("-w", "--wait", help="等待 CSS 选择器出现")
    parser.add_argument("-t", "--timeout", type=int, default=20, help="超时秒数")
    parser.add_argument("--proxy", action="append", help="代理地址（可多次指定）")
    parser.add_argument("--cookie", help="Cookie JSON 文件路径")
    parser.add_argument("--rate", type=float, default=1.0, help="请求间隔秒数")

    args = parser.parse_args()

    scraper = SuperScraper(
        timeout=args.timeout,
        proxies=args.proxy or [],
        cookie_file=args.cookie,
        rate_limit=args.rate,
    )

    print(f"[fetch] {args.url}")
    print(f"  mode: {args.mode} | render: {'browser' if args.render else 'HTTP'}")

    try:
        if args.output:
            scraper.fetch_and_save(args.url, args.output, mode=args.mode, render=args.render)
        else:
            text = scraper.fetch(args.url, mode=args.mode, render=args.render)
            print("\n" + "=" * 60)
            print(text[:5000])
            if len(text) > 5000:
                print(f"\n... (共 {len(text)} 字符，用 -o 保存完整内容)")
    finally:
        scraper.close()
