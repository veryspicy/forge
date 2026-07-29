# 角色权限矩阵

## 角色定义

| 角色 | 英文标识 | 权限范围 | 说明 |
|------|---------|---------|------|
| 管理员 | `admin` | 全部功能 | 角色管理 + 系统配置 + 供应商管理 + 所有运营/客服权限 |
| 运营 | `operator` | 商品/订单/定价 | 商品 CRUD + 上下架 + 订单审核/采购/物流 + 定价配置 |
| 客服 | `support` | 订单查询/退款 | 查单 + 退款处理 + 物流查询 + 用户沟通 |

## 权限矩阵

| 功能模块 | admin | operator | support |
|---------|:-----:|:--------:|:-------:|
| Dashboard 首页 | ✅ | ✅ | ✅ |
| 商品列表 / 搜索 | ✅ | ✅ | ❌ |
| 新建商品 | ✅ | ✅ | ❌ |
| 编辑商品 | ✅ | ✅ | ❌ |
| 上下架商品 | ✅ | ✅ | ❌ |
| 订单列表 | ✅ | ✅ | ✅ |
| 订单详情 | ✅ | ✅ | ✅ |
| 审核确认订单 | ✅ | ✅ | ❌ |
| 推送采购 | ✅ | ✅ | ❌ |
| 采购异常处理 | ✅ | ✅ | ❌ |
| 物流录入 | ✅ | ✅ | ❌ |
| 退款处理 | ✅ | ✅ | ✅ |
| 供应商管理 | ✅ | ❌ | ❌ |
| 定价规则配置 | ✅ | ✅ | ❌ |
| AI 探针记录 | ✅ | ✅ | ❌ |
| 系统设置 | ✅ | ❌ | ❌ |
| 角色管理 | ✅ | ❌ | ❌ |

## 技术实现

### 依赖注入

Admin 路由通过 FastAPI Depends 注入角色检查：

```python
from forge.main.dependencies import require_role, UserRole

# 仅 admin + operator 可访问
Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))

# 所有角色可访问
Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR, UserRole.SUPPORT))
```

### 路由隔离

- 消费者 API：`/api/v1/*`
- 管理后台 API：`/api/admin/v1/*`

## 扩展计划

当前 `require_role` 为占位实现（开发阶段所有已认证用户视为 admin），后续需对接用户表：

```sql
SELECT role FROM users WHERE id = $1
```

正式环境接入后，更新 `dependencies.py` 中 `role_checker` 的实现即可，所有路由的角色检查自动生效。
