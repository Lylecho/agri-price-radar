package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 波动预警记录（同一品类+指标+交易日唯一, 任务重跑幂等）
 */
@Data
@TableName("alert_record")
public class AlertRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String category;

    private String metric;

    /** 触发交易日 */
    private LocalDate tradeDate;

    /** 对比基准日 */
    private LocalDate prevDate;

    private BigDecimal latestPrice;

    private BigDecimal prevPrice;

    /** 实际涨跌幅(%) */
    private BigDecimal changePct;

    /** 触发阈值(%) */
    private BigDecimal threshold;

    private String message;

    private LocalDateTime createdAt;
}
