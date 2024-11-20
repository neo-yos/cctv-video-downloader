#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def extract_host(url: str) -> str:
    from urllib.parse import urlparse
    # Prepend 'http://' if the URL doesn't have a scheme or '//' prefix
    if not url.startswith(('http://', 'https://', '//')):
        url = 'http://' + url
    parsed_url = urlparse(url, scheme='http')
    return f"{parsed_url.scheme}://{parsed_url.hostname}"



def extract_text_within_brackets(text):
    """
    Extract all text within angle brackets from a given string.

    Args:
        text (str): The string to extract from

    Returns:
        str: The extracted text
    """
    pattern =r'\《(.*?)》|\《(.*?)》'
    matches = re.findall(pattern, text)
    results = [match for match in matches]
    return " ".join(results)

def extract_text_after_brackets(text):
    pattern = r'(?<=》)([^《》]*)'
    matches = re.findall(pattern, text)
    results = [match for match in matches]
    return " ".join(results)