import re
import requests

from urllib.parse import urlparse
from bs4 import BeautifulSoup


class SitePageHeader:
    def __init__(self, id, title, name, source_url):
        self.id = id
        self.title = title
        self.name = name
        self.source_url = source_url


class SitePage:
    def __init__(self, header: SitePageHeader):
        self.header = header
        self.text_content = None
        self.tags = None

    def set_text_content(self, text_content):
        self.text_content = text_content

    def set_tags(self, tags):
        self.tags = tags


class SharePointHelper:

    def get_site_id(self, site_url, access_token):
        if not site_url:
            raise ValueError("'site_url' can not be empty")

        parsed_url = urlparse(site_url)
        host_name = parsed_url.hostname
        relative_path = parsed_url.path

        endpoint = (
            f"https://graph.microsoft.com/v1.0/sites/{host_name}:/{relative_path}"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            site_data = response.json()
            site_id = site_data["id"]
            return site_id
        else:
            raise ConnectionError(
                "Failed to retrieve site information from Microsoft Graph API"
            )

    def get_page_headers(self, site_id, access_token):
        if not site_id:
            raise ValueError("'site_id' can not be empty")

        endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/pages"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            pages = []
            pages_data = response.json()["value"]
            for page in pages_data:
                if (
                    "@odata.type" not in page
                    or page["@odata.type"] != "#microsoft.graph.sitePage"
                ):
                    continue

                id = page["id"]
                title = page["title"]
                name = page["name"]
                source_url = page["webUrl"]
                pages.append(SitePageHeader(id, title, name, source_url))

            return pages
        else:
            raise ConnectionError(
                "Failed to retrieve pages information from Microsoft Graph API"
            )

    def extract_project_description(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        headers = soup.find_all("span", class_="fontColorThemePrimary")
        text = ""

        for i, header in enumerate(headers):
            if i > 0:
                text += "\n\n"
            header_text = header.get_text(" ", strip=True)
            text += f"{header_text}\n"

            paragraph = header.find_parent("p")

            next_sibling = paragraph.find_next_sibling()
            while next_sibling:
                if next_sibling.find("span", class_="fontColorThemePrimary"):
                    break
                sibling_text = next_sibling.get_text(" ", strip=True)
                if sibling_text:
                    text += f"{sibling_text} "
                next_sibling = next_sibling.find_next_sibling()

        return text.strip()

    def extract_text(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(" ", strip=True)

    def get_site_page(self, site_id, page_header, access_token):
        if not page_header:
            raise ValueError("'page_header' can not be empty")

        endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/pages/{page_header.id}/microsoft.graph.sitepage/webparts"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            page_data = response.json()["value"]
            site_page = SitePage(header=page_header)
            project_description_marker = "Project Overview"
            tags_marker = "Tags"
            for index, item in reversed(list(enumerate(page_data))):
                if (
                    "@odata.type" not in item
                    or item["@odata.type"] != "#microsoft.graph.textWebPart"
                    or "innerHtml" not in item
                ):
                    continue

                inner_html = item["innerHtml"]
                if project_description_marker in inner_html:
                    del page_data[index]
                    inner_html = self._remove_substring(
                        inner_html, project_description_marker
                    )
                    text_content = self.extract_project_description(
                        html_content=inner_html
                    )
                    site_page.set_text_content(text_content)

                elif tags_marker in inner_html:
                    del page_data[index]
                    inner_html = self._remove_substring(inner_html, tags_marker)
                    text_content = self.extract_text(html_content=inner_html)
                    tags = self.extract_tags(html_content=inner_html)
                    site_page.set_tags(tags)

            return site_page

        else:
            raise ConnectionError(
                "Failed to retrieve pages information from Microsoft Graph API"
            )

    def extract_tags(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        headings = soup.find_all("h3")
        tags = {}
        current_category = None

        for heading in headings:
            category_name = heading.text.strip()
            if category_name:
                category_name = category_name.strip(":")
                current_category = category_name
                tags[current_category] = []
                items_paragraph = heading.find_next_sibling()
                items = items_paragraph.text.split(",")
                for item in items:
                    tags[current_category].append(self._peel_text(text=item.strip()))

        return tags

    def _peel_text(self, text):
        return re.sub(r"[^\w\s,]", "", text)

    def _remove_substring(self, original_string, substring):
        return original_string.replace(substring, "")

    def get_site_pages_as_json(self, site_id: str, access_token: str):
        site_page_headers = self.get_page_headers(site_id, access_token)

        pages = []
        for site_page in [
            self.get_site_page(site_id, page_header, access_token)
            for page_header in site_page_headers
        ]:
            if site_page.text_content and site_page.tags:
                pages.append(
                    {
                        "content": site_page.text_content,
                        "title": site_page.header.title,
                        "tags": site_page.tags,
                        "source_url": site_page.header.source_url,
                    }
                )

        return pages
