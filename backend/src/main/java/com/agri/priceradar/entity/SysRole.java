package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 角色（W2 新增）—— 双角色: ADMIN 超级管理员 / DATA_ADMIN 数据管理员
 */
@Data
@TableName("sys_role")
public class SysRole {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 角色码: ADMIN / DATA_ADMIN */
    private String code;

    private String name;

    private String remark;
}
