package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.AlertRecord;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 预警记录 Mapper（分页查询由 MyBatis-Plus Page + 分页插件完成）
 */
@Mapper
public interface AlertRecordMapper extends BaseMapper<AlertRecord> {
}
