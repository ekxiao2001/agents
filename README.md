## 快速开始
### 准备 sandbox 镜像
```bash
# 基础镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-base:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-base:latest agentscope/runtime-sandbox-base:latest

# GUI镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-gui:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-gui:latest agentscope/runtime-sandbox-gui:latest

# 文件系统镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-filesystem:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-filesystem:latest agentscope/runtime-sandbox-filesystem:latest

# 浏览器镜像
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest && docker tag agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-browser:latest agentscope/runtime-sandbox-browser:latest
```

### 一键部署容器
```bash
docker-compose up -d --build
```
**Note**: 
初次启动时需要等待UV安装依赖，可能需要一些时间。