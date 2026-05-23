import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import axios from 'axios'

// 配置 axios 默认指向后端地址
axios.defaults.baseURL = 'http://localhost:8000'
axios.defaults.timeout = 60000  // 60秒，大文件上传校验需要时间

const app = createApp(App)

// 把 axios 挂到全局，方便组件里 this.$http 直接用
app.config.globalProperties.$http = axios

app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')