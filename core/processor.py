import sys
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import re
from typing import Optional
from playwright.async_api import async_playwright


class TwitterLinkProcessor:
    """Twitter链接处理工具类, 用于处理短链接和提取图片"""
    
    @staticmethod
    async def ensure_playwright_browser():
        """
        确保 Playwright Chromium 浏览器已安装
        """
        try:
            import playwright
            from playwright.async_api import async_playwright

            # 尝试启动浏览器来检查是否已安装
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch()
                    await browser.close()
                    return
                except Exception:
                    pass

            # 如果启动失败，安装浏览器
            logger.info("正在安装 Playwright Chromium...")
            import subprocess
            subprocess.run(['playwright', 'install', 'chromium'], check=True)
            logger.info("Playwright Chromium 安装完成")

        except Exception as e:
            logger.error(f"安装 Playwright Chromium 时出错: {str(e)}")
            raise

    @staticmethod
    async def extract_image_with_playwright(url: str) -> Optional[str]:
        """
        使用 playwright 处理动态加载的页面并提取图片链接
        
        Args:
            url: 要处理的URL
            
        Returns:
            Optional[str]: 提取到的图片URL，如果未找到则返回None
        """
        # 确保浏览器已安装
        await TwitterLinkProcessor.ensure_playwright_browser()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # 设置超时时间
                page.set_default_timeout(30000)

                # 访问URL
                await page.goto(url)

                # 等待图片元素加载
                await page.wait_for_selector('img')

                # 获取所有图片元素
                images = await page.query_selector_all('img')
                for img in images:
                    src = await img.get_attribute('src')
                    if src and "media" in src:  # 过滤 Twitter 图片链接
                        logger.info(f"找到图片链接: {src}")
                        await browser.close()
                        return src

                logger.info("未能找到图片链接。")
                return None

            except Exception as e:
                logger.error(f"Playwright 出现错误: {e}")
                return None
            finally:
                await browser.close()

    @staticmethod
    def extract_image_with_selenium(url: str) -> Optional[str]:
        """
        使用 Selenium 处理动态加载的页面并提取图片链接
        
        Args:
            url: 要处理的URL
            
        Returns:
            Optional[str]: 提取到的图片URL，如果未找到则返回None
        """
        try:
            # 设置 Chrome 浏览器选项
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # 无头模式
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument(
                "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )

            # 启动浏览器
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            # 打开目标 URL
            driver.get(url)

            # 等待页面加载完成
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'img'))
            )

            # 尝试从 <img> 提取图片链接
            img_elements = driver.find_elements(By.TAG_NAME, 'img')
            for img in img_elements:
                image_url = img.get_attribute('src')
                if image_url and "media" in image_url:  # 过滤 Twitter 图片链接
                    logger.info(f"通过 <img> 找到图片链接: {image_url}")
                    driver.quit()
                    return image_url

            logger.info("未能找到图片链接。")
            driver.quit()
            return None
        except Exception as e:
            logger.error(f"Selenium 出现错误: {e}")
            return None

    @staticmethod
    def extract_short_url(tweet_text: str) -> str:
        """
        从推文内容中提取Twitter短链接

        Args:
            tweet_text: 推文内容

        Returns:
            str: 找到的短链接，如果没有找到返回空字符串
        """
        # 匹配形如 https://t.co/xxxxx 的链接
        pattern = r'https://t\.co/[a-zA-Z0-9]+'
        match = re.search(pattern, tweet_text)

        if match:
            return match.group(0)
        return ''

    @staticmethod
    async def extract_image_url(tweet_text: str) -> str:
        """
        从推文中提取图片URL
        
        Args:
            tweet_text: 推文内容
            
        Returns:
            str: 提取到的图片URL，如果未找到则返回空字符串
        """
        short_url = TwitterLinkProcessor.extract_short_url(tweet_text)
        if not short_url:
            return ''
            
        logger.info(f"找到短链接: {short_url}")
        
        if sys.platform == "darwin":
            image_url = TwitterLinkProcessor.extract_image_with_selenium(short_url)
        else:
            image_url = await TwitterLinkProcessor.extract_image_with_playwright(short_url)
            
        if image_url:
            logger.info(f"图片链接: {image_url}")
            return image_url
        return ''
    
    @staticmethod
    async def expand_short_url(short_url: str) -> str:
        """
        展开Twitter短链接为原始URL
        
        Args:
            short_url: Twitter短链接
            
        Returns:
            str: 展开后的URL，如果失败则返回原短链接
        """
        if not short_url.startswith('https://t.co/'):
            return short_url
            
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(short_url, allow_redirects=False) as response:
                    if response.status in (301, 302):
                        location = response.headers.get('Location')
                        if location:
                            logger.info(f"短链接 {short_url} 已展开为 {location}")
                            return location
            
            logger.warning(f"无法展开短链接: {short_url}")
            return short_url
        except Exception as e:
            logger.error(f"展开短链接时出错: {str(e)}")
            return short_url

