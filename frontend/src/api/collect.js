import request from './request'

/** 任务日志分页: { total, pages, current, size, records } */
export function fetchCollectLogs(page = 1, size = 10) {
  return request.get('/api/admin/collect/logs', { params: { page, size } })
}

/** 单品类数据量与跨度: { cnt, minDate, maxDate } */
export function fetchCategoryStats(category) {
  return request.get('/api/admin/collect/stats', { params: { category } })
}

/** 手动触发一次增量采集（模块 D） */
export function triggerCollect() {
  return request.post('/api/admin/collect/trigger')
}
