import { readFileSync } from 'node:fs'

import { defineConfig } from 'vitepress'

type Locale = 'zh' | 'en'

interface LessonMetadata {
  id: string
  title: Record<Locale, string>
  lecture: Record<Locale, string>
}

interface CourseManifest {
  course: {
    title: Record<Locale, string>
  }
  lessons: LessonMetadata[]
}

const course = JSON.parse(
  readFileSync(new URL('../../course.json', import.meta.url), 'utf-8')
) as CourseManifest

const repositoryUrl = 'https://github.com/wangxunx/robo-genesis-101'
const isEdgeOne = process.env.EDGEONE === '1'
const base = isEdgeOne ? '/' : '/robo-genesis-101/'

function pageLink(sourcePath: string): string {
  if (!sourcePath.startsWith('docs/') || !sourcePath.endsWith('.md')) {
    throw new Error(`Invalid lecture path in course.json: ${sourcePath}`)
  }
  return `/${sourcePath.slice('docs/'.length, -'.md'.length)}`
}

function lessonSidebar(locale: Locale) {
  return [
    {
      text: locale === 'zh' ? '课程目录' : 'Course Outline',
      items: course.lessons.map((lesson) => ({
        text: `${lesson.id} · ${lesson.title[locale]}`,
        link: pageLink(lesson.lecture[locale])
      }))
    }
  ]
}

const firstLessonLink = {
  zh: pageLink(course.lessons[0].lecture.zh),
  en: pageLink(course.lessons[0].lecture.en)
}

const editLinkPattern = `${repositoryUrl}/edit/main/docs/:path`

export default defineConfig({
  lang: 'zh-CN',
  title: 'RoboGenesis 101',
  description: 'A practical bilingual course on robot learning with Genesis',
  base,
  markdown: {
    math: true
  },
  locales: {
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      link: '/zh/',
      title: course.course.title.zh,
      description: '基于 Genesis 的机器人学习实践课程',
      themeConfig: {
        nav: [
          { text: '首页', link: '/zh/' },
          { text: '课程', link: firstLessonLink.zh }
        ],
        sidebar: {
          '/zh/lessons/': lessonSidebar('zh')
        },
        editLink: {
          pattern: editLinkPattern,
          text: '在 GitHub 上编辑此页'
        },
        outline: {
          label: '本页目录'
        },
        docFooter: {
          prev: '上一讲',
          next: '下一讲'
        },
        sidebarMenuLabel: '课程目录',
        returnToTopLabel: '返回顶部',
        langMenuLabel: '切换语言',
        darkModeSwitchLabel: '主题',
        lightModeSwitchTitle: '切换到浅色主题',
        darkModeSwitchTitle: '切换到深色主题',
        skipToContentLabel: '跳到正文',
        footer: {
          copyright:
            '除另有注明的第三方材料外，本项目原创内容采用 MIT License；第三方材料保留原许可'
        }
      }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      title: course.course.title.en,
      description: 'A practical robot learning course built with Genesis',
      themeConfig: {
        nav: [
          { text: 'Home', link: '/en/' },
          { text: 'Lessons', link: firstLessonLink.en }
        ],
        sidebar: {
          '/en/lessons/': lessonSidebar('en')
        },
        editLink: {
          pattern: editLinkPattern,
          text: 'Edit this page on GitHub'
        },
        outline: {
          label: 'On this page'
        },
        docFooter: {
          prev: 'Previous lesson',
          next: 'Next lesson'
        },
        sidebarMenuLabel: 'Course outline',
        returnToTopLabel: 'Return to top',
        langMenuLabel: 'Change language',
        darkModeSwitchLabel: 'Theme',
        lightModeSwitchTitle: 'Switch to light theme',
        darkModeSwitchTitle: 'Switch to dark theme',
        skipToContentLabel: 'Skip to content',
        footer: {
          copyright:
            'Original project content is MIT licensed unless noted otherwise; third-party materials retain their original licenses'
        }
      }
    }
  },
  themeConfig: {
    logo: '/datawhale-logo.png',
    nav: [
      { text: '中文', link: '/zh/' },
      { text: 'English', link: '/en/' }
    ],
    search: {
      provider: 'local',
      options: {
        locales: {
          zh: {
            translations: {
              button: {
                buttonText: '搜索课程',
                buttonAriaLabel: '搜索课程'
              },
              modal: {
                displayDetails: '显示详细列表',
                resetButtonTitle: '清除查询条件',
                backButtonTitle: '关闭搜索',
                noResultsText: '没有找到相关内容',
                footer: {
                  selectText: '选择',
                  navigateText: '切换',
                  closeText: '关闭'
                }
              }
            }
          },
          en: {
            translations: {
              button: {
                buttonText: 'Search lessons',
                buttonAriaLabel: 'Search lessons'
              },
              modal: {
                displayDetails: 'Display detailed list',
                resetButtonTitle: 'Reset search',
                backButtonTitle: 'Close search',
                noResultsText: 'No results found',
                footer: {
                  selectText: 'Select',
                  navigateText: 'Navigate',
                  closeText: 'Close'
                }
              }
            }
          }
        }
      }
    },
    socialLinks: [{ icon: 'github', link: repositoryUrl }],
    editLink: {
      pattern: editLinkPattern,
      text: 'Edit / 编辑'
    },
    footer: {
      copyright: 'RoboGenesis 101 · MIT licensed original content'
    }
  }
})
