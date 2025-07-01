import { useState } from 'react';

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { from: 'You', text: userText }]);
    try {
      const res = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      });
      const data = await res.json();
      if (data.reply) {
        setMessages(prev => [...prev, { from: 'Assistant', text: data.reply }]);
      } else if (data.error) {
        setMessages(prev => [...prev, { from: 'Error', text: data.error }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { from: 'Error', text: String(e) }]);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: '20px auto', fontFamily: 'Arial' }}>
      <h1>RecallIO Chat</h1>
      <div style={{ border: '1px solid #ccc', padding: 10, height: 400, overflowY: 'scroll' }}>
        {messages.map((m, i) => (
          <div key={i}><strong>{m.from}:</strong> {m.text}</div>
        ))}
      </div>
      <div style={{ display: 'flex', marginTop: 10 }}>
        <input
          style={{ flex: 1, marginRight: 5 }}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => (e.key === 'Enter' && sendMessage())}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
