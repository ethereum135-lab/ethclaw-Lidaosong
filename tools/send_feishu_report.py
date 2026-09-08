#!/usr/bin/env python3
"""发送复盘报告到飞书给老李"""
import os, json
from lark_oapi import Client
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
HOME_CHANNEL = os.environ.get("FEISHU_HOME_CHANNEL", "")

if not APP_ID or not APP_SECRET or not HOME_CHANNEL:
    print("❌ 缺少FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_HOME_CHANNEL环境变量")
    exit(1)

client = Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()

def send_message(text_content):
    request_body = (
        CreateMessageRequestBody.builder()
        .receive_id(HOME_CHANNEL)
        .msg_type("text")
        .content(json.dumps({"text": text_content}, ensure_ascii=False))
        .build()
    )
    request = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(request_body)
        .build()
    )
    resp = client.im.v1.message.create(request)
    if resp.code == 0:
        print(f"✅ 飞书投递成功: message_id={resp.data.message_id}")
    else:
        print(f"❌ 飞书投递失败: code={resp.code} msg={resp.msg}")

if __name__ == "__main__":
    import sys
    content = sys.stdin.read().strip()
    if content:
        send_message(content)
    else:
        print("❌ 无内容输入")
