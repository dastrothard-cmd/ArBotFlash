const OPENAI_URL = "https://api.openai.com/v1/responses";

const ACTION_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    reply: { type: "string" },
    actions: {
      type: "array",
      maxItems: 30,
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          type: {
            type: "string",
            enum: [
              "add_tree",
              "update_tree",
              "delete_tree",
              "set_speech",
              "set_accent",
              "set_flash_mode",
              "set_family_filter",
              "navigate",
              "none"
            ]
          },
          binomial: { type: "string" },
          common: { type: "string" },
          family: { type: "string" },
          target: { type: "string" },
          value: { type: "string" }
        },
        required: ["type", "binomial", "common", "family", "target", "value"]
      }
    }
  },
  required: ["reply", "actions"]
};

function sameOrigin(req) {
  const origin = req.headers.origin;
  const host = req.headers.host;
  if (!origin || !host) return true;
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

function extractOutputText(response) {
  if (typeof response.output_text === "string") return response.output_text;
  for (const item of response.output || []) {
    if (item.type !== "message") continue;
    for (const content of item.content || []) {
      if (content.type === "output_text" && typeof content.text === "string") {
        return content.text;
      }
    }
  }
  return "";
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method === "GET") {
    return res.status(200).json({ ready: Boolean(process.env.OPENAI_API_KEY) });
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "POST requests only." });
  }

  if (!sameOrigin(req)) {
    return res.status(403).json({ error: "Request origin not allowed." });
  }

  if (!process.env.OPENAI_API_KEY) {
    return res.status(503).json({ error: "The AI service has not been connected yet." });
  }

  const request = String(req.body?.request || "").trim().slice(0, 1200);
  const trees = Array.isArray(req.body?.trees) ? req.body.trees.slice(0, 500) : [];
  const settings = req.body?.settings || {};

  if (!request) {
    return res.status(400).json({ error: "Request is required." });
  }

  const instructions = `
You are the safe command planner for a mobile Tree ID Trainer.

Turn the user's request into zero or more supported actions. The app applies your actions immediately.

Supported actions:
- add_tree: binomial, common, family
- update_tree: target is the existing binomial/common name; provide changed values and empty strings for unchanged fields
- delete_tree: target identifies the tree
- set_speech: value "on" or "off"
- set_accent: value "Australian", "English", "American", or "German"
- set_flash_mode: value "common-binomial", "binomial-common", "genus-family", or "family-genus"
- set_family_filter: value is a family name, or empty for all
- navigate: value "home", "tutorial", "flash", "familyGame", "nameGame", or "data"
- none: when no supported change should be made

Rules:
1. Never generate code, HTML, JavaScript, URLs, shell commands, or an action outside this list.
2. Never claim the app can rewrite its own source code.
3. For taxonomy additions, use accepted-looking botanical spelling and family names. If genuinely uncertain, make no action and clearly state what is missing.
4. Avoid duplicate additions when the species is already present.
5. A request may produce multiple actions.
6. Every action object must contain every field. Use empty strings for unused fields.
7. Keep the reply direct and brief.
`;

  try {
    const response = await fetch(OPENAI_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || "gpt-4.1-mini",
        instructions,
        input: [{
          role: "user",
          content: [{
            type: "input_text",
            text:
              `USER REQUEST:\n${request}\n\n` +
              `CURRENT SETTINGS:\n${JSON.stringify(settings)}\n\n` +
              `CURRENT TREE LIST:\n${JSON.stringify(trees)}`
          }]
        }],
        store: false,
        text: {
          format: {
            type: "json_schema",
            name: "tree_trainer_command",
            strict: true,
            schema: ACTION_SCHEMA
          }
        }
      })
    });

    const raw = await response.json();

    if (!response.ok) {
      const message = raw?.error?.message || `AI request failed (${response.status}).`;
      return res.status(response.status).json({ error: message });
    }

    const outputText = extractOutputText(raw);
    if (!outputText) {
      return res.status(502).json({ error: "The AI returned no command." });
    }

    let parsed;
    try {
      parsed = JSON.parse(outputText);
    } catch {
      return res.status(502).json({ error: "The AI returned an unreadable command." });
    }

    return res.status(200).json(parsed);
  } catch (error) {
    return res.status(500).json({ error: error?.message || "Unexpected server error." });
  }
};
