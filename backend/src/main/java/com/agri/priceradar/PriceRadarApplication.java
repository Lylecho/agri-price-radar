package com.agri.priceradar;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 菜价雷达 · 主后端启动类（W2）
 * 技术栈: SpringBoot 3.3 + MyBatis-Plus + MySQL 8, JDK17
 * 说明: 日常展示只读已入库快照(price_daily / predict_result), 不现场爬取(蓝图铁律)
 */
@SpringBootApplication
@MapperScan("com.agri.priceradar.mapper")
public class PriceRadarApplication {

    public static void main(String[] args) {
        SpringApplication.run(PriceRadarApplication.class, args);
    }
}
