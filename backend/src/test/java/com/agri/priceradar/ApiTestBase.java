package com.agri.priceradar;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import java.util.UUID;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * 接口测试基类 —— 提供登录换取 JWT 的能力（鉴权接入后所有业务接口都需要令牌）
 * 前置: MySQL 可达且权限、预警、首次改密与审计迁移齐备；凭据经测试环境变量注入
 */
@SpringBootTest(properties = {"apr.collect.script=src/test/resources/collect_stub.py", "apr.collect.project-dir=.", "apr.alert.cron=-"})
@AutoConfigureMockMvc
abstract class ApiTestBase {

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected ObjectMapper objectMapper;

    @Autowired
    protected JdbcTemplate jdbcTemplate;

    @Autowired
    protected PasswordEncoder passwordEncoder;

    protected String testAdmin;
    protected String testDataAdmin;
    protected final String testPassword = requiredEnv("APR_TEST_PASSWORD");
    protected final String newPassword = requiredEnv("APR_TEST_NEW_PASSWORD");

    private static String requiredEnv(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) throw new IllegalStateException("请注入测试环境变量 " + name);
        return value;
    }

    /** 每例使用独立账号，避免已标记首次改密的演示账号干扰回归测试。 */
    @BeforeEach
    void createTestUsers() {
        String suffix = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        testAdmin = "test_admin_" + suffix;
        testDataAdmin = "test_data_" + suffix;
        createUser(testAdmin, "ADMIN");
        createUser(testDataAdmin, "DATA_ADMIN");
    }

    private void createUser(String username, String role) {
        jdbcTemplate.update("INSERT INTO sys_user (username, password, nickname, status) VALUES (?, ?, ?, 1)",
                username, passwordEncoder.encode(testPassword), username);
        jdbcTemplate.update("INSERT INTO sys_user_role (user_id, role_id) " +
                "SELECT u.id, r.id FROM sys_user u JOIN sys_role r ON r.code = ? WHERE u.username = ?",
                role, username);
    }

    @AfterEach
    void removeTestUsers() {
        for (String username : new String[]{testAdmin, testDataAdmin}) {
            if (username == null) continue;
            jdbcTemplate.update("DELETE ur FROM sys_user_role ur JOIN sys_user u ON u.id = ur.user_id WHERE u.username = ?", username);
            jdbcTemplate.update("DELETE FROM sys_user WHERE username = ?", username);
        }
    }

    /** 登录并返回 JWT; 失败返回 null */
    protected String login(String username, String password) throws Exception {
        String body = objectMapper.writeValueAsString(Map.of("username", username, "password", password));
        String response = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode node = objectMapper.readTree(response);
        JsonNode token = node.path("data").path("token");
        return token.isMissingNode() || token.isNull() ? null : token.asText();
    }

    /** 管理员令牌（ADMIN） */
    protected String adminToken() throws Exception {
        return login(testAdmin, testPassword);
    }

    /** 数据管理员令牌（DATA_ADMIN） */
    protected String dataAdminToken() throws Exception {
        return login(testDataAdmin, testPassword);
    }

    protected String bearer(String token) {
        return "Bearer " + token;
    }
}
