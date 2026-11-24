# 管理员书签归类

入口：`https://codefromkarl.xyz/admin/bookmarks/`。登录后导入 Chrome 书签管理器导出的 HTML；书签列表并排展示标题与来源、什么时候用、分类和状态。按标题、原目录、用途或站点搜索，也可以按分类和读取状态筛选。打开「详情」查看建议分类、用途、原文摘录和个人备注；未取到依据时会明确提示。重复导入不会覆盖已有结果和备注。

书签数据与分析结果保存在当前浏览器。换设备或清除站点数据不会保留它们；不要用共享浏览器配置处理私人书签。后台不加载公开站点的主题脚本或统计服务，也不在 GitHub Pages、公开导航、站内搜索和站点地图中发布。

勾选后才出现「分析所选」，按钮和确认框都显示去重后实际发送的公开链接数量。手动最多勾选 20 条；「更多操作」里的「批量分析待分析项」一次最多处理 100 个链接，也需先确认。可以暂停，已完成的结果会保存；下次批量只处理仍待分析的条目。仅发送符合条件的公开 HTTPS URL，不发整份文件、标题、目录或备注。含参数、私网、登录/邀请路径和非 HTTPS 链接只保留在本地；动态页面、PDF、登录墙或正文不足可能无可核实结果。Cloudflare Workers AI 接收公开正文，可能消耗账户 AI 用量；详情中的短摘需与读取到的正文匹配。

## 首次部署

生产主站仍使用 `wrangler.jsonc` 的独立 `firefly` Worker；本功能部署到 `firefly-bookmarks`，只认 `/admin/bookmarks` 和其页面、脚本、分析接口。不要改主站 Custom Domain 或 GitHub Pages 工作流。

1. 用 `pnpm exec wrangler whoami` 确认正确的 Cloudflare 账户；授权过期，在交互终端执行 `pnpm exec wrangler login`。确认目标路由未被其他服务占用，并记录当前域名/路由状态。
2. 在 Cloudflare Zero Trust → Access → Applications 添加一个 **Self-hosted** 应用，同一个应用添加 `codefromkarl.xyz/admin/bookmarks` 与 `codefromkarl.xyz/admin/bookmarks/*` 两个公开目的地，不配置整个根域、不配置 Bypass。Allow 规则只含管理员邮箱，登录方式可用邮件一次性验证码。[路径规则](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/)
3. 获取此应用的 AUD 和团队地址。部署时以临时权限受限的 JSON 或批准的秘密管理方式提供三个绑定：`BOOKMARK_ACCESS_AUD`、`BOOKMARK_ACCESS_ISSUER`（完整的 `https://…cloudflareaccess.com`，无尾斜线）和 `BOOKMARK_ADMIN_EMAIL`。不要提交这些值或将令牌交给脚本。Worker 会独立校验签名、issuer、AUD 和邮箱；缺任一配置时保持关闭。[JWT 校验](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
4. 完成本地检查，再用同一身份配置部署：
   ```bash
   node --test admin/bookmarks/bookmarks.test.mjs
   pnpm check
   pnpm type-check
   pnpm build
   pnpm exec wrangler deploy --config wrangler.bookmarks.jsonc --dry-run
   pnpm exec wrangler deploy --config wrangler.bookmarks.jsonc --secrets-file /path/to/protected/bookmark-bindings.json
   ```
   不需要公开 `workers.dev` 或 Preview URL。第一次真实模型验证先确认账户用量，用获准的公开样本，不导入整库。
5. 分别确认未登录页面/脚本/分析接口被拒绝、管理员登录能打开并导入、另一邮箱不被允许。再验证公开首页、文章、RSS 和 Pagefind 仍可访问。

## 回退

只移除 `firefly-bookmarks` 的 `codefromkarl.xyz/admin/bookmarks*` Worker Route，回到主站原有 404 行为；保留浏览器里的书签数据和既有主站 Worker。若希望连 Access 登录入口也恢复为 404，再单独停用这个 Access 应用。不要修改公开站点和其他 Access 策略。
