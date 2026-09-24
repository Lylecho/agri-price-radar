package com.agri.priceradar.service;

import com.agri.priceradar.common.BizException;
import com.agri.priceradar.common.CategoryCatalog;
import com.agri.priceradar.common.ResultCode;
import com.agri.priceradar.entity.PredictResult;
import com.agri.priceradar.mapper.PredictResultMapper;
import com.agri.priceradar.vo.PredictPointVO;
import com.agri.priceradar.vo.PredictVO;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

/**
 * 预测查询服务 —— 只读 predict_result 预计算表（蓝图 §7 双通道之日常通道）
 * 返回值必然携带模型标识、测试集 MAPE 与免责声明
 */
@Service
public class PredictService {

    private final PredictResultMapper predictMapper;

    public PredictService(PredictResultMapper predictMapper) {
        this.predictMapper = predictMapper;
    }

    public PredictVO latest(String category) {
        String prodName = CategoryCatalog.prodNameOf(category);
        if (prodName == null) {
            throw new BizException(ResultCode.PARAM_ERROR, "未知品类: " + category);
        }
        String model = predictMapper.selectLatestModel(category);
        if (model == null) {
            throw new BizException(ResultCode.NOT_FOUND, category + " 暂无预测数据, 请等待预计算任务运行");
        }
        List<PredictResult> rows = predictMapper.selectByCategoryAndModel(category, model);
        List<PredictPointVO> points = rows.stream()
                .map(r -> new PredictPointVO(r.getPredictDate().toString(), r.getYhat()))
                .toList();
        BigDecimal mapeTest = rows.isEmpty() ? null : rows.get(0).getMapeTest();
        return new PredictVO(category, prodName, model, mapeTest, points, PredictVO.DISCLAIMER);
    }
}
