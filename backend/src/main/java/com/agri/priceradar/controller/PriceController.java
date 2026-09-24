package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.service.PriceService;
import com.agri.priceradar.vo.CategoryVO;
import com.agri.priceradar.vo.ChangeVO;
import com.agri.priceradar.vo.TrendPointVO;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 价格查询接口（蓝图 §6; 只读, 日常展示通道）
 */
@RestController
@RequestMapping("/api/price")
@Validated
public class PriceController {

    private final PriceService priceService;

    public PriceController(PriceService priceService) {
        this.priceService = priceService;
    }

    /** 五品类概览: 代表品名/单位/最新价 */
    @GetMapping("/categories")
    public Result<List<CategoryVO>> categories() {
        return Result.ok(priceService.listCategories());
    }

    /** 日度均价趋势（days: 90=近90天, 1095≈近3年） */
    @GetMapping("/trend")
    public Result<List<TrendPointVO>> trend(@RequestParam String category,
                                            @RequestParam(defaultValue = "90")
                                            @Min(value = 1, message = "days 最小为 1")
                                            @Max(value = 1095, message = "days 最大为 1095") int days) {
        return Result.ok(priceService.trend(category, days));
    }

    /** 最新日环比（红涨绿跌） */
    @GetMapping("/change")
    public Result<ChangeVO> change(@RequestParam String category) {
        return Result.ok(priceService.change(category));
    }
}
