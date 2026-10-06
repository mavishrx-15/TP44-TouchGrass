# Iteration 3 后端交接

脚手架基于 CBD 提交 `2fa3ea7`。已有 CBD/facts、地图、路线和密码接口继续可用。
新业务接口明确返回 HTTP 501 `feature_not_implemented`，不能当作已实现。
代码目前仅在本地，commit/push 由 Tian 决定。

## 模块分工（剩余负责人待确认）

| 模块 | 负责人 | 文件 |
|---|---|---|
| CBD/树木数据 | Tian，已确定 | `app/cbd.py`、`routers/cbd_data.py`、`services/cbd_data.py`、`schemas/cbd.py`、`tests/test_cbd_data.py` |
| 路线/推荐 | 建议 sliu | `routers/sprout_routes.py`、`services/planning.py`、`repositories/planning.py`、`integrations/google_routes.py`、`schemas/planning.py`、现有 `routers/routes.py` |
| Sprout 固定模板 | 建议 sliu，配合 mavis | `services/sprout.py` |
| 天气 | 待确认，不默认追加给 Tian | `routers/weather.py`、`services/weather.py`、`repositories/weather.py`、`integrations/weather_provider.py`、`schemas/weather.py`、migration 002 |
| pin/照片/留言/报告 | 待确认 | `routers/pins.py`、`routers/messages.py`、`services/community.py`、`repositories/community.py`、`integrations/photo_storage.py`、`schemas/community.py`、migration 003 |

路线和社区都是大模块。先汇报已有实现，再确定剩余任务负责人和时间。
不要根据“Sprout 是固定文案”就把所有剩余后端交给一人。

## 共享代码规则

- 新模块按 router → service → repository/integration 分层，不调用另一个 router handler。
- 共享坐标在 `schemas/common.py`；地图模型在 `schemas/map_data.py`；原有密度和树木
  聚合在 `services/zone_data.py`。旧地图 router 的导出保留兼容，新代码直接导入共享模块。
- `app/cbd.py` 由 Tian 维护，是唯一覆盖规则；其他模块复用 `require_inside()`。
- CBD 默认边界仍是暂定的 156 zones，PDF 写 186，需与 mavis 确认坐标，不硬编码数量。
- `main.py` 注册、`config.py`、依赖、schema 已准备；之后公共文件变更统一协调。
- 每个功能新增独立测试；scaffold 测试不等于功能验收完成。
- migration 002 天气，003 社区；之后从 004 起协调编号，不修改已经部署的 migration。
- 不记录定位 body，不把坐标加入 query string。GET pins 的 query 只包含 zoneId。
- 不建 mood、压力评分、GPS轨迹、积分、skin、visit 服务端表。报告不发 council 或邮件。

## 已注册接口

所有接口使用原有 `Authorization: Bearer <token>`；契约见 `/docs` 和 `/openapi.json`。

| 方法/路径 | 输入 | 当前状态 |
|---|---|---|
| GET `/api/cbd/zones` | 无 | 已实现 |
| GET `/api/zones/{zone_id}/facts` | 原始 zone ID | 已实现 |
| POST `/api/sprout/route` | JSON origin + preferences | 501；CBD 外 422 |
| POST `/api/sprout/areas` | 同上，另有 excludedZoneIds、limit 1–3 | 501 |
| GET `/api/weather/now` | 无 | 501，未来无有效数据应为 503 |
| POST `/api/pins` | multipart lat、lng、accuracyM、可选 photo | 501；CBD 外 422 |
| POST `/api/pins/{pin_id}/messages` | JSON kind、body | 501 |
| GET `/api/pins?zoneId=...` | zoneId | 501 |

pin/message/query 请求附加 `X-Device-ID`，对应前端 localStorage 的随机 UUID。
它是匿名标识，不是实名账户；不得放入公共响应。真实功能启用前必须完成作者访问
校验、限流和审核权限，不能依赖客户端提供的 approval 状态。

规划请求示例（额外 mood 字段会被拒绝）：

```json
{
  "origin": {"lat": -37.8183, "lng": 144.9671},
  "preferences": {
    "canopy": "dense", "shade": "cool", "noise": "quiet",
    "allergy": "avoid", "walkingTime": 20
  }
}
```

偏好均可省略。No preference 发 null/省略，不发字符串 none。
areas 可以排除设备今天访问过的 excludedZoneIds，服务器不保存 visit。
新路线响应使用 distanceMeters（米）、durationMinutes（分钟）、denseZoneShare（0–1）；
前端在 adapter 处理，不改变旧接口 distanceKm。目的地区域标识是 destination.zoneId。
steps 含 instruction、streetName、start、distanceMeters。explanation 由固定模板生成。

## 各模块待实现

### 路线/推荐

- CBD 全候选；估算直线距离 ×1.3 ÷80，不再限制 nearest precinct。
- 时间区间：5→3–7，10→8–12，15→13–17，20+→18–30，未选→5–15。
- canopy 筛选和 park share 排序；allergy=avoid 优先高花粉树最少。
- top 3 目的地求 Google 路线，按真实时间、花粉、canopy 选择；未满足时诚实说明。
- areas 与 route 使用同一排序；定义 denseZoneShare 沿线长度占比算法。
- steps 和重新规划；复用旧 routes，按 access token 每 20 秒限一次。
- 仅在真实结果生成后调用 `sprout.explain_route`，不使用 AI 或虚构树木事实。

### 天气

- newest reading <30分钟；否则 loader，3秒超时，结果存库，失败返回503。
- >=25 warm，>=15 mild，其他 cool，包含分数温度；存储UTC观测时间。
- provider 可替换；不能用抓取时间假装观测时间。

### 社区

- 最大5MB JPEG/PNG；bounded read、解码校验、缩放、重编码去元数据。
  真正实现时添加并锁定 Pillow；目前仅装上传解析所需 multipart。
- 私有Supabase bucket；权限检查后签发短时URL，失败清理孤立照片对象。
- zone bounds 关联区域；25m内最近tree ID只存后端，不对外展示。
- pending默认；approved和本人pending可见，消息/pin/照片分别校验。
  hidden内容的作者可见性与security lead确认；禁止返回device_id和photo_path。
- body最多1000字符；message/report只保存TouchGrass；实现发布限流。
  POSTS_PER_DEVICE_PER_HOUR=10为暂定值，需security lead确认。
- security lead用Supabase Table Editor审核，暂不做管理页面。

## 数据库和验证

schema 已含 weather_readings、tree_pins、tree_messages。已有数据库人工执行002、003；
应用启动不自动迁移，本次未改共享数据库或创建Storage bucket。SQLite和PostgreSQL支持
这些SQL；不要用seed覆盖共享数据。Supabase server key只放后端环境，不进前端或Git。

从backend运行：

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
black --check .
ruff check .
uvicorn app.main:app --reload --port 8080
```

Swagger: http://localhost:8080/docs。密码配置与之前一致。

## 可转发说明

Iteration 3后端脚手架已搭好：CBD/facts可用，route/areas、天气、pin、留言接口和模型
已注册，未实现模块返回501。共享坐标和树木统计已拆出来，不用互改router。
Tian负责CBD/facts，建议sliu负责路线/Sprout；天气和社区先报已有进度再分配。
各自改模块文件和独立测试，公共配置/迁移编号提前协调。代码目前本地，提交推送后
再按提供的分支/commit合入，避免重复搭骨架。
