import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { sendChatMessage } from '../../api/chat'
import { useIdentity } from '../../context/IdentityContext'
import ToolResultCard from './ToolResultCard'

const GREETING = {
  role: 'assistant',
  content: "Hi! I can help you find a doctor, check availability, or book and cancel appointments. What do you need?",
  toolEvents: [],
}

export default function ChatWidget() {
  const { patientId } = useIdentity()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([GREETING])
  const [input, setInput] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, open])

  const chatMutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply, toolEvents: data.tool_events }])
      if (data.tool_events?.some((e) => ['book_appointment', 'cancel_appointment'].includes(e.tool))) {
        queryClient.invalidateQueries({ queryKey: ['patientAppointments'] })
      }
    },
    onError: (err) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Sorry, something went wrong: ${err.message}`, toolEvents: [] }])
    },
  })

  function handleSend(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || chatMutation.isPending) return
    if (!patientId) {
      setMessages((prev) => [...prev, { role: 'user', content: text }, { role: 'assistant', content: 'Please pick a patient profile from the top bar first.', toolEvents: [] }])
      setInput('')
      return
    }

    const history = messages
      .filter((m) => m !== GREETING)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    chatMutation.mutate({ message: text, conversationHistory: history, patientId })
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg transition-transform hover:scale-105 active:scale-95"
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? (
          <span className="text-xl leading-none">✕</span>
        ) : (
          <span className="text-2xl leading-none">💬</span>
        )}
      </button>

      {open && (
        <div className="animate-slide-up fixed inset-0 z-50 flex flex-col bg-white sm:inset-auto sm:bottom-24 sm:right-5 sm:h-[560px] sm:w-96 sm:rounded-2xl sm:border sm:border-slate-200 sm:shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">CarePoint Assistant</h3>
              <p className="text-xs text-slate-400">Booking help, powered by AI</p>
            </div>
            <button onClick={() => setOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 sm:hidden">
              ✕
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} />
            ))}
            {chatMutation.isPending && <TypingIndicator />}
          </div>

          <form onSubmit={handleSend} className="flex gap-2 border-t border-slate-200 p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 rounded-full border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              type="submit"
              disabled={!input.trim() || chatMutation.isPending}
              className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:bg-brand-300"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </>
  )
}

function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={clsx('animate-fade-in flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        className={clsx(
          'max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm',
          isUser ? 'rounded-br-sm bg-brand-600 text-white' : 'rounded-bl-sm bg-slate-100 text-slate-800',
        )}
      >
        {message.content}
      </div>
      {message.toolEvents?.length > 0 && (
        <div className="w-full max-w-[85%]">
          {message.toolEvents.map((e, i) => (
            <ToolResultCard key={i} event={e} />
          ))}
        </div>
      )}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3 w-fit">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}
