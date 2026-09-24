package com.agri.priceradar;

import com.fasterxml.jackson.databind.JsonNode;
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
 * 前置: MySQL 可达且已执行 backend/sql/w2_auth.sql（预置 admin/dataadmin 账号）
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTestBase {

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected ObjectMapper objectMapper;

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
        return login("admin", "admin123");
    }

    /** 数据管理员令牌（DATA_ADMIN） */
    protected String dataAdminToken() throws Exception {
        return login("dataadmin", "dataadmin123");
    }

    protected String bearer(String token) {
        return "Bearer " + token;
    }
}
