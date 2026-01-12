# Antigravity Shorts Automation System

This project is a standalone, agentic-style automation for creating YouTube Shorts without external workflow tools like n8n.

## Structure
- `scripts/assemble_video.py`: The engine that combines images, text, and TTS into a video.
- `assets/`: Folder for storing generated images and temp audio.
- `output/`: Where final videos are saved.
- `script.json`: The blueprint for the current video.

## How to Use
1. **Plan & Generate Assets**: The Agent (me) generates the script and images based on your topic.
2. **Configure**: The `script.json` is updated with the text and image paths.
3. **Build**: Run the assembly script.

```bash
# Activate environment
source venv/bin/activate

# Run assembler
python shorts_factory/scripts/assemble_video.py --script shorts_factory/script.json --output shorts_factory/output/final_video.mp4
```

## Requirements
- Python 3.9+
- ffmpeg (installed via imageio-ffmpeg)
- Internet connection (for Edge TTS)

## Content Guidelines (Strict)
1. **Duration**: Must be **under 60 seconds** (Shorts format).
2. **Structure**: Maximum **3 Key Points** per video.
3. **Style**: concise, no unnecessary filler, density insight.

