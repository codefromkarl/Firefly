# 把本机书单同步到博客

以本机书单的书目表为准，不按电子书文件数量计数。先将书名、作者、版次和套装与已有 `src/content/books/` 条目逐一对应；已在博客里的条目沿用原地址和阅读状态，保留只有博客才有的旧书目。新增项默认「计划阅读」，收藏或有电子书不代表已读。

把核对后确实需要新建的条目做成本机 JSON 数组，每条给出 `title`、`authors`（数组）、`description`（自己概述，不复制正文）、`shelf`（站点现有书架键）和相对于书单根目录的 `file`。若 EPUB 的封面其实是推广页，填 `"cover": "generated"` 使用文字封面。清单和源文件不进入 Git；只发布书目信息和封面图。

```bash
pnpm exec tsx scripts/import-book-library.ts --source "$HOME/下载/书单" --manifest /path/to/local-plan.json
# 核对标题、作者、冲突和封面后，用同一条命令加 --apply；重跑已存在的条目不重写。
node --test scripts/import-book-library.test.mjs
pnpm check && pnpm type-check && pnpm build
```

部署公开站点前，确认候选站点仍包括旧书目和原有文章链接。发布后核对 `/books/` 的数量、新书详情及封面，同时确认原有入口和独立的私有书签 Worker 不受影响。
