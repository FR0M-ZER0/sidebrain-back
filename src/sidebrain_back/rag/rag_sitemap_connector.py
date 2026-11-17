from __future__ import annotations

import xml.etree.ElementTree as ElementTree


class RagSitemapConnector:
    @staticmethod
    def is_sitemap_index(xml_content: str) -> bool:
        root = ElementTree.fromstring(xml_content)
        return root.tag.rsplit("}", maxsplit=1)[-1] == "sitemapindex"

    @staticmethod
    def parse(xml_content: str) -> list[str]:
        root = ElementTree.fromstring(xml_content)
        locations = [
            node.text.strip()
            for node in root.iter()
            if node.tag.rsplit("}", maxsplit=1)[-1] == "loc"
            and node.text
            and node.text.strip()
        ]
        if not locations:
            raise ValueError("sitemap contains no locations")
        return locations
