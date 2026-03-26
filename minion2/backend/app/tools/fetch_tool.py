import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any

async def fetch_url(url: str) -> str:
    """
    Python Native replacement for fetch-server.ts
    Quickly fetches text content from a URL with basic cleanup.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Cleanup standard noise
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.decompose()
                
            text = soup.get_text(separator=" ", strip=True)
            
            # Simple densification
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = " ".join(lines)
            
            if len(clean_text) < 200:
                return f"⚠️ Warning: URL returned minimal content (likely bot detection). For full content from {url}, use the Playwright-based browser tools instead."
                
            return clean_text[:12000]
            
    except Exception as e:
        return f"❌ Error fetching {url}: {str(e)}"
