package com.agri.priceradar.service;

import com.agri.priceradar.common.BizException;
import com.agri.priceradar.common.CategoryCatalog;
import com.agri.priceradar.common.ResultCode;
import com.agri.priceradar.entity.PredictResult;
import com.agri.priceradar.mapper.PredictResultMapper;
import com.agri.priceradar.vo.PredictPointVO;
import com.agri.priceradar.vo.PredictVO;
import com.agri.priceradar.vo.RealtimePredictVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Comparator;

/**
 * 预测查询服务 —— 只读 predict_result 预计算表（蓝图 §7 双通道之日常通道）
 * 返回值必然携带模型标识、测试集 MAPE 与免责声明
 */
@Service
public class PredictService {

    private final PredictResultMapper predictMapper;
    private final MlForecastClient mlClient;
    private static final Logger log = LoggerFactory.getLogger(PredictService.class);

    public PredictService(PredictResultMapper predictMapper, MlForecastClient mlClient) {
        this.predictMapper = predictMapper;
        this.mlClient = mlClient;
    }

    /** 算法选择由Python共用R2实现；Java只代理、校验协议并回退参数化只读查询。 */
    public RealtimePredictVO realtime(String category, int days) {
        if (!CategoryCatalog.isValid(category) || days < 1 || days > 7)
            throw new BizException(ResultCode.PARAM_ERROR, "category须为有效品类，days须为1至7");
        try {
            return mlClient.forecast(category, days);
        } catch (Exception e) {
            if (e instanceof InterruptedException) Thread.currentThread().interrupt();
            log.warn("实时算法通道降级: {}", e.getClass().getSimpleName());
        }
        try {
            var saved = latest(category);
            var points = saved.mapeTest() != null && saved.mapeTest().signum() >= 0
                    && saved.mapeTest().doubleValue() <= 30 ? saved.points().stream().limit(days).toList()
                    : List.<PredictPointVO>of();
            return new RealtimePredictVO(category, saved.prodName(), saved.model(), saved.mapeTest(), points,
                    RealtimePredictVO.DISCLAIMER, true, "PRECOMPUTED", !points.isEmpty(),
                    "实时通道不可用，已回退预计算结果");
        } catch (Exception e) {
            // 没有预计算（如MAPE未准入）或查询失败时，也返回可展示的空结果，不抛500。
            log.warn("实时降级无可用预计算: {}", e.getClass().getSimpleName());
            return new RealtimePredictVO(category, CategoryCatalog.prodNameOf(category), null, null, List.of(),
                    RealtimePredictVO.DISCLAIMER, true, "PRECOMPUTED", false,
                    "实时通道不可用，已回退预计算结果；暂无可用预测（仅供参考）");
        }
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
                .sorted(Comparator.comparing(PredictResult::getPredictDate))
                .map(r -> new PredictPointVO(r.getPredictDate().toString(), r.getYhat()))
                .toList();
        BigDecimal mapeTest = rows.isEmpty() ? null : rows.get(0).getMapeTest();
        return new PredictVO(category, prodName, model, mapeTest, points, PredictVO.DISCLAIMER);
    }
}
