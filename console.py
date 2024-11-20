#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from rich.table import Table
from rich.console import Console
from rich.live import Live
from rich.status import Status
from typing import List, Dict

class VideoConsole(object):

    def __init__(self) -> None:
        self.videos = None
        self.console = Console()
        self.table = Table(header_style="bold green")
        self.colors = ["blue", "yellow", "green"]
        self.headers = ["序号", "标题", "源地址"]
        for index, header in enumerate(self.headers):
            match index:
                case 0:
                    self.table.add_column(header, justify="center", style=self.colors[index])
                case _:
                    self.table.add_column(header, style=self.colors[index])

    def create_table(self, videos: List[Dict] = None):
        if videos is None:
            return
        for index, video in enumerate(videos):
            self.table.add_row(str(index + 1), video["title"], video["url"])

    def append_to_table(self, generator_list):
        """append to table dynamically with rich.live"""
        row_count = self.table.row_count
        with Live(self.table, refresh_per_second=30) as live:
            for index, video in enumerate(generator_list):
                self.table.add_row(str(index + row_count + 1), video["title"], video["url"])
                time.sleep(0.01)
                live.update(self.table)

    def ask(self, prompt):
        return self.console.input(prompt)

    def echo(self, message, color: bool = False, err: bool = False, **kwargs):
        if color:
            self.console.print(message, style="bold green")
        elif err:
            self.console.print(message, style="bold red")
        else:
            self.console.print(message, style=kwargs.get("style"))

    def info(self, message):
        self.console.print(message, style="cyan bold")

    def error(self, message):
        self.console.print(message, style="bold red")

    def warning(self, message):
        self.console.print(message, style="bold yellow")

    def success(self):
        self.console.print(message, style="bold green")
        

class ConsoleLogger(object):

    def __init__(self, console) -> None:
        self.console = console

    def log(self, message):
        self.console.print(message)

    def error(self, message):
        self.console.print(message, style="bold red")

    def warning(self, message):
        self.console.print(message, style="bold yellow")

    def success(self, message):
        self.console.print(message, style="bold green")

    def info(self, message):
        self.console.print(message, style="bold blue")
