# 部署文档

## 1. 环境准备

### 1.1 OCI 资源清单

| 资源 | 数量 | 规格 | 区域 | 用途 |
|------|------|------|------|------|
| K3s Master | 1 | VM.Standard.A1.Flex (4 OCPU, 24GB) | US-West | K3s 主节点 |
| K3s Worker | 2 | VM.Standard.A1.Flex (4 OCPU, 24GB) | US-West | 工作节点 |
| K3s Master | 1 | VM.Standard.A1.Flex (4 OCPU, 24GB) | EU-West | K3s 主节点 |
| K3s Worker | 2 | VM.Standard.A1.Flex (4 OCPU, 24GB) | EU-West | 工作节点 |
| Bastion Primary | 1 | VM.Standard.A1.Flex (2 OCPU, 12GB) | US-West | 出口代理 + SSH |
| Bastion Standby | 1 | VM.Standard.A1.Flex (2 OCPU, 12GB) | US-West | 主备切换 |
| Load Balancer | 1 | 100 Mbps | Global | 流量入口 |
| Public IP | 1 | Reserved | Global | 跳板机 VIP |
| Block Volume | 200GB | OCISCSI | US-West | PostgreSQL PVC |
| Block Volume | 100GB | OCISCSI | EU-West | PostgreSQL PVC |
| Object Storage | 1 | Standard | US-West | MinIO 后端 |

### 1.2 域名 DNS 记录

```
# A Records (指向 OCI LB 公网 IP)
@           IN A    <lb-public-ip>
www         IN A    <lb-public-ip>
api         IN A    <lb-public-ip>
ai          IN A    <lb-public-ip>

# CNAME (Cloudflare 代理)
*           IN CNAME forge.com.cdn.cloudflare.net
```

### 1.3 证书

```bash
# 使用 cert-manager 自动签发 Let's Encrypt 证书
# 或通过 OCI Certificate Manager 导入自定义证书
kubectl apply -f k8s/ingress/tls.yaml
```

---

## 2. K3s 集群初始化

### 2.1 Master 节点 (美西)

```bash
#!/bin/bash
# setup-k3s-master-na.sh

# 安装 K3s
curl -sfL https://get.k3s.io | sh -s - server \
  --disable traefik \
  --disable servicelb \
  --tls-san <lb-internal-ip> \
  --cluster-init \
  --write-kubeconfig-mode 644

# 安装 OCISCSI 驱动
kubectl apply -f https://raw.githubusercontent.com/oracle/ociscsi/master/deployable/ociscsi-driver.yaml

# 安装 cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.15.0 \
  --set crds.enabled=true

# 配置存储类
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ociscsi-na
provisioner: ocs.csi.oracle.com
parameters:
  volumeBindingMode: WaitForFirstConsumer
  reclaimPolicy: Delete
EOF

# 设置 kubectl 上下文
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl config set-context k3s-na --cluster=k3s-na
```

### 2.2 Worker 节点 (美西)

```bash
#!/bin/bash
# setup-k3s-worker-na.sh

# 从 Master 获取 join token
# 在 Master 上执行: cat /var/lib/rancher/k3s/server/node-token
# 输出类似: K11xxx::server:yyy

curl -sfL https://get.k3s.io | sh -s - agent \
  --server https://<master-internal-ip>:6443 \
  --token <join-token>
```

### 2.3 跳板机配置

```bash
#!/bin/bash
# setup-bastion.sh

# 安装 HAProxy (出口代理)
apt update && apt install -y haproxy

# 配置 HAProxy 作为 HTTPS 出口代理
cat > /etc/haproxy/haproxy.cfg <<'EOF'
global
    log stdout format raw local0
    maxconn 4096

defaults
    log     global
    mode    tcp
    option  tcplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s

frontend https_out
    bind *:443
    default_backend https_servers

backend https_servers
    balance roundrobin
    server s1 0.0.0.0:443 check
EOF

# 启用 IP 转发
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# 配置 iptables NAT
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# 安装 Keepalived (主备切换)
apt install -y keepalived

# 配置 Keepalived (主节点)
cat > /etc/keepalived/keepalived.conf <<'EOF'
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass password123
    }
    virtual_ipaddress {
        <vip-address> dev eth0 label eth0:vip
    }
}
EOF

# 防火墙规则
ufw allow ssh
ufw default deny incoming
ufw default allow outgoing
ufw enable
```

