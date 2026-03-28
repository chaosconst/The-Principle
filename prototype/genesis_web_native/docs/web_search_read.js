// Genesis Skill: Web Search & Read
// Inject once via /browser exec, then use anywhere.

window.webSearch = async q => {
  const r = await fetch(`https://r.jina.ai/https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(q)}`);
  return (await r.text()).replace(/https:\/\/duckduckgo\.com\/l\/\?uddg=([^&)]+)[^)]*/g, (m, u) => {
    try { return decodeURIComponent(u); } catch { return u; }
  });
};

window.webRead = async u => {
  const r = await fetch(`https://r.jina.ai/${u}`, { headers: { 'X-Return-Format': 'markdown' } });
  return await r.text();
};
