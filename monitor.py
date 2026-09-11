import os
import sys
from urllib.parse import quote

import requests
from playwright.sync_api import sync_playwright

PRODUCT_URL = os.environ.get("PRODUCT_URL", "").strip()
BARK_URL = os.environ.get("BARK_URL", "").strip()

# 命中即视为"还没货/不能买"——根据商品页实际文案调整
OUT_KEYWORDS = [
    "补货中",
    "库存不足",
    "暂时缺货",
    "已售罄",
    "该商品已下架",
    "即将上市",
    "到货通知",
    "商品已失效",
]

# 命中且没命中上面的关键词，即视为"可以买了"——根据商品页实际文案调整
IN_KEYWORDS = [
    "立即购买",
    "马上抢",
    "去支付",
    "立即秒杀",
    "拼单购买",
]

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)


def fetch_page_text(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=MOBILE_UA, viewport={"width": 390, "height": 844})
        page.goto(url, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(2000)
        text = page.inner_text("body")
        browser.close()
        return text


def push_bark(title: str, body: str) -> None:
    if not BARK_URL:
        print("未设置 BARK_URL，跳过推送")
        return
    base = BARK_URL.rstrip("/")
    url = f"{base}/{quote(title)}/{quote(body)}?sound=alarm&level=critical&isArchive=1"
    try:
        requests.get(url, timeout=10)
        print("已推送到 Bark")
    except Exception as e:  # noqa: BLE001
        print(f"推送失败: {e}")


def main() -> None:
    if not PRODUCT_URL:
        print("未设置 PRODUCT_URL，退出")
        sys.exit(1)

    try:
        body_text = fetch_page_text(PRODUCT_URL)
    except Exception as e:  # noqa: BLE001
        print(f"抓取页面失败: {e}")
        sys.exit(0)  # 单次失败不算错误，等下一轮重试

    out_hit = any(k in body_text for k in OUT_KEYWORDS)
    in_hit = any(k in body_text for k in IN_KEYWORDS)

    print(f"out_hit={out_hit}  in_hit={in_hit}")

    if not out_hit and in_hit:
        print("检测到商品可以购买了！")
        push_bark("🔥商品补货/开售了", "快去拼多多下单付款！")
    else:
        print("暂时还不能买，等待下一轮检测")


if __name__ == "__main__":
    main()
