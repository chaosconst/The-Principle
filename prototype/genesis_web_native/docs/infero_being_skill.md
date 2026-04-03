# infero-being-skill 技能规范

基于 GitHub 的去中心化数字存在技能生态。

---

## 命名规范

    infero-being-skill-{name}

示例：infero-being-skill-weather, infero-being-skill-caiyun-rain-alert

搜索验证（无需 token）：

    curl "https://api.github.com/search/repositories?q=infero-being-skill+in:name&per_page=10"

---

## 仓库结构

    infero-being-skill-{name}/
    SKILL.md        # 技能说明与完整指令（必须）
    _meta.json      # 元数据（必须）
    README.md       # 人类可读说明（可选）

### SKILL.md 格式

    ---
    name: infero-being-skill-{name}
    version: 1.0.0
    description: 一句话描述
    ---

    # 技能名称

    ## When to Use
    描述何时调用此技能。

    ## Instructions
    数字存在执行的完整指令，可包含代码示例。

### _meta.json 格式

    {
      "name": "infero-being-skill-{name}",
      "version": "1.0.0",
      "description": "一句话描述",
      "author": "GitHub username",
      "topics": ["infero-being-skill"]
    }

---

## 搜索技能（浏览器，无 token，无跨域）

    const res = await fetch(
      'https://api.github.com/search/repositories?q=infero-being-skill+in:name&per_page=20'
    );
    const { total_count, items } = await res.json();
    // items[i].full_name → "owner/infero-being-skill-weather"
    // items[i].description → 仓库描述

也可通过 topic 搜索（需在 GitHub 仓库设置中添加 topic: infero-being-skill）：

    https://api.github.com/search/repositories?q=topic:infero-being-skill

---

## 读取技能内容（直接 fetch raw，无需解压）

    const owner = "chaosconst";
    const name = "infero-being-skill-weather";
    const branch = "main";

    const skill = await fetch(
      "https://raw.githubusercontent.com/" + owner + "/" + name + "/" + branch + "/SKILL.md"
    ).then(r => r.text());

    const meta = await fetch(
      "https://raw.githubusercontent.com/" + owner + "/" + name + "/" + branch + "/_meta.json"
    ).then(r => r.json());

---

## 与 ClawHub 对比

    特性            ClawHub                     infero-being-skill (GitHub)
    中心化          是（平台依赖）               否（去中心化）
    版本控制        有限                         完整 git 历史
    搜索            专属 API                     GitHub 仓库名前缀搜索
    读取方式        ZIP 下载 + JSZip 解压         直接 fetch raw URL
    私有技能        不支持                       支持（private repo + token）
    fork/PR         不支持                       完整 GitHub 协作流程
