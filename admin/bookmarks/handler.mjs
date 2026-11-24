import { createRemoteJWKSet, jwtVerify } from "jose";

const path = "/admin/bookmarks";
const importPath = `${path}/import`;
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

export function makeHandler({
	shell,
	importShell,
	client,
	banner,
	keys = getKeys,
}) {
	return async (request, env) => {
		const url = new URL(request.url);
		const routes = [
			path,
			`${path}/`,
			importPath,
			`${importPath}/`,
			`${path}/client.js`,
			`${path}/banner.webp`,
		];
		if (!routes.includes(url.pathname)) return json({ error: "未找到" }, 404);
		if (!(await isAdmin(request, env, keys)))
			return json({ error: "仅管理员可访问" }, 403);

		if (request.method !== "GET" && request.method !== "HEAD")
			return json({ error: "请求方式不支持" }, 405);
		if (url.pathname === path || url.pathname === importPath) {
			return new Response(null, {
				status: 308,
				headers: { ...headers, Location: `${url.pathname}/` },
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
		if (url.pathname === `${path}/banner.webp`) {
			return new Response(request.method === "HEAD" ? null : banner, {
				headers: { ...headers, "Content-Type": "image/webp" },
			});
		}
		const nonce = crypto.randomUUID().replaceAll("-", "");
		const page = url.pathname === `${importPath}/` ? importShell : shell;
		return new Response(
			request.method === "HEAD" ? null : page.replaceAll("__NONCE__", nonce),
			{
				headers: {
					...headers,
					"Content-Type": "text/html; charset=utf-8",
					"Content-Security-Policy": `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; img-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`,
				},
			},
		);
	};
}
