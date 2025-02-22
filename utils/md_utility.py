import streamlit as st
import os
import re
import base64
from pathlib import Path

"""  
Usage
with open("README.md", "r") as readme_file:
    readme = readme_file.read()

readme = markdown_insert_images(readme)

with st.container():
    st.markdown(readme, unsafe_allow_html=True)
"""

def markdown_images(markdown):
    """ 
    Example: ![Test image](images/test.png "Alternate text")
    """
    images = re.findall(r'(!\[(?P<image_title>[^\]]+)\]\((?P<image_path>[^\)"\s]+)\s*([^\)]*)\))', markdown)
    return images


def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded


def img_to_html(img_path, img_alt):
    img_format = img_path.split(".")[-1]
    img_html = f'<img src="data:image/{img_format.lower()};base64,{img_to_bytes(img_path)}" alt="{img_alt}" style="max-width: 100%;">'
    return img_html


def markdown_insert_images(markdown):
    images = markdown_images(markdown)

    for image in images:
        image_markdown = image[0]
        image_alt = image[1]
        image_path = image[2]
        if os.path.exists(image_path):
            markdown = markdown.replace(image_markdown, img_to_html(image_path, image_alt))

    # Add two newlines before each image HTML to ensure it's treated as a separate block
    markdown = re.sub(r'(<img [^>]*>)', r'\n\n\1', markdown)
    return markdown
