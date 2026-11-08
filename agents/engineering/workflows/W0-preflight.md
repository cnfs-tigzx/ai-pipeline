# workflow 名称：环境预检（增强版）
description: 检测代理/VPN、网速、GitHub、火山方舟、DockerHub、NPM、OrbStack，输出完整网络报告，支持缓存
steps:
  - name: 执行预检脚本
    run: ./scripts/preflight-check.sh
  - name: 读取报告
    read: ./preflight-report.md
  - name: 输出报告并判断
    message: 将完整markdown报告展示给用户；Act模式下如果存在❌异常，暂停任务，询问是否强制继续