# 私有书签表

展示页：`https://codefromkarl.xyz/admin/bookmarks/`。表格显示书签名、类型和一句用途，上方可按分类筛选。类型描述链接是什么（例如开源项目、资源目录、电子书），分类用来组织主题。展示页没有导入按钮，不读取目标网站，也不运行 AI。

更新时，先在页面外整理好结果，再打开受同一管理员权限保护的 `/admin/bookmarks/import/`，选择 JSON 文件。

导入文件是 JSON 数组，顺序即表格顺序。每条包含书签名、绝对网址和一句用途，可以附上类型和分类（分别最多 32 字）：

```json
[
  {
    "title": "Godot Asset Library",
    "url": "https://godotengine.org/asset-library/asset",
    "purpose": "按 Godot 版本和许可证查找可复用的插件与示例。",
    "type": "资源目录",
    "category": "游戏开发"
  }
]
```

旧结果没有 `type` 或 `category` 也可导入，类型显示「未标注」，未填分类归为「未分类」。只有至少两组可切换时才显示筛选，刷新默认看全部。

一次最多 20,000 条、16 MB。Chrome 原始 HTML 和缺少用途的条目不能导入；任何一条出错都不会覆盖现有表格。确认替换后，完整新表保存在当前浏览器，不上传文件。非 HTTP(S) 地址和含用户名、密码的链接只展示名称。旧版从 Chrome 导入的原始书签保留在原 IndexedDB，不迁移、不删除，也不显示在结果表中。

## 部署与验收

主站仍使用 `wrangler.jsonc` 的独立 `firefly` Worker；这个页面只发布到 `firefly-bookmarks`，不改主站、自定义域名或 GitHub Pages 工作流。只保留展示页、独立更新页、客户端脚本和复用的博客横幅；不在公开导航、站点地图或搜索索引中发布。

部署前确认目标账户、路由、现有 Worker 版本及回退入口。保留现有 Cloudflare Access 应用的两个保护路径 `codefromkarl.xyz/admin/bookmarks` 和 `codefromkarl.xyz/admin/bookmarks/*`、管理员名单及登录方式。不添加 Bypass。Worker 仍逐请求独立校验签名、issuer、AUD 和管理员邮箱：保留 `BOOKMARK_ACCESS_AUD`、`BOOKMARK_ACCESS_ISSUER` 和 `BOOKMARK_ADMIN_EMAIL` 三个生产秘密，缺任何配置时拒绝访问。[Cloudflare JWT 校验说明](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)

```bash
node --test admin/bookmarks/bookmarks.test.mjs
pnpm check
pnpm type-check
pnpm build
pnpm exec wrangler deploy --config wrangler.bookmarks.jsonc --dry-run
```

发布后核对未登录访问后台及其资源被拦截，管理员可在更新页保存结果，回到无导入按钮的展示页看到三列结果，并可切换分类；刷新后结果仍在；确认旧分析端点不可用、公开首页和搜索可访问。无需 Workers AI 绑定。

如需回退，只将书签专用 Worker 回滚到此前版本；可重新查看旧版浏览器中的原始书签。不要切换主站域名或修改现有 Access 策略。
