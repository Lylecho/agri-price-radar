package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 系统用户（W2 新增, 蓝图 §5.4 RBAC）
 * 密码以 BCrypt 摘要存储; 预置 admin(ADMIN) / dataadmin(DATA_ADMIN)
 */
@Data
@TableName("sys_user")
public class SysUser {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String username;

    /** BCrypt 摘要 */
    private String password;

    private String nickname;

    /** 1 启用 / 0 禁用 */
    private Integer status;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
