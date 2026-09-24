package com.agri.priceradar.vo;

import lombok.Data;

import java.time.LocalDate;

/**
 * 品类数据量统计（Mapper 直接映射）
 */
@Data
public class CategoryStatsVO {

    private Long cnt;

    private LocalDate minDate;

    private LocalDate maxDate;
}
