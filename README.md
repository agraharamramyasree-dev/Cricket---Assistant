# PitchSide — AI Cricket Assistant

PitchSide is a small, local cricket chatbot powered by Ollama. It uses the
`qwen2.5:1.5b` model by default, streams answers as they are generated, and
keeps the conversation in your browser.

## Run it

1. Start Ollama and make sure the model is installed:

   ```powershell
   ollama serve
   ollama pull qwen2.5:1.5b
   ```

   If Ollama is already running and the model is installed, skip this step.

2. From this project folder, start the app:

   ```powershell
   python server.py
   ```

3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The app uses only Python's standard library; no package installation is
required. The server binds to `127.0.0.1` so it is only available on your
machine.

## Configuration

The defaults match the local Ollama setup:

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Ollama model tag |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `PORT` | `8000` | PitchSide web server port |

For example, in PowerShell:

```powershell
$env:OLLAMA_MODEL = "qwen2.5:1.5b"
python server.py
```

The assistant is intended for cricket knowledge, rules, tactics, training, and
analysis. It does not have live match data, so check a live source for current
scores and news.
