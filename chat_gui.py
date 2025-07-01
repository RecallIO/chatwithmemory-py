import json
import tkinter as tk
from tkinter import scrolledtext
from recallio import RecallioClient, MemoryWriteRequest, MemoryRecallRequest, RecallioAPIError
import openai

CONFIG_FILE = 'config.json'


def load_config():
    with open(CONFIG_FILE, 'r') as f:
        cfg = json.load(f)
    if not cfg.get('openai', {}).get('api_key'):
        raise ValueError('OpenAI API key missing in config.json')
    rc = cfg.get('recallio', {})
    if not rc.get('api_key') or not rc.get('project_id'):
        raise ValueError('RecallIO configuration incomplete in config.json')
    return cfg


class ChatApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.openai_client = openai.OpenAI(api_key=cfg['openai']['api_key'])
        self.recall_client = RecallioClient(api_key=cfg['recallio']['api_key'])
        self.project_id = cfg['recallio']['project_id']
        self.user_id = cfg['recallio'].get('user_id', 'default_user')
        self._build_ui()

    def _build_ui(self):
        self.root.title('RecallIO Chat')
        self.root.geometry('600x600')
        self.root.configure(bg='#f5f5f5')

        self.chat_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, bg='white')
        self.chat_area.configure(state='disabled')
        self.chat_area.pack(padx=10, pady=10, fill='both', expand=True)

        tk.Label(self.root, text='Recalled summary:', bg='#f5f5f5', fg='#333').pack(anchor='w', padx=10)
        self.recall_area = tk.Text(self.root, height=4, bg='#eef', wrap=tk.WORD)
        self.recall_area.configure(state='disabled')
        self.recall_area.pack(padx=10, pady=(0, 10), fill='x')

        input_frame = tk.Frame(self.root, bg='#f5f5f5')
        input_frame.pack(padx=10, pady=10, fill='x')
        self.entry = tk.Entry(input_frame)
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.entry.bind('<Return>', self.send_message)
        tk.Button(input_frame, text='Send', command=self.send_message).pack(side='right')

    def append_chat(self, sender, text):
        self.chat_area.configure(state='normal')
        self.chat_area.insert(tk.END, f"{sender}: {text}\n")
        self.chat_area.configure(state='disabled')
        self.chat_area.yview(tk.END)

    def update_recall(self, text):
        self.recall_area.configure(state='normal')
        self.recall_area.delete('1.0', tk.END)
        self.recall_area.insert(tk.END, text)
        self.recall_area.configure(state='disabled')

    def send_message(self, event=None):
        user_text = self.entry.get().strip()
        if not user_text:
            return
        self.entry.delete(0, tk.END)
        self.append_chat('You', user_text)

        try:
            self.recall_client.write_memory(
                MemoryWriteRequest(userId=self.user_id, projectId=self.project_id, content=user_text, consentFlag=True)
            )
        except Exception as e:
            self.append_chat('Error', f'RecallIO write failed: {e}')
            return

        summary_text = ''
        try:
            recall_req = MemoryRecallRequest(
                projectId=self.project_id,
                userId=self.user_id,
                query=user_text,
                scope='user',
                summarized=True,
                similarityThreshold=0.5,
                limit=10,
            )
            memories = self.recall_client.recall_memory(recall_req)
            if memories:
                first = memories[0]
                summary_text = getattr(first, 'content', '') or getattr(first, 'summary', '')
        except RecallioAPIError:
            summary_text = ''
        except Exception as e:
            self.append_chat('Error', f'RecallIO recall failed: {e}')
            return
        if summary_text:
            self.update_recall(summary_text)

        messages = []
        if summary_text:
            messages.append({'role': 'system', 'content': f'Recalled Summary: {summary_text}'})
        messages.append({'role': 'user', 'content': user_text})

        try:
            response = self.openai_client.chat.completions.create(model='gpt-3.5-turbo', messages=messages)
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            self.append_chat('Error', f'OpenAI error: {e}')
            return
        self.append_chat('Assistant', reply)

def main():
    try:
        cfg = load_config()
    except Exception as e:
        print(f'Configuration Error: {e}')
        return

    root = tk.Tk()
    ChatApp(root, cfg)
    root.mainloop()


if __name__ == '__main__':
    main()
