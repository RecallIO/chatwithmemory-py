# RecallIO Chat


This project provides a simple desktop chat application built with Tkinter. It connects to OpenAI and RecallIO, storing your messages and recalling summarized memories relevant to your input.

## Setup
=======
This project offers a small web chat that connects to OpenAI and RecallIO. A Flask backend handles the chat logic while a simple Next.js UI provides a modern interface.

## Backend

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Fill out `config.json` with your OpenAI and RecallIO credentials.

## Running

Start the chat application with:
```bash
python chat_gui.py
```
The top area shows the conversation while the lower panel displays the latest recalled summary from RecallIO.