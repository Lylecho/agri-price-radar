package com.agri.priceradar.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 工具（HS256 无状态令牌, 不依赖 Redis）
 * 密钥经配置注入（生产用环境变量 APR_JWT_SECRET 覆盖）
 */
@Component
public class JwtUtil {

    private final SecretKey key;
    private final long expireMillis;

    public JwtUtil(@Value("${apr.jwt.secret}") String secret,
                   @Value("${apr.jwt.expire-minutes:120}") long expireMinutes) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expireMillis = expireMinutes * 60_000L;
    }

    /** 签发令牌: subject=用户ID, 附带 username 与 role */
    public String generate(Long userId, String username, String role) {
        Date now = new Date();
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("username", username)
                .claim("role", role)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expireMillis))
                .signWith(key)
                .compact();
    }

    /** 解析并校验令牌; 非法/过期抛 JwtException */
    public Claims parse(String token) {
        return Jwts.parser().verifyWith(key).build()
                .parseSignedClaims(token).getPayload();
    }

    /** 令牌有效期（秒）, 供前端展示/续期参考 */
    public long getExpireSeconds() {
        return expireMillis / 1000;
    }
}
