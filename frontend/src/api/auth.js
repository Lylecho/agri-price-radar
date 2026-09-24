import request from './request'

/** 登录: 返回 { token, username, nickname, role, expireSeconds } */
export function login(data) {
  return request.post('/api/auth/login', data)
}

/** 当前登录用户（刷新页面时校验登录态） */
export function fetchMe() {
  return request.get('/api/auth/me')
}
