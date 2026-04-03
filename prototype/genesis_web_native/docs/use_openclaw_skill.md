# 如何搜索、下载和阅读 OpenClaw 技能

> ClawHub API: https://wry-manatee-359.convex.site

---

## 1. 搜索技能

GET /api/v1/search?q={关键词}

返回：{ results: [{ slug, displayName, summary, score }] }

浏览器（via /api/fetch）：

    const res = await fetch('/api/fetch?url=' + encodeURIComponent(
      'https://wry-manatee-359.convex.site/api/v1/search?q=weather'
    ));
    const { results } = JSON.parse(await res.text());
    // results[0].slug → 'weather-pollen'

Shell：

    curl -s "https://wry-manatee-359.convex.site/api/v1/search?q=weather"

注意：/api/v1/skills 接口返回空数组（需鉴权），搜索请用 /api/v1/search?q=

---

## 2. 下载技能

GET /api/v1/download?slug={slug}

返回 application/zip，支持跨域，直接 fetch 即可（无需代理）。

ZIP 固定包含：
- SKILL.md — 技能说明与完整指令
- _meta.json — { slug, version, ownerId, publishedAt }

---

## 3. 解压 & 阅读（浏览器）

需要加载 JSZip：

    await new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
      s.onload = res; s.onerror = rej;
      document.head.appendChild(s);
    });

    const buf = await fetch(
      'https://wry-manatee-359.convex.site/api/v1/download?slug=weather'
    ).then(r => r.arrayBuffer());

    const zip = await JSZip.loadAsync(buf);
    const skill = await zip.files['SKILL.md'].async('string');
    const meta  = JSON.parse(await zip.files['_meta.json'].async('string'));
    console.log(skill);

Shell：

    slug="weather"
    curl -s "https://wry-manatee-359.convex.site/api/v1/download?slug=${slug}" -o /tmp/${slug}.zip
    unzip -p /tmp/${slug}.zip SKILL.md
