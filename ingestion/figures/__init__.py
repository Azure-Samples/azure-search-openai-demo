"""
Figure processing and media description utilities.
"""

from .processor import FigureProcessor, MediaDescriptionStrategy, build_figure_markup, process_page_image
from .describers import ContentUnderstandingDescriber, MediaDescriber, MultimodalModelDescriber

__all__ = [
    "FigureProcessor",
    "MediaDescriptionStrategy",
    "build_figure_markup",
    "process_page_image",
    "MediaDescriber",
    "ContentUnderstandingDescriber",
    "MultimodalModelDescriber",
]
