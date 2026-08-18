# 网络设计文档

## 1. 网络拓扑

### 1.1 OCI VCN 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OCI VCN (US-West)                            │
│                                                                     │
│  CIDR: 10.0.0.0/16                                                  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Internet Gateway                          │   │
│  │                    (NAT Gateway)                             │   │
│  └────────────────────┬────────────────────────────────────────┘   │
│                       │                                             │
│          ┌────────────┼────────────┐                               │
│          ▼            ▼            ▼                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│  │  Public      │ │  Public      │ │  Private    │                 │
│  │  Subnet      │ │  Subnet      │ │  Subnet     │                 │
│  │  (10.0.1/24) │ │  (10.0.2/24) │ │  (10.0.3/24)│                 │
│  │              │ │              │ │             │                 │
│  │  OCI LB      │ │  Bastion-    │ │  K3s Master │                 │
│  │  Public IP   │ │  Primary     │ │  (10.0.3.2) │                 │
│  │              │ │  (VIP)       │ │  K3s Worker │                 │
│  │              │ │  (10.0.2.2)  │ │  (10.0.3.3) │                 │
│  │              │ │  Bastion-    │ │  K3s Worker │                 │
│  │              │ │  Standby     │ │  (10.0.3.4) │                 │
│  │              │ │  (10.0.2.3)  │ │  Service    │                 │
│  │              │ │              │ │  Pod IPs    │                 │
│  └──────────────┘ └──────────────┘ │  (10.244.x.x)│                │
│                                    └─────────────┘                 │
│                                                                     │
│  Security Lists:                                                    │
│  ├── Public Subnet: 443 in (LB), 22 out (Bastion SSH)              │
│  ├── Private Subnet: 仅内部通信 (K3s 集群)                          │
│  └── Bastion: 22 in (跳板SSH), 443 out (出站代理)                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        OCI VCN (EU-West)                            │
│  同构结构，CIDR: 10.1.0.0/16                                         │
│  通过 OCI Fast Connect / VPN 互联 (可选)                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 跨区域通信

```
┌──────────────────────────────────────────────────────────────┐
│                   跨区域数据同步                               │
│                                                              │
│  1. PostgreSQL 主从复制                                       │
│     ┌──────────────┐                              ┌────────┐ │
│     │ US-West PG   │  ──replication──▶│ EU-West PG │ │
│     │  (Master)    │                    (Slave)     │ │
│     └──────────────┘                              └────────┘
│     异步复制，延迟 < 5s                               │
│     写入: 仅 Master (US-West)                        │
│     读取: Master (US) + Slave (EU/ME)               │
│                                                     │
│  2. RocketMQ 消息同步                                 │
│     跨区域不需要同步 (各区域独立部署 RocketMQ)         │
│     EU 区域的订单事件在 EU RocketMQ 消费              │
│                                                     │
│  3. Redis 缓存                                        │
│     各区域独立 Redis Cluster                          │
│     热点数据 (商品目录) 通过缓存失效策略保持一致        │
│                                                     │
│  4. MinIO 对象存储                                    │
│     各区域独立 MinIO                                  │
│     图片通过 CDN (Cloudflare) 缓存和分发              │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. 网络安全策略

### 2.1 K8s NetworkPolicy

```yaml
# 1. 仅允许 LB 入站到前端和 API
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-lb-ingress
  namespace: forge-public
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: portal-web
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: <oci-lb-internal-ip>/32
      ports:
        - protocol: TCP
          port: 443

---
# 2. 所有 Pod 出站仅允许经跳板机
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-egress
  namespace: forge-public
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    # DNS 解析
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # 出站 HTTPS (经跳板机)
    - to:
        - ipBlock:
            cidr: <bastion-internal-ip>/32
      ports:
        - protocol: TCP
          port: 443
    # 内部服务通信
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 5432  # PostgreSQL
        - protocol: TCP
          port: 6379  # Redis
        - protocol: TCP
          port: 8081  # RocketMQ Proxy
        - protocol: TCP
          port: 9000  # MinIO
```

### 2.2 安全组规则

| 方向 | 协议 | 端口 | 来源/目标 | 说明 |
|------|------|------|----------|------|
| Ingress | TCP | 443 | 0.0.0.0/0 | HTTPS (LB) |
| Ingress | TCP | 22 | <your-IP>/32 | SSH (跳板机) |
| Outgress | TCP | 443 | <bastion>/32 | 出站 HTTPS |
| Outgress | TCP | 22 | <bastion>/32 | 出站 SSH |
| Internal | TCP | 6443 | K3s 节点间 | K3s API |
| Internal | TCP | 5432 | K3s Pod → PG | 数据库 |
| Internal | TCP | 6379 | K3s Pod → Redis | 缓存 |
| Internal | TCP | 8080,8081 | K3s Pod → MQ | RocketMQ |
| Internal | TCP | 9000 | K3s Pod → MinIO | 对象存储 |

---

## 3. 负载均衡配置

### 3.1 OCI LB 后端集

```
Listener: HTTPS 443
  ├── Backend Set: portal-web-set
  │   ├── 10.244.1.10:3000 (portal-web pod 1)
  │   ├── 10.244.1.11:3000 (portal-web pod 2)
  │   └── 10.244.1.12:3000 (portal-web pod 3)
  │   Health Check: HTTP GET / HTTP/1.1 → 200
  │
  ├── Backend Set: api-set
  │   ├── 10.244.2.10:8000 (backend pod 1)
  │   ├── 10.244.2.11:8000 (backend pod 2)
  │   └── 10.244.2.12:8000 (backend pod 3)
  │   Health Check: HTTP GET /api/health HTTP/1.1 → 200
  │
  └── Backend Set: ai-set
      ├── 10.244.3.10:8001 (ai-service pod 1)
      └── 10.244.3.11:8001 (ai-service pod 2)
      Health Check: HTTP GET /health HTTP/1.1 → 200

