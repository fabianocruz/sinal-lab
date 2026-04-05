/**
 * Text-to-Speech API route — proxies requests to ElevenLabs.
 *
 * Cost control: input is limited to 5000 chars server-side (~$0.75 per request
 * at ElevenLabs Flash pricing). Audio is returned as MP3 with a 24h Cache-Control
 * header so the browser won't re-request the same bytes on the same session.
 *
 * Requires ELEVENLABS_API_KEY in environment (server-only, never NEXT_PUBLIC_).
 */

import { NextRequest, NextResponse } from "next/server";

const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;

// "Lily" — female voice with natural Portuguese/multilingual performance.
// Swap VOICE_ID to test other voices; the model handles pt-BR without accent issues.
const VOICE_ID = "pFZP5JQG7iQjIQuC4Bku";

// Hard cap to control spend: 5000 chars ≈ 3-4 min of audio at normal reading pace.
const MAX_CHARS = 5000;

export async function POST(request: NextRequest) {
  if (!ELEVENLABS_API_KEY) {
    return NextResponse.json({ error: "TTS not configured" }, { status: 503 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (
    !body ||
    typeof body !== "object" ||
    !("text" in body) ||
    typeof (body as Record<string, unknown>).text !== "string"
  ) {
    return NextResponse.json({ error: "text field required" }, { status: 400 });
  }

  const rawText = (body as { text: string }).text.trim();
  if (!rawText) {
    return NextResponse.json({ error: "text must not be empty" }, { status: 400 });
  }

  const truncated = rawText.slice(0, MAX_CHARS);

  try {
    const upstream = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`, {
      method: "POST",
      headers: {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: truncated,
        model_id: "eleven_multilingual_v2",
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
        },
      }),
    });

    if (!upstream.ok) {
      const errorText = await upstream.text().catch(() => "unknown error");
      console.error("ElevenLabs error:", upstream.status, errorText);
      return NextResponse.json({ error: "TTS generation failed" }, { status: 502 });
    }

    const audioBuffer = await upstream.arrayBuffer();
    return new NextResponse(audioBuffer, {
      headers: {
        "Content-Type": "audio/mpeg",
        // Cache for 24h in the browser — same article slug won't re-hit ElevenLabs
        // on page refresh or if the user navigates away and returns.
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (err) {
    console.error("TTS route error:", err);
    return NextResponse.json({ error: "TTS generation failed" }, { status: 500 });
  }
}
