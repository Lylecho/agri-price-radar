package com.agri.priceradar.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 趋势点（Mapper 直接映射, 故用可变类而非 record）
 */
@Data
public class TrendPointVO {

    /** 交易日 */
    private LocalDate tradeDate;

    /** 当日均价（元/主导单位） */
    private BigDecimal avgPrice;
}
