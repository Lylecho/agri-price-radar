import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 统一请求封装（蓝图 §6: 响应结构 {code, msg, data}）
 * - 后端鉴权失败返回 HTTP 200 + body.code=401, 故在响应拦截器内判定业务码
 * - 401: 清理登录态并跳转登录页
 * - 其他错误码: 统一 toast 提示并 reject
 */
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8081',
  timeout: 20000,
})

// 请求拦截: 附加 JWT
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('apr_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 跳转登录页(避免与 router 循环依赖, 使用 location)
function redirectToLogin() {
  localStorage.removeItem('apr_token')
  localStorage.removeItem('apr_user')
  if (!window.location.hash.includes('/login') && !window.location.pathname.includes('/login')) {
    window.location.href = '/login'
  }
}

request.interceptors.response.use(
  (response) => {
    const body = response.data
    // 非标准结构(如静态资源)直接返回
    if (body == null || typeof body.code === 'undefined') {
      return body
    }
    if (body.code === 200) {
      return body.data
    }
    if (body.code === 401) {
      ElMessage.error(body.msg || '未登录或登录已过期')
      redirectToLogin()
      return Promise.reject(new Error(body.msg || '未登录'))
    }
    if (body.code === 403 && body.msg === '请先修改初始密码' && window.location.pathname !== '/change-password') {
      window.location.href = '/change-password'
    }
    ElMessage.error(body.msg || '请求失败')
    return Promise.reject(new Error(body.msg || '请求失败'))
  },
  (error) => {
    const msg = error.response
      ? `请求失败 (HTTP ${error.response.status})`
      : '网络异常, 请检查后端服务是否启动'
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

export default request
