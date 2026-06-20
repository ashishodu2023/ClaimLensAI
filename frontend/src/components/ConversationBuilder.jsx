import { useState } from 'react'
import { Plus, X } from 'lucide-react'

export default function ConversationBuilder({ conversation, setConversation }) {
  const [role, setRole] = useState('user')
  const [text, setText] = useState('')

  const add = () => {
    if (!text.trim()) return
    setConversation((prev) => [...prev, { role, text: text.trim() }])
    setText('')
  }

  const remove = (i) => setConversation((prev) => prev.filter((_, idx) => idx !== i))

  return (
    <div>
      {conversation.length === 0 ? (
        <p className="text-xs text-muted text-center py-3">No messages yet</p>
      ) : (
        <div className="flex flex-col gap-1.5 mb-2.5 max-h-48 overflow-y-auto pr-1">
          {conversation.map((turn, i) => (
            <div key={i} className="flex items-start gap-2 bg-surface2 border border-border rounded-md px-2.5 py-2">
              <span className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded flex-shrink-0 ${
                turn.role === 'user'
                  ? 'bg-accent/15 text-accent'
                  : 'bg-purple-500/15 text-purple-400'
              }`}>
                {turn.role}
              </span>
              <span className="text-xs text-white flex-1 leading-relaxed">{turn.text}</span>
              <button onClick={() => remove(i)} className="text-muted hover:text-red-400 transition-colors flex-shrink-0">
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-1.5">
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="select-field w-20 flex-shrink-0 text-xs"
        >
          <option value="user">User</option>
          <option value="agent">Agent</option>
        </select>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder="Message text…"
          className="input-field flex-1 text-xs"
        />
        <button onClick={add} className="btn-ghost flex-shrink-0">
          <Plus size={14} />
        </button>
      </div>
    </div>
  )
}
