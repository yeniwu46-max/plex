export interface DefenseMeta {
  title: string
  subtitle: string
  version: string
  tagline: string
  a3BaseUrl: string
}

export interface DefensePage {
  id: string
  title: string
  icon: string
  sections: string[]
}

export interface ScriptStep {
  label: string
  account: string | null
  path: string | null
}

export interface FaqItem {
  q: string
  a: string
}

export interface UserCard {
  role: string
  label: string
  color: string
  routes: string[]
}

export interface FeatureSection {
  id: string
  title: string
  summary?: string
  screenshot?: string
  demoUrl?: string
  demoUrlTeacher?: string
  bullets?: string[]
  pitch?: string
  table?: string[][]
  cards?: UserCard[]
  commands?: string[]
  accounts?: { role: string; user: string; pass: string }[]
  steps?: ScriptStep[]
  extends?: string
  faqs?: FaqItem[]
}

export interface ScreenshotItem {
  file: string
  label: string
  route: string
}

export interface DefenseManifest {
  meta: DefenseMeta
  pages: DefensePage[]
  sections: FeatureSection[]
  screenshots: ScreenshotItem[]
}
