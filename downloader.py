""" Download image according to given urls and automatically rename them in order. """
# -*- coding: utf-8 -*-
# author: Yabin Zheng
# Email: sczhengyabin@hotmail.com

from __future__ import print_function

import shutil
import imghdr
import os
import concurrent.futures
import requests
import random
import logging
import string
import cv2
import numpy as np


DEFAULT_FORMAT_FILTER = ["jpg", "jpeg", "png", "bmp", "webp"]

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Proxy-Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, sdch",
    # 'Connection': 'close',
}


def download_image(image_url, dst_dir, file_name, timeout=20, proxy_type=None, 
                   proxy=None, format_filter=DEFAULT_FORMAT_FILTER, min_dim=(0,0)):
    """
        2022/07/19: 
            Add: Return the status
        2022/07/20:
            Add: Customizable image type filter
            Add: Check image size before saving
    """
    proxies = None
    if proxy_type is not None:
        proxies = {
            "http": proxy_type + "://" + proxy,
            "https": proxy_type + "://" + proxy
        }

    response = None
    file_path = os.path.join(dst_dir, file_name)
    try_times = 0
    while True:
        try:
            try_times += 1
            response = requests.get(
                image_url, headers=headers, timeout=timeout, proxies=proxies)

            with open(file_path, 'wb') as f:
                f.write(response.content)
            response.close()

            # Determine the image format
            file_type = imghdr.what(file_path)
            if file_type not in format_filter:
                os.remove(file_path)
                return False
                # print("## Err:  {}".format(image_url))

            # Determine the image size if needed
            if min_dim[0] > 0 and min_dim[1] > 0:
                try:
                    im = np.asarray(bytearray(response.content), dtype="uint8")
                    im = cv2.imdecode(im, cv2.IMREAD_COLOR)
                    height, width = im.shape[:2]
                    if width < min_dim[0] or height < min_dim[1]:
                        os.remove(file_path)
                        return False
                except Exception as e:
                    err_msg = f'Unable to determine the image size for {image_url}'
                    try:
                        logging.error(err_msg)
                    except:
                        # When logging is not configured
                        print(err_msg)

            new_file_name = "{}.{}".format(file_name, file_type)
            new_file_path = os.path.join(dst_dir, new_file_name)
            shutil.move(file_path, new_file_path)
            # print("## OK:  {}  {}".format(new_file_name, image_url))
            return True
            # break
        except Exception as e:
            if try_times < 3:
                continue
            if response:
                response.close()
            # print("## Fail:  {}  {}".format(image_url, e.args))
            return False
            # break


def download_images(image_urls, dst_dir, file_prefix=None, concurrency=50, timeout=20, 
                    proxy_type=None, proxy=None, 
                    format_filter=DEFAULT_FORMAT_FILTER,
                    min_dim=(0,0)):
    """
    Download image according to given urls and automatically rename them in order.
    :param timeout:
    :param proxy:
    :param proxy_type:
    :param image_urls: list of image urls
    :param dst_dir: output the downloaded images to dst_dir
    :param file_prefix: if set to "img", files will be in format "img_xxx.jpg". 
                        if set to None, a random name will be generated.
    :param concurrency: number of requests process simultaneously
    :return: the number of successful downloads
    """
    """
        2022/07/20:
            Add: Support empty file prefix
    """
    success_downloads = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_list = list()
        count = 1
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for image_url in image_urls:
            if file_prefix is not None:
                file_name = file_prefix + "_" + "%04d" % count
            else:
                file_name = ''.join([random.choice(string.ascii_letters) for i in range(8)])
            future_list.append(executor.submit(
                                download_image, image_url, dst_dir, file_name, timeout, proxy_type, proxy, 
                                format_filter, min_dim))
            count += 1
        concurrent.futures.wait(future_list, timeout=180)

        # Count the number of successful downloads
        for future in future_list:
            if future.result():
                success_downloads += 1

    return success_downloads

     