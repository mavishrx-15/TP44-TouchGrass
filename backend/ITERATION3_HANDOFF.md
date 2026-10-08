# Iteration 3 后端交接

分支 `feature/iteration3-integration` 合并了 Tian 的 CBD/脚手架分支和 mavis 的
`feature/iteration3-sprout-guide`。社区和天气用 mavis 已经能跑的实现，脚手架里对应的
空壳已删除。路线规划仍是脚手架，返回 HTTP 501 `feature_not_implemented`，不能当作已实现。

## 模块分工

| 模块 | 负责人 | 文件 |
|---|---|---|
| CBD/树木数据 | Tian | `app/cbd.py`、`routers/cbd_data.py`、`services/cbd_data.py`、`schemas/cbd.py` |
| 路线/推荐、Sprout 解释 | Tian | `routers/sprout_routes.py`、`services/planning.py`、`services/sprout.py`、`repositories/planning.py`、`integrations/google_routes.py`、`schemas/planning.py`、现有 `routers/routes.py` |
| 天气 | sliu | `routers/weather.py`（mavis 的实现） |
| pin/照片/留言/报告 | sliu | `routers/care.py`（mavis 的实现） |
| 前端 | mavis | `frontend/` |

天气和社区的详细待办清单另行提供给 sliu。

## 共享代码规则

- 新模块按 router → service → repository/integration 分层，不调用另一个 router handler。
- 共享坐标在 `schemas/common.py`；地图模型在 `schemas/map_data.py`；密度和树木聚合在
  `services/zone_data.py`。旧地图 router 的导出保留兼容，新代码直接导入共享模块。
- `app/cbd.py` 由 Tian 维护，是唯一的 CBD 判断规则；其他模块用 `require_inside()`。
  边界是 Hoddle Grid，198 个区域，来源见 `database/CBD_API.md`。
- `main.py`、`config.py`、`requirements.txt`、`database/schema.sql` 是公共文件，改动先协调。
- 每个功能新增独立测试；脚手架测试不等于功能验收完成。
- Migration：001 街道名、002 社区（mavis，已在 Supabase 执行）、003 天气、004 社区补列。
  之后的编号先协调，不修改已经执行过的 migration。
- 不记录请求体，不把坐标放进 query string。
- 不建 mood、压力评分、GPS 轨迹、积分、skin、visit 服务端表。报告不发 council 或邮件。

## 接口

所有接口使用 `Authorization: Bearer <token>`；契约见 `/docs` 和 `/openapi.json`。

| 方法/路径 | 当前状态 |
|---|---|
| GET `/api/cbd/zones` | 已实现 |
| GET `/api/zones/{zone_id}/facts` | 已实现 |
| POST `/api/routes` | 已实现；返回 `denseZoneShare` |
| POST `/api/sprout/route` | 501；CBD 外返回 422 |
| POST `/api/sprout/areas` | 501 |
| GET `/api/weather/cbd` | 已实现（mavis）；待补缓存和 `band` |
| `/api/care/...` | 已实现（mavis）；待补设备识别、限流、CBD 校验等 |

## 路线/推荐待实现

规划请求示例（额外的 mood 字段会被拒绝）：

```json
{
  "origin": {"lat": -37.8183, "lng": 144.9671},
  "preferences": {
    "canopy": "dense", "shade": "cool", "noise": "quiet",
    "allergy": "avoid", "walkingTime": 20
  }
}
```

偏好均可省略。No preference 发 null 或省略，不发字符串 none。areas 可以排除设备今天访问过的
excludedZoneIds，服务器不保存访问记录。新路线响应使用 distanceMeters（米）、
durationMinutes（分钟）、denseZoneShare（0–1）；目的地区域标识是 destination.zoneId。
steps 含 instruction、streetName、start、distanceMeters。explanation 由固定模板生成。

- CBD 全部区域作为候选；估算步行时间 = 直线距离 × 1.3 ÷ 80，不再限制 nearest precinct。
- 时间区间：5→3–7，10→8–12，15→13–17，20+→18–30，未选→5–15。
- canopy 筛选和 park share 排序；allergy=avoid 优先高花粉树最少。
- 前 3 个目的地调 Google 路线，按真实时间、花粉、canopy 选择；不满足时如实说明。
- areas 与 route 使用同一套排序。
- steps 和重新规划；复用旧 routes 的业务代码，按 access token 每 20 秒限一次。
- 仅在得到真实结果后调用 `sprout.explain_route`，不使用 AI，不虚构树木数据。

## 运行

```sh
# 在 backend 目录下
python -m pip install -r requirements-dev.txt
python -m pytest -q
black --check .
ruff check .
uvicorn app.main:app --reload --port 8080
```

Swagger: http://localhost:8080/docs。不要对共享数据库运行 `seed.py`，它会覆盖数据。
Supabase 的服务端密钥只放后端环境变量，不进前端或 Git。
