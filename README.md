# X-monitor 项目介绍

## 项目概述
X-monitor 是一个基于 Twitter (X) 的实时监控系统，能够自动基于大模型分析推文内容、识别潜在MEME加密货币交易机会，并支持自动执行链上交易。

## 主要功能
1. **推文监控**：通过 API 接收 Twitter 推文数据
2. **AI 分析**：使用大模型分析推文内容，识别潜在代币信息
3. **代币搜索**：自动搜索代币的市场数据（价格、流动性等）
4. **交易执行**：支持自动在以太坊/BSC/Solana 链上执行代币交易
5. **通知系统**：通过钉钉机器人发送实时通知


## 项目结构
X-monitor/
├── abi/                    # 智能合约 ABI
│   ├── erc20.json          # ERC20 代币合约 ABI
│   └── router.json         # DEX 路由合约 ABI
├── analyzer.py             # AI 分析模块
├── config.py               # 配置管理
├── data_def.py             # 数据结构定义
├── dingding.py             # 钉钉机器人封装
├── notice.py               # 通知系统
├── processor.py            # 推文内容处理器
├── trader.py               # 链上交易模块
├── x_monitor.py            # 主服务入口
├── .env                    # 环境变量配置
└── requirements.txt        # 依赖列表


## 快速开始
1. 安装依赖：
```bash
pip install -r requirements.txt
playwright install chromium

2. 配置环境变量
复制 .env.example 为 .env 并填写您的配置：
- LLM_API_KEY: OpenAI 兼容 API 密钥, model需要可以支持图片分析
- DINGTALK_TOKEN/SECRET: 钉钉机器人凭证
- 区块链相关配置（私钥、RPC 等）

3. 订阅X推送服务
该项目订阅的为apidance的推送服务, 相关服务可参考 https://alpha.apidance.pro/welcome  订阅时选择自定义Hook推送地址,推送到自己的服务器. eg:  http://188.1.1.99:9999/post/tweet

4. 启动服务
python x_monitor.py


5. 测试
POST  /post/tweet

```json
{
    "push_type": "new_tweet",
    "title": "[GROUP] Elon Musk 发布新推文",
    "content": "The Return of the King https://t.co/CjaRrXH7k9",
    "user": {
        "id": 44196397,
        "id_str": "44196397",
        "name": "Elon Musk",
        "screen_name": "elonmusk",
        "location": "",
        "description": "",
        "protected": false,
        "followers_count": 219972879,
        "friends_count": 1092,
        "listed_count": 161564,
        "created_ts": 1243973549,
        "favourites_count": 135600,
        "verified": false,
        "statuses_count": 74875,
        "media_count": 3642,
        "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png",
        "profile_image_url_https": "https://pbs.twimg.com/profile_images/1893803697185910784/Na5lOWi5_normal.jpg",
        "profile_banner_url": "https://pbs.twimg.com/profile_banners/44196397/1739948056",
        "is_blue_verified": false,
        "verified_type": "",
        "pin_tweet_id": "1902141220505243751",
        "ca": "",
        "has_ca": false,
        "init_followers_count": 155506033,
        "init_friends_count": 420,
        "first_created_at": 0,
        "updated_at": 1742441817
    },
    "tweet": {
        "id": 60393895,
        "tweet_id": "1902564961307488532",
        "user_id": "44196397",
        "media_type": "photo",
        "text": "https://t.co/zBa4F6YApG",
        "medias": [
            "https://pbs.twimg.com/ext_tw_video_thumb/1902520094779179008/pu/img/GAxFkN4qowT1vGA_.jpg"
        ],
        "urls": null,
        "is_self_send": true,
        "is_retweet": false,
        "is_quote": false,
        "is_reply": false,
        "is_like": false,
        "related_tweet_id": "",
        "related_user_id": "",
        "publish_time": 1742441809,
        "has_deleted": false,
        "last_deleted_check_at": 0,
        "ca": "",
        "has_ca": false,
        "created_at": 1742441821,
        "updated_at": 1742441821
    }
}
```

## 效果展示
![应用启动](images/start.png) 
![AI分析结果](images/analys1.png)
![AI分析结果](images/analys2.png)
![AI分析结果](images/analys3.png)
![钉钉通知](images/dingding.jpg)