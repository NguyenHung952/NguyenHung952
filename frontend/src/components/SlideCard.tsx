import { typography } from '../design/designSystem'
import { resolveLayout } from '../features/slides/layoutEngine'
import type { Slide, SlideRole } from '../types'

type Props = {
  slide: Slide
  index: number
  onChange: (next: Slide) => void
  onRegenerateImage: (index: number, keyword: string) => void
}

export default function SlideCard({ slide, index, onChange, onRegenerateImage }: Props) {
  const layout = resolveLayout(slide)
  const role = slide.role ?? 'content'

  return (
    <div className="animate-fade-in rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-md transition-opacity duration-500">
      <div className="mb-2 text-xs text-slate-400">Slide {index + 1} · {layout} · role: {role}</div>
      <div className={`grid gap-4 ${layout.startsWith('image_') ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
        {layout === 'image_left' && slide.image_url && <img src={slide.image_url} alt={slide.image_keyword || slide.title} className="h-48 w-full rounded object-cover" />}

        <div className="space-y-2">
          <input className={`w-full rounded bg-slate-800 p-2 ${typography[role as SlideRole] || typography.content}`} value={slide.title} onChange={(e) => onChange({ ...slide, title: e.target.value })} />
          <input className="w-full rounded bg-slate-800 p-2 text-slate-300" placeholder="Subtitle" value={slide.subtitle ?? ''} onChange={(e) => onChange({ ...slide, subtitle: e.target.value })} />
          <textarea className="h-28 w-full rounded bg-slate-800 p-2 text-slate-200" value={slide.bullets.join('\n')} onChange={(e) => onChange({ ...slide, bullets: e.target.value.split('\n').filter(Boolean) })} />
          <select className="w-full rounded bg-slate-800 p-2" value={layout} onChange={(e) => onChange({ ...slide, layout: e.target.value as Slide['layout'] })}>
            <option value="title">title</option><option value="content">content</option><option value="image_left">image_left</option><option value="image_right">image_right</option><option value="section">section</option>
          </select>
          <select className="w-full rounded bg-slate-800 p-2" value={role} onChange={(e) => onChange({ ...slide, role: e.target.value as SlideRole })}>
            <option value="title">title</option><option value="introduction">introduction</option><option value="section">section</option><option value="content">content</option><option value="key_point">key_point</option><option value="summary">summary</option>
          </select>
          <input className="w-full rounded bg-slate-800 p-2 text-slate-300" placeholder="Image keyword" value={slide.image_keyword ?? ''} onChange={(e) => onChange({ ...slide, image_keyword: e.target.value })} />
          <button className="rounded border border-slate-500 px-3 py-1 text-xs" onClick={() => onRegenerateImage(index, slide.image_keyword || slide.title)}>Regenerate image</button>
        </div>

        {layout !== 'image_left' && slide.image_url && <img src={slide.image_url} alt={slide.image_keyword || slide.title} className="h-48 w-full rounded object-cover" />}
      </div>
    </div>
  )
}
