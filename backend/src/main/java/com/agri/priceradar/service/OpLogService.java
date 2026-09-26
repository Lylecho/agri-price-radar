package com.agri.priceradar.service;

import com.agri.priceradar.entity.OpLog;
import com.agri.priceradar.mapper.OpLogMapper;
import com.agri.priceradar.vo.PageResultVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.time.ZoneId;

@Service
public class OpLogService {
    private static final Logger log = LoggerFactory.getLogger(OpLogService.class);
    private final OpLogMapper mapper;

    public OpLogService(OpLogMapper mapper) { this.mapper = mapper; }

    /** 审计失败必须与主业务隔离，异常日志也不能输出待写入的请求数据。 */
    public void writeSafely(OpLog entry) {
        try {
            entry.setUsername(truncate(entry.getUsername() == null ? "匿名" : entry.getUsername(), 32));
            entry.setTarget(truncate(entry.getTarget(), 128));
            entry.setDetail(truncate(entry.getDetail(), 1000));
            entry.setIp(truncate(entry.getIp(), 45));
            entry.setCreatedAt(LocalDateTime.now(ZoneId.of("Asia/Shanghai")));
            mapper.insert(entry);
        } catch (Exception e) {
            log.warn("操作审计写入失败，主业务结果保留: {}", e.getClass().getSimpleName());
        }
    }

    /** 按 Unicode 码点截断，避免截断代理对；与 MySQL utf8mb4 字符数一致。 */
    static String truncate(String value, int length) {
        if (value == null || value.codePointCount(0, value.length()) <= length) return value;
        return value.substring(0, value.offsetByCodePoints(0, length));
    }

    public PageResultVO<OpLog> page(long page, long size, String username, String action) {
        var query = new LambdaQueryWrapper<OpLog>()
                .eq(username != null && !username.isBlank(), OpLog::getUsername, username)
                .eq(action != null && !action.isBlank(), OpLog::getAction, action)
                .orderByDesc(OpLog::getCreatedAt).orderByDesc(OpLog::getId);
        return PageResultVO.of(mapper.selectPage(new Page<>(page, size), query));
    }
}