---

## 3. Harbor 私有仓库部署

```bash
#!/bin/bash
# setup-harbor.sh

# 下载 Harbor
wget https://github.com/goharbor/harbor/releases/download/v2.12.0/harbor-online-installer-v2.12.0.tgz
tar xf harbor-online-installer-v2.12.0.tgz
cd harbor

# 配置 Harbor
cat > harbor.yml <<'EOF'
hostname: harbor.forge.com
port: 443
certificate: /etc/harbor/tls/fullchain.pem
private_key: /etc/harbor/tls/privkey.pem
harbor_admin_password: Harbor12345
data_volume: /data/harbor
log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /var/log/harbor
EOF

# 安装
./install.sh

# 登录
docker login harbor.forge.com
# admin / Harbor12345
```

---

## 4. Jenkins CI/CD 流水线

### 4.1 Jenkins 安装

```bash
# 在 K3s 上部署 Jenkins
kubectl create namespace ci-cd

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jenkins
  namespace: ci-cd
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jenkins
  template:
    metadata:
      labels:
        app: jenkins
    spec:
      containers:
        - name: jenkins
          image: jenkins/jenkins:lts-jdk17
          ports:
            - containerPort: 8080
            - containerPort: 50000
          volumeMounts:
            - name: jenkins-data
              mountPath: /var/jenkins_home
      volumes:
        - name: jenkins-data
          persistentVolumeClaim:
            claimName: jenkins-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: jenkins
  namespace: ci-cd
spec:
  type: ClusterIP
  ports:
    - port: 8080
      targetPort: 8080
  selector:
    app: jenkins
EOF
```

### 4.2 Jenkinsfile

```groovy
pipeline {
    agent any

    environment {
        HARBOR_SERVER = 'harbor.forge.com'
        HARBOR_PROJECT = 'forge'
        NAMESPACE_NA = 'forge-public'
        NAMESPACE_EU = 'forge-public'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Backend Tests') {
            steps {
                container('python:3.12-slim') {
                    sh '''
                        pip install uv
                        cd backend
                        uv sync --frozen
                        uv run pytest tests/ -v
                    '''
                }
            }
        }

        stage('Frontend Build') {
            steps {
                container('node:20-alpine') {
                    sh '''
                        cd portal-web
                        pnpm install --frozen-lockfile
                        pnpm build
                    '''
                }
            }
        }

        stage('Build & Push Images') {
            steps {
                script {
                    def VERSION = "${env.BUILD_ID}-${env.GIT_COMMIT[0..7]}"
                    
                    // Backend
                    sh """
                        docker build -t ${HARBOR_SERVER}/${HARBOR_PROJECT}/backend:${VERSION} backend/
                        docker login ${HARBOR_SERVER} -u admin -p ${HARBOR_PASSWORD}
                        docker push ${HARBOR_SERVER}/${HARBOR_PROJECT}/backend:${VERSION}
                    """
                    
                    // Frontend
                    sh """
                        docker build -t ${HARBOR_SERVER}/${HARBOR_PROJECT}/portal-web:${VERSION} portal-web/
                        docker push ${HARBOR_SERVER}/${HARBOR_PROJECT}/portal-web:${VERSION}
                    """
                    
                    // AI Service
                    sh """
                        docker build -t ${HARBOR_SERVER}/${HARBOR_PROJECT}/ai-service:${VERSION} ai-service/
                        docker push ${HARBOR_SERVER}/${HARBOR_PROJECT}/ai-service:${VERSION}
                    """
                    
                    env.IMAGE_VERSION = VERSION
                }
            }
        }

        stage('Deploy to K3s (NA)') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sh """
                        kubectl --context k3s-na \\
                            set image deployment/portal-web \\
                            portal-web=${HARBOR_SERVER}/${HARBOR_PROJECT}/portal-web:${env.IMAGE_VERSION} \\
                            -n ${NAMESPACE_NA}
                        
                        kubectl --context k3s-na \\
                            set image deployment/backend \\
                            backend=${HARBOR_SERVER}/${HARBOR_PROJECT}/backend:${env.IMAGE_VERSION} \\
                            -n ${NAMESPACE_NA}
                        
                        kubectl --context k3s-na \\
                            set image deployment/ai-service \\
                            ai-service=${HARBOR_SERVER}/${HARBOR_PROJECT}/ai-service:${env.IMAGE_VERSION} \\
                            -n ${NAMESPACE_NA}
                        
                        kubectl --context k3s-na rollout status deployment/portal-web -n ${NAMESPACE_NA}
                        kubectl --context k3s-na rollout status deployment/backend -n ${NAMESPACE_NA}
                    """
                }
            }
        }

        stage('Deploy to K3s (EU)') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sh """
                        kubectl --context k3s-eu \\
                            set image deployment/portal-web \\
                            portal-web=${HARBOR_SERVER}/${HARBOR_PROJECT}/portal-web:${env.IMAGE_VERSION} \\
                            -n ${NAMESPACE_EU}
                        
                        kubectl --context k3s-eu \\
                            set image deployment/backend \\
                            backend=${HARBOR_SERVER}/${HARBOR_PROJECT}/backend:${env.IMAGE_VERSION} \\
                            -n ${NAMESPACE_EU}
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Deployment successful!"
        }
        failure {
            echo "Deployment failed!"
        }
    }
}
```

