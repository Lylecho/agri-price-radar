package com.agri.priceradar;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 菜价雷达 · 主后端启动类（W2）
 * 技术栈: SpringBoot 3.3 + MyBatis-Plus + MySQL 8, JDK17
 * 说明: 日常展示只读已入库快照(price_daily / predict_result), 不现场爬取(蓝图铁律)
 *       @EnableScheduling: 承载预警评估定时任务(采集/预计算由 Python 调度进程负责)
 */
@SpringBootApplication
@EnableScheduling
@MapperScan("com.agri.priceradar.mapper")
public class PriceRadarApplication {

    public static void main(String[] args) {
        SpringApplication.run(PriceRadarApplication.class, args);
    }
}
