package com.agri.priceradar.service;

import com.agri.priceradar.entity.CollectLog;
import com.agri.priceradar.mapper.CollectLogMapper;
import com.agri.priceradar.vo.PageResultVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.stereotype.Service;

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
}
