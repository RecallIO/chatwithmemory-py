import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import openai
from recallio import RecallioClient, MemoryWriteRequest, MemoryRecallRequest, RecallioAPIError

CONFIG_FILE = 'config.json'


def load_config():
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    if 'openai' not in config or not config['openai'].get('api_key'):
        raise ValueError('OpenAI API key missing in config.json')
    recall_cfg = config.get('recallio', {})
    if not recall_cfg.get('api_key') or not recall_cfg.get('project_id'):
        raise ValueError('RecallIO configuration missing in config.json')
    return config


def create_clients(cfg):
    openai_client = openai.OpenAI(api_key=cfg['openai']['api_key'])
    recall_client = RecallioClient(api_key=cfg['recallio']['api_key'])
    return openai_client, recall_client


class ChatGUI:
    def __init__(self, root, openai_client, recall_client, cfg):
        self.root = root
        self.openai_client = openai_client
        self.recall_client = recall_client
        self.project_id = cfg['recallio']['project_id']
        self.user_id = cfg['recallio'].get('user_id', 'default_user')

        root.title("RecallIO Chat")
        root.geometry("600x400")

        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        bottom = ttk.Frame(root)
        bottom.pack(fill=tk.X, padx=10, pady=5)

        self.entry = ttk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind('<Return>', self.send_message)

        send_btn = ttk.Button(bottom, text="Send", command=self.send_message)
        send_btn.pack(side=tk.RIGHT)

    def append_text(self, speaker, text):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, f"{speaker}: {text}\n")
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def send_message(self, event=None):
        user_text = self.entry.get().strip()
        if not user_text:
            return
        self.entry.delete(0, tk.END)
        self.append_text('You', user_text)

        try:
            write_req = MemoryWriteRequest(userId=self.user_id, projectId=self.project_id, content=user_text, consentFlag=True)
            self.recall_client.write_memory(write_req)
        except Exception as e:
            messagebox.showerror('RecallIO Write Error', str(e))

        summary_text = ''
        try:
            recall_req = MemoryRecallRequest(
                projectId=self.project_id,
                userId=self.user_id,
                query=user_text,
                scope='user',
                summarized=True,
                similarityThreshold=0.5,
            )
            memories = self.recall_client.recall_memory(recall_req)
            if memories:
                summary = memories[0]
                if summary.content:
                    summary_text = summary.content
        except RecallioAPIError as e:
            messagebox.showwarning('RecallIO Recall Error', str(e))
        except Exception as e:
            messagebox.showwarning('RecallIO Error', str(e))

        messages = []
        if summary_text:
            messages.append({'role': 'system', 'content': f'Recalled Summary: {summary_text}'})
        messages.append({'role': 'user', 'content': user_text})

        try:
            response = self.openai_client.chat.completions.create(model='gpt-3.5-turbo', messages=messages)
            reply = response.choices[0].message.content
            self.append_text('Assistant', reply)
            try:
                self.recall_client.write_memory(MemoryWriteRequest(userId=self.user_id, projectId=self.project_id, content=reply, consentFlag=True))
            except Exception as e:
                messagebox.showwarning('RecallIO Write Error', str(e))
        except Exception as e:
            messagebox.showerror('OpenAI Error', str(e))


def main():
    try:
        cfg = load_config()
        openai_client, recall_client = create_clients(cfg)
    except Exception as e:
        messagebox.showerror('Configuration Error', str(e))
        return

    root = tk.Tk()
    app = ChatGUI(root, openai_client, recall_client, cfg)
    root.mainloop()


if __name__ == '__main__':
    main()