Routing Rule:
  ├── URL Path / → portal-web-set
  ├── URL Path /api/* → api-set
  ├── URL Path /ws/* → api-set
  └── URL Path /ai/* → ai-set
```

### 3.2 Traefik Ingress 配置

```yaml
# k8s/ingress/traefik-config.yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: forge-ingress
  namespace: forge-public
spec:
  entryPoints:
    - websecure
  routes:
    # Frontend
    - match: Host(`portal-web.forge.com`)
      kind: Rule
      services:
        - name: portal-web-svc
          port: 3000
    # API
    - match: Host(`api.forge.com`) && PathPrefix(`/api`)
      kind: Rule
      middlewares:
        - name: strip-api-prefix
      services:
        - name: backend-svc
          port: 8000
    # AI Chat WebSocket
    - match: Host(`api.forge.com`) && PathPrefix(`/ws`)
      kind: Rule
      services:
        - name: backend-svc
          port: 8000
          scheme: h2c
  tls:
    secretName: forge-tls
```

---

## 4. 跳板机出口代理

### 4.1 HAProxy 出口代理配置

```bash
# /etc/haproxy/haproxy.cfg
global
    log stdout format raw local0
    maxconn 10000

defaults
    log     global
    mode    tcp
    option  tcplog
    timeout connect 10s
    timeout client  60s
    timeout server  60s

# 出站 HTTPS 代理
frontend out_https
    bind *:443
    default_backend out_servers

backend out_servers
    balance roundrobin
    mode tcp
    # 允许访问的目标白名单
    acl allowed_dest dst_port 443
    acl allowed_dest dst_port 80
    tcp-request inspect-delay 5s
    tcp-request content accept if allowed_dest
    server out0 0.0.0.0:443 check inter 30s fall 3 rise 2
```

### 4.2 日志审计

```bash
# /etc/rsyslog.d/40-haproxy.conf
# 记录所有出站连接
$AddUnixListenSocket /var/lib/haproxy/dev/log

local0.* /var/log/haproxy/outbound.log

# 日志轮转
cat > /etc/logrotate.d/haproxy <<'EOF'
/var/log/haproxy/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    copytruncate
}
EOF
```

---

## 5. Cloudflare CDN 配置

### 5.1 DNS 设置

```
# 全部通过 Cloudflare 代理 (Proxy ON)
@           A    <OCI-LB-IP>       # proxied
www         CNAME @                  # proxied
api         CNAME @                  # proxied
ai          CNAME @                  # proxied
```

### 5.2 Edge Cache Rules

| Rule | Cache Level | TTL |
|------|------------|-----|
| `*forge.com/assets/*` | Cache Everything | 1 year |
| `*forge.com/images/*` | Cache Everything | 1 month |
| `*forge.com/*.html` | Bypass Cache | 0 |
| `*forge.com/api/*` | Bypass Cache | 0 |
| `*forge.com/*` | Simple Cache | 2 hours |

### 5.3 WAF 规则

```
# 默认规则集 (免费层)
- Block: SQL Injection
- Block: XSS
- Block: PHP Injection
- Block: HTTP Protocol Violations

# 自定义规则
- Rate Limit: /api/v1/ai/chat/* → 30 req/min per IP
- Rate Limit: /api/v1/auth/* → 10 req/min per IP
- Block: Known Bad Bots
```

---

## 6. 域名和 SSL

### 6.1 cert-manager 配置

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@forge.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: traefik
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: forge-tls
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - portal-web.forge.com
        - api.forge.com
        - ai.forge.com
      secretName: forge-tls-secret
```

---

## 7. 故障转移

### 7.1 跳板机 HA

```
Keepalived VRRP 配置:

Bastion-Primary (Master, Priority 100):
  ├── 持有 VIP: <public-vip>
  ├── HAProxy 运行中
  ├── 日志: /var/log/haproxy/access.log
  └── 状态: MASTER

Bastion-Standby (Backup, Priority 90):
  ├── 监听 VRRP 通告
  ├── HAProxy 热备 (同步配置)
  ├── 切换时间: < 3s
  └── 状态: BACKUP

切换条件:
  ├── Primary 心跳丢失 (3个通告周期 = 3s)
  ├── 自动提升 Standby 为 Master
  └── VIP 漂移到新 Master
```

### 7.2 K3s 高可用

```
Multi-Master K3s:

Master-1 (US-West): 选举 Leader
Master-2 (US-West): Follower

etcd/Kine 数据同步:
  ├── SQLite (单 Master) → 自动 Leader 切换
  └── 切换时间: < 30s

Worker 节点:
  ├── 自动重连到新的 Leader
  └── Pod 自动调度到新 Master
```

### 7.3 跨区域故障转移

```
主区域 (US-West) 故障时:

1. Cloudflare 自动检测 (30s)
2. DNS 切换到 EU-West
3. EU-West 集群接管所有流量
4. 数据一致性: 最多丢失 5s 数据 (异步复制延迟)

恢复后:
1. US-West 重新上线
2. EU-West PG Slave → Promote to Master
3. US-West PG 重新同步
4. DNS 切回 US-West (可选)
```
