package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.entity.CollectLog;
import com.agri.priceradar.service.CollectLogService;
import com.agri.priceradar.service.CollectTriggerService;
import com.agri.priceradar.service.PriceService;
import com.agri.priceradar.vo.CategoryStatsVO;
import com.agri.priceradar.vo.PageResultVO;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 管理端采集监控接口（蓝图 §6）
 * 权限: SecurityConfig 限定 /api/admin/** 需 ADMIN 或 DATA_ADMIN
 */
@RestController
@RequestMapping("/api/admin/collect")
@Validated
public class AdminCollectController {

    private final CollectLogService collectLogService;
    private final PriceService priceService;
    private final CollectTriggerService collectTriggerService;

    public AdminCollectController(CollectLogService collectLogService, PriceService priceService,
                                  CollectTriggerService collectTriggerService) {
        this.collectLogService = collectLogService;
        this.priceService = priceService;
        this.collectTriggerService = collectTriggerService;
    }

    /** 任务日志分页 */
    @GetMapping("/logs")
    public Result<PageResultVO<CollectLog>> logs(@RequestParam(defaultValue = "1")
                                                 @Min(value = 1, message = "page 最小为 1") long page,
                                                 @RequestParam(defaultValue = "10")
                                                 @Min(value = 1, message = "size 最小为 1")
                                                 @Max(value = 100, message = "size 最大为 100") long size) {
        return Result.ok(collectLogService.page(page, size));
    }

    /** 单品类数据量与跨度 */
    @GetMapping("/stats")
    public Result<CategoryStatsVO> stats(@RequestParam String category) {
        return Result.ok(priceService.stats(category));
    }

    /**
     * 手动触发一次增量采集（异步子进程; 同一时刻仅允许一个任务）
     * 返回: { accepted: true/false, running: bool, message }
     */
    @PostMapping("/trigger")
    public Result<Map<String, Object>> trigger() {
        boolean accepted = collectTriggerService.trigger();
        if (!accepted) {
            return Result.ok(Map.of(
                    "accepted", false,
                    "running", true,
                    "message", "已有采集任务正在执行, 请稍后查看任务日志"));
        }
        return Result.ok(Map.of(
                "accepted", true,
                "running", true,
                "message", "已提交增量采集任务(回看3天), 请稍后刷新任务日志"));
    }
}
