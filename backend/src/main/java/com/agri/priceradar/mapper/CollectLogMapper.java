package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.CollectLog;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 任务日志 Mapper（分页查询由 MyBatis-Plus Page + 分页插件完成）
 */
@Mapper
public interface CollectLogMapper extends BaseMapper<CollectLog> {
}
