import { createRemoteJWKSet, jwtVerify } from "jose";
import { analyzeBookmark, publicBookmarkURL } from "./analysis.mjs";

const path = "/admin/bookmarks";
const headers = {
	"Cache-Control": "private, no-store",
	"Referrer-Policy": "no-referrer",
	"X-Content-Type-Options": "nosniff",
	"X-Robots-Tag": "noindex, nofollow",
	"Cross-Origin-Resource-Policy": "same-origin",
	"Cross-Origin-Opener-Policy": "same-origin",
};

let remote;
function getKeys(issuer) {
	if (remote?.issuer !== issuer) {
		remote = {
			issuer,
			keys: createRemoteJWKSet(new URL("/cdn-cgi/access/certs", issuer), {
				timeoutDuration: 3500,
			}),
		};
	}
	return remote.keys;
}

async function isAdmin(request, env, keys) {
	const issuer = env.BOOKMARK_ACCESS_ISSUER;
	const audience = env.BOOKMARK_ACCESS_AUD;
	const email = env.BOOKMARK_ADMIN_EMAIL?.trim().toLowerCase();
	const token = request.headers.get("cf-access-jwt-assertion");
	if (
		!/^https:\/\/[a-z0-9-]+[.]cloudflareaccess[.]com$/.test(issuer ?? "") ||
		!audience ||
		!email ||
		!token ||
		token.length > 8192
	)
		return false;
	try {
		const { payload } = await jwtVerify(token, keys(issuer), {
			issuer,
			audience,
			algorithms: ["RS256"],
			requiredClaims: ["iss", "aud", "exp", "email"],
		});
		return (
			typeof payload.email === "string" && payload.email.toLowerCase() === email
		);
	} catch {
		return false;
	}
}

function json(data, status) {
	return Response.json(data, { status, headers });
}

async function readURL(request) {
	if (!request.body || request.headers.get("Content-Length") > 4096)
		return null;
	const reader = request.body.pipeThrough(new TextDecoderStream()).getReader();
	let text = "";
	try {
		for (;;) {
			const { done, value } = await reader.read();
			if (done) break;
			text += value;
			if (text.length > 3072) {
				await reader.cancel();
				return null;
			}
		}
		const input = JSON.parse(text);
		return publicBookmarkURL(input?.url);
	} catch {
		return null;
	} finally {
		reader.releaseLock();
	}
}

export function makeHandler({
	shell,
	client,
	keys = getKeys,
	analyze = analyzeBookmark,
}) {
	return async (request, env) => {
		const url = new URL(request.url);
		const routes = [path, `${path}/`, `${path}/client.js`, `${path}/analyze`];
		if (!routes.includes(url.pathname)) return json({ error: "未找到" }, 404);
		if (!(await isAdmin(request, env, keys)))
			return json({ error: "仅管理员可访问" }, 403);

		if (url.pathname === `${path}/analyze`) {
			if (request.method !== "POST")
				return json({ error: "请求方式不支持" }, 405);
			if (
				request.headers.get("Origin") !== url.origin ||
				!/^application\/json(?:;|$)/i.test(
					request.headers.get("Content-Type") ?? "",
				)
			)
				return json({ error: "请从书签管理页发起分析" }, 403);

			const link = await readURL(request);
			if (!link)
				return json(
					{ state: "excluded", message: "只分析不含参数的公开 HTTPS 链接" },
					400,
				);
			try {
				return json(await analyze(link, env.AI));
			} catch {
				return json(
					{ state: "error", message: "分析服务暂不可用，可稍后重试" },
					503,
				);
			}
		}
		if (request.method !== "GET" && request.method !== "HEAD")
			return json({ error: "请求方式不支持" }, 405);
		if (url.pathname === path) {
			return new Response(null, {
				status: 308,
				headers: { ...headers, Location: `${path}/` },
			});
		}
		if (url.pathname === `${path}/client.js`) {
			return new Response(request.method === "HEAD" ? null : client, {
				headers: {
					...headers,
					"Content-Type": "text/javascript; charset=utf-8",
				},
			});
		}
		const nonce = crypto.randomUUID().replaceAll("-", "");
		return new Response(
			request.method === "HEAD" ? null : shell.replaceAll("__NONCE__", nonce),
			{
				headers: {
					...headers,
					"Content-Type": "text/html; charset=utf-8",
					"Content-Security-Policy": `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`,
				},
			},
		);
	};
}