---

## 5. ArgoCD 部署

### 5.1 ArgoCD 安装

```bash
# 安装 ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.12.0/manifests/install.yaml

# 获取 Admin 密码
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.admin\\.password}" | base64 -d
```

### 5.2 Application 配置

```yaml
# k8s/argocd/application-na.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: forge-na
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<user>/forge.git
    targetRevision: main
    path: k8s
    helm:
      valueFiles:
        - values-na.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: forge-public
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### 5.3 Helm Values 文件

```yaml
# k8s/values-na.yaml
# 北美区域配置
region: na
environment: production

portal-web:
  image:
    repository: harbor.forge.com/forge/portal-web
    tag: latest
    pullPolicy: Always
  replicas: 3
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
  env:
    NUXT_PUBLIC_API_BASE: "https://api.forge.com/api/v1"
    NUXT_PUBLIC_REGION: "na"
    NUXT_PUBLIC_DEFAULT_CURRENCY: "USD"

backend:
  image:
    repository: harbor.forge.com/forge/backend
    tag: latest
    pullPolicy: Always
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 1Gi
  env:
    DATABASE_URL: "postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres-rw.forge-data.svc:5432/forge"
    REDIS_URL: "redis://redis-svc.forge-data.svc:6379/0"
    ROCKETMQ_PROXY: "rocketmq-proxy.forge-mq.svc:8081"
    REGION: "na"
    DEFAULT_CURRENCY: "USD"

ai_service:
  image:
    repository: harbor.forge.com/forge/ai-service
    tag: latest
    pullPolicy: Always
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 2Gi
```

```yaml
# k8s/values-eu.yaml
# 欧洲区域配置
region: eu
environment: production

portal-web:
  env:
    NUXT_PUBLIC_REGION: "eu"
    NUXT_PUBLIC_DEFAULT_CURRENCY: "EUR"

backend:
  env:
    DATABASE_URL: "postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres-ro.forge-data.svc:5432/forge"
    REGION: "eu"
    DEFAULT_CURRENCY: "EUR"
    VAT_RATE: "0.19"
```

---

## 6. 部署脚本

### 6.1 一键部署脚本

```bash
#!/bin/bash
# deploy.sh

