import styles from "./Answer.module.css";

export const transformYotubeUrlsToEmbdedded = (str: string, iframeWidth: number): string => {
  const urls = extractVimeoUrls(str);
  const urlTransformations: Record<string, string> = {};
  urls.forEach((url) => {
      const id = extractVimeoId(url);
      const height = iframeWidth * 9 / 16 // keep 16 x 9 ratio.
      urlTransformations[url] = `<div class="${styles.videoContainer}" style="width: ${iframeWidth}px; height: ${height}px" ><iframe src="https://player.vimeo.com/video/${id}" frameborder="0" allowfullscreen></iframe></div>`;
  });
  let transformedStr = str;
  for (const [url, transformation] of Object.entries(urlTransformations)) {
    transformedStr = transformedStr.replace(url, transformation);
  }
  return transformedStr;
};

const extractVimeoUrls = (str: string): Set<string> => {
    const vimeoUrlRegex = /https:\/\/player\.vimeo\.com\/video\/(\d+)/g;
    const urls = new Set<string>();
    let match;
    while ((match = vimeoUrlRegex.exec(str)) !== null) {
        urls.add(match[0]);
    }
    return urls;
};

const extractVimeoId = (url: string): string => {
    const vimeoBaseUrl = "https://player.vimeo.com/video/";
    if (url.startsWith(vimeoBaseUrl)) {
        const idPart = url.slice(vimeoBaseUrl.length);
        return idPart;
    }

    return "";
}