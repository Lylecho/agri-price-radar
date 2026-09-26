package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.OpLog;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/** 使用 MyBatis-Plus 参数绑定，不拼接筛选条件。 */
@Mapper
public interface OpLogMapper extends BaseMapper<OpLog> {
}
