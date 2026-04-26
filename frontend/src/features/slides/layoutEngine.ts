import type { Slide, SlideLayout } from '../../types'

export function resolveLayout(slide: Slide): SlideLayout {
  if (slide.layout) return slide.layout
  if (slide.image_keyword || slide.image_url) return 'image_right'
  return 'content'
}
