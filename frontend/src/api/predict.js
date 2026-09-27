import request from './request'

/**
 * 未来7天预测: { category, prodName, model, mapeTest, points:[{date,yhat}], disclaimer }
 * 注意: 展示时必须附带 disclaimer（蓝图铁律）
 */
export function fetchPredict(category) {
  return request.get('/api/predict/latest', { params: { category }, emptyPredictionOn404: true })
}

export function fetchRealtimePredict(category, days = 7) {
  return request.get('/api/predict/realtime', { params: { category, days } })
}
