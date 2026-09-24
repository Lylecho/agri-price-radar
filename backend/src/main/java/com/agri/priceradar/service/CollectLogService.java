package com.agri.priceradar.service;

import com.agri.priceradar.entity.CollectLog;
import com.agri.priceradar.mapper.CollectLogMapper;
import com.agri.priceradar.vo.PageResultVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * 任务日志查询服务（管理端监控定时采集/预计算）
 */
@Service
public class CollectLogService {

    private final CollectLogMapper collectLogMapper;

    public CollectLogService(CollectLogMapper collectLogMapper) {
        this.collectLogMapper = collectLogMapper;
    }

    /** 分页查询任务日志（按开始时间倒序） */
    public PageResultVO<CollectLog> page(long current, long size) {
        Page<CollectLog> page = new Page<>(current, size);
        Page<CollectLog> result = collectLogMapper.selectPage(page,
                new LambdaQueryWrapper<CollectLog>().orderByDesc(CollectLog::getStartedAt));
        return PageResultVO.of(result);
    }

    /**
     * 写入任务日志（Java 侧任务: 手动采集、预警评估）
     * 与 Python 侧 scheduler 写同一张 collect_log, 管理端统一查看
     */
    public void writeLog(String job, String status, String detail, Integer rowsWritten,
                         LocalDateTime startedAt, LocalDateTime finishedAt) {
        CollectLog log = new CollectLog();
        log.setJob(job);
        log.setStatus(status);
        log.setDetail(detail == null ? null : detail.substring(0, Math.min(1000, detail.length())));
        log.setRowsWritten(rowsWritten);
        log.setStartedAt(startedAt);
        log.setFinishedAt(finishedAt);
        collectLogMapper.insert(log);
    }
}
