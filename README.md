# Yuki Clanbattle
Yuki源自公主连结里的角色 [雪](https://pcredivewiki.tw/Character/Detail/%E9%9B%AA)   
Princess Connect Re:Dive clanbattle bot based on nonebot2   
适用于公主连结的公会战管理机器人插件，基于nonebot2，同时支持新旧两种会战模式
### 注意：即使插件完全兼容nonebot2，由于插件功能相对独立性并且需要挂载根目录，不建议将其作为其他机器人的插件加载，插件也不会上传到pypi和nonebot商店，建议用单独的nonebot2实例运行本插件

支持平台：Onebot v11、~~Telegram在路上了~~   

需求：安装好nonebot2(2.0.0b4+)和onebot适配器，安装peewee，去[前端项目Action页面](https://github.com/ColdThunder11/yuki_clanbattle_web/actions)Artifacts内下载最新的构建并解压到插件根目录的dist文件夹内，即index.html位于./dist/index.html。   

Nginx反代配置文件示例：
```
        location /api
        {
            proxy_pass http://127.0.0.1:port;
            proxy_set_header X-Real-IP $remote_addr;
        }
        location / {
            root 前端文件目录;
            try_files $uri $uri/ /index.html;
        }
```

部署指南：在线等pr，任何有关询问如何部署的issue均不会回答   

Todo list:   
- [ ] Telegram支持
- [ ] 部署文档（等PR）
- [ ] ~~Discord支持~~

特别感谢：[Lancercmd](https://github.com/Lancercmd)的优妮（指抄了部分正则）

~~[请我喝杯奶茶](https://afdian.net/a/coldthunder11)~~