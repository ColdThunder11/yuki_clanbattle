# Yuki Clanbattle
Yuki源自公主连结里的角色 [雪](https://pcredivewiki.tw/Character/Detail/%E9%9B%AA)   
Princess Connect Re:Dive clanbattle bot based on NoneBot2   
适用于公主连结的公会战管理机器人插件，基于 NoneBot2 ，同时支持新旧两种会战模式
### 注意：即使插件完全兼容 NoneBot2 ，由于插件功能相对独立性并且需要挂载根目录，不建议将其作为其他机器人的插件加载，插件也不会上传到 PyPI 和 NoneBot 商店，建议用单独的 NoneBot2 实例运行本插件
# 平台支持
OneNot V11: `nonebot-adapter-onebot`  
~~Telegram~~  
# 安装
1. 在开始安装插件前，请确保你已安装并部署 [NoneBot2](https://github.com/nonebot/nonebot2)，并已成功使 NoneBot 响应目标平台的指令  
2. 在Bot插件目录执行命令`git clone https://github.com/ColdThunder11/yuki_clanbattle_web.git` 或 手动[下载mater分支源码](https://github.com/OREOCODEDEV/yuki_clanbattle/archive/refs/heads/master.zip)并解压到Bot插件目录  
3. 前往[前端项目Action页面](https://github.com/ColdThunder11/yuki_clanbattle_web/actions)，并在最新 workflow 页面底部的 Artifacts 标签中下载最新构建  
4. 解压上一步骤下载的文件至插件根目录`dist`文件夹中，此时该插件的部分文件树结构应为：  
    ```
    .
    ├── docs
    ├── dist
    │   ├── css
    │   ├── fonts
    │   ├── img
    │   ├── js
    │   ├── index.html
    │   └── favicon.ico
    ├── __init__.py
    └── README.md
    ```
5. 安装项目所需依赖  
peewee: `pip install peewee`  
6. 将插件根目录的`config.example.json`文件重命名为`config.json`，并修改其中的配置项，使其符合你的设置，其中部分配置项及说明如下：  
    ```
    web_url: 此服务器的公开地址
    disable_private_message: 禁用私聊回复（不影响私聊接收功能）
    enable_anti_msg_fail: 规避风控模式，会修改部分回复内容以降低消息发送失败概率
    db_salt: 用户 Web 密码存储加密密钥
    boss_info: BOSS相关配置
        # 下列每个设置项均以 日服(jp) 台服(tw) 国服(cn) 作为区分
        boss: 各个阶段的各个BOSS血量
        cyle: 各个阶段的周目数值
    ```
7. 现在你已经完成了该插件所有的安装，尝试重新运行 NoneBot2 加载该插件即可，在需要使用会战机器人的群中发送“帮助”以获得帮助页面链接  
8. （可选）如有需要，你可按照下列示例配置 Nginx 反代：
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
# 其它
部署指南：在线等pr，任何有关询问如何部署的issue均不会回答   
Todo list:
- [ ] Telegram支持
- [ ] 部署文档（等PR）
- [ ] ~~Discord支持~~

特别感谢：  
@[Lancercmd](https://github.com/Lancercmd) 的优妮（指抄了部分正则）

~~[请我喝杯奶茶](https://afdian.net/a/coldthunder11)~~