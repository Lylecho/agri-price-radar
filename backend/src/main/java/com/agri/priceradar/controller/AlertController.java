package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.dto.AlertRuleUpdateRequest;
import com.agri.priceradar.entity.AlertRecord;
import com.agri.priceradar.entity.AlertRule;
import com.agri.priceradar.service.AlertService;
import com.agri.priceradar.vo.PageResultVO;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 波动预警接口（蓝图 §6 扩展; 阈值语义 = 日环比涨跌幅绝对值）
 * 权限: 查询需登录; 规则修改仅 ADMIN（SecurityConfig 已限定 /api/admin/**, 此处用方法级校验细化）
 */
@RestController
@RequestMapping("/api/alert")
@Validated
public class AlertController {

    private final AlertService alertService;

    public AlertController(AlertService alertService) {
        this.alertService = alertService;
    }

    /** 预警规则列表（登录即可见） */
    @GetMapping("/rules")
    public Result<List<AlertRule>> rules() {
        return Result.ok(alertService.listRules());
    }

    /** 修改阈值/启用状态 —— 仅超级管理员 */
    @PutMapping("/rules/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<AlertRule> updateRule(@PathVariable Long id,
                                        @Valid @RequestBody AlertRuleUpdateRequest request) {
        return Result.ok(alertService.updateRule(id, request));
    }

    /** 预警记录分页 */
    @GetMapping("/records")
    public Result<PageResultVO<AlertRecord>> records(@RequestParam(defaultValue = "1")
                                                     @Min(value = 1, message = "page 最小为 1") long page,
                                                     @RequestParam(defaultValue = "10")
                                                     @Min(value = 1, message = "size 最小为 1")
                                                     @Max(value = 100, message = "size 最大为 100") long size) {
        return Result.ok(alertService.pageRecords(page, size));
    }

    /** 各品类触发次数概览 */
    @GetMapping("/summary")
    public Result<List<Map<String, Object>>> summary() {
        return Result.ok(alertService.countByCategory());
    }

    /**
     * 立即执行一次预警评估（仅 ADMIN; 定时任务默认 21:30 自动执行）
     * 返回: { triggered: 触发条数 }
     */
    @PostMapping("/evaluate")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Map<String, Object>> evaluate() {
        int triggered = alertService.evaluateAll();
        return Result.ok(Map.of("triggered", triggered,
                "message", "预警评估完成, 触发 " + triggered + " 条"));
    }
}
