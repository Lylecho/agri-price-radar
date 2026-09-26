package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.entity.OpLog;
import com.agri.priceradar.service.OpLogService;
import com.agri.priceradar.vo.PageResultVO;
import jakarta.validation.constraints.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/oplog")
@Validated
public class OpLogController {
    private final OpLogService service;
    public OpLogController(OpLogService service) { this.service = service; }

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<PageResultVO<OpLog>> page(
            @RequestParam(defaultValue = "1") @Min(1) long page,
            @RequestParam(defaultValue = "10") @Min(1) @Max(100) long size,
            @RequestParam(required = false) @Size(max = 32) String username,
            @RequestParam(required = false) @Pattern(regexp = "|LOGIN|CHANGE_PASSWORD|UPDATE_ALERT_RULE|TRIGGER_COLLECT") String action) {
        return Result.ok(service.page(page, size, username, action));
    }
}