set -euo pipefail

REGION=${1:-na}  # na | eu
IMAGE_TAG=${2:-latest}

echo "=== Deploying to ${REGION} region ==="

# Login to Harbor
docker login harbor.forge.com

# Build images
echo "Building images..."
docker build -t harbor.forge.com/forge/portal-web:${IMAGE_TAG} ./portal-web/
docker build -t harbor.forge.com/forge/backend:${IMAGE_TAG} ./backend/
docker build -t harbor.forge.com/forge/ai-service:${IMAGE_TAG} ./ai-service/

# Push images
echo "Pushing images..."
docker push harbor.forge.com/forge/portal-web:${IMAGE_TAG}
docker push harbor.forge.com/forge/backend:${IMAGE_TAG}
docker push harbor.forge.com/forge/ai-service:${IMAGE_TAG}

# Deploy to K3s
if [ "$REGION" = "na" ]; then
    CONTEXT="k3s-na"
    VALUES_FILE="values-na.yaml"
else
    CONTEXT="k3s-eu"
    VALUES_FILE="values-eu.yaml"
fi

echo "Deploying with kubectl --context ${CONTEXT}..."
kubectl --context ${CONTEXT} set image \
    deployment/portal-web portal-web=harbor.forge.com/forge/portal-web:${IMAGE_TAG} \
    -n forge-public

kubectl --context ${CONTEXT} set image \
    deployment/backend backend=harbor.forge.com/forge/backend:${IMAGE_TAG} \
    -n forge-public

kubectl --context ${CONTEXT} set image \
    deployment/ai-service ai-service=harbor.forge.com/forge/ai-service:${IMAGE_TAG} \
    -n forge-public

# Wait for rollout
echo "Waiting for rollout..."
kubectl --context ${CONTEXT} rollout status deployment/portal-web -n forge-public
kubectl --context ${CONTEXT} rollout status deployment/backend -n forge-public
kubectl --context ${CONTEXT} rollout status deployment/ai-service -n forge-public

echo "=== Deployment complete! ==="
echo "Frontend: https://portal-web.forge.com"
echo "API: https://api.forge.com"
```

### 6.2 回滚脚本

```bash
#!/bin/bash
# rollback.sh

set -euo pipefail

REGION=${1:-na}
CONTEXT="k3s-${REGION}"

echo "Rolling back in ${REGION}..."

kubectl --context ${CONTEXT} rollout undo deployment/portal-web -n forge-public
kubectl --context ${CONTEXT} rollout undo deployment/backend -n forge-public
kubectl --context ${CONTEXT} rollout undo deployment/ai-service -n forge-public

echo "Rollback complete!"
```

---

## 7. 监控和维护

### 7.1 健康检查

```bash
# 检查所有 Pod 状态
kubectl --context k3s-na get pods -n forge-public -o wide

# 检查 Pod 日志
kubectl --context k3s-na logs -f deployment/backend -n forge-public

# 检查数据库连接
kubectl --context k3s-na exec -it deployment/backend -n forge-public -- \
    python -c "from sqlalchemy import create_engine; print('OK')"

# 检查 RocketMQ 连接
kubectl --context k3s-na exec -it deployment/backend -n forge-public -- \
    python -c "import httpx; r = httpx.get('http://rocketmq-proxy:8081'); print(r.status_code)"
```

### 7.2 扩容

```bash
# 手动扩容
kubectl --context k3s-na scale deployment/backend --replicas=5 -n forge-public

# HPA 自动扩容 (由 k8s/templates/portal-web/hpa.yaml 等配置)
kubectl --context k3s-na get hpa -n forge-public
```

### 7.3 备份

```bash
# PostgreSQL 备份
kubectl --context k3s-na exec -it postgres-0 -n forge-data -- \
    pg_dump -U postgres forge > backup-$(date +%Y%m%d).sql

# 恢复
kubectl --context k3s-na exec -it postgres-0 -n forge-data -- \
    psql -U postgres forge < backup-20250115.sql
```
