package com.agri.priceradar.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * 预警评估定时任务（Java 侧）
 *
 * 分工说明: Python 调度进程负责「采集 + 预测预计算」(数据生产),
 *           Java 侧负责「预警评估」(业务判定, 复用价格服务口径), 结果统一写 collect_log。
 * 默认 21:30 执行(在 21:00 预计算之后), 可通过 apr.alert.cron 覆盖。
 */
@Component
public class AlertScheduleJob {

    private static final Logger log = LoggerFactory.getLogger(AlertScheduleJob.class);
    private static final String JOB = "alert";

    private final AlertService alertService;
    private final CollectLogService collectLogService;

    public AlertScheduleJob(AlertService alertService, CollectLogService collectLogService) {
        this.alertService = alertService;
        this.collectLogService = collectLogService;
    }

    @Scheduled(cron = "${apr.alert.cron:0 30 21 * * ?}")
    public void run() {
        LocalDateTime started = LocalDateTime.now();
        try {
            int triggered = alertService.evaluateAll();
            LocalDateTime ended = LocalDateTime.now();
            collectLogService.writeLog(JOB, "SUCCESS",
                    "预警评估完成, 触发 " + triggered + " 条", triggered, started, ended);
            log.info("预警定时任务完成: 触发 {} 条", triggered);
        } catch (Exception e) {
            LocalDateTime ended = LocalDateTime.now();
            collectLogService.writeLog(JOB, "FAILED",
                    "预警评估异常: " + e.getMessage(), null, started, ended);
            log.error("预警定时任务失败", e);
        }
    }
}
