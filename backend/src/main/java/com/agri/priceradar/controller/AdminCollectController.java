package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.entity.CollectLog;
import com.agri.priceradar.service.CollectLogService;
import com.agri.priceradar.service.PriceService;
import com.agri.priceradar.vo.CategoryStatsVO;
import com.agri.priceradar.vo.PageResultVO;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端采集监控接口（蓝图 §6）
 *
 * ⚠️ W2.1 尚未接入鉴权: 本组接口在 W2.2 将强制校验 DATA_ADMIN / ADMIN 角色
 *    （蓝图 §3 RBAC; AGENTS.md 铁律 8: 接口层强制校验）。当前仅绑定本机开发环境使用。
 */
@RestController
@RequestMapping("/api/admin/collect")
@Validated
public class AdminCollectController {

    private final CollectLogService collectLogService;
    private final PriceService priceService;

    public AdminCollectController(CollectLogService collectLogService, PriceService priceService) {
        this.collectLogService = collectLogService;
        this.priceService = priceService;
    }

    /** 任务日志分页（W2.2 起需 DATA_ADMIN+） */
    @GetMapping("/logs")
    public Result<PageResultVO<CollectLog>> logs(@RequestParam(defaultValue = "1")
                                                 @Min(value = 1, message = "page 最小为 1") long page,
                                                 @RequestParam(defaultValue = "10")
                                                 @Min(value = 1, message = "size 最小为 1")
                                                 @Max(value = 100, message = "size 最大为 100") long size) {
        return Result.ok(collectLogService.page(page, size));
    }

    /** 单品类数据量与跨度（W2.2 起需 DATA_ADMIN+） */
    @GetMapping("/stats")
    public Result<CategoryStatsVO> stats(@RequestParam String category) {
        return Result.ok(priceService.stats(category));
    }
}
