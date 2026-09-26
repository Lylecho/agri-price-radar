-- =====================================================================
-- W3 · 操作审计：登录、改密、预警规则修改、手动采集受理结果
-- 执行：python python/scripts/run_sql.py backend/sql/w3_oplog.sql
-- 幂等：CREATE TABLE IF NOT EXISTS，可重复执行，不修改已有审计数据。
-- =====================================================================
CREATE TABLE IF NOT EXISTS op_log (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    user_id     BIGINT        NULL COMMENT '操作人ID，未认证时为空',
    username    VARCHAR(32)   NOT NULL COMMENT '操作人或登录时提交的用户名',
    action      VARCHAR(32)   NOT NULL COMMENT 'LOGIN/CHANGE_PASSWORD/UPDATE_ALERT_RULE/TRIGGER_COLLECT',
    target      VARCHAR(128)  NULL COMMENT '目标账号、规则ID或采集任务',
    result      VARCHAR(16)   NOT NULL COMMENT 'SUCCESS/FAILED',
    detail      VARCHAR(1000) NULL COMMENT '安全摘要，不含密码、令牌或完整请求体',
    ip          VARCHAR(45)   NULL COMMENT '请求来源IPv4或IPv6',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username_time (username, created_at),
    INDEX idx_action_time (action, created_at),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统操作审计日志';
