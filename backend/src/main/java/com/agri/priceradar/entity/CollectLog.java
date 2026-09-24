package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 采集/预计算任务日志（对应 collect_log 表）—— 数据管理员据此监控定时任务
 */
@Data
@TableName("collect_log")
public class CollectLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 任务名: collect / precompute */
    private String job;

    /** SUCCESS / FAILED */
    private String status;

    /** 摘要 */
    private String detail;

    private Integer rowsWritten;

    private LocalDateTime startedAt;

    private LocalDateTime finishedAt;
}
