package com.agri.priceradar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

/** 操作审计，仅保存白名单摘要。 */
@Data
@TableName("op_log")
public class OpLog {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private String username;
    private String action;
    private String target;
    private String result;
    private String detail;
    private String ip;
    private LocalDateTime createdAt;
}
