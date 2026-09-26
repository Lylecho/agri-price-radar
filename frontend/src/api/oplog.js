import request from './request'

export function fetchOpLogs(params) {
  return request.get('/api/admin/oplog', { params })
}
