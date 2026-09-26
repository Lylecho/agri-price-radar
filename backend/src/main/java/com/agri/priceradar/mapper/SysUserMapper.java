package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.SysUser;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 系统用户 Mapper（登录与角色查询; 全部 #{} 参数化）
 */
@Mapper
public interface SysUserMapper extends BaseMapper<SysUser> {

    /** 按登录名取启用状态的用户 */
    @Select("SELECT * FROM sys_user WHERE username = #{username} AND status = 1")
    SysUser selectByUsername(@Param("username") String username);

    /** 用户拥有的角色码列表（如 ADMIN / DATA_ADMIN） */
    @Select("SELECT r.code FROM sys_role r " +
            "JOIN sys_user_role ur ON ur.role_id = r.id " +
            "WHERE ur.user_id = #{userId}")
    List<String> selectRoleCodes(@Param("userId") Long userId);

    /** 并发安全地更新密码和首次改密标记 */
    @Update("UPDATE sys_user SET password = #{newHash}, must_change_pwd = 0 " +
            "WHERE id = #{userId} AND password = #{oldHash} AND status = 1")
    int updatePassword(@Param("userId") Long userId, @Param("oldHash") String oldHash,
                       @Param("newHash") String newHash);
}
