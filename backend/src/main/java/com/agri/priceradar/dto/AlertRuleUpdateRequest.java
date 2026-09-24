package com.agri.priceradar.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/**
 * 预警规则更新请求（阈值语义: 日环比涨跌幅绝对值, 单位 %）
 */
public record AlertRuleUpdateRequest(
        @NotNull(message = "阈值不能为空")
        @DecimalMin(value = "0.01", message = "阈值需大于 0")
        @DecimalMax(value = "100.0", message = "阈值需小于等于 100")
        BigDecimal threshold,

        @NotNull(message = "启用状态不能为空")
        Integer enabled,

        String remark) {
}
