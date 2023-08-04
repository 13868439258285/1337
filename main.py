#!/usr/bin/env python3


from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import requests
import os
import random
import time
import threading
from requests.exceptions import ProxyError, SSLError

app = Flask(__name__)

# Lock for thread-safe access to blacklist and cooldowns files
blacklist_lock = threading.Lock()
cooldowns_lock = threading.Lock()

def get_proxy():
    """Returns a random proxy from the list of proxies."""
    with open("proxies.txt", "r") as f:
        proxies = f.readlines()
    proxy = random.choice(proxies).strip()
    return proxy

def get_user_agent():
    """Returns a random user agent from the list of user agents."""
    with open("useragents.txt", "r") as f:
        user_agents = f.readlines()
    user_agent = random.choice(user_agents).strip()
    return user_agent

def open_product_page(url, proxy, max_retry=3):
    """Opens the product page with the given URL and proxy."""
    headers = {
        "User-Agent": get_user_agent()  # Get a random user agent for each request
    }

    retry_count = 0
    while retry_count < max_retry:
        try:
            response = requests.get(url, headers=headers, proxies={"http": proxy})
            if response.status_code == 200:
                print("Product page opened successfully with proxy:", proxy)
                return True
            else:
                print("Failed to open product page with proxy:", proxy)
        except (requests.exceptions.RequestException, ProxyError, SSLError) as e:
            print("Error while opening the product page with proxy:", proxy)
            print("Exception:", e)
        retry_count += 1
        proxy = get_proxy()  # Get another proxy and retry

    print("Max retries reached. Failed to open product page with any proxy.")
    return False

def simulate_views(url, views, use_delay, delay):
    proxies = [get_proxy() for _ in range(views)]
    success_count = 0

    def bot_request(proxy):
        nonlocal success_count
        if open_product_page(url, proxy):
            success_count += 1

    with ThreadPoolExecutor(max_workers=views) as executor:
        executor.map(bot_request, proxies)

    return success_count

def check_blacklist(user_ip):
    """Check if the user's IP is blacklisted."""
    with blacklist_lock:
        with open("blacklist.txt", "r") as f:
            for line in f:
                if line.strip() == user_ip:
                    return True
    return False

def add_to_blacklist(user_ip):
    """Add the user's IP to the blacklist for 30 minutes."""
    with blacklist_lock:
        with open("blacklist.txt", "a") as f:
            f.write(user_ip + "\n")

    # Schedule the removal of the IP from the blacklist after 30 minutes
    threading.Timer(1800, remove_from_blacklist, args=[user_ip]).start()

def remove_from_blacklist(user_ip):
    """Remove the user's IP from the blacklist."""
    with blacklist_lock:
        with open("blacklist.txt", "r") as f:
            lines = f.readlines()

        with open("blacklist.txt", "w") as f:
            for line in lines:
                if line.strip() != user_ip:
                    f.write(line)

def check_cooldown(user_ip):
    """Check if the user is still in cooldown period."""
    with cooldowns_lock:
        cooldowns = {}
        current_time = time.time()

        with open("cooldowns.txt", "r") as f:
            for line in f:
                ip, timestamp = line.strip().split(",")
                cooldowns[ip] = float(timestamp)

        last_used_time = cooldowns.get(user_ip, 0)
        cooldown_time = 600  # 10 minutes cooldown

        if current_time - last_used_time < cooldown_time:
            return True

        # Update the cooldowns file with the current timestamp
        cooldowns[user_ip] = current_time

        with open("cooldowns.txt", "w") as f:
            for ip, timestamp in cooldowns.items():
                f.write(f"{ip},{timestamp}\n")

        return False

def check_whitelist(user_ip):
    """Check if the user's IP is whitelisted."""
    with open("whitelist.txt", "r") as f:
        for line in f:
            if line.strip() == user_ip:
                return True
    return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_ip = request.remote_addr

        if check_whitelist(user_ip):
            # If the user is whitelisted, skip cooldown and blacklist checks
            url = request.form.get('url')
            views = int(request.form.get('views'))
            use_delay = 'use_delay' in request.form
            delay = int(request.form.get('delay')) if use_delay else 0

            print(f"Botting URL: {url} with {views} views.")
            print(f"Use Delay: {use_delay}, Delay: {delay}")

            success_count = simulate_views(url, views, use_delay, delay)
            return jsonify({'status': 'success', 'views': success_count})

        elif check_blacklist(user_ip):
            # If the user is blacklisted, return an error
            return jsonify({'status': 'error', 'message': 'You are blacklisted.'})

        elif check_cooldown(user_ip):
            # If the user is on cooldown, return an error
            return jsonify({'status': 'error', 'message': 'Cooldown period not over.'})
        
        else:
            # Add the user to the blacklist and set a cooldown
            add_to_blacklist(user_ip)
            return jsonify({'status': 'error', 'message': 'You are blacklisted.'})

    else:
        return render_template('homepage.html')

@app.route('/ebay.html')
def ebay():
    return render_template('ebay.html')

@app.route('/Us.html')
def Us():
    return render_template('Us.html')

@app.route('/tiktok.html')
def tiktok():
    return render_template('tiktok.html')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=1337)
