package com.agri.priceradar;

import com.agri.priceradar.entity.PredictResult;
import com.agri.priceradar.mapper.PredictResultMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import java.net.InetSocketAddress;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.concurrent.Executors;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** 真实HTTP传输桩+MockMvc权限链；只mock回退表，避免修改业务预测快照。 */
class RealtimePredictIntegrationTest extends ApiTestBase {
    private static HttpServer server;
    private static final java.util.concurrent.ExecutorService executor = Executors.newCachedThreadPool(r -> {
        Thread thread = new Thread(r); thread.setDaemon(true); return thread;
    });
    private static volatile String mode = "OK";
    static { startServer(0); }
    private static final int PORT = server.getAddress().getPort();

    private static void startServer(int port) {
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
            server.setExecutor(executor);
            server.createContext("/ml/forecast", exchange -> {
                try {
                    String current = mode;
                    if (current.equals("SLOW")) Thread.sleep(1200);
                    int status = current.equals("ERROR") ? 503 : 200;
                    String body = current.equals("BAD") ? "{}" : """
                        {"code":200,"msg":"成功","data":{"category":"大白菜","prod_name":"大白菜",
                        "model":"Prophet","mape_test":20,"admitted":true,"snapshot_date":"2026-09-27",
                        "disclaimer":"预测结果仅供参考，不构成任何买卖建议",
                        "yhat":[{"date":"2026-09-28","yhat":1},{"date":"2026-09-29","yhat":2},{"date":"2026-09-30","yhat":3}]}}
                        """;
                    if (current.equals("REJECT")) body = body.replace("\"mape_test\":20", "\"mape_test\":40")
                            .replace("\"admitted\":true", "\"admitted\":false")
                            .replaceAll("\"yhat\":\\[.*?]", "\"yhat\":[]");
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    exchange.sendResponseHeaders(status, bytes.length);
                    if (current.equals("BODY")) {
                        exchange.getResponseBody().write(bytes, 0, 1);
                        exchange.getResponseBody().flush();
                        Thread.sleep(1200);
                        exchange.getResponseBody().write(bytes, 1, bytes.length - 1);
                    } else exchange.getResponseBody().write(bytes);
                } catch (Exception ignored) {
                    // 超时测试中客户端主动断开，写回失败是预期行为。
                } finally { exchange.close(); }
            });
            server.start();
        } catch (Exception e) { throw new IllegalStateException(e); }
    }

    @DynamicPropertySource
    static void config(DynamicPropertyRegistry registry) {
        registry.add("apr.ml.base-url", () -> "http://127.0.0.1:" + PORT);
        registry.add("apr.ml.timeout-ms", () -> 400);
    }

    @MockBean private PredictResultMapper predictions;
    private String token;

    @BeforeEach
    void setupForecast() throws Exception {
        mode = "OK";
        token = dataAdminToken();
        var rows = new ArrayList<PredictResult>();
        for (int i = 0; i < 7; i++) {
            var row = new PredictResult();
            row.setPredictDate(LocalDate.of(2026, 9, 28).plusDays(i));
            row.setModel("ARIMA(1,1,1)"); row.setMapeTest(BigDecimal.TEN); row.setYhat(BigDecimal.ONE);
            rows.add(row);
        }
        when(predictions.selectLatestModel("大白菜")).thenReturn("ARIMA(1,1,1)");
        when(predictions.selectByCategoryAndModel("大白菜", "ARIMA(1,1,1)")).thenReturn(rows);
    }

    @AfterAll
    static void stop() { server.stop(0); executor.shutdownNow(); }

    private org.springframework.test.web.servlet.ResultActions call() throws Exception {
        return mockMvc.perform(get("/api/predict/realtime").param("category", "大白菜").param("days", "3")
                .header("Authorization", bearer(token)));
    }

    private void expectFallback() throws Exception {
        call().andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.degraded").value(true))
                .andExpect(jsonPath("$.data.source").value("PRECOMPUTED"))
                .andExpect(jsonPath("$.data.model").value("ARIMA(1,1,1)"))
                .andExpect(jsonPath("$.data.points.length()").value(3));
    }

    @Test void normalForDataAdmin() throws Exception {
        call().andExpect(jsonPath("$.data.degraded").value(false))
                .andExpect(jsonPath("$.data.model").value("Prophet"))
                .andExpect(jsonPath("$.data.points.length()").value(3))
                .andExpect(jsonPath("$.data.disclaimer").value("预测结果仅供参考，不构成任何买卖建议"));
        verifyNoInteractions(predictions);
    }
    @Test void timeoutFallsBackWithinDeadline() throws Exception {
        mode = "SLOW";
        long start = System.nanoTime(); expectFallback();
        assertTrue((System.nanoTime() - start) / 1_000_000 < 1100);
    }
    @Test void slowBodyAlsoHasDeadline() throws Exception {
        mode = "BODY";
        long start = System.nanoTime(); expectFallback();
        assertTrue((System.nanoTime() - start) / 1_000_000 < 1100);
    }
    @Test void connectionRefusedFallsBack() throws Exception {
        server.stop(0);
        try { expectFallback(); } finally { startServer(PORT); }
    }
    @Test void service503FallsBack() throws Exception { mode = "ERROR"; expectFallback(); }
    @Test void malformedResponseFallsBack() throws Exception { mode = "BAD"; expectFallback(); }
    @Test void noSavedPredictionReturnsEmpty200() throws Exception {
        mode = "ERROR";
        when(predictions.selectLatestModel("大白菜")).thenReturn(null);
        call().andExpect(jsonPath("$.code").value(200)).andExpect(jsonPath("$.data.degraded").value(true))
                .andExpect(jsonPath("$.data.points.length()").value(0));
    }
    @Test void admissionRejectionDoesNotResurrectSavedPrediction() throws Exception {
        mode = "REJECT";
        call().andExpect(jsonPath("$.data.degraded").value(false))
                .andExpect(jsonPath("$.data.admitted").value(false)).andExpect(jsonPath("$.data.points.length()").value(0));
        verifyNoInteractions(predictions);
    }
    @Test void invalidInputsAre400() throws Exception {
        for (String days : new String[]{"0", "8", "abc"}) {
            mockMvc.perform(get("/api/predict/realtime").param("category", "大白菜").param("days", days)
                    .header("Authorization", bearer(token))).andExpect(jsonPath("$.code").value(400));
        }
        mockMvc.perform(get("/api/predict/realtime").param("category", "未知").header("Authorization", bearer(token)))
                .andExpect(jsonPath("$.code").value(400));
    }
    @Test void anonymousIs401() throws Exception {
        mockMvc.perform(get("/api/predict/realtime").param("category", "大白菜"))
                .andExpect(jsonPath("$.code").value(401));
    }
}
