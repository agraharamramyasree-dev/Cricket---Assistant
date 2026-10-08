import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
SYSTEM_PROMPT = (
    "You are PitchSide, a friendly and knowledgeable AI cricket assistant. "
    "Help with cricket rules, tactics, formats, player and team context, "
    "training, and match analysis. Be clear and concise, use examples when "
    "helpful, and keep answers to 1-3 short paragraphs unless a list is useful. "
    "Prioritize correctness over confidence; say when you are unsure, and do "
    "not invent rules, statistics, quotes, or player facts. Treat these "
    "cricket facts as ground truth: an over consists of six legal deliveries; "
    "a wide or no-ball does not count as a legal delivery. A maiden over means "
    "zero runs are charged to the bowler. Byes and leg-byes do not count "
    "against the bowler, but a wide or no-ball does, so an over containing a "
    "wide or no-ball is not a maiden. A maiden does not require a wicket. If "
    "asked what a maiden over is, give that definition and do not contradict "
    "it. You do not have live scores or "
    "real-time news unless the user provides that information; never invent "
    "live match facts. Keep answers focused on cricket."
)


class CricketAssistantHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def do_GET(self):
        if self.path == "/api/health":
            self.handle_health()
            return
        if self.path.startswith("/api/"):
            self.send_error(404, "API endpoint not found")
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404, "API endpoint not found")
            return
        self.handle_chat()

    def handle_health(self):
        try:
            with urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as response:
                data = json.loads(response.read())
            models = [model.get("name", "") for model in data.get("models", [])]
            self.send_json(
                200,
                {
                    "ok": MODEL in models,
                    "model": MODEL,
                    "ollama": True,
                },
            )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            self.send_json(
                503,
                {"ok": False, "model": MODEL, "ollama": False, "error": str(error)},
            )

    def handle_chat(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 1 or content_length > 128_000:
                self.send_json(400, {"error": "Request body must be between 1 byte and 128 KB."})
                return

            body = json.loads(self.rfile.read(content_length))
            if not isinstance(body, dict):
                self.send_json(400, {"error": "Request body must be a JSON object."})
                return
            messages = body.get("messages")
            if not isinstance(messages, list) or not messages:
                self.send_json(400, {"error": "Send at least one chat message."})
                return

            clean_messages = []
            for message in messages[-20:]:
                if not isinstance(message, dict):
                    self.send_json(400, {"error": "Each message must have a role and content."})
                    return
                role = message.get("role")
                content = message.get("content")
                if role not in ("user", "assistant") or not isinstance(content, str):
                    self.send_json(400, {"error": "Each message must have a valid role and text content."})
                    return
                if not content.strip() or len(content) > 4000:
                    self.send_json(400, {"error": "Messages must contain 1 to 4,000 characters."})
                    return
                clean_messages.append({"role": role, "content": content})
            if clean_messages[-1]["role"] != "user":
                self.send_json(400, {"error": "The latest message must be from the user."})
                return

            payload = json.dumps(
                {
                    "model": MODEL,
                    "stream": True,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        *clean_messages,
                    ],
                    "options": {"temperature": 0.2, "num_predict": 180},
                }
            ).encode("utf-8")
            request = Request(
                f"{OLLAMA_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                ollama_response = urlopen(request, timeout=300)
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_json(error.code, {"error": f"Ollama: {detail or error.reason}"})
                return
            except (URLError, TimeoutError) as error:
                self.send_json(
                    503,
                    {"error": f"Could not reach Ollama at {OLLAMA_URL}: {error}"},
                )
                return

            with ollama_response:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                try:
                    while True:
                        chunk = ollama_response.read(4096)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Request body must be valid JSON."})
        except (ValueError, TypeError) as error:
            self.send_json(400, {"error": f"Invalid request: {error}"})

    def send_json(self, status, data):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), CricketAssistantHandler)
    print(f"PitchSide is running at http://127.0.0.1:{port}")
    print(f"Using Ollama model: {MODEL} ({OLLAMA_URL})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down PitchSide.")
    finally:
        server.server_close()
