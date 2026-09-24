// 应用入口 —— 注册 Pinia / Router / Element Plus(中文), 样式加载顺序:
// element 官方样式 → 设计令牌 → Element 主题覆盖 → 全局基础样式(后者覆盖前者)
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './styles/fonts.css'
import './styles/tokens.css'
import './styles/element-theme.css'
import './styles/base.css'

createApp(App)
  .use(createPinia())
  .use(router)
  .use(ElementPlus, { locale: zhCn })
  .mount('#app')
