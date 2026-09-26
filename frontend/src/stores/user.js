import { defineStore } from 'pinia'
import { login as apiLogin, fetchMe } from '@/api/auth'

/**
 * 登录态 Store（token 持久化到 localStorage, 刷新页面保持登录）
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('apr_token') || '',
    username: '',
    nickname: '',
    role: '',
    mustChangePwd: false,
    profileLoaded: false,
  }),

  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.role === 'ADMIN',
    /** 角色中文名（顶栏展示） */
    roleLabel: (s) => (s.role === 'ADMIN' ? '超级管理员' : s.role === 'DATA_ADMIN' ? '数据管理员' : '未知角色'),
  },

  actions: {
    async login(payload) {
      const data = await apiLogin(payload)
      this.token = data.token
      this.username = data.username
      this.nickname = data.nickname || data.username
      this.role = data.role
      this.mustChangePwd = !!data.mustChangePwd
      this.profileLoaded = true
      localStorage.setItem('apr_token', data.token)
      localStorage.setItem('apr_user', JSON.stringify({ username: data.username, role: data.role }))
      return data
    },

    /** 刷新页面后从后端校验令牌并补齐用户信息 */
    async loadProfile() {
      const data = await fetchMe()
      this.username = data.username
      this.nickname = data.nickname || data.username
      this.role = data.role
      this.mustChangePwd = !!data.mustChangePwd
      this.profileLoaded = true
      return data
    },

    logout() {
      this.token = ''
      this.username = ''
      this.nickname = ''
      this.role = ''
      this.mustChangePwd = false
      this.profileLoaded = false
      localStorage.removeItem('apr_token')
      localStorage.removeItem('apr_user')
    },
  },
})
