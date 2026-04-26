export default function LandingPage({ onStart }: { onStart: () => void }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="mb-4 text-5xl font-bold">AI Presentation SaaS</h1>
        <p className="mb-8 text-lg text-slate-300">Create, design, and share professional slides in minutes.</p>
        <div className="mb-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-700 p-4">⚡ Generate with AI + streaming</div>
          <div className="rounded-xl border border-slate-700 p-4">🎨 Smart layouts + design system</div>
          <div className="rounded-xl border border-slate-700 p-4">📤 Export, save, and share links</div>
        </div>
        <button onClick={onStart} className="rounded bg-indigo-500 px-6 py-3 font-semibold">Start Free</button>
      </div>
    </div>
  )
}
