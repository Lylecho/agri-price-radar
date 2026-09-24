package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 波动预警规则（阈值语义: 日环比涨跌幅的绝对值, 单位 %）
 */
@Data
@TableName("alert_rule")
public class AlertRule {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 展示品类 */
    private String category;

    /** 指标: DOD_PCT = 日环比涨跌幅(%) */
    private String metric;

    /** 阈值(绝对值, %) */
    private BigDecimal threshold;

    /** 1启用 / 0停用 */
    private Integer enabled;

    private String remark;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
