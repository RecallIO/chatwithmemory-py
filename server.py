import json
from flask import Flask, request, jsonify
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


app = Flask(__name__)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    user_text = (data.get('message') or '').strip()
    if not user_text:
        return jsonify({'error': 'message is required'}), 400

    cfg = app.config['cfg']
    openai_client = app.config['openai_client']
    recall_client = app.config['recall_client']
    project_id = cfg['recallio']['project_id']
    user_id = cfg['recallio'].get('user_id', 'default_user')

    try:
        recall_client.write_memory(
            MemoryWriteRequest(userId=user_id, projectId=project_id, content=user_text, consentFlag=True)
        )
    except Exception as e:
        return jsonify({'error': f'RecallIO write failed: {e}'}), 500

    summary_text = ''
    try:
        recall_req = MemoryRecallRequest(
            projectId=project_id,
            userId=user_id,
            query=user_text,
            scope='user',
            summarized=True,
            similarityThreshold=0.5,
            limit=10,
        )
        memories = recall_client.recall_memory(recall_req)
        if memories:
            summary = memories[0]
            if summary.content:
                summary_text = summary.content
    except RecallioAPIError as e:
        summary_text = ''
    except Exception as e:
        return jsonify({'error': f'RecallIO recall failed: {e}'}), 500

    messages = []
    if summary_text:
        messages.append({'role': 'system', 'content': f'Recalled Summary: {summary_text}'})
    messages.append({'role': 'user', 'content': user_text})

    try:
        response = openai_client.chat.completions.create(model='gpt-3.5-turbo', messages=messages)
        reply = response.choices[0].message.content
    except Exception as e:
        return jsonify({'error': f'OpenAI error: {e}'}), 500

    return jsonify({'reply': reply})


def main():
    try:
        cfg = load_config()
        openai_client, recall_client = create_clients(cfg)
    except Exception as e:
        print(f'Configuration Error: {e}')
        return

    app.config['cfg'] = cfg
    app.config['openai_client'] = openai_client
    app.config['recall_client'] = recall_client
    app.run(debug=True)


if __name__ == '__main__':
    main()
