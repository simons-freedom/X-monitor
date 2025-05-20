from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

def get_tweet_details(url):
    """
    通过浏览器模拟获取推文详细信息
    
    :param url: 推文链接（例如：https://x.com/realDonaldTrump/status/1924523182909747657）
    :return: 结构化推文数据字典
    """
    with sync_playwright() as p:
        # 启动Chromium浏览器（无头模式）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 访问目标页面
            page.goto(url, timeout=60000)
            time.sleep(3)  # 等待动态内容加载
            
            # 获取页面HTML内容
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            author_info = extract_author(soup)
            
            # 解析关键数据
            return {
                "content": extract_content(soup),  # 修改字段名
                "name": author_info.get("name"),
                "username": author_info.get("username"),
                "timestamp": extract_time(soup),
            }
        finally:
            browser.close()

# 辅助解析函数
def extract_content(soup):
    # 从title标签提取推文内容（格式：作者名 on X: "内容" / X）
    try:
        title_tag = soup.title
        if not title_tag or not title_tag.string:
            return None
            
        title_text = title_tag.string.strip()
        if ": " in title_text and " / X" in title_text:
            # 分割出核心内容部分
            content_part = title_text.split(": ", 1)[1].rsplit(" / X", 1)[0]
            # 去除首尾可能的引号
            return content_part.strip('"')
    except (AttributeError, IndexError, ValueError):
        pass
    return None

def extract_author(soup):
    # 提取作者信息
    import re
    
    author_section = soup.find('div', {'data-testid': 'User-Name'})
    if not author_section:
        return None
    
    # 使用正则表达式提取username
    username_pattern = r'@([A-Za-z0-9_]+)'
    text_content = author_section.get_text()
    
    # 在用户信息区块中查找首个@符号后的用户名
    username_match = re.search(username_pattern, text_content)
    
    return {
        "name": author_section.find('span').text if author_section.find('span') else None,
        "username": username_match.group(1) if username_match else None
    } if author_section else {"name": None, "username": None}  # 保证始终返回字典

def extract_time(soup):
    # 提取时间戳
    time_tag = soup.find('time')
    return time_tag['datetime'] if time_tag else None



# 使用示例
if __name__ == "__main__":
    tweet_url = "https://x.com/realDonaldTrump/status/1923432648103333919"
    result = get_tweet_details(tweet_url)
    
    print("推文详细信息：")
    for key, value in result.items():
        print(f"{key.upper()}: {value}")