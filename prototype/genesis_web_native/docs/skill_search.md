# Skill: Web Search

Search the web from within the browser using Jina AI + DuckDuckGo Lite. No API key required, no CORS issues.

## Usage

Call inside `/browser exec`:

```javascript
async function search(query, n = 5) {
    const url = `https://r.jina.ai/https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`;
    const res = await fetch(url);
    const text = await res.text();

    const results = [];
    const lines = text.split('\n');
    let current = null;
    for (const line of lines) {
        const titleMatch = line.match(/^\d+\.\s+\*\*(.+?)\*\*/);
        const urlMatch = line.match(/\(([^)]+\.[^)]+)\)/);
        if (titleMatch) {
            if (current) results.push(current);
            current = { title: titleMatch[1], url: '', snippet: '' };
        } else if (urlMatch && current && !current.url) {
            current.url = urlMatch[1];
        } else if (current && line.trim() && !line.startsWith('#')) {
            current.snippet += line.trim() + ' ';
        }
        if (results.length >= n) break;
    }
    if (current && results.length < n) results.push(current);
    return results.slice(0, n);
}

const results = await search('your query here', 5);
return JSON.stringify(results, null, 2);
```

## Return Format

```json
[
  {
    "title": "Result Title",
    "url": "example.com",
    "snippet": "Brief description of the result..."
  }
]
```

## Example

```javascript
const results = await search('latest AI news', 3);
for (const r of results) {
    console.log(r.title, r.url);
}
return results;
```

## Limitations

- Results from DuckDuckGo, not Google
- Jina AI free tier may rate-limit heavy usage
- Network latency ~1-3 seconds
