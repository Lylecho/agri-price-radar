package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.service.PredictService;
import com.agri.priceradar.vo.PredictVO;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 预测查询接口（蓝图 §6; 只读 predict_result 预计算表）
 * 返回体携带 model / mapeTest / disclaimer（铁律: 预测展示必须带免责声明）
 */
@RestController
@RequestMapping("/api/predict")
public class PredictController {

    private final PredictService predictService;

    public PredictController(PredictService predictService) {
        this.predictService = predictService;
    }

    /** 某品类未来 7 天预测（含模型、测试集 MAPE 与免责声明） */
    @GetMapping("/latest")
    public Result<PredictVO> latest(@RequestParam String category) {
        return Result.ok(predictService.latest(category));
    }
}
