import asyncio
import random
import urllib.parse
import httpx
from playwright.async_api import async_playwright
from typing import Dict, Any, List


import os


class BrowserTool:
    """
    Python Native replacement for browser-server.ts. (Minion 2.0 Native)
    Uses Playwright with Manual Stealth injection to satisfy Docker compatibility (Python 3.12+).
    """

    CDP_ENDPOINT = os.getenv("CDP_URL", "http://host.docker.internal:9222")

    def __init__(self, storage=None):
        self.storage = storage
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def _ensure_browser(self):
        """Connect to the user's live Chrome session via CDP remote debugging (Minion 2.0 Native)."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
            # 🏛️ Neural Bridge Handshake: Explicitly discover the WebSocket URL
            # because connect_over_cdp's auto-discovery often fails in Docker bridges with Status 500.
            try:
                print(f"📡 [BROWSER] Orchestrating CDP Handshake: {self.CDP_ENDPOINT}...")
                
                # Fetch the browser version/WS info manually with Host spoofing for Docker-to-Host security bypass
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{self.CDP_ENDPOINT.rstrip('/')}/json/version",
                        headers={"Host": "localhost"}
                    )
                    resp.raise_for_status()
                    browser_info = resp.json()
                    ws_url = browser_info.get("webSocketDebuggerUrl")
                    
                    if not ws_url:
                        raise Exception("CDP endpoint found, but webSocketDebuggerUrl is missing. Is Chrome open with --remote-debugging-port=9222?")
                    
                    # 🏛️ Crucial Network Rewrite: Map host-local WS to Docker bridge
                    # Force the exact bridge network location (host.docker.internal:9222) into the WS URL
                    import urllib.parse
                    parsed_ws = urllib.parse.urlparse(ws_url)
                    # Extract netloc from our trusted CDP endpoint (usually host.docker.internal:9222)
                    target_netloc = urllib.parse.urlparse(self.CDP_ENDPOINT).netloc
                    ws_url = parsed_ws._replace(netloc=target_netloc).geturl()
                    
                    print(f"🌐 [BROWSER] Constructed Neural Link: {ws_url}")
                    
                self.browser = await self.playwright.chromium.connect_over_cdp(ws_url, timeout=15000)
                self.context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
                
                if len(self.context.pages) > 0:
                    self.page = self.context.pages[0]
                else:
                    self.page = await self.context.new_page()
                
                print(f"✅ [BROWSER] Neural Bridge Established with Host Chrome.")
            except Exception as e:
                print(f"❌ [BROWSER FAULT] Bridge Disconnected: {str(e)}")
                print(f"💡 [RESOLUTION] Run: 'socat TCP-LISTEN:9222,fork,reuseaddr TCP:127.0.0.1:9222' on your Mac.")
                raise e

    async def _apply_stealth(self, page):
        """Native Minion Stealth: Injects navigator bypasses directly (Docker Compatible)."""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

    async def _new_page(self):
        """Open a fresh tab in the user's real Chrome — inherits all cookies and sessions."""
        await self._ensure_browser()
        page = await self.context.new_page()
        await self._apply_stealth(page)
        return page

    async def goto_and_scrape(self, url: str) -> str:
        """Navigates to a URL in a fresh tab, extracts text, then closes the tab."""
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            
            # Temporary switch for the scrape_text call
            old_page = self.page
            self.page = page
            text = await self.scrape_text()
            self.page = old_page
            
            return text
        except Exception as e:
            return f"❌ Browser Error for {url}: {str(e)}"
        finally:
            if page and not page.is_closed():
                await page.close()

    async def scrape_text(self) -> str:
        """Extracts cleaned inner text from the current active page (assumes caller manages page lifecycle)."""
        await self._ensure_browser()
        target_page = self.page
        if not target_page or target_page.is_closed():
            return "❌ Error: No active page to scrape. Visit a URL first using 'goto'."
            
        for attempt in range(3):
            try:
                content = await target_page.evaluate("""() => {
                    document.querySelectorAll('script, style, nav, footer, header').forEach(s => s.remove());
                    return document.body.innerText;
                }""")
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                return " ".join(lines)[:15000]
            except Exception as e:
                err_str = str(e)
                if "Execution context was destroyed" in err_str or "navigation" in err_str.lower():
                    print(f"⚠️ [EXTRACTOR] Fast redirect caught, waiting for page stabilization (attempt {attempt+1})...")
                    await asyncio.sleep(2)
                else:
                    return f"❌ Extractor Fault: {err_str}"
        return "❌ Extractor failed due to continuous aggressive redirects."

    async def deep_search(self, query: str) -> str:
        """
        Three-engine human-behaviour search using fresh tabs:
          1. DuckDuckGo  — fresh tab, homepage navigation, character typing
          2. Google      — fresh tab fallback, homepage navigation, character typing
          3. Yahoo       — fresh tab ultimate fallback, homepage navigation, character typing
        """
        await self._ensure_browser()

        # ── Engine 1: DuckDuckGo (human-like typing on homepage) ─────────────────
        page = None
        try:
            print(f"📡 [DDG] Stealth search: {query[:80]}")
            
            # 🏛️ Neural Sync: Check 24h Search Cache
            if self.storage:
                cached = await self.storage.get_search_cache("duckduckgo", query)
                if cached:
                    print(f"⚡ [CACHE HIT] DuckDuckGo: Using fresh 24h manifest.")
                    return f"🧠 [SOURCE: CACHE]: DuckDuckGo Results\n{cached}"
            
            page = await self._new_page()
            await page.goto("https://duckduckgo.com", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(0.8, 1.8))   # human landing pause

            # Click the search box
            search_box = page.locator("input[name='q'], input[type='text']").first
            await search_box.click()
            await asyncio.sleep(random.uniform(0.3, 0.7))

            # Type character-by-character at human speed (~60-120 WPM = 20-80 ms/char)
            for char in query:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.02, 0.08))

            await asyncio.sleep(random.uniform(0.3, 0.6))   # pause before submitting
            await page.keyboard.press("Enter")

            # Wait for results
            try:
                await page.wait_for_selector(
                    "[data-result='web'], .result, .results--main",
                    timeout=12000
                )
            except Exception:
                await asyncio.sleep(3)  # fallback wait

            await asyncio.sleep(random.uniform(0.5, 1.2))
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(0.5)

            page_html = await page.content()
            if "CAPTCHA" in page_html or "unusual traffic" in page_html:
                print("⚠️ [DDG] Block/CAPTCHA detected — rotating to Google...")
            else:
                # Extract results via JS (plain strings, no template literals in Python strings)
                extracted = await page.evaluate("""() => {
                    const selectors = ['[data-result="web"]', '.result', '.results--main .result'];
                    let items = [];
                    for (const sel of selectors) {
                        items = Array.from(document.querySelectorAll(sel)).slice(0, 10);
                        if (items.length > 2) break;
                    }
                    return items.map(el => {
                        const titleEl = el.querySelector('h2, h3, .result__title, a');
                        const title = titleEl ? titleEl.innerText.trim() : '';
                        const linkEl = el.querySelector('a[href]');
                        const link = linkEl ? linkEl.href : '';
                        const snippetEl = el.querySelector('.result__snippet, p');
                        const snippet = snippetEl
                            ? snippetEl.innerText.trim()
                            : el.innerText.split('\\n').slice(0, 3).join(' ').trim().slice(0, 300);
                        if (!title || title.length < 4 || !link.startsWith('http')) return null;
                        if (/pornhub|sex\\.com|adult/.test(link)) return null;
                        return '[TITLE]: ' + title + '\\n[URL]: ' + link + '\\n[SUMMARY]: ' + snippet + '\\n';
                    }).filter(Boolean).join('------------------------------\\n');
                }""")

                if extracted and len(extracted) > 150:
                    print(f"✅ [DDG] Search successful. Initiating Deep Extraction on top results...")
                    
                    # 🏛️ Deep Extraction Sync: Collect the links for automated 'digging'
                    links = []
                    for item in extracted.split("------------------------------\n"):
                        if "[URL]: " in item:
                            link = item.split("[URL]: ")[1].split("\n")[0].strip()
                            if link and link.startswith("http"): links.append(link)
                    
                    # Dig into the top 5 links to satisfy the requirement for an extensive initial search
                    deep_intel = ""
                    for i, link in enumerate(links[:5]):
                        try:
                            print(f"📡 [DIGGING {i+1}/5] Auto-Extracting: {link[:50]}...")
                            text = await self.goto_and_scrape(link)
                            if text and "❌" not in text:
                                # Standardized high-fidelity limit for multi-source extraction
                                deep_intel += f"\n\n📂 [DEEP EXTRACTION: {link}]\n{text[:4000]}\n"
                        except Exception:
                            continue
                            
                    await page.close()
                    hub_res = f"{extracted}\n{deep_intel}"
                    if self.storage:
                        await self.storage.set_search_cache("duckduckgo", query, hub_res)
                    return f"🧠 [SOURCE]: DuckDuckGo Results\n{hub_res}"
                else:
                    print(f"⚠️ [DDG] Minimal results ({len(extracted)} chars) — rotating to Google...")
        except Exception as e:
            print(f"❌ [DDG] Fault: {str(e)[:120]}")
        finally:
            if page and not page.is_closed():
                await page.close()

        # ── Engine 2: Google (fresh tab with consent bypass) ───────────────
        page = None
        try:
            print(f"📡 [GOOGLE] Stealth search: {query[:80]}")

            # 🏛️ Neural Sync: Check 24h Search Cache
            if self.storage:
                cached = await self.storage.get_search_cache("google", query)
                if cached:
                    print(f"⚡ [CACHE HIT] Google: Using fresh 24h manifest.")
                    return f"🧠 [SOURCE: CACHE]: Google Results\n{cached}"

            page = await self._new_page()
            await page.goto(
                "https://www.google.com",
                wait_until="domcontentloaded",
                timeout=20000
            )
            await asyncio.sleep(random.uniform(0.8, 1.5))

            # Dismiss consent/GDPR walls
            for consent_text in ["Accept all", "I agree", "Allow all", "Accept cookies", "Agree"]:
                try:
                    btn = page.get_by_text(consent_text, exact=False)
                    if await btn.is_visible(timeout=600):
                        await btn.click()
                        await asyncio.sleep(0.8)
                        break
                except Exception:
                    continue

            # Locate the search box and type humanly
            search_box = page.locator("textarea[name='q'], input[name='q']").first
            await search_box.click()
            await asyncio.sleep(random.uniform(0.3, 0.7))

            for char in query:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.01, 0.05))

            await asyncio.sleep(random.uniform(0.4, 0.8))
            await page.keyboard.press("Enter")
            
            # Wait for results to propagate
            try:
                await page.wait_for_selector(
                    "h3, #search, #rso",
                    timeout=10000
                )
            except Exception:
                await asyncio.sleep(3)

            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(random.uniform(0.6, 1.2))

            page_html = await page.content()
            if "CAPTCHA" in page_html or "unusual traffic" in page_html:
                print("⚠️ [GOOGLE] Traffic gate detected.")
            else:
                extracted = await page.evaluate("""() => {
                    const items = Array.from(
                        document.querySelectorAll('.g, [data-sokoban-container]')
                    ).slice(0, 10);
                    return items.map(el => {
                        const h3 = el.querySelector('h3');
                        const title = h3 ? h3.innerText.trim() : '';
                        const linkEl = el.querySelector('a[href]');
                        const link = linkEl ? linkEl.href : '';
                        const snippetEl = el.querySelector('.VwiC3b, span[data-sncf]');
                        const snippet = snippetEl
                            ? snippetEl.innerText.trim()
                            : el.innerText.split('\\n').slice(0, 3).join(' ').trim().slice(0, 300);
                        if (!title || title.length < 4 || !link.startsWith('http')) return null;
                        return '[TITLE]: ' + title + '\\n[URL]: ' + link + '\\n[SUMMARY]: ' + snippet + '\\n';
                    }).filter(Boolean).join('------------------------------\\n');
                }""")

                if extracted and len(extracted) > 150:
                    print(f"✅ [GOOGLE] Search successful. Initiating Deep Extraction on top results...")
                    
                    # 🏛️ Deep Extraction Sync: Collect the links for automated 'digging'
                    links = []
                    for item in extracted.split("------------------------------\n"):
                        if "[URL]: " in item:
                            link = item.split("[URL]: ")[1].split("\n")[0].strip()
                            if link and link.startswith("http"): links.append(link)
                    
                    # Dig into the top 5 links for extensive initial research
                    deep_intel = ""
                    for i, link in enumerate(links[:5]):
                        try:
                            print(f"📡 [DIGGING {i+1}/5] Auto-Extracting: {link[:50]}...")
                            text = await self.goto_and_scrape(link)
                            if text and "❌" not in text:
                                # Standardized high-fidelity limit for multi-source extraction
                                deep_intel += f"\n\n📂 [DEEP EXTRACTION: {link}]\n{text[:4000]}\n"
                        except Exception:
                            continue
                            
                    hub_res = f"{extracted}\n{deep_intel}"
                    if self.storage:
                        await self.storage.set_search_cache("google", query, hub_res)
                    await page.close()
                    return f"🧠 [SOURCE]: Google Results\n{hub_res}"
                else:
                    print(f"⚠️ [GOOGLE] Minimal results ({len(extracted)} chars).")
        except Exception as e:
            print(f"❌ [GOOGLE] Fault: {str(e)[:120]}")
        finally:
            if page and not page.is_closed():
                await page.close()

        # ── Engine 3: Yahoo (fresh tab ultimate fallback) ───────────────
        page = None
        try:
            print(f"📡 [YAHOO] Stealth search: {query[:80]}")

            # 🏛️ Neural Sync: Check 24h Search Cache
            if self.storage:
                cached = await self.storage.get_search_cache("yahoo", query)
                if cached:
                    print(f"⚡ [CACHE HIT] Yahoo: Using fresh 24h manifest.")
                    return f"🧠 [SOURCE: CACHE]: Yahoo Results\n{cached}"

            page = await self._new_page()
            await page.goto(
                "https://search.yahoo.com/",
                wait_until="domcontentloaded",
                timeout=20000
            )
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            search_box = page.locator("input[name='p'], input[name='q']").first
            await search_box.click()
            await asyncio.sleep(random.uniform(0.3, 0.7))

            for char in query:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.01, 0.05))

            await asyncio.sleep(random.uniform(0.4, 0.8))
            await page.keyboard.press("Enter")
            
            try:
                await page.wait_for_selector("ol.mb-15, .compTitle, h3", timeout=10000)
            except Exception:
                await asyncio.sleep(3)

            page_html = await page.content()
            if "CAPTCHA" in page_html or "unusual traffic" in page_html:
                print("⚠️ [YAHOO] Traffic gate detected.")
            else:
                extracted = await page.evaluate("""() => {
                    const items = Array.from(
                        document.querySelectorAll('.algo, .P-14, .compTitle')
                    ).slice(0, 10);
                    return items.map(el => {
                        const h3 = el.querySelector('h3, .title');
                        const title = h3 ? h3.innerText.trim() : '';
                        const linkEl = el.querySelector('a[href]');
                        const link = linkEl ? linkEl.href : '';
                        const snippetEl = el.querySelector('.compText, .fc-falcon');
                        const snippet = snippetEl
                            ? snippetEl.innerText.trim()
                            : el.innerText.split('\\n').slice(0, 3).join(' ').trim().slice(0, 300);
                        if (!title || title.length < 4 || !link.startsWith('http')) return null;
                        return '[TITLE]: ' + title + '\\n[URL]: ' + link + '\\n[SUMMARY]: ' + snippet + '\\n';
                    }).filter(Boolean).join('------------------------------\\n');
                }""")

                if extracted and len(extracted) > 150:
                    print(f"✅ [YAHOO] Search successful. Initiating Deep Extraction on top results...")
                    
                    # 🏛️ Deep Extraction Sync: Collect the links for automated 'digging'
                    links = []
                    for item in extracted.split("------------------------------\n"):
                        if "[URL]: " in item:
                            link = item.split("[URL]: ")[1].split("\n")[0].strip()
                            if link and link.startswith("http"): links.append(link)
                    
                    # Dig into the top 5 links for extensive initial research
                    deep_intel = ""
                    for i, link in enumerate(links[:5]):
                        try:
                            print(f"📡 [DIGGING {i+1}/5] Auto-Extracting: {link[:50]}...")
                            text = await self.goto_and_scrape(link)
                            if text and "❌" not in text:
                                # Standardized high-fidelity limit for multi-source extraction
                                deep_intel += f"\n\n📂 [DEEP EXTRACTION: {link}]\n{text[:4000]}\n"
                        except Exception:
                            continue
                            
                    hub_res = f"{extracted}\n{deep_intel}"
                    if self.storage:
                        await self.storage.set_search_cache("yahoo", query, hub_res)
                    await page.close()
                    return f"🧠 [SOURCE]: Yahoo Results\n{hub_res}"
                else:
                    print(f"⚠️ [YAHOO] Minimal results ({len(extracted)} chars).")
        except Exception as e:
            print(f"❌ [YAHOO] Fault: {str(e)[:120]}")
        finally:
            if page and not page.is_closed():
                await page.close()


        return (
            "❌ [DISCOVERY FAILURE] DuckDuckGo, Google, and Yahoo are currently throttled for this query. "
            "Try a different query or use 'goto' with a direct URL for manual scraping."
        )

    async def close(self):
        """Disconnect from CDP — does NOT close the user's Chrome."""
        if self.browser:
            await self.browser.close()  # disconnects CDP, doesn't kill Chrome
        if self.playwright:
            await self.playwright.stop()
