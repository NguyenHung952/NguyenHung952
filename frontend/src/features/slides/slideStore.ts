import type { Slide } from '../../types'

export type SlideAction =
  | { type: 'addSlide'; payload: Slide }
  | { type: 'updateSlide'; payload: { index: number; slide: Slide } }
  | { type: 'reorderSlide'; payload: { from: number; to: number } }
  | { type: 'setSlides'; payload: Slide[] }

export function slideReducer(state: Slide[], action: SlideAction): Slide[] {
  switch (action.type) {
    case 'addSlide':
      return [...state, action.payload]
    case 'updateSlide':
      return state.map((slide, index) => (index === action.payload.index ? action.payload.slide : slide))
    case 'reorderSlide': {
      const next = [...state]
      const [moved] = next.splice(action.payload.from, 1)
      next.splice(action.payload.to, 0, moved)
      return next
    }
    case 'setSlides':
      return action.payload
    default:
      return state
  }
}
