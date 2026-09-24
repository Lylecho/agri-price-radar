-- =====================================================================
-- W2.2 · 预警模块 DDL（蓝图 §5.4 预留项落地; 阈值语义: 日环比涨跌幅）
-- 执行: python python/scripts/run_sql.py backend/sql/w22_alert.sql
-- 幂等: CREATE TABLE IF NOT EXISTS + upsert 种子
-- =====================================================================

CREATE TABLE IF NOT EXISTS alert_rule (
    id          BIGINT       PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    category    VARCHAR(32)  NOT NULL COMMENT '展示品类',
    metric      VARCHAR(16)  NOT NULL DEFAULT 'DOD_PCT' COMMENT '指标: DOD_PCT=日环比涨跌幅(%)',
    threshold   DECIMAL(6,3) NOT NULL COMMENT '阈值(绝对值, %)',
    enabled     TINYINT      NOT NULL DEFAULT 1 COMMENT '1启用/0停用',
    remark      VARCHAR(128) NULL COMMENT '备注',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_rule (category, metric)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='波动预警规则';

CREATE TABLE IF NOT EXISTS alert_record (
    id            BIGINT        PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    category      VARCHAR(32)   NOT NULL COMMENT '展示品类',
    metric        VARCHAR(16)   NOT NULL COMMENT '指标',
    trade_date    DATE          NOT NULL COMMENT '触发交易日',
    prev_date     DATE          NULL     COMMENT '对比基准日',
    latest_price  DECIMAL(10,3) NULL     COMMENT '当日均价',
    prev_price    DECIMAL(10,3) NULL     COMMENT '基准日均价',
    change_pct    DECIMAL(6,3)  NULL     COMMENT '实际涨跌幅(%)',
    threshold     DECIMAL(6,3)  NULL     COMMENT '触发时阈值(%)',
    message       VARCHAR(255)  NULL     COMMENT '提示文案',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 同一品类同指标同交易日只保留一条(任务重跑幂等)
    UNIQUE KEY uk_record (category, metric, trade_date),
    INDEX idx_record_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='波动预警记录';

-- 默认规则: 日环比绝对涨跌幅 ≥ 5% 触发（用户可在管理端调整）
INSERT INTO alert_rule (category, metric, threshold, enabled, remark) VALUES
    ('大白菜', 'DOD_PCT', 5.000, 1, '默认阈值 5%'),
    ('黄瓜',   'DOD_PCT', 5.000, 1, '默认阈值 5%'),
    ('西红柿', 'DOD_PCT', 5.000, 1, '默认阈值 5%'),
    ('猪肉',   'DOD_PCT', 5.000, 1, '默认阈值 5%'),
    ('鸡蛋',   'DOD_PCT', 5.000, 1, '默认阈值 5%')
ON DUPLICATE KEY UPDATE threshold = VALUES(threshold);
