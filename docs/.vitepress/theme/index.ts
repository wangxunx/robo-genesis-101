import DefaultTheme from 'vitepress/theme'
import './custom.css'
import type { Theme } from 'vitepress'
import 'viewerjs/dist/viewer.min.css';
import imageViewer from 'vitepress-plugin-image-viewer';
import vImageViewer from 'vitepress-plugin-image-viewer/lib/vImageViewer.vue';
import { useRoute } from 'vitepress';
import { h } from 'vue';

const announcementText = {
    root: '⚠️ Alpha 内测版本 · Alpha preview: course content is incomplete and may change.',
    zh: '⚠️ Alpha 内测版本：课程内容尚未完成，可能发生变更，欢迎通过 Issue 提交反馈。',
    en: '⚠️ Alpha preview: course content is incomplete and may change. Feedback is welcome through Issues.'
}

const Announcement = {
    setup() {
        const route = useRoute()
        return () => {
            const locale = /\/en(?:\/|$)/.test(route.path)
                ? 'en'
                : /\/zh(?:\/|$)/.test(route.path)
                  ? 'zh'
                  : 'root'
            return h('div', { class: 'announcement-banner' }, announcementText[locale])
        }
    }
}

export default {
    extends: DefaultTheme,
    enhanceApp({ app }) {
        // 注册全局组件（可选）
        app.component('vImageViewer', vImageViewer);
    },
    setup() {
        const route = useRoute();
        // 启用插件
        imageViewer(route);
    },
    Layout() {
        return h(DefaultTheme.Layout, null, {
            'layout-top': () => h(Announcement)
        })
    }
} satisfies Theme
