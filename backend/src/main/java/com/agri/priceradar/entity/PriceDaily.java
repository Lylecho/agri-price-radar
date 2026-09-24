package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 采集明细（对应 MySQL 表 price_daily, DDL v2）
 * 唯一键: (prod_name, pub_date, place, spec_info, unit_info)
 */
@Data
@TableName("price_daily")
public class PriceDaily {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 品名（接口原值, 如 白条猪/散鸡蛋） */
    private String prodName;

    /** 品类（接口原值） */
    private String prodCat;

    private BigDecimal lowPrice;

    private BigDecimal highPrice;

    private BigDecimal avgPrice;

    /** 产地 */
    private String place;

    /** 规格 */
    private String specInfo;

    /** 计价单位: 斤/箱/筐/个（v2 起纳入唯一键, 防异单位互相覆盖） */
    private String unitInfo;

    /** 发布日期 */
    private LocalDate pubDate;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
