package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.AlertRule;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 预警规则 Mapper（CRUD 由 MyBatis-Plus 提供）
 */
@Mapper
public interface AlertRuleMapper extends BaseMapper<AlertRule> {
}
