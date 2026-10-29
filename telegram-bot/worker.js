// Telegram 机器人 webhook → GitHub Actions(repository_dispatch)
//
// 流程:手机把行程截图/文字发给机器人 → Telegram 推到本 Worker → 本 Worker 校验
// 白名单后触发 sa-archive 的 telegram_ingest.yml(把整条 Telegram message 放进
// client_payload)→ workflow 里 headless claude 看图入库 → 用机器人回复结果。
//
// 本 Worker 只做「收 + 转发」,不解析、不碰 Supabase,所以只需要下面这几个变量
// (Cloudflare 后台 Settings → Variables and Secrets,全部设成 Secret):
//   TELEGRAM_BOT_TOKEN       @BotFather 给的 token
//   TELEGRAM_WEBHOOK_SECRET  自己随便生成的一串字母数字,setWebhook 时一起传给 Telegram
//   ALLOWED_USER_IDS         允许使用的 Telegram 用户 ID,逗号分隔(发 /id 给机器人可查)
//   GITHUB_TOKEN             fine-grained PAT,只授权 sa-archive,Contents: Read and write
//   GITHUB_REPO              Gabby-Zhang/sa-archive
//
// 失败绝不静默:触发 GitHub 失败会立刻回复「⚠️ 没转出去,请重发」。

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      // 浏览器打开 /setup:用本 Worker 里存的 token/secret 把 Telegram webhook 指向自己,
      // 不用手拼带 token 的 setWebhook 链接;/status 查看 webhook 状态(不含 token)
      const path = new URL(request.url).pathname;
      if (path === "/setup") {
        const r = await tg(env, "setWebhook", {
          url: new URL(request.url).origin,
          secret_token: env.TELEGRAM_WEBHOOK_SECRET,
          allowed_updates: ["message"],
        });
        return json(r);
      }
      if (path === "/status") return json(await tg(env, "getWebhookInfo", {}));
      return new Response("ok");
    }

    // 只认 Telegram 带着我们 secret 的请求,防止别人伪造
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.TELEGRAM_WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("ok");
    }
    const msg = update.message || update.channel_post;
    // 一律回 200:非 200 会让 Telegram 反复重推同一条
    if (!msg || !msg.from) return new Response("ok");

    const chatId = msg.chat.id;
    const userId = String(msg.from.id);
    const text = (msg.text || "").trim();

    if (text === "/start" || text === "/id") {
      await reply(env, chatId, msg.message_id,
        `你的 Telegram 用户 ID:${userId}\n` +
        `把它加进 Worker 的 ALLOWED_USER_IDS 后,直接发行程截图或文字给我即可。`);
      return new Response("ok");
    }

    const allowed = (env.ALLOWED_USER_IDS || "").split(",").map(s => s.trim()).filter(Boolean);
    if (!allowed.includes(userId)) {
      await reply(env, chatId, msg.message_id, `⛔ 未授权(用户 ID ${userId})。`);
      return new Response("ok");
    }

    const hasImage = Boolean(
      (msg.photo && msg.photo.length) ||
      (msg.document && (msg.document.mime_type || "").startsWith("image/"))
    );
    if (!hasImage && !text && !msg.caption) {
      await reply(env, chatId, msg.message_id, "只收图片或文字哦。");
      return new Response("ok");
    }

    const resp = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "sa-archive-telegram-bot",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ event_type: "telegram", client_payload: { message: msg } }),
    });

    if (resp.ok) {
      await reply(env, chatId, msg.message_id, "📥 收到,解析中(约 1–2 分钟)…");
    } else {
      const detail = (await resp.text()).slice(0, 200);
      await reply(env, chatId, msg.message_id,
        `⚠️ 没转出去(GitHub ${resp.status}),请稍后重发。\n${detail}`);
    }
    return new Response("ok");
  },
};

async function tg(env, method, payload) {
  // 出错时返回诊断信息而不是抛异常(只报 token 的格式,不泄露 token 本身)
  const token = env.TELEGRAM_BOT_TOKEN || "";
  const diag = {
    token_set: Boolean(token),
    token_format_ok: /^\d+:[A-Za-z0-9_-]{30,}$/.test(token),
    token_has_whitespace: /\s/.test(token),
    webhook_secret_length: (env.TELEGRAM_WEBHOOK_SECRET || "").length,
  };
  try {
    const resp = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const text = await resp.text();
    try {
      return JSON.parse(text);
    } catch {
      return { ok: false, http_status: resp.status, body: text.slice(0, 300), ...diag };
    }
  } catch (e) {
    return { ok: false, error: String(e), ...diag };
  }
}

function json(obj) {
  return new Response(JSON.stringify(obj, null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

async function reply(env, chatId, replyTo, text) {
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      reply_parameters: { message_id: replyTo, allow_sending_without_reply: true },
    }),
  });
}
