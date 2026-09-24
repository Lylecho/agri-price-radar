import request from './request'

/** 五品类概览: [{ category, prodName, unit, latestDate, latestPrice }] */
export function fetchCategories() {
  return request.get('/api/price/categories')
}

/** 日度均价序列: [{ tradeDate, avgPrice }] */
export function fetchTrend(category, days = 90) {
  return request.get('/api/price/trend', { params: { category, days } })
}

/** 最新日环比: { category, latestDate, prevDate, latestPrice, prevPrice, changePct } */
export function fetchChange(category) {
  return request.get('/api/price/change', { params: { category } })
}
