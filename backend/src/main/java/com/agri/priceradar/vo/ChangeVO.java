package com.agri.priceradar.vo;

import java.math.BigDecimal;

/**
 * 环比涨跌（最新交易日 vs 前一交易日; 前端按红涨绿跌渲染）
 *
 * @param changePct 涨跌幅（%）, 正=涨
 */
public record ChangeVO(String category, String latestDate, String prevDate,
                       BigDecimal latestPrice, BigDecimal prevPrice, BigDecimal changePct) {
}
