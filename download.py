#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import multiprocessing
import os
import re
import shutil
from typing import Dict, Generator, List, Tuple

import requests

from console import VideoConsole
from util import extract_host

SUCCESS = "success"
FAILED = "failed"


class VideoDownloader(object):
    def __init__(self, videos: List[Dict], *, output: str, headers: Dict = None) -> None:
        self.videos = videos
        self.output = output
        self.headers = headers
        self.default_timeout = 60

    def download(self):
        for video in self.videos:
            guid = video["guid"]
            url = f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}&client=flash&im=0&vn=2049&wlan="
            out_path = os.path.join(self.output, guid)
            os.makedirs(out_path, exist_ok=True)
            try:
                resp = requests.get(url, headers=self.headers, timeout=self.default_timeout)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding
                    json_data = json.loads(resp.text)
                    m3u8_url = json_data.get("hls_url")
                    self.fetch_m3u8(m3u8_url, out_path=out_path, file_name=video["title"])
            except Exception as e:
                raise Exception(f"Extract video information error:{e}")

    def fetch_m3u8(self, m3u8_url: str, out_path: str = None, file_name: str = None) -> None:
        try:
            resp = requests.get(m3u8_url, headers=self.headers, timeout=self.default_timeout)
            if resp.status_code == 200:
                lines = resp.text.splitlines()
                m3u8_files = [line for line in lines if line.endswith(".m3u8")]

                host = extract_host(m3u8_url)
                hd_m3u8_url = host + m3u8_files[0] if m3u8_files else None
                if hd_m3u8_url is not None:
                    response = requests.get(hd_m3u8_url, headers=self.headers, timeout=self.default_timeout)
                    if response.status_code == 200:
                        lines = response.text.splitlines()
                        ts_files = [line for line in lines if line.endswith(".ts")]
                        # parallel download
                        tasks = []
                        hd_m3u8_url = hd_m3u8_url[:hd_m3u8_url.rfind('/') + 1]
                        for ts_file in ts_files:
                            p = multiprocessing.Process(target=self.fetch_ts, args=(out_path, hd_m3u8_url+ts_file,))
                            tasks.append(p)
                            p.start()
                        for p in tasks:
                            p.join()
                        self.merge(ts_files, sub_dir=out_path, file_name=file_name)
        except Exception as e:
            raise Exception(f"Fetch m3u8 error:{e}")

    def merge(self, ts_files: List[str], sub_dir: str = None, file_name: str = None):
        guid = os.path.basename(sub_dir)
        file_path = os.path.join(sub_dir, f"{guid}.txt")
        new_name = os.path.join(sub_dir, f"{file_name}.mp4")
        try:
            # write ts_files to text file
            with open(file_path, "w+") as f:
                for ts_file in ts_files:
                    f.write("file '" + ts_file + "'\n")

            tmp = os.path.join(sub_dir, f"{guid}.mp4")
            # merge ts_files to mp4
            result = os.system(f"ffmpeg -f concat -safe 0 -i {file_path} -c copy {tmp} > NUL 2>&1")
            if result != 0:
                raise Exception("Failed to merge ts files into mp4.")
            # rename mp4
            os.replace(tmp, new_name)
        except Exception as e:
            raise e
        finally:
            # clean all ts files and f'{guid}.txt'
            try:
                # self.status.info(f"Removing file {file_path}")
                os.remove(file_path)
                for ts_file in ts_files:
                    # self.status.info(f"Removing file {os.path.join(sub_dir, ts_file)}")
                    os.remove(os.path.join(sub_dir, ts_file))
                # move to parent dir
                shutil.move(new_name, self.output)
                shutil.rmtree(sub_dir)
            except Exception as cleanup_error:
                # self.status.error(f"Error during cleanup: {cleanup_error}")
                raise cleanup_error

    def fetch_ts(self, sub_dir: str, ts_url: str) -> None:
        file_name = os.path.basename(ts_url)
        file_path = os.path.join(sub_dir, file_name)
        try:
            resp = requests.get(ts_url, headers=self.headers, stream=True)
            if resp.status_code == 200:
                with open(file_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            # self.status.error(f"Fetch ts file {file_name} error:{e}")
            raise e


class VideoCrawler(object):

    def __init__(self, url: str, output: str, console:VideoConsole) -> None:
        self.original_url = url
        self.scheme_host = extract_host(url)
        self.output = output
        self.guid = None
        self.video_id = None
        self.channel_id = None
        self.video_list = []
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Host": "tv.cctv.com",
            "Sec-Ch-Ua": '"Chromium";v="128", "NotA=Brand";v="24", "Microsoft Edge";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0",
        }
        self.console = console

    def find_video(self):
        try:
            resp = requests.get(self.original_url, headers=self.headers)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                content = resp.text
                javascript_variable_pattern = r"var\s+(\w+)\s*=\s*['\"](.*?)['\"];"
                javascript_vars = re.findall(javascript_variable_pattern, content)
                video_info = {
                    "url": self.original_url,
                }
                for var_name, var_value in javascript_vars:
                    match var_name:
                        case "guid":
                            self.guid = var_value
                            video_info["guid"] = var_value
                        case "itemid1":
                            self.video_id = var_value
                            video_info["vid"] = var_value
                        case "commentTitle":
                            video_info["title"] = var_value
                        case "column_id":
                            self.channel_id = var_value
                            video_info["channel_id"] = var_value
                        case _:
                            pass
                self.video_list.append(video_info)
        except Exception as e:
            self.console.error(f"Find video error: {e}")
            raise e
        return self.video_list

    def find_more_videos(self) -> Generator[Dict, None, None]:
        """
        fetch same channel videos by guid and channel id
        """
        channel_video_url = "https://api.cntv.cn/video/getVideoListByTopicIdInfo"
        try:
            params = {
                "videoid": self.video_id,
                "topicid": self.channel_id,
                "serviceId": "tvcctv",
                "type": "1",
                "t": "jsonp",
                "cb": "setItem1",
            }
            api_headers = self.headers.copy()
            api_headers["Accept"] = "*/*"
            api_headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
            api_headers["Referer"] = f"{self.scheme_host}/"
            api_headers["Sec-Fetch-Dest"] = "script"
            api_headers["Sec-Fetch-Mode"] = "no-cors"
            api_headers["Sec-Fetch-Site"] = "cross-site"
            # delete some keys
            api_headers.pop("Cache-Control")
            api_headers.pop("Connection")
            api_headers.pop("Host")
            api_headers.pop("Upgrade-Insecure-Requests")
            resp = requests.get(channel_video_url, params=params, headers=api_headers)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                content = resp.text
                match_json_str = re.search(r"\((.*)\)", content)
                if match_json_str:
                    same_guids  = set([video["guid"] for video in self.video_list])
                    json_str = match_json_str.group(1)
                    json_data = json.loads(json_str)
                    video_list = json_data["data"]
                    for video in video_list:
                        video_info = {
                            "url": video["video_url"],
                            "title": video["video_title"],
                            "vid": video["video_id"],
                            "guid": video["guid"],
                        }
                        # 判断guid是否重复，重复则不添加
                        if video_info["guid"] in same_guids:
                            continue
                        same_guids.add(video_info["guid"])
                        self.video_list.append(video_info)
                        yield video_info
        except Exception as e:
            self.console.error(f"Find video error: {e}")
            raise e

    def download_video(self, video_serial_no: int) -> Tuple[str, str]:
        """
        download video by serial number
        """
        video = self.video_list[video_serial_no - 1]
        self.console.info(f"Downloading video {video['title']}...")
        video_headers = self.headers.copy()
        video_headers["Accept"] = "*/*"
        video_headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
        video_headers["Origin"] = self.scheme_host
        video_headers["Priority"] = "u=1, i"
        video_headers["Referer"] = f"{self.scheme_host}/"
        video_headers["Sec-Fetch-Dest"] = "empty"
        video_headers["Sec-Fetch-Mode"] = "no-cors"
        video_headers["Sec-Fetch-Site"] = "cross-site"
        # delete some keys
        for key in ["Cache-Control", "Connection", "Host", "Upgrade-Insecure-Requests"]:
            video_headers.pop(key)

        try:
            vdr = VideoDownloader(
                [video],
                output=self.output,
                headers=video_headers,
            )
            vdr.download()
            return video["title"], SUCCESS
        except Exception as e:
            self.console.error(f"Download video error: {e}")
            raise Exception(f"Download video error:{e}")

    def download_all(self):
        records = {}
        for index, video in enumerate(self.video_list):
            try:
                name, ok = self.download_video(index + 1)
                records[name]=ok
            except Exception:
                records[video["title"]]= FAILED
        return records

    def video_count(self):
        """
        return video count
        """
        return len(self.video_list)
