const OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech";

const COMMON_STYLE =
  "Speak at a calm educational pace. Pronounce botanical Latin names carefully, " +
  "naturally and distinctly. Keep the same voice, accent and vocal character for " +
  "the entire utterance.";

const VOICE_PROFILES = {
  australian_female: {
    voice: "marin",
    instructions:
      "Use the voice of an adult woman speaking natural contemporary Australian English. " +
      "Use a clearly Australian, non-rhotic accent with natural Australian vowel shapes. " +
      "Do not drift into an American, Canadian or British accent. " + COMMON_STYLE
  },
  australian_male: {
    voice: "cedar",
    instructions:
      "Use the voice of an adult man speaking natural contemporary Australian English. " +
      "Use a clearly Australian, non-rhotic accent with natural Australian vowel shapes. " +
      "Do not drift into an American, Canadian or British accent. " + COMMON_STYLE
  },
  british_female: {
    voice: "coral",
    instructions:
      "Use the voice of an adult woman speaking contemporary Standard British English " +
      "from southern England, with a natural modern Received Pronunciation character. " +
      "Use a non-rhotic British accent, British vowel shapes and British cadence. " +
      "Never use General American pronunciation and do not pronounce post-vocalic R sounds. " +
      COMMON_STYLE
  },
  british_male: {
    voice: "fable",
    instructions:
      "Use the voice of an adult man speaking contemporary Standard British English " +
      "from southern England, with a natural modern Received Pronunciation character. " +
      "Use a non-rhotic British accent, British vowel shapes and British cadence. " +
      "Never use General American pronunciation and do not pronounce post-vocalic R sounds. " +
      COMMON_STYLE
  },
  american_female: {
    voice: "nova",
    instructions:
      "Use the voice of an adult woman speaking natural General American English. " +
      "Use a clear rhotic American accent and an even educational delivery. " + COMMON_STYLE
  },
  american_male: {
    voice: "echo",
    instructions:
      "Use the voice of an adult man speaking natural General American English. " +
      "Use a clear rhotic American accent and an even educational delivery. " + COMMON_STYLE
  },
  german_female: {
    voice: "shimmer",
    instructions:
      "Use the voice of an adult German woman speaking clear English with a genuine, " +
      "restrained German accent. Keep precise consonants, slightly German vowel colouring " +
      "and a natural German-influenced rhythm. Do not use a General American accent, " +
      "and do not exaggerate or parody the German accent. " + COMMON_STYLE
  },
  german_male: {
    voice: "onyx",
    instructions:
      "Use the voice of an adult German man speaking clear English with a genuine, " +
      "restrained German accent. Keep precise consonants, slightly German vowel colouring " +
      "and a natural German-influenced rhythm. Do not use a General American accent, " +
      "and do not exaggerate or parody the German accent. " + COMMON_STYLE
  }
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

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    return res.status(405).json({ error: "POST requests only." });
  }
  if (!sameOrigin(req)) {
    return res.status(403).json({ error: "Request origin not allowed." });
  }
  if (!process.env.OPENAI_API_KEY) {
    return res.status(503).json({ error: "AI voices are not connected." });
  }

  const text = String(req.body?.text || "").trim().slice(0, 320);
  const profileId = String(
    req.body?.profile || "australian_female"
  ).toLowerCase();
  const profile =
    VOICE_PROFILES[profileId] || VOICE_PROFILES.australian_female;

  if (!text) {
    return res.status(400).json({ error: "Speech text is required." });
  }

  try {
    const response = await fetch(OPENAI_SPEECH_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "gpt-4o-mini-tts",
        voice: profile.voice,
        input: text,
        instructions: profile.instructions,
        response_format: "wav"
      })
    });

    if (!response.ok) {
      let message = `AI voice request failed (${response.status}).`;
      try {
        const body = await response.json();
        if (body?.error?.message) message = body.error.message;
      } catch {}
      return res.status(response.status).json({ error: message });
    }

    const audio = Buffer.from(await response.arrayBuffer());
    res.setHeader("Content-Type", "audio/wav");
    res.setHeader("Content-Length", String(audio.length));
    return res.status(200).send(audio);
  } catch (error) {
    return res.status(500).json({
      error: error?.message || "The AI voice request failed."
    });
  }
};
