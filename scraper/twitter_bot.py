import tweepy
import json
from datetime import datetime

# Twitter API設定
def init_twitter_api(config):
    auth = tweepy.OAuthHandler(
        config["twitter"]["api_key"],
        config["twitter"]["api_secret"]
    )
    auth.set_access_token(
        config["twitter"]["access_token"],
        config["twitter"]["access_secret"]
    )
    return tweepy.API(auth)

# 設定読み込み（実際にはscraper.pyと共有する）
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "twitter": {
                "api_key": "YOUR_API_KEY",
                "api_secret": "YOUR_API_SECRET",
                "access_token": "YOUR_ACCESS_TOKEN",
                "access_secret": "YOUR_ACCESS_SECRET"
            }
        }

# 通知をツイート
def tweet_notification(message):
    config = load_config()
    try:
        api = init_twitter_api(config)
        api.update_status(message)
        print(f"Tweet sent: {message}")
        return True
    except Exception as e:
        print(f"Error sending tweet: {e}")
        return False

# 通知データを読み込んでツイート
def process_notifications():
    try:
        with open("price_history.json", "r", encoding="utf-8") as f:
            db = json.load(f)
        
        # 未ツイートの通知をチェック
        for notification in db.get("notifications", []):
            if not notification.get("tweeted", False):
                if tweet_notification(notification["message"]):
                    notification["tweeted"] = True
        
        # 更新したデータを保存
        with open("price_history.json", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
                
    except Exception as e:
        print(f"Error processing notifications: {e}")

if __name__ == "__main__":
    process_notifications()