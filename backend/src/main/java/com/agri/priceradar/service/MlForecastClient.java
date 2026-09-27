package com.agri.priceradar.service;

import com.agri.priceradar.common.CategoryCatalog;
import com.agri.priceradar.vo.PredictPointVO;
import com.agri.priceradar.vo.RealtimePredictVO;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/** JDK17客户端：对连接、响应头和完整响应体设置统一截止时间，不重试。 */
@Component
public class MlForecastClient {
    private final HttpClient http;
    private final ObjectMapper json;
    private final String baseUrl;
    private final long timeoutMs;

    public MlForecastClient(ObjectMapper json,
            @Value("${apr.ml.base-url:http://127.0.0.1:8001}") String baseUrl,
            @Value("${apr.ml.timeout-ms:2800}") long timeoutMs) {
        this.json = json;
        this.baseUrl = baseUrl;
        this.timeoutMs = Math.max(1, Math.min(3000, timeoutMs));
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(Math.min(500, this.timeoutMs)))
                .followRedirects(HttpClient.Redirect.NEVER).build();
    }

    public RealtimePredictVO forecast(String category, int days) throws Exception {
        var request = HttpRequest.newBuilder(URI.create(baseUrl.replaceAll("/+$", "") + "/ml/forecast"))
                .timeout(Duration.ofMillis(timeoutMs)).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(Map.of("category", category, "days", days))))
                .build();
        var future = http.sendAsync(request, HttpResponse.BodyHandlers.ofString());
        HttpResponse<String> response;
        try {
            response = future.get(timeoutMs, TimeUnit.MILLISECONDS);
        } finally {
            if (!future.isDone()) future.cancel(true);
        }
        if (response.statusCode() != 200) throw new IllegalStateException("算法HTTP异常");
        var root = json.readTree(response.body());
        var data = root.path("data");
        if (root.path("code").asInt() != 200 || !category.equals(data.path("category").asText())
                || !CategoryCatalog.prodNameOf(category).equals(data.path("prod_name").asText())
                || !data.path("mape_test").isNumber() || !data.path("admitted").isBoolean()
                || !data.path("yhat").isArray()) throw new IllegalStateException("算法响应不完整");
        double mape = data.path("mape_test").asDouble();
        boolean admitted = data.path("admitted").asBoolean();
        String model = data.path("model").asText();
        if (!Double.isFinite(mape) || mape < 0 || admitted != (mape <= 30)
                || model.isBlank() || model.length() > 32
                || !RealtimePredictVO.DISCLAIMER.equals(data.path("disclaimer").asText()))
            throw new IllegalStateException("算法响应未满足准入约定");
        var nodes = data.path("yhat");
        if (nodes.size() != (admitted ? days : 0)) throw new IllegalStateException("预测步数异常");
        var points = new ArrayList<PredictPointVO>();
        LocalDate date = LocalDate.parse(data.path("snapshot_date").asText());
        for (var point : nodes) {
            date = date.plusDays(1);
            if (!date.toString().equals(point.path("date").asText()) || !point.path("yhat").isNumber()
                    || !Double.isFinite(point.path("yhat").asDouble()) || point.path("yhat").asDouble() <= 0)
                throw new IllegalStateException("预测点异常");
            points.add(new PredictPointVO(date.toString(), point.path("yhat").decimalValue()));
        }
        return new RealtimePredictVO(category, CategoryCatalog.prodNameOf(category), model,
                data.path("mape_test").decimalValue(), points, RealtimePredictVO.DISCLAIMER,
                false, "REALTIME", admitted, admitted ? "实时预测" : "波动过大，暂不提供预测（仅供参考）");
    }
}
