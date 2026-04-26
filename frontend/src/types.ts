export type SlideLayout = 'title' | 'content' | 'image_left' | 'image_right' | 'section'
export type SlideRole = 'title' | 'introduction' | 'section' | 'content' | 'key_point' | 'summary'

export type Slide = {
  title: string
  subtitle?: string
  bullets: string[]
  role?: SlideRole
  summary?: string
  image?: string
  image_keyword?: string
  image_url?: string
  layout?: SlideLayout
}
