export const themes = {
  minimal: {
    card: 'bg-slate-900 border-slate-700',
    accent: 'bg-indigo-500',
    text: 'text-white',
  },
  business: {
    card: 'bg-zinc-900 border-zinc-600',
    accent: 'bg-blue-700',
    text: 'text-zinc-50',
  },
  colorful: {
    card: 'bg-purple-950 border-pink-500',
    accent: 'bg-pink-500',
    text: 'text-pink-50',
  },
} as const

export type ThemeName = keyof typeof themes
