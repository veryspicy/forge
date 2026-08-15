# Admin 无响应 / 资源 404 排查与防复发手册

> 适用范围：Forge 项目（D:\codeRepo\forge），admin 容器（forge-admin）经网关（forge-gateway :8080）对外提供 /admin/。
> 记录日期：2026-08-14。适用脚本：`docker/rebuild-admin.ps1`、`docker/check-admin.ps1`。

---

## 1. 故障现象与根因

### 1.1 现象

- 浏览器访问 `http://localhost:8080/admin/` 超时白屏（"操作超时"），或
- 页面白屏，F12 Network 中 js/css 资源 404，但 `index.html` 返回 200。

### 1.2 根因清单

| 环节 | 根因 | 后果 |
|---|---|---|
| 使用层 | `localhost` 同时解析 IPv6 `::1` 与 IPv4 `127.0.0.1`，podman 网关仅监听 IPv4 | 浏览器走 `::1` 连接超时，误判"服务挂了" |
| 部署层 | podman-compose 外部 provider 静默失败（无输出、不生效） | 镜像已更新但容器未重建，页面仍是旧版 |
| 部署层 | 手动 `podman run` 重建容器丢失 compose 参数（网络别名等） | 网关 upstream `admin` 无法解析，502 / host not found |
| 网关层 | nginx 对字面量 `proxy_pass http://admin:80/` 只在**启动时**解析一次并缓存 IP | admin 容器重建换 IP 后，网关仍连旧 IP，转发 404/502 |
| 验证层 | 只验证 `index.html` 200，未验证 js/css 资源全链路 | 假阳性：页面实际不可用但报告"已修复" |
| 浏览器 | 缓存了重建期间失败的响应 | 服务恢复后页面仍白屏，需硬刷新 |

---

## 2. 防复发措施

### 2.1 部署：用脚本重建，禁止手动裸跑

- 统一使用 `docker/rebuild-admin.ps1`：
  - `podman build --no-cache --dns=223.5.5.5`（无缓存，避免 COPY 层命中旧源码；显式 DNS 绕过 registry.npmjs.org EAI_AGAIN）
  - 重建容器优先走 compose，通过 `StartedAt` 校验是否真生效，静默失败自动降级手动 `podman run --network docker_forge --network-alias admin`
  - 完成后自动跑 `check-admin.ps1` 自检，失败即报错退出，不产生假成功

### 2.2 网关：resolver 动态解析（已落地 gateway/nginx.conf）

```nginx
resolver 10.89.0.1 valid=30s ipv6=off;   # podman DNS（dns.podman 网络内 nameserver）
location /admin/ {
    set $admin_upstream http://admin:80;
    rewrite ^/admin/(.*)$ /$1 break;     # 变量 proxy_pass 不自动 strip 前缀，必须显式剥离（踩坑点）
    proxy_pass $admin_upstream;          # 含变量 → 每次请求动态解析 admin
    ...
}
```

- 效果：admin 容器重建更换 IP 后，网关无需重启/reload 即自动恢复（已实测：IP 10.89.0.15→10.89.0.18，网关零操作恢复 200）。
- **踩坑**：`proxy_pass` 一旦含变量，nginx 不会自动剥离 location 前缀，且尾斜杠写法（`proxy_pass $admin_upstream/;`）会把整个原始 URI 替换为 `/`，导致 admin 收到 `GET /` 返回 index.html（829B 假 200）。必须用 `rewrite ^/admin/(.*)$ /$1 break;` 显式剥离后再转发。
- 注意：`resolver` 地址为本机 podman DNS（`podman exec forge-gateway cat /etc/resolv.conf` 可查），换机器/换 k8s 环境需同步修改。
- k8s Ingress 形态不受影响（k8s 的 Service 名本身是稳定的 DNS 记录，由 kube-dns 解析）。

### 2.3 使用：固定访问入口

- 只用 `http://127.0.0.1:8080/admin/`（书签收藏），不要用 `localhost`。
- 可选：编辑 `C:\Windows\System32\drivers\etc\hosts`，注释掉 `::1 localhost` 行（`# ::1 localhost`），一劳永逸避免 IPv6 超时。

### 2.4 验证：全链路健康检查

- 每次 admin 重建后执行 `docker/check-admin.ps1`：
  - 拉取 `index.html` → 正则提取全部 js/css 资源 → 逐一请求验证 200。
  - 任一失败即退出码 1，杜绝"index.html 200 但资源 404"的假通过。
- 浏览器侧：`Ctrl+Shift+R` 硬刷新绕过缓存。

---

## 3. 快速排查流程（下次再出问题按此顺序）

```
1. podman ps -a | grep forge-admin     # 容器是否 Up
2. podman inspect forge-admin --format '{{.State.StartedAt}}'  # 是否刚重建
3. curl -sI http://127.0.0.1:8080/admin/                        # index.html 200？
4. .\docker\check-admin.ps1                                     # 全资源 200？
5. podman exec forge-gateway nginx -t                           # 网关配置语法
6. podman logs forge-admin --tail 50                            # admin nginx 日志
```

若 `check-admin.ps1` 报资源 404 但容器内文件存在（`podman exec forge-admin ls /usr/share/nginx/html/assets/`），
优先怀疑网关 DNS 缓存，直接 `podman exec forge-gateway nginx -s reload` 或按 2.2 确认 resolver 配置已生效。

---

## 4. 关联规则

- 本手册对应 DEV-RULES 第 3 节（部署策略）与第 10 节（重建后端到端验证）的落地工具。
- 更新 DEV-RULES 时保持脚本路径、容器名、网络名与本文档一致。
