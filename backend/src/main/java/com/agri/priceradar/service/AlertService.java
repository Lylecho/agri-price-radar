package com.agri.priceradar.service;

import com.agri.priceradar.aspect.Audited;
import com.agri.priceradar.aspect.AuditAction;

import com.agri.priceradar.common.BizException;
import com.agri.priceradar.common.CategoryCatalog;
import com.agri.priceradar.common.ResultCode;
import com.agri.priceradar.dto.AlertRuleUpdateRequest;
import com.agri.priceradar.entity.AlertRecord;
import com.agri.priceradar.entity.AlertRule;
import com.agri.priceradar.mapper.AlertRecordMapper;
import com.agri.priceradar.mapper.AlertRuleMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.agri.priceradar.vo.PageResultVO;
import com.agri.priceradar.vo.ChangeVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

/**
 * 预警服务 —— 阈值语义: 日环比涨跌幅的绝对值 ≥ 阈值(单位 %)
 *
 * 说明: 预警基于已入库快照计算(与 /api/price/change 同口径), 故结论与前端所见一致;
 *       记录表 (category, metric, trade_date) 唯一, 任务重跑不会重复告警。
 */
@Service
public class AlertService {

    private static final Logger log = LoggerFactory.getLogger(AlertService.class);
    private static final String METRIC_DOD_PCT = "DOD_PCT";

    private final AlertRuleMapper ruleMapper;
    private final AlertRecordMapper recordMapper;
    private final PriceService priceService;

    public AlertService(AlertRuleMapper ruleMapper, AlertRecordMapper recordMapper,
                        PriceService priceService) {
        this.ruleMapper = ruleMapper;
        this.recordMapper = recordMapper;
        this.priceService = priceService;
    }

    /** 全部规则（按品类顺序） */
    public List<AlertRule> listRules() {
        List<AlertRule> rules = ruleMapper.selectList(
                new LambdaQueryWrapper<AlertRule>().orderByAsc(AlertRule::getId));
        rules.sort((a, b) -> Integer.compare(categoryOrder(a.getCategory()), categoryOrder(b.getCategory())));
        return rules;
    }

    /** 更新阈值/启用状态（管理端, 仅 ADMIN 可调用） */
    @Audited(AuditAction.UPDATE_ALERT_RULE)
    public AlertRule updateRule(Long id, AlertRuleUpdateRequest request) {
        AlertRule rule = ruleMapper.selectById(id);
        if (rule == null) {
            throw new BizException(ResultCode.NOT_FOUND, "预警规则不存在: id=" + id);
        }
        rule.setThreshold(request.threshold());
        rule.setEnabled(request.enabled());
        rule.setRemark(request.remark());
        ruleMapper.updateById(rule);
        log.info("预警规则已更新: category={}, threshold={}%, enabled={}",
                rule.getCategory(), rule.getThreshold(), rule.getEnabled());
        return rule;
    }

    /** 预警记录分页（按交易日倒序） */
    public PageResultVO<AlertRecord> pageRecords(long current, long size) {
        Page<AlertRecord> page = new Page<>(current, size);
        Page<AlertRecord> result = recordMapper.selectPage(page,
                new LambdaQueryWrapper<AlertRecord>()
                        .orderByDesc(AlertRecord::getTradeDate)
                        .orderByAsc(AlertRecord::getCategory));
        return PageResultVO.of(result);
    }

    /** 按品类统计触发次数（前端概览用） */
    public List<java.util.Map<String, Object>> countByCategory() {
        List<java.util.Map<String, Object>> list = new ArrayList<>();
        for (String category : CategoryCatalog.all().keySet()) {
            Long cnt = recordMapper.selectCount(
                    new LambdaQueryWrapper<AlertRecord>().eq(AlertRecord::getCategory, category));
            list.add(java.util.Map.of("category", category, "count", cnt));
        }
        return list;
    }

    /**
     * 评估全部启用规则并写入预警记录（由定时任务调用）
     *
     * @return 本次新增/更新的预警条数
     */
    public int evaluateAll() {
        List<AlertRule> rules = ruleMapper.selectList(
                new LambdaQueryWrapper<AlertRule>().eq(AlertRule::getEnabled, 1));
        int written = 0;
        for (AlertRule rule : rules) {
            try {
                if (evaluateOne(rule)) {
                    written++;
                }
            } catch (BizException e) {
                // 某品类数据不足不阻塞其他品类
                log.warn("预警评估跳过 {}({}): {}", rule.getCategory(), rule.getMetric(), e.getMessage());
            }
        }
        log.info("预警评估完成: 规则 {} 条, 触发 {} 条", rules.size(), written);
        return written;
    }

    /** 单条规则评估; 触发返回 true */
    private boolean evaluateOne(AlertRule rule) {
        if (!METRIC_DOD_PCT.equals(rule.getMetric())) {
            return false;
        }
        ChangeVO change = priceService.change(rule.getCategory());   // 复用日环比口径
        if (change.changePct() == null) {
            return false;
        }
        BigDecimal absPct = change.changePct().abs();
        if (absPct.compareTo(rule.getThreshold()) < 0) {
            return false;
        }
        AlertRecord record = new AlertRecord();
        record.setCategory(rule.getCategory());
        record.setMetric(rule.getMetric());
        record.setTradeDate(java.time.LocalDate.parse(change.latestDate()));
        record.setPrevDate(java.time.LocalDate.parse(change.prevDate()));
        record.setLatestPrice(change.latestPrice());
        record.setPrevPrice(change.prevPrice());
        record.setChangePct(change.changePct().setScale(3, RoundingMode.HALF_UP));
        record.setThreshold(rule.getThreshold());
        record.setMessage(String.format("%s 日环比 %s%%（阈值 %s%%）",
                rule.getCategory(), change.changePct().setScale(2, RoundingMode.HALF_UP), rule.getThreshold()));
        try {
            recordMapper.insert(record);
        } catch (DuplicateKeyException e) {
            // 同一交易日已告警过: 更新为最新数值(任务重跑幂等)
            AlertRecord exist = recordMapper.selectOne(new LambdaQueryWrapper<AlertRecord>()
                    .eq(AlertRecord::getCategory, record.getCategory())
                    .eq(AlertRecord::getMetric, record.getMetric())
                    .eq(AlertRecord::getTradeDate, record.getTradeDate()));
            if (exist != null) {
                record.setId(exist.getId());
                recordMapper.updateById(record);
            }
        }
        log.info("触发预警: {}", record.getMessage());
        return true;
    }

    private int categoryOrder(String category) {
        int i = 0;
        for (String c : CategoryCatalog.all().keySet()) {
            if (c.equals(category)) {
                return i;
            }
            i++;
        }
        return Integer.MAX_VALUE;
    }
}
