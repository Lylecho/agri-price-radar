package com.agri.priceradar.service;

import com.agri.priceradar.aspect.Audited;
import com.agri.priceradar.aspect.AuditAction;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 手动触发采集服务（管理端"立即补采"）
 *
 * 设计: 复用 Python 采集器实现（不在 Java 侧重写爬虫, 保持单一实现），
 *       异步子进程执行, 立即返回受理; 结果写入 collect_log 供管理端查看。
 * 约束: 同一时刻只允许一个采集任务（AtomicBoolean 互斥）。
 */
@Service
public class CollectTriggerService {

    private static final Logger log = LoggerFactory.getLogger(CollectTriggerService.class);
    private static final String JOB = "collect";

    private final CollectLogService collectLogService;

    @Value("${apr.collect.python-exe:python}")
    private String pythonExe;

    @Value("${apr.collect.script:python/collector/xinfadi.py}")
    private String script;

    @Value("${apr.collect.project-dir:..}")
    private String projectDir;

    @Value("${apr.collect.lookback-days:3}")
    private int lookbackDays;

    @Value("${apr.collect.timeout-seconds:600}")
    private long timeoutSeconds;

    /** 运行互斥: 已有任务在跑时拒绝再次触发 */
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final ExecutorService executor = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "manual-collect");
        t.setDaemon(true);
        return t;
    });

    public CollectTriggerService(CollectLogService collectLogService) {
        this.collectLogService = collectLogService;
    }

    /** 触发一次增量采集; 已在运行则返回 false */
    @Audited(AuditAction.TRIGGER_COLLECT)
    public boolean trigger() {
        if (!running.compareAndSet(false, true)) {
            return false;
        }
        executor.submit(this::doCollect);
        return true;
    }

    public boolean isRunning() {
        return running.get();
    }

    private void doCollect() {
        LocalDateTime started = LocalDateTime.now();
        try {
            Path workDir = Paths.get(projectDir).toAbsolutePath().normalize();
            ProcessBuilder pb = new ProcessBuilder(
                    pythonExe, script, "collect", "--days", String.valueOf(lookbackDays));
            pb.directory(workDir.toFile());
            pb.redirectErrorStream(true);
            log.info("[手动采集] 启动子进程: {} {} collect --days {}", pythonExe, script, lookbackDays);

            Process process = pb.start();
            StringBuilder output = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line).append('\n');
                    if (output.length() > 4000) {
                        output.setLength(4000);   // 防御超长输出
                    }
                }
            }
            boolean finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            LocalDateTime ended = LocalDateTime.now();
            if (!finished) {
                process.destroyForcibly();
                collectLogService.writeLog(JOB, "FAILED",
                        "[手动] 采集超时(" + timeoutSeconds + "s)被终止", null, started, ended);
                log.error("[手动采集] 超时终止");
                return;
            }
            int exit = process.exitValue();
            String tail = tailOf(output.toString());
            if (exit == 0) {
                collectLogService.writeLog(JOB, "SUCCESS", "[手动] " + tail, null, started, ended);
                log.info("[手动采集] 完成: {}", tail);
            } else {
                collectLogService.writeLog(JOB, "FAILED",
                        "[手动] 退出码 " + exit + ": " + tail, null, started, ended);
                log.error("[手动采集] 失败, 退出码 {}: {}", exit, tail);
            }
        } catch (Exception e) {
            LocalDateTime ended = LocalDateTime.now();
            collectLogService.writeLog(JOB, "FAILED",
                    "[手动] 执行异常: " + e.getMessage(), null, started, ended);
            log.error("[手动采集] 异常", e);
        } finally {
            running.set(false);
        }
    }

    /** 取输出末尾（保留关键摘要, 避免日志过长） */
    private String tailOf(String text) {
        String[] lines = text.strip().split("\n");
        int from = Math.max(0, lines.length - 6);
        return String.join(" | ", java.util.Arrays.copyOfRange(lines, from, lines.length));
    }
}
