import { useMemo, useReducer, useState } from 'react'
import { Download, Moon, Save, Sun, GripVertical, FolderOpen, LogIn, Share2, WandSparkles } from 'lucide-react'
import SlideCard from '../components/SlideCard'
import { useDebounce } from '../hooks/useDebounce'
import type { Slide } from '../types'
import { slideReducer } from '../features/slides/slideStore'
import { themes, type ThemeName } from '../theme/themes'
import LandingPage from './landing/LandingPage'

const API_BASE = 'http://localhost:8000'

export default function App() {
  const [topic, setTopic] = useState('IoT là gì')
  const [description, setDescription] = useState('Giải thích tổng quan cho người mới bắt đầu')
  const [slideCount, setSlideCount] = useState(6)
  const [language, setLanguage] = useState<'vi' | 'en'>('vi')
  const [theme, setTheme] = useState<ThemeName>('minimal')
  const [style, setStyle] = useState<'professional' | 'casual' | 'storytelling'>('professional')
  const [projectIdInput, setProjectIdInput] = useState('')
  const [slides, dispatch] = useReducer(slideReducer, [])
  const [isLoading, setIsLoading] = useState(false)
  const [dark, setDark] = useState(true)
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [loadingSlides, setLoadingSlides] = useState<number[]>([])
  const [rewriteInput, setRewriteInput] = useState('')
  const [rewriteOutput, setRewriteOutput] = useState('')
  const [token, setToken] = useState('')
  const [publicView, setPublicView] = useState(false)
  const [showLanding, setShowLanding] = useState(true)
  const [usage, setUsage] = useState<Record<string, number>>({})

  const debouncedTopic = useDebounce(topic, 400)
  const canGenerate = useMemo(() => debouncedTopic.trim().length >= 2 && !isLoading, [debouncedTopic, isLoading])
  const visibleSlides = useMemo(() => slides.slice(0, 30), [slides]) // light virtual-list style limit

  const login = async () => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'demo', password: 'demo123' }),
    })
    const data = await res.json()
    setToken(data.access_token || '')
  }

  const generateSlides = async () => {
    setIsLoading(true)
    setLoadingSlides(Array.from({ length: slideCount }, (_, i) => i))
    dispatch({ type: 'setSlides', payload: [] })

    try {
      const res = await fetch(`${API_BASE}/api/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, description, slide_count: slideCount, language, theme, style }),
      })

      if (!res.body) return
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let idx = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''
        for (const evt of events) {
          const line = evt.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue
          const payload = JSON.parse(line.replace('data: ', '')) as Slide
          dispatch({ type: 'addSlide', payload })
          setLoadingSlides((prev) => prev.filter((n) => n !== idx))
          idx += 1
        }
      }
    } finally {
      setIsLoading(false)
      setLoadingSlides([])
    }
  }

  const saveProject = async () => {
    const res = await fetch(`${API_BASE}/api/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ topic, payload: { slides } }),
    })
    const data = await res.json()
    setProjectIdInput(String(data.project_id || ''))
  }

  const loadProject = async () => {
    if (!projectIdInput) return
    const endpoint = publicView ? `/api/share/${projectIdInput}` : `/api/project/${projectIdInput}`
    const res = await fetch(`${API_BASE}${endpoint}`)
    const data = await res.json()
    dispatch({ type: 'setSlides', payload: data.slides || [] })
  }

  const regenerateImage = async (index: number, keyword: string) => {
    const res = await fetch(`${API_BASE}/api/image?keyword=${encodeURIComponent(keyword)}`)
    const data = await res.json()
    const old = slides[index]
    if (!old) return
    dispatch({ type: 'updateSlide', payload: { index, slide: { ...old, image_keyword: keyword, image_url: data.image_url } } })
  }

  const rewriteText = async (mode: 'shorten' | 'expand' | 'rewrite_tone') => {
    const res = await fetch(`${API_BASE}/api/rewrite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: rewriteInput, mode, tone: style }),
    })
    const data = await res.json()
    setRewriteOutput(data.result || '')
  }


  const loadAnalytics = async () => {
    if (!token) return
    const res = await fetch(`${API_BASE}/api/analytics`, { headers: { Authorization: `Bearer ${token}` } })
    const data = await res.json()
    setUsage(data.usage || {})
  }
  const exportPptx = async () => {
    const res = await fetch(`${API_BASE}/api/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slides }),
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'generated-slides.pptx'
    a.click()
    URL.revokeObjectURL(url)
  }

  const onDrop = (dropIndex: number) => {
    if (dragIndex === null || dragIndex === dropIndex) return
    dispatch({ type: 'reorderSlide', payload: { from: dragIndex, to: dropIndex } })
    setDragIndex(null)
  }

  const t = themes[theme]

  if (showLanding) {
    return <LandingPage onStart={() => setShowLanding(false)} />
  }

  return (
    <div className={dark ? 'dark' : ''}>
      <div className="min-h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-white">
        <div className="mx-auto max-w-7xl p-6">
          <header className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-bold">AI Presentation SaaS</h1>
            <div className="flex gap-2">
              <button onClick={login} className="rounded border border-slate-600 px-3"><LogIn className="mr-2 inline" size={14} />Login demo</button>
              <button onClick={loadAnalytics} className="rounded border border-slate-600 px-3">Usage</button>
              <button onClick={() => setDark((v) => !v)} className="rounded border border-slate-600 p-2">{dark ? <Sun size={16} /> : <Moon size={16} />}</button>
            </div>
          </header>

          <section className={`mb-6 grid grid-cols-1 gap-3 rounded-xl border p-4 md:grid-cols-3 ${t.card} ${t.text}`}>
            <input className="rounded bg-slate-800 p-2" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic" />
            <input className="rounded bg-slate-800 p-2" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" />
            <input className="rounded bg-slate-800 p-2" type="number" min={3} max={30} value={slideCount} onChange={(e) => setSlideCount(Number(e.target.value))} />
            <select className="rounded bg-slate-800 p-2" value={language} onChange={(e) => setLanguage(e.target.value as 'vi' | 'en')}><option value="vi">Tiếng Việt</option><option value="en">English</option></select>
            <select className="rounded bg-slate-800 p-2" value={theme} onChange={(e) => setTheme(e.target.value as ThemeName)}><option value="minimal">minimal</option><option value="business">business</option><option value="colorful">colorful</option></select>
            <select className="rounded bg-slate-800 p-2" value={style} onChange={(e) => setStyle(e.target.value as 'professional' | 'casual' | 'storytelling')}><option value="professional">professional</option><option value="casual">casual</option><option value="storytelling">storytelling</option></select>

            <div className="col-span-full flex flex-wrap gap-3">
              <button onClick={generateSlides} disabled={!canGenerate} className={`rounded px-4 py-2 font-medium disabled:opacity-50 ${t.accent}`}>{isLoading ? 'AI is thinking...' : 'Generate'}</button>
              <button onClick={exportPptx} disabled={!slides.length} className="rounded border border-slate-500 px-4 py-2 disabled:opacity-50"><Download className="mr-2 inline" size={16} /> Export PPTX</button>
              <button onClick={saveProject} disabled={!slides.length} className="rounded border border-slate-500 px-4 py-2 disabled:opacity-50"><Save className="mr-2 inline" size={16} /> Save</button>
              <input className="rounded bg-slate-800 p-2" placeholder="Project ID" value={projectIdInput} onChange={(e) => setProjectIdInput(e.target.value)} />
              <button onClick={loadProject} className="rounded border border-slate-500 px-4 py-2"><FolderOpen className="mr-2 inline" size={16} /> Load</button>
              <button onClick={() => setPublicView((v) => !v)} className="rounded border border-slate-500 px-4 py-2"><Share2 className="mr-2 inline" size={16} /> {publicView ? 'Public view' : 'Private view'}</button>
            </div>
          </section>

          <section className="mb-6 rounded-xl border border-slate-700 bg-slate-950/60 p-4">
            <h2 className="mb-3 text-lg font-semibold"><WandSparkles className="mr-2 inline" size={16} /> AI Rewrite</h2>
            <textarea className="mb-2 h-24 w-full rounded bg-slate-800 p-2" value={rewriteInput} onChange={(e) => setRewriteInput(e.target.value)} placeholder="Select/edit text then rewrite..." />
            <div className="mb-2 flex gap-2">
              <button className="rounded border border-slate-500 px-3 py-1" onClick={() => rewriteText('shorten')}>shorten</button>
              <button className="rounded border border-slate-500 px-3 py-1" onClick={() => rewriteText('expand')}>expand</button>
              <button className="rounded border border-slate-500 px-3 py-1" onClick={() => rewriteText('rewrite_tone')}>rewrite tone</button>
            </div>
            <div className="rounded bg-slate-800 p-2 text-slate-200">{rewriteOutput}</div>
          </section>

          <section className="mb-6 rounded-xl border border-slate-700 bg-slate-950/60 p-4">
            <h2 className="mb-2 text-lg font-semibold">Usage Analytics</h2>
            <pre className="rounded bg-slate-800 p-3 text-sm text-slate-200">{JSON.stringify(usage, null, 2)}</pre>
          </section>

          <section className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
            <h2 className="mb-4 text-lg font-semibold">Slide Editor (advanced streaming UX)</h2>
            <div className="space-y-3">
              {visibleSlides.map((slide, index) => (
                <div key={`${slide.title}-${index}`} draggable={!publicView} onDragStart={() => setDragIndex(index)} onDragOver={(e) => e.preventDefault()} onDrop={() => onDrop(index)} className="rounded-xl border border-transparent hover:border-indigo-500">
                  <div className="mb-1 flex items-center gap-2 text-xs text-slate-400"><GripVertical size={14} /> Kéo để đổi thứ tự</div>
                  <SlideCard slide={slide} index={index} onRegenerateImage={regenerateImage} onChange={(next) => dispatch({ type: 'updateSlide', payload: { index, slide: next } })} />
                </div>
              ))}

              {isLoading && loadingSlides.map((skeletonId) => (
                <div key={`skeleton-${skeletonId}`} className="animate-pulse rounded-xl border border-slate-700 bg-slate-900 p-4">
                  <div className="mb-2 h-6 w-1/2 rounded bg-slate-700" />
                  <div className="mb-2 h-4 w-3/4 rounded bg-slate-700" />
                  <div className="h-20 w-full rounded bg-slate-700" />
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
