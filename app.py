import requests
import pymysql
from bs4 import BeautifulSoup

# 讀取 set.txt 設定
config = {}

with open('set.txt', 'r', encoding='utf-8') as file:
    for line in file:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            config[key] = value

# 取得爬蟲相關設定
urlSet = config.get("urlSet", "")
find_value = config.get("find", "")

find_tag = ""
find_id = ""
find_class = []

if find_value:
    parts = find_value.split()
    for part in parts:
        if '#' in part:
            tag_id = part.split('#')
            find_tag = tag_id[0] if tag_id[0] else find_tag
            find_id = tag_id[1]
        elif '.' in part:
            tag_class = part.split('.')
            find_tag = tag_class[0] if tag_class[0] else find_tag
            find_class = tag_class[1:]

print("  網站擷取標籤為:", find_tag)
print("  此標籤的 id 為:", find_id)
print("  此標籤的 class 為:", find_class)

if not urlSet:
    print("未在設定檔中找到 urlSet。")
    exit()

# 輸入 p_id
p_id = input("請輸入產品 ID (p_id)：")
search_term = input("請輸入要搜尋的內容：")
url = f"{urlSet}{search_term}"
print("  目標 URL:", url)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
}
response = requests.get(url, headers=headers)
response.encoding = 'utf-8'

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')

    # 遍歷所有標籤，處理 data-srcset 和 data-src
    for tag in soup.find_all():
        if 'data-srcset' in tag.attrs:
            tag['src'] = tag['data-srcset']
            del tag['data-srcset']
        elif 'data-src' in tag.attrs:
            tag['src'] = tag['data-src']
            del tag['data-src']

    # 檢查 ID 是否存在
    all_ids = [tag.get("id") for tag in soup.find_all(id=True)]
    
    if find_id and find_id not in all_ids:
        print(f"找不到 ID {find_id}，可能是動態生成的！")

    # 先找 ID，然後找內部的 class
    parent_div = soup.find(find_tag, id=find_id) if find_id else soup

    if parent_div:
        content = parent_div.find(find_tag, class_=lambda c: c and all(cls in c.split() for cls in find_class))
    else:
        content = None

    if content:
        content_text = str(content)

        with open(f'{search_term}.txt', 'w', encoding='utf-8') as file:
            file.write(content_text)
        print(f"找到內容並儲存為 {search_term}.txt")

        # **從 set.txt 讀取資料庫設定**
        db_host = config.get("db_host", "localhost")
        db_user = config.get("db_user", "root")
        db_password = config.get("db_password", "")
        db_name = config.get("db_name", "")
        db_charset = config.get("db_charset", "utf8")

        # 連接 MySQL 資料庫
        try:
            connection = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                charset=db_charset
            )
            cursor = connection.cursor()

            # 更新 product 表
            sql = "UPDATE product SET p_content=%s WHERE p_id=%s"
            cursor.execute(sql, (content_text, p_id))
            connection.commit()
            print(f"成功更新 p_id={p_id} 的 p_content 欄位")

        except pymysql.MySQLError as e:
            print("資料庫錯誤:", e)
        finally:
            cursor.close()
            connection.close()
    else:
        print("未找到指定內容")
else:
    print(f"請求失敗，狀態碼：{response.status_code}")
