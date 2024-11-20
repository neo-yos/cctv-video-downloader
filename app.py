#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import re
from console import VideoConsole
from download import VideoCrawler, SUCCESS, FAILED


@click.command()
@click.option("--url","-u", required=True, help="the video url that you want to download")
@click.option("--output", "-o", default=".", help="the output path")
def parse_video(url: str, output: str):
    """Parse video information from given url"""
    # validate url use regex, if not valid, console echo error
    url_pattern = r"(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w\.-]*)*\/?$"
    if not re.match(url_pattern, url):
        click.echo(click.style("Invalid url, please try again!", bg="red"))
        return
    try:
        vc = VideoConsole()
        crawler = VideoCrawler(url=url, output=output, console=vc)
        vc.create_table(crawler.find_video())
        more_videos = crawler.find_more_videos()
        vc.append_to_table(more_videos)
        video_count = crawler.video_count()
        # ask user to select a video to download
        while True:
            answer = vc.ask("请选择需要下载的视频序号：")
            match answer:
                case "q" | "Q":
                    vc.echo("Exit, bye bye!", color=True)
                    break
                case n if n.isdigit() and 1 <= int(n) <= video_count:
                    title, ok = crawler.download_video(int(n))
                    match ok:
                        case "success":
                            vc.echo(f"Download video {title} successfully", color=True)
                        case "failed":
                            vc.echo(f"Download video {title} failed", err=True)
                            break
                case n if n.isdigit() and int(n) > video_count:
                    vc.echo("video serial number out of range", err=True)
                case "y" | "Y":
                    # download all list videos
                    results = crawler.download_all()
                    # check all values are success or not
                    if any(ok == "failed" for _, ok in results):
                        for name, value in results:
                            if value == "failed":
                                vc.echo(f"Download video {name} failed", err=True)
                    else:
                        vc.echo(f"Download all videos successfully", color=True)
                    break
                case _:
                    vc.echo(f"Invalid input: {answer}", err=True)
    except Exception as ex:
        click.echo(f"Parse video information failed: {ex}")


if __name__ == "__main__":
    parse_video()
