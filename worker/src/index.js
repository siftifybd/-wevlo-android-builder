const json = (data, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });

function cors(origin, env) {
  if (!env.ALLOWED_ORIGIN || origin !== env.ALLOWED_ORIGIN) return {};
  return {
    "access-control-allow-origin": env.ALLOWED_ORIGIN,
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "Authorization, Content-Type",
    "access-control-max-age": "86400",
    "vary": "Origin",
  };
}

async function verifyFirebaseToken(token, env) {
  const endpoint = `https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${encodeURIComponent(env.FIREBASE_API_KEY || "")}`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ idToken: token }),
  });
  if (!response.ok) throw new Error("Invalid Firebase token");
  const data = await response.json();
  const user = data.users && data.users[0];
  if (!user || !user.localId || user.disabled) throw new Error("User unavailable");
  return user.localId;
}

function validHttps(value) {
  try {
    const u = new URL(value);
    return u.protocol === "https:" && !u.username && !u.password && value.length <= 2048;
  } catch { return false; }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const headers = cors(origin, env);
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      if (!headers["access-control-allow-origin"]) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers });
    }
    if (url.pathname !== "/build" || request.method !== "POST") {
      return json({ error: "Not found" }, 404, headers);
    }
    if (!headers["access-control-allow-origin"]) return json({ error: "Origin not allowed" }, 403);

    const auth = request.headers.get("Authorization") || "";
    const tokenMatch = auth.match(/^Bearer\s+(.+)$/i);
    if (!tokenMatch) return json({ error: "Firebase ID token required" }, 401, headers);

    let uid;
    try { uid = await verifyFirebaseToken(tokenMatch[1], env); }
    catch { return json({ error: "Firebase authentication failed" }, 401, headers); }

    let body;
    try { body = await request.json(); }
    catch { return json({ error: "Invalid JSON" }, 400, headers); }

    const mode = body.mode;
    const appName = String(body.appName || "My Website").trim().slice(0, 40);
    const packageName = String(body.packageName || "").trim();
    if (!["url", "zip"].includes(mode)) return json({ error: "mode must be url or zip" }, 400, headers);
    if (!/^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*){1,5}$/.test(packageName)) {
      return json({ error: "Invalid package name" }, 400, headers);
    }
    const websiteUrl = String(body.websiteUrl || "").trim();
    const websiteZipUrl = String(body.websiteZipUrl || "").trim();
    if (mode === "url" && !validHttps(websiteUrl)) return json({ error: "Valid HTTPS websiteUrl required" }, 400, headers);
    if (mode === "zip" && !validHttps(websiteZipUrl)) return json({ error: "Valid HTTPS websiteZipUrl required" }, 400, headers);

    const endpoint = `https://api.github.com/repos/${env.GH_OWNER}/${env.GH_REPO}/actions/workflows/android-build.yml/dispatches`;
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.GH_TOKEN}`,
        accept: "application/vnd.github+json",
        "x-github-api-version": "2022-11-28",
        "user-agent": "WEVLO-Build-API",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        ref: env.GH_BRANCH || "main",
        inputs: {
          mode,
          website_url: mode === "url" ? websiteUrl : "",
          website_zip_url: mode === "zip" ? websiteZipUrl : "",
          app_name: appName,
          package_name: packageName,
        },
      }),
    });
    if (!response.ok) {
      const detail = (await response.text()).slice(0, 400);
      return json({ error: "GitHub workflow dispatch failed", status: response.status, detail }, 502, headers);
    }
    return json({
      ok: true,
      status: "queued",
      uid,
      actionsUrl: `https://github.com/${env.GH_OWNER}/${env.GH_REPO}/actions`,
      message: "Build request queued. Check GitHub Actions for status and artifacts.",
    }, 202, headers);
  },
};
