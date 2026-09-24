package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 预测预计算结果（对应 predict_result 表）
 * 日常展示只读此表（蓝图 §7 双通道铁律）; 由 Python 端 ml/precompute.py 定时写入
 */
@Data
@TableName("predict_result")
public class PredictResult {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 展示品类（大白菜/黄瓜/西红柿/猪肉/鸡蛋） */
    private String category;

    /** 代表品名 */
    private String prodName;

    /** 预测目标日 */
    private LocalDate predictDate;

    /** 预测均价（元/斤） */
    private BigDecimal yhat;

    /** 模型标识, 如 ARIMA(2,1,1) */
    private String model;

    /** 测试集 MAPE(%) */
    private BigDecimal mapeTest;

    /** 距最后实测日天数 1-7 */
    private Integer horizon;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
