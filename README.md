# 水下六足机器人协作仓库

本仓库用于河海大学智能科学与技术团队与机电团队协同完成水下六足机器人项目。当前阶段只聚焦：

1. 在 MuJoCo 中完成机器人模型可视化；
2. 实现基础关节控制与平面站立/行走；
3. 固化机械模型与控制算法之间的接口；
4. 为“平面—墙壁切换”沉淀可导出的控制参数格式。

本阶段跳过 ROS。所有可交付成果必须能够通过仓库中的文件复现，不能只存在于个人电脑或聊天记录中。

## 快速入口

- [项目章程与分工](docs/01_project_charter.md)
- [机械—控制接口协议](docs/02_interface_contract.md)
- [里程碑与验收标准](docs/03_milestones_acceptance.md)
- [异地协作流程](docs/04_remote_workflow.md)
- [模型参数合同](config/model_contract.yaml)
- [控制序列模板](config/control_sequence_template.yaml)
- [任务看板](PROJECT_BOARD.md)
- [决策记录](docs/decisions/0001_scope_and_conventions.md)

## 推荐目录

```text
assets/                 机电院交付的网格、纹理等资源
config/                 双方共同维护的接口与控制参数
docs/                   需求、协议、会议纪要、决策记录
models/                 MuJoCo MJCF 模型与场景
src/                    可视化、控制、轨迹与数据记录代码
tests/                  模型与控制接口自动检查
runs/                   本地仿真输出（默认不提交大文件）
```

## 协作原则

- 机电院对几何、质量、惯量、关节极限和吸附机构物理参数负责。
- 智能院对 MuJoCo 场景、控制器、步态、状态机和参数导出负责。
- 双方共同对 `config/model_contract.yaml` 的准确性负责；修改接口时必须同步更新该文件。
- 每项工作通过任务卡进入看板；每次接口变化通过决策记录确认。
- 主分支只保存可运行、可复现的成果；阶段成果用标签冻结。

## 第一周启动顺序

1. 机电院补全 `config/model_contract.yaml`，提供轻量化 STL/OBJ 和装配基准说明。
2. 智能院据此建立 `models/robot.xml` 和最小地面场景。
3. 双方联合完成 M0 模型接口评审。
4. 智能院实现关节位置控制、站立姿态和运行日志。
5. 双方按 M1 验收标准录制同一版本的仿真结果。


