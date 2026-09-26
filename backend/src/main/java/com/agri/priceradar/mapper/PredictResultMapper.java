package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.PredictResult;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 预测预计算 Mapper（只读; 写入由 Python 端 ml/precompute.py 完成）
 */
@Mapper
public interface PredictResultMapper extends BaseMapper<PredictResult> {

    /** 该品类最近一次预计算使用的模型（用于取最新一批预测） */
    @Select("SELECT model FROM predict_result WHERE category = #{category} " +
            "ORDER BY updated_at DESC, id DESC LIMIT 1")
    String selectLatestModel(@Param("category") String category);

    /** 指定品类+模型的预测序列 */
    @Select("SELECT * FROM predict_result WHERE category = #{category} AND model = #{model} " +
            "ORDER BY predict_date DESC LIMIT 7")
    List<PredictResult> selectByCategoryAndModel(@Param("category") String category,
                                                 @Param("model") String model);
}
