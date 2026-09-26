package com.agri.priceradar.vo;

import lombok.Data;

import java.time.LocalDate;

/**
 * 品类数据量统计（Mapper 直接映射）
 */
@Data
public class CategoryStatsVO {

    private Long cnt;

    /** 非斤单位及缺失单位的明细数，仅供复核，不改变既有数据。 */
    private Long nonStandardUnitCount;

    /** 按蓝图已定义规则检查散鸡蛋斤价大于15的疑似错标。 */
    private Long suspectPriceCount;

    private LocalDate minDate;

    private LocalDate maxDate;
}
